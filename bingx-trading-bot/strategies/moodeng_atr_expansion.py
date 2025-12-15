"""
MOODENG ATR Expansion Strategy
LONG-only with Daily RSI > 50 filter + Limit orders

Performance (60d backtest):
- Return: +73.8%
- Max DD: -5.53%
- R/DD: 13.34x
- Trades: 26
- Win Rate: 46.2%
- TP Rate: 42.3%

Config: ATR 1.4x, EMA 2%, TP 6x, SL 1.5x, Limit 0.7%
"""

from typing import Optional, Dict
import pandas as pd

class MoodengATRExpansion:
    """MOODENG ATR Expansion with Daily RSI filter"""
    
    def __init__(self):
        self.name = "MOODENG_ATR_EXPANSION"
        self.symbol = "MOODENG-USDT"
        self.timeframes = ["1m", "1d"]  # Need daily for RSI
        
        # Optimized parameters
        self.atr_threshold = 1.4      # ATR expansion threshold
        self.ema_distance = 2.0       # Max distance from EMA20 (%)
        self.tp_multiplier = 6.0      # Take profit (x ATR)
        self.sl_multiplier = 1.5      # Stop loss (x ATR)
        self.limit_offset_pct = 0.7   # Limit order offset (%)
        self.daily_rsi_min = 50       # Daily RSI minimum
        
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
        
        # EMA20
        df['ema20'] = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        df['distance_pct'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)
        
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
            'reason': f'ATR_EXPANSION_{current["atr_ratio"]:.2f}x_RSI_{current["rsi_daily"]:.1f}',
            'metadata': {
                'atr_ratio': current['atr_ratio'],
                'distance_pct': current['distance_pct'],
                'daily_rsi': current['rsi_daily'],
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
