"""
Quick test to verify server can start
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing server startup...\n")

try:
    print("1. Importing modules...")
    from core.config_loader import config
    from core.mt5_connector import MT5Connector
    from core.realtime_server import RealtimeDataServer
    print("   ✓ Imports successful\n")

    print("2. Loading configuration...")
    print(f"   Environment: {config.get_environment_mode()}")
    print(f"   MT5 Login: {config.get_mt5_login()}")
    print(f"   MT5 Server: {config.get_mt5_server()}")
    print(f"   Default Symbol: {config.get_default_symbol()}")
    print("   ✓ Config loaded\n")

    print("3. Testing MT5 connection...")
    connector = MT5Connector()
    if connector.connect_from_config():
        account = connector.get_account_info()
        print(f"   ✓ Connected to account #{account['login']}")
        print(f"   Balance: ${account['balance']}")

        # Test symbol
        symbol = config.get_default_symbol()
        tick = connector.get_current_tick(symbol)
        if tick:
            print(f"   ✓ Symbol '{symbol}' data available")
            print(f"   Current bid: {tick['bid']}")
        else:
            print(f"   ⚠ WARNING: Symbol '{symbol}' not available")

        connector.disconnect()
    else:
        print("   ✗ MT5 connection failed!")
        print("\nPossible issues:")
        print("   - MetaTrader 5 not installed")
        print("   - Wrong credentials in config.json")
        print("   - MT5 terminal is open (close it)")
        sys.exit(1)

    print("\n4. Creating server instance...")
    server = RealtimeDataServer()
    print("   ✓ Server instance created\n")

    print("=" * 60)
    print("✓ All tests passed! Server should start correctly.")
    print("=" * 60)
    print("\nTo start the server, run:")
    print("  python bot.py")
    print("\nOr for debugging:")
    print("  python -u bot.py")

except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nMake sure you're running from the project root directory")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
