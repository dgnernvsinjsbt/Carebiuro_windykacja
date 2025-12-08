"""
MOODENG RSI Momentum LONG Strategy

**Best Strategy by Return/DD Ratio: 10.68x**
+24.02% return, -2.25% DD, 31% WR (from backtest)

Entry Conditions:
- RSI(14) crosses above 55 (prev < 55, current >= 55)
- Bullish candle with body > 0.5%
- Price above SMA(20)

Exit Conditions:
- Stop Loss: 1.0x ATR below entry
- Take Profit: 4.0x ATR above entry
- Time Exit: 60 bars (60 minutes) if neither SL/TP hit
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class MoodengRSIMomentumStrategy(BaseStrategy):
    """
    MOODENG RSI Momentum strategy
    - Catches RSI momentum breakouts above 55
    - Confirms with bullish candle and uptrend
    - 4:1 R:R with tight stops
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__('moodeng_rsi_momentum', config)

        # Extract strategy parameters
        params = config.get('params', {})
        self.rsi_cross_level = params.get('rsi_cross_level', 55)
        self.min_body_pct = params.get('min_body_pct', 0.5)
        self.stop_atr_mult = params.get('stop_atr_mult', 1.0)
        self.target_atr_mult = params.get('target_atr_mult', 4.0)
        self.max_hold_bars = params.get('max_hold_bars', 60)

        # Track entry candle for time exit
        self.entry_time = None

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """Analyze market and generate LONG signal on RSI cross above 55"""
        if len(df_1min) < 30:  # Need at least 20 for SMA + 14 for RSI
            return None

        # Get latest and previous candle
        current = df_1min.iloc[-1]
        previous = df_1min.iloc[-2]

        # Check required indicators exist
        required_cols = ['rsi', 'sma_20', 'atr', 'close', 'open']
        if any(pd.isna(current.get(col)) for col in required_cols):
            return None

        # CONDITION 1: RSI crossed above 55
        rsi_cross = previous['rsi'] < self.rsi_cross_level and current['rsi'] >= self.rsi_cross_level

        if not rsi_cross:
            return None

        # CONDITION 2: Bullish candle with body > 0.5%
        body_pct = abs(current['close'] - current['open']) / current['open'] * 100
        is_bullish = current['close'] > current['open']
        strong_body = body_pct > self.min_body_pct

        if not (is_bullish and strong_body):
            return None

        # CONDITION 3: Price above SMA(20)
        above_sma = current['close'] > current['sma_20']

        if not above_sma:
            return None

        # ALL CONDITIONS MET - GENERATE SIGNAL
        self.signals_generated += 1

        entry_price = current['close']
        atr = current['atr']

        # Calculate SL/TP (1:4 R:R)
        stop_loss = entry_price - (self.stop_atr_mult * atr)
        take_profit = entry_price + (self.target_atr_mult * atr)

        # Store entry time for time-based exit tracking
        self.entry_time = current.get('timestamp', pd.Timestamp.now())

        return {
            'direction': 'LONG',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'pattern': f'RSI Cross Above {self.rsi_cross_level}',
            'confidence': 0.75,  # 31% WR but excellent R:R
            'atr': atr,
            'rsi': current['rsi'],
            'body_pct': body_pct,
            'max_hold_bars': self.max_hold_bars
        }

    def should_exit_time(self, current_bar_index: int, entry_bar_index: int) -> bool:
        """Check if time-based exit should trigger"""
        bars_held = current_bar_index - entry_bar_index
        return bars_held >= self.max_hold_bars

    def get_statistics(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        stats = super().get_statistics()
        stats.update({
            'rsi_cross_level': self.rsi_cross_level,
            'min_body_pct': self.min_body_pct,
            'r_r_ratio': f'{self.target_atr_mult}:{self.stop_atr_mult}',
            'max_hold_minutes': self.max_hold_bars
        })
        return stats
