"""
SHORT-ONLY Backtest Engine with Fees and Leverage
For downtrending memecoins (MELANIA, PI)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Fee structure
TAKER_FEE = 0.0005  # 0.05% per side
ROUND_TRIP_FEE = TAKER_FEE * 2  # 0.10% total

# Short strategies - inverse of long strategies
SHORT_STRATEGIES = [
    # Red candle strategies (inverse of green candle)
    'red_candle_basic',
    'red_candle_min_size',
    'red_candle_2_consec',

    # Breakdown strategies (inverse of breakout)
    'prev_candle_breakdown',
    'period_8_breakdown',
    'period_12_breakdown',

    # Price cross below MA (inverse of cross above)
    'price_cross_below_ema20',
    'price_cross_below_ema50',

    # EMA pullback to short (price bounces up to EMA then rejects)
    'ema20_rejection',
    'ema50_rejection',

    # Red below EMAs
    'red_below_ema20',
    'red_below_ema50',

    # MA crossover bearish
    'ema_5_20_cross_down',
    'ema_10_50_cross_down',

    # RSI overbought (good for shorting)
    'rsi7_overbought_70',
    'rsi14_overbought_70',
    'rsi14_overbought_65',

    # RSI momentum down
    'rsi7_momentum_below_50',
    'rsi14_momentum_below_50',

    # Combined: breakdown below EMA
    'breakdown_8_below_ema20',
]

EXIT_CONFIGS = {
    'fixed_rr_1.0': {'type': 'fixed_rr', 'ratio': 1.0},
    'fixed_rr_1.5': {'type': 'fixed_rr', 'ratio': 1.5},
    'fixed_rr_2.0': {'type': 'fixed_rr', 'ratio': 2.0},
    'fixed_rr_3.0': {'type': 'fixed_rr', 'ratio': 3.0},
    'time_based_4': {'type': 'time', 'candles': 4},
    'time_based_8': {'type': 'time', 'candles': 8},
}


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators"""
    df = df.copy()

    # EMAs
    for period in [5, 10, 20, 50]:
        df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()

    # SMAs
    for period in [20, 50]:
        df[f'sma{period}'] = df['close'].rolling(window=period).mean()

    # RSI
    for period in [7, 14, 21]:
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        df[f'rsi{period}'] = 100 - (100 / (1 + rs))

    # ATR
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr14'] = tr.rolling(window=14).mean()

    # Previous candle data
    df['prev_high'] = df['high'].shift(1)
    df['prev_low'] = df['low'].shift(1)
    df['prev_close'] = df['close'].shift(1)
    df['prev_open'] = df['open'].shift(1)

    # Period highs and lows
    for period in [4, 8, 12]:
        df[f'high_{period}'] = df['high'].rolling(window=period).max()
        df[f'low_{period}'] = df['low'].rolling(window=period).min()

    # Candle properties
    df['is_red'] = df['close'] < df['open']
    df['is_green'] = df['close'] > df['open']
    df['body_size'] = abs(df['close'] - df['open'])
    df['avg_body'] = df['body_size'].rolling(window=20).mean()

    # EMA crossovers
    df['ema5_above_ema20'] = df['ema5'] > df['ema20']
    df['ema10_above_ema50'] = df['ema10'] > df['ema50']

    return df


