// ========================================
// TECHNICAL INDICATORS
// ========================================

function calculateEMA(prices, period) {
    if (!prices || prices.length === 0) return [];

    const k = 2 / (period + 1);
    const ema = [prices[0]];

    for (let i = 1; i < prices.length; i++) {
        ema.push(prices[i] * k + ema[i - 1] * (1 - k));
    }

    return ema;
}

function calculateSnakeColors(snakeValues, closePrices) {
    return snakeValues.map((value, index) =>
        value < closePrices[index] ? COLORS.bullish.border : COLORS.bearish.border
    );
}

function calculateIndicators(closePrices) {
    // Use AppState periods (user-adjustable via range inputs)
    const snakePeriod = AppState.snakePeriod || 100;
    const purplePeriod = AppState.purplePeriod || 10;

    const snake = calculateEMA(closePrices, snakePeriod);
    const purpleLine = calculateEMA(closePrices, purplePeriod);
    const snakeColors = calculateSnakeColors(snake, closePrices);

    return { snake, purpleLine, snakeColors };
}
