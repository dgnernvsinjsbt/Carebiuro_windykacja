"""
FARTCOIN SHORT Reversal Strategy - OPTIMIZED

Individual Performance (Jun-Dec 2025, 15m candles, 5% risk/trade):
- Contribution to Portfolio: $825,559 (15.9% of total)
- Trades: 86
- Best Trade: +$425,624 (Dec 10)

Portfolio Context (all 4 coins combined):
- Total Return: +5,204,473% ($100 → $5.2M)
- Max DD: -65.9% (realistic with 5% risk)
- Return/DD: 78,973x

Strategy Logic:
1. SIGNAL: RSI(14) > 70 (overbought, ready for reversal)
2. ARM: Wait for price to break below swing low (5-candle lookback)
3. ENTRY: Place LIMIT order 1.0 ATR above swing low (catch pullback)
4. SL: Swing high from signal bar to break bar
5. TP: 10% below entry (fixed target)

Position Sizing: 5% risk per trade based on SL distance
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class FartcoinShortReversal(BaseStrategy):
    """FARTCOIN SHORT Reversal Strategy with Limit Orders"""

    def __init__(self, config: Dict[str, Any], symbol: str = 'FARTCOIN-USDT'):
        super().__init__('fartcoin_short_reversal', config, symbol)

        # Strategy parameters (from backtest optimization)
        self.rsi_trigger = 70
        self.lookback = 5
        self.limit_atr_offset = 1.0
        self.tp_pct = 10.0
        self.max_wait_bars = 20
        self.max_sl_pct = 10.0  # Skip trade if SL > 10%

        # State tracking
        self.armed = False
        self.signal_bar_idx = None
        self.swing_low = None
        self.limit_pending = False
        self.limit_placed_bar = None

    def generate_signals(self, df: pd.DataFrame, current_positions: list) -> Optional[Dict[str, Any]]:
        """Generate SHORT reversal signals with detailed logging"""

        # Don't generate new signals if we already have a position
        if current_positions:
            self.logger.debug(f"[FARTCOIN] Skipping signal check - already have position")
            return None

        # Need enough data for lookback
        if len(df) < self.lookback + 14:
            self.logger.debug(f"[FARTCOIN] Insufficient data - need {self.lookback + 14}, have {len(df)}")
            return None

        latest = df.iloc[-1]
        timestamp = latest.get('timestamp', 'N/A')

        # Check for required indicators
        if pd.isna(latest['rsi']) or pd.isna(latest['atr']):
            self.logger.warning(f"[FARTCOIN] Missing indicators at {timestamp} - RSI: {latest['rsi']}, ATR: {latest['atr']}")
            return None

        current_bar_idx = len(df) - 1

        # Determine current state
        if self.limit_pending:
            state = "PENDING"
        elif self.armed:
            state = "ARMED"
        else:
            state = "IDLE"

        # LOG EVERY POLL - pokazuje obecny stan i dane rynkowe
        self.logger.info(f"[FARTCOIN] 📊 Poll {timestamp} | State: {state} | Price: ${latest['close']:.4f} | RSI: {latest['rsi']:.2f} | ATR: ${latest['atr']:.4f}")

        # STEP 1: ARM on RSI > 70
        if latest['rsi'] > self.rsi_trigger and not self.armed and not self.limit_pending:
            self.armed = True
            self.signal_bar_idx = current_bar_idx
            # Calculate swing low (lowest low in last 5 candles including current)
            self.swing_low = df.iloc[-self.lookback:]['low'].min()

            self.logger.info(f"[FARTCOIN] 🎯 ARMED! RSI {latest['rsi']:.2f} > {self.rsi_trigger} at {timestamp}")
            self.logger.info(f"[FARTCOIN]    → Swing Low: ${self.swing_low:.4f} (watching for break)")
            self.logger.info(f"[FARTCOIN]    → Current Price: ${latest['close']:.4f} (${(latest['close'] - self.swing_low):.4f} above support)")

            return None  # Just armed, no order yet

        # STEP 2: Check if price broke below swing low
        if self.armed and self.swing_low is not None and not self.limit_pending:
            distance_to_support = latest['low'] - self.swing_low
            self.logger.info(f"[FARTCOIN] 👀 ARMED - Watching swing low ${self.swing_low:.4f} | Current Low: ${latest['low']:.4f} | Distance: ${distance_to_support:.4f}")

            if latest['low'] < self.swing_low:
                # Price broke support! Place limit order
                limit_price = self.swing_low + (latest['atr'] * self.limit_atr_offset)

                # Calculate swing high (from signal bar to current bar)
                swing_high = df.iloc[self.signal_bar_idx:current_bar_idx+1]['high'].max()

                # Calculate SL distance
                sl_dist_pct = ((swing_high - limit_price) / limit_price) * 100

                self.logger.info(f"[FARTCOIN] 💥 SUPPORT BROKEN! Low ${latest['low']:.4f} < ${self.swing_low:.4f}")
                self.logger.info(f"[FARTCOIN]    → Limit Price: ${limit_price:.4f} (swing_low + {self.limit_atr_offset}*ATR)")
                self.logger.info(f"[FARTCOIN]    → Stop Loss: ${swing_high:.4f} (swing high from signal)")
                self.logger.info(f"[FARTCOIN]    → Take Profit: ${limit_price * (1 - self.tp_pct / 100):.4f} ({self.tp_pct}% below entry)")
                self.logger.info(f"[FARTCOIN]    → SL Distance: {sl_dist_pct:.2f}%")

                # Skip if SL too wide
                if sl_dist_pct <= 0 or sl_dist_pct > self.max_sl_pct:
                    self.logger.warning(f"[FARTCOIN] ❌ TRADE SKIPPED - SL distance {sl_dist_pct:.2f}% outside valid range (0% < SL < {self.max_sl_pct}%)")
                    self.logger.warning(f"[FARTCOIN]    → Limit: ${limit_price:.4f}, SL: ${swing_high:.4f}, Distance: {sl_dist_pct:.2f}%")
                    self.armed = False
                    return None

                # Calculate TP
                tp_price = limit_price * (1 - self.tp_pct / 100)

                # Mark as pending
                self.limit_pending = True
                self.limit_placed_bar = current_bar_idx
                self.armed = False

                self.logger.info(f"[FARTCOIN] ✅ LIMIT ORDER PLACED - Waiting up to {self.max_wait_bars} bars (5 hours) for fill")
                self.logger.info(f"[FARTCOIN]    → Will cancel if not filled by bar {current_bar_idx + self.max_wait_bars}")

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

        # STEP 3: Check if limit order timed out
        if self.limit_pending:
            bars_waiting = current_bar_idx - self.limit_placed_bar
            remaining = self.max_wait_bars - bars_waiting

            self.logger.info(f"[FARTCOIN] ⏳ PENDING - Waiting for limit fill | Bars: {bars_waiting}/{self.max_wait_bars} | Remaining: {remaining} bars ({remaining * 15} min)")

            if bars_waiting > self.max_wait_bars:
                # Timeout, reset state
                self.logger.warning(f"[FARTCOIN] ⏰ TIMEOUT - Limit order not filled after {bars_waiting} bars ({bars_waiting * 15} min)")
                self.logger.warning(f"[FARTCOIN]    → Cancelling order and resetting state")

                self.limit_pending = False
                self.signal_bar_idx = None
                self.swing_low = None
                return None

        return None

    def on_order_filled(self, order: Dict[str, Any]) -> None:
        """Reset state when order fills"""
        self.logger.info(f"[FARTCOIN] ✅ ORDER FILLED - Resetting state")
        self.logger.info(f"[FARTCOIN]    → Entry: ${order.get('limit_price', 'N/A')}, SL: ${order.get('stop_loss', 'N/A')}, TP: ${order.get('take_profit', 'N/A')}")
        self.limit_pending = False
        self.signal_bar_idx = None
        self.swing_low = None

    def on_order_cancelled(self, order: Dict[str, Any]) -> None:
        """Reset state when order cancelled/timeout"""
        self.logger.warning(f"[FARTCOIN] ❌ ORDER CANCELLED - Resetting state")
        self.logger.warning(f"[FARTCOIN]    → Reason: {order.get('reason', 'Unknown')}")
        self.limit_pending = False
        self.signal_bar_idx = None
        self.swing_low = None
        self.armed = False

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """Wrapper for generate_signals to match BaseStrategy interface"""
        return self.generate_signals(df_1min, [])
