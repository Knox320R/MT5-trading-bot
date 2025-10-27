import asyncio
import websockets
import json
import webbrowser
import os
import numpy as np
from datetime import datetime
from .mt5_connector import MT5Connector
from .config_loader import config
from .csv_recorder import CSVRecorder
from .bot_engine import BotEngine
from .order_manager import OrderManager
from .exit_manager import ExitManager
from .trade_logger import TradeLogger
from .timezone_handler import TimezoneHandler
from .risk_manager import RiskManager

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
        self.csv_recorder = CSVRecorder()

        # Initialize bot engine components
        self.tz_handler = TimezoneHandler(
            timezone=config.get_environment_timezone(),
            daily_close_hour=16
        )
        self.bot_engine = BotEngine(self.connector)
        self.order_manager = OrderManager(self.connector, self.tz_handler)
        self.exit_manager = ExitManager(self.order_manager, self.bot_engine.indicator_calc)
        self.trade_logger = TradeLogger(self.tz_handler)
        self.risk_manager = RiskManager(self.tz_handler, self.connector)

        # Track bot states for UI
        self.bot_states = {}  # symbol -> bot results

        # Data caching to prevent hammering MT5 API
        self.bars_cache = {}  # symbol -> {'m1': [...], 'd1': [...], 'm5': [...], 'last_update': timestamp}

    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        try:
            self.clients.add(websocket)
            print(f"[OK] Client connected. Total clients: {len(self.clients)}")

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
                    'environment': config.get_environment_mode(),
                    'indicators': {
                        'snake_period': config.get_snake_period(),
                        'snake_type': config.get_snake_type(),
                        'purple_line_period': config.get_purple_line_period(),
                        'purple_line_type': config.get_purple_line_type()
                    }
                }
            }
            print(f"  Sending initial config...")
            await websocket.send(json.dumps(config_data))
            print(f"  [OK] Config sent successfully")
        except Exception as e:
            print(f"[ERROR] Error registering client: {e}")
            import traceback
            traceback.print_exc()

    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        self.clients.remove(websocket)
        print(f"Client disconnected. Total clients: {len(self.clients)}")

    def convert_to_json_serializable(self, obj):
        """Convert numpy types and enums to native Python types for JSON serialization"""
        from enum import Enum

        if isinstance(obj, dict):
            # Convert enum keys to their values
            return {
                (key.value if isinstance(key, Enum) else key): self.convert_to_json_serializable(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self.convert_to_json_serializable(item) for item in obj]
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, (np.integer, np.int64, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    async def send_data_to_clients(self, data):
        """Send data to all connected clients"""
        if self.clients:
            # Convert numpy types to native Python types
            serializable_data = self.convert_to_json_serializable(data)
            message = json.dumps(serializable_data)
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

            elif command == 'get_trade_history':
                # Fetch trade history from CSV files
                symbol = data.get('symbol', self.current_symbol)
                date_from = data.get('date_from')  # YYYY-MM-DD format
                date_to = data.get('date_to')      # YYYY-MM-DD format

                try:
                    trade_history = self.trade_logger.get_trades_for_period(symbol, date_from, date_to)

                    await websocket.send(json.dumps({
                        'type': 'trade_history',
                        'symbol': symbol,
                        'trades': trade_history
                    }))
                    print(f"  [OK] Sent {len(trade_history)} trade history entries")
                except Exception as e:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': f'Error loading trade history: {str(e)}'
                    }))
                    print(f"  [ERROR] Trade history load failed: {e}")

            elif command == 'get_historical_data':
                # Fetch exact number of historical bars ending at specified time
                symbol = data.get('symbol', self.current_symbol)
                timeframe = data.get('timeframe', 'M1')
                date_to = data.get('date_to')
                bars_count = data.get('bars_count', 100)

                print(f"Historical data request: {symbol} {timeframe} - {bars_count} bars ending at {date_to}")

                try:
                    # Parse datetime string
                    from datetime import datetime
                    dt_to = datetime.fromisoformat(date_to)

                    # Fetch exact number of bars using MT5's copy_rates_from
                    # This is much faster than fetching a range and filtering
                    import MetaTrader5 as mt5

                    timeframe_map = {
                        'M1': mt5.TIMEFRAME_M1,
                        'M5': mt5.TIMEFRAME_M5,
                        'M15': mt5.TIMEFRAME_M15,
                        'M30': mt5.TIMEFRAME_M30,
                        'H1': mt5.TIMEFRAME_H1,
                        'H4': mt5.TIMEFRAME_H4,
                        'D1': mt5.TIMEFRAME_D1
                    }

                    tf = timeframe_map.get(timeframe, mt5.TIMEFRAME_M1)
                    rates = mt5.copy_rates_from(symbol, tf, dt_to, bars_count)

                    if rates is not None and len(rates) > 0:
                        # Convert to bars format
                        bars = []
                        for rate in rates:
                            bars.append({
                                'time': datetime.fromtimestamp(rate['time']).strftime('%Y-%m-%d %H:%M:%S'),
                                'open': float(rate['open']),
                                'high': float(rate['high']),
                                'low': float(rate['low']),
                                'close': float(rate['close']),
                                'tick_volume': int(rate['tick_volume']),
                                'spread': int(rate['spread']),
                                'real_volume': int(rate['real_volume'])
                            })

                        await websocket.send(json.dumps({
                            'type': 'historical_data',
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'date_from': bars[0]['time'] if bars else '',
                            'date_to': date_to,
                            'bars': bars,
                            'bars_count': len(bars)
                        }))
                        print(f"  [OK] Sent {len(bars)} historical bars")
                    else:
                        await websocket.send(json.dumps({
                            'type': 'error',
                            'message': f'No historical data available for {symbol} {timeframe}'
                        }))
                        print(f"  [ERROR] No data available")
                except Exception as e:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': f'Error fetching historical data: {str(e)}'
                    }))
                    print(f"  [ERROR] Error: {e}")

            elif command == 'set_indicator_period':
                # DEPRECATED: Indicator periods are now set in config.json only
                # This command is kept for backward compatibility but does nothing
                print(f"[WARNING] set_indicator_period command is deprecated. EMA periods are now controlled via config.json")
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Indicator periods must be set in config.json and require server restart'
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

            elif command == 'execute_trade':
                # Execute manual trade
                action = data.get('action')  # 'buy' or 'sell'
                symbol = data.get('symbol', self.current_symbol)

                print(f"Manual trade request: {action.upper()} {symbol}")

                try:
                    import MetaTrader5 as mt5

                    # Get symbol info
                    symbol_info = mt5.symbol_info(symbol)
                    if symbol_info is None:
                        await websocket.send(json.dumps({
                            'type': 'error',
                            'message': f'Symbol {symbol} not found'
                        }))
                        print(f"  [ERROR] Symbol not found: {symbol}")
                        return

                    # Get current price
                    tick = mt5.symbol_info_tick(symbol)
                    if tick is None:
                        await websocket.send(json.dumps({
                            'type': 'error',
                            'message': f'Could not get price for {symbol}'
                        }))
                        print(f"  [ERROR] Could not get price")
                        return

                    # Determine order type and price
                    if action == 'buy':
                        order_type = mt5.ORDER_TYPE_BUY
                        price = tick.ask
                    else:  # sell
                        order_type = mt5.ORDER_TYPE_SELL
                        price = tick.bid

                    # Get volume from config or use minimum
                    volume = symbol_info.volume_min

                    # Prepare the request
                    request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": volume,
                        "type": order_type,
                        "price": price,
                        "deviation": 20,
                        "magic": 234000,
                        "comment": "Manual trade from dashboard",
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_IOC,
                    }

                    # Send trade request
                    result = mt5.order_send(request)

                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        await websocket.send(json.dumps({
                            'type': 'error',
                            'message': f'Trade failed: {result.comment}'
                        }))
                        print(f"  [ERROR] Trade failed: {result.retcode} - {result.comment}")
                    else:
                        await websocket.send(json.dumps({
                            'type': 'trade_success',
                            'data': {
                                'order': result.order,
                                'volume': result.volume,
                                'price': result.price,
                                'symbol': symbol,
                                'action': action
                            }
                        }))
                        print(f"  [OK] Trade executed: Order #{result.order}, {action.upper()} {result.volume} {symbol} @ {result.price}")

                except Exception as e:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': f'Error executing trade: {str(e)}'
                    }))
                    print(f"  [ERROR] Error: {e}")

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
            print(f"[ERROR] WebSocket handler error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                await self.unregister_client(websocket)
            except Exception as e:
                print(f"Error unregistering client: {e}")

    def get_bars_cached(self, symbol, timeframe, count):
        """Get bars with caching to prevent hammering MT5 API"""
        import MetaTrader5 as mt5
        from datetime import datetime

        # Determine cache key
        tf_key = f"{timeframe}"

        # Check if we have cached data
        now = datetime.now()
        if symbol in self.bars_cache and tf_key in self.bars_cache[symbol]:
            cached = self.bars_cache[symbol][tf_key]
            last_update = cached.get('last_update')

            # Only refetch if more than 1 minute has passed
            if last_update and (now - last_update).total_seconds() < 60:
                return cached['bars']

        # Fetch fresh data
        if timeframe == 'M1':
            mt5_tf = mt5.TIMEFRAME_M1
        elif timeframe == 'M5':
            mt5_tf = mt5.TIMEFRAME_M5
        elif timeframe == 'D1':
            mt5_tf = mt5.TIMEFRAME_D1
        else:
            return None

        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, count)
        if rates is None or len(rates) == 0:
            return None

        # Convert to bars format
        bars = []
        for rate in rates:
            bars.append({
                'time': datetime.fromtimestamp(rate['time']),
                'open': float(rate['open']),
                'high': float(rate['high']),
                'low': float(rate['low']),
                'close': float(rate['close']),
                'volume': int(rate['tick_volume'])
            })

        # Update cache
        if symbol not in self.bars_cache:
            self.bars_cache[symbol] = {}
        self.bars_cache[symbol][tf_key] = {
            'bars': bars,
            'last_update': now
        }

        return bars

    async def bot_engine_loop(self):
        """Run bot engine for all symbols every 2 seconds"""
        print("Starting bot engine loop...")
        print(f"Checking symbols: {config.get_all_symbols()}")
        print()

        iteration = 0
        while self.running:
            iteration += 1
            try:
                # Get all symbols to check
                all_symbols = config.get_all_symbols()

                for symbol in all_symbols:
                    # Get M1 bars for the symbol (cached to prevent API overload)
                    # Need 7200 M1 bars to calculate EMA100 on H1 (100 H1 bars * 60 minutes)
                    m1_bars = self.get_bars_cached(symbol, 'M1', 7200)
                    if m1_bars is None or len(m1_bars) == 0:
                        continue

                    # Get D1 bars directly from MT5 (uses broker's daily boundary, cached)
                    d1_bars_mt5 = self.get_bars_cached(symbol, 'D1', 10)

                    # Process through bot engine with MT5 D1 bars
                    bot_results = self.bot_engine.process_symbol(symbol, m1_bars, d1_bars_mt5)

                    # Store results for UI
                    self.bot_states[symbol] = bot_results

                    # Check for ready signals and execute if risk gates pass
                    for bot_type, result in bot_results['bot_results'].items():
                        if result['ready']:
                            print(f"[BOT_ENGINE] {symbol} - {bot_type.value} is READY to trade!")

                            # Check if already in position
                            if self.order_manager.has_open_position(symbol, bot_type.value):
                                print(f"[BOT_ENGINE] {symbol} - {bot_type.value} already has open position, skipping")
                                continue

                            # Check global risk gates
                            bot_type_str = bot_type.value
                            order_type = 'buy' if 'buy' in bot_type_str else 'sell'

                            risk_check = self.risk_manager.check_all_gates(symbol, order_type, bot_type_str)
                            if not risk_check['allowed']:
                                print(f"[BLOCKED] {symbol} - {bot_type_str} - Risk gates: {', '.join(risk_check['reasons'])}")
                                continue

                            print(f"[BOT_ENGINE] {symbol} - {bot_type_str} passed all risk gates, executing trade...")

                            # Execute order
                            # Extract text from reasons (handle both dict and string formats)
                            reason_texts = []
                            for r in result['reasons']:
                                if isinstance(r, dict) and 'text' in r:
                                    reason_texts.append(r['text'])
                                elif isinstance(r, str):
                                    reason_texts.append(r)
                            reason_str = ' | '.join(reason_texts)

                            if 'buy' in bot_type_str:
                                entry_result = self.order_manager.execute_buy(
                                    symbol, bot_type_str,
                                    reason=reason_str
                                )
                            else:
                                entry_result = self.order_manager.execute_sell(
                                    symbol, bot_type_str,
                                    reason=reason_str
                                )

                            if entry_result['success']:
                                print(f"[EXECUTED] {bot_type_str}: {symbol} @ {entry_result['price']:.5f}, ticket: {entry_result['ticket']}")

                                # Increment consecutive orders counter
                                self.risk_manager.increment_consecutive_orders(symbol, bot_type_str)

                                # Log trade entry
                                print(f"[BOT_ENGINE] Calling trade_logger.log_trade_entry()...")
                                log_success = self.trade_logger.log_trade_entry(
                                    symbol, bot_type_str, entry_result,
                                    bot_results['bias'], bot_results['trend_summary']
                                )
                                if log_success:
                                    print(f"[BOT_ENGINE] ✓ Trade entry logged to CSV")
                                else:
                                    print(f"[BOT_ENGINE] ✗ Failed to log trade entry to CSV")

                                # Broadcast to clients
                                await self.send_data_to_clients({
                                    'type': 'trade_executed',
                                    'bot_type': bot_type_str,
                                    'symbol': symbol,
                                    'action': order_type,
                                    'price': entry_result['price'],
                                    'ticket': entry_result['ticket']
                                })
                            else:
                                print(f"[FAILED] {bot_type_str}: {symbol} - {entry_result.get('error')}")

                    # Check exits for open positions (cached)
                    m5_bars = self.get_bars_cached(symbol, 'M5', 20)
                    if m5_bars is not None and len(m5_bars) > 0:
                        exits = self.exit_manager.check_exits(symbol, m5_bars)

                        for exit_info in exits:
                            print(f"[EXIT] {self.exit_manager.get_exit_summary(exit_info)}")

                            # Record profit/loss for risk tracking (resets consecutive counter if profitable)
                            self.risk_manager.record_trade_result(symbol, exit_info['profit'], exit_info['bot_type'])

                            # Log trade exit
                            print(f"[BOT_ENGINE] Calling trade_logger.log_trade_exit()...")
                            log_success = self.trade_logger.log_trade_exit(
                                symbol, exit_info['bot_type'], exit_info,
                                bot_results['bias'], bot_results['trend_summary']
                            )
                            if log_success:
                                print(f"[BOT_ENGINE] ✓ Trade exit logged to CSV")
                            else:
                                print(f"[BOT_ENGINE] ✗ Failed to log trade exit to CSV")

                            # Broadcast to clients
                            await self.send_data_to_clients({
                                'type': 'trade_closed',
                                'symbol': symbol,
                                'bot_type': exit_info['bot_type'],
                                'profit': exit_info['profit'],
                                'reason': exit_info['reason']
                            })

                    # Broadcast bot states to clients
                    await self.send_data_to_clients({
                        'type': 'bot_status',
                        'symbol': symbol,
                        'data': bot_results
                    })

                # Print progress every 30 iterations (every 60 seconds)
                if iteration % 30 == 1:
                    print(f"[{iteration}] Bot engine running - checking {len(all_symbols)} symbols")

                # Wait 2 seconds before next cycle
                await asyncio.sleep(2)

            except Exception as e:
                print(f"[ERROR] Error in bot engine loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(5)

    async def detect_signals_loop(self):
        """Detect trading signals for all symbols every 2 seconds (legacy - now using bot_engine_loop)"""
        print("Signal detection loop is replaced by bot_engine_loop")
        # This is now handled by bot_engine_loop
        while self.running:
            await asyncio.sleep(60)

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
                    # Print update every 10 iterations (every 20 seconds with 2s interval)
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
                print(f"[ERROR] Error in market data stream: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(5)

        # Cleanup
        self.connector.disconnect()
        self.csv_recorder.close()

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
                print(f"[OK] Opened in Chrome")
            else:
                print("Chrome not found, using default browser...")
                webbrowser.open(dashboard_url)

        # Start market data streaming in background
        asyncio.create_task(self.stream_market_data())

        # Start bot engine loop in background (replaces old signal detection)
        asyncio.create_task(self.bot_engine_loop())

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
