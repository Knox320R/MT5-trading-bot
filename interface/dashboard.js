// Global variables
let ws = null;
let chart = null;
let historicalChart = null;
let reconnectInterval = null;
let currentPort = 8765;
const portsToTry = [8765, 8766, 8767, 8768, 8769];
let serverConfig = null; // Will be loaded from server
let currentSymbol = null; // Track current symbol
let currentTimeframe = null; // Track current timeframe
let signals = []; // Store signals
let maxSignals = 20; // Maximum number of signals to display

// Chart configuration
const CHART_POINT_RADIUS = 1;  // Global point radius for all curves
const CHART_POINT_HOVER_RADIUS = 3;  // Point radius on hover

// Custom plugin to draw candlestick wicks centered on bodies
const candlestickWickPlugin = {
    id: 'candlestickWick',
    afterDatasetsDraw: function(chart) {
        const ctx = chart.ctx;
        const meta = chart.getDatasetMeta(0); // Wick dataset
        const bodyMeta = chart.getDatasetMeta(1); // Body dataset

        if (!meta || !bodyMeta || meta.hidden || bodyMeta.hidden) return;

        // Get wick colors from custom property or body colors
        const wickColors = chart.data.datasets[0]._wickColors || [];

        meta.data.forEach((element, index) => {
            if (!element || element.skip) return;

            const wickData = chart.data.datasets[0].data[index];
            const bodyData = chart.data.datasets[1].data[index];

            if (!wickData || wickData.length !== 2) return;
            if (!bodyData || bodyData.length !== 2) return;

            // Get the body bar x position (center)
            const bodyBar = bodyMeta.data[index];
            if (!bodyBar) return;

            const x = bodyBar.x;
            const yLow = chart.scales.y.getPixelForValue(wickData[0]);
            const yHigh = chart.scales.y.getPixelForValue(wickData[1]);

            // Get color from stored colors or body colors
            const wickColor = wickColors[index] || chart.data.datasets[1].backgroundColor[index];

            // Draw wick as a thin line centered on the body
            ctx.save();
            ctx.strokeStyle = wickColor;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(x, yLow);
            ctx.lineTo(x, yHigh);
            ctx.stroke();
            ctx.restore();
        });
    }
};

// Initialize Chart.js
function initializeChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Candle Wick',
                    type: 'bar',
                    data: [],
                    backgroundColor: 'rgba(0,0,0,0)',
                    borderColor: 'rgba(0,0,0,0)',
                    borderWidth: 0,
                    barThickness: 1,
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
                    barThickness: 8,
                    order: 2,
                    xAxisID: 'x',
                    yAxisID: 'y'
                },
                {
                    label: 'Close',
                    type: 'line',
                    data: [],
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS,
                    order: 0,
                    hidden: true
                },
                {
                    label: 'High',
                    type: 'line',
                    data: [],
                    borderColor: '#ffe100',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    fill: false,
                    hidden: true,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS,
                    order: 0
                },
                {
                    label: 'Low',
                    type: 'line',
                    data: [],
                    borderColor: '#00bbff',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    fill: false,
                    hidden: true,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS,
                    order: 0
                },
                {
                    label: 'Snake (EMA 100)',
                    type: 'line',
                    data: [],
                    borderColor: '#ffaa00',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS,
                    pointBackgroundColor: [],
                    pointBorderColor: [],
                    segment: {},
                    order: 0,
                    hidden: true
                },
                {
                    label: 'Purple Line (EMA 10)',
                    type: 'line',
                    data: [],
                    borderColor: '#9900ff',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS,
                    order: 0,
                    hidden: true
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
                    },
                    beginAtZero: false
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#00d4ff'
                    }
                },
                candlestickWick: true
            }
        },
        plugins: [candlestickWickPlugin]
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
    } else if (data.type === 'trading_signal') {
        // Received trading signal
        console.log('Received trading signal:', data.signal);
        addSignal(data.signal);
    } else if (data.type === 'historical_data') {
        // Received historical data
        console.log('Received historical data:', data.bars_count, 'bars');
        updateHistoricalChart(data);
    } else if (data.type === 'trade_success') {
        // Trade executed successfully
        const tradeData = data.data;
        const message = `✓ ${tradeData.action.toUpperCase()} order executed!\nSymbol: ${tradeData.symbol}\nVolume: ${tradeData.volume}\nPrice: ${tradeData.price}\nOrder #: ${tradeData.order}`;
        alert(message);
        console.log('Trade success:', tradeData);
        showError(''); // Clear any previous errors
    }
}

