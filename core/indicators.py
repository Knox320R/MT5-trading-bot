"""
Indicators Module
Calculates technical indicators (EMA) with per-timeframe caching.
Uses closed candles only.
"""

from typing import List, Dict, Optional
import numpy as np


class IndicatorCalculator:
    """
    Calculates technical indicators with caching.
    All calculations use close prices from closed candles only.
    """

    def __init__(self, snake_period: int = 100, purple_period: int = 10):
        """
        Initialize indicator calculator.

        Args:
            snake_period: EMA period for Snake indicator
            purple_period: EMA period for Purple Line indicator
        """
        self.snake_period = snake_period
        self.purple_period = purple_period
        self.ema_cache = {}  # (symbol, timeframe, period) -> EMA array

    def set_periods(self, snake_period: int, purple_period: int):
        """
        Update indicator periods (user-adjustable).

        Args:
            snake_period: New Snake EMA period
            purple_period: New Purple Line EMA period
        """
        if snake_period != self.snake_period or purple_period != self.purple_period:
            self.snake_period = snake_period
            self.purple_period = purple_period
            # Clear cache since periods changed
            self.ema_cache.clear()

    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """
        Calculate Exponential Moving Average.

        Args:
            prices: List of close prices
            period: EMA period

        Returns:
            List of EMA values (same length as prices)
        """
        if not prices or len(prices) < period:
            return []

        prices_array = np.array(prices, dtype=float)
        ema = np.zeros(len(prices))

        # Multiplier
        k = 2.0 / (period + 1)

        # Initialize with SMA
        ema[period - 1] = np.mean(prices_array[:period])

        # Calculate EMA
        for i in range(period, len(prices)):
            ema[i] = prices_array[i] * k + ema[i - 1] * (1 - k)

        # Fill initial values with None/NaN
        ema[:period - 1] = np.nan

        return ema.tolist()

    def get_latest_ema(self, prices: List[float], period: int) -> Optional[float]:
        """
        Get the latest EMA value.

        Args:
            prices: List of close prices
            period: EMA period

        Returns:
            Latest EMA value or None if insufficient data
        """
        ema_values = self.calculate_ema(prices, period)
        if not ema_values:
            return None

        # Return last non-NaN value
        for val in reversed(ema_values):
            if not np.isnan(val):
                return val

        return None

    def get_indicators_for_bars(self, bars: List[Dict], cached_key: Optional[str] = None) -> Dict:
        """
        Calculate Snake and Purple Line for a list of bars.

        Args:
            bars: List of OHLC bars
            cached_key: Optional cache key (symbol, timeframe)

        Returns:
            Dictionary with:
            - snake: List of Snake EMA values
            - purple: List of Purple Line EMA values
            - snake_latest: Latest Snake value
            - purple_latest: Latest Purple value
            - close_latest: Latest close price
            - snake_color: 'green' if close >= snake, 'red' if close < snake
        """
        if not bars:
            return {
                'snake': [],
                'purple': [],
                'snake_latest': None,
                'purple_latest': None,
                'close_latest': None,
                'snake_color': None
            }

        # Extract close prices
        closes = [bar['close'] for bar in bars]

        # Calculate EMAs
        snake_ema = self.calculate_ema(closes, self.snake_period)
        purple_ema = self.calculate_ema(closes, self.purple_period)

        # Get latest values
        snake_latest = self.get_latest_ema(closes, self.snake_period)
        purple_latest = self.get_latest_ema(closes, self.purple_period)
        close_latest = closes[-1] if closes else None

        # Determine snake color
        snake_color = None
        if snake_latest is not None and close_latest is not None:
            snake_color = 'green' if close_latest >= snake_latest else 'red'

        return {
            'snake': snake_ema,
            'purple': purple_ema,
            'snake_latest': snake_latest,
            'purple_latest': purple_latest,
            'close_latest': close_latest,
            'snake_color': snake_color,
            'bars': bars
        }

    def get_snake_color(self, close: float, snake_ema: float, equality_is_not_trend: bool = True) -> str:
        """
        Determine snake color based on close price.

        Args:
            close: Close price
            snake_ema: Snake EMA value
            equality_is_not_trend: If True, close == EMA is NOT considered aligned

        Returns:
            'green', 'red', or 'neutral'
        """
        if equality_is_not_trend:
            if close > snake_ema:
                return 'green'
            elif close < snake_ema:
                return 'red'
            else:
                return 'neutral'
        else:
            return 'green' if close >= snake_ema else 'red'

    def check_price_vs_ema(self, close: float, ema: float) -> str:
        """
        Check price position relative to EMA.

        Args:
            close: Close price
            ema: EMA value

        Returns:
            'above', 'below', or 'at'
        """
        if close > ema:
            return 'above'
        elif close < ema:
            return 'below'
        else:
            return 'at'

    def clear_cache(self):
        """Clear EMA cache"""
        self.ema_cache.clear()
