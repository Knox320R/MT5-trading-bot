"""
Order Manager
Executes trades via MT5 and tracks open positions.
Handles order placement, modification, and closure.
"""

from typing import Dict, List, Optional
from datetime import datetime
import MetaTrader5 as mt5
from .config_loader import config
from .timezone_handler import TimezoneHandler


class OrderManager:
    """
    Manages order execution and position tracking.
    All orders executed at next bar open (not on signal bar).
    """

    def __init__(self, mt5_connector, timezone_handler: TimezoneHandler):
        """
        Initialize order manager.

        Args:
            mt5_connector: MT5Connector instance
            timezone_handler: TimezoneHandler for timestamps
        """
        self.connector = mt5_connector
        self.tz_handler = timezone_handler

        # Track open positions
        # symbol -> {bot_type -> {ticket, entry_time, entry_price, lot_size, type}}
        self.open_positions = {}

    def execute_buy(self, symbol: str, bot_type: str, reason: str = "") -> Dict:
        """
        Execute BUY order.

        Args:
            symbol: Trading symbol
            bot_type: Bot that triggered (e.g., 'pain_buy')
            reason: Entry reason for logging

        Returns:
            Dictionary with:
            - success: True if order placed
            - ticket: Order ticket number
            - price: Entry price
            - error: Error message if failed
        """
        # Get lot size from config
        lot_size = config.get('trading', {}).get('lot_size', 0.10)

        # Get current price
        tick = self.connector.get_current_tick(symbol)
        if not tick:
            return {
                'success': False,
                'error': 'Cannot get current tick'
            }

        # Get symbol info
        symbol_info = self.connector.get_symbol_info(symbol)
        if not symbol_info:
            return {
                'success': False,
                'error': 'Cannot get symbol info'
            }

        # Prepare order request
        price = tick['ask']
        point = symbol_info['point']

        # Calculate stop loss and take profit
        # For fixed profit target
        target_usd = config.get('trading', {}).get('trade_target_usd', 2.0)

        # Calculate TP in points
        # Profit = (TP - Entry) * Contract_Size * Lot_Size
        # TP = Entry + (Profit / (Contract_Size * Lot_Size))
        contract_size = symbol_info.get('trade_contract_size', 1.0)
        tp_distance = target_usd / (contract_size * lot_size)

        tp_price = price + tp_distance

        # SL: Use large value (we rely on M5 early exit)
        sl_distance = tp_distance * 3  # 3x risk
        sl_price = price - sl_distance

        # Create order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": config.get('trading', {}).get('max_slippage_pips', 2) * 10,  # Convert pips to points
            "magic": 234000,
            "comment": f"{bot_type}|{reason[:20]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send order
        result = mt5.order_send(request)

        if result is None:
            return {
                'success': False,
                'error': 'order_send returned None'
            }

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                'success': False,
                'error': f'Order failed: {result.retcode}',
                'retcode': result.retcode,
                'comment': result.comment
            }

        # Track position
        if symbol not in self.open_positions:
            self.open_positions[symbol] = {}

        self.open_positions[symbol][bot_type] = {
            'ticket': result.order,
            'entry_time': self.tz_handler.now(),
            'entry_price': result.price,
            'lot_size': lot_size,
            'type': 'BUY',
            'tp': tp_price,
            'sl': sl_price,
            'reason': reason
        }

        return {
            'success': True,
            'ticket': result.order,
            'price': result.price,
            'lot_size': lot_size,
            'tp': tp_price,
            'sl': sl_price
        }

    def execute_sell(self, symbol: str, bot_type: str, reason: str = "") -> Dict:
        """
        Execute SELL order.

        Args:
            symbol: Trading symbol
            bot_type: Bot that triggered (e.g., 'pain_sell')
            reason: Entry reason for logging

        Returns:
            Dictionary with success/error info
        """
        # Get lot size from config
        lot_size = config.get('trading', {}).get('lot_size', 0.10)

        # Get current price
        tick = self.connector.get_current_tick(symbol)
        if not tick:
            return {
                'success': False,
                'error': 'Cannot get current tick'
            }

        # Get symbol info
        symbol_info = self.connector.get_symbol_info(symbol)
        if not symbol_info:
            return {
                'success': False,
                'error': 'Cannot get symbol info'
            }

        # Prepare order request
        price = tick['bid']
        point = symbol_info['point']

        # Calculate stop loss and take profit
        target_usd = config.get('trading', {}).get('trade_target_usd', 2.0)

        contract_size = symbol_info.get('trade_contract_size', 1.0)
        tp_distance = target_usd / (contract_size * lot_size)

        tp_price = price - tp_distance

        # SL: Use large value (we rely on M5 early exit)
        sl_distance = tp_distance * 3  # 3x risk
        sl_price = price + sl_distance

        # Create order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": config.get('trading', {}).get('max_slippage_pips', 2) * 10,
            "magic": 234000,
            "comment": f"{bot_type}|{reason[:20]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send order
        result = mt5.order_send(request)

        if result is None:
            return {
                'success': False,
                'error': 'order_send returned None'
            }

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                'success': False,
                'error': f'Order failed: {result.retcode}',
                'retcode': result.retcode,
                'comment': result.comment
            }

        # Track position
        if symbol not in self.open_positions:
            self.open_positions[symbol] = {}

        self.open_positions[symbol][bot_type] = {
            'ticket': result.order,
            'entry_time': self.tz_handler.now(),
            'entry_price': result.price,
            'lot_size': lot_size,
            'type': 'SELL',
            'tp': tp_price,
            'sl': sl_price,
            'reason': reason
        }

        return {
            'success': True,
            'ticket': result.order,
            'price': result.price,
            'lot_size': lot_size,
            'tp': tp_price,
            'sl': sl_price
        }

    def close_position(self, symbol: str, bot_type: str, reason: str = "") -> Dict:
        """
        Close an open position.

        Args:
            symbol: Trading symbol
            bot_type: Bot type (e.g., 'pain_buy')
            reason: Close reason for logging

        Returns:
            Dictionary with success/error info and profit
        """
        # Check if position exists
        if symbol not in self.open_positions or bot_type not in self.open_positions[symbol]:
            return {
                'success': False,
                'error': 'No open position found'
            }

        position = self.open_positions[symbol][bot_type]
        ticket = position['ticket']

        # Get position info from MT5
        positions = mt5.positions_get(ticket=ticket)
        if not positions or len(positions) == 0:
            # Position already closed
            del self.open_positions[symbol][bot_type]
            return {
                'success': False,
                'error': 'Position already closed'
            }

        mt5_position = positions[0]

        # Prepare close request
        close_type = mt5.ORDER_TYPE_SELL if position['type'] == 'BUY' else mt5.ORDER_TYPE_BUY

        # Get current price
        tick = self.connector.get_current_tick(symbol)
        if not tick:
            return {
                'success': False,
                'error': 'Cannot get current tick for close'
            }

        close_price = tick['bid'] if position['type'] == 'BUY' else tick['ask']

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": position['lot_size'],
            "type": close_type,
            "position": ticket,
            "price": close_price,
            "deviation": config.get('trading', {}).get('max_slippage_pips', 2) * 10,
            "magic": 234000,
            "comment": f"close|{reason[:20]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send close order
        result = mt5.order_send(request)

        if result is None:
            return {
                'success': False,
                'error': 'order_send returned None'
            }

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                'success': False,
                'error': f'Close failed: {result.retcode}',
                'retcode': result.retcode
            }

        # Calculate profit
        profit = mt5_position.profit

        # Remove from tracking
        del self.open_positions[symbol][bot_type]

        return {
            'success': True,
            'ticket': ticket,
            'close_price': result.price,
            'profit': profit,
            'entry_price': position['entry_price'],
            'entry_time': position['entry_time'],
            'close_time': self.tz_handler.now(),
            'reason': reason
        }

    def get_open_position(self, symbol: str, bot_type: str) -> Optional[Dict]:
        """
        Get open position for symbol and bot.

        Args:
            symbol: Trading symbol
            bot_type: Bot type

        Returns:
            Position dict or None
        """
        if symbol not in self.open_positions:
            return None

        return self.open_positions[symbol].get(bot_type)

    def has_open_position(self, symbol: str, bot_type: str) -> bool:
        """
        Check if bot has open position.

        Args:
            symbol: Trading symbol
            bot_type: Bot type

        Returns:
            True if position open
        """
        return self.get_open_position(symbol, bot_type) is not None

    def get_all_open_positions(self, symbol: Optional[str] = None) -> Dict:
        """
        Get all open positions.

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            Dictionary of open positions
        """
        if symbol:
            return self.open_positions.get(symbol, {})
        else:
            return self.open_positions

    def sync_with_mt5(self):
        """
        Sync tracked positions with actual MT5 positions.
        Removes positions that were closed externally.
        """
        # Get all MT5 positions
        mt5_positions = mt5.positions_get()
        if mt5_positions is None:
            return

        mt5_tickets = {pos.ticket for pos in mt5_positions}

        # Check our tracked positions
        to_remove = []
        for symbol in self.open_positions:
            for bot_type in self.open_positions[symbol]:
                ticket = self.open_positions[symbol][bot_type]['ticket']
                if ticket not in mt5_tickets:
                    # Position closed externally
                    to_remove.append((symbol, bot_type))

        # Remove closed positions
        for symbol, bot_type in to_remove:
            del self.open_positions[symbol][bot_type]
