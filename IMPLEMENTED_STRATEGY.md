# Trading Strategy - As Implemented in Code

This document describes the **exact trading workflow** as implemented in the bot engine code, based solely on analyzing the actual Python implementation after specification compliance fixes.

---

## Overview

The system runs **four independent trading bots** simultaneously for each symbol:
1. **PAIN BUY** - Long entries on BUY days without structure validation
2. **PAIN SELL** - Short entries on SELL days with day-stop mechanism
3. **GAIN BUY** - Long entries on BUY days with Fibonacci structure validation
4. **GAIN SELL** - Short entries on SELL days with Fibonacci structure validation

---

## Core Components

### Indicators (TEMPLATE-LOCKED)

**Snake (EMA 100)**
- Primary trend indicator
- **Period: 100 (LOCKED - cannot be modified)**
- Close >= Snake = Green Snake
- Close < Snake = Red Snake
- Used for trend determination and M30 break detection

**Purple Line (EMA 10)**
- Entry signal indicator
- **Period: 10 (LOCKED - cannot be modified)**
- Used for cross-then-touch detection on M1 timeframe
- Used for early exit detection on M5 timeframe

**Note**: Both EMA periods are template-locked. Getters always return 100 and 10 regardless of config values. Attempting to change these values will trigger warnings but not affect bot behavior.

### Timezone & Trading Day Boundary

- Timezone: America/Bogota
- Daily boundary: 16:00 local time
- Trading day starts at 16:00 and runs until next day 15:59
- All daily calculations (bias, swings, consecutive orders) reset at 16:00

---

## Daily Bias Calculation

**Evaluated once per day at 16:00 using yesterday's D1 candle:**

1. **Extract yesterday's candle** (second-to-last D1 bar)

2. **Calculate candle components:**
   - Body = |Close - Open|
   - Upper Wick = High - max(Open, Close)
   - Lower Wick = min(Open, Close) - Low
   - Longest Wick = max(Upper Wick, Lower Wick)

3. **Small Body Rule (Binary):**
   - If Longest Wick > Body → Small Body = TRUE
   - Otherwise → Small Body = FALSE

4. **Determine Bias:**
   - If NOT small body → **NEUTRAL**
   - If small body AND Lower Wick > Upper Wick × 1.05 → **SELL day**
   - If small body AND Upper Wick > Lower Wick × 1.05 → **BUY day**
   - If wicks too close (within 5%) → **NEUTRAL**

5. **SELL Day 50% Wick Level:**
   - Base Low = min(Open, Close)
   - Level50 = Base Low - 0.5 × Lower Wick
   - Used only for PAIN SELL day-stop

**Result:** Each day is classified as BUY, SELL, or NEUTRAL

---

## Trend Alignment Check

**Required for all bot entries:**

Checks three timeframes: **H1, M30, M15**

**Color Determination:**
- Close >= Snake → Green
- Close < Snake → Red
- Close == Snake exactly → Rejected (treated as NOT trend)

**BUY Bots (PAIN BUY, GAIN BUY):**
- Require: H1 green AND M30 green AND M15 green
- All three must be green simultaneously

**SELL Bots (PAIN SELL, GAIN SELL):**
- Require: H1 red AND M30 red AND M15 red
- All three must be red simultaneously

**Equality Handling:**
- When Close == Snake exactly → Treated as NOT trend (rejected)
- This prevents entries on flat/ranging conditions
- Configurable via `equality_is_not_trend` (default: true)

---

## M30 Clean Break Detection (PAIN Bots Only)

**Tracks first clean close above/below Snake after being on opposite side:**

**For PAIN BUY:**
1. Monitor M30 closes relative to M30 Snake
2. Detect when: Previous close < Previous Snake AND Current close >= Current Snake
3. This is "upward break"
4. Break remains valid as long as M30 close stays >= M30 Snake

**For PAIN SELL:**
1. Monitor M30 closes relative to M30 Snake
2. Detect when: Previous close >= Previous Snake AND Current close < Current Snake
3. This is "downward break"
4. Break remains valid as long as M30 close stays < M30 Snake

