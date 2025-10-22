# MT5 Real-Time Trading Bot

A professional automated trading bot for MetaTrader 5 with real-time dashboard visualization.

## Features

- ✅ **Real-time MT5 data streaming** (updates every 1 second)
- ✅ **Beautiful web dashboard** with live charts
- ✅ **Centralized configuration** via JSON
- ✅ **Multi-symbol support** (PainX/GainX 400/600/800/999)
- ✅ **Multiple timeframe analysis** (M1, M5, M15, M30, H1, H4, D1)
- ✅ **Account monitoring** (Balance, Equity, Profit/Loss)
- ✅ **Position tracking** with real-time P&L
- ✅ **Auto-reconnect** on disconnection
- ✅ **Demo and Live account support**

## Project Structure

```
trading-bot/
├── bot.py                  # Main entry point - START HERE
├── config.json             # Centralized configuration file
├── core/                   # Core modules
│   ├── config_loader.py    # Configuration management
│   ├── mt5_connector.py    # MT5 connection and data fetching
│   └── realtime_server.py  # WebSocket server for dashboard
├── interface/              # Web dashboard
│   ├── index.html          # Dashboard HTML
│   ├── style.css           # Dashboard styles
│   └── dashboard.js        # Dashboard JavaScript
├── utils/                  # Utility scripts
│   └── diagnose.py         # Diagnostic tool
└── TROUBLESHOOTING.md      # Troubleshooting guide
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Bot

```bash
python bot.py
```

The bot will:
- Connect to your MT5 account
- Start the WebSocket server
- Open the dashboard in your browser automatically
- Begin streaming real-time data

## Command Line Options

```bash
python bot.py                  # Start normally
python bot.py --no-browser     # Don't open browser
python bot.py --port 8766      # Use specific port
python bot.py --test-connection # Test MT5 connection only
python bot.py --help           # Show all options
```

## Configuration

All settings are in `config.json`:

- **Environment**: Demo/Live mode
- **MT5 Account**: Credentials and server
- **Trading**: Symbols, timeframes, lot sizes
- **Server**: Ports, update interval (default: 1 second)
- **Risk Management**: Daily stops, targets
- **Strategy**: Pain/Gain trading parameters

## Troubleshooting

Run diagnostic tool:
```bash
python utils/diagnose.py
```

Or see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed help.

---

**⚠️ Trading Warning**: Automated trading involves risk. Test in demo mode first.
