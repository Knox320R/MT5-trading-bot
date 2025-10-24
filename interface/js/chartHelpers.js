// ========================================
// CHART DATA PROCESSING HELPERS
// ========================================

function processCandlestickData(bars) {
    return {
        wicks: bars.map(bar => [bar.low, bar.high]),
        bodies: bars.map(bar => [Math.min(bar.open, bar.close), Math.max(bar.open, bar.close)]),
        colors: {
            body: bars.map(bar => bar.close >= bar.open ? COLORS.bullish.body : COLORS.bearish.body),
            border: bars.map(bar => bar.close >= bar.open ? COLORS.bullish.border : COLORS.bearish.border),
            wick: bars.map(bar => bar.close >= bar.open ? COLORS.bullish.wick : COLORS.bearish.wick)
        }
    };
}

function extractPriceData(bars) {
    return {
        labels: bars.map(bar => bar.time),
        close: bars.map(bar => bar.close),
        high: bars.map(bar => bar.high),
        low: bars.map(bar => bar.low)
    };
}

function calculateYAxisRange(highPrices, lowPrices, paddingPercent = 0.1) {
    const allPrices = [...highPrices, ...lowPrices];
    const minPrice = Math.min(...allPrices);
    const maxPrice = Math.max(...allPrices);
    const padding = (maxPrice - minPrice) * paddingPercent;

    return {
        min: minPrice - padding,
        max: maxPrice + padding
    };
}

function updateChartData(chartInstance, bars, updateUI = null) {
    console.log('[chartHelpers] updateChartData called', {
        chartInstance: !!chartInstance,
        barsCount: bars?.length,
        updateUI: !!updateUI
    });

    if (!chartInstance) {
        console.error('[chartHelpers] No chart instance provided');
        return;
    }

    if (!bars || bars.length === 0) {
        console.error('[chartHelpers] No bars data provided');
        return;
    }

    // Extract price data
    const priceData = extractPriceData(bars);

    // Process candlestick data
    const candleData = processCandlestickData(bars);

    // Calculate indicators
    const indicators = calculateIndicators(priceData.close);

    // Update chart labels
    chartInstance.data.labels = priceData.labels;

    // Update candlestick datasets
    chartInstance.data.datasets[0].data = candleData.wicks;
    chartInstance.data.datasets[0]._wickColors = candleData.colors.wick;
    chartInstance.data.datasets[1].data = candleData.bodies;
    chartInstance.data.datasets[1].backgroundColor = candleData.colors.body;
    chartInstance.data.datasets[1].borderColor = candleData.colors.border;

    // Update line datasets
    chartInstance.data.datasets[2].data = priceData.close;
    chartInstance.data.datasets[3].data = priceData.high;
    chartInstance.data.datasets[4].data = priceData.low;
    chartInstance.data.datasets[5].data = indicators.snake;
    chartInstance.data.datasets[5].segment = {
        borderColor: (ctx) => indicators.snakeColors[ctx.p0DataIndex]
    };
    chartInstance.data.datasets[5].pointBackgroundColor = indicators.snakeColors;
    chartInstance.data.datasets[5].pointBorderColor = indicators.snakeColors;
    chartInstance.data.datasets[6].data = indicators.purpleLine;

    // Update Y-axis range
    const yRange = calculateYAxisRange(priceData.high, priceData.low);
    chartInstance.options.scales.y.min = yRange.min;
    chartInstance.options.scales.y.max = yRange.max;

    // Update UI if callback provided
    if (updateUI) {
        updateUI();
    }

    // Update chart without animation
    chartInstance.update('none');
}