**Purpose:** Ensures entry only after momentum shift, not during ranging

---

## M15 Swing + Fibonacci Structure (GAIN Bots Only)

**Calculated using today's M15 bars only (from 16:00 boundary):**

**For GAIN BUY:**
1. Find today's M15 swing:
   - Swing Low = minimum of all M15 lows today
   - Swing High = maximum of all M15 highs today
2. Calculate Fibonacci 50% level:
   - Fib50 = Swing Low + 0.5 × (Swing High - Swing Low)
3. Find largest-body H4 candle among last N closed H4 candles:
   - N = configurable via `h4_candidates` (default: 3)
   - Body = |Close - Open|
   - Select candle with maximum body size
4. Validate H4 covers Fib50:
   - Check if: H4 Low <= Fib50 <= H4 High
   - Must be TRUE to pass structure check

**For GAIN SELL:**
1. Find today's M15 swing:
   - Swing High = maximum of all M15 highs today
   - Swing Low = minimum of all M15 lows today
2. Calculate Fibonacci 50% level:
   - Fib50 = Swing Low + 0.5 × (Swing High - Swing Low)
3. Find largest-body H4 candle among last N closed H4 candles
   - N = configurable via `h4_candidates` (default: 3)
4. Validate H4 covers Fib50:
   - Check if: H4 Low <= Fib50 <= H4 High

**Purpose:** Ensures trade aligns with higher timeframe structure and key level

**Configurability:** User can adjust `h4_candidates` in config.json to scan more or fewer H4 candles

---

## M1 Cross-Then-Touch Entry Logic

**State machine with timeout, used by all 4 bots:**

### States:
1. **IDLE** - Waiting for cross
2. **CROSSED_UP** - Price crossed above Purple, waiting for touch
3. **CROSSED_DOWN** - Price crossed below Purple, waiting for touch
4. **READY_BUY** - Valid BUY signal detected
5. **READY_SELL** - Valid SELL signal detected
6. **EXECUTED** - Order placed, prevents re-entry

### BUY Signal Detection:

**Step 1: Cross Detection**
- Wait in IDLE state
- Monitor M1 closes relative to M1 Purple Line
- Detect: Previous Close < Previous Purple AND Current Close > Current Purple
- State → CROSSED_UP
- Record cross bar index

**Step 2: Touch Detection (after cross)**
- Maximum timeout: Configurable via `max_bars_between_cross_and_touch` (default: 20 bars)
- Looking for: Current Low <= Current Purple <= Current High (price touches Purple)
- Valid touch requires:
  - Current Close >= Current Purple (must close on correct side)
  - Current Close >= Current Snake (must be above Snake)
- If valid → State = READY_BUY
- If timeout or crossed back down → State = IDLE (reset)

**Step 3: Execution**
- When READY_BUY, bot executes at next bar open
- State → EXECUTED
- No re-entry until state reset (prevents duplicate entries)

### SELL Signal Detection:

**Step 1: Cross Detection**
- Wait in IDLE state
- Detect: Previous Close > Previous Purple AND Current Close < Current Purple
- State → CROSSED_DOWN
- Record cross bar index

**Step 2: Touch Detection (after cross)**
- Maximum timeout: Configurable via `max_bars_between_cross_and_touch` (default: 20 bars)
- Looking for: Current Low <= Current Purple <= Current High
- Valid touch requires:
  - Current Close <= Current Purple (must close on correct side)
  - Current Close < Current Snake (must be below Snake)
- If valid → State = READY_SELL
- If timeout or crossed back up → State = IDLE (reset)

**Step 3: Execution**
- When READY_SELL, bot executes at next bar open
- State → EXECUTED

**Reset Conditions:**
- After position exits (allows fresh entry)
- Timeout (configurable bars pass without valid touch)
- Price crosses back to opposite side

---

## Complete Entry Conditions by Bot

### PAIN BUY Entry Conditions:
1. ✓ Daily Bias = BUY
2. ✓ Trend Alignment: H1 green AND M30 green AND M15 green
3. ✓ M30 Clean Break: First close above Snake after being at/below
4. ✓ M1 Cross-Then-Touch: BUY signal active (cross up → touch → close above Purple and Snake)
5. ✓ Consecutive Orders: Less than 3 consecutive PAIN_BUY orders today

