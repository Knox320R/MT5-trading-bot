"""
Fibonacci Structure Checker
Implements structure validation for GAIN bots using M15 swings and H4 confirmation.
"""

from typing import Dict, List, Optional, Tuple


class FibonacciChecker:
    """
    Checks Fibonacci structure for GAIN bot entries.

    GAIN BUY:
    - On today's M15: swing low → high
    - Fib50 = low + 0.5 * (high - low)
    - On H4: largest-body candle among last N must contain Fib50 in its range

    GAIN SELL:
    - On today's M15: swing high → low
    - Fib50 = low + 0.5 * (high - low)
    - On H4: largest-body candle among last N must contain Fib50 in its range
    """

    def __init__(self, h4_candidates: int = 3):
        """
        Initialize Fibonacci checker.

        Args:
            h4_candidates: Number of recent H4 candles to check for largest body
        """
        self.h4_candidates = h4_candidates

    def find_m15_swing_buy(self, m15_bars: List[Dict]) -> Optional[Tuple[float, float, float]]:
        """
        Find M15 swing for BUY setup (low → high).

        Uses today's M15 bars only.

        Args:
            m15_bars: List of M15 bars for today

        Returns:
            Tuple of (swing_low, swing_high, fib50) or None
        """
        if not m15_bars or len(m15_bars) < 2:
            return None

        # Find today's swing low and high
        # Simple approach: use lowest low and highest high from today's M15 bars
        lows = [bar['low'] for bar in m15_bars]
        highs = [bar['high'] for bar in m15_bars]

        swing_low = min(lows)
        swing_high = max(highs)

        # Calculate 50% Fibonacci level
        fib50 = swing_low + 0.5 * (swing_high - swing_low)

        return swing_low, swing_high, fib50

    def find_m15_swing_sell(self, m15_bars: List[Dict]) -> Optional[Tuple[float, float, float]]:
        """
        Find M15 swing for SELL setup (high → low).

        Uses today's M15 bars only.

        Args:
            m15_bars: List of M15 bars for today

        Returns:
            Tuple of (swing_high, swing_low, fib50) or None
        """
        if not m15_bars or len(m15_bars) < 2:
            return None

        # Find today's swing high and low
        lows = [bar['low'] for bar in m15_bars]
        highs = [bar['high'] for bar in m15_bars]

        swing_high = max(highs)
        swing_low = min(lows)

        # Calculate 50% Fibonacci level
        fib50 = swing_low + 0.5 * (swing_high - swing_low)

        return swing_high, swing_low, fib50

    def find_largest_body_h4(self, h4_bars: List[Dict]) -> Optional[Dict]:
        """
        Find the largest-body H4 candle among last N closed candles.

        Args:
            h4_bars: List of H4 bars

        Returns:
            Largest body candle dict or None
        """
        if not h4_bars:
            return None

        # Get last N closed candles (exclude last one as it might be forming)
        candidates = h4_bars[-self.h4_candidates - 1:-1] if len(h4_bars) > self.h4_candidates else h4_bars[:-1]

        if not candidates:
            # If not enough closed bars, use what we have
            candidates = h4_bars[-self.h4_candidates:] if len(h4_bars) >= self.h4_candidates else h4_bars

        if not candidates:
            return None

        # Find largest body
        largest = None
        max_body = 0

        for bar in candidates:
            body = abs(bar['close'] - bar['open'])
            if body > max_body:
                max_body = body
                largest = bar

        return largest

    def check_h4_covers_fib50(self, fib50: float, h4_bar: Dict) -> bool:
        """
        Check if H4 candle range includes the Fib50 level.

        Args:
            fib50: Fibonacci 50% level
            h4_bar: H4 candle

        Returns:
            True if fib50 lies within [low, high] of H4 candle
        """
        if not h4_bar:
            return False

        return h4_bar['low'] <= fib50 <= h4_bar['high']

    def check_gain_buy_structure(self, m15_bars: List[Dict], h4_bars: List[Dict]) -> Dict:
        """
        Check GAIN BUY structure requirements.

        Args:
            m15_bars: Today's M15 bars
            h4_bars: H4 bars

        Returns:
            Dictionary with:
            - valid: True if structure check passes
            - swing_low: Swing low value
            - swing_high: Swing high value
            - fib50: Fibonacci 50% level
            - h4_candle: Largest body H4 candle
            - h4_covers: True if H4 covers Fib50
            - reason: Explanation
        """
        # Find M15 swing
        swing = self.find_m15_swing_buy(m15_bars)
        if not swing:
            return {
                'valid': False,
                'reason': 'Insufficient M15 data for swing detection',
                'swing_low': None,
                'swing_high': None,
                'fib50': None,
                'h4_candle': None,
                'h4_covers': False
            }

        swing_low, swing_high, fib50 = swing

        # Find largest body H4
        h4_candle = self.find_largest_body_h4(h4_bars)
        if not h4_candle:
            return {
                'valid': False,
                'reason': 'No H4 candle found',
                'swing_low': swing_low,
                'swing_high': swing_high,
                'fib50': fib50,
                'h4_candle': None,
                'h4_covers': False
            }

        # Check if H4 covers Fib50
        h4_covers = self.check_h4_covers_fib50(fib50, h4_candle)

        return {
            'valid': h4_covers,
            'reason': 'H4 covers Fib50' if h4_covers else 'H4 does not cover Fib50',
            'swing_low': swing_low,
            'swing_high': swing_high,
            'fib50': fib50,
            'h4_candle': h4_candle,
            'h4_covers': h4_covers
        }

    def check_gain_sell_structure(self, m15_bars: List[Dict], h4_bars: List[Dict]) -> Dict:
        """
        Check GAIN SELL structure requirements.

        Args:
            m15_bars: Today's M15 bars
            h4_bars: H4 bars

        Returns:
            Dictionary with:
            - valid: True if structure check passes
            - swing_high: Swing high value
            - swing_low: Swing low value
            - fib50: Fibonacci 50% level
            - h4_candle: Largest body H4 candle
            - h4_covers: True if H4 covers Fib50
            - reason: Explanation
        """
        # Find M15 swing
        swing = self.find_m15_swing_sell(m15_bars)
        if not swing:
            return {
                'valid': False,
                'reason': 'Insufficient M15 data for swing detection',
                'swing_high': None,
                'swing_low': None,
                'fib50': None,
                'h4_candle': None,
                'h4_covers': False
            }

        swing_high, swing_low, fib50 = swing

        # Find largest body H4
        h4_candle = self.find_largest_body_h4(h4_bars)
        if not h4_candle:
            return {
                'valid': False,
                'reason': 'No H4 candle found',
                'swing_high': swing_high,
                'swing_low': swing_low,
                'fib50': fib50,
                'h4_candle': None,
                'h4_covers': False
            }

        # Check if H4 covers Fib50
        h4_covers = self.check_h4_covers_fib50(fib50, h4_candle)

        return {
            'valid': h4_covers,
            'reason': 'H4 covers Fib50' if h4_covers else 'H4 does not cover Fib50',
            'swing_high': swing_high,
            'swing_low': swing_low,
            'fib50': fib50,
            'h4_candle': h4_candle,
            'h4_covers': h4_covers
        }
