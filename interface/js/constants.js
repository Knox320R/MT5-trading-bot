// ========================================
// CONFIGURATION CONSTANTS
// ========================================

const CHART_CONFIG = {
    pointRadius: 1,
    pointHoverRadius: 3,
    candleBodyThickness: 8,
    candleWickThickness: 1,
    candleWickLineWidth: 1.5
};

const COLORS = {
    bullish: {
        body: 'rgba(0, 255, 0, 0.8)',
        border: '#00ff00',
        wick: 'rgba(0, 255, 0, 1)'
    },
    bearish: {
        body: 'rgba(255, 0, 0, 0.8)',
        border: '#ff0000',
        wick: 'rgba(255, 0, 0, 1)'
    },
    primary: '#00d4ff',
    grid: 'rgba(255, 255, 255, 0.1)',
    white: '#ffffff',
    transparent: 'rgba(0,0,0,0)',
    purple: '#800080'
};

const WEBSOCKET_CONFIG = {
    defaultPort: 8765,
    portsToTry: [8765, 8766, 8767, 8768, 8769],
    reconnectInterval: 3000
};

const SIGNAL_CONFIG = {
    maxSignals: 20
};
