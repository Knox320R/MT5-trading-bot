// ========================================
// WEBSOCKET CONNECTION MANAGEMENT
// ========================================

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectInterval = null;
        this.currentPort = WEBSOCKET_CONFIG.defaultPort;
    }

    connect(port = this.currentPort) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.close();
        }

        this.ws = new WebSocket(`ws://localhost:${port}`);

        this.ws.onopen = () => {
            this.currentPort = port;
            UI.updateStatus({ connection: 'Connected' });

            if (this.reconnectInterval) {
                clearInterval(this.reconnectInterval);
                this.reconnectInterval = null;
            }
        };

        this.ws.onmessage = (event) => {
            this.handleMessage(event);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            UI.updateStatus({ connection: 'Error' });
        };

        this.ws.onclose = () => {
            UI.updateStatus({ connection: 'Disconnected' });

            if (!this.reconnectInterval) {
                this.reconnectInterval = setInterval(() => this.tryReconnect(), WEBSOCKET_CONFIG.reconnectInterval);
            }
        };
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);

            switch(data.type) {
                case 'positions_update':
                    UI.updatePositions(data.positions);
                    break;

                case 'signal':
                    UI.updateSignals([data.signal]);
                    break;

                case 'status':
                    UI.updateStatus(data);
                    break;

                case 'market_update':
                    // Update chart with bars data
                    if (data.bars && data.bars.length > 0) {
                        updateChartData(AppState.chart, data.bars, () => {
                            document.getElementById('chartSymbol').textContent = data.symbol;
                            document.getElementById('chartTimeframe').textContent = data.timeframe;
                        });
                    }

                    // Update market data (bid, ask, spread)
                    if (data.tick) {
                        UI.updateMarketData({
                            bid: data.tick.bid,
                            ask: data.tick.ask,
                            spread: data.tick.spread || (data.tick.ask - data.tick.bid) / data.symbol_info?.point || 0
                        });
                    }

                    // Update account info
                    if (data.account) {
                        UI.updateMarketData({
                            balance: data.account.balance,
                            equity: data.account.equity,
                            profit: data.account.profit
                        });
                    }

                    // Update positions
                    if (data.positions) {
                        UI.updatePositions(data.positions);
                    }
                    break;

                case 'config':

                    // Store server config
                    AppState.serverConfig = data.data;

                    // Set default symbol and timeframe from config
                    AppState.currentSymbol = data.data?.default_symbol || 'PainX 400';
                    AppState.currentTimeframe = data.data?.default_timeframe || 'M1';

                    // Set indicator periods from config
                    if (data.data?.indicators) {
                        AppState.snakePeriod = data.data.indicators.snake_period || 100;
                        AppState.purplePeriod = data.data.indicators.purple_line_period || 10;

                        // Update UI inputs to match config
                        const snakePeriodInput = document.getElementById('snakePeriod');
                        const purplePeriodInput = document.getElementById('purplePeriod');

                        if (snakePeriodInput) {
                            snakePeriodInput.value = AppState.snakePeriod;
                        }
                        if (purplePeriodInput) {
                            purplePeriodInput.value = AppState.purplePeriod;
                        }

                    }

                    // Populate dropdowns with symbols and timeframes from config
                    UI.populateSymbolDropdown(data.data?.symbols || []);
                    UI.populateTimeframeDropdown(data.data?.timeframes || []);

                    break;

                case 'historical_data':
                    this.handleHistoricalData(data);
                    break;

                case 'trade_history':
                    this.handleTradeHistory(data);
                    break;

                case 'trade_result':
                    this.handleTradeResult(data);
                    break;

                case 'symbol_changed':
                    AppState.currentSymbol = data.symbol;
                    break;

                case 'timeframe_changed':
                    AppState.currentTimeframe = data.timeframe;
                    break;

                case 'bot_status':
                    // Update bot status panel
                    if (window.updateBotStatus) {
                        window.updateBotStatus(data);
                    }
                    break;

                case 'trade_executed':
                    // Show notification for trade execution
                    this.showNotification(`Trade Executed: ${data.bot_type} on ${data.symbol}`, 'success');
                    break;

                case 'trade_closed':
                    // Show notification for trade closure
                    const profitSign = data.profit >= 0 ? '+' : '';
                    this.showNotification(`Trade Closed: ${data.bot_type} ${profitSign}$${data.profit.toFixed(2)}`, data.profit >= 0 ? 'success' : 'error');
                    break;

                case 'error':
                    console.error('[websocket] Server error:', data.message || data.error || 'Unknown error');
                    if (data.message) {
                        alert('Server Error: ' + data.message);
                    }
                    break;

                default:
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }

    handleHistoricalData(data) {
        const bars = data.bars;

        if (!bars || bars.length === 0) {
            document.getElementById('historicalChartInfo').textContent = 'No data available';
            return;
        }

        updateChartData(AppState.historicalChart, bars, () => {
            const date = data.date || 'Unknown';
            const timeframe = data.timeframe || 'Unknown';
            document.getElementById('historicalChartInfo').textContent =
                `Historical Data: ${date} - ${timeframe}`;
        });

        // After loading historical data, fetch trade history for the same period
        this.loadTradeHistoryForChart(data);
    }

    loadTradeHistoryForChart(historicalData) {
        if (!historicalData.bars || historicalData.bars.length === 0) return;

        const firstBar = historicalData.bars[0];
        const lastBar = historicalData.bars[historicalData.bars.length - 1];

        // Extract dates from timestamps
        const dateFrom = firstBar.time.split(' ')[0];  // YYYY-MM-DD
        const dateTo = lastBar.time.split(' ')[0];      // YYYY-MM-DD

        this.send({
            command: 'get_trade_history',
            symbol: historicalData.symbol || AppState.currentSymbol,
            date_from: dateFrom,
            date_to: dateTo
        });
    }

    handleTradeHistory(data) {
        const trades = data.trades;

        if (!trades || trades.length === 0) {
            return;
        }

        // Add trade markers to historical chart
        this.addTradeMarkersToChart(trades);
    }

    addTradeMarkersToChart(trades) {

        if (!AppState.historicalChart) {
            return;
        }


        // Create arrays for BUY and SELL markers
        const buyMarkers = [];
        const sellMarkers = [];
        const chartLabels = AppState.historicalChart.data.labels;


        for (const trade of trades) {

            if (trade.action === 'ENTRY' && trade.entry_time) {
                const isBuy = trade.bot_type.includes('buy');

                // Parse entry time to match chart label format
                const entryDateTime = trade.entry_time.split('T');
                const entryDate = entryDateTime[0];
                const entryTime = entryDateTime[1].split('.')[0];
                const formattedTime = `${entryDate} ${entryTime}`;


                // Find nearest bar index in chart labels
                let matchIndex = -1;
                const tradeTime = new Date(trade.entry_time).getTime();
                let minDiff = Infinity;

                for (let i = 0; i < chartLabels.length; i++) {
                    const barTime = new Date(chartLabels[i]).getTime();
                    const diff = Math.abs(barTime - tradeTime);

                    if (diff < minDiff) {
                        minDiff = diff;
                        matchIndex = i;
                    }
                }


                if (matchIndex >= 0) {
                    // Ensure price is a number
                    const price = parseFloat(trade.entry_price);

                    const markerData = {
                        x: matchIndex,
                        y: price,
                        isBuy: isBuy
                    };


                    if (isBuy) {
                        buyMarkers.push(markerData);
                    } else {
                        sellMarkers.push(markerData);
                    }
                } else {
                }
            }
        }


        // Add or update marker datasets
        if (buyMarkers.length > 0 || sellMarkers.length > 0) {
            // Remove existing marker datasets if any
            AppState.historicalChart.data.datasets = AppState.historicalChart.data.datasets.filter(
                ds => ds.label !== 'BUY Trades' && ds.label !== 'SELL Trades'
            );

            // Add BUY markers dataset (green downward triangle)
            if (buyMarkers.length > 0) {
                AppState.historicalChart.data.datasets.push({
                    label: 'BUY Trades',
                    type: 'scatter',
                    data: buyMarkers,
                    backgroundColor: '#00ff00',
                    borderColor: '#00ff00',
                    borderWidth: 2,
                    pointStyle: 'triangle',
                    rotation: 180,  // Point down
                    pointRadius: 12,
                    pointHoverRadius: 15,
                    showLine: false,
                    order: -1,  // Render on top
                    yAxisID: 'y',
                    parsing: false,
                    hidden: false
                });
            }

            // Add SELL markers dataset (red upward triangle)
            if (sellMarkers.length > 0) {
                AppState.historicalChart.data.datasets.push({
                    label: 'SELL Trades',
                    type: 'scatter',
                    data: sellMarkers,
                    backgroundColor: '#ff0000',
                    borderColor: '#ff0000',
                    borderWidth: 2,
                    pointStyle: 'triangle',
                    rotation: 0,  // Point up
                    pointRadius: 12,
                    pointHoverRadius: 15,
                    showLine: false,
                    order: -1,  // Render on top
                    yAxisID: 'y',
                    parsing: false,
                    hidden: false
                });
            }

            // Update chart with animation to make markers visible
            AppState.historicalChart.update();
        }
    }

    handleTradeResult(data) {
        if (data.success) {
            alert(`Trade executed successfully!\nOrder: ${data.order}\nPrice: ${data.price}\nVolume: ${data.volume}`);
        } else {
            alert(`Trade failed: ${data.error}`);
        }
    }

    tryReconnect() {

        for (let port of WEBSOCKET_CONFIG.portsToTry) {
            try {
                this.connect(port);
                break;
            } catch (error) {
            }
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
            return true;
        }
        return false;
    }

    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }

    showNotification(message, type = 'info') {
        // Simple notification using browser notification API or console

        // You can also add a visual notification in the UI if desired
        // For now, just log to console
    }
}
