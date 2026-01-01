"""
Technical Indicators

Calculates technical indicators for trading strategies
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple


def sma(data: pd.Series, period: int) -> pd.Series:
    """
    Simple Moving Average

    Args:
        data: Price series
        period: SMA period

    Returns:
        SMA series
    """
    return data.rolling(window=period).mean()


def ema(data: pd.Series, period: int) -> pd.Series:
    """
    Exponential Moving Average

    Args:
        data: Price series
        period: EMA period

    Returns:
        EMA series
    """
    return data.ewm(span=period, adjust=False).mean()


def rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (Wilder's RSI with EMA smoothing)

    Uses Wilder's smoothing method (EMA) - matches TradingView, BingX, and all
    standard charting platforms.

    Args:
        data: Price series
        period: RSI period (default: 14)

    Returns:
        RSI series (0-100)
    """
    delta = data.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Initialize series
    avg_gain = pd.Series(index=data.index, dtype=float)
    avg_loss = pd.Series(index=data.index, dtype=float)

    # First value: SMA of first 'period' values
    avg_gain.iloc[period] = gain.iloc[1:period+1].mean()
    avg_loss.iloc[period] = loss.iloc[1:period+1].mean()

    # Subsequent values: Wilder's smoothing (EMA with alpha=1/period)
    for i in range(period + 1, len(data)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))

    return rsi_values


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average True Range

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period (default: 14)

    Returns:
        ATR series
    """
    high_low = high - low
    high_close = abs(high - close.shift())
    low_close = abs(low - close.shift())

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr_values = true_range.rolling(window=period).mean()

    return atr_values


def bollinger_bands(data: pd.Series, period: int = 20,
                   std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands

    Args:
        data: Price series
        period: Period for moving average
        std_dev: Number of standard deviations

    Returns:
        Tuple of (middle_band, upper_band, lower_band)
    """
    middle_band = sma(data, period)
    std = data.rolling(window=period).std()

    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)

    return middle_band, upper_band, lower_band


def macd(data: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Moving Average Convergence Divergence

    Args:
        data: Price series
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line period (default: 9)

    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)

    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
              k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        k_period: %K period (default: 14)
        d_period: %D period (default: 3)

    Returns:
        Tuple of (%K, %D)
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(window=d_period).mean()

    return k, d


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average Directional Index

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ADX period (default: 14)

    Returns:
        ADX series
    """
    # Calculate True Range
    tr = atr(high, low, close, period=1)

    # Directional Movement
    up_move = high - high.shift()
    down_move = low.shift() - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # Smooth DM and TR
    plus_dm_smooth = pd.Series(plus_dm, index=close.index).rolling(window=period).mean()
    minus_dm_smooth = pd.Series(minus_dm, index=close.index).rolling(window=period).mean()
    tr_smooth = tr.rolling(window=period).mean()

    # Directional Indicators
    plus_di = 100 * plus_dm_smooth / tr_smooth
    minus_di = 100 * minus_dm_smooth / tr_smooth

    # ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx_values = dx.rolling(window=period).mean()

    return adx_values


def donchian_channel(high: pd.Series, low: pd.Series, period: int = 20) -> Tuple[pd.Series, pd.Series]:
    """
    Donchian Channel

    Args:
        high: High prices
        low: Low prices
        period: Lookback period (default: 20)

    Returns:
        Tuple of (upper_channel, lower_channel)
        upper_channel: Highest high of last N bars (shifted by 1 to avoid lookahead)
        lower_channel: Lowest low of last N bars (shifted by 1 to avoid lookahead)
    """
    upper = high.rolling(window=period).max().shift(1)
    lower = low.rolling(window=period).min().shift(1)
    return upper, lower


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Volume Weighted Average Price

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        volume: Volume

    Returns:
        VWAP series
    """
    typical_price = (high + low + close) / 3
    return (typical_price * volume).cumsum() / volume.cumsum()


def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
              period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """
    SuperTrend Indicator

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period
        multiplier: ATR multiplier

    Returns:
        Tuple of (supertrend, direction)
        direction: 1 for uptrend, -1 for downtrend
    """
    atr_values = atr(high, low, close, period)
    hl_avg = (high + low) / 2

    upper_band = hl_avg + (multiplier * atr_values)
    lower_band = hl_avg - (multiplier * atr_values)

    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)

    # Initialize
    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(close)):
        # Update bands
        if close.iloc[i] > supertrend.iloc[i-1]:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
        else:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1

    return supertrend, direction


class IndicatorCalculator:
    """
    Indicator calculator for real-time data

    Efficiently calculates indicators for streaming data
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize calculator

        Args:
            df: DataFrame with OHLCV data
        """
        self.df = df
        self.required_columns = ['open', 'high', 'low', 'close', 'volume']

        self._validate_data()

    def _validate_data(self) -> None:
        """Validate that required columns exist"""
        missing = [col for col in self.required_columns if col not in self.df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def add_all_indicators(self) -> pd.DataFrame:
        """Add all common indicators to dataframe"""
        df = self.df.copy()

        # Moving averages
        df['sma_20'] = sma(df['close'], 20)
        df['sma_50'] = sma(df['close'], 50)
        df['sma_200'] = sma(df['close'], 200)
        df['ema_20'] = ema(df['close'], 20)

        # RSI
        df['rsi'] = rsi(df['close'], 14)

        # ATR
        df['atr'] = atr(df['high'], df['low'], df['close'], 14)

        # Bollinger Bands
        df['bb_middle'], df['bb_upper'], df['bb_lower'] = bollinger_bands(df['close'], 20, 2.0)

        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = macd(df['close'])

        # Volume indicators
        df['vol_sma'] = sma(df['volume'], 20)
        df['vol_ratio'] = df['volume'] / df['vol_sma']

        # Price structure
        df['body'] = abs(df['close'] - df['open'])
        df['body_pct'] = (df['body'] / df['open']) * 100
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']

        # Trend
        df['uptrend'] = df['close'] > df['sma_50']
        df['downtrend'] = df['close'] < df['sma_50']

        # Volatility
        df['volatility'] = df['atr'].rolling(50).mean()
        df['high_vol'] = df['atr'] > df['volatility'] * 1.1

        return df

    def calculate_for_last_candle(self) -> dict:
        """
        Calculate indicators for the most recent candle

        Returns:
            Dictionary of indicator values
        """
        if len(self.df) < 200:  # Need enough data for 200 SMA
            return {}

        df = self.add_all_indicators()
        last_row = df.iloc[-1]

        return {
            'close': last_row['close'],
            'sma_50': last_row['sma_50'],
            'sma_200': last_row['sma_200'],
            'rsi': last_row['rsi'],
            'atr': last_row['atr'],
            'vol_ratio': last_row['vol_ratio'],
            'body_pct': last_row['body_pct'],
            'is_bullish': last_row['is_bullish'],
            'is_bearish': last_row['is_bearish'],
            'uptrend': last_row['uptrend'],
            'downtrend': last_row['downtrend'],
            'high_vol': last_row['high_vol']
        }
