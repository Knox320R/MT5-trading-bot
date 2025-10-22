# Trading Bot Development TODO

## IMMEDIATE TASK: Signal Detection & Recording System

### Phase 1: Multi-Timeframe Data Collection (PRIORITY)
- [ ] Create multi-timeframe data fetcher
  - [ ] Fetch D1, H4, H1, M30, M15, M5, M1 data simultaneously
  - [ ] Store in organized data structure
  - [ ] Update every 2 seconds

- [ ] Implement Fibonacci calculator
  - [ ] Calculate from high to low (SELL)
  - [ ] Calculate from low to high (BUY)
  - [ ] Identify 50% retracement levels

- [ ] Create wick analyzer for D1
  - [ ] Detect upward vs downward wick
  - [ ] Calculate wick length
  - [ ] Determine body size
  - [ ] Check 50% fill condition

### Phase 2: Indicator Calculations
- [ ] Snake (EMA 100) calculations
  - [x] Calculate EMA 100 for all timeframes
  - [x] Determine color (green/red) based on price
  - [ ] Track color changes across timeframes

- [ ] Purple Line (EMA 10) calculations
  - [x] Calculate EMA 10 for all timeframes
  - [ ] Detect breakouts (price crossing)
  - [ ] Detect touchbacks (price returning)

- [ ] Price position detector
  - [ ] Check if price above/below Snake
  - [ ] Check if price above/below Purple Line
  - [ ] Track breakout directions

### Phase 3: Condition Checking Logic
- [ ] PAIN SELL condition checker
  - [ ] D1: Downward wick detection
  - [ ] H4: 50% Fibonacci coverage
  - [ ] H1: Price below red Snake
  - [ ] M30: Snake is RED
  - [ ] M15: Snake is RED
  - [ ] M1: Price below red Snake + Purple Line break + touchback

- [ ] GAIN SELL condition checker
  - [ ] D1: Downward wick detection
  - [ ] M30: Complete Snake break + RED
  - [ ] M5: Purple Line touch after retreat
  - [ ] M1: Aligned with M5

- [ ] PAIN BUY condition checker
  - [ ] D1: Upward wick detection
  - [ ] M30: Complete Snake break + GREEN
  - [ ] M5: Purple Line touch after retreat
  - [ ] M1: Aligned with M5

- [ ] GAIN BUY condition checker
  - [ ] D1: Upward wick detection
  - [ ] H4: 50% Fibonacci coverage
  - [ ] H1: Price above green Snake
  - [ ] M30: Snake is GREEN
  - [ ] M15: Snake is GREEN
  - [ ] M1: Price above green Snake + Purple Line break + touchback

### Phase 4: Signal Detection Engine
- [ ] Create signal detector class
  - [ ] Run every 2 seconds
  - [ ] Evaluate all symbols (PainX/GainX 400, 600, 800, 999)
  - [ ] Check all conditions for current timeframe
  - [ ] Generate signal object with all details

- [ ] Signal validation
  - [ ] Verify all conditions met
  - [ ] Check trading hours (7PM-6AM COL)
  - [ ] Validate daily targets not exceeded
  - [ ] Check max concurrent orders

### Phase 5: Dashboard Visualization
- [ ] Add signals list box below chart
  - [ ] Create HTML container
  - [ ] Style list with CSS
  - [ ] Display recent signals (last 20)
  - [ ] Auto-scroll to newest

- [ ] Chart markers for signals
  - [ ] BUY marker (green arrow up)
  - [ ] SELL marker (red arrow down)
  - [ ] Position at signal price
  - [ ] Show on M1 chart

- [ ] Signal details display
  - [ ] Timestamp
  - [ ] Symbol name
  - [ ] Signal type (BUY/SELL)
  - [ ] Current price
  - [ ] Snake color
  - [ ] Conditions met summary

### Phase 6: CSV Recording System
- [ ] Create Report folder if not exists
  - [ ] Check folder existence
  - [ ] Create if missing

- [ ] Implement hourly file creation
  - [ ] Generate filename: report_YYYY-MM-DD_HH.csv
  - [ ] Create new file each hour
  - [ ] Write CSV header

- [ ] Signal data formatter
  - [ ] Convert signal object to CSV row
  - [ ] Include all timeframe conditions
  - [ ] Format timestamp properly
  - [ ] Escape special characters

- [ ] CSV writer
  - [ ] Append to current hour file
  - [ ] Handle file rotation at hour change
  - [ ] Ensure data integrity
  - [ ] Add error handling

### Phase 7: Backend Server Updates
- [ ] Update realtime_server.py
  - [ ] Add signal detection loop
  - [ ] Send signals to dashboard via WebSocket
  - [ ] Broadcast to all connected clients

- [ ] Create signal_detector.py module
  - [ ] Multi-timeframe analyzer
  - [ ] Condition checker
  - [ ] Signal generator

- [ ] Create csv_recorder.py module
  - [ ] File management
  - [ ] CSV writing
  - [ ] Hourly rotation

### Phase 8: Frontend Dashboard Updates
- [ ] Update dashboard.js
  - [ ] Handle signal messages from server
  - [ ] Add signal markers to chart
  - [ ] Update signals list box
  - [ ] Implement auto-scroll

- [ ] Add signal controls
  - [ ] Filter by symbol
  - [ ] Filter by type (BUY/SELL)
  - [ ] Clear signals button
  - [ ] Export visible signals

### Phase 9: Testing & Validation
- [ ] Unit tests
  - [ ] Test EMA calculations
  - [ ] Test condition checkers
  - [ ] Test signal detection

- [ ] Integration tests
  - [ ] Test multi-timeframe data flow
  - [ ] Test signal generation
  - [ ] Test CSV writing

- [ ] Live testing
  - [ ] Run with demo account
  - [ ] Verify signal accuracy
  - [ ] Check CSV file creation
  - [ ] Validate dashboard updates

### Phase 10: Documentation
- [ ] Code documentation
  - [ ] Docstrings for all functions
  - [ ] Inline comments for complex logic
  - [ ] README updates

- [ ] User guide
  - [ ] How to read signals
  - [ ] CSV file format explanation
  - [ ] Dashboard controls guide

---

## Future Enhancements (Post-Signal Detection)
- [ ] Automated order execution
- [ ] Trade management (hold 5min, close, wait)
- [ ] Stop loss automation
- [ ] Daily target tracking
- [ ] Performance metrics
- [ ] Backtesting system
- [ ] Alert notifications (Telegram/Email)

---

## Notes
- Focus FIRST on detecting and recording perfect moments
- Do NOT implement actual trading yet
- Build reliable signal detection system
- Ensure accurate CSV logging for analysis
- Dashboard visualization is key for validation
