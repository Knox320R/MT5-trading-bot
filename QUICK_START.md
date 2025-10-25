# Quick Start Guide - MT5 Four-Bot Trading System

## 🚀 **Get Started in 5 Minutes**

### **Step 1: Verify Installation** ✅

```bash
# Check Python
python --version  # Should be 3.7+

# Install dependencies
pip install MetaTrader5 pytz numpy websockets

# Verify MT5
python -c "import MetaTrader5 as mt5; print('MT5 OK:', mt5.version())"
```

---

### **Step 2: Configure Credentials** ✅

Edit `config.json`:

```json
{
  "mt5_account": {
    "demo": {
      "login": YOUR_DEMO_LOGIN,      // ← Change this
      "password": "YOUR_PASSWORD",    // ← Change this
      "server": "Weltrade-Demo"       // ← Verify this
    }
  }
}
```

**Test connection**:
```bash
python bot.py --test-connection
```

Expected output:
```
✓ Connected successfully!
  Account: #19498321
  Balance: $500.00
  Server: Weltrade-Demo
```

---

### **Step 3: Start the Bot** ✅

```bash
python bot.py
```

**What happens**:
1. ✅ Bot connects to MT5
2. ✅ WebSocket server starts on port 8765
3. ✅ Dashboard opens in Chrome automatically
4. ✅ Bot engine starts checking symbols every 2 seconds

**Console output**:
```
==========================================
Starting bot engine loop...
Checking symbols: ['PainX 400', 'PainX 600', ...]
==========================================
[1] Bot engine running - checking 8 symbols
```

---

### **Step 4: Monitor Dashboard** ✅

Dashboard opens automatically at:
```
file:///C:/Users/Administrator/Documents/trading-bot/interface/index.html
```

**What you'll see**:

1. **Connection Status** (top right)
   - 🟢 CONNECTED - Good!
   - 🔴 DISCONNECTED - Check server

2. **Bot Status Panel** (middle)
   - Four bot cards: PAIN BUY, PAIN SELL, GAIN BUY, GAIN SELL
   - **○ SCANNING** - Checking conditions (gray)
   - **● READY** - All conditions met! (green, pulsing)
   - **○ IDLE** - No valid day/conditions (gray)
   - **○ HALTED** - Day-stop triggered (red)

3. **Bot Conditions** (in each card)
   - ✓ Green checkmarks = Condition met
   - ✗ Red crosses = Condition not met

4. **Info Bar** (bottom of bot panel)
   - Trend status (H1/M30/M15)
   - M1 state machine status
   - Daily P/L

---

### **Step 5: Understanding Bot Signals** ✅

#### **NEUTRAL Day** (No Trading)
```
Bot Status Panel:
- Bias: NEUTRAL (gray)
- All bots: ○ IDLE
- Reasons: "Not a BUY/SELL day"
```

#### **BUY Day** (Can trade PAIN BUY & GAIN BUY)
```
Bot Status Panel:
- Bias: BUY (green)
- PAIN BUY: ○ SCANNING or ● READY
- PAIN SELL: ○ IDLE (wrong bias)
- GAIN BUY: ○ SCANNING or ● READY
- GAIN SELL: ○ IDLE (wrong bias)
```

#### **SELL Day** (Can trade PAIN SELL & GAIN SELL)
```
Bot Status Panel:
- Bias: SELL (red)
- PAIN BUY: ○ IDLE (wrong bias)
- PAIN SELL: ○ SCANNING or ● READY
- GAIN BUY: ○ IDLE (wrong bias)
- GAIN SELL: ○ SCANNING or ● READY
```

#### **READY Signal** (All Conditions Met!)
```
PAIN BUY Card:
● READY (green, pulsing)
Reasons:
✓ BUY day
✓ Trend aligned (H1/M30/M15 green)
✓ M30 clean break above snake
✓ M1 cross-then-touch BUY signal
```

**When you see ● READY**:
- Bot will execute automatically (if risk gates pass)
- Console will show: `✅ pain_buy EXECUTED: PainX 400 @ 1.23456`
- Trade logged to `Report/trades_*.csv`

---

### **Step 6: Check Logs** ✅

Logs are auto-created in `Report/` folder:

```bash
# View today's trades
notepad Report/trades_2025-01-24_19.csv

# View signals
notepad Report/signals_2025-01-24_19.csv

# View errors
notepad Report/errors_2025-01-24.log
```

---

## 🎯 **First 24 Hours Checklist**

### **Hour 1-4: Initial Monitoring**
- [ ] Bot starts without errors
- [ ] Dashboard connects (status shows CONNECTED)
- [ ] Bot status panel shows symbol and bias
- [ ] Bias changes at 16:00 COL
- [ ] All 4 bot cards update every 2 seconds

### **Hour 4-8: Condition Checking**
- [ ] Trend status updates (watch H1/M30/M15)
- [ ] M1 state changes (idle → crossed_up/down → ready)
- [ ] Bot conditions show checkmarks/crosses
- [ ] No false READY signals