// Update UI elements based on config
function updateUIFromConfig() {
    if (!serverConfig) return;

    // Set current symbol and timeframe from config
    currentSymbol = serverConfig.default_symbol;
    currentTimeframe = serverConfig.default_timeframe;

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

    // Create candlestick wicks (shadows) - thin lines from low to high
    const candleWicks = bars.map(bar => {
        return [bar.low, bar.high];
    });

    // Create candlestick bodies (bar chart data showing open to close)
    // Using floating bar format: [min, max]
    const candleBodies = bars.map(bar => {
        return [Math.min(bar.open, bar.close), Math.max(bar.open, bar.close)];
    });

    // Create colors for candles (green if close > open, red if close < open)
    const candleColors = bars.map(bar => {
        return bar.close >= bar.open ? 'rgba(0, 255, 0, 0.8)' : 'rgba(255, 0, 0, 0.8)';
    });

    const candleBorderColors = bars.map(bar => {
        return bar.close >= bar.open ? '#00ff00' : '#ff0000';
    });

    // Wick colors - same as body colors but for the thin line
    const wickColors = bars.map(bar => {
        return bar.close >= bar.open ? 'rgba(0, 255, 0, 1)' : 'rgba(255, 0, 0, 1)';
    });

    // Calculate EMAs from server config
    const snakePeriod = serverConfig?.indicators?.snake_period || 100;
    const purplePeriod = serverConfig?.indicators?.purple_line_period || 10;
    const snake = calculateEMA(closePrices, snakePeriod);
    const purpleLine = calculateEMA(closePrices, purplePeriod);

    // Create color array for each Snake point
    const snakeColors = snake.map((value, index) => {
        // Green when snake is below price, Red when above price
        return value < closePrices[index] ? '#00ff00' : '#ff0000';
    });

    // Update labels
    chart.data.labels = labels;

    // Update candlestick wicks (thin lines from low to high)
    chart.data.datasets[0].data = candleWicks;
    chart.data.datasets[0]._wickColors = wickColors; // Store colors for plugin

    // Update candlestick bodies (thick bars from open to close)
    chart.data.datasets[1].data = candleBodies;
    chart.data.datasets[1].backgroundColor = candleColors;
    chart.data.datasets[1].borderColor = candleBorderColors;

    // Update line datasets (indices shifted by +1 due to wick dataset)
    chart.data.datasets[2].data = closePrices;
    chart.data.datasets[3].data = highPrices;
    chart.data.datasets[4].data = lowPrices;
    chart.data.datasets[5].data = snake;
    chart.data.datasets[5].segment = {
        borderColor: (ctx) => {
            const index = ctx.p0DataIndex;
            return snakeColors[index];
        }
    };
    chart.data.datasets[5].pointBackgroundColor = snakeColors;
    chart.data.datasets[5].pointBorderColor = snakeColors;
    chart.data.datasets[6].data = purpleLine;

    // Calculate Y-axis range to zoom in on the price action
    const allPrices = [...highPrices, ...lowPrices];
    const minPrice = Math.min(...allPrices);
    const maxPrice = Math.max(...allPrices);
    const padding = (maxPrice - minPrice) * 0.1; // 10% padding

    chart.options.scales.y.min = minPrice - padding;
    chart.options.scales.y.max = maxPrice + padding;

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

// Add signal to list
function addSignal(signal) {
    // Add to beginning of array
    signals.unshift(signal);

    // Keep only last N signals
    if (signals.length > maxSignals) {
        signals.pop();
    }

    // Update display
    updateSignalsList();
}

// Update signals list display
function updateSignalsList() {
    const container = document.getElementById('signalsListBox');

    if (signals.length === 0) {
        container.innerHTML = '<div class="no-data">Waiting for signals...</div>';
        return;
    }

    let html = '';
    signals.forEach(signal => {
        const signalType = signal.type.includes('BUY') ? 'buy' : 'sell';
        const timestamp = new Date(signal.timestamp).toLocaleString();

        html += `
            <div class="signal-item ${signalType}">
                <div class="signal-header">
                    <div class="signal-type ${signalType}">${signal.type.replace('_', ' ')}</div>
                    <div class="signal-time">${timestamp}</div>
                </div>
                <div class="signal-symbol">${signal.symbol}</div>
                <div class="signal-price">
                    <span class="signal-price-label">Price:</span> ${signal.price ? signal.price.toFixed(5) : '--'}
                </div>
                <div class="signal-conditions">
                    ${signal.reasons.map(reason => `<div class="signal-condition met">${reason}</div>`).join('')}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;

    // Auto-scroll to top (newest signal)
    container.scrollTop = 0;
}

// Clear all signals
function clearSignals() {
    signals = [];
    updateSignalsList();
}

// Execute manual trade
function executeTrade(action) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        alert('Not connected to server');
        return;
    }

    if (!currentSymbol) {
        alert('No symbol selected');
        return;
    }

    // Confirm trade
    const confirmMsg = `Execute ${action.toUpperCase()} trade for ${currentSymbol}?`;
    if (!confirm(confirmMsg)) {
        return;
    }

    console.log(`Executing ${action} trade for ${currentSymbol}`);

    // Send trade command to server
    ws.send(JSON.stringify({
        command: 'execute_trade',
        action: action,
        symbol: currentSymbol
    }));
}

// Event listeners
function setupEventListeners() {
    // Handle symbol change
    document.getElementById('symbolSelect').addEventListener('change', (e) => {
        currentSymbol = e.target.value;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                command: 'set_symbol',
                symbol: e.target.value
            }));
        }
    });

    // Handle timeframe change
    document.getElementById('timeframeSelect').addEventListener('change', (e) => {
        currentTimeframe = e.target.value;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                command: 'set_timeframe',
                timeframe: e.target.value
            }));
        }
    });

    // Handle Clear Signals button
    document.getElementById('clearSignalsBtn').addEventListener('click', () => {
        clearSignals();
    });

    // Handle Buy button
    document.getElementById('buyBtn').addEventListener('click', () => {
        executeTrade('buy');
    });

    // Handle Sell button
    document.getElementById('sellBtn').addEventListener('click', () => {
        executeTrade('sell');
    });
}

// Initialize Historical Chart
function initializeHistoricalChart() {
    const ctx = document.getElementById('historicalChart').getContext('2d');
    historicalChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Candle Wick',
                    type: 'bar',
                    data: [],
                    backgroundColor: 'rgba(0,0,0,0)',
                    borderColor: 'rgba(0,0,0,0)',
                    borderWidth: 0,
                    barThickness: 1,
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
                    barThickness: 8,
                    order: 2,
                    xAxisID: 'x',
                    yAxisID: 'y'
                },
                {
                    label: 'Close',
                    type: 'line',
                    data: [],
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS,
                    order: 0,
                    hidden: true
                },
                {
                    label: 'High',
                    type: 'line',
                    data: [],
                    borderColor: '#ffe100',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    fill: false,
                    hidden: true,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS,
                    order: 0
                },
                {
                    label: 'Low',
                    type: 'line',
                    data: [],
                    borderColor: '#00bbff',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    fill: false,
                    hidden: true,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS,
                    order: 0
                },
                {
                    label: 'Snake (EMA 100)',
                    type: 'line',
                    data: [],
                    borderColor: '#ffaa00',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS,
                    pointBackgroundColor: [],
                    pointBorderColor: [],
                    segment: {},
                    order: 0,
                    hidden: true
                },
                {
                    label: 'Purple Line (EMA 10)',
                    type: 'line',
                    data: [],
                    borderColor: '#9900ff',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false,
                    pointRadius: CHART_POINT_RADIUS,
                    pointHoverRadius: CHART_POINT_HOVER_RADIUS,
                    order: 0,
                    hidden: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
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
                    },
                    beginAtZero: false
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#ffffff'
                    }
                },
                candlestickWick: true
            }
        },
        plugins: [candlestickWickPlugin]
    });
}

// Load Historical Data
function loadHistoricalData() {
    const dateInput = document.getElementById('historicalDate').value;
    const endTime = document.getElementById('historicalEndTime').value;
    const timeframe = document.getElementById('historicalTimeframe').value;

    if (!dateInput) {
        alert('Please select a date');
        return;
    }

    // Calculate exact number of bars needed based on timeframe
    // Fetch only what's needed to display on the chart
    let barsToFetch;

    switch(timeframe) {
        case 'M1':
            barsToFetch = 60;   // 1 hour of M1 bars
            break;
        case 'M5':
            barsToFetch = 72;   // 6 hours of M5 bars
            break;
        case 'M15':
            barsToFetch = 96;   // 1 day of M15 bars
            break;
        case 'M30':
            barsToFetch = 48;   // 1 day of M30 bars
            break;
        case 'H1':
            barsToFetch = 24;   // 1 day of H1 bars
            break;
        case 'H4':
            barsToFetch = 42;   // 1 week of H4 bars
            break;
        case 'D1':
            barsToFetch = 30;   // 1 month of D1 bars
            break;
        default:
            barsToFetch = 100;
    }

    // Build end datetime from selected date and time
    const dateTo = `${dateInput}T${endTime}:59`;

    console.log('Loading historical data:', timeframe, `(${barsToFetch} bars ending at ${dateTo})`);

    // Send request to server - fetch exact number of bars backward from end time
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            command: 'get_historical_data',
            symbol: currentSymbol || serverConfig?.default_symbol || 'PainX 400',
            timeframe: timeframe,
            date_to: dateTo,
            bars_count: barsToFetch
        }));

        document.getElementById('historicalChartInfo').textContent = 'Loading...';
    } else {
        alert('Not connected to server');
    }
}

// Update Historical Chart
function updateHistoricalChart(data) {
    console.log('=== UPDATE HISTORICAL CHART DEBUG ===');
    console.log('1. Received data:', data);

    const bars = data.bars;
    console.log('2. Bars array:', bars);
    console.log('3. Bars count:', bars ? bars.length : 'NULL');

    if (!bars || bars.length === 0) {
        console.log('ERROR: No bars data received!');
        document.getElementById('historicalChartInfo').textContent = 'No data available';
        return;
    }

    console.log('4. First bar:', bars[0]);
    console.log('5. Last bar:', bars[bars.length - 1]);

    // Extract data
    const labels = bars.map(bar => bar.time);
    const closePrices = bars.map(bar => bar.close);
    const highPrices = bars.map(bar => bar.high);
    const lowPrices = bars.map(bar => bar.low);

    // Create candlestick wicks (shadows) - thin lines from low to high
    const candleWicks = bars.map(bar => {
        return [bar.low, bar.high];
    });

    // Create candlestick bodies (bar chart data showing open to close)
    // Using floating bar format: [min, max]
    const candleBodies = bars.map(bar => {
        return [Math.min(bar.open, bar.close), Math.max(bar.open, bar.close)];
    });

    // Create colors for candles (green if close > open, red if close < open)
    const candleColors = bars.map(bar => {
        return bar.close >= bar.open ? 'rgba(0, 255, 0, 0.8)' : 'rgba(255, 0, 0, 0.8)';
    });

    const candleBorderColors = bars.map(bar => {
        return bar.close >= bar.open ? '#00ff00' : '#ff0000';
    });

    // Wick colors - same as body colors
    const wickColors = bars.map(bar => {
        return bar.close >= bar.open ? 'rgba(0, 255, 0, 1)' : 'rgba(255, 0, 0, 1)';
    });

    console.log('6. Labels (first 3):', labels.slice(0, 3));
    console.log('7. Close prices (first 3):', closePrices.slice(0, 3));
    console.log('8. Candle bodies (first 3):', candleBodies.slice(0, 3));
    console.log('9. High prices (first 3):', highPrices.slice(0, 3));
    console.log('10. Low prices (first 3):', lowPrices.slice(0, 3));

    // Calculate EMAs
    const snakePeriod = serverConfig?.indicators?.snake_period || 100;
    const purplePeriod = serverConfig?.indicators?.purple_line_period || 10;
    console.log('11. Snake period:', snakePeriod, 'Purple period:', purplePeriod);

    const snake = calculateEMA(closePrices, snakePeriod);
    const purpleLine = calculateEMA(closePrices, purplePeriod);

    console.log('12. Snake EMA (first 3):', snake ? snake.slice(0, 3) : 'NULL');
    console.log('13. Purple EMA (first 3):', purpleLine ? purpleLine.slice(0, 3) : 'NULL');

    // Create color array for Snake
    const snakeColors = snake.map((value, index) => {
        return value < closePrices[index] ? '#00ff00' : '#ff0000';
    });

    // Update chart data
    historicalChart.data.labels = labels;

    // Update candlestick wicks (thin lines from low to high)
    historicalChart.data.datasets[0].data = candleWicks;
    historicalChart.data.datasets[0]._wickColors = wickColors; // Store colors for plugin

    // Update candlestick bodies (thick bars from open to close)
    historicalChart.data.datasets[1].data = candleBodies;
    historicalChart.data.datasets[1].backgroundColor = candleColors;
    historicalChart.data.datasets[1].borderColor = candleBorderColors;

    // Update line datasets (indices shifted by +1 due to wick dataset)
    historicalChart.data.datasets[2].data = closePrices;
    historicalChart.data.datasets[3].data = highPrices;
    historicalChart.data.datasets[4].data = lowPrices;
    historicalChart.data.datasets[5].data = snake;
    historicalChart.data.datasets[5].segment = {
        borderColor: (ctx) => {
            const index = ctx.p0DataIndex;
            return snakeColors[index];
        }
    };
    historicalChart.data.datasets[5].pointBackgroundColor = snakeColors;
    historicalChart.data.datasets[5].pointBorderColor = snakeColors;
    historicalChart.data.datasets[6].data = purpleLine;

    const timeframe = data.timeframe;
    console.log('14. Timeframe:', timeframe);

    console.log('15. Chart data assigned. Labels count:', historicalChart.data.labels.length);
    console.log('16. Dataset[0] (Candle Body) count:', historicalChart.data.datasets[0].data.length);
    console.log('17. Dataset[1] (Close) count:', historicalChart.data.datasets[1].data.length);
    console.log('18. About to update chart...');

    // Update with new configuration
    historicalChart.update('none');

    console.log('19. Chart updated successfully!');

    // Update info
    const infoText = `${data.symbol} ${data.timeframe} - ${data.date_from.split('T')[1]} to ${data.date_to.split('T')[1]} (${bars.length} bars)`;
    document.getElementById('historicalChartInfo').textContent = infoText;

    console.log('20. Info updated:', infoText);
    console.log('=== END HISTORICAL CHART UPDATE ===');
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    initializeChart();
    initializeHistoricalChart();
    setupEventListeners();
    connectWebSocket();

    // Set default date to yesterday
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    document.getElementById('historicalDate').valueAsDate = yesterday;

    // Add historical chart event listener
    document.getElementById('loadHistoricalBtn').addEventListener('click', loadHistoricalData);
});