**All 5 must be TRUE simultaneously**

### PAIN SELL Entry Conditions:
1. ✓ Daily Bias = SELL
2. ✓ NOT halted by day-stop
3. ✓ Trend Alignment: H1 red AND M30 red AND M15 red
4. ✓ M30 Clean Break: First close below Snake after being at/above
5. ✓ M1 Cross-Then-Touch: SELL signal active (cross down → touch → close below Purple and below Snake)
6. ✓ Consecutive Orders: Less than 3 consecutive PAIN_SELL orders today

**All 6 must be TRUE simultaneously**

### GAIN BUY Entry Conditions:
1. ✓ Daily Bias = BUY
2. ✓ Fibonacci Structure: Today's M15 Fib50 covered by largest-body H4 candle (from last N closed H4 bars, N=configurable)
3. ✓ Trend Alignment: H1 green AND M30 green AND M15 green
4. ✓ M1 Cross-Then-Touch: BUY signal active (same as PAIN BUY)
5. ✓ Consecutive Orders: Less than 3 consecutive GAIN_BUY orders today

**All 5 must be TRUE simultaneously** (no M30 break required)

### GAIN SELL Entry Conditions:
1. ✓ Daily Bias = SELL
2. ✓ Fibonacci Structure: Today's M15 Fib50 covered by largest-body H4 candle (from last N closed H4 bars, N=configurable)
3. ✓ Trend Alignment: H1 red AND M30 red AND M15 red
4. ✓ M1 Cross-Then-Touch: SELL signal active (same as PAIN SELL)
5. ✓ Consecutive Orders: Less than 3 consecutive GAIN_SELL orders today

**All 5 must be TRUE simultaneously** (no M30 break required, no day-stop)

---

## Trade Execution

**Order Parameters:**
- Lot Size: 0.10 (configurable via `lot_size`)
- Fixed Profit Target: $2.00 USD (configurable via `trade_target_usd`)
- Stop Loss: 3× the profit distance (protective stop, not primary exit)
- Slippage: Maximum 2 pips (configurable via `max_slippage_pips`)
- Comment: "bot_type|reason" (e.g., "pain_buy|M1 cross-touch")

**Entry Timing:**
- Execute at next bar open after all conditions met
- Uses MT5 market order (TRADE_ACTION_DEAL)

**Take Profit Calculation:**
- Target USD = configurable (default $2.00)
- TP Distance = Target USD / (Contract Size × Lot Size)
- TP Price = Entry Price ± TP Distance

**Stop Loss Calculation:**
- SL Distance = TP Distance × 3
- SL Price = Entry Price ∓ SL Distance
- Note: SL is protective only; early exit mechanism is primary

---

## Exit Management

### Primary Exit: M5 Purple Break (Early Exit)

**Monitored every cycle:**

**For BUY Positions:**
- Monitor M5 closes relative to M5 Purple Line (EMA 10)
- Exit if: M5 Close < M5 Purple
- This indicates momentum reversal

**For SELL Positions:**
- Monitor M5 closes relative to M5 Purple Line (EMA 10)
- Exit if: M5 Close > M5 Purple
- This indicates momentum reversal

**Purpose:** Exit before hitting stop loss when trend reverses

**Configurability:** Can be disabled via `early_exit_on_m5_purple_break` (default: true)

### Secondary Exit: Fixed Profit Target

- Take Profit at configurable USD amount (default $2.00)
- Automatically triggered by MT5 when TP price reached

### Tertiary Exit: Stop Loss

- Large stop loss (3× profit distance)
- Only triggered if early exit fails and price moves strongly against position

**Exit Priority:**
1. M5 Purple Break (most common) → Early exit
2. Take Profit → Target reached
3. Stop Loss → Last resort

**Note:** No time-based exits are implemented per specification

---

## PAIN SELL 50% Wick Day-Stop Mechanism

**Only applies to PAIN SELL bot on SELL days:**

