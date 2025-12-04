"""
Visualize PI/USDT Short Strategy Results
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load trade results
trades = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/pi_short_summary.csv')
trades['entry_time'] = pd.to_datetime(trades['entry_time'])
trades['exit_time'] = pd.to_datetime(trades['exit_time'])

# Create figure with subplots
fig, axes = plt.subplots(3, 1, figsize=(14, 12))
fig.suptitle('PI/USDT Short Strategy: EMA 5/20 Cross Down with 1.5:1 RR', fontsize=16, fontweight='bold')

# 1. Equity Curve
ax1 = axes[0]
ax1.plot(trades['exit_time'], trades['equity'], linewidth=2, color='#2E86AB', label='Equity')
ax1.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='Starting Capital')
ax1.fill_between(trades['exit_time'], 1.0, trades['equity'],
                  where=(trades['equity'] >= 1.0), alpha=0.3, color='green', interpolate=True)
ax1.fill_between(trades['exit_time'], 1.0, trades['equity'],
                  where=(trades['equity'] < 1.0), alpha=0.3, color='red', interpolate=True)
ax1.set_ylabel('Equity (starting = 1.0)', fontsize=11, fontweight='bold')
ax1.set_title(f'Equity Curve: {trades["equity"].iloc[-1]:.4f}x ({(trades["equity"].iloc[-1]-1)*100:.2f}% return)',
              fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left')

# 2. Drawdown
ax2 = axes[1]
ax2.fill_between(trades['exit_time'], 0, -trades['drawdown_pct'],
                  alpha=0.6, color='#D62828', label='Drawdown')
ax2.set_ylabel('Drawdown (%)', fontsize=11, fontweight='bold')
ax2.set_title(f'Drawdown: Max = {trades["drawdown_pct"].max():.2f}%', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(loc='lower left')
ax2.set_ylim([-(trades['drawdown_pct'].max() * 1.2), 2])

# 3. Trade P&L Distribution
ax3 = axes[2]
winning_trades = trades[trades['net_pnl_pct'] > 0]
losing_trades = trades[trades['net_pnl_pct'] <= 0]

ax3.scatter(winning_trades['exit_time'], winning_trades['net_pnl_pct'],
           color='green', alpha=0.6, s=50, label=f'Wins ({len(winning_trades)})')
ax3.scatter(losing_trades['exit_time'], losing_trades['net_pnl_pct'],
           color='red', alpha=0.6, s=50, label=f'Losses ({len(losing_trades)})')
ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
ax3.set_ylabel('Trade P&L (%)', fontsize=11, fontweight='bold')
ax3.set_xlabel('Date', fontsize=11, fontweight='bold')
ax3.set_title(f'Individual Trade Performance: Win Rate = {len(winning_trades)/len(trades)*100:.1f}%',
              fontsize=12, fontweight='bold')
ax3.grid(True, alpha=0.3)
ax3.legend(loc='upper right')

plt.tight_layout()
plt.savefig('/workspaces/Carebiuro_windykacja/trading/results/pi_short_equity.png', dpi=300, bbox_inches='tight')
print("Equity curve saved to: trading/results/pi_short_equity.png")

# Create additional analysis charts
fig2, axes2 = plt.subplots(2, 2, figsize=(14, 10))
fig2.suptitle('PI/USDT Short Strategy: Detailed Analysis', fontsize=16, fontweight='bold')

# 1. P&L Distribution Histogram
ax1 = axes2[0, 0]
ax1.hist(winning_trades['net_pnl_pct'], bins=20, alpha=0.7, color='green', label='Wins', edgecolor='black')
ax1.hist(losing_trades['net_pnl_pct'], bins=20, alpha=0.7, color='red', label='Losses', edgecolor='black')
ax1.axvline(x=0, color='black', linestyle='--', linewidth=2)
ax1.set_xlabel('P&L (%)', fontweight='bold')
ax1.set_ylabel('Frequency', fontweight='bold')
ax1.set_title('P&L Distribution', fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. Exit Reasons
ax2 = axes2[0, 1]
exit_counts = trades['exit_reason'].value_counts()
colors_exit = ['#06A77D' if reason == 'take_profit' else '#D62828' for reason in exit_counts.index]
ax2.bar(exit_counts.index, exit_counts.values, color=colors_exit, alpha=0.7, edgecolor='black')
ax2.set_xlabel('Exit Reason', fontweight='bold')
ax2.set_ylabel('Count', fontweight='bold')
ax2.set_title('Exit Reason Distribution', fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')
for i, (reason, count) in enumerate(exit_counts.items()):
    ax2.text(i, count + 1, str(count), ha='center', fontweight='bold')

# 3. Rolling Win Rate (20-trade window)
ax3 = axes2[1, 0]
trades['is_win'] = (trades['net_pnl_pct'] > 0).astype(int)
rolling_wr = trades['is_win'].rolling(window=20, min_periods=10).mean() * 100
ax3.plot(trades['exit_time'], rolling_wr, color='#2E86AB', linewidth=2)
ax3.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% WR')
ax3.fill_between(trades['exit_time'], 50, rolling_wr,
                  where=(rolling_wr >= 50), alpha=0.3, color='green', interpolate=True)
ax3.fill_between(trades['exit_time'], 50, rolling_wr,
                  where=(rolling_wr < 50), alpha=0.3, color='red', interpolate=True)
ax3.set_xlabel('Date', fontweight='bold')
ax3.set_ylabel('Win Rate (%)', fontweight='bold')
ax3.set_title('Rolling 20-Trade Win Rate', fontweight='bold')
ax3.legend()
ax3.grid(True, alpha=0.3)

# 4. Cumulative P&L by Month
ax4 = axes2[1, 1]
trades['month'] = trades['exit_time'].dt.to_period('M')
monthly_pnl = trades.groupby('month')['net_pnl_pct'].sum()
colors_monthly = ['green' if pnl > 0 else 'red' for pnl in monthly_pnl.values]
ax4.bar(range(len(monthly_pnl)), monthly_pnl.values, color=colors_monthly, alpha=0.7, edgecolor='black')
ax4.set_xticks(range(len(monthly_pnl)))
ax4.set_xticklabels([str(m) for m in monthly_pnl.index], rotation=45)
ax4.set_xlabel('Month', fontweight='bold')
ax4.set_ylabel('Total P&L (%)', fontweight='bold')
ax4.set_title('Monthly P&L', fontweight='bold')
ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax4.grid(True, alpha=0.3, axis='y')
for i, pnl in enumerate(monthly_pnl.values):
    ax4.text(i, pnl + (1 if pnl > 0 else -1), f'{pnl:.1f}%', ha='center', fontweight='bold', fontsize=9)

plt.tight_layout()
plt.savefig('/workspaces/Carebiuro_windykacja/trading/results/pi_short_analysis_charts.png', dpi=300, bbox_inches='tight')
print("Analysis charts saved to: trading/results/pi_short_analysis_charts.png")

# Print summary statistics
print("\n" + "="*60)
print("PI/USDT SHORT STRATEGY - SUMMARY STATISTICS")
print("="*60)
print(f"Strategy: EMA 5/20 Cross Down with 1.5:1 Risk-Reward")
print(f"Period: {trades['entry_time'].min()} to {trades['exit_time'].max()}")
print(f"\nPerformance:")
print(f"  Total Return: {(trades['equity'].iloc[-1]-1)*100:.2f}%")
print(f"  Total Trades: {len(trades)}")
print(f"  Win Rate: {len(winning_trades)/len(trades)*100:.1f}%")
print(f"  Profit Factor: {winning_trades['net_pnl_pct'].sum() / abs(losing_trades['net_pnl_pct'].sum()):.2f}")
print(f"\nTrade Characteristics:")
print(f"  Avg Win: {winning_trades['net_pnl_pct'].mean():.2f}%")
print(f"  Avg Loss: {abs(losing_trades['net_pnl_pct'].mean()):.2f}%")
print(f"  Largest Win: {trades['net_pnl_pct'].max():.2f}%")
print(f"  Largest Loss: {trades['net_pnl_pct'].min():.2f}%")
print(f"  Reward/Risk: {winning_trades['net_pnl_pct'].mean() / abs(losing_trades['net_pnl_pct'].mean()):.2f}:1")
print(f"\nRisk Metrics:")
print(f"  Max Drawdown: {trades['drawdown_pct'].max():.2f}%")
print(f"  Avg Fees per Trade: {trades['fees_pct'].mean():.4f}%")
print(f"\nExit Analysis:")
for reason, count in exit_counts.items():
    print(f"  {reason}: {count} ({count/len(trades)*100:.1f}%)")
print("="*60)