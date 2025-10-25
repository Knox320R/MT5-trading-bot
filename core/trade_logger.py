"""
Trade Logger
Comprehensive logging system with:
1. Rotating logs every 15 minutes
2. Trade CSV export to Report/ folder
3. Signal detection logging
"""

import os
import csv
from datetime import datetime
from typing import Dict, List
from .timezone_handler import TimezoneHandler


class TradeLogger:
    """
    Logs all trading activity to CSV files.
    Separate files for trades and signals.
    """

    def __init__(self, timezone_handler: TimezoneHandler, report_dir: str = "Report"):
        """
        Initialize trade logger.

        Args:
            timezone_handler: TimezoneHandler for timestamps
            report_dir: Directory for CSV files (default: "Report")
        """
        self.tz_handler = timezone_handler
        self.report_dir = report_dir

        # Create report directory if needed
        os.makedirs(report_dir, exist_ok=True)

        # CSV field names
        self.trade_fields = [
            'timestamp', 'symbol', 'bot_type', 'action', 'ticket',
            'entry_price', 'exit_price', 'lot_size', 'profit_usd',
            'entry_time', 'exit_time', 'duration_minutes',
            'entry_reason', 'exit_reason', 'bias', 'trend_status'
        ]

        self.signal_fields = [
            'timestamp', 'symbol', 'bot_type', 'signal_type',
            'price', 'bias', 'trend_h1', 'trend_m30', 'trend_m15',
            'm30_break', 'm1_state', 'fib50', 'reasons', 'executed'
        ]

    def log_trade_entry(self, symbol: str, bot_type: str, entry_info: Dict,
                       bias: str, trend_status: str) -> bool:
        """
        Log trade entry to CSV.

        Args:
            symbol: Trading symbol
            bot_type: Bot type (e.g., 'pain_buy')
            entry_info: Entry information from order_manager
            bias: Daily bias (BUY/SELL/NEUTRAL)
            trend_status: Trend alignment status

        Returns:
            True if logged successfully
        """
        try:
            timestamp = self.tz_handler.now()
            date_str = timestamp.strftime('%Y-%m-%d')
            hour_str = timestamp.strftime('%H')

            # Create hourly CSV file
            filename = os.path.join(self.report_dir, f"trades_{date_str}_{hour_str}.csv")

            # Check if file exists
            file_exists = os.path.exists(filename)

            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.trade_fields)

                if not file_exists:
                    writer.writeheader()

                writer.writerow({
                    'timestamp': timestamp.isoformat(),
                    'symbol': symbol,
                    'bot_type': bot_type,
                    'action': 'ENTRY',
                    'ticket': entry_info.get('ticket', ''),
                    'entry_price': entry_info.get('price', 0),
                    'exit_price': '',
                    'lot_size': entry_info.get('lot_size', 0),
                    'profit_usd': '',
                    'entry_time': timestamp.isoformat(),
                    'exit_time': '',
                    'duration_minutes': '',
                    'entry_reason': entry_info.get('reason', ''),
                    'exit_reason': '',
                    'bias': bias,
                    'trend_status': trend_status
                })

            return True

        except Exception as e:
            print(f"Error logging trade entry: {e}")
            return False

    def log_trade_exit(self, symbol: str, bot_type: str, exit_info: Dict,
                      bias: str, trend_status: str) -> bool:
        """
        Log trade exit to CSV.

        Args:
            symbol: Trading symbol
            bot_type: Bot type
            exit_info: Exit information from exit_manager
            bias: Daily bias
            trend_status: Trend alignment status

        Returns:
            True if logged successfully
        """
        try:
            timestamp = self.tz_handler.now()
            date_str = timestamp.strftime('%Y-%m-%d')
            hour_str = timestamp.strftime('%H')

            filename = os.path.join(self.report_dir, f"trades_{date_str}_{hour_str}.csv")

            # Calculate duration
            entry_time = exit_info.get('entry_time')
            exit_time = exit_info.get('close_time')

            if entry_time and exit_time:
                duration = (exit_time - entry_time).total_seconds() / 60
            else:
                duration = 0

            file_exists = os.path.exists(filename)

            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.trade_fields)

                if not file_exists:
                    writer.writeheader()

                writer.writerow({
                    'timestamp': timestamp.isoformat(),
                    'symbol': symbol,
                    'bot_type': bot_type,
                    'action': 'EXIT',
                    'ticket': exit_info.get('ticket', ''),
                    'entry_price': exit_info.get('entry_price', 0),
                    'exit_price': exit_info.get('close_price', 0),
                    'lot_size': '',
                    'profit_usd': exit_info.get('profit', 0),
                    'entry_time': entry_time.isoformat() if entry_time else '',
                    'exit_time': exit_time.isoformat() if exit_time else '',
                    'duration_minutes': f"{duration:.1f}",
                    'entry_reason': '',
                    'exit_reason': exit_info.get('reason', ''),
                    'bias': bias,
                    'trend_status': trend_status
                })

            return True

        except Exception as e:
            print(f"Error logging trade exit: {e}")
            return False

    def log_signal(self, symbol: str, bot_type: str, signal_info: Dict) -> bool:
        """
        Log signal detection to CSV.

        Args:
            symbol: Trading symbol
            bot_type: Bot type
            signal_info: Signal information

        Returns:
            True if logged successfully
        """
        try:
            timestamp = self.tz_handler.now()
            date_str = timestamp.strftime('%Y-%m-%d')
            hour_str = timestamp.strftime('%H')

            filename = os.path.join(self.report_dir, f"signals_{date_str}_{hour_str}.csv")

            file_exists = os.path.exists(filename)

            # Extract reasons
            reasons = signal_info.get('reasons', [])
            reasons_str = ' | '.join(reasons)

            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.signal_fields)

                if not file_exists:
                    writer.writeheader()

                writer.writerow({
                    'timestamp': timestamp.isoformat(),
                    'symbol': symbol,
                    'bot_type': bot_type,
                    'signal_type': 'READY' if signal_info.get('ready') else 'NOT_READY',
                    'price': signal_info.get('price', ''),
                    'bias': signal_info.get('bias', ''),
                    'trend_h1': signal_info.get('trend_h1', ''),
                    'trend_m30': signal_info.get('trend_m30', ''),
                    'trend_m15': signal_info.get('trend_m15', ''),
                    'm30_break': signal_info.get('m30_break', ''),
                    'm1_state': signal_info.get('m1_state', ''),
                    'fib50': signal_info.get('fib50', ''),
                    'reasons': reasons_str,
                    'executed': signal_info.get('executed', False)
                })

            return True

        except Exception as e:
            print(f"Error logging signal: {e}")
            return False

    def log_error(self, error_type: str, message: str, details: Dict = None):
        """
        Log errors to error log file.

        Args:
            error_type: Type of error
            message: Error message
            details: Additional details
        """
        try:
            timestamp = self.tz_handler.now()
            date_str = timestamp.strftime('%Y-%m-%d')

            filename = os.path.join(self.report_dir, f"errors_{date_str}.log")

            with open(filename, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp.isoformat()}] {error_type}: {message}\n")
                if details:
                    f.write(f"  Details: {details}\n")
                f.write("\n")

        except Exception as e:
            print(f"Error logging error (meta!): {e}")

    def get_daily_summary(self, date: str = None) -> Dict:
        """
        Get summary of trading activity for a day.

        Args:
            date: Date string (YYYY-MM-DD), defaults to today

        Returns:
            Dictionary with daily statistics
        """
        if date is None:
            date = self.tz_handler.now().strftime('%Y-%m-%d')

        summary = {
            'date': date,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'net_profit': 0.0,
            'win_rate': 0.0,
            'by_bot': {}
        }

        # Read all hourly files for the day
        for hour in range(24):
            hour_str = f"{hour:02d}"
            filename = os.path.join(self.report_dir, f"trades_{date}_{hour_str}.csv")

            if not os.path.exists(filename):
                continue

            try:
                with open(filename, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)

                    for row in reader:
                        if row['action'] == 'EXIT' and row['profit_usd']:
                            summary['total_trades'] += 1

                            profit = float(row['profit_usd'])
                            bot_type = row['bot_type']

                            if profit > 0:
                                summary['winning_trades'] += 1
                                summary['total_profit'] += profit
                            else:
                                summary['losing_trades'] += 1
                                summary['total_loss'] += abs(profit)

                            summary['net_profit'] += profit

                            # Per-bot stats
                            if bot_type not in summary['by_bot']:
                                summary['by_bot'][bot_type] = {
                                    'trades': 0,
                                    'profit': 0.0
                                }

                            summary['by_bot'][bot_type]['trades'] += 1
                            summary['by_bot'][bot_type]['profit'] += profit

            except Exception as e:
                print(f"Error reading {filename}: {e}")

        # Calculate win rate
        if summary['total_trades'] > 0:
            summary['win_rate'] = (summary['winning_trades'] / summary['total_trades']) * 100

        return summary
