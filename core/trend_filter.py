"""
Trend Filter Service
Checks higher-timeframe trend alignment (H1, M30, M15).
All bots require trend alignment matching their direction.
"""

from typing import Dict, List
from .indicators import IndicatorCalculator


class TrendFilterService:
    """
    Checks trend alignment across multiple timeframes.
    Green snake = close >= EMA100
    Red snake = close < EMA100
    """

    def __init__(self, indicator_calc: IndicatorCalculator, equality_is_not_trend: bool = True):
        """
        Initialize trend filter.

        Args:
            indicator_calc: Indicator calculator instance
            equality_is_not_trend: If True, close == EMA100 is NOT considered aligned
        """
        self.indicator_calc = indicator_calc
        self.equality_is_not_trend = equality_is_not_trend
        self.timeframes_to_check = ['H1', 'M30', 'M15']

    def check_alignment(self, tf_data: Dict[str, Dict], required_color: str) -> Dict:
        """
        Check if H1, M30, M15 are all aligned with required color.

        Args:
            tf_data: Dictionary mapping timeframe -> indicator data
                    Each must have 'close_latest' and 'snake_latest'
            required_color: 'green' for BUY bots, 'red' for SELL bots

        Returns:
            Dictionary with:
            - aligned: True if all timeframes match required color
            - details: Dict of timeframe -> (color, aligned)
            - missing: List of misaligned timeframes
        """
        details = {}
        missing = []
        all_aligned = True

        for tf in self.timeframes_to_check:
            if tf not in tf_data:
                details[tf] = ('unknown', False)
                missing.append(f"{tf}: No data")
                all_aligned = False
                continue

            data = tf_data[tf]
            close = data.get('close_latest')
            snake = data.get('snake_latest')

            if close is None or snake is None:
                details[tf] = ('unknown', False)
                missing.append(f"{tf}: Missing indicators")
                all_aligned = False
                continue

            # Determine color
            color = self.indicator_calc.get_snake_color(
                close, snake, self.equality_is_not_trend
            )

            # Check if aligned
            is_aligned = (color == required_color)
            details[tf] = (color, is_aligned)

            if not is_aligned:
                missing.append(f"{tf}: {color} (need {required_color})")
                all_aligned = False

        return {
            'aligned': all_aligned,
            'details': details,
            'missing': missing
        }

    def get_trend_summary(self, tf_data: Dict[str, Dict]) -> str:
        """
        Get human-readable trend summary.

        Args:
            tf_data: Dictionary mapping timeframe -> indicator data

        Returns:
            Summary string like "H1:green M30:green M15:red"
        """
        parts = []
        for tf in self.timeframes_to_check:
            if tf not in tf_data:
                parts.append(f"{tf}:?")
                continue

            data = tf_data[tf]
            close = data.get('close_latest')
            snake = data.get('snake_latest')

            if close is None or snake is None:
                parts.append(f"{tf}:?")
                continue

            color = self.indicator_calc.get_snake_color(
                close, snake, self.equality_is_not_trend
            )
            parts.append(f"{tf}:{color}")

        return " ".join(parts)
