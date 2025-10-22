// Global variables
let ws = null;
let chart = null;
let reconnectInterval = null;
let currentPort = 8765;
const portsToTry = [8765, 8766, 8767, 8768, 8769];
let serverConfig = null; // Will be loaded from server

// Chart configuration
const CHART_POINT_RADIUS = 1.3;  // Global point radius for all curves
const CHART_POINT_HOVER_RADIUS = 5;  // Point radius on hover

// Initialize Chart.js
function initializeChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Close',
                    data: [],
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS
                },
                {
                    label: 'High',
                    data: [],
                    borderColor: '#ffe100',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    fill: false,
                    hidden: false,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS
                },
                {
                    label: 'Low',
                    data: [],
                    borderColor: '#00bbff',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    fill: false,
                    hidden: false,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS
                },
                {
                    label: 'Snake (EMA 100)',
                    data: [],
                    borderColor: '#ffaa00',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS,
                    pointBackgroundColor: [],
                    pointBorderColor: [],
                    segment: {}
                },
                {
                    label: 'Purple Line (EMA 10)',
                    data: [],
                    borderColor: '#9900ff',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false, // Disable all animations
            animations: {
                tension: {
                    duration: 0
                }
            },
            transitions: {
                active: {
                    animation: {
                        duration: 0
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#00d4ff',
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#00d4ff'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#00d4ff'
                    }
                }
            }
        }
    });
}

// Connect to WebSocket server
function connectWebSocket(portIndex = 0) {
    if (portIndex >= portsToTry.length) {
        showError('Could not connect to server on any port. Make sure realtime_server.py is running.');
        return;
    }

    currentPort = portsToTry[portIndex];
    console.log(`Attempting to connect to port ${currentPort}...`);

    ws = new WebSocket(`ws://127.0.0.1:${currentPort}`);

    ws.onopen = () => {
        console.log(`Connected to MT5 server on port ${currentPort}`);
        document.getElementById('statusIndicator').textContent = 'CONNECTED';
        document.getElementById('statusIndicator').className = 'status connected';
        clearInterval(reconnectInterval);
        showError('');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
    };

    ws.onclose = () => {
        console.log('Disconnected from MT5 server');
        document.getElementById('statusIndicator').textContent = 'DISCONNECTED';
        document.getElementById('statusIndicator').className = 'status disconnected';

        // Try to reconnect every 3 seconds
        if (!reconnectInterval) {
            reconnectInterval = setInterval(() => {
                console.log('Attempting to reconnect...');
                connectWebSocket();
            }, 3000);
        }
    };

    ws.onerror = (error) => {
        console.error(`WebSocket error on port ${currentPort}:`, error);
        // Try next port
        setTimeout(() => connectWebSocket(portIndex + 1), 500);
    };
}

// Handle messages from server
function handleServerMessage(data) {
    if (data.type === 'market_update') {
        updateMarketData(data);
    } else if (data.type === 'error') {
        showError(data.message);
    } else if (data.type === 'config') {
        // Received config from server
        serverConfig = data.data;
        console.log('Received config from server:', serverConfig);
        updateUIFromConfig();
    }
}

// Update UI elements based on config
function updateUIFromConfig() {
    if (!serverConfig) return;

    // Update page title
    if (serverConfig.dashboard_title) {
        document.querySelector('h1').childNodes[0].textContent = serverConfig.dashboard_title + ' ';
    }

    // Update symbol dropdown
    if (serverConfig.symbols) {
        const symbolSelect = document.getElementById('symbolSelect');
        symbolSelect.innerHTML = '';

        serverConfig.symbols.forEach(symbol => {
            const option = document.createElement('option');
            option.value = symbol;
            option.textContent = symbol;
            if (symbol === serverConfig.default_symbol) {
                option.selected = true;
            }
            symbolSelect.appendChild(option);
        });
    }

    // Update timeframe dropdown
    if (serverConfig.timeframes) {
        const timeframeSelect = document.getElementById('timeframeSelect');
        timeframeSelect.innerHTML = '';

        const timeframeLabels = {
            'M1': 'M1 (1 Minute)',
            'M5': 'M5 (5 Minutes)',
            'M15': 'M15 (15 Minutes)',
            'M30': 'M30 (30 Minutes)',
            'H1': 'H1 (1 Hour)',
            'H4': 'H4 (4 Hours)',
            'D1': 'D1 (1 Day)'
        };

        serverConfig.timeframes.forEach(tf => {
            const option = document.createElement('option');
            option.value = tf;
            option.textContent = timeframeLabels[tf] || tf;
            if (tf === serverConfig.default_timeframe) {
                option.selected = true;
            }
            timeframeSelect.appendChild(option);
        });
    }

    // Show environment mode
    if (serverConfig.environment) {
        const envBadge = document.createElement('span');
        envBadge.style.cssText = 'margin-left: 10px; padding: 5px 10px; background: ' +
            (serverConfig.environment === 'demo' ? '#ff9800' : '#f44336') +
            '; border-radius: 3px; font-size: 12px;';
        envBadge.textContent = serverConfig.environment.toUpperCase();
        document.querySelector('h1').appendChild(envBadge);
    }
}

