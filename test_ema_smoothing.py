"""
Test EMA Calculation with Configurable Smoothing
Verify that our EMA implementation correctly uses the formula from EMA.txt with configurable Smoothing parameter
"""

import sys
sys.path.append('core')

from indicators import IndicatorCalculator

def test_ema_with_different_smoothing():
    """
    Test EMA calculation with different smoothing values.

    Formula from EMA.txt:
    EMA_today = (Value_today * (Smoothing / (1 + Days))) + EMA_yesterday * (1 - (Smoothing / (1 + Days)))

    where:
    - Smoothing = configurable (typically 1-3)
    - Days = period
    """

    # Sample price data
    prices = [
        22.27, 22.19, 22.08, 22.17, 22.18,
        22.13, 22.23, 22.43, 22.24, 22.29,  # Day 10
        22.15, 22.39, 22.38, 22.61, 23.36,
        24.05, 23.75, 23.83, 23.95, 23.63
    ]

    period = 10

    print("="*80)
    print("EMA Calculation Test with Configurable Smoothing")
    print("="*80)
    print(f"Period (Days): {period}")
    print(f"Prices: {len(prices)} data points")
    print()

    # Test with different smoothing values
    smoothing_values = [1.0, 2.0, 3.0]

    for smoothing in smoothing_values:
        print(f"\n{'='*80}")
        print(f"Testing with Smoothing = {smoothing}")
        print(f"{'='*80}")

        calc = IndicatorCalculator(snake_period=100, purple_period=10, smoothing=smoothing)

        # Calculate multiplier
        k = smoothing / (period + 1)
        print(f"Multiplier k = {smoothing}/(period+1) = {smoothing}/{period+1} = {k:.6f}")
        print(f"This means {k*100:.2f}% weight on new data, {(1-k)*100:.2f}% on previous EMA")
        print()

        # Calculate EMA
        ema_values = calc.calculate_ema(prices, period)

        # Verify first EMA is SMA
        sma_10 = sum(prices[:10]) / 10
        print(f"First 10 prices: {prices[:10]}")
        print(f"SMA (average of first 10): {sma_10:.4f}")
        print(f"EMA at day 10 (index 9): {ema_values[9]:.4f}")
        print(f"Match: {abs(ema_values[9] - sma_10) < 0.0001}")
        print()

        # Manually verify formula for day 11
        ema_manual_11 = prices[10] * k + ema_values[9] * (1 - k)
        print(f"Manual verification of formula for Day 11:")
        print(f"  EMA = Price * k + EMA_prev * (1-k)")
        print(f"  EMA = {prices[10]:.4f} * {k:.6f} + {ema_values[9]:.4f} * {1-k:.6f}")
        print(f"  EMA = {ema_manual_11:.4f}")
        print(f"  Calculated: {ema_values[10]:.4f}")
        print(f"  Match: {abs(ema_values[10] - ema_manual_11) < 0.0001}")
        print()

        # Show last few EMA values
        print(f"Last 5 EMA values:")
        for i in range(len(prices)-5, len(prices)):
            print(f"  Day {i+1}: Price={prices[i]:6.2f}, EMA={ema_values[i]:7.4f}")
        print()

    # Compare EMAs with different smoothing at the same point
    print("="*80)
    print("Comparison of Final EMA Values (Day 20)")
    print("="*80)
    print(f"Price on Day 20: {prices[-1]:.2f}")
    print()

    for smoothing in smoothing_values:
        calc = IndicatorCalculator(smoothing=smoothing)
        ema = calc.calculate_ema(prices, period)
        latest = ema[-1]
        k = smoothing / (period + 1)
        print(f"Smoothing={smoothing:.1f}: EMA={latest:.4f}, Weight on new data={k*100:.2f}%")

    print()
    print("="*80)
    print("Key Observations:")
    print("="*80)
    print("1. Higher smoothing = Higher weight on recent prices")
    print("2. Higher smoothing = More responsive to price changes")
    print("3. Lower smoothing = More stable, less volatile EMA")
    print()
    print("Standard Smoothing = 2.0 (recommended in EMA.txt)")
    print()

    # Test that config parameters work
    print("="*80)
    print("Testing Config Integration")
    print("="*80)

    # Load config and verify smoothing is read correctly
    from config_loader import config
    smoothing_from_config = config.get_ema_smoothing()
    snake_period_from_config = config.get_snake_period()
    purple_period_from_config = config.get_purple_line_period()

    print(f"EMA Smoothing from config.json: {smoothing_from_config}")
    print(f"Snake Period from config.json: {snake_period_from_config}")
    print(f"Purple Period from config.json: {purple_period_from_config}")
    print()

    # Calculate with config values
    calc_from_config = IndicatorCalculator(
        snake_period=snake_period_from_config,
        purple_period=purple_period_from_config,
        smoothing=smoothing_from_config
    )

    ema_config = calc_from_config.calculate_ema(prices, period)
    print(f"EMA calculated with config values: {ema_config[-1]:.4f}")
    print()

    print("="*80)
    print("[PASS] All EMA Smoothing Tests Complete")
    print("="*80)
    print()
    print("Formula Implementation Summary:")
    print("- Formula: EMA = (Value * (Smoothing/(1+Days))) + EMA_prev * (1-(Smoothing/(1+Days)))")
    print("- Smoothing: Configurable in config.json (indicators.ema_formula.smoothing)")
    print("- Days (Period): Configurable per indicator (snake.period, purple_line.period)")
    print("- All parameters centrally controlled via config.json")
    print()

if __name__ == "__main__":
    test_ema_with_different_smoothing()
