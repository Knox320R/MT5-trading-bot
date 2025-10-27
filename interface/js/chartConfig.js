// ========================================
// CHART CONFIGURATION FACTORY
// ========================================

// Custom plugin to draw candlestick wicks centered on bodies
const candlestickWickPlugin = {
    id: 'candlestickWick',
    afterDatasetsDraw: function(chart) {
        const ctx = chart.ctx;
        const wickMeta = chart.getDatasetMeta(0);
        const bodyMeta = chart.getDatasetMeta(1);
        const wickDataset = chart.data.datasets[0];

        // Don't draw if body is hidden or wick is disabled
        if (!wickMeta || !bodyMeta || bodyMeta.hidden) return;
        if (wickDataset._wickEnabled === false) return;

        const wickColors = wickDataset._wickColors || [];

        wickMeta.data.forEach((element, index) => {
            if (!element || element.skip) return;

            const wickData = chart.data.datasets[0].data[index];
            const bodyData = chart.data.datasets[1].data[index];

            if (!wickData || wickData.length !== 2) return;
            if (!bodyData || bodyData.length !== 2) return;

            const bodyBar = bodyMeta.data[index];
            if (!bodyBar) return;

            const x = bodyBar.x;
            const yLow = chart.scales.y.getPixelForValue(wickData[0]);
            const yHigh = chart.scales.y.getPixelForValue(wickData[1]);
            const wickColor = wickColors[index] || chart.data.datasets[1].backgroundColor[index];

            ctx.save();
            ctx.strokeStyle = wickColor;
            ctx.lineWidth = CHART_CONFIG.candleWickLineWidth;
            ctx.beginPath();
            ctx.moveTo(x, yLow);
            ctx.lineTo(x, yHigh);
            ctx.stroke();
            ctx.restore();
        });
    }
};

function createDatasetConfig() {
    return [
        {
            label: 'Candle Wick',
            type: 'bar',
            data: [],
            backgroundColor: COLORS.transparent,
            borderColor: COLORS.transparent,
            borderWidth: 0,
            barThickness: CHART_CONFIG.candleWickThickness,
            order: 3,
            xAxisID: 'x',
            yAxisID: 'y'
        },
        {
            label: 'Candle Body',
            type: 'bar',
            data: [],
            backgroundColor: [],
            borderColor: [],
            borderWidth: 1,
            barThickness: CHART_CONFIG.candleBodyThickness,
            order: 2,
            xAxisID: 'x',
            yAxisID: 'y'
        },
        {
            label: 'Close',
            type: 'line',
            data: [],
            borderColor: COLORS.primary,
            backgroundColor: 'rgba(0, 212, 255, 0.1)',
            borderWidth: 2,
            tension: 0.1,
            pointRadius: CHART_CONFIG.pointRadius,
            pointHoverRadius: CHART_CONFIG.pointHoverRadius,
            order: 0,
            hidden: true
        },
        {
            label: 'High',
            type: 'line',
            data: [],
            borderColor: '#ff0000',
            borderWidth: 1,
            pointRadius: CHART_CONFIG.pointRadius,
            pointHoverRadius: CHART_CONFIG.pointHoverRadius,
            tension: 0.1,
            order: 0,
            hidden: true
        },
        {
            label: 'Low',
            type: 'line',
            data: [],
            borderColor: '#00ff00',
            borderWidth: 1,
            pointRadius: CHART_CONFIG.pointRadius,
            pointHoverRadius: CHART_CONFIG.pointHoverRadius,
            tension: 0.1,
            order: 0,
            hidden: true
        },
        {
            label: 'Snake',
            type: 'line',
            data: [],
            borderWidth: 2,
            tension: 0.4,
            fill: false,
            pointRadius: CHART_CONFIG.pointRadius,
            pointHoverRadius: CHART_CONFIG.pointHoverRadius,
            order: 0,
            hidden: true
        },
        {
            label: 'Purple Line',
            type: 'line',
            data: [],
            borderColor: COLORS.purple,
            borderWidth: 2,
            tension: 0.4,
            fill: false,
            pointRadius: CHART_CONFIG.pointRadius,
            pointHoverRadius: CHART_CONFIG.pointHoverRadius,
            order: 0,
            hidden: true
        }
    ];
}

function createChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        animations: {
            tension: { duration: 0 }
        },
        transitions: {
            active: {
                animation: { duration: 0 }
            }
        },
        scales: {
            x: {
                grid: { color: COLORS.grid },
                ticks: {
                    color: COLORS.primary,
                    maxRotation: 45,
                    minRotation: 45
                }
            },
            y: {
                grid: { color: COLORS.grid },
                ticks: { color: COLORS.primary },
                beginAtZero: false
            }
        },
        plugins: {
            legend: {
                display: false
            },
            candlestickWick: true
        }
    };
}

function initializeChart(canvasId) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: createDatasetConfig()
        },
        options: createChartOptions(),
        plugins: [candlestickWickPlugin, tradeMarkerPlugin]
    });
}
