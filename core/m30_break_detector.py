"""
M30 Break Detector
Detects the "first clean close" above/below Snake on M30 timeframe.
Used by PAIN bots as an additional filter.
"""

from typing import Dict, Optional, List


class M30BreakDetector:
    """
    Tracks M30 Snake breaks for PAIN bot entry filtering.

    PAIN BUY: Requires first clean close ABOVE snake after being at/below it
    PAIN SELL: Requires first clean close BELOW snake after being at/above it
    """

    def __init__(self):
        """Initialize break detector with state tracking"""
        # symbol -> {'last_break_type': 'up'/'down', 'break_bar_index': int, 'previous_state': 'above'/'below'/'at'}
        self.state = {}

    def update(self, symbol: str, m30_bars: List[Dict], snake_values: List[float]):
        """
        Update break state for symbol.

        Args:
            symbol: Trading symbol
            m30_bars: List of M30 bars
            snake_values: List of Snake EMA values (same length as bars)
        """
        if not m30_bars or not snake_values or len(m30_bars) != len(snake_values):
            return

        if symbol not in self.state:
            self.state[symbol] = {
                'last_break_type': None,
                'break_bar_index': -1,
                'previous_state': None
            }

        # Check last few bars for break pattern
        # We need at least 2 bars to detect a break
        if len(m30_bars) < 2:
            return

        # Look at last bar
        last_idx = len(m30_bars) - 1
        last_close = m30_bars[last_idx]['close']
        last_snake = snake_values[last_idx]

        prev_idx = last_idx - 1
        prev_close = m30_bars[prev_idx]['close']
        prev_snake = snake_values[prev_idx]

        # Determine states
        last_state = 'above' if last_close >= last_snake else 'below'
        prev_state = 'above' if prev_close >= prev_snake else 'below'

        # Detect break
        if prev_state != last_state:
            # State changed - this is a break
            if prev_state == 'below' and last_state == 'above':
                # Clean close above (upward break)
                self.state[symbol] = {
                    'last_break_type': 'up',
                    'break_bar_index': last_idx,
                    'previous_state': prev_state
                }
            elif prev_state == 'above' and last_state == 'below':
                # Clean close below (downward break)
                self.state[symbol] = {
                    'last_break_type': 'down',
                    'break_bar_index': last_idx,
                    'previous_state': prev_state
                }

    def check_upward_break(self, symbol: str, m30_bars: List[Dict], snake_values: List[float]) -> bool:
        """
        Check if there's a valid upward break (for PAIN BUY).

        First clean close ABOVE Snake after being at or below it.

        Args:
            symbol: Trading symbol
            m30_bars: List of M30 bars
            snake_values: List of Snake EMA values

        Returns:
            True if upward break condition met
        """
        # Update state first
        self.update(symbol, m30_bars, snake_values)

        if symbol not in self.state:
            return False

        state = self.state[symbol]

        # Check if we have an upward break
        if state['last_break_type'] != 'up':
            return False

        # Verify current price is still above snake
        if not m30_bars or not snake_values:
            return False

        last_close = m30_bars[-1]['close']
        last_snake = snake_values[-1]

        return last_close >= last_snake

    def check_downward_break(self, symbol: str, m30_bars: List[Dict], snake_values: List[float]) -> bool:
        """
        Check if there's a valid downward break (for PAIN SELL).

        First clean close BELOW Snake after being at or above it.

        Args:
            symbol: Trading symbol
            m30_bars: List of M30 bars
            snake_values: List of Snake EMA values

        Returns:
            True if downward break condition met
        """
        # Update state first
        self.update(symbol, m30_bars, snake_values)

        if symbol not in self.state:
            return False

        state = self.state[symbol]

        # Check if we have a downward break
        if state['last_break_type'] != 'down':
            return False

        # Verify current price is still below snake
        if not m30_bars or not snake_values:
            return False

        last_close = m30_bars[-1]['close']
        last_snake = snake_values[-1]

        return last_close < last_snake

    def get_break_status(self, symbol: str) -> Dict:
        """
        Get current break status for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with break state info
        """
        if symbol not in self.state:
            return {
                'has_break': False,
                'break_type': None,
                'break_index': -1
            }

        state = self.state[symbol]
        return {
            'has_break': state['last_break_type'] is not None,
            'break_type': state['last_break_type'],
            'break_index': state['break_bar_index']
        }

    def reset(self, symbol: Optional[str] = None):
        """
        Reset break state.

        Args:
            symbol: Symbol to reset, or None to reset all
        """
        if symbol:
            self.state.pop(symbol, None)
        else:
            self.state.clear()
