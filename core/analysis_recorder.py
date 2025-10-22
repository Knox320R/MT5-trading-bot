"""
Analysis Recorder - Records all potentially feasible trading moments
Even if they don't meet all strict requirements
"""

import csv
import os
from datetime import datetime


class AnalysisRecorder:
    """Records all analysis data for potential trading moments to CSV files"""

    def __init__(self, output_dir='Report'):
        """
        Initialize the analysis recorder

        Args:
            output_dir: Directory to store analysis CSV files
        """
        self.output_dir = output_dir
        self.current_file = None
        self.current_writer = None
        self.current_hour = None

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def get_filename(self):
        """Generate filename based on current date and hour"""
        now = datetime.now()
        return os.path.join(
            self.output_dir,
            f'analysis_{now.strftime("%Y-%m-%d_%H")}.csv'
        )

    def ensure_file_open(self):
        """Ensure the correct file is open for the current hour"""
        now = datetime.now()
        current_hour = now.strftime('%Y-%m-%d_%H')

        # If hour changed or file not open, open new file
        if current_hour != self.current_hour:
            # Close previous file if open
            if self.current_file:
                self.current_file.close()

            filename = self.get_filename()
            file_exists = os.path.exists(filename)

            # Open file in append mode
            self.current_file = open(filename, 'a', newline='', encoding='utf-8')
            self.current_writer = csv.writer(self.current_file)
            self.current_hour = current_hour

            # Write header if new file
            if not file_exists:
                self.write_header()
                print(f"📊 Created analysis file: {filename}")

    def write_header(self):
        """Write CSV header row"""
        header = [
            'Timestamp',
            'Symbol',
            'Price',
            'Bid',
            'Ask',
            'Spread',
            # Snake colors (EMA 100)
            'Snake_D1',
            'Snake_H4',
            'Snake_H1',
            'Snake_M30',
            'Snake_M15',
            'Snake_M5',
            'Snake_M1',
            # Purple Line position (EMA 10)
            'PurpleLine_D1',
            'PurpleLine_H4',
            'PurpleLine_H1',
            'PurpleLine_M30',
            'PurpleLine_M15',
            'PurpleLine_M5',
            'PurpleLine_M1',
            # Analysis results
            'D1_Bias',
            'H4_Fib_Met',
            'Purple_Breakout',
            'Purple_Touchback',
            # Potential signal types
            'Could_Be_PAIN_SELL',
            'Could_Be_GAIN_SELL',
            'Could_Be_PAIN_BUY',
            'Could_Be_GAIN_BUY',
            # Missing conditions
            'Missing_Conditions',
            'Notes'
        ]
        self.current_writer.writerow(header)

    def record_analysis(self, analysis_data):
        """
        Record analysis data to CSV

        Args:
            analysis_data: Dictionary containing analysis information
        """
        try:
            self.ensure_file_open()

            # Extract data with defaults
            timestamp = analysis_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            symbol = analysis_data.get('symbol', 'N/A')
            price = analysis_data.get('price', 0)
            bid = analysis_data.get('bid', 0)
            ask = analysis_data.get('ask', 0)
            spread = analysis_data.get('spread', 0)

            # Snake colors for each timeframe
            snake_colors = analysis_data.get('snake_colors', {})
            snake_d1 = snake_colors.get('D1', 'N/A')
            snake_h4 = snake_colors.get('H4', 'N/A')
            snake_h1 = snake_colors.get('H1', 'N/A')
            snake_m30 = snake_colors.get('M30', 'N/A')
            snake_m15 = snake_colors.get('M15', 'N/A')
            snake_m5 = snake_colors.get('M5', 'N/A')
            snake_m1 = snake_colors.get('M1', 'N/A')

            # Purple Line positions
            purple_positions = analysis_data.get('purple_positions', {})
            purple_d1 = purple_positions.get('D1', 'N/A')
            purple_h4 = purple_positions.get('H4', 'N/A')
            purple_h1 = purple_positions.get('H1', 'N/A')
            purple_m30 = purple_positions.get('M30', 'N/A')
            purple_m15 = purple_positions.get('M15', 'N/A')
            purple_m5 = purple_positions.get('M5', 'N/A')
            purple_m1 = purple_positions.get('M1', 'N/A')

            # Analysis results
            d1_bias = analysis_data.get('d1_bias', 'N/A')
            h4_fib_met = analysis_data.get('h4_fib_met', False)
            purple_breakout = analysis_data.get('purple_breakout', 'N/A')
            purple_touchback = analysis_data.get('purple_touchback', False)

            # Potential signals
            could_pain_sell = analysis_data.get('could_pain_sell', False)
            could_gain_sell = analysis_data.get('could_gain_sell', False)
            could_pain_buy = analysis_data.get('could_pain_buy', False)
            could_gain_buy = analysis_data.get('could_gain_buy', False)

            # Missing conditions and notes
            missing = ', '.join(analysis_data.get('missing_conditions', []))
            notes = analysis_data.get('notes', '')

            # Write row
            row = [
                timestamp,
                symbol,
                f'{price:.5f}' if price else 'N/A',
                f'{bid:.5f}' if bid else 'N/A',
                f'{ask:.5f}' if ask else 'N/A',
                f'{spread:.5f}' if spread else 'N/A',
                snake_d1, snake_h4, snake_h1, snake_m30, snake_m15, snake_m5, snake_m1,
                purple_d1, purple_h4, purple_h1, purple_m30, purple_m15, purple_m5, purple_m1,
                d1_bias,
                'YES' if h4_fib_met else 'NO',
                purple_breakout,
                'YES' if purple_touchback else 'NO',
                'YES' if could_pain_sell else 'NO',
                'YES' if could_gain_sell else 'NO',
                'YES' if could_pain_buy else 'NO',
                'YES' if could_gain_buy else 'NO',
                missing,
                notes
            ]

            self.current_writer.writerow(row)
            self.current_file.flush()  # Ensure data is written immediately

        except Exception as e:
            print(f"Error recording analysis: {e}")

    def close(self):
        """Close the current file"""
        if self.current_file:
            self.current_file.close()
            self.current_file = None
            self.current_writer = None
            self.current_hour = None
