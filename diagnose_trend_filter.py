"""
Diagnose trend filter issues
"""
import json
import MetaTrader5 as mt5
from datetime import datetime
from core.bot_engine import BotEngine
from core.mt5_connector import MT5Connector

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

# Initialize MT5
mt5_path = config.get('mt5_path', '')
if mt5_path:
    mt5.initialize(path=mt5_path)
else:
    mt5.initialize()

symbol = "PainX 400"

print("="*80)
print("TREND FILTER DIAGNOSTIC")
print("="*80)

# Get M1 bars (need 7200 for EMA100 on H1)
m1_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 7200)
m1_bars = []
for rate in m1_rates:
    m1_bars.append({
        'time': datetime.fromtimestamp(rate['time']),
        'open': float(rate['open']),
        'high': float(rate['high']),
        'low': float(rate['low']),
        'close': float(rate['close']),
        'volume': int(rate['tick_volume'])
    })

# Get D1 bars from MT5
d1_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, 5)
d1_bars_mt5 = []
for rate in d1_rates:
    d1_bars_mt5.append({
        'time': datetime.fromtimestamp(rate['time']),
        'open': float(rate['open']),
        'high': float(rate['high']),
        'low': float(rate['low']),
        'close': float(rate['close']),
        'volume': int(rate['tick_volume'])
    })

# Process through bot engine
connector = MT5Connector()
bot_engine = BotEngine(connector)

# Get the tf_indicators to see what data we have
from core.data_resampler import DataResampler
resampler = DataResampler(timezone="America/Bogota")
tf_data = resampler.resample_all_timeframes(m1_bars)

print("\nTIMEFRAME DATA AVAILABILITY:")
print("="*80)
for tf in ['M1', 'M5', 'M15', 'M30', 'H1', 'H4']:
    bars = tf_data.get(tf, [])
    print(f"{tf}: {len(bars)} bars")

# Calculate indicators
tf_indicators = {}
for tf, bars in tf_data.items():
    tf_indicators[tf] = bot_engine.indicator_calc.get_indicators_for_bars(bars, f"{symbol}_{tf}")

print("\nINDICATOR DATA FOR TREND TIMEFRAMES (H1, M30, M15):")
print("="*80)
for tf in ['H1', 'M30', 'M15']:
    if tf in tf_indicators:
        data = tf_indicators[tf]
        close = data.get('close_latest')
        snake = data.get('snake_latest')

        print(f"\n{tf}:")
        print(f"  close_latest: {close}")
        print(f"  snake_latest: {snake}")
        print(f"  Has both values? {close is not None and snake is not None}")

        if close is not None and snake is not None:
            if close > snake:
                color = "green"
            elif close < snake:
                color = "red"
            else:
                color = "neutral (equal)"
            print(f"  Color: {color}")
            print(f"  Difference: {close - snake:.5f}")
    else:
        print(f"\n{tf}: NOT IN tf_indicators!")

# Check trend alignment
print("\n" + "="*80)
print("TREND FILTER CHECK")
print("="*80)

trend_buy = bot_engine.trend_filter.check_alignment(tf_indicators, 'green')
trend_sell = bot_engine.trend_filter.check_alignment(tf_indicators, 'red')

print(f"\nBUY Trend (need all green):")
print(f"  Aligned: {trend_buy['aligned']}")
print(f"  Details: {trend_buy['details']}")
print(f"  Missing: {trend_buy['missing']}")

print(f"\nSELL Trend (need all red):")
print(f"  Aligned: {trend_sell['aligned']}")
print(f"  Details: {trend_sell['details']}")
print(f"  Missing: {trend_sell['missing']}")

print(f"\nTrend Summary: {bot_engine.trend_filter.get_trend_summary(tf_indicators)}")

# Show what equality_is_not_trend is set to
print("\n" + "="*80)
print("CONFIGURATION")
print("="*80)
print(f"equality_is_not_trend: {bot_engine.trend_filter.equality_is_not_trend}")

mt5.shutdown()
