// ========================================
// UI UPDATE FUNCTIONS
// ========================================

const UI = {
    updatePositions(positions) {
        const container = document.getElementById('positionsContainer');

        if (!positions || positions.length === 0) {
            container.innerHTML = '<div class="no-data">No open positions</div>';
            return;
        }

        container.innerHTML = positions.map(pos => `
            <div class="position-item ${pos.type === 0 ? 'buy' : 'sell'}">
                <div class="position-header">
                    <span class="position-symbol">${pos.symbol}</span>
                    <span class="position-type">${pos.type === 0 ? 'BUY' : 'SELL'}</span>
                </div>
                <div class="position-details">
                    <div class="detail-row">
                        <span>Volume:</span>
                        <span>${pos.volume.toFixed(2)}</span>
                    </div>
                    <div class="detail-row">
                        <span>Price:</span>
                        <span>${pos.price_open.toFixed(2)}</span>
                    </div>
                    <div class="detail-row">
                        <span>Current:</span>
                        <span>${pos.price_current.toFixed(2)}</span>
                    </div>
                    <div class="detail-row ${pos.profit >= 0 ? 'profit' : 'loss'}">
                        <span>P/L:</span>
                        <span>${pos.profit >= 0 ? '+' : ''}${pos.profit.toFixed(2)}</span>
                    </div>
                </div>
            </div>
        `).join('');
    },

    updateSignals(newSignals) {
        if (!newSignals || newSignals.length === 0) return;

        AppState.signals = [...newSignals, ...AppState.signals].slice(0, SIGNAL_CONFIG.maxSignals);

        const container = document.getElementById('signalsContainer');
        container.innerHTML = AppState.signals.map(signal => `
            <div class="signal-item ${signal.type}">
                <div class="signal-header">
                    <span class="signal-type">${signal.type.toUpperCase()}</span>
                    <span class="signal-time">${signal.time}</span>
                </div>
                <div class="signal-details">
                    <div>${signal.symbol} @ ${signal.price}</div>
                    ${signal.reason ? `<div class="signal-reason">${signal.reason}</div>` : ''}
                </div>
            </div>
        `).join('');
    },

    updateStatus(status) {
        const statusElement = document.getElementById('statusIndicator');
        const botStatusElement = document.getElementById('botStatus');

        if (statusElement) {
            statusElement.textContent = status.connection || 'Unknown';
            statusElement.className = 'status ' + (status.connection === 'Connected' ? 'connected' : 'disconnected');
        }

        if (botStatusElement && status.bot_running !== undefined) {
            botStatusElement.textContent = status.bot_running ? 'Running' : 'Stopped';
            botStatusElement.className = 'status-badge ' + (status.bot_running ? 'running' : 'stopped');
        }
    },

    updateMarketData(data) {
        const elements = {
            bidPrice: document.getElementById('bidPrice'),
            askPrice: document.getElementById('askPrice'),
            spread: document.getElementById('spread'),
            balance: document.getElementById('balance'),
            equity: document.getElementById('equity'),
            profit: document.getElementById('profit')
        };

        if (elements.bidPrice && data.bid !== undefined) {
            elements.bidPrice.textContent = data.bid.toFixed(2);
        }
        if (elements.askPrice && data.ask !== undefined) {
            elements.askPrice.textContent = data.ask.toFixed(2);
        }
        if (elements.spread && data.spread !== undefined) {
            elements.spread.textContent = data.spread.toFixed(2);
        }
        if (elements.balance && data.balance !== undefined) {
            elements.balance.textContent = data.balance.toFixed(2);
        }
        if (elements.equity && data.equity !== undefined) {
            elements.equity.textContent = data.equity.toFixed(2);
        }
        if (elements.profit && data.profit !== undefined) {
            elements.profit.textContent = data.profit.toFixed(2);
        }
    },

    populateSymbolDropdown(symbols) {
        const dropdown = document.getElementById('symbolSelect');
        if (!dropdown) return;

        // Add event listener only once
        if (!dropdown.dataset.listenerAdded) {
            dropdown.addEventListener('change', (e) => {
                if (AppState.wsManager.isConnected()) {
                    AppState.currentSymbol = e.target.value;
                    AppState.wsManager.send({
                        command: 'set_symbol',
                        symbol: AppState.currentSymbol
                    });
                }
            });
            dropdown.dataset.listenerAdded = 'true';
        }

        // Update options if we have symbols from server
        if (symbols && symbols.length > 0 && !dropdown.dataset.serverPopulated) {
            dropdown.innerHTML = symbols.map(symbol =>
                `<option value="${symbol}" ${symbol === AppState.currentSymbol ? 'selected' : ''}>${symbol}</option>`
            ).join('');
            dropdown.dataset.serverPopulated = 'true';
        }
    },

    populateTimeframeDropdown(timeframes) {
        const dropdown = document.getElementById('timeframeSelect');
        if (!dropdown) return;

        // Add event listener only once
        if (!dropdown.dataset.listenerAdded) {
            dropdown.addEventListener('change', (e) => {
                if (AppState.wsManager.isConnected()) {
                    AppState.currentTimeframe = e.target.value;
                    AppState.wsManager.send({
                        command: 'set_timeframe',
                        timeframe: AppState.currentTimeframe
                    });
                }
            });
            dropdown.dataset.listenerAdded = 'true';
        }

        // Update options if we have timeframes from server (optional, HTML has defaults)
        if (timeframes && timeframes.length > 0 && !dropdown.dataset.serverPopulated) {
            dropdown.innerHTML = timeframes.map(tf =>
                `<option value="${tf}" ${tf === AppState.currentTimeframe ? 'selected' : ''}>${tf}</option>`
            ).join('');
            dropdown.dataset.serverPopulated = 'true';
        }
    }
};
