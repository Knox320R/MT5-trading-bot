"""
Test daily bias calculation with specific candle example
"""

# Test case: Previous day's candle with long LOWER wick
test_candle = {
    'open': 1.1000,
    'high': 1.1050,
    'low': 1.0800,   # Long lower wick
    'close': 1.1010
}

o = test_candle['open']
h = test_candle['high']
l = test_candle['low']
c = test_candle['close']

# Calculate components
body = abs(c - o)
upper_wick = h - max(o, c)
lower_wick = min(o, c) - l

print("=" * 60)
print("DAILY BIAS CALCULATION TEST")
print("=" * 60)
print(f"Candle: O={o:.4f}, H={h:.4f}, L={l:.4f}, C={c:.4f}")
print()
print(f"Body size:       {body:.4f} = |{c:.4f} - {o:.4f}|")
print(f"Upper wick:      {upper_wick:.4f} = {h:.4f} - max({o:.4f}, {c:.4f})")
print(f"Lower wick:      {lower_wick:.4f} = min({o:.4f}, {c:.4f}) - {l:.4f}")
print()
print(f"Longest wick:    {max(upper_wick, lower_wick):.4f}")
print(f"Is small body?   {max(upper_wick, lower_wick) > body} (longest_wick > body)")
print()
print("LOGIC:")
print(f"  Lower wick ({lower_wick:.4f}) vs Upper wick ({upper_wick:.4f})")
print(f"  Lower wick is {'LONGER' if lower_wick > upper_wick else 'SHORTER'}")
print()

epsilon = 0.05
if lower_wick > upper_wick * (1 + epsilon):
    bias = 'BUY'
    print(f"RESULT: BUY day (long lower wick = buyers rejected lower prices)")
elif upper_wick > lower_wick * (1 + epsilon):
    bias = 'SELL'
    print(f"RESULT: SELL day (long upper wick = sellers rejected higher prices)")
else:
    bias = 'NEUTRAL'
    print(f"RESULT: NEUTRAL (wicks too similar)")

print()
print("=" * 60)
print()

# Now test with long UPPER wick (SELL day)
print("TEST 2: Long UPPER wick scenario")
test_candle2 = {
    'open': 1.1000,
    'high': 1.1200,   # Long upper wick
    'low': 1.0950,
    'close': 1.0990
}

o2 = test_candle2['open']
h2 = test_candle2['high']
l2 = test_candle2['low']
c2 = test_candle2['close']

body2 = abs(c2 - o2)
upper_wick2 = h2 - max(o2, c2)
lower_wick2 = min(o2, c2) - l2

print(f"Candle: O={o2:.4f}, H={h2:.4f}, L={l2:.4f}, C={c2:.4f}")
print(f"Body size:       {body2:.4f}")
print(f"Upper wick:      {upper_wick2:.4f}")
print(f"Lower wick:      {lower_wick2:.4f}")
print()

if lower_wick2 > upper_wick2 * (1 + epsilon):
    bias2 = 'BUY'
    print(f"RESULT: BUY day")
elif upper_wick2 > lower_wick2 * (1 + epsilon):
    bias2 = 'SELL'
    print(f"RESULT: SELL day")
else:
    bias2 = 'NEUTRAL'
    print(f"RESULT: NEUTRAL")

print("=" * 60)
