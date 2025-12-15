"""
TRUMPSOL ATR Expansion Strategy with Trend Filter
LONG-only when Price > EMA20 (trend alignment) + Daily RSI > 50 + Limit orders

Performance (60d backtest):
- Return: +24.65%
- Max DD: -4.66%
- R/DD: 5.29x
- Trades: 23
- Win Rate: 39.1%
- TP Rate: 34.8%

Config: ATR 1.5x, EMA 2%, TP 8x, SL 1.5x, Limit 0.5%, Price > EMA20

Status: NOT LIVE - Available for future deployment
"""

from typing import Optional, Dict
import pandas as pd

class TrumpsolATRExpansion:
    """TRUMPSOL ATR Expansion with Trend Filter (Price > EMA20)"""

    def __init__(self):
        self.name = "TRUMPSOL_ATR_EXPANSION"
        self.symbol = "TRUMPSOL-USDT"
        self.timeframes = ["1m", "1d"]  # Need daily for RSI

        # Optimized parameters
        self.atr_threshold = 1.5      # ATR expansion threshold
        self.ema_distance = 2.0       # Max distance from EMA20 (%)
        self.tp_multiplier = 8.0      # Take profit (x ATR)
        self.sl_multiplier = 1.5      # Stop loss (x ATR)
        self.limit_offset_pct = 0.5   # Limit order offset (%)
        self.daily_rsi_min = 50       # Daily RSI minimum
        self.trend_filter = True      # CRITICAL: Only LONG above EMA20

        self.atr_period = 14
        self.atr_ma_period = 20
        self.ema_period = 20
        self.max_hold_bars = 200

    def calculate_indicators(self, df_1m: pd.DataFrame, df_1d: pd.DataFrame) -> pd.DataFrame:
        """Calculate all required indicators"""
        df = df_1m.copy()

        # ATR and ATR MA
        df['atr'] = self._calculate_atr(df, self.atr_period)
        df['atr_ma'] = df['atr'].rolling(self.atr_ma_period).mean()
        df['atr_ratio'] = df['atr'] / df['atr_ma']

        # EMA20 for trend and distance
        df['ema20'] = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        df['distance_pct'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)

        # Trend filter - price above EMA
        df['above_ema'] = df['close'] > df['ema20']

        # Bullish candle
        df['is_bullish'] = df['close'] > df['open']

        # Daily RSI
        df_1d['rsi_daily'] = self._calculate_rsi(df_1d['close'], 14)

        # Merge daily RSI to 1m data
        df = df.set_index('timestamp')
        df_1d_indexed = df_1d.set_index('timestamp')[['rsi_daily']]
        df = df.join(df_1d_indexed, how='left')
        df['rsi_daily'] = df['rsi_daily'].ffill()
        df = df.reset_index()

        return df

    def generate_signal(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Generate LONG signal if all conditions met
        KEY: Only trade when price > EMA20 (trend alignment)
        Returns None or signal dict with limit order
        """
        if len(df) < max(self.atr_period, self.atr_ma_period, self.ema_period):
            return None

        current = df.iloc[-1]

        # Check all entry conditions
        if pd.isna(current['atr_ratio']) or pd.isna(current['rsi_daily']):
            return None

        # ATR expansion
        if current['atr_ratio'] <= self.atr_threshold:
            return None

        # Distance from EMA20
        if current['distance_pct'] >= self.ema_distance:
            return None

        # Bullish candle
        if not current['is_bullish']:
            return None

        # Daily RSI filter
        if current['rsi_daily'] <= self.daily_rsi_min:
            return None

        # TREND FILTER (KEY: Logical, replicable edge)
        # Only trade ATR expansion when price is ABOVE EMA20 (uptrend)
        # This improved R/DD from 4.02x to 5.29x (31.6% improvement)
        if self.trend_filter and not current['above_ema']:
            return None

        # All conditions met - generate LONG signal with limit order
        signal_price = current['close']
        limit_price = signal_price * (1 + self.limit_offset_pct / 100)

        atr_value = current['atr']
        tp_price = limit_price + (self.tp_multiplier * atr_value)
        sl_price = limit_price - (self.sl_multiplier * atr_value)

        return {
            'strategy': self.name,
            'symbol': self.symbol,
            'direction': 'LONG',
            'order_type': 'LIMIT',
            'limit_price': limit_price,
            'signal_price': signal_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'reason': f'ATR_EXPANSION_{current["atr_ratio"]:.2f}x_TREND_ALIGNED',
            'metadata': {
                'atr_ratio': current['atr_ratio'],
                'distance_pct': current['distance_pct'],
                'daily_rsi': current['rsi_daily'],
                'above_ema': current['above_ema'],
                'atr_value': atr_value
            }
        }

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
