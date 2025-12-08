import pandas as pd
import numpy as np
from datetime import datetime

def calculate_ema(df, span):
    return df['close'].ewm(span=span, adjust=False).mean()

def backtest_strategy(df, ema_fast, ema_slow, sl_pct, tp_pct, mom_7d_threshold, mom_14d_threshold, timeframe):
    """
    Backtest short strategy with given parameters
    """
    df = df.copy()

    # Calculate EMAs
    df['ema_fast'] = calculate_ema(df, ema_fast)
    df['ema_slow'] = calculate_ema(df, ema_slow)

    # Calculate momentum lookback periods based on timeframe
    if timeframe == '15m':
        lookback_7d = 672  # 7 days * 96 candles/day
        lookback_14d = 1344
    elif timeframe == '30m':
        lookback_7d = 336  # 7 days * 48 candles/day
        lookback_14d = 672
    else:
        raise ValueError(f"Unknown timeframe: {timeframe}")

    df['momentum_7d'] = df['close'].pct_change(lookback_7d) * 100
    df['momentum_14d'] = df['close'].pct_change(lookback_14d) * 100

    # Filter: allow shorts when momentum is below threshold
    df['allow_short'] = (df['momentum_7d'] < mom_7d_threshold) & (df['momentum_14d'] < mom_14d_threshold)

    # Trading simulation
    equity_curve = []
    trades = []

    in_position = False
    entry_price = 0
    entry_date = None
    stop_loss = 0
    take_profit = 0
    equity = 1.0
    peak = 1.0
    max_dd = 0

    fee = 0.0001  # 0.01% taker fee

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]

        if not in_position:
            # Entry: EMA fast crosses DOWN below EMA slow
            if (row['ema_fast'] < row['ema_slow'] and
                prev_row['ema_fast'] >= prev_row['ema_slow'] and
                row['allow_short']):

                in_position = True
                entry_price = row['close']
                entry_date = row['timestamp']
                stop_loss = entry_price * (1 + sl_pct/100)
                take_profit = entry_price * (1 - tp_pct/100)

        else:
            # Check exit conditions
            exit_type = None
            exit_price = None

            if row['high'] >= stop_loss:
                # Stop loss hit
                exit_price = stop_loss
                exit_type = 'SL'
                pnl = (entry_price - stop_loss) / entry_price - fee

            elif row['low'] <= take_profit:
                # Take profit hit
                exit_price = take_profit
                exit_type = 'TP'
                pnl = (entry_price - take_profit) / entry_price - fee

            if exit_type:
                equity *= (1 + pnl)

                trades.append({
                    'entry_date': entry_date,
                    'exit_date': row['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl * 100,
                    'exit_type': exit_type
                })

                in_position = False

        # Track drawdown
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)

        equity_curve.append(equity)

    # Calculate metrics
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t['pnl_pct'] > 0])
    losing_trades = len([t for t in trades if t['pnl_pct'] < 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    tp_hits = len([t for t in trades if t['exit_type'] == 'TP'])
    sl_hits = len([t for t in trades if t['exit_type'] == 'SL'])

    final_return = (equity - 1) * 100
    rr_score = final_return / max_dd if max_dd > 0 else 0

    return {
        'final_equity': equity,
        'return_pct': final_return,
        'max_dd': max_dd,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'tp_hits': tp_hits,
        'sl_hits': sl_hits,
        'rr_score': rr_score,
        'trades': trades
    }

# Load all tokens
tokens = {
    'FARTCOIN': {
        '15m': '../fartcoin_15m_3months.csv',
        '30m': 'fartcoin_30m_jan2025.csv'
    },
    'PENGU': {
        '15m': '../pengu_15m_full.csv',
        '30m': 'pengu_30m_jan2025.csv'
    },
    'PI': {
        '15m': '../pi_15m_3months.csv',
        '30m': 'pi_30m_jan2025.csv'
    },
    'MELANIA': {
        '15m': '../melania_15m_3months.csv',
        '30m': 'melania_30m_jan2025.csv'
    }
}

# Strategy configs
config_15m = {
    'ema_fast': 8,
    'ema_slow': 21,
    'sl_pct': 4.0,
    'tp_pct': 8.0,
    'mom_7d_threshold': 5,
    'mom_14d_threshold': 10
}

config_30m = {
    'ema_fast': 3,
    'ema_slow': 15,
    'sl_pct': 4.0,
    'tp_pct': 8.0,
    'mom_7d_threshold': 5,
    'mom_14d_threshold': 10
}

print("\n" + "="*120)
print("15-MINUTE vs 30-MINUTE TIMEFRAME COMPARISON")
print("="*120)
print(f"15M Strategy: EMA {config_15m['ema_fast']}/{config_15m['ema_slow']} | SL {config_15m['sl_pct']}% | TP {config_15m['tp_pct']}%")
print(f"30M Strategy: EMA {config_30m['ema_fast']}/{config_30m['ema_slow']} | SL {config_30m['sl_pct']}% | TP {config_30m['tp_pct']}%")
print("="*120)

results_comparison = []

for token, files in tokens.items():
    print(f"\n{token}:")
    print("-" * 120)

    # Load data
    df_15m = pd.read_csv(files['15m'])
    df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])

    df_30m = pd.read_csv(files['30m'])
    df_30m['timestamp'] = pd.to_datetime(df_30m['timestamp'])

    # Get date ranges
    min_date = df_30m['timestamp'].min()
    max_date = df_30m['timestamp'].max()

    # Filter 15M to same date range for fair comparison
    df_15m_filtered = df_15m[(df_15m['timestamp'] >= min_date) & (df_15m['timestamp'] <= max_date)]

    # Calculate days
    days = (max_date - min_date).days

    # Run backtests
    result_15m = backtest_strategy(df_15m_filtered, **config_15m, timeframe='15m')
    result_30m = backtest_strategy(df_30m, **config_30m, timeframe='30m')

    # Print comparison table
    print(f"{'Metric':<25} {'15-Minute':<20} {'30-Minute':<20} {'Difference':<20}")
    print("-" * 120)
    print(f"{'Period':<25} {days} days ({min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')})")
    print(f"{'Total Return':<25} {result_15m['return_pct']:>6.1f}%            {result_30m['return_pct']:>6.1f}%            {result_30m['return_pct'] - result_15m['return_pct']:>+6.1f}%")
    print(f"{'Max Drawdown':<25} {result_15m['max_dd']:>6.1f}%            {result_30m['max_dd']:>6.1f}%            {result_30m['max_dd'] - result_15m['max_dd']:>+6.1f}%")
    print(f"{'Risk:Reward Score':<25} {result_15m['rr_score']:>6.2f}x            {result_30m['rr_score']:>6.2f}x            {result_30m['rr_score'] - result_15m['rr_score']:>+6.2f}x")
    print(f"{'Total Trades':<25} {result_15m['total_trades']:>6}              {result_30m['total_trades']:>6}              {result_30m['total_trades'] - result_15m['total_trades']:>+6}")
    print(f"{'Winning Trades':<25} {result_15m['winning_trades']:>6}              {result_30m['winning_trades']:>6}              {result_30m['winning_trades'] - result_15m['winning_trades']:>+6}")
    print(f"{'Losing Trades':<25} {result_15m['losing_trades']:>6}              {result_30m['losing_trades']:>6}              {result_30m['losing_trades'] - result_15m['losing_trades']:>+6}")
    print(f"{'Win Rate':<25} {result_15m['win_rate']:>6.1f}%            {result_30m['win_rate']:>6.1f}%            {result_30m['win_rate'] - result_15m['win_rate']:>+6.1f}%")
    print(f"{'TP Hits':<25} {result_15m['tp_hits']:>6}              {result_30m['tp_hits']:>6}              {result_30m['tp_hits'] - result_15m['tp_hits']:>+6}")
    print(f"{'SL Hits':<25} {result_15m['sl_hits']:>6}              {result_30m['sl_hits']:>6}              {result_30m['sl_hits'] - result_15m['sl_hits']:>+6}")

    # Determine winner
    if result_30m['return_pct'] > result_15m['return_pct']:
        winner = "30M 🏆"
        winner_margin = result_30m['return_pct'] - result_15m['return_pct']
    else:
        winner = "15M 🏆"
        winner_margin = result_15m['return_pct'] - result_30m['return_pct']

    print(f"\n{'Winner:':<25} {winner} (by +{winner_margin:.1f}%)")

    # Store for summary
    results_comparison.append({
        'token': token,
        'days': days,
        '15m_return': result_15m['return_pct'],
        '30m_return': result_30m['return_pct'],
        '15m_dd': result_15m['max_dd'],
        '30m_dd': result_30m['max_dd'],
        '15m_rr': result_15m['rr_score'],
        '30m_rr': result_30m['rr_score'],
        '15m_trades': result_15m['total_trades'],
        '30m_trades': result_30m['total_trades'],
        '15m_winrate': result_15m['win_rate'],
        '30m_winrate': result_30m['win_rate'],
        'winner': '30M' if result_30m['return_pct'] > result_15m['return_pct'] else '15M'
    })

