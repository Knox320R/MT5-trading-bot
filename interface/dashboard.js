// ========================================
// MAIN APPLICATION STATE
// ========================================

const AppState = {
    chart: null,
    historicalChart: null,
    wsManager: null,
    serverConfig: null,
    currentSymbol: null,
    currentTimeframe: null,
    signals: [],
    snakePeriod: 100,
    purplePeriod: 10
};

// ========================================
// TRADING FUNCTIONS
// ========================================

function executeTrade(action) {
    if (!AppState.wsManager.isConnected()) {
        alert('Not connected to server');
        return;
    }

    if (!AppState.currentSymbol) {
        alert('No symbol selected');
        return;
    }

    const confirmMsg = `Execute ${action.toUpperCase()} trade for ${AppState.currentSymbol}?`;
    if (!confirm(confirmMsg)) {
        return;
    }

    AppState.wsManager.send({
        command: 'execute_trade',
        action: action,
        symbol: AppState.currentSymbol
    });
}

function setupTradingButtons() {
    document.getElementById('buyBtn').addEventListener('click', () => {
        executeTrade('buy');
    });

    document.getElementById('sellBtn').addEventListener('click', () => {
        executeTrade('sell');
    });
}

// ========================================
// HISTORICAL DATA FUNCTIONS
// ========================================

function loadHistoricalData() {
    if (!AppState.wsManager.isConnected()) {
        alert('Not connected to server');
        return;
    }

    let date = document.getElementById('historicalDate').value;
    const timeframe = document.getElementById('historicalTimeframe').value;
    const endTime = document.getElementById('historicalEndTime')?.value || '23:59';

    // Default to today if no date selected
    if (!date) {
        const today = new Date();
        date = today.toISOString().split('T')[0]; // Format: YYYY-MM-DD
        document.getElementById('historicalDate').value = date;
    }

    // Combine date and end time to create datetime string
    const dateTimeStr = `${date}T${endTime}:00`;

    document.getElementById('historicalChartInfo').textContent = 'Loading...';

    AppState.wsManager.send({
        command: 'get_historical_data',
        date_to: dateTimeStr,  // Changed from 'date' to 'date_to' and use full datetime
        timeframe: timeframe,
        symbol: AppState.currentSymbol,
        bars_count: 100
    });
}

function setupHistoricalDataControls() {
    document.getElementById('loadHistoricalBtn').addEventListener('click', loadHistoricalData);
}

// ========================================
// PERIOD CONTROLS
// ========================================

function setupPeriodControls() {
    const snakePeriodInput = document.getElementById('snakePeriod');
    const purplePeriodInput = document.getElementById('purplePeriod');
    const snakePeriodValue = document.getElementById('snakePeriodValue');
    const purplePeriodValue = document.getElementById('purplePeriodValue');

    if (!snakePeriodInput || !purplePeriodInput) return;

    // Update Snake period
    snakePeriodInput.addEventListener('input', (e) => {
        const newPeriod = parseInt(e.target.value);
        snakePeriodValue.textContent = newPeriod;
        AppState.snakePeriod = newPeriod;

        // Send to server for bot strategy
        if (AppState.wsManager.isConnected()) {
            AppState.wsManager.send({
                command: 'set_indicator_period',
                indicator: 'snake',
                period: newPeriod
            });
        }

        // Recalculate and update chart if data exists
        if (AppState.chart && AppState.chart.data.labels.length > 0) {
            const closePrices = AppState.chart.data.datasets[2].data;
            const indicators = calculateIndicators(closePrices);

            AppState.chart.data.datasets[5].data = indicators.snake;
            AppState.chart.data.datasets[5].segment = {
                borderColor: (ctx) => indicators.snakeColors[ctx.p0DataIndex]
            };
            AppState.chart.data.datasets[5].pointBackgroundColor = indicators.snakeColors;
            AppState.chart.data.datasets[5].pointBorderColor = indicators.snakeColors;

            AppState.chart.update('none');
        }
    });

    // Update Purple period
    purplePeriodInput.addEventListener('input', (e) => {
        const newPeriod = parseInt(e.target.value);
        purplePeriodValue.textContent = newPeriod;
        AppState.purplePeriod = newPeriod;

        // Send to server for bot strategy
        if (AppState.wsManager.isConnected()) {
            AppState.wsManager.send({
                command: 'set_indicator_period',
                indicator: 'purple',
                period: newPeriod
            });
        }

        // Recalculate and update chart if data exists
        if (AppState.chart && AppState.chart.data.labels.length > 0) {
            const closePrices = AppState.chart.data.datasets[2].data;
            const indicators = calculateIndicators(closePrices);

            AppState.chart.data.datasets[6].data = indicators.purpleLine;

            AppState.chart.update('none');
        }
    });
}

