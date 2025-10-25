"""
M1 State Machine
Tracks cross-then-touch pattern for Purple Line (EMA10) entries.
Implements the exact trigger primitives from specification.
"""

from typing import Dict, Optional, List
from enum import Enum


class EntryState(Enum):
    """States for M1 entry state machine"""
    IDLE = "idle"                    # Waiting for cross
    CROSSED_UP = "crossed_up"        # Crossed above purple, waiting for touch
    CROSSED_DOWN = "crossed_down"    # Crossed below purple, waiting for touch
    READY_BUY = "ready_buy"          # Touch detected, ready to BUY
    READY_SELL = "ready_sell"        # Touch detected, ready to SELL
    EXECUTED = "executed"            # Order executed, waiting for exit


class M1StateMachine:
    """
    State machine for M1 cross-then-touch entry detection.

    BUY sequence:
    1. Close crosses ABOVE EMA10
    2. Later, candle TOUCHES EMA10 (low <= EMA10 <= high) while close >= EMA10 and close >= EMA100
    3. Execute BUY at next bar open

    SELL sequence:
    1. Close crosses BELOW EMA10
    2. Later, candle TOUCHES EMA10 (low <= EMA10 <= high) while close <= EMA10 and close < EMA100
    3. Execute SELL at next bar open
    """

    def __init__(self, max_bars_between: int = 20):
        """
        Initialize state machine.

        Args:
            max_bars_between: Max bars allowed between cross and touch
        """
        self.max_bars_between = max_bars_between
        # symbol -> state dict
        self.states = {}

    def update(self, symbol: str, m1_bars: List[Dict], purple_values: List[float], snake_values: List[float]):
        """
        Update state machine with latest M1 bar.

        Args:
            symbol: Trading symbol
            m1_bars: List of M1 bars
            purple_values: List of Purple EMA10 values
            snake_values: List of Snake EMA100 values
        """
        if not m1_bars or len(m1_bars) < 2:
            return

        if not purple_values or not snake_values:
            return

        if len(m1_bars) != len(purple_values) or len(m1_bars) != len(snake_values):
            return

        # Initialize state if needed
        if symbol not in self.states:
            self.states[symbol] = {
                'state': EntryState.IDLE,
                'cross_bar_index': -1,
                'cross_direction': None,
                'ready_bar_index': -1
            }

        state = self.states[symbol]
        last_idx = len(m1_bars) - 1
        prev_idx = last_idx - 1

        # Get current and previous bar data
        curr_bar = m1_bars[last_idx]
        prev_bar = m1_bars[prev_idx]
        curr_close = curr_bar['close']
        curr_high = curr_bar['high']
        curr_low = curr_bar['low']
        prev_close = prev_bar['close']

        curr_purple = purple_values[last_idx]
        prev_purple = purple_values[prev_idx]
        curr_snake = snake_values[last_idx]

        # State machine logic
        if state['state'] == EntryState.IDLE:
            # Looking for cross
            # Upward cross: prev_close < prev_purple AND curr_close > curr_purple
            if prev_close < prev_purple and curr_close > curr_purple:
                state['state'] = EntryState.CROSSED_UP
                state['cross_bar_index'] = last_idx
                state['cross_direction'] = 'up'

            # Downward cross: prev_close > prev_purple AND curr_close < curr_purple
            elif prev_close > prev_purple and curr_close < curr_purple:
                state['state'] = EntryState.CROSSED_DOWN
                state['cross_bar_index'] = last_idx
                state['cross_direction'] = 'down'

        elif state['state'] == EntryState.CROSSED_UP:
            # Looking for touch from above
            # Touch: low <= purple <= high
            # BUY requires: close >= purple AND close >= snake
            bars_since_cross = last_idx - state['cross_bar_index']

            if bars_since_cross > self.max_bars_between:
                # Timeout - reset
                state['state'] = EntryState.IDLE
                state['cross_bar_index'] = -1

            elif curr_low <= curr_purple <= curr_high:
                # Touch detected
                if curr_close >= curr_purple and curr_close >= curr_snake:
                    # Valid BUY touch
                    state['state'] = EntryState.READY_BUY
                    state['ready_bar_index'] = last_idx
                else:
                    # Touch but wrong side - reset
                    state['state'] = EntryState.IDLE
                    state['cross_bar_index'] = -1

            elif curr_close < curr_purple:
                # Crossed back down - reset
                state['state'] = EntryState.IDLE
                state['cross_bar_index'] = -1

        elif state['state'] == EntryState.CROSSED_DOWN:
            # Looking for touch from below
            # Touch: low <= purple <= high
            # SELL requires: close <= purple AND close < snake
            bars_since_cross = last_idx - state['cross_bar_index']

            if bars_since_cross > self.max_bars_between:
                # Timeout - reset
                state['state'] = EntryState.IDLE
                state['cross_bar_index'] = -1

            elif curr_low <= curr_purple <= curr_high:
                # Touch detected
                if curr_close <= curr_purple and curr_close < curr_snake:
                    # Valid SELL touch
                    state['state'] = EntryState.READY_SELL
                    state['ready_bar_index'] = last_idx
                else:
                    # Touch but wrong side - reset
                    state['state'] = EntryState.IDLE
                    state['cross_bar_index'] = -1

            elif curr_close > curr_purple:
                # Crossed back up - reset
                state['state'] = EntryState.IDLE
                state['cross_bar_index'] = -1

        elif state['state'] in [EntryState.READY_BUY, EntryState.READY_SELL]:
            # Signal already fired - waiting for execution or reset
            pass

        elif state['state'] == EntryState.EXECUTED:
            # Order executed - waiting for exit signal or manual reset
            pass

    def is_buy_signal(self, symbol: str) -> bool:
        """
        Check if BUY signal is active.

        Returns:
            True if ready to execute BUY at next bar open
        """
        if symbol not in self.states:
            return False

        return self.states[symbol]['state'] == EntryState.READY_BUY

    def is_sell_signal(self, symbol: str) -> bool:
        """
        Check if SELL signal is active.

        Returns:
            True if ready to execute SELL at next bar open
        """
        if symbol not in self.states:
            return False

        return self.states[symbol]['state'] == EntryState.READY_SELL

    def mark_executed(self, symbol: str):
        """
        Mark signal as executed.
        Prevents re-entry until reset.

        Args:
            symbol: Trading symbol
        """
        if symbol in self.states:
            self.states[symbol]['state'] = EntryState.EXECUTED

    def reset(self, symbol: str):
        """
        Reset state machine for symbol.
        Required after exit to allow re-entry.

        Args:
            symbol: Trading symbol
        """
        if symbol in self.states:
            self.states[symbol] = {
                'state': EntryState.IDLE,
                'cross_bar_index': -1,
                'cross_direction': None,
                'ready_bar_index': -1
            }

    def get_state(self, symbol: str) -> Dict:
        """
        Get current state for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            State dictionary
        """
        if symbol not in self.states:
            return {
                'state': 'none',
                'cross_bar_index': -1,
                'cross_direction': None,
                'ready': False
            }

        state = self.states[symbol]
        return {
            'state': state['state'].value,
            'cross_bar_index': state['cross_bar_index'],
            'cross_direction': state['cross_direction'],
            'ready': state['state'] in [EntryState.READY_BUY, EntryState.READY_SELL]
        }

    def get_state_summary(self, symbol: str) -> str:
        """
        Get human-readable state summary.

        Args:
            symbol: Trading symbol

        Returns:
            Summary string
        """
        state = self.get_state(symbol)
        return f"{state['state']} (cross: {state['cross_direction'] or 'none'})"
