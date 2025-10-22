"""
Simple HTTP server to serve config.json to the dashboard
This allows the HTML dashboard to access configuration
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from config_loader import config

class ConfigHTTPRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow local file access
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        if self.path == '/config' or self.path == '/config.json':
            # Serve config as JSON
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            # Get dashboard-relevant config
            dashboard_config = {
                'symbols': {
                    'all': config.get_all_symbols(),
                    'pain': config.get_pain_symbols(),
                    'gain': config.get_gain_symbols()
                },
                'timeframes': config.get_timeframes(),
                'default_symbol': config.get_default_symbol(),
                'default_timeframe': config.get_default_timeframe(),
                'dashboard': {
                    'title': config.get_dashboard_title(),
                    'theme': config.get('dashboard', 'theme', default='dark'),
                    'chart_bars_count': config.get_chart_bars_count()
                },
                'environment': config.get_environment_mode(),
                'server': {
                    'host': config.get_server_host(),
                    'ports': config.get_server_ports()
                },
                'trading': {
                    'lot_size': config.get_lot_size(),
                    'daily_target': config.get_daily_target_usd(),
                    'daily_stop': config.get_daily_stop_usd()
                }
            }

            self.wfile.write(json.dumps(dashboard_config, indent=2).encode())
        else:
            super().do_GET()


if __name__ == '__main__':
    port = 8000
    server = HTTPServer(('localhost', port), ConfigHTTPRequestHandler)
    print(f"Config server running on http://localhost:{port}")
    print(f"Access config at: http://localhost:{port}/config")
    server.serve_forever()
