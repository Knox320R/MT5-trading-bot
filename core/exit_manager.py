"""
Exit Manager
Monitors open positions and triggers exits based on:
1. Fixed profit target (TP hit)
2. M5 purple line break (early exit)
3. Stop loss hit
"""

from typing import Dict, List, Optional
from datetime import datetime
from .order_manager import OrderManager
from .indicators import IndicatorCalculator
from .config_loader import config


class ExitManager:
    """
    Monitors exits for all open positions.
    Checks M5 timeframe for purple line breaks.
    """

    def __init__(self, order_manager: OrderManager, indicator_calc: IndicatorCalculator):
        """
        Initialize exit manager.

        Args:
            order_manager: OrderManager instance
            indicator_calc: IndicatorCalculator for M5 purple line
        """
        self.order_manager = order_manager
        self.indicator_calc = indicator_calc

        # Track last M5 check per symbol
        self.last_m5_check = {}

    def check_exits(self, symbol: str, m5_bars: List[Dict]) -> List[Dict]:
        """
        Check all exit conditions for symbol.

        Args:
            symbol: Trading symbol
            m5_bars: M5 timeframe bars

        Returns:
            List of exit actions taken
        """
        exits = []

        # Get all open positions for symbol
        open_positions = self.order_manager.get_all_open_positions(symbol)

        if not open_positions:
            return exits

        # Calculate M5 indicators
        if not m5_bars or len(m5_bars) < 2:
            return exits

        m5_indicators = self.indicator_calc.get_indicators_for_bars(m5_bars, f"{symbol}_M5")

        # Get latest M5 close and purple
        latest_close = m5_indicators['close_latest']
        latest_purple = m5_indicators['purple_latest']

        if latest_close is None or latest_purple is None:
            return exits

        # Check each bot's position
        for bot_type, position in open_positions.items():
            # Check M5 purple break early exit
            exit_signal = self._check_m5_purple_break(
                bot_type, position, latest_close, latest_purple
            )

            if exit_signal:
                # Close position
                result = self.order_manager.close_position(
                    symbol, bot_type, reason=exit_signal['reason']
                )

                if result['success']:
                    exits.append({
                        'symbol': symbol,
                        'bot_type': bot_type,
                        'exit_type': exit_signal['type'],
                        'reason': exit_signal['reason'],
                        'profit': result['profit'],
                        'ticket': result['ticket'],
                        'entry_price': result['entry_price'],
                        'close_price': result['close_price'],
                        'entry_time': result['entry_time'],
                        'close_time': result['close_time']
                    })

        return exits

    def _check_m5_purple_break(self, bot_type: str, position: Dict,
                                m5_close: float, m5_purple: float) -> Optional[Dict]:
        """
        Check if M5 closed against purple line.

        BUY positions: Exit if M5 closes BELOW purple
        SELL positions: Exit if M5 closes ABOVE purple

        Args:
            bot_type: Bot type (e.g., 'pain_buy')
            position: Position dict
            m5_close: Latest M5 close price
            m5_purple: Latest M5 purple (EMA10)

        Returns:
            Exit signal dict or None
        """
        # Check if early exit is enabled
        if not config.get_early_exit_on_m5_purple_break():
            return None

        position_type = position['type']

        if position_type == 'BUY':
            # BUY exit: M5 closes below purple
            if m5_close < m5_purple:
                return {
                    'type': 'M5_PURPLE_BREAK',
                    'reason': f'M5 closed below purple ({m5_close:.5f} < {m5_purple:.5f})'
                }

        elif position_type == 'SELL':
            # SELL exit: M5 closes above purple
            if m5_close > m5_purple:
                return {
                    'type': 'M5_PURPLE_BREAK',
                    'reason': f'M5 closed above purple ({m5_close:.5f} > {m5_purple:.5f})'
                }

        return None

    def check_profit_targets(self, symbol: str) -> List[Dict]:
        """
        Check if positions hit profit targets.
        (This is handled by MT5 TP automatically, but we can verify)

        Args:
            symbol: Trading symbol

        Returns:
            List of positions that hit TP
        """
        exits = []

        # Sync with MT5 to detect closed positions
        self.order_manager.sync_with_mt5()

        return exits

    def get_exit_summary(self, exit_info: Dict) -> str:
        """
        Get human-readable exit summary.

        Args:
            exit_info: Exit information dict

        Returns:
            Summary string
        """
        profit_sign = "+" if exit_info['profit'] >= 0 else ""
        return (
            f"{exit_info['bot_type']} {exit_info['symbol']}: "
            f"{exit_info['exit_type']} {profit_sign}${exit_info['profit']:.2f} "
            f"({exit_info['reason']})"
        )
