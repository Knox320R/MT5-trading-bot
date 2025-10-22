"""
Signal Detection Module
Detects perfect trading moments based on multi-timeframe analysis
"""
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from .mt5_connector import MT5Connector
from .config_loader import config


class SignalDetector:
    def __init__(self, connector: MT5Connector):
        self.connector = connector
        self.timeframes = ['D1', 'H4', 'H1', 'M30', 'M15', 'M5', 'M1']

    def calculate_ema(self, prices, period):
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)

        # Start with SMA
        sma = sum(prices[:period]) / period
        ema = sma

        # Calculate EMA
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def get_multi_timeframe_data(self, symbol):
        """Fetch data for all timeframes"""
        data = {}

        for tf in self.timeframes:
            bars = self.connector.get_bars(symbol, tf, 100)
            if bars:
                close_prices = [bar['close'] for bar in bars]
                high_prices = [bar['high'] for bar in bars]
                low_prices = [bar['low'] for bar in bars]

                # Calculate indicators
                snake = self.calculate_ema(close_prices, 100)
                purple_line = self.calculate_ema(close_prices, 10)

                data[tf] = {
                    'bars': bars,
                    'close': close_prices[-1] if close_prices else None,
                    'high': high_prices[-1] if high_prices else None,
                    'low': low_prices[-1] if low_prices else None,
                    'snake': snake,
                    'purple_line': purple_line,
                    'snake_color': 'green' if snake and snake < close_prices[-1] else 'red',
                    'price_vs_snake': 'above' if close_prices[-1] > snake else 'below',
                    'price_vs_purple': 'above' if close_prices[-1] > purple_line else 'below'
                }

        return data

    def analyze_d1_wick(self, bars):
        """Analyze D1 candle wick for daily bias"""
        if len(bars) < 2:
            return None, None

        prev_candle = bars[-2]
        current_candle = bars[-1]

        # Calculate body and wicks
        body_size = abs(prev_candle['close'] - prev_candle['open'])
        upper_wick = prev_candle['high'] - max(prev_candle['open'], prev_candle['close'])
        lower_wick = min(prev_candle['open'], prev_candle['close']) - prev_candle['low']

        # Determine bias
        bias = None
        if lower_wick > upper_wick and body_size < lower_wick:
            bias = 'SELL'
        elif upper_wick > lower_wick and body_size < upper_wick:
            bias = 'BUY'

        # Check if 50% wick filled
        longest_wick = max(upper_wick, lower_wick)
        wick_50_percent = longest_wick * 0.5

        if bias == 'SELL':
            current_move = current_candle['high'] - prev_candle['low']
            wick_filled = current_move >= wick_50_percent
        elif bias == 'BUY':
            current_move = prev_candle['high'] - current_candle['low']
            wick_filled = current_move >= wick_50_percent
        else:
            wick_filled = False

        return bias, wick_filled

    def check_fibonacci_retracement(self, h4_data, m15_data):
        """Check if H4 candle covers 50% of Fibonacci retracement"""
        if not h4_data or not m15_data:
            return False

        # This is simplified - full implementation would calculate actual Fib levels
        # For now, we'll check if H4 previous candle moved at least 50% of the range
        h4_bars = h4_data['bars']
        if len(h4_bars) < 2:
            return False

        prev_h4 = h4_bars[-2]
        body_size = abs(prev_h4['close'] - prev_h4['open'])
        candle_range = prev_h4['high'] - prev_h4['low']

        return body_size >= (candle_range * 0.5)

    def detect_purple_line_breakout(self, m1_data, m5_data):
        """Detect Purple Line breakout and touchback"""
        if not m1_data or not m1_data['bars'] or len(m1_data['bars']) < 3:
            return False, False

        bars = m1_data['bars']
        purple = m1_data['purple_line']

        # Check last 3 candles for breakout and touchback pattern
        candle_1 = bars[-3]  # Oldest
        candle_2 = bars[-2]  # Middle
        candle_3 = bars[-1]  # Current

        # Breakout down: candle crosses below purple line
        breakout_down = (candle_1['close'] > purple and candle_2['close'] < purple)
        # Touchback: price returns to touch purple from below
        touchback_down = breakout_down and (candle_3['high'] >= purple * 0.999)

        # Breakout up: candle crosses above purple line
        breakout_up = (candle_1['close'] < purple and candle_2['close'] > purple)
        # Touchback: price returns to touch purple from above
        touchback_up = breakout_up and (candle_3['low'] <= purple * 1.001)

        return (breakout_down, touchback_down), (breakout_up, touchback_up)

    def check_pain_sell_conditions(self, symbol, data):
        """Check all conditions for PAIN SELL signal"""
        conditions = {
            'symbol': symbol,
            'type': 'PAIN_SELL',
            'met': False,
            'reasons': []
        }

        # D1: Downward wick
        d1_bias, wick_filled = self.analyze_d1_wick(data['D1']['bars'])
        if d1_bias != 'SELL':
            conditions['reasons'].append('D1: No downward wick')
            return conditions
        if wick_filled:
            conditions['reasons'].append('D1: 50% wick already filled - stop trading')
            return conditions
        conditions['reasons'].append('D1: Downward wick ✓')

        # H4: 50% Fibonacci
        if not self.check_fibonacci_retracement(data.get('H4'), data.get('M15')):
            conditions['reasons'].append('H4: No 50% Fib coverage')
            return conditions
        conditions['reasons'].append('H4: 50% Fib ✓')

        # H1: Price below red Snake
        if data['H1']['price_vs_snake'] != 'below' or data['H1']['snake_color'] != 'red':
            conditions['reasons'].append('H1: Price not below red Snake')
            return conditions
        conditions['reasons'].append('H1: Price below red Snake ✓')

        # M30: Snake RED
        if data['M30']['snake_color'] != 'red':
            conditions['reasons'].append('M30: Snake not RED')
            return conditions
        conditions['reasons'].append('M30: Snake RED ✓')

        # M15: Snake RED
        if data['M15']['snake_color'] != 'red':
            conditions['reasons'].append('M15: Snake not RED')
            return conditions
        conditions['reasons'].append('M15: Snake RED ✓')

        # M1: Price below red Snake + Purple Line break + touchback
        if data['M1']['price_vs_snake'] != 'below' or data['M1']['snake_color'] != 'red':
            conditions['reasons'].append('M1: Price not below red Snake')
            return conditions

        (breakout_down, touchback_down), _ = self.detect_purple_line_breakout(data['M1'], data['M5'])
        if not (breakout_down and touchback_down):
            conditions['reasons'].append('M1: No Purple Line break + touchback')
            return conditions

        conditions['reasons'].append('M1: All conditions met ✓')
        conditions['met'] = True
        conditions['price'] = data['M1']['close']

        return conditions

    def check_gain_sell_conditions(self, symbol, data):
        """Check all conditions for GAIN SELL signal"""
        conditions = {
            'symbol': symbol,
            'type': 'GAIN_SELL',
            'met': False,
            'reasons': []
        }

        # D1: Downward wick
        d1_bias, wick_filled = self.analyze_d1_wick(data['D1']['bars'])
        if d1_bias != 'SELL':
            conditions['reasons'].append('D1: No downward wick')
            return conditions
        if wick_filled:
            conditions['reasons'].append('D1: 50% wick already filled - stop trading')
            return conditions
        conditions['reasons'].append('D1: Downward wick ✓')

        # M30: Complete Snake break + RED
        if data['M30']['snake_color'] != 'red':
            conditions['reasons'].append('M30: Snake not RED')
            return conditions
        conditions['reasons'].append('M30: Snake RED ✓')

        # M5: Purple Line touch after retreat
        if data['M5']['price_vs_purple'] != 'below':
            conditions['reasons'].append('M5: Price not touching Purple Line')
            return conditions
        conditions['reasons'].append('M5: Purple Line touched ✓')

        # M1: Aligned with M5
        if data['M1']['price_vs_purple'] != 'below' and data['M1']['price_vs_snake'] != 'below':
            conditions['reasons'].append('M1: Not aligned with M5')
            return conditions

        conditions['reasons'].append('M1: Aligned with M5 ✓')
        conditions['met'] = True
        conditions['price'] = data['M1']['close']

        return conditions

    def check_pain_buy_conditions(self, symbol, data):
        """Check all conditions for PAIN BUY signal"""
        conditions = {
            'symbol': symbol,
            'type': 'PAIN_BUY',
            'met': False,
            'reasons': []
        }

        # D1: Upward wick
        d1_bias, wick_filled = self.analyze_d1_wick(data['D1']['bars'])
        if d1_bias != 'BUY':
            conditions['reasons'].append('D1: No upward wick')
            return conditions
        if wick_filled:
            conditions['reasons'].append('D1: 50% wick already filled - stop trading')
            return conditions
        conditions['reasons'].append('D1: Upward wick ✓')

        # M30: Complete Snake break + GREEN
        if data['M30']['snake_color'] != 'green':
            conditions['reasons'].append('M30: Snake not GREEN')
            return conditions
        conditions['reasons'].append('M30: Snake GREEN ✓')

        # M5: Purple Line touch after retreat
        if data['M5']['price_vs_purple'] != 'above':
            conditions['reasons'].append('M5: Price not touching Purple Line')
            return conditions
        conditions['reasons'].append('M5: Purple Line touched ✓')

        # M1: Aligned with M5
        if data['M1']['price_vs_purple'] != 'above' and data['M1']['price_vs_snake'] != 'above':
            conditions['reasons'].append('M1: Not aligned with M5')
            return conditions

        conditions['reasons'].append('M1: Aligned with M5 ✓')
        conditions['met'] = True
        conditions['price'] = data['M1']['close']

        return conditions

    def check_gain_buy_conditions(self, symbol, data):
        """Check all conditions for GAIN BUY signal"""
        conditions = {
            'symbol': symbol,
            'type': 'GAIN_BUY',
            'met': False,
            'reasons': []
        }

        # D1: Upward wick
        d1_bias, wick_filled = self.analyze_d1_wick(data['D1']['bars'])
        if d1_bias != 'BUY':
            conditions['reasons'].append('D1: No upward wick')
            return conditions
        if wick_filled:
            conditions['reasons'].append('D1: 50% wick already filled - stop trading')
            return conditions
        conditions['reasons'].append('D1: Upward wick ✓')

        # H4: 50% Fibonacci
        if not self.check_fibonacci_retracement(data.get('H4'), data.get('M15')):
            conditions['reasons'].append('H4: No 50% Fib coverage')
            return conditions
        conditions['reasons'].append('H4: 50% Fib ✓')

        # H1: Price above green Snake
        if data['H1']['price_vs_snake'] != 'above' or data['H1']['snake_color'] != 'green':
            conditions['reasons'].append('H1: Price not above green Snake')
            return conditions
        conditions['reasons'].append('H1: Price above green Snake ✓')

        # M30: Snake GREEN
        if data['M30']['snake_color'] != 'green':
            conditions['reasons'].append('M30: Snake not GREEN')
            return conditions
        conditions['reasons'].append('M30: Snake GREEN ✓')

        # M15: Snake GREEN
        if data['M15']['snake_color'] != 'green':
            conditions['reasons'].append('M15: Snake not GREEN')
            return conditions
        conditions['reasons'].append('M15: Snake GREEN ✓')

        # M1: Price above green Snake + Purple Line break + touchback
        if data['M1']['price_vs_snake'] != 'above' or data['M1']['snake_color'] != 'green':
            conditions['reasons'].append('M1: Price not above green Snake')
            return conditions

        _, (breakout_up, touchback_up) = self.detect_purple_line_breakout(data['M1'], data['M5'])
        if not (breakout_up and touchback_up):
            conditions['reasons'].append('M1: No Purple Line break + touchback')
            return conditions

        conditions['reasons'].append('M1: All conditions met ✓')
        conditions['met'] = True
        conditions['price'] = data['M1']['close']

        return conditions

    def get_analysis_data(self, symbol):
        """
        Get detailed analysis data for a symbol, even if conditions are not fully met.
        This is used for analysis recording to track all potential moments.

        Returns:
            Dictionary with comprehensive analysis information
        """
        # Get multi-timeframe data
        data = self.get_multi_timeframe_data(symbol)

        if not data or 'M1' not in data:
            return None

        # Get current tick for bid/ask
        tick = self.connector.get_current_tick(symbol)
        if not tick:
            return None

        # Determine symbol type
        is_pain = 'Pain' in symbol
        is_gain = 'Gain' in symbol

        # Build snake colors dict
        snake_colors = {
            'D1': data['D1']['snake_color'],
            'H4': data['H4']['snake_color'],
            'H1': data['H1']['snake_color'],
            'M30': data['M30']['snake_color'],
            'M15': data['M15']['snake_color'],
            'M5': data['M5']['snake_color'],
            'M1': data['M1']['snake_color'],
        }

        # Build purple line positions (relative to price)
        purple_positions = {
            'D1': data['D1']['price_vs_purple'],
            'H4': data['H4']['price_vs_purple'],
            'H1': data['H1']['price_vs_purple'],
            'M30': data['M30']['price_vs_purple'],
            'M15': data['M15']['price_vs_purple'],
            'M5': data['M5']['price_vs_purple'],
            'M1': data['M1']['price_vs_purple'],
        }

        # Analyze conditions
        d1_wick_result = self.analyze_d1_wick(data['D1']['bars']) if 'D1' in data else (None, False)
        d1_wick = d1_wick_result[0] if d1_wick_result[0] else 'NEUTRAL'
        h4_fib = self.check_fibonacci_retracement(data.get('H4'), data.get('M15'))

        # Detect purple line breakout
        (breakout_down, touchback_down), (breakout_up, touchback_up) = self.detect_purple_line_breakout(data['M1'], data['M5'])

        purple_breakout = 'NONE'
        if breakout_up and touchback_up:
            purple_breakout = 'UP+TOUCHBACK'
        elif breakout_down and touchback_down:
            purple_breakout = 'DOWN+TOUCHBACK'
        elif breakout_up:
            purple_breakout = 'UP'
        elif breakout_down:
            purple_breakout = 'DOWN'

        # Check which signal types could be close
        could_pain_sell = False
        could_gain_sell = False
        could_pain_buy = False
        could_gain_buy = False
        missing_conditions = []

        if is_pain:
            # Check PAIN SELL potential
            pain_sell_result = self.check_pain_sell_conditions(symbol, data)
            could_pain_sell = pain_sell_result['met']
            if not could_pain_sell:
                # Extract missing conditions from reasons
                for reason in pain_sell_result['reasons']:
                    if '✓' not in reason:
                        missing_conditions.append(f"PAIN_SELL: {reason}")

            # Check PAIN BUY potential
            pain_buy_result = self.check_pain_buy_conditions(symbol, data)
            could_pain_buy = pain_buy_result['met']
            if not could_pain_buy:
                for reason in pain_buy_result['reasons']:
                    if '✓' not in reason:
                        missing_conditions.append(f"PAIN_BUY: {reason}")

        if is_gain:
            # Check GAIN SELL potential
            gain_sell_result = self.check_gain_sell_conditions(symbol, data)
            could_gain_sell = gain_sell_result['met']
            if not could_gain_sell:
                for reason in gain_sell_result['reasons']:
                    if '✓' not in reason:
                        missing_conditions.append(f"GAIN_SELL: {reason}")

            # Check GAIN BUY potential
            gain_buy_result = self.check_gain_buy_conditions(symbol, data)
            could_gain_buy = gain_buy_result['met']
            if not could_gain_buy:
                for reason in gain_buy_result['reasons']:
                    if '✓' not in reason:
                        missing_conditions.append(f"GAIN_BUY: {reason}")

        # Build notes
        notes = []
        if len(missing_conditions) == 0:
            notes.append("ALL CONDITIONS MET!")

        # Count how many snakes are green/red
        green_count = sum(1 for color in snake_colors.values() if color == 'green')
        red_count = sum(1 for color in snake_colors.values() if color == 'red')
        notes.append(f"Snakes: {green_count} green, {red_count} red")

        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'price': data['M1']['close'],
            'bid': tick['bid'],
            'ask': tick['ask'],
            'spread': tick['spread'],
            'snake_colors': snake_colors,
            'purple_positions': purple_positions,
            'd1_bias': d1_wick,
            'h4_fib_met': h4_fib,
            'purple_breakout': purple_breakout,
            'purple_touchback': (breakout_up and touchback_up) or (breakout_down and touchback_down),
            'could_pain_sell': could_pain_sell,
            'could_gain_sell': could_gain_sell,
            'could_pain_buy': could_pain_buy,
            'could_gain_buy': could_gain_buy,
            'missing_conditions': missing_conditions,
            'notes': ' | '.join(notes)
        }

    def detect_signals(self, symbol):
        """Detect all possible signals for a symbol"""
        signals = []

        # Get multi-timeframe data
        data = self.get_multi_timeframe_data(symbol)

        if not data or 'M1' not in data:
            return signals

        # Determine symbol type
        is_pain = 'Pain' in symbol
        is_gain = 'Gain' in symbol

        # Check appropriate conditions
        if is_pain:
            sell_signal = self.check_pain_sell_conditions(symbol, data)
            if sell_signal['met']:
                signals.append(sell_signal)

            buy_signal = self.check_pain_buy_conditions(symbol, data)
            if buy_signal['met']:
                signals.append(buy_signal)

        if is_gain:
            sell_signal = self.check_gain_sell_conditions(symbol, data)
            if sell_signal['met']:
                signals.append(sell_signal)

            buy_signal = self.check_gain_buy_conditions(symbol, data)
            if buy_signal['met']:
                signals.append(buy_signal)

        # Add timestamp and multi-timeframe snapshot
        for signal in signals:
            signal['timestamp'] = datetime.now().isoformat()
            signal['timeframe_data'] = {
                'D1': data['D1']['snake_color'],
                'H4': data['H4']['snake_color'],
                'H1': data['H1']['snake_color'],
                'M30': data['M30']['snake_color'],
                'M15': data['M15']['snake_color'],
                'M5': data['M5']['snake_color'],
                'M1': data['M1']['snake_color'],
            }

        return signals
