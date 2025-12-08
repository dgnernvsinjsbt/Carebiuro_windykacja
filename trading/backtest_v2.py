"""
Comprehensive Backtesting Engine for FARTCOIN/USDT Trading Strategies
Version 2 - Clean implementation with robust error handling

Features:
- Daily compounding
- 5% daily drawdown limit
- Session-based analysis
- Multiple exit methods
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# INDICATORS
# ============================================================================

def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators needed for strategies"""
    data = df.copy()

    # Simple Moving Averages
    for period in [5, 10, 20, 50]:
        data[f'sma_{period}'] = data['close'].rolling(window=period).mean()

    # Exponential Moving Averages
    for period in [5, 10, 20, 50]:
        data[f'ema_{period}'] = data['close'].ewm(span=period, adjust=False).mean()

    # RSI
    for period in [7, 14, 21]:
        delta = data['close'].diff()
        gain = delta.clip(lower=0).rolling(window=period).mean()
        loss = (-delta.clip(upper=0)).rolling(window=period).mean()
        rs = gain / loss
        data[f'rsi_{period}'] = 100 - (100 / (1 + rs))

    # ATR
    high_low = data['high'] - data['low']
    high_close = abs(data['high'] - data['close'].shift(1))
    low_close = abs(data['low'] - data['close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['atr_14'] = tr.rolling(window=14).mean()

    # Period highs/lows
    for period in [4, 8, 12, 20]:
        data[f'high_{period}'] = data['high'].rolling(window=period).max().shift(1)
        data[f'low_{period}'] = data['low'].rolling(window=period).min().shift(1)

    # Candle info
    data['is_green'] = (data['close'] > data['open']).astype(int)
    data['body_pct'] = abs(data['close'] - data['open']) / data['open'] * 100

    # Previous values for crossover detection
    data['prev_close'] = data['close'].shift(1)

    return data


# ============================================================================
# STRATEGY SIGNALS
# ============================================================================

def generate_signals(data: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """Generate entry signals and stop losses for a given strategy"""
    signals = pd.DataFrame(index=data.index)
    signals['entry'] = 0
    signals['stop_loss'] = np.nan

    # Skip first 60 rows to ensure all indicators are calculated
    start_idx = 60

    if strategy == 'green_candle_basic':
        # Enter on any green candle
        mask = (data['is_green'] == 1) & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low'] * 0.999

    elif strategy == 'green_candle_min_size':
        # Enter on green candle with minimum 0.3% body
        mask = (data['is_green'] == 1) & (data['body_pct'] >= 0.3) & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low'] * 0.999

    elif strategy == 'green_candle_2_consec':
        # Enter after 2 consecutive green candles
        prev_green = data['is_green'].shift(1) == 1
        mask = (data['is_green'] == 1) & prev_green & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        # Stop below lower of both candles
        signals.loc[mask, 'stop_loss'] = np.minimum(data.loc[mask, 'low'], data['low'].shift(1).loc[mask]) * 0.999

    elif strategy == 'price_cross_sma20':
        # Price crosses above SMA20
        above = data['close'] > data['sma_20']
        was_below = data['prev_close'] <= data['sma_20'].shift(1)
        mask = above & was_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'close'] - data.loc[mask, 'atr_14'] * 2

    elif strategy == 'price_cross_ema20':
        # Price crosses above EMA20
        above = data['close'] > data['ema_20']
        was_below = data['prev_close'] <= data['ema_20'].shift(1)
        mask = above & was_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'close'] - data.loc[mask, 'atr_14'] * 2

    elif strategy == 'price_cross_ema10':
        # Price crosses above EMA10
        above = data['close'] > data['ema_10']
        was_below = data['prev_close'] <= data['ema_10'].shift(1)
        mask = above & was_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'close'] - data.loc[mask, 'atr_14'] * 2

    elif strategy == 'price_cross_ema50':
        # Price crosses above EMA50
        above = data['close'] > data['ema_50']
        was_below = data['prev_close'] <= data['ema_50'].shift(1)
        mask = above & was_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'close'] - data.loc[mask, 'atr_14'] * 2

    elif strategy == 'ema_5_20_cross':
        # EMA5 crosses above EMA20
        above = data['ema_5'] > data['ema_20']
        was_below = data['ema_5'].shift(1) <= data['ema_20'].shift(1)
        mask = above & was_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'ema_20'] - data.loc[mask, 'atr_14']

    elif strategy == 'ema_10_50_cross':
        # EMA10 crosses above EMA50
        above = data['ema_10'] > data['ema_50']
        was_below = data['ema_10'].shift(1) <= data['ema_50'].shift(1)
        mask = above & was_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'ema_50'] - data.loc[mask, 'atr_14']

    elif strategy == 'ema20_pullback':
        # Price pulls back to EMA20 in uptrend
        above_ma = data['close'] > data['ema_20']
        touched_ma = data['low'] <= data['ema_20'] * 1.005
        green = data['is_green'] == 1
        uptrend = data['ema_20'] > data['ema_20'].shift(5)
        mask = above_ma & touched_ma & green & uptrend & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low'] * 0.998

    elif strategy == 'ema50_pullback':
        # Price pulls back to EMA50 in uptrend
        above_ma = data['close'] > data['ema_50']
        touched_ma = data['low'] <= data['ema_50'] * 1.01
        green = data['is_green'] == 1
        uptrend = data['ema_50'] > data['ema_50'].shift(10)
        mask = above_ma & touched_ma & green & uptrend & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low'] * 0.998

    elif strategy == 'rsi14_oversold_30':
        # RSI crosses above 30
        above = data['rsi_14'] >= 30
        was_below = data['rsi_14'].shift(1) < 30
        mask = above & was_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low_4'] * 0.998

    elif strategy == 'rsi14_oversold_35':
        # RSI crosses above 35
        above = data['rsi_14'] >= 35
        was_below = data['rsi_14'].shift(1) < 35
        mask = above & was_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low_4'] * 0.998

    elif strategy == 'rsi7_oversold_30':
        # RSI7 crosses above 30
        above = data['rsi_7'] >= 30
        was_below = data['rsi_7'].shift(1) < 30
        mask = above & was_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low_4'] * 0.998

    elif strategy == 'rsi14_momentum_50':
        # RSI crosses above 50
        above = data['rsi_14'] >= 50
        was_below = data['rsi_14'].shift(1) < 50
        mask = above & was_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'close'] - data.loc[mask, 'atr_14'] * 2

    elif strategy == 'rsi7_momentum_50':
        # RSI7 crosses above 50
        above = data['rsi_7'] >= 50
        was_below = data['rsi_7'].shift(1) < 50
        mask = above & was_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'close'] - data.loc[mask, 'atr_14'] * 2

    elif strategy == 'prev_candle_breakout':
        # Break above previous candle high
        prev_high = data['high'].shift(1)
        mask = (data['close'] > prev_high) & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low'] * 0.999

    elif strategy == 'period_4_breakout':
        # Break above 4-period high
        mask = (data['close'] > data['high_4']) & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low_4'] * 0.999

    elif strategy == 'period_8_breakout':
        # Break above 8-period high
        mask = (data['close'] > data['high_8']) & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low_8'] * 0.999

    elif strategy == 'period_12_breakout':
        # Break above 12-period high
        mask = (data['close'] > data['high_12']) & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low_12'] * 0.999

    elif strategy == 'session_open_breakout':
        # Break above daily open
        dates = pd.to_datetime(data['timestamp']).dt.date
        daily_open = data.groupby(dates)['open'].transform('first')
        prev_close_below = data['prev_close'] <= daily_open.shift(1)
        mask = (data['close'] > daily_open) & prev_close_below & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low'] * 0.999

    elif strategy == 'green_above_ema20':
        # Green candle above EMA20
        mask = (data['is_green'] == 1) & (data['close'] > data['ema_20']) & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = np.maximum(data.loc[mask, 'low'], data.loc[mask, 'ema_20']) * 0.998

    elif strategy == 'green_above_sma20':
        # Green candle above SMA20
        mask = (data['is_green'] == 1) & (data['close'] > data['sma_20']) & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = np.maximum(data.loc[mask, 'low'], data.loc[mask, 'sma_20']) * 0.998

    elif strategy == 'green_above_ema50':
        # Green candle above EMA50
        mask = (data['is_green'] == 1) & (data['close'] > data['ema_50']) & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = np.maximum(data.loc[mask, 'low'], data.loc[mask, 'ema_50']) * 0.998

    elif strategy == 'rsi_oversold_above_ema20':
        # RSI oversold bounce + above EMA20
        rsi_bounce = (data['rsi_14'] >= 30) & (data['rsi_14'].shift(1) < 30)
        above_ma = data['close'] > data['ema_20']
        mask = rsi_bounce & above_ma & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low'] * 0.998

    elif strategy == 'breakout_8_above_ema20':
        # 8-period breakout + above EMA20
        breakout = data['close'] > data['high_8']
        above_ma = data['close'] > data['ema_20']
        mask = breakout & above_ma & (data.index >= start_idx)
        signals.loc[mask, 'entry'] = 1
        signals.loc[mask, 'stop_loss'] = data.loc[mask, 'low_8'] * 0.998

    # Fill NaN stop losses with ATR-based stop
    nan_stops = signals['stop_loss'].isna() & (signals['entry'] == 1)
    if nan_stops.any():
        signals.loc[nan_stops, 'stop_loss'] = data.loc[nan_stops, 'close'] - data.loc[nan_stops, 'atr_14'] * 2

    return signals


