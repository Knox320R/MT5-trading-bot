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
    signals: []
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
// INITIALIZATION
// ========================================

function initializeApp() {
    // Initialize charts
    AppState.chart = initializeChart('priceChart', COLORS.primary);
    AppState.historicalChart = initializeChart('historicalChart', COLORS.white);

    // Initialize WebSocket
    AppState.wsManager = new WebSocketManager();
    AppState.wsManager.connect();

    // Setup event handlers
    setupTradingButtons();
    setupHistoricalDataControls();
}

// Start application when DOM is ready
document.addEventListener('DOMContentLoaded', initializeApp);
