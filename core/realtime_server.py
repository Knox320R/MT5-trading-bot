import asyncio
import websockets
import json
import webbrowser
import os
from datetime import datetime
from .mt5_connector import MT5Connector
from .config_loader import config

# Set Windows-specific event loop policy
if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class RealtimeDataServer:
    def __init__(self):
        self.connector = MT5Connector()
        self.clients = set()
        self.running = False
        self.current_symbol = config.get_default_symbol()
        self.timeframe = config.get_default_timeframe()
        self.update_interval = config.get_update_interval()

    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        try:
            self.clients.add(websocket)
            print(f"✓ Client connected. Total clients: {len(self.clients)}")

            # Send initial config to client
            config_data = {
                'type': 'config',
                'data': {
                    'symbols': config.get_all_symbols(),
                    'pain_symbols': config.get_pain_symbols(),
                    'gain_symbols': config.get_gain_symbols(),
                    'timeframes': config.get_timeframes(),
                    'default_symbol': config.get_default_symbol(),
                    'default_timeframe': config.get_default_timeframe(),
                    'dashboard_title': config.get_dashboard_title(),
                    'environment': config.get_environment_mode()
                }
            }
            print(f"  Sending initial config...")
            await websocket.send(json.dumps(config_data))
            print(f"  ✓ Config sent successfully")
        except Exception as e:
            print(f"✗ Error registering client: {e}")
            import traceback
            traceback.print_exc()

    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        self.clients.remove(websocket)
        print(f"Client disconnected. Total clients: {len(self.clients)}")

    async def send_data_to_clients(self, data):
        """Send data to all connected clients"""
        if self.clients:
            message = json.dumps(data)
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )

    async def handle_client_message(self, websocket, message):
        """Handle incoming messages from clients"""
        try:
            data = json.loads(message)
            command = data.get('command')

            if command == 'set_symbol':
                symbol = data.get('symbol', config.get_default_symbol())
                if symbol in config.get_all_symbols():
                    self.current_symbol = symbol
                    print(f"Symbol changed to: {self.current_symbol}")
                    await websocket.send(json.dumps({
                        'type': 'symbol_changed',
                        'symbol': self.current_symbol
                    }))
                else:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': f'Invalid symbol: {symbol}'
                    }))

            elif command == 'set_timeframe':
                timeframe = data.get('timeframe', config.get_default_timeframe())
                if timeframe in config.get_timeframes():
                    self.timeframe = timeframe
                    print(f"Timeframe changed to: {self.timeframe}")
                    await websocket.send(json.dumps({
                        'type': 'timeframe_changed',
                        'timeframe': self.timeframe
                    }))
                else:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': f'Invalid timeframe: {timeframe}'
                    }))

            elif command == 'get_config':
                # Send config to client
                await websocket.send(json.dumps({
                    'type': 'config',
                    'data': {
                        'symbols': config.get_all_symbols(),
                        'timeframes': config.get_timeframes(),
                        'current_symbol': self.current_symbol,
                        'current_timeframe': self.timeframe,
                        'environment': config.get_environment_mode()
                    }
                }))

        except Exception as e:
            print(f"Error handling client message: {e}")

    async def websocket_handler(self, websocket):
        """Handle WebSocket connections"""
        print(f"New WebSocket connection attempt from {websocket.remote_address}")
        try:
            await self.register_client(websocket)
            async for message in websocket:
                await self.handle_client_message(websocket, message)
        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection closed: {e}")
        except Exception as e:
            print(f"✗ WebSocket handler error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                await self.unregister_client(websocket)
            except Exception as e:
                print(f"Error unregistering client: {e}")

    async def stream_market_data(self):
        """Stream market data to connected clients"""
        # Connect using config credentials
        if not self.connector.connect_from_config():
            print("Failed to connect to MT5")
            return

        print("Starting market data stream...")
        print(f"Symbol: {self.current_symbol}")
        print(f"Timeframe: {self.timeframe}")
        print(f"Update interval: {self.update_interval}s")
        print()

        iteration = 0
        while self.running:
            iteration += 1
            try:
                # Get current tick
                tick = self.connector.get_current_tick(self.current_symbol)

                # Get recent bars
                bars = self.connector.get_bars(
                    self.current_symbol,
                    self.timeframe,
                    config.get_chart_bars_count()
                )

                # Get account info
                account = self.connector.get_account_info()

                # Get positions
                positions = self.connector.get_positions()

                # Get symbol info
                symbol_info = self.connector.get_symbol_info(self.current_symbol)

                if tick and bars:
                    # Print update every 10 iterations (every 10 seconds)
                    if iteration % 10 == 1:
                        print(f"[{iteration}] Streaming data - Bid: {tick['bid']}, Clients: {len(self.clients)}")

                    data = {
                        'type': 'market_update',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'symbol': self.current_symbol,
                        'timeframe': self.timeframe,
                        'tick': tick,
                        'bars': bars,
                        'account': account,
                        'positions': positions,
                        'symbol_info': symbol_info
                    }

                    await self.send_data_to_clients(data)
                elif not bars:
                    # Symbol might not exist or no data available
                    print(f"⚠ No data available for {self.current_symbol}")
                    error_data = {
                        'type': 'error',
                        'message': f"No data available for {self.current_symbol}. Symbol might not exist."
                    }
                    await self.send_data_to_clients(error_data)

                # Update at configured interval
                await asyncio.sleep(self.update_interval)

            except Exception as e:
                print(f"✗ Error in market data stream: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(5)

        self.connector.disconnect()

    async def start(self, host=None, port=None, open_browser=None):
        """Start the WebSocket server"""
        # Use config defaults if not provided
        if host is None:
            host = config.get_server_host()
        if port is None:
            ports = config.get_server_ports()
            port = ports[0] if ports else 8765
        if open_browser is None:
            open_browser = config.get_auto_open_browser()

        self.running = True

        # Start WebSocket server - bind to IPv4 only
        server = await websockets.serve(
            self.websocket_handler,
            host,
            port,
            family=2  # Force IPv4 (AF_INET)
        )
        print(f"WebSocket server started on ws://{host}:{port}")
        print(f"Environment: {config.get_environment_mode().upper()}")
        print(f"MT5 Account: {config.get_mt5_login()} @ {config.get_mt5_server()}")

        # Open browser automatically
        if open_browser:
            # Fix path - go up one directory from core/
            project_root = os.path.dirname(os.path.dirname(__file__))
            dashboard_path = os.path.join(project_root, 'interface', 'index.html')
            dashboard_url = f'file:///{dashboard_path.replace(os.sep, "/")}'
            print(f"Opening dashboard in Chrome...")

            # Try to open in Chrome specifically
            chrome_path = None
            possible_chrome_paths = [
                r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                os.path.expanduser(r'~\AppData\Local\Google\Chrome\Application\chrome.exe'),
            ]

            for path in possible_chrome_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break

            if chrome_path:
                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
                webbrowser.get('chrome').open(dashboard_url)
                print(f"✓ Opened in Chrome")
            else:
                print("Chrome not found, using default browser...")
                webbrowser.open(dashboard_url)

        # Start market data streaming in background
        asyncio.create_task(self.stream_market_data())

        # Keep server running
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    print("="*60)
    print(" MT5 Real-Time Data Server")
    print("="*60)
    print(f"Loading configuration...")
    print(f"Environment: {config.get_environment_mode().upper()}")
    print(f"MT5 Account: {config.get_mt5_login()}")
    print(f"MT5 Server: {config.get_mt5_server()}")
    print(f"Default Symbol: {config.get_default_symbol()}")
    print(f"Default Timeframe: {config.get_default_timeframe()}")
    print("="*60)
    print()

    # Create and start server
    realtime_server = RealtimeDataServer()

    # Try different ports if configured port is in use
    ports_to_try = config.get_server_ports()

    for port in ports_to_try:
        try:
            print(f"Attempting to start server on port {port}...")
            asyncio.run(realtime_server.start(port=port))
            break
        except OSError as e:
            if e.errno == 10048:
                print(f"Port {port} is already in use, trying next port...")
                continue
            else:
                raise
        except KeyboardInterrupt:
            print("\nServer stopped by user")
            break
    else:
        print("\nERROR: Could not find an available port. Please run kill_server.bat first.")
