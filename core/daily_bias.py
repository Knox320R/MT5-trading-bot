"""
Daily Bias Service
Computes daily trading bias (BUY/SELL/NEUTRAL) based on yesterday's daily candle.
Uses wick and body analysis with exact rules from specification.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime
from .timezone_handler import TimezoneHandler


class DailyBiasService:
    """
    Computes and caches daily trading bias.
    Evaluates once at 16:00 COL and caches until next 16:00.
    """

    def __init__(self, timezone_handler: TimezoneHandler, epsilon: float = 0.05):
        """
        Initialize daily bias service.

        Args:
            timezone_handler: Timezone handler for daily boundary
            epsilon: Tie-breaker ratio for upper vs lower wick comparison
        """
        self.tz_handler = timezone_handler
        self.epsilon = epsilon
        self.bias_cache = {}  # symbol -> (bias, level50, trading_day)

    def compute_bias(self, yesterday_candle: Dict) -> Tuple[str, Optional[float]]:
        """
        Compute trading bias from yesterday's daily candle.

        Args:
            yesterday_candle: OHLC dict with 'open', 'high', 'low', 'close'

        Returns:
            Tuple of (bias, level50)
            - bias: 'BUY', 'SELL', or 'NEUTRAL'
            - level50: For SELL days, the 50% wick stop level. None otherwise.
        """
        o = yesterday_candle['open']
        h = yesterday_candle['high']
        l = yesterday_candle['low']
        c = yesterday_candle['close']

        # Calculate components
        range_val = h - l
        body = abs(c - o)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        # Determine longest wick
        longest_wick = max(upper_wick, lower_wick)

        # Small body rule: longest wick must be larger than body
        is_small_body = longest_wick > body

        if not is_small_body:
            return 'NEUTRAL', None

        # Determine bias based on which wick is longer
        # Use epsilon for tie-breaking
        if lower_wick > upper_wick * (1 + self.epsilon):
            # SELL day
            bias = 'SELL'
            # Compute 50% wick stop level
            base_low = min(o, c)
            level50 = base_low - 0.5 * lower_wick
        elif upper_wick > lower_wick * (1 + self.epsilon):
            # BUY day
            bias = 'BUY'
            level50 = None  # BUY days don't use wick stop
        else:
            # Too close - neutral
            bias = 'NEUTRAL'
            level50 = None

        return bias, level50

    def get_bias(self, symbol: str, d1_bars: list, force_refresh: bool = False) -> Dict:
        """
        Get current trading bias for symbol.

        Caches bias per symbol until next daily boundary.

        Args:
            symbol: Trading symbol
            d1_bars: List of D1 bars (at least 2 needed)
            force_refresh: Force recomputation even if cached

        Returns:
            Dictionary with:
            - bias: 'BUY', 'SELL', or 'NEUTRAL'
            - level50: Stop level for SELL days (or None)
            - yesterday: Yesterday's candle data
            - trading_day: Current trading day
        """
        current_day = self.tz_handler.get_current_trading_day()

        # Check cache
        if not force_refresh and symbol in self.bias_cache:
            cached_bias, cached_level50, cached_day, yesterday = self.bias_cache[symbol]
            if cached_day == current_day:
                return {
                    'bias': cached_bias,
                    'level50': cached_level50,
                    'yesterday': yesterday,
                    'trading_day': current_day
                }

        # Need to compute
        if not d1_bars or len(d1_bars) < 2:
            return {
                'bias': 'NEUTRAL',
                'level50': None,
                'yesterday': None,
                'trading_day': current_day,
                'error': 'Insufficient D1 bars'
            }

        # Get yesterday's candle (second to last)
        yesterday = d1_bars[-2]

        # Compute bias
        bias, level50 = self.compute_bias(yesterday)

        # Cache result
        self.bias_cache[symbol] = (bias, level50, current_day, yesterday)

        return {
            'bias': bias,
            'level50': level50,
            'yesterday': yesterday,
            'trading_day': current_day
        }

    def is_day_stop_triggered(self, symbol: str, current_low: float) -> bool:
        """
        Check if PAIN SELL 50% wick day-stop is triggered.

        Only applies to SELL days.

        Args:
            symbol: Trading symbol
            current_low: Today's current low price

        Returns:
            True if day-stop triggered (stop all new trades)
        """
        if symbol not in self.bias_cache:
            return False

        bias, level50, _, _ = self.bias_cache[symbol]

        if bias != 'SELL' or level50 is None:
            return False

        # Check if today's low has reached or breached the 50% wick level
        return current_low <= level50

    def clear_cache(self, symbol: Optional[str] = None):
        """
        Clear bias cache.

        Args:
            symbol: Symbol to clear, or None to clear all
        """
        if symbol:
            self.bias_cache.pop(symbol, None)
        else:
            self.bias_cache.clear()

    def get_bias_summary(self, symbol: str) -> str:
        """
        Get human-readable summary of current bias.

        Args:
            symbol: Trading symbol

        Returns:
            Summary string
        """
        if symbol not in self.bias_cache:
            return "No bias computed yet"

        bias, level50, day, yesterday = self.bias_cache[symbol]

        if bias == 'NEUTRAL':
            return f"NEUTRAL day ({day}) - No trading"
        elif bias == 'SELL':
            return f"SELL day ({day}) - Stop level: {level50:.5f}"
        else:  # BUY
            return f"BUY day ({day})"
