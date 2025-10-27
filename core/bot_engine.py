"""
Bot Engine - Four-Bot Trading System
Implements PAIN BUY, PAIN SELL, GAIN BUY, GAIN SELL bots per symbol.
All bots run in parallel with independent state machines.
"""

from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

from .data_resampler import DataResampler
from .timezone_handler import TimezoneHandler
from .daily_bias import DailyBiasService
from .indicators import IndicatorCalculator
from .trend_filter import TrendFilterService
from .m30_break_detector import M30BreakDetector
from .m1_state_machine import M1StateMachine
from .fibonacci_checker import FibonacciChecker
from .config_loader import config


class BotType(Enum):
    """Four bot types"""
    PAIN_BUY = "pain_buy"
    PAIN_SELL = "pain_sell"
    GAIN_BUY = "gain_buy"
    GAIN_SELL = "gain_sell"


class BotState(Enum):
    """Bot operational states"""
    IDLE = "idle"                  # No conditions met
    SCANNING = "scanning"          # Checking conditions
    READY = "ready"                # All conditions met, ready to enter
    IN_POSITION = "in_position"    # Trade active
    HALTED = "halted"              # Stopped (e.g., day-stop triggered)


class BotEngine:
    """
    Main bot engine managing all four bots per symbol.
    Deterministic rule-based execution.
    """

    def __init__(self, mt5_connector):
        """
        Initialize bot engine.

        Args:
            mt5_connector: MT5Connector instance for market data and orders
        """
        self.connector = mt5_connector

        # Initialize all services
        self.tz_handler = TimezoneHandler(
            timezone=config.get_environment_timezone(),
            daily_close_hour=16
        )

        self.resampler = DataResampler(timezone=self.tz_handler.timezone.zone)

        self.daily_bias = DailyBiasService(
            self.tz_handler,
            epsilon=config.get_daily_bias_epsilon()
        )

        # Get indicator parameters from config (user-adjustable)
        snake_period = config.get_snake_period()  # Days parameter
        purple_period = config.get_purple_line_period()  # Days parameter
        smoothing = config.get_ema_smoothing()  # Smoothing factor

        self.indicator_calc = IndicatorCalculator(snake_period, purple_period, smoothing)

        equality_is_not_trend = config.get_equality_is_not_trend()
        self.trend_filter = TrendFilterService(self.indicator_calc, equality_is_not_trend)

        self.m30_break = M30BreakDetector()

        max_bars_between = config.get_max_bars_between_cross_and_touch()
        self.m1_state = M1StateMachine(max_bars_between)

        h4_candidates = config.get_h4_candidates()
        self.fib_checker = FibonacciChecker(h4_candidates)

        # Bot states per symbol
        # symbol -> {bot_type -> {state, position_ticket, entry_time, etc.}}
        self.bot_states = {}

        # Last processed bar timestamps (to ensure closed candles only)
        self.last_processed_time = {}

    def update_indicator_periods(self, snake_period: int, purple_period: int):
        """
        Update indicator periods (called when user changes via UI).

        Args:
            snake_period: New Snake period
            purple_period: New Purple period
        """
        self.indicator_calc.set_periods(snake_period, purple_period)

    def initialize_symbol(self, symbol: str):
        """
        Initialize bot states for a symbol.

        Args:
            symbol: Trading symbol
        """
        if symbol not in self.bot_states:
            self.bot_states[symbol] = {}

            for bot_type in BotType:
                self.bot_states[symbol][bot_type] = {
                    'state': BotState.IDLE,
                    'position_ticket': None,
                    'entry_time': None,
                    'entry_price': None,
                    'reasons': [],
                    'last_check': None
                }

    def process_symbol(self, symbol: str, m1_bars: List[Dict], d1_bars_mt5: List[Dict] = None) -> Dict:
        """
        Process one symbol through all four bots.

        Args:
            symbol: Trading symbol
            m1_bars: List of M1 OHLC bars (closed candles only)
            d1_bars_mt5: Optional D1 bars from MT5 (uses broker's daily boundary).
                         If provided, these are used for daily bias instead of resampled D1.

        Returns:
            Dictionary with bot states and signals
        """
        self.initialize_symbol(symbol)

        # Resample to all timeframes (except D1 if MT5 D1 bars provided)
        tf_data = self.resampler.resample_all_timeframes(m1_bars)

        # Calculate indicators for all timeframes
        tf_indicators = {}
        for tf, bars in tf_data.items():
            tf_indicators[tf] = self.indicator_calc.get_indicators_for_bars(bars, f"{symbol}_{tf}")

        # Get daily bias using MT5's native D1 bars if provided, otherwise use resampled
        d1_bars = d1_bars_mt5 if d1_bars_mt5 is not None else tf_data.get('D1', [])
        bias_result = self.daily_bias.get_bias(symbol, d1_bars)
        bias = bias_result['bias']
        level50 = bias_result.get('level50')

        # Check day-stop for PAIN SELL
        if bias == 'SELL' and level50 is not None:
            current_low = min([bar['low'] for bar in m1_bars[-10:]]) if m1_bars else 0
            if self.daily_bias.is_day_stop_triggered(symbol, current_low):
                # Halt PAIN SELL bot
                self.bot_states[symbol][BotType.PAIN_SELL]['state'] = BotState.HALTED
                self.bot_states[symbol][BotType.PAIN_SELL]['reasons'] = ['Day-stop triggered (50% wick filled)']

        # Check trend alignment
        trend_buy = self.trend_filter.check_alignment(tf_indicators, 'green')
        trend_sell = self.trend_filter.check_alignment(tf_indicators, 'red')

        # Update M30 break detector
        m30_bars = tf_data.get('M30', [])
        m30_snake = tf_indicators.get('M30', {}).get('snake', [])
        self.m30_break.update(symbol, m30_bars, m30_snake)

        # Update M1 state machine
        m1_bars_data = tf_data.get('M1', [])
        m1_purple = tf_indicators.get('M1', {}).get('purple', [])
        m1_snake = tf_indicators.get('M1', {}).get('snake', [])
        self.m1_state.update(symbol, m1_bars_data, m1_purple, m1_snake)

        # Check bots based on symbol type
        results = {}

        # Determine symbol type
        is_pain = config.is_pain_symbol(symbol)
        is_gain = config.is_gain_symbol(symbol)

        # PAIN bots only for PainX symbols
        if is_pain:
            results[BotType.PAIN_BUY] = self._check_pain_buy(
                symbol, bias, trend_buy, m30_bars, m30_snake, tf_indicators
            )
            results[BotType.PAIN_SELL] = self._check_pain_sell(
                symbol, bias, trend_sell, m30_bars, m30_snake, tf_indicators
            )

        # GAIN bots only for GainX symbols
        if is_gain:
            m15_bars = tf_data.get('M15', [])
            h4_bars = tf_data.get('H4', [])
            results[BotType.GAIN_BUY] = self._check_gain_buy(
                symbol, bias, trend_buy, m15_bars, h4_bars, tf_indicators
            )
            results[BotType.GAIN_SELL] = self._check_gain_sell(
                symbol, bias, trend_sell, m15_bars, h4_bars, tf_indicators
            )

        return {
            'symbol': symbol,
            'bias': bias,
            'level50': level50,
            'trend_summary': self.trend_filter.get_trend_summary(tf_indicators),
            'm1_state': self.m1_state.get_state_summary(symbol),
            'bot_results': results,
            'timestamp': self.tz_handler.now().isoformat()
        }

    def _check_pain_buy(self, symbol: str, bias: str, trend: Dict,
                        m30_bars: List[Dict], m30_snake: List[float],
                        tf_indicators: Dict) -> Dict:
        """Check PAIN BUY bot conditions"""
        reasons = []
        ready = True

        # 1. BUY day only
        if bias == 'BUY':
            reasons.append({
                'text': "✓ BUY day",
                'detail': "Yesterday's D1 candle has a long lower wick indicating buyers rejected lower prices"
            })
        else:
            reasons.append({
                'text': f"✗ Not a BUY day (bias: {bias})",
                'detail': f"Daily bias is {bias}. PAIN BUY requires a BUY day (long lower wick on yesterday's D1 candle)"
            })
            ready = False

        # 2. Trend alignment (H1, M30, M15 green)
        if trend['aligned']:
            reasons.append({
                'text': "✓ Trend aligned (H1/M30/M15 green)",
                'detail': "All three timeframes (H1, M30, M15) have price above Snake (EMA100), confirming uptrend"
            })
        else:
            reasons.append({
                'text': f"✗ Trend not aligned: {', '.join(trend['missing'])}",
                'detail': f"Need all timeframes green (price > EMA100). Current: {', '.join(trend['missing'])}"
            })
            ready = False

        # 3. M30 clean break above snake
        if self.m30_break.check_upward_break(symbol, m30_bars, m30_snake):
            reasons.append({
                'text': "✓ M30 clean break above snake",
                'detail': "M30 candle closed above Snake (EMA100) and held for required persistence"
            })
        else:
            reasons.append({
                'text': "✗ M30: No clean break above snake",
                'detail': "Need M30 candle to close above Snake (EMA100) and hold for persistence bars"
            })
            ready = False

        # 4. M1 cross-then-touch
        if self.m1_state.is_buy_signal(symbol):
            reasons.append({
                'text': "✓ M1 cross-then-touch BUY signal",
                'detail': "M1 crossed above Purple line (EMA10) then touched it again from above"
            })
        else:
            reasons.append({
                'text': "✗ M1: No cross-then-touch BUY signal",
                'detail': "Need M1 to cross above Purple (EMA10), then touch it again from above within max bars"
            })
            ready = False

        return {'ready': ready, 'reasons': reasons}

    def _check_pain_sell(self, symbol: str, bias: str, trend: Dict,
                         m30_bars: List[Dict], m30_snake: List[float],
                         tf_indicators: Dict) -> Dict:
        """Check PAIN SELL bot conditions"""
        reasons = []
        ready = True

        # Check if halted (always show this first)
        is_halted = self.bot_states[symbol][BotType.PAIN_SELL]['state'] == BotState.HALTED
        if is_halted:
            reasons.append({
                'text': "✗ HALTED: Day-stop triggered",
                'detail': "Today's low breached 50% of yesterday's lower wick - PAIN SELL halted for the day"
            })
            ready = False
        else:
            reasons.append({
                'text': "✓ Not halted",
                'detail': "Day-stop not triggered (today's low hasn't breached 50% of yesterday's lower wick)"
            })

        # 1. SELL day only
        if bias == 'SELL':
            reasons.append({
                'text': "✓ SELL day",
                'detail': "Yesterday's D1 candle has a long upper wick indicating sellers rejected higher prices"
            })
        else:
            reasons.append({
                'text': f"✗ Not a SELL day (bias: {bias})",
                'detail': f"Daily bias is {bias}. PAIN SELL requires a SELL day (long upper wick on yesterday's D1 candle)"
            })
            ready = False

        # 2. Trend alignment (H1, M30, M15 red)
        if trend['aligned']:
            reasons.append({
                'text': "✓ Trend aligned (H1/M30/M15 red)",
                'detail': "All three timeframes (H1, M30, M15) have price below Snake (EMA100), confirming downtrend"
            })
        else:
            reasons.append({
                'text': f"✗ Trend not aligned: {', '.join(trend['missing'])}",
                'detail': f"Need all timeframes red (price < EMA100). Current: {', '.join(trend['missing'])}"
            })
            ready = False

        # 3. M30 clean break below snake
        if self.m30_break.check_downward_break(symbol, m30_bars, m30_snake):
            reasons.append({
                'text': "✓ M30 clean break below snake",
                'detail': "M30 candle closed below Snake (EMA100) and held for required persistence"
            })
        else:
            reasons.append({
                'text': "✗ M30: No clean break below snake",
                'detail': "Need M30 candle to close below Snake (EMA100) and hold for persistence bars"
            })
            ready = False

        # 4. M1 cross-then-touch
        if self.m1_state.is_sell_signal(symbol):
            reasons.append({
                'text': "✓ M1 cross-then-touch SELL signal",
                'detail': "M1 crossed below Purple line (EMA10) then touched it again from below"
            })
        else:
            reasons.append({
                'text': "✗ M1: No cross-then-touch SELL signal",
                'detail': "Need M1 to cross below Purple (EMA10), then touch it again from below within max bars"
            })
            ready = False

        return {'ready': ready, 'reasons': reasons}

    def _check_gain_buy(self, symbol: str, bias: str, trend: Dict,
                        m15_bars: List[Dict], h4_bars: List[Dict],
                        tf_indicators: Dict) -> Dict:
        """Check GAIN BUY bot conditions"""
        reasons = []
        ready = True

        # 1. BUY day only
        if bias == 'BUY':
            reasons.append({
                'text': "✓ BUY day",
                'detail': "Yesterday's D1 candle has a long lower wick indicating buyers rejected lower prices"
            })
        else:
            reasons.append({
                'text': f"✗ Not a BUY day (bias: {bias})",
                'detail': f"Daily bias is {bias}. GAIN BUY requires a BUY day (long lower wick on yesterday's D1 candle)"
            })
            ready = False

        # 2. Structure check (M15 + H4 Fibonacci)
        structure = self.fib_checker.check_gain_buy_structure(m15_bars, h4_bars)
        if structure['valid']:
            reasons.append({
                'text': f"✓ Structure valid (Fib50: {structure['fib50']:.5f})",
                'detail': f"M15 has valid swing low and H4's largest body candle covers Fib 50% at {structure['fib50']:.5f}"
            })
        else:
            reasons.append({
                'text': f"✗ Structure: {structure['reason']}",
                'detail': "Need M15 swing low (3-bar pattern) and H4 largest-body candle covering Fib 50% level"
            })
            ready = False

        # 3. Trend alignment (H1, M30, M15 green)
        if trend['aligned']:
            reasons.append({
                'text': "✓ Trend aligned (H1/M30/M15 green)",
                'detail': "All three timeframes (H1, M30, M15) have price above Snake (EMA100), confirming uptrend"
            })
        else:
            reasons.append({
                'text': f"✗ Trend not aligned: {', '.join(trend['missing'])}",
                'detail': f"Need all timeframes green (price > EMA100). Current: {', '.join(trend['missing'])}"
            })
            ready = False

        # 4. M1 cross-then-touch (same as PAIN BUY)
        if self.m1_state.is_buy_signal(symbol):
            reasons.append({
                'text': "✓ M1 cross-then-touch BUY signal",
                'detail': "M1 crossed above Purple line (EMA10) then touched it again from above"
            })
        else:
            reasons.append({
                'text': "✗ M1: No cross-then-touch BUY signal",
                'detail': "Need M1 to cross above Purple (EMA10), then touch it again from above within max bars"
            })
            ready = False

        return {'ready': ready, 'reasons': reasons}

    def _check_gain_sell(self, symbol: str, bias: str, trend: Dict,
                         m15_bars: List[Dict], h4_bars: List[Dict],
                         tf_indicators: Dict) -> Dict:
        """Check GAIN SELL bot conditions"""
        reasons = []
        ready = True

        # 1. SELL day only
        if bias == 'SELL':
            reasons.append({
                'text': "✓ SELL day",
                'detail': "Yesterday's D1 candle has a long upper wick indicating sellers rejected higher prices"
            })
        else:
            reasons.append({
                'text': f"✗ Not a SELL day (bias: {bias})",
                'detail': f"Daily bias is {bias}. GAIN SELL requires a SELL day (long upper wick on yesterday's D1 candle)"
            })
            ready = False

        # 2. Structure check (M15 + H4 Fibonacci)
        structure = self.fib_checker.check_gain_sell_structure(m15_bars, h4_bars)
        if structure['valid']:
            reasons.append({
                'text': f"✓ Structure valid (Fib50: {structure['fib50']:.5f})",
                'detail': f"M15 has valid swing high and H4's largest body candle covers Fib 50% at {structure['fib50']:.5f}"
            })
        else:
            reasons.append({
                'text': f"✗ Structure: {structure['reason']}",
                'detail': "Need M15 swing high (3-bar pattern) and H4 largest-body candle covering Fib 50% level"
            })
            ready = False

        # 3. Trend alignment (H1, M30, M15 red)
        if trend['aligned']:
            reasons.append({
                'text': "✓ Trend aligned (H1/M30/M15 red)",
                'detail': "All three timeframes (H1, M30, M15) have price below Snake (EMA100), confirming downtrend"
            })
        else:
            reasons.append({
                'text': f"✗ Trend not aligned: {', '.join(trend['missing'])}",
                'detail': f"Need all timeframes red (price < EMA100). Current: {', '.join(trend['missing'])}"
            })
            ready = False

        # 4. M1 cross-then-touch (same as PAIN SELL)
        if self.m1_state.is_sell_signal(symbol):
            reasons.append({
                'text': "✓ M1 cross-then-touch SELL signal",
                'detail': "M1 crossed below Purple line (EMA10) then touched it again from below"
            })
        else:
            reasons.append({
                'text': "✗ M1: No cross-then-touch SELL signal",
                'detail': "Need M1 to cross below Purple (EMA10), then touch it again from below within max bars"
            })
            ready = False

        return {'ready': ready, 'reasons': reasons}

    def get_bot_summary(self, symbol: str) -> str:
        """
        Get human-readable summary of all bot states for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Summary string
        """
        if symbol not in self.bot_states:
            return "No bots initialized"

        parts = []
        for bot_type in BotType:
            state = self.bot_states[symbol][bot_type]
            parts.append(f"{bot_type.value}: {state['state'].value}")

        return " | ".join(parts)