// ========================================
// INITIALIZATION
// ========================================

function initializeApp() {
    // Initialize charts
    AppState.chart = initializeChart('priceChart');
    AppState.historicalChart = initializeChart('historicalChart');

    // Initialize WebSocket
    AppState.wsManager = new WebSocketManager();
    AppState.wsManager.connect();

    // Setup event handlers
    setupTradingButtons();
    setupHistoricalDataControls();
    setupChartToggles();
    setupHistoricalChartToggles();
    setupPeriodControls();
}

function setupChartToggles() {
    const toggles = [
        { id: 'toggleCandleWick', datasetIndex: 0, isWick: true },
        { id: 'toggleCandleBody', datasetIndex: 1 },
        { id: 'toggleClose', datasetIndex: 2 },
        { id: 'toggleHigh', datasetIndex: 3 },
        { id: 'toggleLow', datasetIndex: 4 },
        { id: 'toggleSnake', datasetIndex: 5 },
        { id: 'togglePurple', datasetIndex: 6 }
    ];

    toggles.forEach(toggle => {
        const checkbox = document.getElementById(toggle.id);
        if (checkbox && AppState.chart) {
            // Set initial checkbox state based on dataset visibility
            const dataset = AppState.chart.data.datasets[toggle.datasetIndex];

            // For wick, check if it's enabled via a custom flag (since the dataset stays visible)
            if (toggle.isWick) {
                checkbox.checked = dataset._wickEnabled !== false;
            } else {
                checkbox.checked = !dataset.hidden;
            }

            // Add change listener
            checkbox.addEventListener('change', (e) => {
                const isVisible = e.target.checked;

                if (toggle.isWick) {
                    // For wick: use custom flag and keep dataset visible to prevent bar repositioning
                    AppState.chart.data.datasets[toggle.datasetIndex]._wickEnabled = isVisible;
                } else {
                    // For other datasets: use normal hidden property
                    AppState.chart.data.datasets[toggle.datasetIndex].hidden = !isVisible;
                }

                AppState.chart.update('none');
            });
        }
    });
}

function setupHistoricalChartToggles() {
    const toggles = [
        { id: 'toggleHistoricalWick', datasetIndex: 0, isWick: true },
        { id: 'toggleHistoricalBody', datasetIndex: 1 },
        { id: 'toggleHistoricalClose', datasetIndex: 2 },
        { id: 'toggleHistoricalHigh', datasetIndex: 3 },
        { id: 'toggleHistoricalLow', datasetIndex: 4 },
        { id: 'toggleHistoricalSnake', datasetIndex: 5 },
        { id: 'toggleHistoricalPurple', datasetIndex: 6 }
    ];

    toggles.forEach(toggle => {
        const checkbox = document.getElementById(toggle.id);
        if (checkbox && AppState.historicalChart) {
            // Set initial checkbox state based on dataset visibility
            const dataset = AppState.historicalChart.data.datasets[toggle.datasetIndex];

            // For wick, check if it's enabled via a custom flag (since the dataset stays visible)
            if (toggle.isWick) {
                checkbox.checked = dataset._wickEnabled !== false;
            } else {
                checkbox.checked = !dataset.hidden;
            }

            // Add change listener
            checkbox.addEventListener('change', (e) => {
                const isVisible = e.target.checked;

                if (toggle.isWick) {
                    // For wick: use custom flag and keep dataset visible to prevent bar repositioning
                    AppState.historicalChart.data.datasets[toggle.datasetIndex]._wickEnabled = isVisible;
                } else {
                    // For other datasets: use normal hidden property
                    AppState.historicalChart.data.datasets[toggle.datasetIndex].hidden = !isVisible;
                }

                AppState.historicalChart.update('none');
            });
        }
    });
}

// Start application when DOM is ready
document.addEventListener('DOMContentLoaded', initializeApp);