**Activation:**
1. When Daily Bias = SELL, Level50 is calculated
2. Monitor today's lowest price continuously
3. If Today's Low <= Level50 → Day-stop TRIGGERED
4. PAIN SELL bot state → HALTED

**Effect:**
- No new PAIN SELL entries allowed for remainder of day (until 16:00 reset)
- Existing PAIN SELL positions NOT automatically closed
- Other bots (PAIN BUY, GAIN BUY, GAIN SELL) unaffected

**Purpose:** Prevents excessive SELL entries after price has already moved 50% of yesterday's lower wick

**Reset:**
- At 16:00 daily boundary when new bias calculated
- HALTED state cleared for new trading day

**Configurability:** Can be disabled via `pain_sell_50pct_wick_stop` (default: true)

---

## Risk Management Gates

**Checked before EVERY trade execution:**

### 1. Session Time Gate
- Trading hours: 19:00 - 06:00 COL time
- Blocks trades outside these hours
- Configurable via `session.enabled` and `session.trading_hours`

### 2. Symbol Enabled Gate
- Symbol must be in config.json symbols list
- Verifies symbol is configured for trading

### 3. Spread Gate
- Maximum spread: 2.0 pips (configurable)
- Blocks trades if spread too wide
- Configurable via `max_spread_pips`

### 4. Daily Profit Target Gate
- Target: $100.00 USD per day (configurable)
- Stops all trading when reached
- Configurable via `daily_target_usd`

### 5. Daily Loss Limit Gate
- Limit: $40.00 USD loss per day (configurable)
- Stops all trading when breached
- Configurable via `daily_stop_usd`

### 6. **Consecutive Orders Gate** (Per Bot Per Symbol)
- **Limit: 3 orders in a row** (configurable)
- **Tracks consecutive orders per bot type per symbol**
- **Counter increments:** Each time order is placed
- **Counter resets when:**
  - Profitable trade closes (P&L > $0) → Breaks losing streak
  - Daily boundary at 16:00 COL → Fresh start
- **Blocks:** 4th consecutive order for that specific bot/symbol combination
- **Example:**
  ```
  PAIN_BUY on PainX 400:
  Order 1: Loss -$0.50 → Counter = 1
  Order 2: Loss -$0.50 → Counter = 2
  Order 3: Loss -$0.50 → Counter = 3
  Order 4: BLOCKED (limit reached)

  [Order 3 exits with profit +$0.30]
  → Counter RESETS to 0

  Order 4: Now ALLOWED → Counter = 1
  ```
