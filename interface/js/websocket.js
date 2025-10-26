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