# ============================================================================
# BACKTESTING ENGINE
# ============================================================================

class BacktestEngine:
    """Core backtesting engine with daily compounding and drawdown limits"""

    def __init__(self, data: pd.DataFrame, initial_capital: float = 10000):
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.daily_drawdown_limit = 0.05

        # Prepare data
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        self.data['date'] = self.data['timestamp'].dt.date
        self.data['hour'] = self.data['timestamp'].dt.hour
        self.data = self.data.reset_index(drop=True)

        # Calculate indicators once
        print("Calculating technical indicators...")
        self.data = calculate_all_indicators(self.data)

    def run_strategy(self, strategy_name: str, exit_config: Dict,
                     session_hours: Optional[Tuple[int, int]] = None) -> Dict:
        """Run a single strategy with specified exit method"""

        # Generate signals
        signals = generate_signals(self.data, strategy_name)

        # Merge signals with data
        trade_data = self.data.copy()
        trade_data['entry_signal'] = signals['entry'].values
        trade_data['stop_loss_level'] = signals['stop_loss'].values

        # Filter by session hours
        if session_hours:
            start_hour, end_hour = session_hours
            if start_hour < end_hour:
                session_mask = (trade_data['hour'] >= start_hour) & (trade_data['hour'] < end_hour)
            else:
                session_mask = (trade_data['hour'] >= start_hour) | (trade_data['hour'] < end_hour)
            trade_data.loc[~session_mask, 'entry_signal'] = 0

        # Simulate trading
        trades = self._simulate_trading(trade_data, exit_config)

        # Calculate metrics
        metrics = self._calculate_metrics(trades, strategy_name, exit_config, session_hours)

        return metrics

    def _simulate_trading(self, data: pd.DataFrame, exit_config: Dict) -> List[Dict]:
        """Simulate trading with daily compounding and drawdown limits"""
        capital = self.initial_capital
        trades = []
        position = None

        daily_start_capital = {}
        daily_halted = set()

        for idx in range(len(data)):
            row = data.iloc[idx]
            current_date = row['date']

            # Track daily capital
            if current_date not in daily_start_capital:
                daily_start_capital[current_date] = capital

            # Check if halted
            if current_date in daily_halted:
                # Close position at end of day if needed
                if position and (idx == len(data) - 1 or data.iloc[idx + 1]['date'] != current_date):
                    pnl_pct = (row['close'] - position['entry_price']) / position['entry_price']
                    pnl = pnl_pct * position['capital_used']
                    trades.append({
                        'entry_date': position['entry_date'],
                        'entry_price': position['entry_price'],
                        'exit_price': row['close'],
                        'exit_reason': 'halted_eod',
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'duration': idx - position['entry_idx']
                    })
                    capital += pnl
                    position = None
                continue

            # Check daily drawdown
            daily_return = (capital - daily_start_capital[current_date]) / daily_start_capital[current_date]
            if daily_return <= -self.daily_drawdown_limit:
                daily_halted.add(current_date)
                if position:
                    pnl_pct = (row['close'] - position['entry_price']) / position['entry_price']
                    pnl = pnl_pct * position['capital_used']
                    trades.append({
                        'entry_date': position['entry_date'],
                        'entry_price': position['entry_price'],
                        'exit_price': row['close'],
                        'exit_reason': 'drawdown_limit',
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'duration': idx - position['entry_idx']
                    })
                    capital += pnl
                    position = None
                continue

            # Manage open position
            if position:
                exit_price = None
                exit_reason = None

                # Check stop loss
                if row['low'] <= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'stop_loss'

                # Check exit based on method
                elif exit_config['type'] == 'fixed_rr':
                    if row['high'] >= position['target']:
                        exit_price = position['target']
                        exit_reason = 'target'

                elif exit_config['type'] == 'trail_atr':
                    position['highest'] = max(position['highest'], row['high'])
                    atr = row['atr_14'] if not pd.isna(row['atr_14']) else position['entry_price'] * 0.02
                    trail_stop = position['highest'] - (atr * exit_config['multiplier'])
                    if trail_stop > position['stop_loss']:
                        position['stop_loss'] = trail_stop
                    if row['low'] <= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = 'trailing_stop'

                elif exit_config['type'] == 'time_based':
                    if idx - position['entry_idx'] >= exit_config['candles']:
                        exit_price = row['close']
                        exit_reason = 'time_exit'

                # End of day exit
                if exit_price is None and idx < len(data) - 1:
                    if data.iloc[idx + 1]['date'] != current_date:
                        exit_price = row['close']
                        exit_reason = 'end_of_day'

                # Last candle exit
                if exit_price is None and idx == len(data) - 1:
                    exit_price = row['close']
                    exit_reason = 'end_of_data'

                # Execute exit
                if exit_price:
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                    pnl = pnl_pct * position['capital_used']
                    trades.append({
                        'entry_date': position['entry_date'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'duration': idx - position['entry_idx']
                    })
                    capital += pnl
                    position = None

            # Check for new entry
            if position is None and row['entry_signal'] == 1:
                stop_loss = row['stop_loss_level']
                if pd.isna(stop_loss) or stop_loss >= row['close']:
                    continue

                # Calculate target for fixed RR
                target = None
                if exit_config['type'] == 'fixed_rr':
                    risk = row['close'] - stop_loss
                    target = row['close'] + (risk * exit_config['ratio'])

                position = {
                    'entry_date': current_date,
                    'entry_price': row['close'],
                    'stop_loss': stop_loss,
                    'target': target,
                    'entry_idx': idx,
                    'capital_used': capital,
                    'highest': row['high']
                }

        return trades

    def _calculate_metrics(self, trades: List[Dict], strategy_name: str,
                          exit_config: Dict, session_hours: Optional[Tuple[int, int]]) -> Dict:
        """Calculate performance metrics"""

        exit_str = f"{exit_config['type']}_{exit_config.get('ratio', exit_config.get('multiplier', exit_config.get('candles', '')))}"
        session_str = f"{session_hours[0]}-{session_hours[1]}" if session_hours else "all"

        if len(trades) == 0:
            return {
                'strategy': strategy_name,
                'exit_method': exit_str,
                'session': session_str,
                'total_trades': 0,
                'total_return_pct': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_duration': 0,
                'largest_win': 0,
                'largest_loss': 0
            }

        trades_df = pd.DataFrame(trades)

        # Basic stats
        total_trades = len(trades_df)
        winners = trades_df[trades_df['pnl'] > 0]
        losers = trades_df[trades_df['pnl'] < 0]

        win_rate = len(winners) / total_trades if total_trades > 0 else 0

        gross_profit = winners['pnl'].sum() if len(winners) > 0 else 0
        gross_loss = abs(losers['pnl'].sum()) if len(losers) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999 if gross_profit > 0 else 0)

        # Returns
        cumulative = self.initial_capital + trades_df['pnl'].cumsum()
        final_capital = cumulative.iloc[-1]
        total_return_pct = ((final_capital - self.initial_capital) / self.initial_capital) * 100

        # Drawdown
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = abs(drawdown.min()) * 100

        # Averages
        avg_win = winners['pnl_pct'].mean() * 100 if len(winners) > 0 else 0
        avg_loss = losers['pnl_pct'].mean() * 100 if len(losers) > 0 else 0

        # Sharpe
        if len(trades_df) > 1:
            returns = trades_df['pnl_pct']
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe = 0

        # Other
        avg_duration = trades_df['duration'].mean()
        largest_win = winners['pnl_pct'].max() * 100 if len(winners) > 0 else 0
        largest_loss = losers['pnl_pct'].min() * 100 if len(losers) > 0 else 0

        return {
            'strategy': strategy_name,
            'exit_method': exit_str,
            'session': session_str,
            'total_trades': total_trades,
            'total_return_pct': round(total_return_pct, 2),
            'win_rate': round(win_rate * 100, 2),
            'profit_factor': round(min(profit_factor, 999), 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'max_drawdown': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe, 2),
            'avg_duration': round(avg_duration, 1),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2)
        }

    def get_trades(self, strategy_name: str, exit_config: Dict) -> pd.DataFrame:
        """Get detailed trades for a strategy"""
        signals = generate_signals(self.data, strategy_name)
        trade_data = self.data.copy()
        trade_data['entry_signal'] = signals['entry'].values
        trade_data['stop_loss_level'] = signals['stop_loss'].values
        trades = self._simulate_trading(trade_data, exit_config)
        return pd.DataFrame(trades)


