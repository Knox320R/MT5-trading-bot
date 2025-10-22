import MetaTrader5 as mt5
from datetime import datetime
import json
from .config_loader import config

class MT5Connector:
    def __init__(self, use_config=True):
        self.initialized = False
        self.account_info = None
        self.use_config = use_config

    def connect_from_config(self):
        """Connect to MT5 using credentials from config file"""
        login = config.get_mt5_login()
        password = config.get_mt5_password()
        server = config.get_mt5_server()

        mode = "DEMO" if config.is_demo_mode() else "LIVE"
        print(f"Connecting to {mode} account...")

        return self.connect(login, password, server)

    def connect(self, login, password, server):
        """Connect to MT5 account"""
        if not mt5.initialize():
            print(f"initialize() failed, error code = {mt5.last_error()}")
            return False

        # Login to account
        authorized = mt5.login(login, password=password, server=server)
        if not authorized:
            print(f"Login failed, error code = {mt5.last_error()}")
            mt5.shutdown()
            return False

        self.initialized = True
        self.account_info = mt5.account_info()
        print(f"Connected to account #{login} on {server}")
        return True

    def get_account_info(self):
        """Get account information"""
        if not self.initialized:
            return None

        account = mt5.account_info()
        if account is None:
            return None

        return {
            'login': account.login,
            'balance': account.balance,
            'equity': account.equity,
            'margin': account.margin,
            'margin_free': account.margin_free,
            'profit': account.profit,
            'leverage': account.leverage,
            'currency': account.currency,
            'server': account.server,
            'company': account.company,
            'mode': 'DEMO' if config.is_demo_mode() else 'LIVE'
        }

    def get_symbol_info(self, symbol):
        """Get symbol information"""
        if not self.initialized:
            return None

        info = mt5.symbol_info(symbol)
        if info is None:
            return None

        return {
            'name': symbol,
            'bid': info.bid,
            'ask': info.ask,
            'spread': info.spread,
            'digits': info.digits,
            'point': info.point,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
            'volume_step': info.volume_step,
            'trade_tick_size': info.trade_tick_size,
            'trade_contract_size': info.trade_contract_size
        }

    def get_current_tick(self, symbol):
        """Get current tick data for symbol"""
        if not self.initialized:
            return None

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None

        return {
            'time': datetime.fromtimestamp(tick.time).strftime('%Y-%m-%d %H:%M:%S'),
            'bid': tick.bid,
            'ask': tick.ask,
            'last': tick.last,
            'volume': tick.volume,
            'spread': (tick.ask - tick.bid)
        }

    def get_bars(self, symbol, timeframe=None, count=None):
        """Get historical bars for symbol"""
        if not self.initialized:
            return None

        # Use config defaults if not provided
        if timeframe is None:
            timeframe = config.get_default_timeframe()
        if count is None:
            count = config.get_chart_bars_count()

        # Map timeframe string to MT5 constant
        timeframe_map = {
            'S2': mt5.TIMEFRAME_M1,  # Use M1 bars for S2, but update every 2 seconds
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1
        }

        tf = timeframe_map.get(timeframe, mt5.TIMEFRAME_M1)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)

        if rates is None:
            return None

        bars = []
        for rate in rates:
            bars.append({
                'time': datetime.fromtimestamp(rate['time']).strftime('%Y-%m-%d %H:%M:%S'),
                'open': rate['open'],
                'high': rate['high'],
                'low': rate['low'],
                'close': rate['close'],
                'volume': rate['tick_volume']
            })

        return bars

    def get_positions(self):
        """Get open positions"""
        if not self.initialized:
            return None

        positions = mt5.positions_get()
        if positions is None:
            return []

        result = []
        for pos in positions:
            result.append({
                'ticket': pos.ticket,
                'time': datetime.fromtimestamp(pos.time).strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'BUY' if pos.type == 0 else 'SELL',
                'symbol': pos.symbol,
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'comment': pos.comment
            })

        return result

    def get_available_symbols(self):
        """Get list of all available symbols"""
        if not self.initialized:
            return []

        symbols = mt5.symbols_get()
        if symbols is None:
            return []

        return [s.name for s in symbols]

    def disconnect(self):
        """Disconnect from MT5"""
        if self.initialized:
            mt5.shutdown()
            self.initialized = False
            print("Disconnected from MT5")


if __name__ == "__main__":
    # Test connection using config file
    print("Testing MT5 Connector with config file...")
    print(f"Environment: {config.get_environment_mode()}")
    print(f"Login: {config.get_mt5_login()}")
    print(f"Server: {config.get_mt5_server()}")
    print()

    connector = MT5Connector()

    if connector.connect_from_config():
        # Get account info
        account = connector.get_account_info()
        print(f"\nAccount Info:")
        print(json.dumps(account, indent=2))

        # Test with default symbol from config
        symbol = config.get_default_symbol()
        print(f"\nTrying to get data for {symbol}...")

        # Get symbol info
        symbol_info = connector.get_symbol_info(symbol)
        if symbol_info:
            print(f"\nSymbol Info:")
            print(json.dumps(symbol_info, indent=2))

            # Get bars
            timeframe = config.get_default_timeframe()
            bars = connector.get_bars(symbol, timeframe, 10)
            if bars:
                print(f"\nLast 10 bars for {symbol} ({timeframe}):")
                for bar in bars[-3:]:  # Show last 3
                    print(f"  {bar['time']}: O={bar['open']}, H={bar['high']}, L={bar['low']}, C={bar['close']}")
        else:
            print(f"Symbol {symbol} not found. Available symbols:")
            symbols = connector.get_available_symbols()
            print(symbols[:20])  # Print first 20 symbols

        connector.disconnect()
