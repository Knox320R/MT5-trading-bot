#!/usr/bin/env python3
"""
MT5 Trading Bot - Main Entry Point

This is the main script to start the trading bot.
It handles:
- Configuration loading
- MT5 connection
- WebSocket server for real-time dashboard
- Data streaming

Usage:
    python bot.py              # Start with default config
    python bot.py --no-browser # Start without opening browser
    python bot.py --port 8765  # Start on specific port
"""

import asyncio
import argparse
import sys
from core.realtime_server import RealtimeDataServer
from core.config_loader import config

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='MT5 Real-Time Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bot.py                    Start bot with auto-open browser
  python bot.py --no-browser       Start bot without opening browser
  python bot.py --port 8766        Start on port 8766
  python bot.py --config my.json   Use custom config file
        """
    )

    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not open browser automatically'
    )

    parser.add_argument(
        '--port',
        type=int,
        help='WebSocket server port (default: from config)'
    )

    parser.add_argument(
        '--host',
        type=str,
        help='WebSocket server host (default: from config)'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to config file (default: config.json)'
    )

    parser.add_argument(
        '--test-connection',
        action='store_true',
        help='Test MT5 connection and exit'
    )

    return parser.parse_args()

def print_banner():
    """Print startup banner"""
    print("=" * 70)
    print("  MT5 Real-Time Trading Bot".center(70))
    print("=" * 70)

def print_config_info():
    """Print configuration information"""
    print(f"Configuration:")
    print(f"  Environment:       {config.get_environment_mode().upper()}")
    print(f"  MT5 Account:       {config.get_mt5_login()}")
    print(f"  MT5 Server:        {config.get_mt5_server()}")
    print(f"  Default Symbol:    {config.get_default_symbol()}")
    print(f"  Default Timeframe: {config.get_default_timeframe()}")
    print(f"  Update Interval:   {config.get_update_interval()}s")
    print("=" * 70)

def test_mt5_connection():
    """Test MT5 connection"""
    from core.mt5_connector import MT5Connector

    print("\nTesting MT5 connection...")
    connector = MT5Connector()

    if connector.connect_from_config():
        account = connector.get_account_info()
        print(f"✓ Connected successfully!")
        print(f"  Account: #{account['login']}")
        print(f"  Balance: ${account['balance']}")
        print(f"  Equity:  ${account['equity']}")
        print(f"  Server:  {account['server']}")

        # Test symbol access
        symbol = config.get_default_symbol()
        tick = connector.get_current_tick(symbol)
        if tick:
            print(f"\n✓ Symbol '{symbol}' accessible")
            print(f"  Bid: {tick['bid']}")
            print(f"  Ask: {tick['ask']}")
        else:
            print(f"\n⚠ WARNING: Symbol '{symbol}' not available")

        connector.disconnect()
        return True
    else:
        print("✗ Connection failed!")
        print("\nPossible issues:")
        print("  - MetaTrader 5 is not installed")
        print("  - Wrong credentials in config.json")
        print("  - MT5 terminal is already open (close it)")
        print("  - Server name is incorrect")
        return False

async def start_bot(args):
    """Start the bot"""
    try:
        # Create server instance
        server = RealtimeDataServer()

        # Determine parameters
        host = args.host if args.host else None
        port = args.port if args.port else None
        open_browser = not args.no_browser

        # Start server
        await server.start(
            host=host,
            port=port,
            open_browser=open_browser
        )

    except KeyboardInterrupt:
        print("\n\nBot stopped by user")
    except Exception as e:
        print(f"\n✗ Error starting bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main entry point"""
    args = parse_arguments()

    # Load custom config if specified
    if args.config:
        config.load_config(args.config)

    # Print banner
    print_banner()

    # Test connection mode
    if args.test_connection:
        success = test_mt5_connection()
        sys.exit(0 if success else 1)

    # Print configuration
    print_config_info()
    print()

    # Try different ports if configured port is in use
    ports_to_try = config.get_server_ports() if not args.port else [args.port]

    for port in ports_to_try:
        try:
            print(f"Starting server on port {port}...")
            args.port = port
            asyncio.run(start_bot(args))
            break
        except OSError as e:
            if e.errno == 10048:  # Port in use
                if port == ports_to_try[-1]:  # Last port
                    print(f"\n✗ All ports in use!")
                    print(f"Run 'kill_server.bat' to free up ports")
                    sys.exit(1)
                else:
                    print(f"Port {port} in use, trying next port...")
                    continue
            else:
                raise
        except KeyboardInterrupt:
            print("\n\nBot stopped by user")
            break

if __name__ == "__main__":
    main()
