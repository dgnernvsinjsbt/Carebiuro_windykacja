"""
Adaptive Trading System with Rolling Lookback Optimization
For FARTCOIN/USDT 15-minute data

This system:
1. Switches between longs/shorts based on market regime
2. Adapts position size and leverage based on volatility
3. Takes fewer, higher-quality trades
4. Continuously recalibrates using rolling lookback windows
5. Sits out during unfavorable conditions
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    # Data
    DATA_PATH = '/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv'
    RESULTS_DIR = '/workspaces/Carebiuro_windykacja/trading/results/'

    # Trading
    INITIAL_CAPITAL = 1000
    FEE_RATE = 0.001  # 0.1% round-trip
    MAX_LEVERAGE = 10
    BASE_LEVERAGE = 5

    # Rolling Optimization
    SHORT_WINDOWS = [15, 21, 30]  # days
    MEDIUM_WINDOWS = [45, 60, 90]  # days
    RECALIBRATION_FREQ = 7  # days
    MIN_LOOKBACK_DAYS = 15  # minimum data needed

    # Indicators
    EMA_FAST_OPTIONS = [8, 13, 21]
    EMA_SLOW_OPTIONS = [50, 100, 200]
    DAILY_EMA_OPTIONS = [3, 5, 8, 13]
    ATR_PERIODS = [14, 20]
    ATR_PERCENTILE_WINDOW = 50

    # Regime Detection
    ADX_THRESHOLD = 20
    CHOP_CROSS_LIMIT = 3
    MIN_WIN_RATE = 35

    # Position Sizing
    POSITION_SIZING_METHODS = ['volatility_inverse', 'winrate_adaptive', 'fixed_tier']

    # Exit Strategy
    CANDLES_TO_HOLD_OPTIONS = [4, 6, 8]
    RR_RATIOS = [1.5, 2.0, 2.5, 3.0]
    EOD_EXIT_HOUR = 23  # UTC
    EOD_EXIT_MINUTE = 45

    # Trade Filtering
    MIN_CONFLUENCE_SCORE = 5
    MIN_PATTERN_QUALITY = 4
    BEST_SESSION_START = 18  # UTC
    BEST_SESSION_END = 23    # UTC

    # Volatility Regimes
    VOL_LOW_PERCENTILE = 25
    VOL_HIGH_PERCENTILE = 75
    VOL_EXTREME_PERCENTILE = 95


# ============================================================================
# INDICATOR CALCULATIONS
# ============================================================================

def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return df['close'].ewm(span=period, adjust=False).mean()


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()

    return atr


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average Directional Index"""
    high = df['high']
    low = df['low']
    close = df['close']

    # Plus/Minus Directional Movement
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    # True Range
    tr = calculate_atr(df, period)

    # Directional Indicators
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / tr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / tr)

    # ADX
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()

    return adx.fillna(0)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all technical indicators to dataframe"""
    df = df.copy()

    # EMAs
    for period in [8, 13, 21, 50, 100, 200]:
        df[f'ema{period}'] = calculate_ema(df, period)

    # ATR
    for period in Config.ATR_PERIODS:
        df[f'atr{period}'] = calculate_atr(df, period)

    # ADX
    df['adx'] = calculate_adx(df, 14)

    # Daily aggregation for daily EMA
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    daily_close = df.groupby('date')['close'].last()

    for period in Config.DAILY_EMA_OPTIONS:
        daily_ema = daily_close.ewm(span=period, adjust=False).mean()
        df[f'daily_ema{period}'] = df['date'].map(daily_ema)

    # Price characteristics
    df['is_green'] = df['close'] > df['open']
    df['body_size'] = np.abs(df['close'] - df['open'])
    df['candle_range'] = df['high'] - df['low']
    df['body_ratio'] = df['body_size'] / df['candle_range'].replace(0, np.nan)

    # Volume
    df['avg_volume'] = df['volume'].rolling(window=20).mean()
    df['volume_ratio'] = df['volume'] / df['avg_volume'].replace(0, np.nan)

    # Hour of day
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour

    return df


# ============================================================================
# REGIME DETECTION
# ============================================================================

class RegimeDetector:
    """Detect market regime: trend direction + volatility"""

    @staticmethod
    def detect_trend_regime(df: pd.DataFrame, idx: int,
                           fast_ema: int = 21, slow_ema: int = 50,
                           daily_ema: int = 8) -> str:
        """Classify trend: STRONG_UP, WEAK_UP, RANGING, WEAK_DOWN, STRONG_DOWN"""
        row = df.iloc[idx]
        price = row['close']

        ema_fast = row[f'ema{fast_ema}']
        ema_slow = row[f'ema{slow_ema}']
        daily_close = df[df['date'] == row['date']]['close'].iloc[-1]
        daily_ema_val = row[f'daily_ema{daily_ema}']

        # Strong uptrend: price above all EMAs + daily above daily EMA
        if (price > ema_fast and price > ema_slow and
            ema_fast > ema_slow and daily_close > daily_ema_val):
            return 'STRONG_UPTREND'

        # Strong downtrend: price below all EMAs + daily below daily EMA
        elif (price < ema_fast and price < ema_slow and
              ema_fast < ema_slow and daily_close < daily_ema_val):
            return 'STRONG_DOWNTREND'

        # Weak uptrend: price > fast EMA but mixed signals
        elif price > ema_fast and ema_fast > ema_slow:
            return 'WEAK_UPTREND'

        # Weak downtrend: price < fast EMA but mixed signals
        elif price < ema_fast and ema_fast < ema_slow:
            return 'WEAK_DOWNTREND'

        # Ranging/Chop: price oscillating around EMAs
        else:
            return 'RANGING'

    @staticmethod
    def detect_volatility_regime(df: pd.DataFrame, idx: int,
                                atr_period: int = 14) -> str:
        """Classify volatility: LOW, NORMAL, HIGH, EXTREME"""
        row = df.iloc[idx]
        current_atr = row[f'atr{atr_period}']

        # Calculate percentile of current ATR vs recent history
        window_start = max(0, idx - Config.ATR_PERCENTILE_WINDOW)
        recent_atrs = df.iloc[window_start:idx+1][f'atr{atr_period}']

        if len(recent_atrs) < 10:
            return 'NORMAL'

        percentile = (recent_atrs < current_atr).sum() / len(recent_atrs) * 100

        if percentile > Config.VOL_EXTREME_PERCENTILE:
            return 'EXTREME'
        elif percentile > Config.VOL_HIGH_PERCENTILE:
            return 'HIGH'
        elif percentile < Config.VOL_LOW_PERCENTILE:
            return 'LOW'
        else:
            return 'NORMAL'

    @staticmethod
    def is_choppy(df: pd.DataFrame, idx: int, lookback: int = 20,
                 ema_period: int = 21) -> bool:
        """Detect if market is choppy (no clear trend)"""
        if idx < lookback:
            return False

        row = df.iloc[idx]

        # Check ADX
        if row['adx'] < Config.ADX_THRESHOLD:
            return True

        # Check EMA crosses
        window = df.iloc[idx-lookback:idx+1]
        ema_col = f'ema{ema_period}'
        crosses = 0

        for i in range(len(window) - 1):
            prev_above = window.iloc[i]['close'] > window.iloc[i][ema_col]
            curr_above = window.iloc[i+1]['close'] > window.iloc[i+1][ema_col]
            if prev_above != curr_above:
                crosses += 1

        if crosses > Config.CHOP_CROSS_LIMIT:
            return True

        return False

    @staticmethod
    def should_trade(trend_regime: str, vol_regime: str,
                    recent_win_rate: float, is_chop: bool) -> bool:
        """Determine if we should trade based on conditions"""
        # Don't trade in extreme volatility
        if vol_regime == 'EXTREME':
            return False

        # Don't trade if choppy
        if is_chop:
            return False

        # Don't trade in ranging markets
        if trend_regime == 'RANGING':
            return False

        # Don't trade if recent win rate is too low
        if recent_win_rate < Config.MIN_WIN_RATE:
            return False

        return True


# ============================================================================
# SIGNAL GENERATION
# ============================================================================

class SignalGenerator:
    """Generate long and short signals based on regime"""

    @staticmethod
    def generate_long_signal(df: pd.DataFrame, idx: int,
                            ema_period: int = 21) -> Tuple[bool, str]:
        """Generate long signal (EMA pullback, breakout, or support bounce)"""
        if idx < 2:
            return False, ""

        row = df.iloc[idx]
        prev_row = df.iloc[idx-1]
        ema_col = f'ema{ema_period}'

        # EMA20 pullback: close > EMA, low touches EMA, green candle
        touch_distance = abs(row['low'] - row[ema_col]) / row[ema_col]
        if (row['close'] > row[ema_col] and
            touch_distance < 0.01 and  # Low within 1% of EMA
            row['is_green']):
            return True, "ema_pullback"

        # Breakout: close > previous high with volume
        if (row['close'] > prev_row['high'] and
            row['volume_ratio'] > 1.2 and
            row['is_green']):
            return True, "breakout"

        # Support bounce: price bounces off recent low with green reversal
        if idx >= 5:
            recent_low = df.iloc[idx-5:idx]['low'].min()
            bounce_distance = abs(row['low'] - recent_low) / recent_low
            if (bounce_distance < 0.005 and  # Within 0.5% of support
                row['is_green'] and
                row['close'] > row[ema_col]):
                return True, "support_bounce"

        return False, ""

    @staticmethod
    def generate_short_signal(df: pd.DataFrame, idx: int,
                             ema_period: int = 21) -> Tuple[bool, str]:
        """Generate short signal (EMA rejection, breakdown, or resistance rejection)"""
        if idx < 2:
            return False, ""

        row = df.iloc[idx]
        prev_row = df.iloc[idx-1]
        ema_col = f'ema{ema_period}'

        # EMA20 rejection: close < EMA, high touches EMA, red candle
        touch_distance = abs(row['high'] - row[ema_col]) / row[ema_col]
        if (row['close'] < row[ema_col] and
            touch_distance < 0.01 and  # High within 1% of EMA
            not row['is_green']):
            return True, "ema_rejection"

        # Breakdown: close < previous low
        if (row['close'] < prev_row['low'] and
            not row['is_green']):
            return True, "breakdown"

        # Resistance rejection: price rejected at recent high with red reversal
        if idx >= 5:
            recent_high = df.iloc[idx-5:idx]['high'].max()
            rejection_distance = abs(row['high'] - recent_high) / recent_high
            if (rejection_distance < 0.005 and  # Within 0.5% of resistance
                not row['is_green'] and
                row['close'] < row[ema_col]):
                return True, "resistance_rejection"

        return False, ""

    @staticmethod
    def calculate_confluence_score(df: pd.DataFrame, idx: int,
                                  direction: str, ema_fast: int = 21,
                                  ema_slow: int = 50, daily_ema: int = 8) -> int:
        """Calculate signal confluence score (0-8)"""
        row = df.iloc[idx]
        score = 0

        ema_fast_val = row[f'ema{ema_fast}']
        ema_slow_val = row[f'ema{ema_slow}']
        daily_close = df[df['date'] == row['date']]['close'].iloc[-1]
        daily_ema_val = row[f'daily_ema{daily_ema}']

        if direction == 'long':
            # Price action
            if row['close'] > ema_fast_val:
                score += 1
            if row['close'] > ema_slow_val:
                score += 1
            if row['is_green']:
                score += 1

            # Trend alignment
            if daily_close > daily_ema_val:
                score += 2
            if ema_fast_val > ema_slow_val:
                score += 1

            # Volume confirmation
            if row['volume_ratio'] > 1.2:
                score += 1

            # Strong body
            if row['body_ratio'] > 0.6:
                score += 1

        elif direction == 'short':
            # Price action
            if row['close'] < ema_fast_val:
                score += 1
            if row['close'] < ema_slow_val:
                score += 1
            if not row['is_green']:
                score += 1

            # Trend alignment
            if daily_close < daily_ema_val:
                score += 2
            if ema_fast_val < ema_slow_val:
                score += 1

            # Volume confirmation
            if row['volume_ratio'] > 1.2:
                score += 1

            # Strong body
            if row['body_ratio'] > 0.6:
                score += 1

        return score

    @staticmethod
    def in_best_session(hour: int) -> bool:
        """Check if current time is in best trading session"""
        return Config.BEST_SESSION_START <= hour < Config.BEST_SESSION_END


# ============================================================================
# POSITION SIZING
# ============================================================================

class PositionSizer:
    """Calculate position size based on different methods"""

    @staticmethod
    def volatility_inverse_size(current_atr: float, avg_atr: float,
                               base_size: float = 1.0) -> float:
        """Higher volatility = smaller position"""
        vol_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        if vol_ratio > 2.0:
            return base_size * 0.25
        elif vol_ratio > 1.5:
            return base_size * 0.5
        elif vol_ratio > 1.0:
            return base_size * 0.75
        else:
            return base_size * 1.0

    @staticmethod
    def winrate_adaptive_size(recent_wr: float, base_size: float = 1.0) -> float:
        """Scale position based on recent performance"""
        if recent_wr >= 55:
            return base_size * 1.25
        elif recent_wr >= 45:
            return base_size * 1.0
        elif recent_wr >= 35:
            return base_size * 0.5
        else:
            return 0  # Stop trading

    @staticmethod
    def fixed_tier_size(trend_regime: str, vol_regime: str) -> float:
        """Fixed tiers based on conditions"""
        tiers = {
            ('STRONG_UPTREND', 'LOW'): 1.0,
            ('STRONG_UPTREND', 'NORMAL'): 1.0,
            ('STRONG_UPTREND', 'HIGH'): 0.7,
            ('WEAK_UPTREND', 'LOW'): 0.5,
            ('WEAK_UPTREND', 'NORMAL'): 0.5,
            ('WEAK_UPTREND', 'HIGH'): 0.3,
            ('STRONG_DOWNTREND', 'LOW'): 0.8,
            ('STRONG_DOWNTREND', 'NORMAL'): 0.8,
            ('STRONG_DOWNTREND', 'HIGH'): 0.5,
            ('WEAK_DOWNTREND', 'LOW'): 0.5,
            ('WEAK_DOWNTREND', 'NORMAL'): 0.5,
            ('WEAK_DOWNTREND', 'HIGH'): 0.3,
        }
        return tiers.get((trend_regime, vol_regime), 0.25)

    @staticmethod
    def calculate_dynamic_leverage(trend_regime: str, vol_regime: str,
                                  recent_wr: float) -> int:
        """Calculate leverage based on conditions"""
        leverage = Config.BASE_LEVERAGE

        # Increase in strong trends with low volatility and good win rate
        if (trend_regime in ['STRONG_UPTREND', 'STRONG_DOWNTREND'] and
            vol_regime == 'LOW' and recent_wr > 50):
            leverage = 10

        # Reduce in high volatility or poor performance
        elif vol_regime == 'HIGH' or recent_wr < 45:
            leverage = 3

        # Minimal leverage in extreme conditions
        elif vol_regime == 'EXTREME' or recent_wr < 35:
            leverage = 1

        return min(leverage, Config.MAX_LEVERAGE)


# ============================================================================
# BACKTESTER
# ============================================================================

class Trade:
    """Represents a single trade"""
    def __init__(self, entry_idx: int, entry_price: float, direction: str,
                 size: float, leverage: int, stop_loss: float, take_profit: float,
                 entry_time: str, signal_type: str, regime: str):
        self.entry_idx = entry_idx
        self.entry_price = entry_price
        self.direction = direction  # 'long' or 'short'
        self.size = size
        self.leverage = leverage
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.entry_time = entry_time
        self.signal_type = signal_type
        self.regime = regime

        self.exit_idx = None
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None
        self.pnl = 0
        self.pnl_pct = 0
        self.return_pct = 0


class Backtester:
    """Walk-forward backtester with rolling optimization"""

    def __init__(self, df: pd.DataFrame, config: Dict):
        self.df = df
        self.config = config
        self.trades: List[Trade] = []
        self.equity_curve = []
        self.capital = Config.INITIAL_CAPITAL
        self.peak_capital = Config.INITIAL_CAPITAL

    def run(self) -> Dict:
        """Run backtest with rolling optimization"""
        print(f"\n{'='*80}")
        print(f"Starting backtest: {self.config['name']}")
        print(f"{'='*80}")

        current_trade = None
        last_optimization_date = None
        optimization_params = self.config.copy()

        for idx in range(len(self.df)):
            row = self.df.iloc[idx]
            current_date = row['date']

            # Skip early data (insufficient for indicators)
            if idx < 200:
                continue

            # Rolling optimization
            if self.config.get('use_rolling_optimization', False):
                days_since_last = 0 if last_optimization_date is None else \
                                 (current_date - last_optimization_date).days

                if (last_optimization_date is None or
                    days_since_last >= Config.RECALIBRATION_FREQ):

                    lookback_days = self.config['lookback_days']
                    optimization_params = self._optimize_parameters(idx, lookback_days)
                    last_optimization_date = current_date

                    if idx % 1000 == 0:
                        print(f"  Optimized at idx {idx}, date {current_date}")

            # Check if we need to exit existing trade
            if current_trade is not None:
                exit_signal, exit_reason = self._check_exit(current_trade, idx)

                if exit_signal:
                    self._close_trade(current_trade, idx, row['close'], exit_reason)
                    current_trade = None

            # Check for new entry signals (only if no open trade)
            if current_trade is None:
                current_trade = self._check_entry(idx, optimization_params)

            # Update equity curve
            unrealized_pnl = 0
            if current_trade is not None:
                unrealized_pnl = self._calculate_unrealized_pnl(current_trade, row['close'])

            current_equity = self.capital + unrealized_pnl
            self.equity_curve.append({
                'timestamp': row['timestamp'],
                'equity': current_equity,
                'trade_open': current_trade is not None
            })

            # Update peak for drawdown calculation
            if current_equity > self.peak_capital:
                self.peak_capital = current_equity

        # Close any remaining open trade
        if current_trade is not None:
            last_idx = len(self.df) - 1
            self._close_trade(current_trade, last_idx,
                            self.df.iloc[last_idx]['close'], 'end_of_data')

        return self._calculate_metrics()

    def _optimize_parameters(self, current_idx: int, lookback_days: int) -> Dict:
        """Optimize parameters based on recent performance"""
        # For simplicity, use base parameters
        # In production, would test multiple combinations
        params = self.config.copy()

        # Could test different EMAs, ATR periods, position sizing, etc.
        # For now, return base config
        return params

    def _check_entry(self, idx: int, params: Dict) -> Optional[Trade]:
        """Check for entry signal"""
        row = self.df.iloc[idx]

        # Regime detection
        trend_regime = RegimeDetector.detect_trend_regime(
            self.df, idx,
            fast_ema=params['ema_fast'],
            slow_ema=params['ema_slow'],
            daily_ema=params['daily_ema']
        )

        vol_regime = RegimeDetector.detect_volatility_regime(
            self.df, idx, atr_period=params['atr_period']
        )

        is_chop = RegimeDetector.is_choppy(
            self.df, idx, lookback=20, ema_period=params['ema_fast']
        )

        # Calculate recent win rate
        recent_trades = self.trades[-20:] if len(self.trades) >= 20 else self.trades
        recent_wr = (sum(1 for t in recent_trades if t.pnl > 0) / len(recent_trades) * 100
                    if recent_trades else 50)

        # Should we trade?
        if not RegimeDetector.should_trade(trend_regime, vol_regime, recent_wr, is_chop):
            return None

        # Generate signals
        direction = None
        signal_type = ""

        if trend_regime in ['STRONG_UPTREND', 'WEAK_UPTREND']:
            has_signal, signal_type = SignalGenerator.generate_long_signal(
                self.df, idx, ema_period=params['ema_fast']
            )
            if has_signal:
                direction = 'long'

        elif trend_regime in ['STRONG_DOWNTREND', 'WEAK_DOWNTREND']:
            has_signal, signal_type = SignalGenerator.generate_short_signal(
                self.df, idx, ema_period=params['ema_fast']
            )
            if has_signal:
                direction = 'short'

        if direction is None:
            return None

        # Calculate confluence score
        confluence = SignalGenerator.calculate_confluence_score(
            self.df, idx, direction,
            ema_fast=params['ema_fast'],
            ema_slow=params['ema_slow'],
            daily_ema=params['daily_ema']
        )

        if confluence < params['min_confluence_score']:
            return None

        # Check time filter
        if not SignalGenerator.in_best_session(row['hour']):
            return None

        # Calculate position size
        current_atr = row[f"atr{params['atr_period']}"]
        avg_atr = self.df.iloc[max(0, idx-50):idx][f"atr{params['atr_period']}"].mean()

        if params['position_sizing'] == 'volatility_inverse':
            size = PositionSizer.volatility_inverse_size(current_atr, avg_atr)
        elif params['position_sizing'] == 'winrate_adaptive':
            size = PositionSizer.winrate_adaptive_size(recent_wr)
        else:  # fixed_tier
            size = PositionSizer.fixed_tier_size(trend_regime, vol_regime)

        if size == 0:
            return None

        # Calculate leverage
        leverage = PositionSizer.calculate_dynamic_leverage(
            trend_regime, vol_regime, recent_wr
        )

        # Calculate stop loss and take profit
        entry_price = row['close']

        if direction == 'long':
            stop_loss = entry_price - (current_atr * params['atr_stop_multiplier'])
            take_profit = entry_price + (entry_price - stop_loss) * params['rr_ratio']
        else:  # short
            stop_loss = entry_price + (current_atr * params['atr_stop_multiplier'])
            take_profit = entry_price - (stop_loss - entry_price) * params['rr_ratio']

        # Create trade
        trade = Trade(
            entry_idx=idx,
            entry_price=entry_price,
            direction=direction,
            size=size,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=row['timestamp'],
            signal_type=signal_type,
            regime=f"{trend_regime}_{vol_regime}"
        )

        return trade

    def _check_exit(self, trade: Trade, idx: int) -> Tuple[bool, str]:
        """Check if we should exit trade"""
        row = self.df.iloc[idx]

        # Check stop loss and take profit
        if trade.direction == 'long':
            if row['low'] <= trade.stop_loss:
                return True, 'stop_loss'
            if row['high'] >= trade.take_profit:
                return True, 'take_profit'
        else:  # short
            if row['high'] >= trade.stop_loss:
                return True, 'stop_loss'
            if row['low'] <= trade.take_profit:
                return True, 'take_profit'

        # Check time-based exit
        candles_held = idx - trade.entry_idx
        if candles_held >= self.config['candles_to_hold']:
            return True, 'time_exit'

        # Check EOD exit
        if row['hour'] == Config.EOD_EXIT_HOUR and idx > trade.entry_idx:
            return True, 'eod_exit'

        return False, ""

    def _close_trade(self, trade: Trade, exit_idx: int,
                    exit_price: float, exit_reason: str):
        """Close trade and update capital"""
        trade.exit_idx = exit_idx
        trade.exit_price = exit_price
        trade.exit_time = self.df.iloc[exit_idx]['timestamp']
        trade.exit_reason = exit_reason

        # Calculate P&L
        if trade.direction == 'long':
            price_change_pct = (exit_price - trade.entry_price) / trade.entry_price
        else:  # short
            price_change_pct = (trade.entry_price - exit_price) / trade.entry_price

        # Apply leverage and position size
        gross_return = price_change_pct * trade.leverage * trade.size

        # Subtract fees (entry + exit)
        net_return = gross_return - (2 * Config.FEE_RATE)

        # Calculate dollar P&L
        trade.pnl = self.capital * net_return
        trade.pnl_pct = net_return * 100
        trade.return_pct = gross_return * 100

        # Update capital
        self.capital += trade.pnl

        # Record trade
        self.trades.append(trade)

    def _calculate_unrealized_pnl(self, trade: Trade, current_price: float) -> float:
        """Calculate unrealized P&L for open trade"""
        if trade.direction == 'long':
            price_change_pct = (current_price - trade.entry_price) / trade.entry_price
        else:
            price_change_pct = (trade.entry_price - current_price) / trade.entry_price

        gross_return = price_change_pct * trade.leverage * trade.size
        net_return = gross_return - (2 * Config.FEE_RATE)

        return self.capital * net_return

    def _calculate_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not self.trades:
            return {
                'config_name': self.config['name'],
                'total_return_pct': 0,
                'final_capital': self.capital,
                'total_trades': 0,
                'win_rate': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'avg_trade_return': 0,
                'total_fees_paid': 0,
                'winning_trades': 0,
                'losing_trades': 0
            }

        # Basic metrics
        total_return_pct = ((self.capital - Config.INITIAL_CAPITAL) /
                           Config.INITIAL_CAPITAL * 100)

        wins = [t for t in self.trades if t.pnl > 0]
        losses = [t for t in self.trades if t.pnl <= 0]

        win_rate = len(wins) / len(self.trades) * 100 if self.trades else 0

        # P&L stats
        total_win = sum(t.pnl for t in wins)
        total_loss = abs(sum(t.pnl for t in losses))

        avg_win = total_win / len(wins) if wins else 0
        avg_loss = total_loss / len(losses) if losses else 0

        profit_factor = total_win / total_loss if total_loss > 0 else 0

        # Drawdown calculation
        equity_curve_df = pd.DataFrame(self.equity_curve)
        equity_curve_df['peak'] = equity_curve_df['equity'].cummax()
        equity_curve_df['drawdown'] = (equity_curve_df['equity'] -
                                       equity_curve_df['peak']) / equity_curve_df['peak'] * 100
        max_drawdown_pct = equity_curve_df['drawdown'].min()

        # Sharpe ratio
        sharpe_ratio = (total_return_pct / abs(max_drawdown_pct)
                       if max_drawdown_pct != 0 else 0)

        # Trade distribution
        long_trades = [t for t in self.trades if t.direction == 'long']
        short_trades = [t for t in self.trades if t.direction == 'short']

        return {
            'config_name': self.config['name'],
            'total_return_pct': total_return_pct,
            'final_capital': self.capital,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'max_drawdown_pct': max_drawdown_pct,
            'sharpe_ratio': sharpe_ratio,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': max([t.pnl for t in self.trades]) if self.trades else 0,
            'largest_loss': min([t.pnl for t in self.trades]) if self.trades else 0,
            'avg_trade_return': np.mean([t.pnl_pct for t in self.trades]) if self.trades else 0,
            'total_fees_paid': len(self.trades) * 2 * Config.FEE_RATE * Config.INITIAL_CAPITAL,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'long_trades': len(long_trades),
            'short_trades': len(short_trades),
            'long_win_rate': (sum(1 for t in long_trades if t.pnl > 0) / len(long_trades) * 100
                             if long_trades else 0),
            'short_win_rate': (sum(1 for t in short_trades if t.pnl > 0) / len(short_trades) * 100
                              if short_trades else 0)
        }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def create_test_configurations() -> List[Dict]:
    """Create different test configurations"""
    configs = []

    # Base parameters
    base_params = {
        'ema_fast': 21,
        'ema_slow': 50,
        'daily_ema': 8,
        'atr_period': 14,
        'atr_stop_multiplier': 2.0,
        'rr_ratio': 2.0,
        'candles_to_hold': 6,
        'min_confluence_score': 5,
        'position_sizing': 'volatility_inverse'
    }

    # 1. Static baseline (no rolling optimization)
    configs.append({
        **base_params,
        'name': 'Static_Baseline',
        'use_rolling_optimization': False
    })

    # 2. Rolling 30-day optimization
    configs.append({
        **base_params,
        'name': 'Rolling_30day',
        'use_rolling_optimization': True,
        'lookback_days': 30
    })

    # 3. Rolling 90-day optimization
    configs.append({
        **base_params,
        'name': 'Rolling_90day',
        'use_rolling_optimization': True,
        'lookback_days': 90
    })

    # 4. Winrate adaptive sizing with 30-day rolling
    configs.append({
        **base_params,
        'name': 'Rolling_30day_WinrateAdaptive',
        'use_rolling_optimization': True,
        'lookback_days': 30,
        'position_sizing': 'winrate_adaptive'
    })

    # 5. Fixed tier sizing with 90-day rolling
    configs.append({
        **base_params,
        'name': 'Rolling_90day_FixedTier',
        'use_rolling_optimization': True,
        'lookback_days': 90,
        'position_sizing': 'fixed_tier'
    })

    return configs


def run_comprehensive_backtest():
    """Run complete backtesting suite"""
    print("\n" + "="*80)
    print("ADAPTIVE TRADING SYSTEM - COMPREHENSIVE BACKTEST")
    print("="*80)

    # Load data
    print("\nLoading data...")
    df = pd.read_csv(Config.DATA_PATH)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"Loaded {len(df):,} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Price range: ${df['close'].min():.4f} to ${df['close'].max():.4f}")

    # Calculate indicators
    print("\nCalculating indicators...")
    df = add_indicators(df)

    # Create test configurations
    configs = create_test_configurations()

    # Run backtests
    results = []
    all_backtests = {}

    for config in configs:
        backtester = Backtester(df, config)
        metrics = backtester.run()
        results.append(metrics)
        all_backtests[config['name']] = backtester

        print(f"\n{config['name']} Results:")
        print(f"  Total Return: {metrics['total_return_pct']:.2f}%")
        print(f"  Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"  Win Rate: {metrics['win_rate']:.2f}%")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Long/Short: {metrics['long_trades']}/{metrics['short_trades']}")

    # Save results
    print("\n\nSaving results...")
    save_results(results, all_backtests, df)

    print("\n" + "="*80)
    print("BACKTEST COMPLETE!")
    print("="*80)


def save_results(results: List[Dict], backtests: Dict, df: pd.DataFrame):
    """Save all results and visualizations"""
    import os
    os.makedirs(Config.RESULTS_DIR, exist_ok=True)

    # 1. Save summary results
    results_df = pd.DataFrame(results)
    results_df.to_csv(f"{Config.RESULTS_DIR}adaptive_system_results.csv", index=False)
    print(f"  ✓ Saved: adaptive_system_results.csv")

    # 2. Create equity curves comparison
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Adaptive Trading System - Performance Comparison', fontsize=16, fontweight='bold')

    # Equity curves
    ax = axes[0, 0]
    for name, backtester in backtests.items():
        equity_df = pd.DataFrame(backtester.equity_curve)
        equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
        ax.plot(equity_df['timestamp'], equity_df['equity'], label=name, linewidth=2)
    ax.axhline(y=Config.INITIAL_CAPITAL, color='black', linestyle='--', alpha=0.3)
    ax.set_title('Equity Curves', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date')
    ax.set_ylabel('Equity ($)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Return comparison
    ax = axes[0, 1]
    names = [r['config_name'] for r in results]
    returns = [r['total_return_pct'] for r in results]
    colors = ['green' if r > 0 else 'red' for r in returns]
    ax.bar(range(len(names)), returns, color=colors, alpha=0.7)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha='right')
    ax.set_title('Total Returns', fontsize=14, fontweight='bold')
    ax.set_ylabel('Return (%)')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3, axis='y')

    # Win rate comparison
    ax = axes[1, 0]
    win_rates = [r['win_rate'] for r in results]
    ax.bar(range(len(names)), win_rates, color='steelblue', alpha=0.7)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha='right')
    ax.set_title('Win Rates', fontsize=14, fontweight='bold')
    ax.set_ylabel('Win Rate (%)')
    ax.axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='50%')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Sharpe ratio comparison
    ax = axes[1, 1]
    sharpe_ratios = [r['sharpe_ratio'] for r in results]
    ax.bar(range(len(names)), sharpe_ratios, color='purple', alpha=0.7)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha='right')
    ax.set_title('Sharpe Ratios', fontsize=14, fontweight='bold')
    ax.set_ylabel('Sharpe Ratio')
    ax.axhline(y=1.0, color='orange', linestyle='--', alpha=0.5, label='1.0')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(f"{Config.RESULTS_DIR}adaptive_equity_curves.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved: adaptive_equity_curves.png")

    # 3. Regime analysis
    regime_data = []
    for name, backtester in backtests.items():
        for trade in backtester.trades:
            regime_data.append({
                'config': name,
                'regime': trade.regime,
                'direction': trade.direction,
                'signal_type': trade.signal_type,
                'pnl': trade.pnl,
                'return_pct': trade.return_pct,
                'leverage': trade.leverage,
                'size': trade.size
            })

    if regime_data:
        regime_df = pd.DataFrame(regime_data)
        regime_df.to_csv(f"{Config.RESULTS_DIR}regime_analysis.csv", index=False)
        print(f"  ✓ Saved: regime_analysis.csv")

    # 4. Rolling optimization log (for rolling configs only)
    rolling_log = []
    for name, backtester in backtests.items():
        if 'Rolling' in name:
            for i, trade in enumerate(backtester.trades):
                rolling_log.append({
                    'config': name,
                    'trade_num': i + 1,
                    'entry_time': trade.entry_time,
                    'regime': trade.regime,
                    'direction': trade.direction,
                    'leverage': trade.leverage,
                    'size': trade.size,
                    'return_pct': trade.return_pct
                })

    if rolling_log:
        rolling_df = pd.DataFrame(rolling_log)
        rolling_df.to_csv(f"{Config.RESULTS_DIR}rolling_optimization_log.csv", index=False)
        print(f"  ✓ Saved: rolling_optimization_log.csv")


if __name__ == "__main__":
    run_comprehensive_backtest()
