# MT5 Real-Time Trading Dashboard

This dashboard connects to your MetaTrader 5 account and displays real-time trading data for PainX and GainX symbols.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Test MT5 Connection

First, make sure MetaTrader 5 is installed and you can login to your demo account.

Test the connection:

```bash
python mt5_connector.py
```

This will connect to the demo account and show available symbols.

### 3. Start the Real-Time Server

```bash
python realtime_server.py
```

The server will:
- Connect to your MT5 demo account
- Start streaming real-time data
- Run a WebSocket server on `ws://localhost:8765`

### 4. Open the Dashboard

Simply open `realtime_dashboard.html` in your web browser (Chrome, Firefox, or Edge).

The dashboard will automatically connect to the server and start displaying:
- Real-time bid/ask prices
- Live price charts
- Account balance and equity
- Current profit/loss
- Open positions

## Features

- **Real-Time Price Updates**: See live bid/ask prices updating every second
- **Interactive Charts**: View historical candlestick data for any timeframe
- **Symbol Switching**: Choose between PainX400/600/800/999 and GainX400/600/800/999
- **Timeframe Selection**: View data in M1, M5, M15, M30, H1, H4, or D1
- **Account Monitoring**: Track your balance, equity, and profit in real-time
- **Position Tracking**: See all open positions with their current profit/loss

## Usage

1. Select a symbol from the dropdown (e.g., PainX400)
2. Select a timeframe (e.g., M1 for 1-minute candles)
3. Watch the data update in real-time

The dashboard will automatically reconnect if the connection is lost.

## Troubleshooting

### "Symbol not found" error

If you see this error, the symbol might not be available on your broker. Try:
1. Opening MetaTrader 5
2. Going to View → Market Watch
3. Right-click → Show All
4. Search for the symbol (PainX400, GainX400, etc.)
5. If not found, check with your broker about symbol names

### Connection fails

Make sure:
1. MetaTrader 5 is installed
2. The account credentials in `realtime_server.py` are correct
3. No firewall is blocking the WebSocket connection
4. The MT5 terminal is closed (the Python script will connect directly)

## Files

- `mt5_connector.py` - MT5 connection and data fetching
- `realtime_server.py` - WebSocket server for streaming data
- `realtime_dashboard.html` - Web-based dashboard UI
- `requirements.txt` - Python dependencies
