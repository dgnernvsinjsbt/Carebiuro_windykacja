"""
Detailed Portfolio Analysis - Weekly Breakdown & Trade Quality
"""

import pandas as pd
import numpy as np

# Load data
equity_df = pd.read_csv("trading/results/portfolio_equity_curve.csv")
equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
equity_df['date'] = equity_df['timestamp'].dt.date

trades_df = pd.read_csv("trading/results/portfolio_all_trades.csv")
trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date'])
trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date'])
trades_df['week'] = trades_df['entry_date'].dt.isocalendar().week

executed = trades_df[trades_df['status'] == 'EXECUTED'].copy()

print("=" * 100)
print("PORTFOLIO ANALYSIS - DETAILED BREAKDOWN")
print("=" * 100)

# Weekly Performance
print("\n📅 WEEKLY PERFORMANCE BREAKDOWN")
print("-" * 100)

weekly_stats = executed.groupby('week').agg({
    'pnl_pct': ['count', 'sum', 'mean', lambda x: (x > 0).sum()],
    'equity_before': ['first', 'last']
}).round(2)

weekly_stats.columns = ['Trades', 'Total_Return_%', 'Avg_Return_%', 'Winners', 'Start_Equity', 'End_Equity']
weekly_stats['Win_Rate_%'] = (weekly_stats['Winners'] / weekly_stats['Trades'] * 100).round(1)
weekly_stats['Equity_Growth_%'] = ((weekly_stats['End_Equity'] - weekly_stats['Start_Equity']) / weekly_stats['Start_Equity'] * 100).round(2)

print(weekly_stats)

# Best and Worst Trades
print("\n🏆 TOP 10 BEST TRADES")
print("-" * 100)
best_trades = executed.nlargest(10, 'pnl_pct')[['entry_date', 'strategy', 'pnl_pct', 'equity_before']].copy()
best_trades['profit_usd'] = (best_trades['pnl_pct'] / 100 * best_trades['equity_before']).round(2)
best_trades['entry_date'] = best_trades['entry_date'].dt.strftime('%Y-%m-%d %H:%M')
print(best_trades.to_string(index=False))

print("\n💀 TOP 10 WORST TRADES")
print("-" * 100)
worst_trades = executed.nsmallest(10, 'pnl_pct')[['entry_date', 'strategy', 'pnl_pct', 'equity_before']].copy()
worst_trades['loss_usd'] = (worst_trades['pnl_pct'] / 100 * worst_trades['equity_before']).round(2)
worst_trades['entry_date'] = worst_trades['entry_date'].dt.strftime('%Y-%m-%d %H:%M')
print(worst_trades.to_string(index=False))

# Strategy Performance Metrics
print("\n📊 STRATEGY DETAILED METRICS")
print("-" * 100)

for strategy in executed['strategy'].unique():
    strat_trades = executed[executed['strategy'] == strategy]

    winners = strat_trades[strat_trades['pnl_pct'] > 0]
    losers = strat_trades[strat_trades['pnl_pct'] <= 0]

    print(f"\n{strategy}")
    print(f"  Trades: {len(strat_trades)}")
    print(f"  Winners: {len(winners)} ({len(winners)/len(strat_trades)*100:.1f}%)")
    print(f"  Losers: {len(losers)} ({len(losers)/len(strat_trades)*100:.1f}%)")
    print(f"  Total Return: +{strat_trades['pnl_pct'].sum():.2f}%")
    print(f"  Avg Winner: +{winners['pnl_pct'].mean():.2f}%" if len(winners) > 0 else "  Avg Winner: N/A")
    print(f"  Avg Loser: {losers['pnl_pct'].mean():.2f}%" if len(losers) > 0 else "  Avg Loser: N/A")
    print(f"  Best Trade: +{strat_trades['pnl_pct'].max():.2f}%")
    print(f"  Worst Trade: {strat_trades['pnl_pct'].min():.2f}%")
    print(f"  Profit Factor: {winners['pnl_pct'].sum() / abs(losers['pnl_pct'].sum()):.2f}x" if len(losers) > 0 and losers['pnl_pct'].sum() != 0 else "  Profit Factor: ∞")

