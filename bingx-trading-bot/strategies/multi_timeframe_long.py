"""
Multi-Timeframe LONG Strategy

7.14x R:R ratio, +10.38% return, -1.45% DD (from backtest)
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class MultiTimeframeLongStrategy(BaseStrategy):
    """
    Multi-timeframe LONG strategy
    - 1-min explosive bullish pattern
    - 5-min uptrend confirmation
    """

    def __init__(self, config: Dict[str, Any], symbol: str = 'FARTCOIN-USDT'):
        super().__init__('multi_timeframe_long', config, symbol)

        # Extract strategy parameters - params may be at root or under 'params' key
        params = config.get('params', config)  # Support both config structures
        self.body_threshold = params.get('body_threshold', 1.2)
        self.volume_multiplier = params.get('volume_multiplier', 3.0)
        self.wick_threshold = params.get('wick_threshold', 0.35)
        self.rsi_long_min = params.get('rsi_long_min', 45)
        self.stop_atr_mult = params.get('stop_atr_mult', 3.0)
        self.target_atr_mult = params.get('target_atr_mult', 12.0)
        self.rsi_5min_min = params.get('rsi_5min_min', 57)
        self.distance_from_sma = params.get('distance_from_sma', 0.6)

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """Analyze market and generate LONG signal"""
        if len(df_1min) < 250:
            return None

        # Get latest candle
        row = df_1min.iloc[-1]

        # Check required indicators exist
        if pd.isna(row.get('atr')) or pd.isna(row.get('rsi')):
            return None

        # 1-MIN EXPLOSIVE BULLISH BREAKOUT
        pattern_detected = (
            row['is_bullish'] and
            row['uptrend'] and
            row['body_pct'] > self.body_threshold and
            row['vol_ratio'] > self.volume_multiplier and
            row['lower_wick'] < row['body'] * self.wick_threshold and
            row['upper_wick'] < row['body'] * self.wick_threshold and
            row['rsi'] > self.rsi_long_min and row['rsi'] < 75 and
            row['high_vol']
        )

        if not pattern_detected:
            return None

        # CHECK 5-MIN FILTER
        if df_5min is not None and len(df_5min) > 0:
            row_5min = df_5min.iloc[-1]

            close_above_sma = row_5min['close'] > row_5min.get('sma_50', 0)
            rsi_bullish = row_5min.get('rsi', 50) > self.rsi_5min_min

            distance = ((row_5min['close'] - row_5min.get('sma_50', row_5min['close'])) /
                       row_5min.get('sma_50', row_5min['close'])) * 100
            strong_distance = distance > self.distance_from_sma

            if not (close_above_sma and rsi_bullish and strong_distance):
                return None

        # SIGNAL GENERATED
        self.signals_generated += 1

        entry_price = row['close']
        atr = row['atr']

        stop_loss = entry_price - (self.stop_atr_mult * atr)
        take_profit = entry_price + (self.target_atr_mult * atr)

        return {
            'direction': 'LONG',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'pattern': 'Explosive Bullish Breakout',
            'confidence': 0.85,
            'atr': atr
        }
