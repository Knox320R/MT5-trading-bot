// ========================================
// BOT STATUS UI UPDATES
// ========================================

function updateBotStatus(data) {
    if (!data || !data.data) return;

    const botData = data.data;
    const symbol = data.symbol;

    // ONLY update if this is the currently selected symbol
    // Don't auto-switch when bot engine processes other symbols
    if (AppState.currentSymbol && symbol !== AppState.currentSymbol) {
        return;
    }

    // Update header
    document.getElementById('botSymbol').textContent = symbol;

    // Update bias indicator
    const biasElem = document.getElementById('botBias');
    const bias = botData.bias || 'NEUTRAL';
    biasElem.textContent = bias;
    biasElem.className = `bias-indicator ${bias}`;

    // Update trend and M1 state
    document.getElementById('botTrend').textContent = botData.trend_summary || '--';
    document.getElementById('botM1State').textContent = botData.m1_state || '--';

    // Update each bot
    const botResults = botData.bot_results || {};

    // Bot type mapping
    const botMap = {
        'pain_buy': {
            cardId: 'painBuyCard',
            statusId: 'painBuyStatus',
            reasonsId: 'painBuyReasons'
        },
        'pain_sell': {
            cardId: 'painSellCard',
            statusId: 'painSellStatus',
            reasonsId: 'painSellReasons'
        },
        'gain_buy': {
            cardId: 'gainBuyCard',
            statusId: 'gainBuyStatus',
            reasonsId: 'gainBuyReasons'
        },
        'gain_sell': {
            cardId: 'gainSellCard',
            statusId: 'gainSellStatus',
            reasonsId: 'gainSellReasons'
        }
    };

    // Update each bot status
    for (const [botName, result] of Object.entries(botResults)) {
        // botName is now a string (e.g., 'pain_buy', 'pain_sell')
        if (!botMap[botName]) continue;

        const card = document.getElementById(botMap[botName].cardId);
        const statusElem = document.getElementById(botMap[botName].statusId);
        const reasonsElem = document.getElementById(botMap[botName].reasonsId);

        if (!card || !statusElem || !reasonsElem) continue;

        // Update status
        if (result.ready) {
            statusElem.textContent = '● READY';
            statusElem.className = 'bot-status ready';
            card.classList.add('ready');
            card.classList.remove('halted');
        } else {
            statusElem.textContent = '○ SCANNING';
            statusElem.className = 'bot-status';
            card.classList.remove('ready', 'halted');
        }

        // Update reasons
        if (result.reasons && result.reasons.length > 0) {
            const formattedReasons = result.reasons.map(reason => {
                if (reason.includes('✓')) {
                    return `<span class="check">${reason}</span>`;
                } else {
                    return `<span class="cross">${reason}</span>`;
                }
            }).join('<br>');

            reasonsElem.innerHTML = formattedReasons;
        } else {
            reasonsElem.textContent = 'Checking conditions...';
        }
    }
}

// Export for use in websocket handler
window.updateBotStatus = updateBotStatus;
