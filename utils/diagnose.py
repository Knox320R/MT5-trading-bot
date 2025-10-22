"""
Diagnostic script to check if everything is set up correctly
"""
import os
import sys
import json

print("="*70)
print(" MT5 Trading Bot - Diagnostic Tool")
print("="*70)
print()

# Check 1: Python version
print("1. Checking Python version...")
print(f"   Python version: {sys.version}")
if sys.version_info < (3, 7):
    print("   ❌ ERROR: Python 3.7+ required")
else:
    print("   ✓ OK")
print()

# Check 2: Required files
print("2. Checking required files...")
required_files = [
    'config.json',
    'config_loader.py',
    'mt5_connector.py',
    'realtime_server.py',
    'interface/index.html',
    'interface/style.css',
    'interface/dashboard.js'
]

all_files_exist = True
for file in required_files:
    if os.path.exists(file):
        print(f"   ✓ {file}")
    else:
        print(f"   ❌ MISSING: {file}")
        all_files_exist = False

if all_files_exist:
    print("   ✓ All files present")
else:
    print("   ❌ Some files are missing!")
print()

# Check 3: Required packages
print("3. Checking required packages...")
packages = {
    'MetaTrader5': 'MetaTrader5',
    'websockets': 'websockets',
    'asyncio': 'asyncio'
}

all_packages_installed = True
for package_import, package_name in packages.items():
    try:
        __import__(package_import)
        print(f"   ✓ {package_name}")
    except ImportError:
        print(f"   ❌ MISSING: {package_name}")
        all_packages_installed = False

if all_packages_installed:
    print("   ✓ All packages installed")
else:
    print("   ❌ Run: pip install -r requirements.txt")
print()

# Check 4: Config file
print("4. Checking config.json...")
try:
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Check essential fields
    checks = [
        ('environment.mode', ['environment', 'mode']),
        ('mt5_account.demo.login', ['mt5_account', 'demo', 'login']),
        ('mt5_account.demo.server', ['mt5_account', 'demo', 'server']),
        ('server.ports', ['server', 'ports']),
    ]

    for name, path in checks:
        value = config
        try:
            for key in path:
                value = value[key]
            print(f"   ✓ {name}: {value}")
        except KeyError:
            print(f"   ❌ MISSING: {name}")

    print("   ✓ Config file valid")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
print()

# Check 5: MT5 Connection
print("5. Testing MT5 connection...")
try:
    from core.config_loader import config
    from core.mt5_connector import MT5Connector

    connector = MT5Connector()
    if connector.connect_from_config():
        account = connector.get_account_info()
        print(f"   ✓ Connected to MT5")
        print(f"   ✓ Account: #{account['login']}")
        print(f"   ✓ Balance: ${account['balance']}")
        print(f"   ✓ Server: {account['server']}")

        # Test symbol
        symbol = config.get_default_symbol()
        tick = connector.get_current_tick(symbol)
        if tick:
            print(f"   ✓ Symbol '{symbol}' accessible")
            print(f"   ✓ Current bid: {tick['bid']}")
        else:
            print(f"   ⚠ WARNING: Symbol '{symbol}' not available")

        connector.disconnect()
    else:
        print("   ❌ Could not connect to MT5")
        print("   → Check if MT5 terminal is closed")
        print("   → Verify credentials in config.json")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
print()

# Check 6: Port availability
print("6. Checking port availability...")
import socket

ports_to_check = [8765, 8766, 8767, 8768, 8769]
available_ports = []

for port in ports_to_check:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()

    if result != 0:
        print(f"   ✓ Port {port} available")
        available_ports.append(port)
    else:
        print(f"   ⚠ Port {port} in use")

if available_ports:
    print(f"   ✓ {len(available_ports)} port(s) available")
else:
    print("   ❌ All ports in use! Run kill_server.bat")
print()

# Summary
print("="*70)
print(" SUMMARY")
print("="*70)

if all_files_exist and all_packages_installed and len(available_ports) > 0:
    print("✓ System is ready!")
    print()
    print("To start the dashboard:")
    print("  1. Run: python realtime_server.py")
    print("  2. Browser will open automatically")
    print("  3. Dashboard should connect and show data")
else:
    print("❌ Issues detected. Please fix the errors above.")
    print()
    print("Common fixes:")
    print("  - Install packages: pip install -r requirements.txt")
    print("  - Kill stuck processes: kill_server.bat")
    print("  - Check config.json has correct credentials")
    print("  - Make sure MT5 is installed")

print("="*70)