### **Hour 8-24: Signal Validation**
- [ ] Daily bias is correct (check yesterday's candle manually)
- [ ] BUY day only allows BUY bots
- [ ] SELL day only allows SELL bots
- [ ] PAIN SELL halts if 50% wick filled
- [ ] Re-entry requires new cross-then-touch

### **Day 2-3: Trade Execution**
- [ ] READY signals execute automatically
- [ ] Orders appear in MT5 terminal
- [ ] Exits trigger on M5 purple break OR profit target
- [ ] CSV logs record all trades
- [ ] No duplicate entries (re-entry prevention works)

---

## ⚙️ **Configuration Tips**

### **Start Conservative**
```json
{
  "trading": {
    "lot_size": 0.01,          // Very small lots
    "daily_target_usd": 10.0,   // Low target
    "daily_stop_usd": 5.0,      // Tight stop
    "max_concurrent_orders": 1   // One trade at a time
  }
}
```

### **After 1 Week (If Profitable)**
```json
{
  "trading": {
    "lot_size": 0.05,
    "daily_target_usd": 50.0,
    "daily_stop_usd": 20.0,
    "max_concurrent_orders": 2
  }
}
```

### **After 1 Month (If Consistently Profitable)**
```json
{
  "trading": {
    "lot_size": 0.10,
    "daily_target_usd": 100.0,
    "daily_stop_usd": 40.0,
    "max_concurrent_orders": 3
  }
}
```

---

## 🔧 **Common Issues & Solutions**

### **Issue: "Failed to connect to MT5"**
**Solution**:
1. Close MetaTrader 5 terminal (bot will open it)
2. Check credentials in `config.json`
3. Run: `python bot.py --test-connection`

---

### **Issue: "Port 8765 already in use"**
**Solution**:
```bash
# Bot will try ports: 8765, 8766, 8767, 8768, 8769
# Or specify custom port:
python bot.py --port 9000
```

---

### **Issue: "No bots ever show READY"**
**Check**:
1. **Is it a BUY/SELL day?** (Not NEUTRAL)
   - Dashboard shows: Bias: BUY or SELL
2. **Are you within trading hours?** (19:00-06:00 COL)
   - Check config.json session times
3. **Is trend aligned?** (H1/M30/M15 all same color)
   - Dashboard shows: Trend: H1:green M30:green M15:green
4. **Has M1 cross-then-touch occurred?**
   - Dashboard shows: M1 State: crossed_up/down → ready

---

### **Issue: "Dashboard not updating"**
**Solution**:
1. Check console: Should show `[N] Bot engine running`
2. Refresh dashboard (F5)
3. Check WebSocket status (top right): Should be CONNECTED
4. Check browser console (F12) for errors

---

### **Issue: "Trades not executing"**
**Check**:
1. **Bot shows READY?** - Must see green pulsing ● READY
2. **Risk gates passing?** - Check:
   - Spread < 2 pips
   - Daily profit not reached
   - Daily loss not exceeded
   - Max orders not reached
3. **Account has margin?** - Check MT5 terminal

---

## 📊 **Daily Routine**

### **Morning (Before 16:00 COL)**
1. Check yesterday's daily candle
2. Predict today's bias:
   - Small body + lower wick > body = SELL day
   - Small body + upper wick > body = BUY day
3. Verify bot shows same bias at 16:00

### **Evening (19:00-06:00 Trading Session)**
1. Monitor dashboard
2. Watch for READY signals
3. Verify trades execute
4. Check exits trigger correctly
5. Review `Report/trades_*.csv` at end of day

### **Weekly**
1. Review `Report/trades_*.csv` for all days
2. Calculate win rate, average profit
3. Adjust parameters if needed
4. Backup Report folder

---

## 🎓 **Learning Resources**

### **Understanding the Bots**
```
1. Read overview/strategy.txt     (Strategy specification)
2. Read overview/feedback.txt     (Logic corrections)
3. Read overview/rule.txt         (Hard rules)
4. Watch dashboard for 1-2 days   (See patterns)
5. Review Report/signals_*.csv    (See all signals)
```

### **Code Deep Dive**
```
1. Start: bot.py
2. Core: core/bot_engine.py
3. Entry Logic: core/m1_state_machine.py
4. Bias: core/daily_bias.py
5. Full Docs: README.md
```

---

## ✅ **Success Indicators**

After 24-48 hours, you should see:

- ✅ **Bias changes at 16:00 daily**
  - Console: Daily bias updated
  - Dashboard: Bias indicator changes color

- ✅ **Bot conditions update in real-time**
  - Checkmarks/crosses change as market moves
  - Trend status updates

- ✅ **READY signals appear when conditions met**
  - Green pulsing ● READY
  - All conditions show ✓

- ✅ **Trades execute automatically**
  - Console: ✅ bot_type EXECUTED
  - MT5 terminal shows order
  - CSV log records entry

- ✅ **Exits trigger correctly**
  - Console: 🔴 EXIT
  - MT5 position closes
  - CSV log records exit with profit

---

## 🚀 **You're Ready!**

Start the bot:
```bash
python bot.py
```

Monitor the dashboard for first 24-48 hours.

**Good luck! 🎯📈**

---

**Need Help?**
- Check `README.md` for full documentation
- Review `COMPLETION_REPORT.md` for technical details
- Examine logs in `Report/` folder
- Read inline code comments in `core/` modules

**Happy Trading!** 🎉
