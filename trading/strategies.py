"""
Trading Strategy Implementations for FARTCOIN/USDT Backtesting

Each strategy returns entry signals and stop loss levels as DataFrames.
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators needed for strategies"""
    data = df.copy()

    # Simple Moving Averages
    for period in [5, 10, 20, 50]:
        data[f'sma_{period}'] = data['close'].rolling(window=period).mean()

    # Exponential Moving Averages
    for period in [5, 10, 20, 50]:
        data[f'ema_{period}'] = data['close'].ewm(span=period, adjust=False).mean()

    # RSI calculations
    for period in [7, 14, 21]:
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        data[f'rsi_{period}'] = 100 - (100 / (1 + rs))

    # ATR for stop loss calculations
    data['tr'] = np.maximum(
        data['high'] - data['low'],
        np.maximum(
            abs(data['high'] - data['close'].shift(1)),
            abs(data['low'] - data['close'].shift(1))
        )
    )
    data['atr_14'] = data['tr'].rolling(window=14).mean()

    # Period highs/lows - include more periods for flexibility
    for period in [2, 4, 6, 8, 12, 20]:
        data[f'high_{period}'] = data['high'].rolling(window=period).max()
        data[f'low_{period}'] = data['low'].rolling(window=period).min()

    # Candle characteristics
    data['candle_size'] = abs(data['close'] - data['open'])
    data['is_green'] = (data['close'] > data['open']).astype(int)
    data['prev_green'] = data['is_green'].shift(1)
    data['consecutive_greens'] = data['is_green'].groupby(
        (data['is_green'] != data['is_green'].shift()).cumsum()
    ).cumsum()

    return data


# ===== STRATEGY 1: GREEN CANDLE ENTRY =====