# Print overall summary
print("\n" + "="*120)
print("OVERALL SUMMARY")
print("="*120)

df_summary = pd.DataFrame(results_comparison)

avg_15m_return = df_summary['15m_return'].mean()
avg_30m_return = df_summary['30m_return'].mean()
avg_15m_dd = df_summary['15m_dd'].mean()
avg_30m_dd = df_summary['30m_dd'].mean()
avg_15m_rr = df_summary['15m_rr'].mean()
avg_30m_rr = df_summary['30m_rr'].mean()
avg_15m_winrate = df_summary['15m_winrate'].mean()
avg_30m_winrate = df_summary['30m_winrate'].mean()

print(f"\n{'Metric':<25} {'15-Minute AVG':<20} {'30-Minute AVG':<20} {'Improvement':<20}")
print("-" * 120)
print(f"{'Average Return':<25} {avg_15m_return:>6.1f}%            {avg_30m_return:>6.1f}%            {avg_30m_return - avg_15m_return:>+6.1f}%")
print(f"{'Average Drawdown':<25} {avg_15m_dd:>6.1f}%            {avg_30m_dd:>6.1f}%            {avg_30m_dd - avg_15m_dd:>+6.1f}%")
print(f"{'Average R:R Score':<25} {avg_15m_rr:>6.2f}x            {avg_30m_rr:>6.2f}x            {avg_30m_rr - avg_15m_rr:>+6.2f}x")
print(f"{'Average Win Rate':<25} {avg_15m_winrate:>6.1f}%            {avg_30m_winrate:>6.1f}%            {avg_30m_winrate - avg_15m_winrate:>+6.1f}%")

