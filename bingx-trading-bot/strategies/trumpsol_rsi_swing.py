"""
TRUMPSOL RSI Swing Strategy - CORRECTED RSI

Performance (90 days, 1h candles - WITH FIXED WILDER'S RSI):
- Return/DD: 2.10x
- Return: +1.31%
- Max DD: -0.62%
- Win Rate: 76.9%
- Trades: 13

Entry: RSI(14) crosses above 30 (LONG) or below 65 (SHORT)
Limit: 1.5% offset from signal price (wait max 5 bars)
Exit: 2.0x ATR stop loss, 1.5x ATR take profit, or RSI reversal
"""

from typing import Dict, Any, Optional
import pandas as pd
from .base_strategy import BaseStrategy


class TRUMPSOLRSISwingStrategy(BaseStrategy):
    """TRUMPSOL RSI Mean Reversion Strategy with Limit Orders"""

    def __init__(self, config: Dict[str, Any], symbol: str = 'TRUMPSOL'):
        super().__init__('trumpsol_rsi_swing', config, symbol)

        # RSI parameters
        self.rsi_low = config.get('rsi_low', 30)
        self.rsi_high = config.get('rsi_high', 65)

        # Limit order parameters
        self.limit_offset_pct = config.get('limit_offset_pct', 1.5)
        self.max_wait_bars = config.get('max_wait_bars', 5)

        # Exit parameters
        self.stop_atr_mult = config.get('stop_atr_mult', 2.0)
        self.tp_atr_mult = config.get('tp_atr_mult', 1.5)
        self.max_hold_bars = config.get('max_hold_bars', 0)  # 0 = disabled

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """Required analyze method for BaseStrategy compatibility"""
        return self.generate_signals(df_1min, [])

    def generate_signals(self, df: pd.DataFrame, current_positions: list) -> Optional[Dict[str, Any]]:
        """Generate LONG/SHORT signals based on RSI crossovers"""

        if len(df) < 2:
            return None

        if current_positions:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        if pd.isna(latest['rsi']) or pd.isna(latest['atr']):
            return None

        # LONG signal: RSI crosses above 30
        if latest['rsi'] > self.rsi_low and prev['rsi'] <= self.rsi_low:
            signal_price = latest['close']
            limit_price = signal_price * (1 - self.limit_offset_pct / 100)
            stop_loss = limit_price - (self.stop_atr_mult * latest['atr'])
            take_profit = limit_price + (self.tp_atr_mult * latest['atr'])

            return {
                'side': 'LONG',
                'type': 'LIMIT',
                'limit_price': limit_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'max_wait_bars': self.max_wait_bars,
                'reason': f"RSI crossed above {self.rsi_low} ({latest['rsi']:.1f})",
                'metadata': {'rsi': latest['rsi'], 'atr': latest['atr'], 'signal_price': signal_price}
            }

        # SHORT signal: RSI crosses below 65
        elif latest['rsi'] < self.rsi_high and prev['rsi'] >= self.rsi_high:
            signal_price = latest['close']
            limit_price = signal_price * (1 + self.limit_offset_pct / 100)
            stop_loss = limit_price + (self.stop_atr_mult * latest['atr'])
            take_profit = limit_price - (self.tp_atr_mult * latest['atr'])

            return {
                'side': 'SHORT',
                'type': 'LIMIT',
                'limit_price': limit_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'max_wait_bars': self.max_wait_bars,
                'reason': f"RSI crossed below {self.rsi_high} ({latest['rsi']:.1f})",
                'metadata': {'rsi': latest['rsi'], 'atr': latest['atr'], 'signal_price': signal_price}
            }

        return None

    def should_exit(self, position: Dict[str, Any], df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Exit logic: RSI reversal or max hold time"""

        if len(df) < 2:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # Calculate bars held
        entry_bar = position.get('entry_bar', 0)
        if isinstance(latest.name, int):
            bars_held = latest.name - entry_bar
        else:
            # For timestamp index, count rows
            bars_held = len(df) - 1 - entry_bar if entry_bar < len(df) else 0

        # RSI exit
        if position['side'] == 'LONG':
            if latest['rsi'] < self.rsi_high and prev['rsi'] >= self.rsi_high:
                return {'reason': f'RSI exit (crossed below {self.rsi_high})', 'exit_price': latest['close']}
        else:
            if latest['rsi'] > self.rsi_low and prev['rsi'] <= self.rsi_low:
                return {'reason': f'RSI exit (crossed above {self.rsi_low})', 'exit_price': latest['close']}

        # Time exit (only if max_hold_bars > 0)
        if self.max_hold_bars > 0 and bars_held >= self.max_hold_bars:
            return {'reason': f'Time exit ({bars_held} bars)', 'exit_price': latest['close']}

        return None