def green_candle_entry(data: pd.DataFrame, min_size: float = 0.0,
                       consecutive: int = 1) -> pd.DataFrame:
    """
    Enter long on green candle close
    Stop loss below that candle's low

    Args:
        min_size: Minimum candle size as % of price
        consecutive: Number of consecutive green candles required
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    # Basic green candle signal
    is_green = data['close'] > data['open']
    size_ok = data['candle_size'] >= (data['close'] * min_size)

    if consecutive > 1:
        consec_ok = data['consecutive_greens'] >= consecutive
        entry_signal = is_green & size_ok & consec_ok
    else:
        entry_signal = is_green & size_ok

    signals.loc[entry_signal, 'entry'] = 1
    signals.loc[entry_signal, 'stop_loss'] = data.loc[entry_signal, 'low']

    return signals


# ===== STRATEGY 2: MOVING AVERAGE CROSSOVER =====

def ma_crossover(data: pd.DataFrame, ma_type: str = 'sma',
                 period: int = 20) -> pd.DataFrame:
    """
    Price crosses above moving average
    Stop loss 2 ATR below entry or recent swing low
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    ma_col = f'{ma_type}_{period}'

    # Price crosses above MA
    above_ma = data['close'] > data[ma_col]
    was_below = data['close'].shift(1) <= data[ma_col].shift(1)
    crossover = above_ma & was_below

    signals.loc[crossover, 'entry'] = 1

    # Stop loss: 2 ATR below entry or low of previous N candles
    lookback = min(period//2, 8)
    if f'low_{lookback}' in data.columns:
        stop_distance = data['atr_14'] * 2
        swing_low = data[f'low_{lookback}']
        signals.loc[crossover, 'stop_loss'] = np.minimum(
            data.loc[crossover, 'close'] - stop_distance,
            swing_low
        )
    else:
        # Fallback to 2 ATR
        stop_distance = data['atr_14'] * 2
        signals.loc[crossover, 'stop_loss'] = data.loc[crossover, 'close'] - stop_distance

    return signals


def dual_ma_crossover(data: pd.DataFrame, fast: int = 5,
                      slow: int = 20, ma_type: str = 'ema') -> pd.DataFrame:
    """
    Fast MA crosses above slow MA
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    fast_col = f'{ma_type}_{fast}'
    slow_col = f'{ma_type}_{slow}'

    # Fast crosses above slow
    fast_above = data[fast_col] > data[slow_col]
    was_below = data[fast_col].shift(1) <= data[slow_col].shift(1)
    crossover = fast_above & was_below

    signals.loc[crossover, 'entry'] = 1

    # Stop below slow MA or 2 ATR
    stop_distance = data['atr_14'] * 2
    signals.loc[crossover, 'stop_loss'] = np.minimum(
        data.loc[crossover, slow_col],
        data.loc[crossover, 'close'] - stop_distance
    )

    return signals


def ma_pullback(data: pd.DataFrame, period: int = 20,
                ma_type: str = 'ema') -> pd.DataFrame:
    """
    Price pulls back to MA then continues up
    Entry when price bounces off MA
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    ma_col = f'{ma_type}_{period}'

    # Price was above MA
    above_ma = data['close'].shift(1) > data[ma_col].shift(1)

    # Price touched or went below MA
    touched_ma = (data['low'] <= data[ma_col] * 1.002)  # 0.2% tolerance

    # Price now closes above MA again
    closes_above = data['close'] > data[ma_col]

    entry_signal = above_ma & touched_ma & closes_above

    signals.loc[entry_signal, 'entry'] = 1
    signals.loc[entry_signal, 'stop_loss'] = data.loc[entry_signal, 'low']

    return signals


# ===== STRATEGY 3: RSI STRATEGIES =====

def rsi_oversold_bounce(data: pd.DataFrame, period: int = 14,
                        threshold: int = 30) -> pd.DataFrame:
    """
    RSI was oversold, now crosses back above threshold
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    rsi_col = f'rsi_{period}'

    # RSI was below threshold
    was_oversold = data[rsi_col].shift(1) < threshold

    # RSI now above threshold
    crosses_above = data[rsi_col] > threshold

    entry_signal = was_oversold & crosses_above

    signals.loc[entry_signal, 'entry'] = 1

    # Stop below recent low
    signals.loc[entry_signal, 'stop_loss'] = data.loc[entry_signal, f'low_4']

    return signals


def rsi_momentum(data: pd.DataFrame, period: int = 14,
                 threshold: int = 50) -> pd.DataFrame:
    """
    RSI crosses above 50 (momentum)
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    rsi_col = f'rsi_{period}'

    # RSI crosses above threshold
    was_below = data[rsi_col].shift(1) <= threshold
    crosses_above = data[rsi_col] > threshold

    entry_signal = was_below & crosses_above

    signals.loc[entry_signal, 'entry'] = 1
    signals.loc[entry_signal, 'stop_loss'] = data.loc[entry_signal, 'close'] - data.loc[entry_signal, 'atr_14'] * 2

    return signals


# ===== STRATEGY 4: BREAKOUT STRATEGIES =====

def previous_candle_breakout(data: pd.DataFrame) -> pd.DataFrame:
    """
    Break above previous candle high
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    # Current close above previous high
    prev_high = data['high'].shift(1)
    breakout = data['close'] > prev_high

    signals.loc[breakout, 'entry'] = 1
    signals.loc[breakout, 'stop_loss'] = data.loc[breakout, 'low']

    return signals


def period_high_breakout(data: pd.DataFrame, period: int = 8) -> pd.DataFrame:
    """
    Break above N-period high
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    high_col = f'high_{period}'

    # Current close above period high
    period_high = data[high_col].shift(1)
    breakout = data['close'] > period_high

    signals.loc[breakout, 'entry'] = 1

    # Stop below period low
    signals.loc[breakout, 'stop_loss'] = data.loc[breakout, f'low_{period//2}']

    return signals


def session_open_breakout(data: pd.DataFrame) -> pd.DataFrame:
    """
    Break above session (day) open price
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    # Get daily open (first candle of each day)
    data['date'] = pd.to_datetime(data['timestamp']).dt.date
    daily_open = data.groupby('date')['open'].transform('first')

    # Break above daily open
    was_below = data['close'].shift(1) <= daily_open.shift(1)
    breaks_above = data['close'] > daily_open

    entry_signal = was_below & breaks_above

    signals.loc[entry_signal, 'entry'] = 1
    signals.loc[entry_signal, 'stop_loss'] = data.loc[entry_signal, 'low']

    return signals


# ===== STRATEGY 5: COMBINED/HYBRID =====

def green_above_ma(data: pd.DataFrame, period: int = 20,
                   ma_type: str = 'ema') -> pd.DataFrame:
    """
    Green candle + price above MA
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    ma_col = f'{ma_type}_{period}'

    is_green = data['close'] > data['open']
    above_ma = data['close'] > data[ma_col]

    entry_signal = is_green & above_ma

    signals.loc[entry_signal, 'entry'] = 1
    signals.loc[entry_signal, 'stop_loss'] = data.loc[entry_signal, 'low']

    return signals


def rsi_above_ma(data: pd.DataFrame, rsi_period: int = 14,
                 rsi_threshold: int = 30, ma_period: int = 20) -> pd.DataFrame:
    """
    RSI oversold bounce + price above MA
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    rsi_col = f'rsi_{rsi_period}'
    ma_col = f'ema_{ma_period}'

    # RSI bounce
    was_oversold = data[rsi_col].shift(1) < rsi_threshold
    crosses_above = data[rsi_col] >= rsi_threshold

    # Above MA
    above_ma = data['close'] > data[ma_col]

    entry_signal = was_oversold & crosses_above & above_ma

    signals.loc[entry_signal, 'entry'] = 1
    signals.loc[entry_signal, 'stop_loss'] = data.loc[entry_signal, 'low']

    return signals


def breakout_above_ma(data: pd.DataFrame, period: int = 8,
                      ma_period: int = 20) -> pd.DataFrame:
    """
    Period high breakout + price above MA
    """
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    high_col = f'high_{period}'
    ma_col = f'ema_{ma_period}'

    # Breakout
    period_high = data[high_col].shift(1)
    breakout = data['close'] > period_high

    # Above MA
    above_ma = data['close'] > data[ma_col]

    entry_signal = breakout & above_ma

    signals.loc[entry_signal, 'entry'] = 1
    signals.loc[entry_signal, 'stop_loss'] = data.loc[entry_signal, f'low_{period//2}']

    return signals


# ===== EXIT METHODS =====

def fixed_rr_exit(entry_price: float, stop_loss: float,
                  rr_ratio: float) -> float:
    """
    Calculate fixed risk-reward target
    """
    risk = entry_price - stop_loss
    target = entry_price + (risk * rr_ratio)
    return target


def trailing_stop_atr(current_price: float, highest_since_entry: float,
                      atr: float, multiplier: float = 2.0) -> float:
    """
    ATR-based trailing stop
    """
    return highest_since_entry - (atr * multiplier)


def trailing_stop_candle(current_low: float, lookback_lows: List[float],
                         periods: int = 2) -> float:
    """
    Trail stop below recent candle lows
    """
    return min(lookback_lows[-periods:]) if len(lookback_lows) >= periods else current_low


# ===== STRATEGY REGISTRY =====

STRATEGIES = {
    # Green Candle Variations
    'green_candle_basic': lambda df: green_candle_entry(df, min_size=0.0, consecutive=1),
    'green_candle_min_size': lambda df: green_candle_entry(df, min_size=0.001, consecutive=1),
    'green_candle_2_consec': lambda df: green_candle_entry(df, min_size=0.0, consecutive=2),

    # MA Crossover Variations
    'price_cross_sma20': lambda df: ma_crossover(df, ma_type='sma', period=20),
    'price_cross_ema20': lambda df: ma_crossover(df, ma_type='ema', period=20),
    'price_cross_ema10': lambda df: ma_crossover(df, ma_type='ema', period=10),
    'price_cross_ema50': lambda df: ma_crossover(df, ma_type='ema', period=50),

    # Dual MA
    'ema_5_20_cross': lambda df: dual_ma_crossover(df, fast=5, slow=20, ma_type='ema'),
    'ema_10_50_cross': lambda df: dual_ma_crossover(df, fast=10, slow=50, ma_type='ema'),

    # MA Pullback
    'ema20_pullback': lambda df: ma_pullback(df, period=20, ma_type='ema'),
    'ema50_pullback': lambda df: ma_pullback(df, period=50, ma_type='ema'),

    # RSI Strategies
    'rsi14_oversold_30': lambda df: rsi_oversold_bounce(df, period=14, threshold=30),
    'rsi14_oversold_35': lambda df: rsi_oversold_bounce(df, period=14, threshold=35),
    'rsi14_momentum_50': lambda df: rsi_momentum(df, period=14, threshold=50),
    'rsi7_momentum_50': lambda df: rsi_momentum(df, period=7, threshold=50),

    # Breakout Strategies
    'prev_candle_breakout': lambda df: previous_candle_breakout(df),
    'period_4_breakout': lambda df: period_high_breakout(df, period=4),
    'period_8_breakout': lambda df: period_high_breakout(df, period=8),
    'period_12_breakout': lambda df: period_high_breakout(df, period=12),
    'session_open_breakout': lambda df: session_open_breakout(df),

    # Hybrid Strategies
    'green_above_ema20': lambda df: green_above_ma(df, period=20, ma_type='ema'),
    'green_above_sma20': lambda df: green_above_ma(df, period=20, ma_type='sma'),
    'rsi_oversold_above_ema20': lambda df: rsi_above_ma(df, rsi_period=14, rsi_threshold=30, ma_period=20),
    'breakout_8_above_ema20': lambda df: breakout_above_ma(df, period=8, ma_period=20),
}


# Exit configurations to test for each strategy
EXIT_CONFIGS = {
    'rr_1.0': {'type': 'fixed_rr', 'ratio': 1.0},
    'rr_1.5': {'type': 'fixed_rr', 'ratio': 1.5},
    'rr_2.0': {'type': 'fixed_rr', 'ratio': 2.0},
    'rr_3.0': {'type': 'fixed_rr', 'ratio': 3.0},
    'trail_atr_2x': {'type': 'trail_atr', 'multiplier': 2.0},
    'trail_atr_1.5x': {'type': 'trail_atr', 'multiplier': 1.5},
    'time_4_candles': {'type': 'time_based', 'candles': 4},
    'time_8_candles': {'type': 'time_based', 'candles': 8},
    'tp_5pct': {'type': 'fixed_pct', 'target_pct': 0.05},
    'tp_10pct': {'type': 'fixed_pct', 'target_pct': 0.10},
    'tp_15pct': {'type': 'fixed_pct', 'target_pct': 0.15},
}
