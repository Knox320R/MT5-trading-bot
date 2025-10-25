# Configuration Documentation (config.json)

**Last Updated**: 2025-10-25

This document provides detailed explanations for every configuration item in `config.json`.

---

## Table of Contents

1. [Environment Settings](#environment-settings)
2. [MT5 Connection](#mt5-connection)
3. [Symbol Configuration](#symbol-configuration)
4. [Trading Parameters](#trading-parameters)
5. [Risk Management](#risk-management)
6. [Indicators](#indicators)
7. [Entry Conditions](#entry-conditions)
8. [Exit Conditions](#exit-conditions)
9. [Daily Bias](#daily-bias)
10. [Server Settings](#server-settings)
11. [Backtesting](#backtesting)

---

## Environment Settings

### `environment.mode`
- **Type**: String
- **Values**: `"DEMO"` or `"LIVE"`
- **Purpose**: Determines which MT5 account to use
- **Used In**: `core/config_loader.py`, `core/realtime_server.py`
- **How It Works**:
  - `"DEMO"`: Uses demo account credentials (safe for testing)
  - `"LIVE"`: Uses live account credentials (real money)
- **⚠️ WARNING**: Always test thoroughly on DEMO before switching to LIVE
- **Example**:
  ```json
  "mode": "DEMO"
  ```

### `environment.timezone`
- **Type**: String
- **Values**: Any valid timezone (e.g., `"Europe/London"`, `"America/New_York"`)
- **Purpose**: Sets the timezone for daily calculations and logs
- **Used In**: `core/timezone_handler.py`, daily bias calculations
- **How It Works**:
  - All times are converted to this timezone
  - Daily reset happens at 16:00 in this timezone
  - Yesterday's candle is calculated based on this timezone
- **Example**:
  ```json
  "timezone": "Europe/London"
  ```

---

## MT5 Connection

### `mt5.demo_account` / `mt5.live_account`
Each account has 3 required fields:

#### `login`
- **Type**: Integer
- **Purpose**: Your MT5 account number
- **Used In**: `core/mt5_connector.py` connection
- **How To Find**:
  1. Open MT5 terminal
  2. Click "File" → "Login to Trade Account"
  3. Your login number is shown
- **Example**:
  ```json
  "login": 19498321
  ```

#### `password`
- **Type**: String
- **Purpose**: Your MT5 account password
- **Used In**: `core/mt5_connector.py` connection
- **Security**:
  - ⚠️ Keep this file secure (don't share publicly)
  - Consider using environment variables for production
- **Example**:
  ```json
  "password": "YourPassword123"
  ```

#### `server`
- **Type**: String
- **Purpose**: MT5 broker server name
- **Used In**: `core/mt5_connector.py` connection
- **How To Find**:
  1. Open MT5 terminal
  2. Check top-left corner or Account Info
  3. Server name is shown (e.g., "Weltrade-Demo")
- **Example**:
  ```json
  "server": "Weltrade-Demo"
  ```

---

## Symbol Configuration

### `symbols.default_symbol`
- **Type**: String
- **Purpose**: The symbol loaded when dashboard starts
- **Used In**: `core/realtime_server.py` initial chart display
- **Must Be**: One of the symbols in `all_symbols` list
- **Example**:
  ```json
  "default_symbol": "PainX 400"
  ```

### `symbols.all_symbols`
- **Type**: Array of strings
- **Purpose**: All symbols available in the dashboard dropdown
- **Used In**:
  - `interface/js/ui.js` (symbol dropdown)
  - `core/bot_engine.py` (multi-symbol scanning)
- **How It Works**: Bot checks ALL these symbols for trading opportunities
- **Example**:
  ```json
  "all_symbols": ["PainX 400", "PainX 600", "GainX 400"]
  ```

### `symbols.pain_symbols`
- **Type**: Array of strings
- **Purpose**: Symbols designated for PAIN strategy bots
- **Used In**: `core/bot_engine.py` strategy assignment
- **How It Works**:
  - These symbols use PAIN BUY and PAIN SELL bots
  - Must be subset of `all_symbols`
- **Strategy**: PAIN bots trade against daily bias
- **Example**:
  ```json
  "pain_symbols": ["PainX 400", "PainX 600"]
  ```

### `symbols.gain_symbols`
- **Type**: Array of strings
- **Purpose**: Symbols designated for GAIN strategy bots
- **Used In**: `core/bot_engine.py` strategy assignment
- **How It Works**:
  - These symbols use GAIN BUY and GAIN SELL bots
  - Must be subset of `all_symbols`
- **Strategy**: GAIN bots trade with daily bias
- **Example**:
  ```json
  "gain_symbols": ["GainX 400", "GainX 600"]
  ```

---

## Trading Parameters

### `trading.default_timeframe`
- **Type**: String
- **Values**: `"M1"`, `"M5"`, `"M15"`, `"M30"`, `"H1"`, `"H4"`, `"D1"`
- **Purpose**: Default timeframe for charts and entry scanning
- **Used In**:
  - `core/realtime_server.py` (chart display)
  - `core/bot_engine.py` (M1 entry scanning)
- **Note**: M1 is used for actual entry decisions regardless of this setting
- **Example**:
  ```json
  "default_timeframe": "M1"
  ```

### `trading.timeframes`
- **Type**: Array of strings
- **Purpose**: All timeframes available in dashboard dropdown
- **Used In**: `interface/js/ui.js` (timeframe dropdown)
- **Available Values**: `["M1", "M5", "M15", "M30", "H1", "H4", "D1"]`
- **Example**:
  ```json
  "timeframes": ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
  ```

### `trading.default_volume`
- **Type**: Float
- **Purpose**: Position size in lots for each trade
- **Used In**: `core/order_manager.py` when placing orders
- **How It Works**:
  - Standard lot = 100,000 units of base currency
  - 0.01 lot = 1,000 units (micro lot)
  - Minimum usually 0.01 (check your broker)
- **Risk**: Larger volume = more profit/loss per pip
- **Example**:
  ```json
  "default_volume": 0.01
  ```

### `trading.max_spread`
- **Type**: Float
- **Purpose**: Maximum spread allowed for trade entry (in points)
- **Used In**: `core/risk_manager.py` spread gate check
- **How It Works**:
  - Spread = Ask - Bid
  - If spread > max_spread, order is rejected
  - Prevents trading during high volatility/low liquidity
- **Typical Values**:
  - Forex majors: 1-5 points
  - Exotic pairs: 10-50 points
  - Check your broker's typical spreads
- **Example**:
  ```json
  "max_spread": 50.0
  ```

### `trading.slippage`
- **Type**: Integer
- **Purpose**: Maximum price deviation allowed when executing orders (in points)
- **Used In**: `core/order_manager.py` order execution
- **How It Works**:
  - Price can move between order request and execution
  - If slippage exceeds this value, order is rejected
  - Higher value = more likely to execute but at worse price
- **Typical Values**: 10-50 points
- **Example**:
  ```json
  "slippage": 10
  ```

### `trading.magic_number`
- **Type**: Integer
- **Purpose**: Unique identifier for orders placed by this bot
- **Used In**: `core/order_manager.py` order placement
- **How It Works**:
  - All orders have this magic number attached
  - Used to distinguish bot orders from manual orders
  - Multiple bots can use different magic numbers
- **Must Be**: Unique number (avoid common numbers like 12345)
- **Example**:
  ```json
  "magic_number": 202510251
  ```

---

## Risk Management

### `risk.max_daily_loss`
- **Type**: Float
- **Purpose**: Maximum loss allowed per day in USD
- **Used In**: `core/risk_manager.py` daily loss gate
- **How It Works**:
  - Tracks total P/L since daily reset (16:00)
  - If loss exceeds this value, all trading stops until next day
  - Resets at 16:00 timezone time
- **⚠️ CRITICAL**: This protects your account from catastrophic losses
- **Recommendation**: Set to 2-5% of account balance
- **Example**:
  ```json
  "max_daily_loss": 100.0
  ```
  *Stops trading if you lose $100 in one day*

### `risk.max_concurrent_orders`
- **Type**: Integer
- **Purpose**: Maximum consecutive orders in a row per bot per symbol
- **Used In**: `core/risk_manager.py` consecutive orders gate
- **How It Works**:
  - Counter increments each time a bot places an order
  - Counter resets when:
    - A profitable trade closes (breaks losing streak)
    - Daily reset at 16:00
  - If counter reaches max, that bot stops trading that symbol
- **⚠️ IMPORTANT**: This is NOT "max positions at once"
- **Example Scenario**:
  ```json
  "max_concurrent_orders": 3
  ```
  - PAIN BUY places order #1 → Counter = 1
  - Order #1 closes at loss → Counter = 1 (still)
  - PAIN BUY places order #2 → Counter = 2
  - Order #2 closes at loss → Counter = 2 (still)
  - PAIN BUY places order #3 → Counter = 3 (LIMIT REACHED)
  - PAIN BUY blocked until profit or daily reset
  - Order #3 closes at profit → Counter = 0 (RESET)

### `risk.max_positions_per_symbol`
- **Type**: Integer
- **Purpose**: Maximum open positions allowed per symbol at the same time
- **Used In**: `core/risk_manager.py` position count gate
- **How It Works**:
  - Counts current open positions for the symbol
  - If count >= max, new orders are rejected
  - Prevents over-exposure to one symbol
- **Note**: This is total across all bots
- **Example**:
  ```json
  "max_positions_per_symbol": 1
  ```
  *Only one position allowed on PainX 400 at a time*

### `risk.min_free_margin`
- **Type**: Float
- **Purpose**: Minimum free margin required to place new orders (in USD)
- **Used In**: `core/risk_manager.py` margin gate
- **How It Works**:
  - Free Margin = Equity - Used Margin
  - If free margin < this value, orders are rejected
  - Prevents margin calls
- **Recommendation**: At least $100-500 for micro accounts
- **Example**:
  ```json
  "min_free_margin": 100.0
  ```

---

## Indicators

### `indicators.snake`
- **Purpose**: Primary trend indicator (EMA 100)
- **🔒 TEMPLATE-LOCKED**: Period cannot be changed

#### `period`
- **Type**: Integer
- **Value**: `100` (LOCKED)
- **Purpose**: EMA calculation period
- **Used In**: `core/indicator_calculator.py`
- **How It Works**: EMA of last 100 closes
- **⚠️ DO NOT CHANGE**: This is enforced at code level

#### `type`
- **Type**: String
- **Value**: `"EMA"`
- **Purpose**: Indicator type

#### `locked`
- **Type**: Boolean
- **Value**: `true`
- **Purpose**: Indicates this value is template-locked

### `indicators.purple_line`
- **Purpose**: Entry signal indicator (EMA 10)
- **🔒 TEMPLATE-LOCKED**: Period cannot be changed

#### `period`
- **Type**: Integer
- **Value**: `10` (LOCKED)
- **Purpose**: EMA calculation period
- **Used In**: `core/indicator_calculator.py`
- **How It Works**: EMA of last 10 closes
- **⚠️ DO NOT CHANGE**: This is enforced at code level

---

## Entry Conditions

### `entry_conditions.h4_candidates`
- **Purpose**: H4 candle pattern requirements for entry eligibility

#### `min_body_percent`
- **Type**: Float (0.0 to 1.0)
- **Purpose**: Minimum body size as percentage of total candle range
- **Used In**: `core/candidate_checker.py`
- **How It Works**:
  - Body % = |Close - Open| / (High - Low)
  - If body % < this value, H4 candle is rejected
  - Filters out doji/indecision candles
- **Range**: 0.0 (no filter) to 1.0 (full body only)
- **Example**:
  ```json
  "min_body_percent": 0.3
  ```
  *Body must be at least 30% of total candle range*

#### `max_wick_percent`
- **Type**: Float (0.0 to 1.0)
- **Purpose**: Maximum wick size as percentage of total candle range
- **Used In**: `core/candidate_checker.py`
- **How It Works**:
  - Top Wick % = (High - max(Open,Close)) / (High - Low)
  - Bottom Wick % = (min(Open,Close) - Low) / (High - Low)
  - If either wick % > this value, candle is rejected
  - Filters out candles with long wicks (rejection)
- **Range**: 0.0 (no wicks) to 1.0 (full wick allowed)
- **Example**:
  ```json
  "max_wick_percent": 0.4
  ```
  *Wicks cannot exceed 40% of total candle range*

#### `lookback_candles`
- **Type**: Integer
- **Purpose**: How many recent H4 candles to check for candidates
- **Used In**: `core/candidate_checker.py`
- **How It Works**:
  - Checks last N H4 candles
  - Uses most recent valid candidate
  - Larger value = older candles allowed
- **Typical Range**: 3-10 candles
- **Example**:
  ```json
  "lookback_candles": 5
  ```
  *Check last 5 H4 candles for valid candidates*

### `entry_conditions.m1_entry`
- **Purpose**: M1 candle requirements for actual trade entry

#### `min_body_pips`
- **Type**: Float
- **Purpose**: Minimum M1 body size in pips for entry
- **Used In**: `core/entry_checker.py`
- **How It Works**:
  - Body Pips = |Close - Open| in pips
  - If body < this value, entry is rejected
  - Filters out small/indecisive M1 candles
- **Typical Range**: 0.5 - 5.0 pips
- **Example**:
  ```json
  "min_body_pips": 1.0
  ```
  *M1 candle body must be at least 1 pip*

#### `wick_size_max`
- **Type**: Float
- **Purpose**: Maximum wick size relative to body (ratio)
- **Used In**: `core/entry_checker.py`
- **How It Works**:
  - Wick Ratio = Max Wick / Body
  - If ratio > this value, entry is rejected
  - Filters out M1 candles with large wicks
- **Typical Range**: 0.3 - 1.0
- **Example**:
  ```json
  "wick_size_max": 0.5
  ```
  *Wick cannot be more than 50% of body size*

#### `consecutive_bars`
- **Type**: Integer
- **Purpose**: Number of consecutive M1 bars with same color required
- **Used In**: `core/entry_checker.py`
- **How It Works**:
  - Checks last N M1 candles
  - All must be same direction (all bullish or all bearish)
  - Confirms momentum before entry
- **Typical Range**: 1-3 bars
- **Example**:
  ```json
  "consecutive_bars": 2
  ```
  *Need 2 consecutive M1 candles in same direction*

---

## Exit Conditions

### `exit_conditions.take_profit_pips`
- **Type**: Float
- **Purpose**: Take profit target in pips
- **Used In**: `core/exit_manager.py`
- **How It Works**:
  - TP = Entry Price ± (TP pips * point value)
  - Position closes automatically when price reaches TP
  - BUY: TP above entry | SELL: TP below entry
- **⚠️ Note**: Currently using dynamic TP based on H4 high/low
- **Example**:
  ```json
  "take_profit_pips": 50.0
  ```

### `exit_conditions.stop_loss_pips`
- **Type**: Float
- **Purpose**: Stop loss in pips
- **Used In**: `core/exit_manager.py`
- **How It Works**:
  - SL = Entry Price ∓ (SL pips * point value)
  - Position closes automatically when price reaches SL
  - BUY: SL below entry | SELL: SL above entry
- **⚠️ CRITICAL**: Always use stop loss to limit risk
- **Example**:
  ```json
  "stop_loss_pips": 20.0
  ```

### `exit_conditions.trailing_stop`

#### `enabled`
- **Type**: Boolean
- **Purpose**: Enable/disable trailing stop
- **Used In**: `core/exit_manager.py`
- **How It Works**:
  - If true, SL moves with price as profit increases
  - If false, SL stays at initial value
- **Example**:
  ```json
  "enabled": false
  ```

#### `activation_pips`
- **Type**: Float
- **Purpose**: Profit level where trailing stop activates (pips)
- **Used In**: `core/exit_manager.py`
- **How It Works**:
  - Trailing only starts after profit > this value
  - Before activation, uses normal SL
- **Example**:
  ```json
  "activation_pips": 10.0
  ```

#### `distance_pips`
- **Type**: Float
- **Purpose**: Distance of trailing stop behind current price (pips)
- **Used In**: `core/exit_manager.py`
- **How It Works**:
  - SL follows price at this distance
  - Locks in profits as price moves favorably
- **Example**:
  ```json
  "distance_pips": 5.0
  ```

---

## Daily Bias

### `daily_bias.epsilon_wick_ratio`
- **Type**: Float (0.0 to 1.0)
- **Purpose**: Minimum wick difference required for BUY/SELL bias
- **Used In**: `core/daily_bias.py`
- **How It Works**:
  - Calculates yesterday's D1 top and bottom wick sizes
  - Top Wick = High - max(Open, Close)
  - Bottom Wick = min(Open, Close) - Low
  - Wick Dominance = |TopWick - BottomWick| / (High - Low)
  - If dominance < epsilon → NEUTRAL
  - If TopWick > BottomWick → SELL bias
  - If BottomWick > TopWick → BUY bias
- **Also Requires**: Small body rule (longest wick > body)
- **Range**:
  - 0.01 = Very loose (1% difference)
  - 0.05 = Standard (5% difference)
  - 0.10 = Very strict (10% difference)
- **⚠️ WARNING**: Lower values = more BUY/SELL days but weaker bias
- **Example**:
  ```json
  "epsilon_wick_ratio": 0.05
  ```
  *Wicks must differ by at least 5% for directional bias*

**Example Scenarios**:

**Scenario 1: SELL Bias**
```
Yesterday's D1:
High = 1.2100
Open = 1.2080
Close = 1.2040
Low = 1.2020

Top Wick = 1.2100 - 1.2080 = 20 pips
Bottom Wick = 1.2040 - 1.2020 = 20 pips
Body = |1.2040 - 1.2080| = 40 pips
Range = 1.2100 - 1.2020 = 80 pips

Small Body Check: max(20, 20) = 20 < 40 → FALSE → NEUTRAL
```

**Scenario 2: BUY Bias**
```
Yesterday's D1:
High = 1.2100
Open = 1.2040
Close = 1.2080
Low = 1.2020

Top Wick = 1.2100 - 1.2080 = 20 pips
Bottom Wick = 1.2040 - 1.2020 = 20 pips... wait, Close > Open so:
Bottom Wick = 1.2040 - 1.2020 = 20 pips
Body = |1.2080 - 1.2040| = 40 pips
Range = 80 pips

Top Wick = 20 pips
Bottom Wick = 20 pips
Longest Wick = 20 pips < Body (40 pips) → Small body rule fails → NEUTRAL

Let's try again:
High = 1.2100
Open = 1.2060
Close = 1.2050
Low = 1.2010

Top Wick = 1.2100 - 1.2060 = 40 pips
Bottom Wick = 1.2050 - 1.2010 = 40 pips
Body = |1.2050 - 1.2060| = 10 pips
Range = 90 pips

Small Body Check: max(40, 40) = 40 > 10 → TRUE ✓
Wick Dominance = |40 - 40| / 90 = 0% < 5% → NEUTRAL

Let's try BUY:
High = 1.2100
Open = 1.2060
Close = 1.2050
Low = 1.2000

Top Wick = 1.2100 - 1.2060 = 40 pips
Bottom Wick = 1.2050 - 1.2000 = 50 pips
Body = 10 pips
Range = 100 pips

Small Body Check: 50 > 10 → TRUE ✓
Wick Dominance = |40 - 50| / 100 = 10% > 5% → TRUE ✓
Bottom Wick > Top Wick → BUY BIAS ✓
```

---

## Server Settings

### `server.host`
- **Type**: String
- **Purpose**: IP address for WebSocket server
- **Used In**: `core/realtime_server.py`
- **Values**:
  - `"127.0.0.1"` = Localhost only (can't access from other devices)
  - `"0.0.0.0"` = All network interfaces (can access from other devices)
- **Security**: Use 127.0.0.1 for local development
- **Example**:
  ```json
  "host": "127.0.0.1"
  ```

### `server.ports`
- **Type**: Array of integers
- **Purpose**: WebSocket server port numbers to try
- **Used In**: `core/realtime_server.py`
- **How It Works**:
  - Tries first port in list
  - If occupied, tries next port
  - Uses first available port
- **Typical Ports**: 8765, 8080, 3000
- **Example**:
  ```json
  "ports": [8765, 8080, 3000]
  ```

### `server.update_interval`
- **Type**: Integer
- **Purpose**: Seconds between market data updates
- **Used In**: `core/realtime_server.py` streaming loop
- **How It Works**:
  - Server fetches new data every N seconds
  - Sends update to all connected browsers
  - Lower = more frequent updates, higher CPU usage
- **Range**: 1-10 seconds
- **Recommendation**: 2 seconds for real-time monitoring
- **Example**:
  ```json
  "update_interval": 2
  ```

### `server.chart_bars_count`
- **Type**: Integer
- **Purpose**: Number of bars to display in main chart
- **Used In**: `core/realtime_server.py` when fetching bars
- **How It Works**:
  - Fetches last N bars from MT5
  - More bars = more history visible
  - More bars = higher memory usage
- **Range**: 50-500 bars
- **Example**:
  ```json
  "chart_bars_count": 100
  ```
  *Shows last 100 candles on chart*

### `server.auto_open_browser`
- **Type**: Boolean
- **Purpose**: Automatically open dashboard in browser when bot starts
- **Used In**: `core/realtime_server.py` startup
- **Values**:
  - `true` = Opens Chrome/default browser automatically
  - `false` = Must open dashboard manually
- **Example**:
  ```json
  "auto_open_browser": true
  ```

---

## Backtesting

### `backtest.use_backtest`
- **Type**: Boolean
- **Purpose**: Enable backtesting mode (not fully implemented)
- **Used In**: Future backtest module
- **Values**:
  - `true` = Backtesting mode
  - `false` = Live trading mode
- **⚠️ Note**: Currently not used
- **Example**:
  ```json
  "use_backtest": false
  ```

### `backtest.start_date`
- **Type**: String (YYYY-MM-DD format)
- **Purpose**: Backtest start date
- **Used In**: Future backtest module
- **Example**:
  ```json
  "start_date": "2024-01-01"
  ```

### `backtest.end_date`
- **Type**: String (YYYY-MM-DD format)
- **Purpose**: Backtest end date
- **Used In**: Future backtest module
- **Example**:
  ```json
  "end_date": "2024-12-31"
  ```

### `backtest.initial_balance`
- **Type**: Float
- **Purpose**: Starting account balance for backtest
- **Used In**: Future backtest module
- **Example**:
  ```json
  "initial_balance": 10000.0
  ```

---

## Common Configuration Scenarios

### Conservative Risk Settings
```json
{
  "risk": {
    "max_daily_loss": 50.0,
    "max_concurrent_orders": 2,
    "max_positions_per_symbol": 1,
    "min_free_margin": 200.0
  },
  "trading": {
    "default_volume": 0.01
  }
}
```

### Aggressive Risk Settings (⚠️ Not Recommended for Beginners)
```json
{
  "risk": {
    "max_daily_loss": 200.0,
    "max_concurrent_orders": 5,
    "max_positions_per_symbol": 3,
    "min_free_margin": 100.0
  },
  "trading": {
    "default_volume": 0.05
  }
}
```

### Strict Entry Conditions (Fewer, Higher Quality Trades)
```json
{
  "entry_conditions": {
    "h4_candidates": {
      "min_body_percent": 0.5,
      "max_wick_percent": 0.3,
      "lookback_candles": 3
    },
    "m1_entry": {
      "min_body_pips": 2.0,
      "wick_size_max": 0.3,
      "consecutive_bars": 3
    }
  },
  "daily_bias": {
    "epsilon_wick_ratio": 0.10
  }
}
```

### Loose Entry Conditions (More Frequent Trades)
```json
{
  "entry_conditions": {
    "h4_candidates": {
      "min_body_percent": 0.2,
      "max_wick_percent": 0.6,
      "lookback_candles": 10
    },
    "m1_entry": {
      "min_body_pips": 0.5,
      "wick_size_max": 0.7,
      "consecutive_bars": 1
    }
  },
  "daily_bias": {
    "epsilon_wick_ratio": 0.01
  }
}
```

---

## Configuration Change Workflow

1. **Stop the bot** if running (`Ctrl+C`)
2. **Edit `config.json`**
3. **Validate JSON syntax** (use online validator if unsure)
4. **Save the file**
5. **Restart the bot** (`python bot.py`)
6. **Verify changes** in console output

---

## Troubleshooting

### Bot won't start after config change
- **Check JSON syntax**: Missing comma, bracket, quote
- **Use JSON validator**: https://jsonlint.com
- **Check quotes**: Must use double quotes `"` not single `'`

### Bot shows "Configuration loaded" but behaves oddly
- **Check data types**: Strings need quotes, numbers don't
- **Check value ranges**: Some values must be 0.0-1.0
- **Check required fields**: All fields must be present

### Daily bias always shows NEUTRAL
- **Lower epsilon_wick_ratio**: Try 0.01 instead of 0.05
- **Check previous day**: May legitimately be neutral
- **Use diagnostic**: Run `python check_bias.py`

---

## Quick Reference

### Most Important Settings to Adjust

1. **Risk Management** (Protect your account)
   - `risk.max_daily_loss`
   - `risk.max_concurrent_orders`
   - `trading.default_volume`

2. **Entry Conditions** (Trading frequency)
   - `daily_bias.epsilon_wick_ratio`
   - `entry_conditions.m1_entry.min_body_pips`
   - `entry_conditions.h4_candidates.min_body_percent`

3. **Exit Conditions** (Profit targets)
   - `exit_conditions.take_profit_pips`
   - `exit_conditions.stop_loss_pips`

### Settings You Should NOT Change

1. **Template-Locked Indicators**
   - `indicators.snake.period` (locked at 100)
   - `indicators.purple_line.period` (locked at 10)

2. **Server Settings** (unless you know what you're doing)
   - `server.host`
   - `server.ports`

---

## Additional Resources

- **Strategy Documentation**: See `IMPLEMENTED_STRATEGY.md`
- **Specification Compliance**: See `SPEC_COMPLIANCE_FIXES.md`
- **Debug Logging**: See `DEBUG_LOGGING_ADDED.md`
- **MT5 Connection Issues**: Run `python diagnose_mt5.py`
- **Daily Bias Checker**: Run `python check_bias.py`

---

**Last Updated**: 2025-10-25
**Configuration Version**: 1.0
**Compatible With**: Trading Bot v1.0