# ============================================================================
# STRATEGY AND EXIT CONFIGURATIONS
# ============================================================================

STRATEGIES = [
    # Green Candle
    'green_candle_basic',
    'green_candle_min_size',
    'green_candle_2_consec',

    # MA Cross
    'price_cross_sma20',
    'price_cross_ema20',
    'price_cross_ema10',
    'price_cross_ema50',
    'ema_5_20_cross',
    'ema_10_50_cross',

    # MA Pullback
    'ema20_pullback',
    'ema50_pullback',

    # RSI
    'rsi14_oversold_30',
    'rsi14_oversold_35',
    'rsi7_oversold_30',
    'rsi14_momentum_50',
    'rsi7_momentum_50',

    # Breakout
    'prev_candle_breakout',
    'period_4_breakout',
    'period_8_breakout',
    'period_12_breakout',
    'session_open_breakout',

    # Hybrid
    'green_above_ema20',
    'green_above_sma20',
    'green_above_ema50',
    'rsi_oversold_above_ema20',
    'breakout_8_above_ema20',
]

EXIT_CONFIGS = {
    'rr_1.0': {'type': 'fixed_rr', 'ratio': 1.0},
    'rr_1.5': {'type': 'fixed_rr', 'ratio': 1.5},
    'rr_2.0': {'type': 'fixed_rr', 'ratio': 2.0},
    'rr_3.0': {'type': 'fixed_rr', 'ratio': 3.0},
    'trail_atr_2.0': {'type': 'trail_atr', 'multiplier': 2.0},
    'trail_atr_1.5': {'type': 'trail_atr', 'multiplier': 1.5},
    'time_4': {'type': 'time_based', 'candles': 4},
    'time_8': {'type': 'time_based', 'candles': 8},
}


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_comprehensive_backtest(data_path: str, output_dir: str):
    """Run comprehensive backtest on all strategies"""
    print("=" * 80)
    print("FARTCOIN/USDT COMPREHENSIVE STRATEGY BACKTEST v2")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    data = pd.read_csv(data_path)
    print(f"Loaded {len(data)} candles from {data['timestamp'].iloc[0]} to {data['timestamp'].iloc[-1]}")

    # Initialize engine
    engine = BacktestEngine(data)

    # Test all combinations
    all_results = []
    total = len(STRATEGIES) * len(EXIT_CONFIGS)

    print(f"\nTesting {len(STRATEGIES)} strategies with {len(EXIT_CONFIGS)} exit methods")
    print(f"Total combinations: {total}")
    print("-" * 80)

    counter = 0
    for strategy in STRATEGIES:
        for exit_name, exit_config in EXIT_CONFIGS.items():
            counter += 1
            print(f"[{counter}/{total}] {strategy} + {exit_name}...", end=' ')

            try:
                metrics = engine.run_strategy(strategy, exit_config)
                all_results.append(metrics)
                print(f"✓ Return: {metrics['total_return_pct']:.1f}%, Trades: {metrics['total_trades']}")
            except Exception as e:
                print(f"✗ Error: {str(e)}")

    # Create results DataFrame
    results_df = pd.DataFrame(all_results)
    results_df = results_df.sort_values('total_return_pct', ascending=False)

    # Save results
    results_df.to_csv(f'{output_dir}/detailed_results.csv', index=False)
    print(f"\n✓ Saved detailed results to {output_dir}/detailed_results.csv")

    # Print top performers
    print("\n" + "=" * 80)
    print("TOP 10 STRATEGIES")
    print("=" * 80)

    for i, (_, row) in enumerate(results_df.head(10).iterrows()):
        print(f"\n#{i+1}: {row['strategy']} + {row['exit_method']}")
        print(f"  Return: {row['total_return_pct']:.2f}% | Win Rate: {row['win_rate']:.1f}% | "
              f"Trades: {row['total_trades']} | PF: {row['profit_factor']:.2f} | MaxDD: {row['max_drawdown']:.1f}%")

    # Generate summary report
    generate_summary(results_df, output_dir, engine)

    # Session analysis for top strategy
    if len(results_df) > 0:
        print("\n" + "=" * 80)
        print("SESSION ANALYSIS FOR TOP STRATEGY")
        print("=" * 80)

        top = results_df.iloc[0]
        exit_config = EXIT_CONFIGS.get(top['exit_method'].replace('fixed_rr_', 'rr_').replace('trail_atr_', 'trail_atr_').replace('time_based_', 'time_'))

        # Find correct exit config
        for name, config in EXIT_CONFIGS.items():
            if name in top['exit_method'] or top['exit_method'].replace('_', '') == name.replace('_', ''):
                exit_config = config
                break

        if exit_config:
            sessions = [
                ('asian', (0, 8)),
                ('european', (8, 16)),
                ('us', (16, 24)),
                ('morning', (6, 12)),
                ('evening', (18, 24)),
            ]

            print(f"\nAnalyzing: {top['strategy']} + {top['exit_method']}")
            for session_name, hours in sessions:
                try:
                    metrics = engine.run_strategy(top['strategy'], exit_config, session_hours=hours)
                    print(f"  {session_name:12s}: {metrics['total_return_pct']:7.2f}% "
                          f"(Trades: {metrics['total_trades']:3d}, WR: {metrics['win_rate']:5.1f}%)")
                except Exception as e:
                    print(f"  {session_name:12s}: Error - {str(e)}")

    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)

    return results_df


