"""
ETH/USDT Session-Based Trading Analysis
Test if time-based filtering improves strategy performance
Goal: >4:1 profit-to-drawdown ratio through session optimization
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Load data
print("Loading ETH/USDT 1m data from LBank...")
df = pd.read_csv('./eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Loaded {len(df):,} candles")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

# Calculate technical indicators
df['hour'] = df['timestamp'].dt.hour
df['range'] = df['high'] - df['low']
df['range_pct'] = (df['range'] / df['close']) * 100

# ATR (14-period)
df['tr'] = np.maximum(df['high'] - df['low'],
                      np.maximum(abs(df['high'] - df['close'].shift(1)),
                                abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

# EMA for trend analysis
df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
df['trend'] = np.where(df['ema20'] > df['ema50'], 1, -1)

# RSI for mean reversion
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

df['rsi'] = calculate_rsi(df['close'])

print("\n" + "="*80)
print("HOURLY PATTERN ANALYSIS")
print("="*80)

# Group by hour
hourly_stats = df.groupby('hour').agg({
    'volume': 'mean',
    'range_pct': 'mean',
    'atr_pct': 'mean',
    'close': 'count'
}).round(4)

hourly_stats.columns = ['avg_volume', 'avg_range_pct', 'avg_atr_pct', 'candle_count']

# Calculate trend strength by hour
trend_by_hour = df.groupby('hour', group_keys=False).apply(
    lambda x: (x['trend'] == 1).sum() / len(x) * 100, include_groups=False
).round(2)
hourly_stats['trend_up_pct'] = trend_by_hour

# Volatility rank
hourly_stats['volatility_rank'] = hourly_stats['avg_atr_pct'].rank(ascending=False).astype(int)

# Reorder columns
hourly_stats = hourly_stats[['candle_count', 'avg_volume', 'avg_atr_pct', 'avg_range_pct', 'trend_up_pct', 'volatility_rank']]

print("\nHourly Statistics (UTC):")
print(hourly_stats.to_string())

# Identify sessions
def get_session(hour):
    if 23 <= hour or hour < 7:
        return 'Asian'
    elif 7 <= hour < 15:
        return 'European'
    elif 13 <= hour < 21:  # Overlaps with European
        return 'US'
    else:
        return 'Off-hours'

df['session'] = df['hour'].apply(get_session)

# Session summary
print("\n" + "="*80)
print("SESSION SUMMARY")
print("="*80)

session_stats = df.groupby('session').agg({
    'volume': 'mean',
    'atr_pct': 'mean',
    'range_pct': 'mean',
    'close': 'count'
}).round(4)

session_stats.columns = ['avg_volume', 'avg_atr_pct', 'avg_range_pct', 'candle_count']
session_stats = session_stats.sort_values('avg_volume', ascending=False)

print(session_stats.to_string())

# Identify best/worst hours
top_5_hours = hourly_stats.nlargest(5, 'avg_atr_pct').index.tolist()
bottom_5_hours = hourly_stats.nsmallest(5, 'avg_atr_pct').index.tolist()

print(f"\nMost volatile hours (highest ATR%): {top_5_hours}")
print(f"Least volatile hours (lowest ATR%): {bottom_5_hours}")

# Save hourly stats
hourly_stats.to_csv('./results/eth_hourly_stats.csv')
print("\nSaved: ./results/eth_hourly_stats.csv")

print("\n" + "="*80)
print("STRATEGY BACKTESTING BY SESSION")
print("="*80)

def backtest_strategy(df, strategy_type='mean_reversion', allowed_hours=None,
                     stop_loss_pct=0.5, take_profit_pct=1.0, leverage=10):
    """
    Backtest a strategy with optional hour filtering

    strategy_type: 'mean_reversion' or 'trend_following'
    allowed_hours: list of hours (0-23) to trade, or None for all hours
    """

    balance = 10000
    position = None
    trades = []
    equity = [balance]

    for i in range(250, len(df)):
        row = df.iloc[i]

        # Check if we should trade this hour
        if allowed_hours is not None and row['hour'] not in allowed_hours:
            equity.append(balance if position is None else balance + position['unrealized_pnl'])
            continue

        # Update position if exists
        if position is not None:
            current_price = row['close']
            position['unrealized_pnl'] = (current_price - position['entry']) / position['entry'] * 100 * leverage * position['size']

            # Check stop loss
            if position['side'] == 'long':
                if current_price <= position['stop']:
                    pnl = (position['stop'] - position['entry']) / position['entry'] * 100 * leverage * position['size']
                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': position['side'],
                        'entry': position['entry'],
                        'exit': position['stop'],
                        'pnl': pnl,
                        'pnl_pct': (position['stop'] - position['entry']) / position['entry'] * 100 * leverage,
                        'reason': 'stop_loss'
                    })
                    position = None
                    equity.append(balance)
                    continue

                # Check take profit
                if current_price >= position['target']:
                    pnl = (position['target'] - position['entry']) / position['entry'] * 100 * leverage * position['size']
                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': position['side'],
                        'entry': position['entry'],
                        'exit': position['target'],
                        'pnl': pnl,
                        'pnl_pct': (position['target'] - position['entry']) / position['entry'] * 100 * leverage,
                        'reason': 'take_profit'
                    })
                    position = None
                    equity.append(balance)
                    continue

            else:  # short
                if current_price >= position['stop']:
                    pnl = (position['entry'] - position['stop']) / position['entry'] * 100 * leverage * position['size']
                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': position['side'],
                        'entry': position['entry'],
                        'exit': position['stop'],
                        'pnl': pnl,
                        'pnl_pct': (position['entry'] - position['stop']) / position['entry'] * 100 * leverage,
                        'reason': 'stop_loss'
                    })
                    position = None
                    equity.append(balance)
                    continue

                if current_price <= position['target']:
                    pnl = (position['entry'] - position['target']) / position['entry'] * 100 * leverage * position['size']
                    balance += pnl
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'side': position['side'],
                        'entry': position['entry'],
                        'exit': position['target'],
                        'pnl': pnl,
                        'pnl_pct': (position['entry'] - position['target']) / position['entry'] * 100 * leverage,
                        'reason': 'take_profit'
                    })
                    position = None
                    equity.append(balance)
                    continue

        # Generate signals
        if position is None:
            signal = None

            if strategy_type == 'mean_reversion':
                # RSI oversold/overbought
                if row['rsi'] < 30:
                    signal = 'long'
                elif row['rsi'] > 70:
                    signal = 'short'

            elif strategy_type == 'trend_following':
                # EMA pullback
                if row['close'] > row['ema50'] and row['close'] < row['ema20']:
                    signal = 'long'
                elif row['close'] < row['ema50'] and row['close'] > row['ema20']:
                    signal = 'short'

            if signal:
                entry_price = row['close']
                position_size = balance * 0.1  # 10% of balance per trade

                if signal == 'long':
                    stop = entry_price * (1 - stop_loss_pct / 100)
                    target = entry_price * (1 + take_profit_pct / 100)
                else:
                    stop = entry_price * (1 + stop_loss_pct / 100)
                    target = entry_price * (1 - take_profit_pct / 100)

                position = {
                    'entry_time': row['timestamp'],
                    'side': signal,
                    'entry': entry_price,
                    'stop': stop,
                    'target': target,
                    'size': position_size,
                    'unrealized_pnl': 0
                }

        equity.append(balance if position is None else balance + position['unrealized_pnl'])

    # Close any remaining position
    if position is not None:
        final_price = df.iloc[-1]['close']
        if position['side'] == 'long':
            pnl = (final_price - position['entry']) / position['entry'] * 100 * leverage * position['size']
        else:
            pnl = (position['entry'] - final_price) / position['entry'] * 100 * leverage * position['size']

        balance += pnl
        trades.append({
            'entry_time': position['entry_time'],
            'exit_time': df.iloc[-1]['timestamp'],
            'side': position['side'],
            'entry': position['entry'],
            'exit': final_price,
            'pnl': pnl,
            'pnl_pct': pnl / position['size'] * 100,
            'reason': 'final_close'
        })

    # Calculate metrics
    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)

    total_return = (balance - 10000) / 10000 * 100

    wins = trades_df[trades_df['pnl'] > 0]
    losses = trades_df[trades_df['pnl'] <= 0]

    win_rate = len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0
    avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
    avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0

    # Drawdown
    equity_series = pd.Series(equity)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_drawdown = drawdown.min()

    profit_dd_ratio = abs(total_return / max_drawdown) if max_drawdown != 0 else 0

    return {
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'profit_dd_ratio': profit_dd_ratio,
        'win_rate': win_rate,
        'total_trades': len(trades_df),
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'final_balance': balance,
        'trades': trades_df,
        'equity': equity
    }

# Define session hour ranges
sessions = {
    '24/7': None,
    'Asian (23-07 UTC)': list(range(23, 24)) + list(range(0, 7)),
    'European (07-15 UTC)': list(range(7, 15)),
    'US (13-21 UTC)': list(range(13, 21)),
    'Euro+US (07-21 UTC)': list(range(7, 21)),
    'High Volume (09-19 UTC)': list(range(9, 19)),
    'Avoid Off-hours (07-21 UTC)': list(range(7, 21)),
    'Peak Volatility (Top 8h)': top_5_hours + [h for h in top_5_hours[:3]],  # Extend to 8 hours
}

print("\nTesting Mean Reversion Strategy across sessions...")
print("-" * 80)

mean_reversion_results = []

for session_name, hours in sessions.items():
    print(f"\nTesting: {session_name}")
    result = backtest_strategy(
        df,
        strategy_type='mean_reversion',
        allowed_hours=hours,
        stop_loss_pct=0.5,
        take_profit_pct=1.0,
        leverage=10
    )

    if result:
        mean_reversion_results.append({
            'session': session_name,
            'hours': str(hours) if hours else 'All',
            **{k: v for k, v in result.items() if k not in ['trades', 'equity']}
        })

        print(f"  Return: {result['total_return']:.2f}% | DD: {result['max_drawdown']:.2f}% | P/DD: {result['profit_dd_ratio']:.2f}")
        print(f"  Trades: {result['total_trades']} | Win Rate: {result['win_rate']:.1f}%")

print("\n" + "="*80)
print("Testing Trend Following Strategy across sessions...")
print("-" * 80)

trend_following_results = []

for session_name, hours in sessions.items():
    print(f"\nTesting: {session_name}")
    result = backtest_strategy(
        df,
        strategy_type='trend_following',
        allowed_hours=hours,
        stop_loss_pct=0.4,
        take_profit_pct=0.8,
        leverage=10
    )

    if result:
        trend_following_results.append({
            'session': session_name,
            'hours': str(hours) if hours else 'All',
            **{k: v for k, v in result.items() if k not in ['trades', 'equity']}
        })

        print(f"  Return: {result['total_return']:.2f}% | DD: {result['max_drawdown']:.2f}% | P/DD: {result['profit_dd_ratio']:.2f}")
        print(f"  Trades: {result['total_trades']} | Win Rate: {result['win_rate']:.1f}%")

# Create comparison dataframes
mr_df = pd.DataFrame(mean_reversion_results)
tf_df = pd.DataFrame(trend_following_results)

# Find best strategies
best_mr = mr_df.loc[mr_df['profit_dd_ratio'].idxmax()]
best_tf = tf_df.loc[tf_df['profit_dd_ratio'].idxmax()]

print("\n" + "="*80)
print("BEST STRATEGIES BY PROFIT/DD RATIO")
print("="*80)

print("\nMean Reversion - Best Session:")
print(f"  Session: {best_mr['session']}")
print(f"  Return: {best_mr['total_return']:.2f}%")
print(f"  Max DD: {best_mr['max_drawdown']:.2f}%")
print(f"  P/DD Ratio: {best_mr['profit_dd_ratio']:.2f}")
print(f"  Trades: {best_mr['total_trades']}")
print(f"  Win Rate: {best_mr['win_rate']:.1f}%")

print("\nTrend Following - Best Session:")
print(f"  Session: {best_tf['session']}")
print(f"  Return: {best_tf['total_return']:.2f}%")
print(f"  Max DD: {best_tf['max_drawdown']:.2f}%")
print(f"  P/DD Ratio: {best_tf['profit_dd_ratio']:.2f}")
print(f"  Trades: {best_tf['total_trades']}")
print(f"  Win Rate: {best_tf['win_rate']:.1f}%")

# Save results
mr_df.to_csv('./results/eth_mean_reversion_sessions.csv', index=False)
tf_df.to_csv('./results/eth_trend_following_sessions.csv', index=False)

print("\n" + "="*80)
print("FILES SAVED")
print("="*80)
print("./results/eth_hourly_stats.csv")
print("./results/eth_mean_reversion_sessions.csv")
print("./results/eth_trend_following_sessions.csv")

print("\n" + "="*80)
print("OPTIMIZATION: Testing custom hour combinations...")
print("="*80)

# Test avoiding worst hours
worst_hours = bottom_5_hours
all_hours_except_worst = [h for h in range(24) if h not in worst_hours]

print(f"\nAvoiding worst hours: {worst_hours}")
result = backtest_strategy(
    df,
    strategy_type='mean_reversion',
    allowed_hours=all_hours_except_worst,
    stop_loss_pct=0.5,
    take_profit_pct=1.0,
    leverage=10
)

if result:
    print(f"Result: Return: {result['total_return']:.2f}% | DD: {result['max_drawdown']:.2f}% | P/DD: {result['profit_dd_ratio']:.2f}")

print("\nAnalysis complete!")
