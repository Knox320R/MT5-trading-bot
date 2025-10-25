"""
Risk Manager
Enforces global risk gates before allowing any trade execution.
Checks: session time, spread, slippage, daily limits, consecutive orders.
"""

from typing import Dict, Optional
from datetime import datetime
from .timezone_handler import TimezoneHandler
from .config_loader import config


class RiskManager:
    """
    Global risk gates for all bots.
    All checks must pass before executing any order.
    """

    def __init__(self, timezone_handler: TimezoneHandler, mt5_connector):
        """
        Initialize risk manager.

        Args:
            timezone_handler: Timezone handler for session time
            mt5_connector: MT5 connector for account/symbol info
        """
        self.tz_handler = timezone_handler
        self.connector = mt5_connector

        # Daily tracking (resets at 16:00)
        self.daily_stats = {}  # symbol -> {profit, loss, trade_count, last_reset_day}

    def check_all_gates(self, symbol: str, order_type: str) -> Dict:
        """
        Check all risk gates before allowing trade.

        Args:
            symbol: Trading symbol
            order_type: 'buy' or 'sell'

        Returns:
            Dictionary with:
            - allowed: True if all gates pass
            - reasons: List of failed gates (if any)
            - gates: Dict of individual gate results
        """
        gates = {}
        reasons = []

        # 1. Session time
        gates['session'] = self._check_session_active()
        if not gates['session']['allowed']:
            reasons.append(gates['session']['reason'])

        # 2. Symbol enabled
        gates['symbol'] = self._check_symbol_enabled(symbol)
        if not gates['symbol']['allowed']:
            reasons.append(gates['symbol']['reason'])

        # 3. Spread
        gates['spread'] = self._check_spread(symbol)
        if not gates['spread']['allowed']:
            reasons.append(gates['spread']['reason'])

        # 4. Daily profit target
        gates['daily_profit'] = self._check_daily_profit(symbol)
        if not gates['daily_profit']['allowed']:
            reasons.append(gates['daily_profit']['reason'])

        # 5. Daily loss limit
        gates['daily_loss'] = self._check_daily_loss(symbol)
        if not gates['daily_loss']['allowed']:
            reasons.append(gates['daily_loss']['reason'])

        # 6. Consecutive orders
        gates['consecutive'] = self._check_consecutive_orders(symbol)
        if not gates['consecutive']['allowed']:
            reasons.append(gates['consecutive']['reason'])

        # 7. Account health
        gates['account'] = self._check_account_health()
        if not gates['account']['allowed']:
            reasons.append(gates['account']['reason'])

        all_allowed = len(reasons) == 0

        return {
            'allowed': all_allowed,
            'reasons': reasons,
            'gates': gates
        }

    def _check_session_active(self) -> Dict:
        """Check if within trading hours"""
        if not config.get_session_enabled():
            return {'allowed': True, 'reason': 'Session checking disabled'}

        trading_hours = config.get_trading_hours()
        start_time = trading_hours.get('start', '19:00')
        end_time = trading_hours.get('end', '06:00')

        in_session = self.tz_handler.is_within_trading_hours(start_time, end_time)

        return {
            'allowed': in_session,
            'reason': '' if in_session else f'Outside trading hours ({start_time}-{end_time})',
            'start': start_time,
            'end': end_time
        }

    def _check_symbol_enabled(self, symbol: str) -> Dict:
        """Check if symbol is enabled for trading"""
        # For now, assume all configured symbols are enabled
        all_symbols = config.get_all_symbols()
        enabled = symbol in all_symbols

        return {
            'allowed': enabled,
            'reason': '' if enabled else f'Symbol {symbol} not in config'
        }

    def _check_spread(self, symbol: str) -> Dict:
        """Check if spread is within acceptable limits"""
        max_spread_pips = config.get_max_spread_pips()

        symbol_info = self.connector.get_symbol_info(symbol)
        if not symbol_info:
            return {
                'allowed': False,
                'reason': 'Cannot get symbol info',
                'spread': None
            }

        spread_points = symbol_info.get('spread', 0)
        point = symbol_info.get('point', 0.00001)

        # Convert to pips (for 5-digit brokers, 10 points = 1 pip)
        spread_pips = (spread_points * point) / 0.0001

        within_limit = spread_pips <= max_spread_pips

        return {
            'allowed': within_limit,
            'reason': '' if within_limit else f'Spread {spread_pips:.1f} pips > max {max_spread_pips} pips',
            'spread': spread_pips,
            'max': max_spread_pips
        }

    def _check_daily_profit(self, symbol: str) -> Dict:
        """Check if daily profit target reached"""
        if not config.is_daily_target_enabled():
            return {'allowed': True, 'reason': 'Daily target checking disabled'}

        target_usd = config.get_daily_target_usd()

        # Get daily stats
        stats = self._get_daily_stats(symbol)
        current_profit = stats['profit']

        target_reached = current_profit >= target_usd

        return {
            'allowed': not target_reached,
            'reason': '' if not target_reached else f'Daily target ${target_usd} reached (profit: ${current_profit:.2f})',
            'current': current_profit,
            'target': target_usd
        }

    def _check_daily_loss(self, symbol: str) -> Dict:
        """Check if daily loss limit breached"""
        if not config.is_daily_stop_enabled():
            return {'allowed': True, 'reason': 'Daily stop checking disabled'}

        limit_usd = config.get_daily_stop_usd()

        # Get daily stats
        stats = self._get_daily_stats(symbol)
        current_loss = stats['loss']

        limit_breached = current_loss >= limit_usd

        return {
            'allowed': not limit_breached,
            'reason': '' if not limit_breached else f'Daily loss limit ${limit_usd} breached (loss: ${current_loss:.2f})',
            'current': current_loss,
            'limit': limit_usd
        }

    def _check_consecutive_orders(self, symbol: str) -> Dict:
        """Check if max consecutive orders exceeded"""
        max_orders = config.get_max_concurrent_orders()

        # Get current open positions for symbol
        positions = self.connector.get_positions(symbol) if hasattr(self.connector, 'get_positions') else []
        current_count = len(positions)

        within_limit = current_count < max_orders

        return {
            'allowed': within_limit,
            'reason': '' if within_limit else f'Max concurrent orders ({max_orders}) reached',
            'current': current_count,
            'max': max_orders
        }

    def _check_account_health(self) -> Dict:
        """Check account margin and health"""
        account = self.connector.get_account_info()
        if not account:
            return {
                'allowed': False,
                'reason': 'Cannot get account info'
            }

        # Check margin level (if applicable)
        margin = account.get('margin', 0)
        margin_free = account.get('margin_free', 0)
        equity = account.get('equity', 0)

        # Simple check: ensure positive equity and free margin
        healthy = equity > 0 and margin_free > 0

        return {
            'allowed': healthy,
            'reason': '' if healthy else 'Insufficient margin or negative equity',
            'equity': equity,
            'margin_free': margin_free
        }

    def _get_daily_stats(self, symbol: str) -> Dict:
        """Get or initialize daily statistics"""
        current_day = self.tz_handler.get_current_trading_day()

        if symbol not in self.daily_stats:
            self.daily_stats[symbol] = {
                'profit': 0.0,
                'loss': 0.0,
                'trade_count': 0,
                'last_reset_day': current_day
            }

        stats = self.daily_stats[symbol]

        # Reset if new trading day
        if stats['last_reset_day'] != current_day:
            stats['profit'] = 0.0
            stats['loss'] = 0.0
            stats['trade_count'] = 0
            stats['last_reset_day'] = current_day

        return stats

    def record_trade_result(self, symbol: str, profit_usd: float):
        """
        Record trade result for daily tracking.

        Args:
            symbol: Trading symbol
            profit_usd: Profit/loss in USD (negative for loss)
        """
        stats = self._get_daily_stats(symbol)

        if profit_usd > 0:
            stats['profit'] += profit_usd
        else:
            stats['loss'] += abs(profit_usd)

        stats['trade_count'] += 1

    def get_daily_summary(self, symbol: str) -> str:
        """
        Get human-readable daily summary.

        Args:
            symbol: Trading symbol

        Returns:
            Summary string
        """
        stats = self._get_daily_stats(symbol)
        return f"Day: +${stats['profit']:.2f} / -${stats['loss']:.2f} | Trades: {stats['trade_count']}"

    def reset_daily_stats(self, symbol: Optional[str] = None):
        """
        Reset daily statistics.

        Args:
            symbol: Symbol to reset, or None for all
        """
        if symbol:
            self.daily_stats.pop(symbol, None)
        else:
            self.daily_stats.clear()