def generate_summary(results_df: pd.DataFrame, output_dir: str, engine: BacktestEngine):
    """Generate summary markdown report"""

    report = []
    report.append("# FARTCOIN/USDT Trading Strategy Backtest Results")
    report.append("")
    report.append(f"**Backtest Period**: {engine.data['timestamp'].iloc[0]} to {engine.data['timestamp'].iloc[-1]}")
    report.append(f"**Total Candles**: {len(engine.data)} (15-minute intervals)")
    report.append(f"**Initial Capital**: $10,000")
    report.append(f"**Trading Fees**: 0%")
    report.append(f"**Daily Drawdown Limit**: 5%")
    report.append("")
    report.append("---")
    report.append("")

    # Top 10 table
    report.append("## Strategy Rankings - Top 10")
    report.append("")
    report.append("| Rank | Strategy | Exit | Return % | Trades | Win Rate % | PF | Max DD % | Sharpe |")
    report.append("|------|----------|------|----------|--------|------------|-----|----------|--------|")

    for i, (_, row) in enumerate(results_df.head(10).iterrows()):
        report.append(f"| {i+1} | {row['strategy']} | {row['exit_method']} | "
                     f"{row['total_return_pct']:.1f} | {row['total_trades']} | "
                     f"{row['win_rate']:.1f} | {row['profit_factor']:.2f} | "
                     f"{row['max_drawdown']:.1f} | {row['sharpe_ratio']:.2f} |")

    report.append("")
    report.append("---")
    report.append("")

    # Top 3 detailed
    report.append("## Top 3 Strategies - Detailed Analysis")
    report.append("")

    for i, (_, row) in enumerate(results_df.head(3).iterrows()):
        report.append(f"### #{i+1}: {row['strategy']} + {row['exit_method']}")
        report.append("")
        report.append(f"- **Total Return**: {row['total_return_pct']:.2f}%")
        report.append(f"- **Final Capital**: ${10000 * (1 + row['total_return_pct']/100):,.2f}")
        report.append(f"- **Total Trades**: {row['total_trades']}")
        report.append(f"- **Win Rate**: {row['win_rate']:.2f}%")
        report.append(f"- **Profit Factor**: {row['profit_factor']:.2f}")
        report.append(f"- **Avg Win**: {row['avg_win']:.2f}%")
        report.append(f"- **Avg Loss**: {row['avg_loss']:.2f}%")
        report.append(f"- **Max Drawdown**: {row['max_drawdown']:.2f}%")
        report.append(f"- **Sharpe Ratio**: {row['sharpe_ratio']:.2f}")
        report.append(f"- **Avg Duration**: {row['avg_duration']:.1f} candles ({row['avg_duration'] * 15:.0f} min)")
        report.append(f"- **Largest Win**: {row['largest_win']:.2f}%")
        report.append(f"- **Largest Loss**: {row['largest_loss']:.2f}%")
        report.append("")

    # Recommended strategy
    if len(results_df) > 0:
        best = results_df.iloc[0]
        report.append("---")
        report.append("")
        report.append("## Recommended Strategy")
        report.append("")
        report.append(f"**Strategy**: {best['strategy']}")
        report.append(f"**Exit Method**: {best['exit_method']}")
        report.append("")
        report.append("### Entry Rules")

        if 'green' in best['strategy']:
            if 'above' in best['strategy']:
                report.append("- Enter LONG when green candle closes ABOVE the moving average")
            elif '2_consec' in best['strategy']:
                report.append("- Enter LONG after 2 consecutive green candles")
            elif 'min_size' in best['strategy']:
                report.append("- Enter LONG on green candle with minimum 0.3% body size")
            else:
                report.append("- Enter LONG on any green candle close")
        elif 'cross' in best['strategy']:
            report.append("- Enter LONG when fast indicator crosses above slow indicator")
        elif 'pullback' in best['strategy']:
            report.append("- Enter LONG when price pulls back to MA in an uptrend and bounces")
        elif 'rsi' in best['strategy']:
            if 'oversold' in best['strategy']:
                report.append("- Enter LONG when RSI crosses above oversold level")
            else:
                report.append("- Enter LONG when RSI crosses above 50 (momentum)")
        elif 'breakout' in best['strategy']:
            report.append("- Enter LONG on breakout above recent high")

        report.append("")
        report.append("### Exit Rules")

        if 'rr' in best['exit_method']:
            ratio = best['exit_method'].split('_')[-1]
            report.append(f"- Take profit at {ratio}x risk (Risk:Reward = 1:{ratio})")
        elif 'trail' in best['exit_method']:
            mult = best['exit_method'].split('_')[-1]
            report.append(f"- Trailing stop at {mult}x ATR below highest price")
        elif 'time' in best['exit_method']:
            candles = best['exit_method'].split('_')[-1]
            report.append(f"- Exit after {candles} candles")

        report.append("- Stop loss always enforced")
        report.append("- Close all positions at end of day")
        report.append("")
        report.append("### Risk Management")
        report.append("- Use 100% of capital per trade (long only)")
        report.append("- Stop trading if 5% daily drawdown hit")
        report.append("- No overnight positions")

    with open(f'{output_dir}/summary.md', 'w') as f:
        f.write('\n'.join(report))

    print(f"✓ Saved summary to {output_dir}/summary.md")


if __name__ == '__main__':
    data_path = './fartcoin_15m_3months.csv'
    output_dir = './trading/results'

    results = run_comprehensive_backtest(data_path, output_dir)
