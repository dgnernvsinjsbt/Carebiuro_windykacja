#!/usr/bin/env python3
"""Analyze REAL MELANIA backtest results from existing file"""
import pandas as pd
import numpy as np

print("="*80)
print("MELANIA SHORT REVERSAL - REAL RESULTS ANALYSIS")
print("="*80)

# Load existing results
df = pd.read_csv('trading/melania_6months_short_only.csv')

print(f"\n📊 Data Loaded:")
print(f"   Total Trades: {len(df)}")
print(f"   Period: {df['entry_time'].min()} to {df['exit_time'].max()}")

# Calculate equity curve
equity = 100.0
equity_curve = [100.0]

for _, row in df.iterrows():
    equity += row['pnl_dollar']
    equity_curve.append(equity)

# Calculate max drawdown (CORRECTED METHOD)
eq_series = pd.Series(equity_curve)
running_max = eq_series.expanding().max()
drawdown = (eq_series - running_max) / running_max * 100
max_dd = drawdown.min()

total_return = ((equity - 100) / 100) * 100
return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

# Calculate consecutive wins/losses
consecutive_wins = 0
consecutive_losses = 0
max_consecutive_wins = 0
max_consecutive_losses = 0

for _, row in df.iterrows():
    if row['pnl_dollar'] > 0:
        consecutive_wins += 1
        consecutive_losses = 0
        max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
    else:
        consecutive_losses += 1
        consecutive_wins = 0
        max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

# Trade statistics
winners = df[df['pnl_dollar'] > 0]
losers = df[df['pnl_dollar'] <= 0]
win_rate = (len(winners) / len(df)) * 100

print(f"\n{'='*80}")
print("📊 MELANIA SHORT REVERSAL - REAL STATISTICS")
print(f"{'='*80}")

print(f"\n💰 Performance:")
print(f"   Total Return: {total_return:+.2f}%")
print(f"   Max Drawdown: {max_dd:.2f}%")
print(f"   Return/DD Ratio: {return_dd:.2f}x")
print(f"   Final Equity: ${equity:.2f}")

print(f"\n📈 Trade Statistics:")
print(f"   Total Trades: {len(df)}")
print(f"   Winners: {len(winners)} ({win_rate:.1f}%)")
print(f"   Losers: {len(losers)} ({100-win_rate:.1f}%)")

print(f"\n🔥 Streaks:")
print(f"   Max Consecutive Wins: {max_consecutive_wins}")
print(f"   Max Consecutive Losses: {max_consecutive_losses}")

print(f"\n💵 P&L Breakdown:")
print(f"   Avg Winner: {winners['pnl_pct'].mean():.2f}% (${winners['pnl_dollar'].mean():.2f})")
print(f"   Avg Loser: {losers['pnl_pct'].mean():.2f}% (${losers['pnl_dollar'].mean():.2f})")
print(f"   Best Trade: {df['pnl_pct'].max():.2f}% (${df['pnl_dollar'].max():.2f})")
print(f"   Worst Trade: {df['pnl_pct'].min():.2f}% (${df['pnl_dollar'].min():.2f})")

print(f"\n🎯 Exit Types:")
for exit_type in df['exit_reason'].unique():
    count = len(df[df['exit_reason'] == exit_type])
    pct = (count / len(df)) * 100
    print(f"   {exit_type}: {count} ({pct:.1f}%)")

# Monthly breakdown
df['month'] = pd.to_datetime(df['entry_time']).dt.to_period('M')
monthly = df.groupby('month').agg({
    'pnl_dollar': ['sum', 'count']
})

print(f"\n📅 Monthly Breakdown:")
for month in sorted(df['month'].unique()):
    month_trades = df[df['month'] == month]
    month_profit = month_trades['pnl_dollar'].sum()
    month_count = len(month_trades)
    month_win_rate = (len(month_trades[month_trades['pnl_dollar'] > 0]) / month_count * 100) if month_count > 0 else 0
    print(f"   {month}: {month_count} trades, ${month_profit:+.2f} ({month_win_rate:.1f}% win rate)")

print(f"\n{'='*80}")
print("✅ ANALYSIS COMPLETE")
print(f"{'='*80}")
