"""
Indicators Module
Calculates technical indicators (EMA) with per-timeframe caching.
Uses closed candles only.

Exponential Moving Average (EMA) Implementation
==============================================

This module implements the standard EMA formula as defined in EMA.txt:

Formula:
    EMA_today = (Value_today * (Smoothing / (1 + Days))) +
                EMA_yesterday * (1 - (Smoothing / (1 + Days)))

    where Smoothing = 2 (standard)

Key Properties of EMA:
- Gives MORE WEIGHT to recent prices (unlike SMA which weights all prices equally)
- Responds MORE QUICKLY to price changes than SMA
- More sensitive to current market trends
- Used for both short-term (8, 10, 12, 20, 26 day) and long-term (50, 100, 200 day) analysis

Trading System Usage:
---------------------
1. Snake Indicator (EMA 100):
   - Long-term trend indicator
   - Green zone (price > EMA100) = Uptrend
   - Red zone (price < EMA100) = Downtrend
   - Used across H1, M30, M15 timeframes for trend alignment

2. Purple Line (EMA 10):
   - Short-term trend indicator
   - Used on M1 timeframe for entry signals
   - Cross-then-touch pattern triggers trades

References:
- EMA.txt in overview/ folder
- Standard Investopedia EMA definition
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
        Calculate Exponential Moving Average using the standard formula.

        Formula (from EMA.txt):
        EMA_today = (Value_today * (Smoothing / (1 + Days))) + EMA_yesterday * (1 - (Smoothing / (1 + Days)))

        where:
        - Smoothing = 2 (standard smoothing factor)
        - Days = period (number of observations)
        - Multiplier k = 2 / (period + 1)

        Process:
        1. Calculate SMA for the first 'period' prices
        2. Use that SMA as EMA_yesterday for the next calculation
        3. For each subsequent price, apply: EMA = Close * k + EMA_previous * (1 - k)

        Example for 20-period EMA:
        - Day 1-19: Not enough data (filled with NaN)
        - Day 20: SMA of days 1-20 = first EMA value
        - Day 21+: EMA formula applied using previous EMA

        Args:
            prices: List of close prices
            period: EMA period (e.g., 10, 20, 50, 100, 200)

        Returns:
            List of EMA values (same length as prices, initial values are NaN)
        """
        if not prices or len(prices) < period:
            return []

        prices_array = np.array(prices, dtype=float)
        ema = np.zeros(len(prices))

        # Multiplier: k = Smoothing / (1 + Days) where Smoothing = 2
        # This gives more recent observations more weight
        # Example: 20-period EMA has k = 2/(20+1) = 0.0952 (9.52% weight on new data)
        k = 2.0 / (period + 1)

        # Step 1: Initialize with SMA of first 'period' prices
        # This is the EMA value at index (period - 1)
        sma = np.mean(prices_array[:period])
        ema[period - 1] = sma

        # Step 2: Calculate EMA for remaining prices using the formula:
        # EMA_today = Close_today * k + EMA_yesterday * (1 - k)
        for i in range(period, len(prices)):
            ema[i] = prices_array[i] * k + ema[i - 1] * (1 - k)

        # Step 3: Fill initial values (before we have enough data) with NaN
        # These represent periods where we don't have enough historical data
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
