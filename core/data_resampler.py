"""
Data Resampler Module
Resamples M1 candles to higher timeframes (M5, M15, M30, H1, H4, D1)
Uses CLOSED candles only - never partial bars
"""

from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional
import MetaTrader5 as mt5


class DataResampler:
    """
    Resamples M1 candles to higher timeframes.
    All operations use closed candles only.
    Timezone-aware for America/Bogota daily boundary at 16:00.
    """

    # Timeframe definitions in minutes
    TIMEFRAMES = {
        'M1': 1,
        'M5': 5,
        'M15': 15,
        'M30': 30,
        'H1': 60,
        'H4': 240,
        'D1': 1440  # 24 hours
    }

    def __init__(self, timezone='America/Bogota'):
        """
        Initialize resampler with timezone.

        Args:
            timezone: IANA timezone name for daily boundary
        """
        self.timezone = pytz.timezone(timezone)

    def resample_m1_to_timeframe(self, m1_bars: List[Dict], target_tf: str) -> List[Dict]:
        """
        Resample M1 bars to target timeframe.

        Args:
            m1_bars: List of M1 OHLC dictionaries with 'time', 'open', 'high', 'low', 'close', 'volume'
            target_tf: Target timeframe ('M5', 'M15', 'M30', 'H1', 'H4', 'D1')

        Returns:
            List of resampled OHLC bars
        """
        if not m1_bars or target_tf not in self.TIMEFRAMES:
            return []

        if target_tf == 'M1':
            return m1_bars

        tf_minutes = self.TIMEFRAMES[target_tf]
        resampled = []
        current_bar = None

        for m1 in m1_bars:
            # Get bar timestamp
            if isinstance(m1['time'], str):
                bar_time = datetime.fromisoformat(m1['time'].replace('Z', '+00:00'))
            elif isinstance(m1['time'], datetime):
                bar_time = m1['time']
            else:
                # Unix timestamp
                bar_time = datetime.fromtimestamp(m1['time'])

            # Make timezone-aware if not already
            if bar_time.tzinfo is None:
                bar_time = self.timezone.localize(bar_time)
            else:
                bar_time = bar_time.astimezone(self.timezone)

            # Determine which resampled bar this M1 belongs to
            bar_key = self._get_bar_key(bar_time, tf_minutes)

            if current_bar is None or current_bar['_key'] != bar_key:
                # Start new resampled bar
                if current_bar is not None:
                    resampled.append(self._finalize_bar(current_bar))

                current_bar = {
                    '_key': bar_key,
                    'time': bar_time,
                    'open': m1['open'],
                    'high': m1['high'],
                    'low': m1['low'],
                    'close': m1['close'],
                    'volume': m1.get('volume', 0)
                }
            else:
                # Update existing resampled bar
                current_bar['high'] = max(current_bar['high'], m1['high'])
                current_bar['low'] = min(current_bar['low'], m1['low'])
                current_bar['close'] = m1['close']  # Last close
                current_bar['volume'] += m1.get('volume', 0)
                current_bar['time'] = bar_time  # Update to latest time

        # Finalize last bar
        if current_bar is not None:
            resampled.append(self._finalize_bar(current_bar))

        return resampled

    def _get_bar_key(self, dt: datetime, tf_minutes: int) -> str:
        """
        Get unique key for a bar based on timeframe.

        For D1, uses 16:00 boundary in America/Bogota.
        For intraday, uses standard rounding.
        """
        if tf_minutes == 1440:  # D1
            # Daily bar changes at 16:00 COL
            # If before 16:00, belongs to previous day
            if dt.hour < 16:
                day = dt.date() - timedelta(days=1)
            else:
                day = dt.date()
            return f"D1_{day}"
        else:
            # Intraday: round down to timeframe boundary
            total_minutes = dt.hour * 60 + dt.minute
            bar_index = total_minutes // tf_minutes
            bar_start_minutes = bar_index * tf_minutes
            bar_hour = bar_start_minutes // 60
            bar_minute = bar_start_minutes % 60

            return f"{dt.date()}_{bar_hour:02d}:{bar_minute:02d}"

    def _finalize_bar(self, bar: Dict) -> Dict:
        """Remove internal keys and return clean bar"""
        return {
            'time': bar['time'],
            'open': bar['open'],
            'high': bar['high'],
            'low': bar['low'],
            'close': bar['close'],
            'volume': bar['volume']
        }

    def resample_all_timeframes(self, m1_bars: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Resample M1 bars to all standard timeframes.

        Args:
            m1_bars: List of M1 OHLC bars

        Returns:
            Dictionary mapping timeframe name to list of bars
        """
        result = {'M1': m1_bars}

        for tf in ['M5', 'M15', 'M30', 'H1', 'H4', 'D1']:
            result[tf] = self.resample_m1_to_timeframe(m1_bars, tf)

        return result

    def get_latest_closed_bar(self, bars: List[Dict]) -> Optional[Dict]:
        """
        Get the latest CLOSED bar.
        Excludes the last bar if it's not yet closed.

        Args:
            bars: List of bars

        Returns:
            Latest closed bar or None
        """
        if not bars:
            return None

        # For safety, always return second-to-last bar
        # (last bar might still be forming)
        if len(bars) >= 2:
            return bars[-2]
        elif len(bars) == 1:
            # Only one bar - assume it's closed if old enough
            bar_time = bars[0]['time']
            if isinstance(bar_time, str):
                bar_time = datetime.fromisoformat(bar_time.replace('Z', '+00:00'))

            now = datetime.now(self.timezone)
            age = (now - bar_time).total_seconds()

            # If bar is more than 2 minutes old, consider it closed
            if age > 120:
                return bars[0]

        return None

    def is_new_bar_formed(self, timeframe: str, last_check_time: datetime, current_time: datetime) -> bool:
        """
        Check if a new bar has formed in the given timeframe.

        Args:
            timeframe: Timeframe to check ('M1', 'M5', etc.)
            last_check_time: Last time we checked
            current_time: Current time

        Returns:
            True if a new bar has formed
        """
        if timeframe not in self.TIMEFRAMES:
            return False

        tf_minutes = self.TIMEFRAMES[timeframe]

        # For D1, check if we crossed 16:00 boundary
        if tf_minutes == 1440:
            last_day_key = self._get_bar_key(last_check_time, tf_minutes)
            current_day_key = self._get_bar_key(current_time, tf_minutes)
            return last_day_key != current_day_key
        else:
            # For intraday, check if bar key changed
            last_key = self._get_bar_key(last_check_time, tf_minutes)
            current_key = self._get_bar_key(current_time, tf_minutes)
            return last_key != current_key
