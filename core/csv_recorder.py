"""
CSV Recorder Module
Records trading signals to CSV files (one file per hour)
"""
import os
import csv
from datetime import datetime
from pathlib import Path


class CSVRecorder:
    def __init__(self, output_folder='Report'):
        self.output_folder = output_folder
        self.current_file = None
        self.current_hour = None
        self.csv_writer = None
        self.file_handle = None

        # Create output folder if it doesn't exist
        Path(self.output_folder).mkdir(parents=True, exist_ok=True)

    def get_filename(self, timestamp=None):
        """Generate filename based on timestamp"""
        if timestamp is None:
            timestamp = datetime.now()

        filename = timestamp.strftime('report_%Y-%m-%d_%H.csv')
        return os.path.join(self.output_folder, filename)

    def ensure_file_open(self):
        """Ensure the correct CSV file is open for the current hour"""
        now = datetime.now()
        current_hour = now.strftime('%Y-%m-%d_%H')

        # Check if we need to rotate to a new file
        if self.current_hour != current_hour:
            # Close existing file
            if self.file_handle:
                self.file_handle.close()

            # Open new file
            filename = self.get_filename(now)
            file_exists = os.path.exists(filename)

            self.file_handle = open(filename, 'a', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.file_handle)

            # Write header if new file
            if not file_exists:
                self.write_header()

            self.current_file = filename
            self.current_hour = current_hour
            print(f"📝 CSV Recorder: Now writing to {filename}")

    def write_header(self):
        """Write CSV header"""
        header = [
            'Timestamp',
            'Symbol',
            'SignalType',
            'Price',
            'SnakeColor_M1',
            'PurpleLine_Position',
            'D1_Snake',
            'H4_Snake',
            'H1_Snake',
            'M30_Snake',
            'M15_Snake',
            'M5_Snake',
            'M1_Snake',
            'Conditions_Met',
            'Reasons'
        ]
        self.csv_writer.writerow(header)
        self.file_handle.flush()

    def record_signal(self, signal):
        """Record a signal to CSV file"""
        try:
            self.ensure_file_open()

            # Extract data from signal
            timestamp = signal.get('timestamp', datetime.now().isoformat())
            symbol = signal.get('symbol', '')
            signal_type = signal.get('type', '')
            price = signal.get('price', 0.0)
            met = signal.get('met', False)
            reasons = '; '.join(signal.get('reasons', []))

            # Get timeframe data
            tf_data = signal.get('timeframe_data', {})

            # Prepare row
            row = [
                timestamp,
                symbol,
                signal_type,
                f"{price:.5f}",
                tf_data.get('M1', ''),
                signal.get('purple_line_position', ''),
                tf_data.get('D1', ''),
                tf_data.get('H4', ''),
                tf_data.get('H1', ''),
                tf_data.get('M30', ''),
                tf_data.get('M15', ''),
                tf_data.get('M5', ''),
                tf_data.get('M1', ''),
                'YES' if met else 'NO',
                reasons
            ]

            # Write row
            self.csv_writer.writerow(row)
            self.file_handle.flush()  # Ensure data is written immediately

            print(f"✓ Recorded signal: {signal_type} {symbol} @ {price:.5f}")

        except Exception as e:
            print(f"✗ Error recording signal to CSV: {e}")
            import traceback
            traceback.print_exc()

    def close(self):
        """Close the CSV file"""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
            self.csv_writer = None
            print("CSV Recorder closed")
