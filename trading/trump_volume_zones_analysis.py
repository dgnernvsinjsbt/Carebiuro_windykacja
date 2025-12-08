"""
Analyze TRUMP Volume Zones: Max Drawdown vs Max Profit
"""
import pandas as pd
import numpy as np

# Load trades
trades = pd.read_csv('results/TRUMP_volume_zones_trades.csv')

print("="*60)
print("TRUMP VOLUME ZONES - EQUITY CURVE ANALYSIS")
print("="*60)
print()

# Calculate cumulative equity curve
trades['cumulative_pnl'] = (trades['pnl'] * 100).cumsum()
trades['equity'] = 100 + trades['cumulative_pnl']  # Start with $100

# Calculate running max (peak equity)
trades['running_max'] = trades['equity'].cummax()

# Calculate drawdown from peak
trades['drawdown'] = trades['equity'] - trades['running_max']
trades['drawdown_pct'] = (trades['drawdown'] / trades['running_max']) * 100

# Stats
max_profit = trades['cumulative_pnl'].max()
final_profit = trades['cumulative_pnl'].iloc[-1]
max_drawdown = trades['drawdown_pct'].min()
max_drawdown_abs = trades['drawdown'].min()

# Find when max DD occurred
max_dd_idx = trades['drawdown_pct'].idxmin()
max_dd_trade = trades.loc[max_dd_idx]

# Find when max profit occurred
max_profit_idx = trades['cumulative_pnl'].idxmax()
max_profit_trade = trades.loc[max_profit_idx]

print(f"Total Trades: {len(trades)}")
print(f"Final Return: {final_profit:.2f}%")
print()

print("PEAK PROFIT:")
print(f"  Max Profit: {max_profit:.2f}%")
print(f"  Occurred at trade: {max_profit_idx + 1}/{len(trades)}")
print(f"  Equity at peak: ${trades.loc[max_profit_idx, 'equity']:.2f}")
print()

print("MAX DRAWDOWN:")
print(f"  Max Drawdown: {max_drawdown:.2f}%")
print(f"  Max DD (absolute): ${max_drawdown_abs:.2f}")
print(f"  Occurred at trade: {max_dd_idx + 1}/{len(trades)}")
print(f"  Equity at lowest: ${trades.loc[max_dd_idx, 'equity']:.2f}")
print(f"  Peak before DD: ${trades.loc[max_dd_idx, 'running_max']:.2f}")
print()

# Calculate recovery
if max_dd_idx < len(trades) - 1:
    recovered = trades.loc[max_dd_idx:, 'drawdown_pct'] >= -0.01  # Recovered if DD < 0.01%
    if recovered.any():
        recovery_idx = trades.loc[max_dd_idx:][recovered].index[0]
        trades_to_recover = recovery_idx - max_dd_idx
        print(f"Recovery: {trades_to_recover} trades to recover from max DD")
    else:
        print("Recovery: Still in drawdown at end of period")
else:
    print("Recovery: Max DD occurred at final trade")
print()

# Show equity curve milestones
print("EQUITY CURVE MILESTONES:")
print(f"  Starting equity: $100.00")
print(f"  Peak equity: ${trades['equity'].max():.2f}")
print(f"  Lowest equity: ${trades['equity'].min():.2f}")
print(f"  Final equity: ${trades['equity'].iloc[-1]:.2f}")
print()

# Consecutive wins/losses
trades['is_win'] = trades['pnl'] > 0
trades['streak'] = (trades['is_win'] != trades['is_win'].shift()).cumsum()
streak_lengths = trades.groupby('streak')['is_win'].agg(['sum', 'count'])
max_win_streak = streak_lengths[streak_lengths['sum'] == streak_lengths['count']]['count'].max()
max_loss_streak = streak_lengths[streak_lengths['sum'] == 0]['count'].max()

print("STREAKS:")
print(f"  Max consecutive wins: {max_win_streak}")
print(f"  Max consecutive losses: {max_loss_streak}")
print()

# Top 5 and bottom 5 trades
print("TOP 5 WINNING TRADES:")
top_5 = trades.nlargest(5, 'pnl')[['direction', 'pnl', 'bars', 'exit_reason', 'zone_bars']]
for idx, row in top_5.iterrows():
    print(f"  {row['direction']:5} {row['pnl']*100:+.2f}% ({row['bars']} bars, {row['exit_reason']}, zone: {row['zone_bars']} bars)")
print()

print("TOP 5 LOSING TRADES:")
bottom_5 = trades.nsmallest(5, 'pnl')[['direction', 'pnl', 'bars', 'exit_reason', 'zone_bars']]
for idx, row in bottom_5.iterrows():
    print(f"  {row['direction']:5} {row['pnl']*100:+.2f}% ({row['bars']} bars, {row['exit_reason']}, zone: {row['zone_bars']} bars)")
print()

# Risk metrics
print("RISK METRICS:")
returns_array = trades['pnl'].values * 100
sharpe = returns_array.mean() / returns_array.std() if returns_array.std() > 0 else 0
print(f"  Sharpe Ratio (trade-based): {sharpe:.2f}")
print(f"  Profit Factor: {abs(trades[trades['pnl'] > 0]['pnl'].sum() / trades[trades['pnl'] <= 0]['pnl'].sum()):.2f}")
print(f"  Max Profit / Max Drawdown: {abs(max_profit / max_drawdown):.2f}x")
print()

# Compare to previous approaches
print("="*60)
print("COMPARISON TO PREVIOUS APPROACHES")
print("="*60)
print(f"{'Approach':<30} {'Return':>8} {'Max DD':>8} {'Return/DD':>10}")
print("-"*60)
print(f"{'Scalping':<30} {'-0.59%':>8} {'N/A':>8} {'N/A':>10}")
print(f"{'Mean-Reversion':<30} {'-2.91%':>8} {'N/A':>8} {'N/A':>10}")
print(f"{'Patterns Filtered':<30} {'-1.05%':>8} {'N/A':>8} {'N/A':>10}")
print(f"{'Volume Zones':<30} {f'+{final_profit:.2f}%':>8} {f'{max_drawdown:.2f}%':>8} {f'{abs(final_profit/max_drawdown):.2f}x':>10}")