# Count winners
winner_30m = len(df_summary[df_summary['winner'] == '30M'])
winner_15m = len(df_summary[df_summary['winner'] == '15M'])

print(f"\n{'Tokens where 30M wins:':<25} {winner_30m}/4")
print(f"{'Tokens where 15M wins:':<25} {winner_15m}/4")

# Calculate relative improvement
rel_improvement = ((avg_30m_return / avg_15m_return) - 1) * 100 if avg_15m_return > 0 else 0

print("\n" + "="*120)
print("VERDICT:")
print("="*120)

if avg_30m_return > avg_15m_return:
    print(f"🏆 30-MINUTE TIMEFRAME IS THE WINNER!")
    print(f"   - Average return improvement: +{avg_30m_return - avg_15m_return:.1f}% absolute (+{rel_improvement:.1f}% relative)")
    print(f"   - Wins on {winner_30m}/4 tokens")
    print(f"   - Better Risk:Reward score: {avg_30m_rr:.2f}x vs {avg_15m_rr:.2f}x")
else:
    print(f"🏆 15-MINUTE TIMEFRAME IS THE WINNER!")
    print(f"   - Average return improvement: +{avg_15m_return - avg_30m_return:.1f}% absolute")
    print(f"   - Wins on {winner_15m}/4 tokens")

print("="*120)

# Save detailed comparison
df_summary.to_csv('trading/results/15m_vs_30m_detailed_comparison.csv', index=False)
print("\n✅ Detailed comparison saved to trading/results/15m_vs_30m_detailed_comparison.csv")