// Update market data on the dashboard
function updateMarketData(data) {
    // Update tick data
    if (data.tick) {
        document.getElementById('bidPrice').textContent = data.tick.bid.toFixed(2);
        document.getElementById('askPrice').textContent = data.tick.ask.toFixed(2);
        document.getElementById('spread').textContent = data.tick.spread.toFixed(2);

        // Add updating animation
        ['bidPrice', 'askPrice', 'spread'].forEach(id => {
            const el = document.getElementById(id);
            el.classList.add('updating');
            setTimeout(() => el.classList.remove('updating'), 2000);
        });
    }

    // Update account data
    if (data.account) {
        document.getElementById('balance').textContent = data.account.balance.toFixed(2);
        document.getElementById('equity').textContent = data.account.equity.toFixed(2);

        const profitEl = document.getElementById('profit');
        profitEl.textContent = data.account.profit.toFixed(2);
        profitEl.className = 'card-value ' + (data.account.profit >= 0 ? 'positive' : 'negative');
    }

    // Update chart with bars data
    if (data.bars && data.bars.length > 0) {
        updateChart(data.bars, data.symbol, data.timeframe);
    }

    // Update positions
    if (data.positions) {
        updatePositions(data.positions);
    }

    // Clear any error messages
    showError('');
}

// Calculate EMA (Exponential Moving Average)
function calculateEMA(data, period) {
    const ema = [];
    const multiplier = 2 / (period + 1);

    // Start with SMA for first value
    let sum = 0;
    for (let i = 0; i < period && i < data.length; i++) {
        sum += data[i];
    }
    let previousEMA = sum / Math.min(period, data.length);
    ema.push(previousEMA);

    // Calculate EMA for remaining values
    for (let i = 1; i < data.length; i++) {
        const currentEMA = (data[i] - previousEMA) * multiplier + previousEMA;
        ema.push(currentEMA);
        previousEMA = currentEMA;
    }

    return ema;
}

// Get Snake color segments based on price comparison
function getSnakeColorSegments(closePrices, snakeValues) {
    const segments = [];
    let currentColor = null;
    let currentSegment = [];

    for (let i = 0; i < closePrices.length; i++) {
        // Green when snake is below price, Red when above price
        const color = snakeValues[i] < closePrices[i] ? '#00ff00' : '#ff0000';

        if (color !== currentColor) {
            if (currentSegment.length > 0) {
                segments.push({ color: currentColor, data: currentSegment });
            }
            currentColor = color;
            currentSegment = [snakeValues[i]];
        } else {
            currentSegment.push(snakeValues[i]);
        }
    }

    if (currentSegment.length > 0) {
        segments.push({ color: currentColor, data: currentSegment });
    }

    return segments;
}

// Update chart with candlestick data
function updateChart(bars, symbol, timeframe) {
    document.getElementById('chartSymbol').textContent = symbol;
    document.getElementById('chartTimeframe').textContent = timeframe;

    // Extract data from bars
    const labels = bars.map(bar => bar.time);
    const closePrices = bars.map(bar => bar.close);
    const highPrices = bars.map(bar => bar.high);
    const lowPrices = bars.map(bar => bar.low);

    // Calculate EMAs
    const snake = calculateEMA(closePrices, 100);  // Snake: EMA 100
    const purpleLine = calculateEMA(closePrices, 10);  // Purple Line: EMA 10

    // Create color array for each Snake point
    const snakeColors = snake.map((value, index) => {
        // Green when snake is below price, Red when above price
        return value < closePrices[index] ? '#00ff00' : '#ff0000';
    });

    // Update labels
    chart.data.labels = labels;

    // Update only the data arrays, not the entire dataset objects
    chart.data.datasets[0].data = closePrices;
    chart.data.datasets[1].data = highPrices;
    chart.data.datasets[2].data = lowPrices;
    chart.data.datasets[3].data = snake;
    chart.data.datasets[3].segment = {
        borderColor: (ctx) => {
            // Color each segment based on the point colors
            const index = ctx.p0DataIndex;
            return snakeColors[index];
        }
    };
    chart.data.datasets[3].pointBackgroundColor = snakeColors;  // Point (node) colors
    chart.data.datasets[3].pointBorderColor = snakeColors;  // Point border colors
    chart.data.datasets[4].data = purpleLine;

    // Update without animation
    chart.update('none');
}

// Update positions table
function updatePositions(positions) {
    const container = document.getElementById('positionsContainer');

    if (positions.length === 0) {
        container.innerHTML = '<div class="no-data">No open positions</div>';
        return;
    }

    let html = '<table class="positions-table">';
    html += '<thead><tr><th>Ticket</th><th>Type</th><th>Symbol</th><th>Volume</th><th>Open Price</th><th>Current Price</th><th>Profit</th></tr></thead>';
    html += '<tbody>';

    positions.forEach(pos => {
        html += `<tr>
            <td>${pos.ticket}</td>
            <td class="type-${pos.type.toLowerCase()}">${pos.type}</td>
            <td>${pos.symbol}</td>
            <td>${pos.volume}</td>
            <td>${pos.price_open.toFixed(4)}</td>
            <td>${pos.price_current.toFixed(4)}</td>
            <td class="${pos.profit >= 0 ? 'type-buy' : 'type-sell'}">${pos.profit.toFixed(2)}</td>
        </tr>`;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// Show error message
function showError(message) {
    const container = document.getElementById('errorContainer');
    if (message) {
        container.innerHTML = `<div class="error-message">${message}</div>`;
    } else {
        container.innerHTML = '';
    }
}

// Event listeners
function setupEventListeners() {
    // Handle symbol change
    document.getElementById('symbolSelect').addEventListener('change', (e) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                command: 'set_symbol',
                symbol: e.target.value
            }));
        }
    });

    // Handle timeframe change
    document.getElementById('timeframeSelect').addEventListener('change', (e) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                command: 'set_timeframe',
                timeframe: e.target.value
            }));
        }
    });
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    initializeChart();
    setupEventListeners();
    connectWebSocket();
});
