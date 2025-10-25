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

        # Get indicator periods (user-adjustable)
        snake_period = config.get_snake_period()
        purple_period = config.get_purple_line_period()

        self.indicator_calc = IndicatorCalculator(snake_period, purple_period)

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

    def process_symbol(self, symbol: str, m1_bars: List[Dict]) -> Dict:
        """
        Process one symbol through all four bots.

        Args:
            symbol: Trading symbol
            m1_bars: List of M1 OHLC bars (closed candles only)

        Returns:
            Dictionary with bot states and signals
        """
        self.initialize_symbol(symbol)

        # Resample to all timeframes
        tf_data = self.resampler.resample_all_timeframes(m1_bars)

        # Calculate indicators for all timeframes
        tf_indicators = {}
        for tf, bars in tf_data.items():
            tf_indicators[tf] = self.indicator_calc.get_indicators_for_bars(bars, f"{symbol}_{tf}")

        # Get daily bias
        d1_bars = tf_data.get('D1', [])
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

        # Check each bot
        results = {}

        # PAIN BUY
        results[BotType.PAIN_BUY] = self._check_pain_buy(
            symbol, bias, trend_buy, m30_bars, m30_snake, tf_indicators
        )

        # PAIN SELL
        results[BotType.PAIN_SELL] = self._check_pain_sell(
            symbol, bias, trend_sell, m30_bars, m30_snake, tf_indicators
        )

        # GAIN BUY
        m15_bars = tf_data.get('M15', [])
        h4_bars = tf_data.get('H4', [])
        results[BotType.GAIN_BUY] = self._check_gain_buy(
            symbol, bias, trend_buy, m15_bars, h4_bars, tf_indicators
        )

        # GAIN SELL
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
        ready = False

        # 1. BUY day only
        if bias != 'BUY':
            reasons.append(f"Not a BUY day (bias: {bias})")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ BUY day")

        # 2. Trend alignment (H1, M30, M15 green)
        if not trend['aligned']:
            reasons.append(f"Trend not aligned: {', '.join(trend['missing'])}")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ Trend aligned (H1/M30/M15 green)")

        # 3. M30 clean break above snake
        if not self.m30_break.check_upward_break(symbol, m30_bars, m30_snake):
            reasons.append("M30: No clean break above snake")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ M30 clean break above snake")

        # 4. M1 cross-then-touch
        if not self.m1_state.is_buy_signal(symbol):
            reasons.append("M1: No cross-then-touch BUY signal")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ M1 cross-then-touch BUY signal")

        # All conditions met!
        ready = True
        return {'ready': ready, 'reasons': reasons}

    def _check_pain_sell(self, symbol: str, bias: str, trend: Dict,
                         m30_bars: List[Dict], m30_snake: List[float],
                         tf_indicators: Dict) -> Dict:
        """Check PAIN SELL bot conditions"""
        reasons = []
        ready = False

        # Check if halted
        if self.bot_states[symbol][BotType.PAIN_SELL]['state'] == BotState.HALTED:
            reasons.append("HALTED: Day-stop triggered")
            return {'ready': False, 'reasons': reasons}

        # 1. SELL day only
        if bias != 'SELL':
            reasons.append(f"Not a SELL day (bias: {bias})")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ SELL day")

        # 2. Trend alignment (H1, M30, M15 red)
        if not trend['aligned']:
            reasons.append(f"Trend not aligned: {', '.join(trend['missing'])}")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ Trend aligned (H1/M30/M15 red)")

        # 3. M30 clean break below snake
        if not self.m30_break.check_downward_break(symbol, m30_bars, m30_snake):
            reasons.append("M30: No clean break below snake")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ M30 clean break below snake")

        # 4. M1 cross-then-touch
        if not self.m1_state.is_sell_signal(symbol):
            reasons.append("M1: No cross-then-touch SELL signal")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ M1 cross-then-touch SELL signal")

        # All conditions met!
        ready = True
        return {'ready': ready, 'reasons': reasons}

    def _check_gain_buy(self, symbol: str, bias: str, trend: Dict,
                        m15_bars: List[Dict], h4_bars: List[Dict],
                        tf_indicators: Dict) -> Dict:
        """Check GAIN BUY bot conditions"""
        reasons = []
        ready = False

        # 1. BUY day only
        if bias != 'BUY':
            reasons.append(f"Not a BUY day (bias: {bias})")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ BUY day")

        # 2. Structure check (M15 + H4 Fibonacci)
        structure = self.fib_checker.check_gain_buy_structure(m15_bars, h4_bars)
        if not structure['valid']:
            reasons.append(f"Structure: {structure['reason']}")
            return {'ready': False, 'reasons': reasons}

        reasons.append(f"✓ Structure valid (Fib50: {structure['fib50']:.5f})")

        # 3. Trend alignment (H1, M30, M15 green)
        if not trend['aligned']:
            reasons.append(f"Trend not aligned: {', '.join(trend['missing'])}")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ Trend aligned (H1/M30/M15 green)")

        # 4. M1 cross-then-touch (same as PAIN BUY)
        if not self.m1_state.is_buy_signal(symbol):
            reasons.append("M1: No cross-then-touch BUY signal")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ M1 cross-then-touch BUY signal")

        # All conditions met!
        ready = True
        return {'ready': ready, 'reasons': reasons}

    def _check_gain_sell(self, symbol: str, bias: str, trend: Dict,
                         m15_bars: List[Dict], h4_bars: List[Dict],
                         tf_indicators: Dict) -> Dict:
        """Check GAIN SELL bot conditions"""
        reasons = []
        ready = False

        # 1. SELL day only
        if bias != 'SELL':
            reasons.append(f"Not a SELL day (bias: {bias})")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ SELL day")

        # 2. Structure check (M15 + H4 Fibonacci)
        structure = self.fib_checker.check_gain_sell_structure(m15_bars, h4_bars)
        if not structure['valid']:
            reasons.append(f"Structure: {structure['reason']}")
            return {'ready': False, 'reasons': reasons}

        reasons.append(f"✓ Structure valid (Fib50: {structure['fib50']:.5f})")

        # 3. Trend alignment (H1, M30, M15 red)
        if not trend['aligned']:
            reasons.append(f"Trend not aligned: {', '.join(trend['missing'])}")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ Trend aligned (H1/M30/M15 red)")

        # 4. M1 cross-then-touch (same as PAIN SELL)
        if not self.m1_state.is_sell_signal(symbol):
            reasons.append("M1: No cross-then-touch SELL signal")
            return {'ready': False, 'reasons': reasons}

        reasons.append("✓ M1 cross-then-touch SELL signal")

        # All conditions met!
        ready = True
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
