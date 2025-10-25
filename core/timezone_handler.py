"""
Timezone Handler Module
Manages timezone conversions and daily boundary detection for America/Bogota.
Daily candle closes at 16:00 local time (4:00 PM Colombia).
"""

from datetime import datetime, time, timedelta
import pytz
from typing import Optional


class TimezoneHandler:
    """
    Handles timezone operations for the trading bot.
    Anchored to America/Bogota with daily close at 16:00.
    """

    def __init__(self, timezone: str = 'America/Bogota', daily_close_hour: int = 16):
        """
        Initialize timezone handler.

        Args:
            timezone: IANA timezone name
            daily_close_hour: Hour of day when daily candle closes (0-23)
        """
        self.timezone = pytz.timezone(timezone)
        self.daily_close_hour = daily_close_hour
        self.daily_close_time = time(daily_close_hour, 0, 0)

    def now(self) -> datetime:
        """Get current time in configured timezone"""
        return datetime.now(self.timezone)

    def to_local(self, dt: datetime) -> datetime:
        """Convert datetime to local timezone"""
        if dt.tzinfo is None:
            # Assume UTC if no timezone
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(self.timezone)

    def to_utc(self, dt: datetime) -> datetime:
        """Convert datetime to UTC"""
        if dt.tzinfo is None:
            # Assume local timezone
            dt = self.timezone.localize(dt)
        return dt.astimezone(pytz.UTC)

    def get_current_trading_day(self, ref_time: Optional[datetime] = None) -> datetime:
        """
        Get the current trading day based on 16:00 boundary.

        If before 16:00, returns previous calendar day.
        If at or after 16:00, returns current calendar day.

        Args:
            ref_time: Reference time (defaults to now)

        Returns:
            Trading day as date
        """
        if ref_time is None:
            ref_time = self.now()
        else:
            ref_time = self.to_local(ref_time)

        if ref_time.hour < self.daily_close_hour:
            # Before 16:00 - still in previous trading day
            return (ref_time.date() - timedelta(days=1))
        else:
            # At or after 16:00 - current trading day
            return ref_time.date()

    def get_daily_close_time(self, trading_day: datetime.date) -> datetime:
        """
        Get the exact datetime when daily candle closes for a trading day.

        Args:
            trading_day: The trading day

        Returns:
            Datetime of daily close (16:00 on the given day)
        """
        close_dt = datetime.combine(trading_day, self.daily_close_time)
        return self.timezone.localize(close_dt)

    def is_daily_boundary_crossed(self, time1: datetime, time2: datetime) -> bool:
        """
        Check if the daily boundary (16:00) was crossed between two times.

        Args:
            time1: Earlier time
            time2: Later time

        Returns:
            True if 16:00 boundary was crossed
        """
        day1 = self.get_current_trading_day(time1)
        day2 = self.get_current_trading_day(time2)
        return day1 != day2

    def get_previous_trading_day(self, ref_time: Optional[datetime] = None) -> datetime.date:
        """
        Get the previous trading day.

        Args:
            ref_time: Reference time (defaults to now)

        Returns:
            Previous trading day
        """
        current_day = self.get_current_trading_day(ref_time)
        return current_day - timedelta(days=1)

    def is_within_trading_hours(self, start_time: str, end_time: str, ref_time: Optional[datetime] = None) -> bool:
        """
        Check if current time is within trading hours.

        Handles overnight sessions (e.g., 19:00 to 06:00).

        Args:
            start_time: Start time in HH:MM format (e.g., "19:00")
            end_time: End time in HH:MM format (e.g., "06:00")
            ref_time: Reference time (defaults to now)

        Returns:
            True if within trading hours
        """
        if ref_time is None:
            ref_time = self.now()
        else:
            ref_time = self.to_local(ref_time)

        # Parse times
        start_hour, start_min = map(int, start_time.split(':'))
        end_hour, end_min = map(int, end_time.split(':'))

        start_t = time(start_hour, start_min)
        end_t = time(end_hour, end_min)
        current_t = ref_time.time()

        if start_t <= end_t:
            # Same-day session (e.g., 09:00 to 17:00)
            return start_t <= current_t <= end_t
        else:
            # Overnight session (e.g., 19:00 to 06:00)
            return current_t >= start_t or current_t <= end_t

    def format_local(self, dt: datetime, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
        """
        Format datetime in local timezone.

        Args:
            dt: Datetime to format
            fmt: Format string

        Returns:
            Formatted string
        """
        local_dt = self.to_local(dt)
        return local_dt.strftime(fmt)
