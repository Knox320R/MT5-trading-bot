import json
import os
from typing import Dict, Any, Optional

class Config:
    """Centralized configuration manager for the trading bot"""

    _instance = None
    _config_data = None
    _config_file = "config.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config_data is None:
            self.load_config()

    def load_config(self, config_file: Optional[str] = None):
        """Load configuration from JSON file"""
        if config_file:
            self._config_file = config_file

        # Look for config in parent directory (project root)
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self._config_file)

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            self._config_data = json.load(f)

        print(f"Configuration loaded from {config_path}")

    def save_config(self, config_file: Optional[str] = None):
        """Save current configuration to JSON file"""
        if config_file:
            self._config_file = config_file

        # Save to parent directory (project root)
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self._config_file)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config_data, f, indent=2)

        print(f"Configuration saved to {config_path}")

    def get(self, *keys, default=None) -> Any:
        """
        Get configuration value using dot notation or multiple keys.

        Usage:
            config.get('environment', 'timezone', default='America/Bogota')
            config.get('trading', 'lot_size', default=0.10)

        Note: default must be passed as keyword argument, not positional.
        """
        data = self._config_data

        for key in keys:
            # Validate that key is hashable (string or int)
            if not isinstance(key, (str, int)):
                raise TypeError(
                    f"Config keys must be strings or integers, got {type(key).__name__}. "
                    f"If you meant to pass a default value, use default=... as keyword argument."
                )

            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default

        return data

    def set(self, *keys, value):
        """Set configuration value using multiple keys"""
        if len(keys) == 0:
            raise ValueError("At least one key is required")

        data = self._config_data

        for key in keys[:-1]:
            if key not in data:
                data[key] = {}
            data = data[key]

        data[keys[-1]] = value

    # Environment settings
    def get_environment_mode(self) -> str:
        """Get current environment mode (demo/live)"""
        return self.get('environment', 'mode', default='demo')

    def is_demo_mode(self) -> bool:
        """Check if running in demo mode"""
        return self.get_environment_mode() == 'demo'

    def is_live_mode(self) -> bool:
        """Check if running in live mode"""
        return self.get_environment_mode() == 'live'

    # MT5 Account settings
    def get_mt5_credentials(self) -> Dict[str, Any]:
        """Get MT5 account credentials based on current environment"""
        mode = self.get_environment_mode()
        return self.get('mt5_account', mode, default={})

    def get_mt5_login(self) -> int:
        """Get MT5 account login"""
        return self.get_mt5_credentials().get('login')

    def get_mt5_password(self) -> str:
        """Get MT5 account password"""
        return self.get_mt5_credentials().get('password')

    def get_mt5_server(self) -> str:
        """Get MT5 server name"""
        return self.get_mt5_credentials().get('server')

    # Symbol settings
    def get_all_symbols(self) -> list:
        """Get all trading symbols"""
        symbols = []
        symbols.extend(self.get('symbols', 'pain', default=[]))
        symbols.extend(self.get('symbols', 'gain', default=[]))
        symbols.extend(self.get('symbols', 'other', default=[]))
        return symbols

    def get_pain_symbols(self) -> list:
        """Get PainX symbols"""
        return self.get('symbols', 'pain', default=[])

    def get_gain_symbols(self) -> list:
        """Get GainX symbols"""
        return self.get('symbols', 'gain', default=[])

    def is_pain_symbol(self, symbol: str) -> bool:
        """Check if symbol is a PAIN symbol"""
        return symbol in self.get_pain_symbols()

    def is_gain_symbol(self, symbol: str) -> bool:
        """Check if symbol is a GAIN symbol"""
        return symbol in self.get_gain_symbols()

    def get_default_symbol(self) -> str:
        """Get default trading symbol"""
        return self.get('trading', 'default_symbol', default='PainX 400')

    def get_default_timeframe(self) -> str:
        """Get default timeframe"""
        return self.get('trading', 'default_timeframe', default='M1')

    def get_timeframes(self) -> list:
        """Get all available timeframes"""
        return self.get('trading', 'timeframes', default=['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'])

    # Trading settings
    def get_lot_size(self) -> float:
        """Get default lot size"""
        return self.get('trading', 'lot_size', default=0.10)

    def get_max_lot_size(self) -> float:
        """Get maximum lot size"""
        return self.get('trading', 'max_lot_size', default=1.0)

    def get_min_lot_size(self) -> float:
        """Get minimum lot size"""
        return self.get('trading', 'min_lot_size', default=0.01)

    def get_daily_target_usd(self) -> float:
        """Get daily profit target in USD"""
        return self.get('trading', 'daily_target_usd', default=100.0)

    def get_daily_stop_usd(self) -> float:
        """Get daily stop loss in USD"""
        return self.get('trading', 'daily_stop_usd', default=40.0)

    def get_max_concurrent_orders(self) -> int:
        """Get maximum concurrent orders"""
        return self.get('trading', 'max_concurrent_orders', default=3)

    # Server settings
    def get_server_host(self) -> str:
        """Get WebSocket server host"""
        return self.get('server', 'host', default='127.0.0.1')

    def get_server_ports(self) -> list:
        """Get list of ports to try"""
        return self.get('server', 'ports', default=[8765, 8766, 8767, 8768, 8769])

    def get_auto_open_browser(self) -> bool:
        """Check if browser should auto-open"""
        return self.get('server', 'auto_open_browser', default=True)

    def get_update_interval(self) -> int:
        """Get data update interval in seconds"""
        return self.get('server', 'update_interval_seconds', default=1)

    # Strategy settings
    def is_strategy_enabled(self, strategy_name: str) -> bool:
        """Check if a strategy is enabled"""
        return self.get('strategy', strategy_name, 'enabled', default=False)

    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Get complete strategy configuration"""
        return self.get('strategy', strategy_name, default={})

    # Risk management
    def is_daily_stop_enabled(self) -> bool:
        """Check if daily stop is enabled"""
        return self.get('risk_management', 'enable_daily_stop', default=True)

    def is_daily_target_enabled(self) -> bool:
        """Check if daily target is enabled"""
        return self.get('risk_management', 'enable_daily_target', default=True)

    # Logging settings
    def is_logging_enabled(self) -> bool:
        """Check if logging is enabled"""
        return self.get('logging', 'enabled', default=True)

    def get_log_level(self) -> str:
        """Get logging level"""
        return self.get('logging', 'level', default='INFO')

    def get_log_directory(self) -> str:
        """Get log directory path"""
        return self.get('logging', 'log_directory', default='logs')

    # Indicator settings (User-configurable)
    def get_ema_smoothing(self) -> float:
        """
        Get EMA smoothing factor from config.json.

        Default: 2.0 (standard smoothing factor per EMA.txt)

        This value is used in the EMA formula:
        EMA_today = (Value_today * (Smoothing / (1 + Days))) + EMA_yesterday * (1 - (Smoothing / (1 + Days)))
        where k = Smoothing / (1 + Days)

        Higher smoothing values give MORE weight to recent data:
        - Smoothing = 2: Standard (recommended per EMA.txt)
        - Smoothing = 3: More responsive to price changes
        - Smoothing = 1: Less responsive to price changes

        Config location: indicators.ema_formula.smoothing

        Returns:
            EMA smoothing factor (typically 1.0 to 3.0)
        """
        return float(self.get('indicators', 'ema_formula', 'smoothing', default=2.0))

    def get_snake_period(self) -> int:
        """
        Get Snake (EMA) period from config.json.

        Default: 100 (commonly used for long-term trend identification)

        This is the "Days" parameter in the EMA formula:
        EMA_today = (Value_today * (Smoothing / (1 + Days))) + EMA_yesterday * (1 - (Smoothing / (1 + Days)))

        Config location: indicators.snake.period

        Returns:
            Snake EMA period (recommended: 50, 100, or 200)
        """
        return self.get('indicators', 'snake', 'period', default=100)

    def get_snake_type(self) -> str:
        """Get Snake indicator type"""
        return self.get('indicators', 'snake', 'type', default='EMA')

    def get_purple_line_period(self) -> int:
        """
        Get Purple Line (EMA) period from config.json.

        Default: 10 (commonly used for short-term entry signals)

        This is the "Days" parameter in the EMA formula:
        EMA_today = (Value_today * (Smoothing / (1 + Days))) + EMA_yesterday * (1 - (Smoothing / (1 + Days)))

        Config location: indicators.purple_line.period

        Returns:
            Purple Line EMA period (recommended: 8, 10, 12, or 20)
        """
        return self.get('indicators', 'purple_line', 'period', default=10)

    def get_purple_line_type(self) -> str:
        """Get Purple Line indicator type"""
        return self.get('indicators', 'purple_line', 'type', default='EMA')

    def get_rsi_period(self) -> int:
        """Get RSI period"""
        return self.get('indicators', 'rsi', 'period', default=14)

    # Dashboard settings
    def get_dashboard_title(self) -> str:
        """Get dashboard title"""
        return self.get('dashboard', 'title', default='MT5 Real-Time Trading Dashboard')

    def get_chart_bars_count(self) -> int:
        """Get number of bars to display on chart"""
        return self.get('dashboard', 'chart_bars_count', default=100)

    # Notifications
    def is_desktop_notifications_enabled(self) -> bool:
        """Check if desktop notifications are enabled"""
        return self.get('notifications', 'desktop', 'enabled', default=True)

    # Helper method to get entire config
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration"""
        return self._config_data.copy()

    def reload(self):
        """Reload configuration from file"""
        self.load_config()

    # Bot Engine specific methods
    def get_bot_engine_enabled_bots(self):
        """Get list of enabled bot names"""
        bots = self.get('bot_engine', 'bots', default={})
        return [bot_name for bot_name, bot_config in bots.items() if bot_config.get('enabled', True)]

    def get_daily_bias_small_body_rule(self):
        """Get small body rule"""
        return self.get('daily_bias', 'small_body_rule', default='longest_wick_gt_body')

    def get_daily_bias_epsilon(self):
        """Get epsilon for wick ratio"""
        return self.get('daily_bias', 'epsilon_wick_ratio', default=0.05)

    def get_trend_filter_timeframes(self):
        """Get timeframes to check for trend alignment"""
        return self.get('trend_filters', 'timeframes_to_check', default=['H1', 'M30', 'M15'])

    def get_equality_is_not_trend(self):
        """Check if equality should be treated as not trend"""
        return self.get('trend_filters', 'equality_is_not_trend', default=True)

    def get_h4_candidates(self):
        """Get number of H4 candles to check"""
        return self.get('structure_checks', 'h4_candidates', default=3)

    def get_max_bars_between_cross_and_touch(self):
        """Get max bars allowed between cross and touch"""
        return self.get('entry_m1', 'max_bars_between_cross_and_touch', default=20)

    def get_early_exit_on_m5_purple_break(self):
        """Check if M5 purple break early exit is enabled"""
        return self.get('exits', 'early_exit_on_m5_purple_break', default=True)

    def get_pain_sell_50pct_wick_stop(self):
        """Check if PAIN SELL 50% wick stop is enabled"""
        return self.get('day_stops', 'pain_sell_50pct_wick_stop', default=True)

    def get_max_concurrent_orders(self):
        """Get maximum concurrent orders allowed"""
        return self.get('trading', 'max_concurrent_orders', default=3)

    def get_trade_target_usd(self):
        """Get fixed profit target in USD"""
        return self.get('trading', 'trade_target_usd', default=2.0)

    def get_max_spread_pips(self):
        """Get maximum allowed spread in pips"""
        return self.get('trading', 'max_spread_pips', default=2.0)

    def get_max_slippage_pips(self):
        """Get maximum allowed slippage in pips"""
        return self.get('trading', 'max_slippage_pips', default=2.0)

    def get_trading_hours(self):
        """Get trading hours"""
        return self.get('session', 'trading_hours', default={'start': '19:00', 'end': '06:00'})

    def get_session_enabled(self):
        """Check if session time filter is enabled"""
        return self.get('session', 'enabled', default=True)

    def get_environment_timezone(self):
        """Get environment timezone"""
        return self.get('environment', 'timezone', default='America/Bogota')


# Create a global instance
config = Config()


if __name__ == "__main__":
    # Test configuration loading
    print("Testing configuration loader...")
    print(f"Environment mode: {config.get_environment_mode()}")
    print(f"Is demo mode: {config.is_demo_mode()}")
    print(f"MT5 Login: {config.get_mt5_login()}")
    print(f"MT5 Server: {config.get_mt5_server()}")
    print(f"Default Symbol: {config.get_default_symbol()}")
    print(f"Default Timeframe: {config.get_default_timeframe()}")
    print(f"All Symbols: {config.get_all_symbols()}")
    print(f"Lot Size: {config.get_lot_size()}")
    print(f"Daily Target: ${config.get_daily_target_usd()}")
    print(f"Daily Stop: ${config.get_daily_stop_usd()}")
    print(f"Server Host: {config.get_server_host()}")
    print(f"Server Ports: {config.get_server_ports()}")
    print(f"Auto open browser: {config.get_auto_open_browser()}")
