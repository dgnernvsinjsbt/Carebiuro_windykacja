"""
DOGE SHORT Reversal Strategy - OPTIMIZED

Individual Performance (Jun-Dec 2025, 15m candles, 5% risk/trade):
- Contribution to Portfolio: $2,993,404 (57.5% of total!) 🏆
- Trades: 79
- Profitable Months: 5/7
- Best Trade: +$998,362 (Dec 9)

Portfolio Context (all 4 coins combined):
- Total Return: +5,204,473% ($100 → $5.2M)
- Max DD: -65.9% (realistic with 5% risk)
- Return/DD: 78,973x

Strategy Logic:
1. SIGNAL: RSI(14) > 72 (overbought, ready for reversal)
2. ARM: Wait for price to break below swing low (5-candle lookback)
3. ENTRY: Place LIMIT order 0.6 ATR above swing low (tighter entry)
4. SL: Swing high from signal bar to break bar
5. TP: 6% below entry (tighter target, higher win rate)

Position Sizing: 5% risk per trade based on SL distance
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class DogeShortReversal(BaseStrategy):
    """DOGE SHORT Reversal Strategy with Limit Orders"""

    def __init__(self, config: Dict[str, Any], symbol: str = 'DOGE-USDT'):
        super().__init__('doge_short_reversal', config, symbol)

        # Strategy parameters (from backtest optimization)
        self.rsi_trigger = 72
        self.lookback = 5
        self.limit_atr_offset = 0.6  # Tighter offset for DOGE
        self.tp_pct = 6.0  # Tighter TP target
        self.max_wait_bars = 20
        self.max_sl_pct = 10.0

        # State tracking
        self.armed = False
        self.signal_bar_idx = None
        self.swing_low = None
        self.limit_pending = False
        self.limit_placed_bar = None

    def generate_signals(self, df: pd.DataFrame, current_positions: list) -> Optional[Dict[str, Any]]:
        """Generate SHORT reversal signals"""

        if current_positions:
            return None

        if len(df) < self.lookback + 14:
            return None

        latest = df.iloc[-1]

        if pd.isna(latest['rsi']) or pd.isna(latest['atr']):
            return None

        current_bar_idx = len(df) - 1

        # STEP 1: ARM on RSI > 72
        if latest['rsi'] > self.rsi_trigger and not self.armed and not self.limit_pending:
            self.armed = True
            self.signal_bar_idx = current_bar_idx
            self.swing_low = df.iloc[-self.lookback:]['low'].min()
            return None

        # STEP 2: Check if price broke below swing low
        if self.armed and self.swing_low is not None and not self.limit_pending:
            if latest['low'] < self.swing_low:
                limit_price = self.swing_low + (latest['atr'] * self.limit_atr_offset)
                swing_high = df.iloc[self.signal_bar_idx:current_bar_idx+1]['high'].max()
                sl_dist_pct = ((swing_high - limit_price) / limit_price) * 100

                if sl_dist_pct <= 0 or sl_dist_pct > self.max_sl_pct:
                    self.armed = False
                    return None

                tp_price = limit_price * (1 - self.tp_pct / 100)

                self.limit_pending = True
                self.limit_placed_bar = current_bar_idx
                self.armed = False

                return {
                    'side': 'SHORT',
                    'type': 'LIMIT',
                    'limit_price': limit_price,
                    'stop_loss': swing_high,
                    'take_profit': tp_price,
                    'max_wait_bars': self.max_wait_bars,
                    'reason': f"RSI reversal: broke ${self.swing_low:.4f} support after RSI>{self.rsi_trigger}",
                    'metadata': {
                        'rsi': latest['rsi'],
                        'atr': latest['atr'],
                        'swing_low': self.swing_low,
                        'swing_high': swing_high,
                        'sl_dist_pct': sl_dist_pct
                    }
                }

        # STEP 3: Check timeout
        if self.limit_pending:
            bars_waiting = current_bar_idx - self.limit_placed_bar
            if bars_waiting > self.max_wait_bars:
                self.limit_pending = False
                self.signal_bar_idx = None
                self.swing_low = None
                return None

        return None

    def on_order_filled(self, order: Dict[str, Any]) -> None:
        """Reset state when order fills"""
        self.limit_pending = False
        self.signal_bar_idx = None
        self.swing_low = None

    def on_order_cancelled(self, order: Dict[str, Any]) -> None:
        """Reset state when order cancelled/timeout"""
        self.limit_pending = False
        self.signal_bar_idx = None
        self.swing_low = None
        self.armed = False

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """Wrapper for generate_signals to match BaseStrategy interface"""
        return self.generate_signals(df_1min, [])
