"""
ETH RSI Swing Strategy (Limit Orders)

**Return/DD Ratio: 15.56x** 🏆 BEST SWING STRATEGY!
+134.09% return, -8.62% DD, 96 trades (from 90-day backtest)

Entry Conditions:
- RSI 30/68: LONG when RSI crosses above 30, SHORT when RSI crosses below 68
- Limit Order: 0.6% offset (LONG: -0.6% below signal, SHORT: +0.6% above signal)
- Max wait: 5 bars for limit fill (else cancel)

Exit Conditions:
- Stop Loss: 2.0x ATR from entry
- Take Profit: RSI 68 for LONG, RSI 30 for SHORT
- Max Hold: 168 bars (2.8 hours on 1min TF)

Fees: 0.02% maker (limit orders)
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class ETHRSISwingStrategy(BaseStrategy):
    """
    ETH RSI Mean Reversion with Limit Orders
    - Buy oversold (RSI < 30), sell overbought (RSI > 68)
    - Higher RSI exit (68 vs BTC 65) lets winners run longer
    - Uses real limit orders on exchange
    - 2x ATR dynamic stop loss
    """

    def __init__(self, config: Dict[str, Any], symbol: str = 'ETH-USDT'):
        super().__init__('eth_rsi_swing', config, symbol)

        # Entry parameters
        self.rsi_low = config.get('rsi_low', 30)
        self.rsi_high = config.get('rsi_high', 68)  # Higher than BTC!
        self.limit_offset_pct = config.get('limit_offset_pct', 0.6)
        self.max_wait_bars = config.get('max_wait_bars', 5)

        # Exit parameters
        self.stop_atr_mult = config.get('stop_atr_mult', 2.0)
        self.max_hold_bars = config.get('max_hold_bars', 168)

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None, df_1d: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze market and generate limit order on RSI crossover

        Returns:
            None - No signal
            Dict with 'type': 'PENDING_LIMIT_REQUEST' - Request to place limit order
        """
        if len(df_1min) < 50:
            return None

        current = df_1min.iloc[-1]
        prev = df_1min.iloc[-2]
        current_bar = len(df_1min) - 1

        # Check required indicators
        required_cols = ['rsi', 'atr', 'close', 'high', 'low']
        if any(pd.isna(current.get(col)) for col in required_cols):
            return None

        if pd.isna(prev.get('rsi')):
            return None

        current_rsi = current['rsi']
        prev_rsi = prev['rsi']

        direction = None
        pattern = None

        # LONG signal: RSI crosses above 30
        if prev_rsi <= self.rsi_low and current_rsi > self.rsi_low:
            direction = 'LONG'
            pattern = f'RSI Cross Above {self.rsi_low}'

        # SHORT signal: RSI crosses below 68
        elif prev_rsi >= self.rsi_high and current_rsi < self.rsi_high:
            direction = 'SHORT'
            pattern = f'RSI Cross Below {self.rsi_high}'

        if direction is None:
            return None

        # Calculate limit price (offset from signal)
        signal_price = current['close']
        if direction == 'LONG':
            limit_price = signal_price * (1 - self.limit_offset_pct / 100)  # Below market
        else:  # SHORT
            limit_price = signal_price * (1 + self.limit_offset_pct / 100)  # Above market

        # Calculate SL (from limit price)
        atr = current['atr']
        if direction == 'LONG':
            stop_loss = limit_price - (self.stop_atr_mult * atr)
            take_profit = None  # RSI-based exit
        else:  # SHORT
            stop_loss = limit_price + (self.stop_atr_mult * atr)
            take_profit = None

        # Increment signal counter
        self.signals_generated += 1

        # Return PENDING_LIMIT_REQUEST
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
            'pattern': pattern,
            'confidence': 0.55,  # 55% WR from backtest
            'atr': atr,
            'rsi': current_rsi,
            'limit_offset_pct': self.limit_offset_pct,
            'max_hold_bars': self.max_hold_bars,
            'exit_rsi_target': self.rsi_high if direction == 'LONG' else self.rsi_low,
        }

    def should_exit_rsi(self, current_rsi: float, direction: str) -> bool:
        """Check if RSI-based exit should trigger"""
        if direction == 'LONG':
            return current_rsi >= self.rsi_high
        else:  # SHORT
            return current_rsi <= self.rsi_low

    def should_exit_time(self, current_bar_index: int, entry_bar_index: int) -> bool:
        """Check if time-based exit should trigger"""
        bars_held = current_bar_index - entry_bar_index
        return bars_held >= self.max_hold_bars

    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        stats = super().get_statistics()
        stats.update({
            'rsi_low': self.rsi_low,
            'rsi_high': self.rsi_high,
            'limit_offset_pct': self.limit_offset_pct,
            'stop_atr_mult': self.stop_atr_mult,
            'max_hold_bars': self.max_hold_bars,
        })
        return stats