- **Independence:** Each bot has separate counter (PAIN_BUY counter doesn't affect GAIN_BUY)
- Configurable via `max_concurrent_orders`

### 7. Account Health Gate
- Verifies MT5 connection active
- Verifies account info accessible
- Checks margin availability

**If ANY gate fails → Trade blocked**

---

## Data Flow & Timing

### Data Processing Cycle (Every 2 seconds):

1. **Fetch M1 Bars** (200 bars)
2. **Resample to All Timeframes:**
   - M1 → M5, M15, M30, H1, H4, D1
   - Respects 16:00 daily boundary
3. **Calculate Daily Bias** (using D1 yesterday candle)
4. **Calculate Indicators:**
   - Snake (EMA 100 - LOCKED) for all timeframes
   - Purple (EMA 10 - LOCKED) for all timeframes
5. **Check Trend Alignment** (H1, M30, M15)
6. **Update M30 Break Detector** (PAIN bots)
7. **Calculate Fibonacci Structure** (GAIN bots)
8. **Update M1 State Machine** (all bots)
9. **Evaluate Each Bot:**
   - PAIN BUY conditions
   - PAIN SELL conditions (check day-stop)
   - GAIN BUY conditions
   - GAIN SELL conditions
10. **Check Risk Gates** (if any bot ready)
    - Including consecutive orders check per bot
11. **Execute Trades** (if gates pass)
    - Increment consecutive orders counter
12. **Monitor Exits:**
    - Fetch M5 bars
    - Check M5 Purple breaks
    - Close positions if exit signal
    - Reset consecutive counter if profitable
13. **Broadcast to UI** (bot status, trades)

### Exit Monitoring Cycle (Every 2 seconds):

1. **Fetch M5 Bars** (20 bars)
2. **Calculate M5 Purple Line**
3. **For Each Open Position:**
   - Check M5 close vs M5 Purple
   - If break detected → Close position
   - Record profit/loss
   - **Reset consecutive counter if profitable**
4. **Update Risk Manager** (track daily P&L)

---

## State Management

### Bot States Per Symbol:
- **IDLE** - No signal, scanning
- **SCANNING** - Conditions being checked
- **READY** - All conditions met, ready to enter
- **IN_POSITION** - Trade active
- **HALTED** - Day-stop triggered (PAIN SELL only)

### M1 Entry States Per Symbol:
- **IDLE** - Waiting for cross
- **CROSSED_UP** - Crossed above Purple, waiting for touch
- **CROSSED_DOWN** - Crossed below Purple, waiting for touch
- **READY_BUY** - Valid BUY touch detected
- **READY_SELL** - Valid SELL touch detected
- **EXECUTED** - Order placed, locked until exit

### M30 Break States Per Symbol:
- **last_break_type**: 'up', 'down', or None
- **break_bar_index**: Index of break candle
- Resets when price crosses back

### Consecutive Orders Tracking (Per Bot Per Symbol):
- **consecutive_count**: Number of consecutive orders
- **last_reset_day**: Last reset date (for daily boundary)
- Resets on profitable trade or daily boundary
- Independent counter for each bot type

---

## Key Design Principles

1. **Closed Candles Only:**
   - Never uses forming/incomplete bars for logic
   - All decisions based on fully closed candles

2. **Deterministic Rules:**
   - No discretionary judgment
   - All conditions binary (true/false)
   - Same inputs always produce same output

3. **Four Independent Bots:**
   - Run in parallel
   - Don't interfere with each other
   - Each has own state machine and consecutive orders counter

4. **Single Entry, Multiple Conditions:**
   - All entry conditions must be TRUE
   - Missing one condition = no trade

5. **Early Exit Priority:**
   - M5 Purple break checked before TP/SL
   - Preserves capital when momentum shifts

6. **Consecutive Orders Protection:**
   - Prevents over-trading same bot on losing streaks
   - Resets on profitable trade (allows continuation)
   - Per bot per symbol isolation

7. **Day-Stop for PAIN SELL:**
   - Prevents over-trading in one direction
   - Only affects one bot type

8. **Daily Reset:**
   - Bias recalculated at 16:00
   - Fibonacci swings reset to today's data
   - Consecutive orders counters reset
   - States persist intraday

9. **Template Locking:**
   - EMA periods (100, 10) cannot be modified
   - Enforced at getter level with warnings
   - Ensures strategy consistency

10. **Centralized Configuration:**
    - All parameters in config.json
    - No hardcoded values in logic
    - User-configurable where appropriate
    - Template-locked where required

---

## Configurable Parameters

### Fully Configurable (User Can Modify):

| Parameter | Default | Config Path |
|-----------|---------|-------------|
| Lot Size | 0.10 | `trading.lot_size` |
| Trade Target USD | $2.00 | `trading.trade_target_usd` |
| Daily Target USD | $100.00 | `trading.daily_target_usd` |
| Daily Stop USD | $40.00 | `trading.daily_stop_usd` |
| Max Spread Pips | 2.0 | `trading.max_spread_pips` |
| Max Slippage Pips | 2.0 | `trading.max_slippage_pips` |
| Max Consecutive Orders | 3 | `trading.max_concurrent_orders` |
| Trading Hours Start | 19:00 | `session.trading_hours.start` |
| Trading Hours End | 06:00 | `session.trading_hours.end` |
| H4 Candidates | 3 | `structure_checks.h4_candidates` |
| Max Bars Cross-Touch | 20 | `entry_m1.max_bars_between_cross_and_touch` |
| Equality is Not Trend | true | `trend_filters.equality_is_not_trend` |
| Daily Bias Epsilon | 0.05 | `daily_bias.epsilon_wick_ratio` |
| M5 Purple Break Exit | true | `exits.early_exit_on_m5_purple_break` |
| PAIN SELL Wick Stop | true | `day_stops.pain_sell_50pct_wick_stop` |

### Template-Locked (Cannot Be Modified):

| Parameter | Value | Enforcement |
|-----------|-------|-------------|
| Snake Period | 100 | Hardcoded in getter, warns if config differs |
| Purple Line Period | 10 | Hardcoded in getter, warns if config differs |
| Snake Type | EMA | Required for strategy |
| Purple Type | EMA | Required for strategy |

---

## Example Trading Scenario

**Scenario: PAIN BUY Entry with Consecutive Orders Limit**

**Day Setup:**
- Time: 20:00 COL (within trading hours 19:00-06:00)
- Yesterday's D1: Upper wick dominant + small body → **Daily Bias = BUY**

**Trend Confirmation:**
- H1: Close 1.2050, Snake 1.2040 → Green
- M30: Close 1.2048, Snake 1.2038 → Green
- M15: Close 1.2049, Snake 1.2037 → Green
- **Trend Aligned = TRUE** ✓

**M30 Break:**
- Previous M30: Close 1.2035 < Snake 1.2038 (below)
- Current M30: Close 1.2048 >= Snake 1.2038 (above)
- **Clean Upward Break = TRUE** ✓

**M1 Entry Signal:**
- 20:15 - M1 Close 1.2045 crosses ABOVE Purple 1.2044 → State = CROSSED_UP
- 20:17 - M1 touches Purple 1.2046, Close 1.2047 (>= Purple, >= Snake) → State = READY_BUY ✓

**Risk Gates:**
- Session time: 20:17 COL (OK)
- Spread: 1.5 pips (< 2.0 pips, OK)
- Daily P&L: +$5 (< $100 target, < $40 loss, OK)
- **Consecutive PAIN_BUY orders: 2** (< 3 max, OK) ✓
- **All Gates Pass** ✓

**Execution #1:**
- Entry: 1.2048 (next bar open)
- TP: 1.2068 (+$2.00)
- SL: 1.2008 (protective)
- Lot: 0.10
- Comment: "pain_buy|M1 cross-touch"
- **Consecutive counter: 2 → 3**

**Exit Monitoring:**
- 20:30 - M5 closes at 1.2055 > M5 Purple 1.2053 (still valid)
- 20:35 - M5 closes at 1.2062 > M5 Purple 1.2058 (still valid)
- 20:40 - M5 closes at 1.2045 < M5 Purple 1.2049 → **Purple Break Detected**
- Exit: 1.2045
- Profit: -$0.30 (loss)
- **Consecutive counter: Stays at 3** (no reset on loss)

**Next Signal (same day, 21:00):**
- All conditions met again
- **Consecutive PAIN_BUY orders: 3** (AT limit)
- **4th order BLOCKED** - consecutive limit reached

**Later (21:30) - Different Outcome:**
- Suppose the 3rd trade had exited profitable at 1.2068 (+$2.00)
- **Consecutive counter: 3 → RESET to 0** (profitable trade)
- New signal at 22:00 → **ALLOWED** (counter reset)

**Result:** Consecutive orders limit prevents excessive losses from same bot, resets on profitable trade to allow continuation

---

## Summary

This strategy combines:
- **Daily bias** from higher timeframe structure
- **Multi-timeframe trend alignment** for confluence
- **Momentum confirmation** via M30 break (PAIN) or Fibonacci structure (GAIN)
- **Precise M1 timing** using cross-then-touch state machine
- **Early exit protection** via M5 Purple break monitoring
- **Consecutive orders protection** per bot/symbol with reset on profit
- **Risk controls** via multiple gates and day-stop mechanism
- **Template locking** for critical EMA periods
- **Full configurability** for all non-critical parameters

All bots operate simultaneously, each targeting different market conditions (simple trend breaks vs structure-confirmed entries), with independent consecutive orders tracking providing diversified entry opportunities while maintaining strict risk management and preventing over-trading on losing streaks.

