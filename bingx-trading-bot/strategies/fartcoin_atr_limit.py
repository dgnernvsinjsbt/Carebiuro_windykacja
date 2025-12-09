"""
FARTCOIN ATR Expansion (Limit Order) Strategy

**Return/DD Ratio: 8.44x (Rank #4)**
+101.11% return, -11.98% DD, 42.6% WR (from 32-day backtest)

Entry Conditions:
- ATR Expansion: Current ATR > 1.5x rolling 20-bar average (volatility breakout)
- EMA Distance Filter: Price within 3% of EMA(20) (prevents late entries)
- Directional Candle: Bullish (close > open) for LONG, Bearish for SHORT
- Limit Order: Place 1% away from signal price, wait max 3 bars for fill

Exit Conditions:
- Stop Loss: 2.0x ATR from entry
- Take Profit: 8.0x ATR from entry (4:1 R:R)
- Max Hold: 200 bars (3.3 hours)

Fees: 0.05% per side (limit orders that fill as aggressive taker)

LIVE IMPLEMENTATION:
- Uses REAL limit orders on BingX
- PendingOrderManager tracks order status
- Cancels if no fill after 3 bars (3 minutes)
- Avoids 55-second slippage from polling delay
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class FartcoinATRLimitStrategy(BaseStrategy):
    """
    FARTCOIN ATR Expansion + Limit Order strategy
    - Catches explosive pump/dump moves via ATR expansion
    - Uses real limit orders on exchange (not simulation)
    - EMA distance prevents overextended entries
    - 4:1 R:R with 8x ATR target
    """

    def __init__(self, config: Dict[str, Any], symbol: str = 'FARTCOIN-USDT'):
        super().__init__('fartcoin_atr_limit', config, symbol)

        # Strategy parameters from config
        self.atr_expansion_mult = config.get('atr_expansion_mult', 1.5)
        self.atr_lookback_bars = config.get('atr_lookback_bars', 20)
        self.ema_distance_max_pct = config.get('ema_distance_max_pct', 3.0)
        self.limit_offset_pct = config.get('limit_offset_pct', 1.0)
        self.max_wait_bars = config.get('max_wait_bars', 3)

        # Exit parameters
        self.stop_atr_mult = config.get('stop_atr_mult', 2.0)
        self.target_atr_mult = config.get('target_atr_mult', 8.0)
        self.max_hold_bars = config.get('max_hold_bars', 200)

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze market and generate pending limit order request on ATR expansion

        Returns:
            None - No signal
            Dict with 'type': 'PENDING_LIMIT_REQUEST' - Request to place limit order
            Dict with 'type': 'SIGNAL' - Unused (PendingOrderManager returns filled signals)
        """
        if len(df_1min) < 30:  # Need enough data for indicators
            return None

        current = df_1min.iloc[-1]
        current_bar = len(df_1min) - 1

        # Check required indicators
        required_cols = ['atr', 'ema_20', 'close', 'open', 'high', 'low']
        if any(pd.isna(current.get(col)) for col in required_cols):
            return None

        # Calculate ATR expansion ratio
        df_recent = df_1min.tail(self.atr_lookback_bars)
        atr_avg = df_recent['atr'].mean()

        if pd.isna(atr_avg) or atr_avg == 0:
            return None

        atr_ratio = current['atr'] / atr_avg

        # Check ATR expansion
        if atr_ratio <= self.atr_expansion_mult:
            return None

        # Check EMA distance (must be within 3%)
        ema_distance_pct = abs((current['close'] - current['ema_20']) / current['ema_20'] * 100)
        if ema_distance_pct > self.ema_distance_max_pct:
            return None

        # Determine direction from candle
        is_bullish = current['close'] > current['open']
        is_bearish = current['close'] < current['open']

        if not (is_bullish or is_bearish):
            return None  # Doji - skip

        direction = 'LONG' if is_bullish else 'SHORT'

        # Calculate limit price (1% away from signal)
        signal_price = current['close']
        if direction == 'LONG':
            limit_price = signal_price * (1 + self.limit_offset_pct / 100)
        else:  # SHORT
            limit_price = signal_price * (1 - self.limit_offset_pct / 100)

        # Calculate SL/TP (from limit price, not signal price)
        atr = current['atr']
        if direction == 'LONG':
            stop_loss = limit_price - (self.stop_atr_mult * atr)
            take_profit = limit_price + (self.target_atr_mult * atr)
        else:  # SHORT
            stop_loss = limit_price + (self.stop_atr_mult * atr)
            take_profit = limit_price - (self.target_atr_mult * atr)

        # Increment signal counter
        self.signals_generated += 1

        # Return PENDING_LIMIT_REQUEST (not a signal yet!)
        # PendingOrderManager will place the actual limit order
        return {
            'type': 'PENDING_LIMIT_REQUEST',
            'strategy': self.name,
            'direction': direction,
            'signal_price': signal_price,
            'limit_price': limit_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'current_bar': current_bar,
            'max_wait_bars': self.max_wait_bars,
            'pattern': f'ATR Expansion {atr_ratio:.2f}x',
            'confidence': 0.80,  # 42.6% WR but excellent R:R
            'atr': atr,
            'atr_ratio': atr_ratio,
            'ema_distance_pct': ema_distance_pct,
            'limit_offset_pct': self.limit_offset_pct,
            'max_hold_bars': self.max_hold_bars,
        }

    def should_exit_time(self, current_bar_index: int, entry_bar_index: int) -> bool:
        """Check if time-based exit should trigger (200 bars = 3.3 hours)"""
        bars_held = current_bar_index - entry_bar_index
        return bars_held >= self.max_hold_bars

    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        stats = super().get_statistics()
        stats.update({
            'atr_expansion_mult': self.atr_expansion_mult,
            'ema_distance_max_pct': self.ema_distance_max_pct,
            'limit_offset_pct': self.limit_offset_pct,
            'r_r_ratio': f'{self.target_atr_mult}:{self.stop_atr_mult}',
            'max_hold_minutes': self.max_hold_bars,
        })
        return stats