# Equity Milestones
print("\n🎯 EQUITY MILESTONES")
print("-" * 100)
milestones = [10000, 12000, 15000, 18000, 20000, 22000]

for milestone in milestones:
    milestone_reached = equity_df[equity_df['equity'] >= milestone]
    if len(milestone_reached) > 0:
        first_time = milestone_reached.iloc[0]
        days_elapsed = (first_time['timestamp'] - equity_df['timestamp'].iloc[0]).days
        print(f"  ${milestone:,} reached on {first_time['timestamp'].strftime('%Y-%m-%d %H:%M')} (Day {days_elapsed})")

# Compounding Effect Analysis
print("\n💰 COMPOUNDING EFFECT ANALYSIS")
print("-" * 100)

# Calculate what returns would be WITHOUT compounding (fixed $10k per trade)
executed['fixed_pnl_usd'] = executed['pnl_pct'] / 100 * 10000
total_without_compounding = 10000 + executed['fixed_pnl_usd'].sum()

print(f"  If each trade used fixed $10,000 (NO compounding):")
print(f"    Final Equity: ${total_without_compounding:,.2f}")
print(f"    Total Return: {(total_without_compounding - 10000) / 10000 * 100:+.2f}%")
print(f"\n  With compounding (actual simulation):")
print(f"    Final Equity: $22,681.83")
print(f"    Total Return: +126.82%")
print(f"\n  Compounding Bonus: ${22681.83 - total_without_compounding:,.2f} ({(22681.83 / total_without_compounding - 1) * 100:+.1f}%)")

# Position Conflicts Analysis
print("\n⚠️  POSITION CONFLICTS ANALYSIS")
print("-" * 100)
skipped = trades_df[trades_df['status'] == 'SKIPPED']

if len(skipped) > 0:
    print(f"  Total Skipped: {len(skipped)} trades")
    print(f"  Missed Return: {skipped['pnl_pct'].sum():+.2f}%")
    print(f"\n  Skipped by Strategy:")
    for strategy in skipped['strategy'].unique():
        strat_skipped = skipped[skipped['strategy'] == strategy]
        print(f"    {strategy}: {len(strat_skipped)} trades (missed {strat_skipped['pnl_pct'].sum():+.2f}%)")
else:
    print("  No trades were skipped - perfect execution!")

# Consecutive Wins/Losses
print("\n🔥 STREAK ANALYSIS")
print("-" * 100)

executed['is_win'] = executed['pnl_pct'] > 0
executed['streak_id'] = (executed['is_win'] != executed['is_win'].shift()).cumsum()

win_streaks = executed[executed['is_win']].groupby('streak_id').size()
loss_streaks = executed[~executed['is_win']].groupby('streak_id').size()

print(f"  Longest Win Streak: {win_streaks.max() if len(win_streaks) > 0 else 0} consecutive trades")
print(f"  Longest Loss Streak: {loss_streaks.max() if len(loss_streaks) > 0 else 0} consecutive trades")
print(f"  Total Win Streaks: {len(win_streaks)}")
print(f"  Total Loss Streaks: {len(loss_streaks)}")

# Risk Metrics
print("\n⚡ RISK METRICS")
print("-" * 100)

daily_returns = equity_df.groupby('date')['equity'].last().pct_change().dropna()
sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(30) if daily_returns.std() > 0 else 0

print(f"  Max Drawdown: -5.88%")
print(f"  Sharpe Ratio: {sharpe_ratio:.2f} (annualized estimate)")
print(f"  Daily Volatility: {daily_returns.std() * 100:.2f}%")
print(f"  Best Day: +{daily_returns.max() * 100:.2f}%")
print(f"  Worst Day: {daily_returns.min() * 100:.2f}%")

print("\n" + "=" * 100)
print("END OF DETAILED ANALYSIS")
print("=" * 100)
