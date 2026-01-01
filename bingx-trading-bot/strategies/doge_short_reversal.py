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
        """Generate SHORT reversal signals with detailed logging"""

        if current_positions:
            self.logger.debug(f"[DOGE] Skipping signal check - already have position")
            return None

        if len(df) < self.lookback + 14:
            self.logger.debug(f"[DOGE] Insufficient data - need {self.lookback + 14}, have {len(df)}")
            return None

        latest = df.iloc[-1]
        timestamp = latest.get('timestamp', 'N/A')

        if pd.isna(latest['rsi']) or pd.isna(latest['atr']):
            self.logger.warning(f"[DOGE] Missing indicators at {timestamp} - RSI: {latest['rsi']}, ATR: {latest['atr']}")
            return None

        current_bar_idx = len(df) - 1

        # Determine current state
        if self.limit_pending:
            state = "PENDING"
        elif self.armed:
            state = "ARMED"
        else:
            state = "IDLE"

        # LOG EVERY POLL
        self.logger.info(f"[DOGE] 📊 Poll {timestamp} | State: {state} | Price: ${latest['close']:.4f} | RSI: {latest['rsi']:.2f} | ATR: ${latest['atr']:.4f}")

        # STEP 1: ARM on RSI > 72
        if latest['rsi'] > self.rsi_trigger and not self.armed and not self.limit_pending:
            self.armed = True
            self.signal_bar_idx = current_bar_idx
            self.swing_low = df.iloc[-self.lookback:]['low'].min()

            self.logger.info(f"[DOGE] 🎯 ARMED! RSI {latest['rsi']:.2f} > {self.rsi_trigger} at {timestamp}")
            self.logger.info(f"[DOGE]    → Swing Low: ${self.swing_low:.4f} (watching for break)")
            self.logger.info(f"[DOGE]    → Current Price: ${latest['close']:.4f} (${(latest['close'] - self.swing_low):.4f} above support)")

            return None

        # STEP 2: Check if price broke below swing low
        if self.armed and self.swing_low is not None and not self.limit_pending:
            distance_to_support = latest['low'] - self.swing_low
            self.logger.info(f"[DOGE] 👀 ARMED - Watching swing low ${self.swing_low:.4f} | Current Low: ${latest['low']:.4f} | Distance: ${distance_to_support:.4f}")

            if latest['low'] < self.swing_low:
                limit_price = self.swing_low + (latest['atr'] * self.limit_atr_offset)
                swing_high = df.iloc[self.signal_bar_idx:current_bar_idx+1]['high'].max()
                sl_dist_pct = ((swing_high - limit_price) / limit_price) * 100

                self.logger.info(f"[DOGE] 💥 SUPPORT BROKEN! Low ${latest['low']:.4f} < ${self.swing_low:.4f}")
                self.logger.info(f"[DOGE]    → Limit Price: ${limit_price:.4f} (swing_low + {self.limit_atr_offset}*ATR)")
                self.logger.info(f"[DOGE]    → Stop Loss: ${swing_high:.4f} (swing high from signal)")
                self.logger.info(f"[DOGE]    → Take Profit: ${limit_price * (1 - self.tp_pct / 100):.4f} ({self.tp_pct}% below entry)")
                self.logger.info(f"[DOGE]    → SL Distance: {sl_dist_pct:.2f}%")

                if sl_dist_pct <= 0 or sl_dist_pct > self.max_sl_pct:
                    self.logger.warning(f"[DOGE] ❌ TRADE SKIPPED - SL distance {sl_dist_pct:.2f}% outside valid range (0% < SL < {self.max_sl_pct}%)")
                    self.logger.warning(f"[DOGE]    → Limit: ${limit_price:.4f}, SL: ${swing_high:.4f}, Distance: {sl_dist_pct:.2f}%")
                    self.armed = False
                    return None

                tp_price = limit_price * (1 - self.tp_pct / 100)

                self.limit_pending = True
                self.limit_placed_bar = current_bar_idx
                self.armed = False

                self.logger.info(f"[DOGE] ✅ LIMIT ORDER PLACED - Waiting up to {self.max_wait_bars} bars (5 hours) for fill")
                self.logger.info(f"[DOGE]    → Will cancel if not filled by bar {current_bar_idx + self.max_wait_bars}")

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
            remaining = self.max_wait_bars - bars_waiting

            self.logger.info(f"[DOGE] ⏳ PENDING - Waiting for limit fill | Bars: {bars_waiting}/{self.max_wait_bars} | Remaining: {remaining} bars ({remaining * 15} min)")

            if bars_waiting > self.max_wait_bars:
                self.logger.warning(f"[DOGE] ⏰ TIMEOUT - Limit order not filled after {bars_waiting} bars ({bars_waiting * 15} min)")
                self.logger.warning(f"[DOGE]    → Cancelling order and resetting state")

                self.limit_pending = False
                self.signal_bar_idx = None
                self.swing_low = None
                return None

        return None

    def on_order_filled(self, order: Dict[str, Any]) -> None:
        """Reset state when order fills"""
        self.logger.info(f"[DOGE] ✅ ORDER FILLED - Resetting state")
        self.logger.info(f"[DOGE]    → Entry: ${order.get('limit_price', 'N/A')}, SL: ${order.get('stop_loss', 'N/A')}, TP: ${order.get('take_profit', 'N/A')}")
        self.limit_pending = False
        self.signal_bar_idx = None
        self.swing_low = None

    def on_order_cancelled(self, order: Dict[str, Any]) -> None:
        """Reset state when order cancelled/timeout"""
        self.logger.warning(f"[DOGE] ❌ ORDER CANCELLED - Resetting state")
        self.logger.warning(f"[DOGE]    → Reason: {order.get('reason', 'Unknown')}")
        self.limit_pending = False
        self.signal_bar_idx = None
        self.swing_low = None
        self.armed = False

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """Wrapper for generate_signals to match BaseStrategy interface"""
        return self.generate_signals(df_1min, [])