def generate_short_signals(df: pd.DataFrame, strategy: str) -> pd.DataFrame:
    """Generate SHORT entry signals based on strategy"""
    df = df.copy()
    df['signal'] = 0
    df['stop_price'] = np.nan  # Stop loss ABOVE entry for shorts

    if strategy == 'red_candle_basic':
        df.loc[df['is_red'], 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.001

    elif strategy == 'red_candle_min_size':
        df.loc[(df['is_red']) & (df['body_size'] > df['avg_body'] * 0.5), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.001

    elif strategy == 'red_candle_2_consec':
        df['prev_red'] = df['is_red'].shift(1)
        df.loc[(df['is_red']) & (df['prev_red']), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df[['high', 'high']].shift(1).max(axis=1) * 1.001

    elif strategy == 'prev_candle_breakdown':
        # Price breaks below previous candle's low
        df.loc[df['close'] < df['prev_low'], 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.001

    elif strategy == 'period_8_breakdown':
        df.loc[df['close'] < df['low_8'].shift(1), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high_8'] + df['high_8'] * 0.001

    elif strategy == 'period_12_breakdown':
        df.loc[df['close'] < df['low_12'].shift(1), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high_12'] + df['high_12'] * 0.001

    elif strategy == 'price_cross_below_ema20':
        df['was_above'] = df['close'].shift(1) > df['ema20'].shift(1)
        df.loc[(df['close'] < df['ema20']) & (df['was_above']), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['ema20'] * 1.01

    elif strategy == 'price_cross_below_ema50':
        df['was_above'] = df['close'].shift(1) > df['ema50'].shift(1)
        df.loc[(df['close'] < df['ema50']) & (df['was_above']), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['ema50'] * 1.01

    elif strategy == 'ema20_rejection':
        # Price pulls up to EMA20 from below and gets rejected (red candle)
        df.loc[(df['close'] < df['ema20']) &
               (df['high'] >= df['ema20'] * 0.995) &
               (df['is_red']), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.001

    elif strategy == 'ema50_rejection':
        df.loc[(df['close'] < df['ema50']) &
               (df['high'] >= df['ema50'] * 0.995) &
               (df['is_red']), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.001

    elif strategy == 'red_below_ema20':
        df.loc[(df['is_red']) & (df['close'] < df['ema20']), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.001

    elif strategy == 'red_below_ema50':
        df.loc[(df['is_red']) & (df['close'] < df['ema50']), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.001

    elif strategy == 'ema_5_20_cross_down':
        df['cross_down'] = (df['ema5'] < df['ema20']) & (df['ema5'].shift(1) >= df['ema20'].shift(1))
        df.loc[df['cross_down'], 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['atr14']

    elif strategy == 'ema_10_50_cross_down':
        df['cross_down'] = (df['ema10'] < df['ema50']) & (df['ema10'].shift(1) >= df['ema50'].shift(1))
        df.loc[df['cross_down'], 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['atr14']

    elif strategy == 'rsi7_overbought_70':
        df.loc[(df['rsi7'] > 70) & (df['rsi7'].shift(1) <= 70), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.01

    elif strategy == 'rsi14_overbought_70':
        df.loc[(df['rsi14'] > 70) & (df['rsi14'].shift(1) <= 70), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.01

    elif strategy == 'rsi14_overbought_65':
        df.loc[(df['rsi14'] > 65) & (df['rsi14'].shift(1) <= 65), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.01

    elif strategy == 'rsi7_momentum_below_50':
        df.loc[(df['rsi7'] < 50) & (df['rsi7'].shift(1) >= 50) & (df['is_red']), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.005

    elif strategy == 'rsi14_momentum_below_50':
        df.loc[(df['rsi14'] < 50) & (df['rsi14'].shift(1) >= 50) & (df['is_red']), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high'] + df['high'] * 0.005

    elif strategy == 'breakdown_8_below_ema20':
        df.loc[(df['close'] < df['low_8'].shift(1)) & (df['close'] < df['ema20']), 'signal'] = 1
        df.loc[df['signal'] == 1, 'stop_price'] = df['high_8'] + df['high_8'] * 0.001

    return df


class ShortBacktestEngine:
    """Backtest engine for SHORT-only strategies with fees and leverage"""

    def __init__(self, data: pd.DataFrame, initial_capital: float = 10000):
        self.raw_data = data.copy()
        self.raw_data['timestamp'] = pd.to_datetime(self.raw_data['timestamp'])
        self.raw_data['date'] = self.raw_data['timestamp'].dt.date
        self.initial_capital = initial_capital
        self.data = calculate_indicators(self.raw_data)

    def run_strategy(self, strategy_name: str, exit_config: Dict,
                     leverage: float = 1.0) -> Dict:
        """Run a single SHORT strategy with leverage and fees"""

        # Generate signals
        data = generate_short_signals(self.data.copy(), strategy_name)

        # Skip warmup period
        data = data.iloc[60:].reset_index(drop=True)

        # Simulate trading
        trades = self._simulate_trading(data, exit_config, leverage)

        # Calculate metrics
        metrics = self._calculate_metrics(trades, leverage)
        metrics['strategy'] = strategy_name
        metrics['exit_method'] = exit_config.get('type', '') + '_' + str(exit_config.get('ratio', exit_config.get('candles', '')))
        metrics['leverage'] = leverage

        return metrics

    def _simulate_trading(self, data: pd.DataFrame, exit_config: Dict,
                          leverage: float) -> List[Dict]:
        """Simulate SHORT trading with daily compounding"""

        capital = self.initial_capital
        trades = []

        in_trade = False
        entry_price = 0
        stop_loss = 0
        take_profit = 0
        entry_idx = 0
        daily_start_capital = capital
        current_date = None

        for i in range(len(data)):
            row = data.iloc[i]

            # Check for new day
            if row['date'] != current_date:
                # Close any open position at day end
                if in_trade and i > 0:
                    exit_price = data.iloc[i-1]['close']
                    # SHORT P&L: profit when price goes DOWN
                    pnl_pct = (entry_price - exit_price) / entry_price
                    pnl_pct_with_fees = pnl_pct - ROUND_TRIP_FEE
                    pnl_pct_leveraged = pnl_pct_with_fees * leverage

                    # Liquidation check
                    if pnl_pct_leveraged < -0.95:
                        pnl_pct_leveraged = -0.95

                    capital *= (1 + pnl_pct_leveraged)
                    trades.append({
                        'entry_idx': entry_idx,
                        'exit_idx': i-1,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl_pct': pnl_pct_leveraged * 100,
                        'pnl_pct_raw': pnl_pct * 100,
                        'exit_reason': 'EOD',
                        'duration': i - 1 - entry_idx
                    })
                    in_trade = False

                current_date = row['date']
                daily_start_capital = capital

            # Check daily drawdown limit (5%)
            if capital < daily_start_capital * 0.95:
                continue

            # Capital depleted
            if capital < 100:
                break

            if not in_trade:
                # Check for SHORT entry signal
                if row['signal'] == 1 and not pd.isna(row['stop_price']):
                    entry_price = row['close']
                    stop_loss = row['stop_price']  # ABOVE entry for shorts
                    risk = stop_loss - entry_price  # Risk is positive (stop is above)

                    if exit_config['type'] == 'fixed_rr':
                        # Take profit BELOW entry for shorts
                        take_profit = entry_price - (risk * exit_config['ratio'])
                    else:
                        take_profit = 0  # Will use time-based exit

                    entry_idx = i
                    in_trade = True
            else:
                # Check exits for SHORT position
                exit_price = None
                exit_reason = None

                # Check stop loss (price goes UP = loss for short)
                if row['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                # Check take profit (price goes DOWN = profit for short)
                elif exit_config['type'] == 'fixed_rr' and row['low'] <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                # Check time-based exit
                elif exit_config['type'] == 'time' and (i - entry_idx) >= exit_config['candles']:
                    exit_price = row['close']
                    exit_reason = 'TIME'

                if exit_price:
                    # SHORT P&L: profit when price goes DOWN
                    pnl_pct = (entry_price - exit_price) / entry_price
                    pnl_pct_with_fees = pnl_pct - ROUND_TRIP_FEE
                    pnl_pct_leveraged = pnl_pct_with_fees * leverage

                    # Liquidation check
                    if pnl_pct_leveraged < -0.95:
                        pnl_pct_leveraged = -0.95

                    capital *= (1 + pnl_pct_leveraged)
                    trades.append({
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl_pct': pnl_pct_leveraged * 100,
                        'pnl_pct_raw': pnl_pct * 100,
                        'exit_reason': exit_reason,
                        'duration': i - entry_idx
                    })
                    in_trade = False

        return trades

    def _calculate_metrics(self, trades: List[Dict], leverage: float) -> Dict:
        """Calculate performance metrics"""

        if not trades:
            return {
                'total_trades': 0,
                'total_return_pct': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'avg_duration': 0,
                'final_capital': self.initial_capital
            }

        trades_df = pd.DataFrame(trades)

        # Calculate cumulative equity
        equity = [self.initial_capital]
        for t in trades:
            equity.append(equity[-1] * (1 + t['pnl_pct'] / 100))

        final_capital = equity[-1]
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100

        # Win rate
        wins = trades_df[trades_df['pnl_pct'] > 0]
        losses = trades_df[trades_df['pnl_pct'] <= 0]
        win_rate = len(wins) / len(trades_df) * 100

        # Profit factor
        gross_profit = wins['pnl_pct'].sum() if len(wins) > 0 else 0
        gross_loss = abs(losses['pnl_pct'].sum()) if len(losses) > 0 else 0.001
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Max drawdown
        equity_arr = np.array(equity)
        peak = np.maximum.accumulate(equity_arr)
        drawdown = (peak - equity_arr) / peak * 100
        max_dd = drawdown.max()

        # Average metrics
        avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0
        avg_duration = trades_df['duration'].mean()

        # Largest win/loss
        largest_win = trades_df['pnl_pct'].max()
        largest_loss = trades_df['pnl_pct'].min()

        return {
            'total_trades': len(trades_df),
            'total_return_pct': round(total_return, 2),
            'win_rate': round(win_rate, 2),
            'profit_factor': round(profit_factor, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'max_drawdown': round(max_dd, 2),
            'avg_duration': round(avg_duration, 1),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2),
            'final_capital': round(final_capital, 2)
        }


def run_full_backtest(csv_path: str, token_name: str):
    """Run full backtest for a token"""

    print(f"\n{'='*80}")
    print(f"SHORT-ONLY BACKTEST: {token_name}")
    print(f"{'='*80}")
    print(f"Fees: 0.05% taker (both sides) = 0.10% round-trip")
    print(f"Initial Capital: $10,000")
    print(f"Strategies: {len(SHORT_STRATEGIES)} x {len(EXIT_CONFIGS)} exits = {len(SHORT_STRATEGIES) * len(EXIT_CONFIGS)} combinations")

    # Load data
    df = pd.read_csv(csv_path)
    print(f"Candles: {len(df)}")

    # Run backtest
    engine = ShortBacktestEngine(df)

    results = []
    leverage_levels = [1, 2, 3, 5]

    for strategy in SHORT_STRATEGIES:
        for exit_name, exit_config in EXIT_CONFIGS.items():
            for leverage in leverage_levels:
                try:
                    metrics = engine.run_strategy(strategy, exit_config, leverage)
                    results.append(metrics)
                except Exception as e:
                    print(f"Error: {strategy} + {exit_name} @ {leverage}x: {e}")

    results_df = pd.DataFrame(results)

    # Save detailed results
    results_df.to_csv(f'/workspaces/Carebiuro_windykacja/trading/results/{token_name.lower()}_short_results.csv', index=False)

    return results_df


def print_top_results(results_df: pd.DataFrame, token_name: str, top_n: int = 15):
    """Print top performing strategies"""

    print(f"\n{'='*100}")
    print(f"TOP {top_n} SHORT STRATEGIES - {token_name}")
    print(f"{'='*100}")

    # Group by leverage
    for lev in [1, 2, 3, 5]:
        lev_df = results_df[results_df['leverage'] == lev].copy()
        lev_df = lev_df.sort_values('total_return_pct', ascending=False).head(top_n)

        print(f"\n--- {lev}x LEVERAGE ---")
        print(f"{'Rank':<5} {'Strategy':<35} {'Exit':<15} {'Return%':<10} {'MaxDD%':<10} {'WinRate%':<10} {'Trades':<8} {'AvgDur':<8}")
        print("-" * 110)

        for idx, (_, row) in enumerate(lev_df.iterrows(), 1):
            print(f"{idx:<5} {row['strategy']:<35} {row['exit_method']:<15} {row['total_return_pct']:>8.1f}% {row['max_drawdown']:>8.1f}% {row['win_rate']:>8.1f}% {row['total_trades']:>6} {row['avg_duration']:>6.1f}")


if __name__ == "__main__":
    import os

    # Create results directory
    os.makedirs('/workspaces/Carebiuro_windykacja/trading/results', exist_ok=True)

    # Run backtest for MELANIA
    melania_results = run_full_backtest(
        '/workspaces/Carebiuro_windykacja/melania_15m_3months.csv',
        'MELANIA'
    )
    print_top_results(melania_results, 'MELANIA')

    # Run backtest for PI
    pi_results = run_full_backtest(
        '/workspaces/Carebiuro_windykacja/pi_15m_3months.csv',
        'PI'
    )
    print_top_results(pi_results, 'PI')

    # Summary comparison
    print(f"\n{'='*100}")
    print("BEST STRATEGIES COMPARISON (All Leverage Levels)")
    print(f"{'='*100}")

    for token, df in [('MELANIA', melania_results), ('PI', pi_results)]:
        best = df.loc[df['total_return_pct'].idxmax()]
        print(f"\n{token} BEST: {best['strategy']} + {best['exit_method']} @ {best['leverage']}x")
        print(f"  Return: {best['total_return_pct']:.1f}% | Max DD: {best['max_drawdown']:.1f}% | Win Rate: {best['win_rate']:.1f}%")
        print(f"  Trades: {best['total_trades']} | Final Capital: ${best['final_capital']:,.0f}")
