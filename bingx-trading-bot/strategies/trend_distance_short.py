"""
Trend + Distance SHORT Strategy

8.88x R:R ratio, +20.08% return, -2.26% DD (from backtest)
"""

from typing import Optional, Dict, Any
import pandas as pd
from .base_strategy import BaseStrategy


class TrendDistanceShortStrategy(BaseStrategy):
    """
    Trend + Distance SHORT strategy
    - Strong downtrend filter (below 50 & 200 SMA)
    - 2% distance requirement from 50 SMA
    - Explosive bearish breakdown
    """

    def __init__(self, config: Dict[str, Any], symbol: str = 'FARTCOIN-USDT'):
        super().__init__('trend_distance_short', config, symbol)

        # Extract strategy parameters - params may be at root or under 'params' key
        params = config.get('params', config)  # Support both config structures
        self.body_threshold = params.get('body_threshold', 1.2)
        self.volume_multiplier = params.get('volume_multiplier', 3.0)
        self.wick_threshold = params.get('wick_threshold', 0.35)
        self.rsi_short_min = params.get('rsi_short_min', 25)
        self.rsi_short_max = params.get('rsi_short_max', 55)
        self.stop_atr_mult = params.get('stop_atr_mult', 3.0)
        self.target_atr_mult = params.get('target_atr_mult', 15.0)
        self.distance_from_50sma = params.get('distance_from_50sma', 2.0)
        self.below_200sma = params.get('below_200sma', True)

    def analyze(self, df_1min: pd.DataFrame, df_5min: Optional[pd.DataFrame] = None) -> Optional[Dict[str, Any]]:
        """Analyze market and generate SHORT signal"""
        if len(df_1min) < 250:
            return None

        # Get latest candle
        row = df_1min.iloc[-1]

        # Check required indicators exist
        if pd.isna(row.get('atr')) or pd.isna(row.get('rsi')) or pd.isna(row.get('sma_200')):
            return None

        # STRONG DOWNTREND FILTER
        below_50sma = row['close'] < row.get('sma_50', row['close'])
        below_200sma_check = row['close'] < row.get('sma_200', row['close']) if self.below_200sma else True

        # Distance from 50 SMA (at least 2% below)
        distance = ((row.get('sma_50', row['close']) - row['close']) / row.get('sma_50', row['close'])) * 100
        strong_distance = distance > self.distance_from_50sma

        if not (below_50sma and below_200sma_check and strong_distance):
            return None

        # EXPLOSIVE BEARISH BREAKDOWN
        pattern_detected = (
            row['is_bearish'] and
            row['downtrend'] and
            row['body_pct'] > self.body_threshold and
            row['vol_ratio'] > self.volume_multiplier and
            row['lower_wick'] < row['body'] * self.wick_threshold and
            row['upper_wick'] < row['body'] * self.wick_threshold and
            row['rsi'] > self.rsi_short_min and row['rsi'] < self.rsi_short_max and
            row['high_vol']
        )

        if not pattern_detected:
            return None

        # SIGNAL GENERATED
        self.signals_generated += 1

        entry_price = row['close']
        atr = row['atr']

        stop_loss = entry_price + (self.stop_atr_mult * atr)
        take_profit = entry_price - (self.target_atr_mult * atr)

        return {
            'direction': 'SHORT',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'pattern': 'Explosive Bearish Breakdown',
            'confidence': 0.88,
            'atr': atr
        }
