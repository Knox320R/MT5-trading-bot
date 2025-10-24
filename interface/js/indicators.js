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
    const snakePeriod = AppState.serverConfig?.indicators?.snake_period || 100;
    const purplePeriod = AppState.serverConfig?.indicators?.purple_line_period || 10;

    const snake = calculateEMA(closePrices, snakePeriod);
    const purpleLine = calculateEMA(closePrices, purplePeriod);
    const snakeColors = calculateSnakeColors(snake, closePrices);

    return { snake, purpleLine, snakeColors };
}
