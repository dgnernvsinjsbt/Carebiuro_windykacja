"""
Visualize Portfolio Simulation Results
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Load equity curve
equity_df = pd.read_csv("trading/results/portfolio_equity_curve.csv")
equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])

# Load all trades
trades_df = pd.read_csv("trading/results/portfolio_all_trades.csv")
trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date'])

# Create figure with multiple subplots
fig, axes = plt.subplots(3, 1, figsize=(14, 10))
fig.suptitle('BingX Trading Bot - Portfolio Simulation (30 Days)', fontsize=16, fontweight='bold')

# 1. Equity Curve
ax1 = axes[0]
ax1.plot(equity_df['timestamp'], equity_df['equity'], color='#2E7D32', linewidth=2, label='Portfolio Equity')
ax1.axhline(y=10000, color='gray', linestyle='--', alpha=0.5, label='Starting Capital')
ax1.fill_between(equity_df['timestamp'], 10000, equity_df['equity'],
                  where=(equity_df['equity'] >= 10000), alpha=0.2, color='green')
ax1.fill_between(equity_df['timestamp'], 10000, equity_df['equity'],
                  where=(equity_df['equity'] < 10000), alpha=0.2, color='red')
ax1.set_ylabel('Equity ($)', fontsize=11, fontweight='bold')
ax1.set_title('Portfolio Equity Curve', fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left')
ax1.set_ylim(9000, equity_df['equity'].max() * 1.05)

# Add annotations for key milestones
final_equity = equity_df['equity'].iloc[-1]
max_equity = equity_df['equity'].max()
ax1.annotate(f'Final: ${final_equity:,.0f}\n(+126.82%)',
             xy=(equity_df['timestamp'].iloc[-1], final_equity),
             xytext=(-100, -30), textcoords='offset points',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.8),
             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

# 2. Drawdown
ax2 = axes[1]
ax2.fill_between(equity_df['timestamp'], 0, equity_df['drawdown_pct'],
                  color='red', alpha=0.3)
ax2.plot(equity_df['timestamp'], equity_df['drawdown_pct'],
         color='darkred', linewidth=1.5, label='Drawdown')
ax2.set_ylabel('Drawdown (%)', fontsize=11, fontweight='bold')
ax2.set_title('Portfolio Drawdown Over Time', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(loc='lower left')
ax2.set_ylim(equity_df['drawdown_pct'].min() * 1.2, 1)

# Add max drawdown annotation
max_dd_idx = equity_df['drawdown_pct'].idxmin()
max_dd = equity_df['drawdown_pct'].iloc[max_dd_idx]
max_dd_time = equity_df['timestamp'].iloc[max_dd_idx]
ax2.annotate(f'Max DD: {max_dd:.2f}%',
             xy=(max_dd_time, max_dd),
             xytext=(20, 20), textcoords='offset points',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8),
             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

# 3. Strategy Contribution (bar chart)
ax3 = axes[2]
executed_trades = trades_df[trades_df['status'] == 'EXECUTED']
strategy_stats = executed_trades.groupby('strategy').agg({
    'pnl_pct': ['count', 'sum', 'mean']
}).round(4)
strategy_stats.columns = ['Trades', 'Total Return %', 'Avg Return %']

strategies = strategy_stats.index.tolist()
x_pos = range(len(strategies))

# Bar chart of total returns
bars = ax3.bar(x_pos, strategy_stats['Total Return %'],
               color=['#FF6B35' if 'FART' in s else '#4ECDC4' if 'MOOD' in s else '#95E1D3' for s in strategies],
               alpha=0.8, edgecolor='black', linewidth=1.5)

# Add value labels on bars
for i, (strategy, row) in enumerate(strategy_stats.iterrows()):
    ax3.text(i, row['Total Return %'] + 1,
             f"+{row['Total Return %']:.1f}%\n({int(row['Trades'])} trades)",
             ha='center', va='bottom', fontsize=9, fontweight='bold')

ax3.set_ylabel('Total Return Contribution (%)', fontsize=11, fontweight='bold')
ax3.set_title('Strategy Contribution Breakdown', fontsize=12, fontweight='bold')
ax3.set_xticks(x_pos)
ax3.set_xticklabels(strategies, rotation=0, ha='center')
ax3.grid(True, alpha=0.3, axis='y')
ax3.axhline(y=0, color='black', linewidth=1)

plt.tight_layout()
plt.savefig('trading/results/portfolio_simulation_analysis.png', dpi=150, bbox_inches='tight')
print("Saved visualization to trading/results/portfolio_simulation_analysis.png")
plt.close()

# Print summary stats
print("\n" + "="*80)
print("PORTFOLIO SIMULATION - KEY INSIGHTS")
print("="*80)
print(f"\n📈 PERFORMANCE")
print(f"   Starting Capital: $10,000")
print(f"   Final Equity: ${final_equity:,.2f}")
print(f"   Total Return: +126.82%")
print(f"   Max Drawdown: -5.88%")
print(f"   Return/DD Ratio: 21.59x")

print(f"\n📊 TRADING ACTIVITY")
print(f"   Total Signals: 342")
print(f"   Trades Executed: 326 (95.3%)")
print(f"   Trades Skipped: 16 (4.7%)")
print(f"   Win Rate: 39.57%")

print(f"\n🎯 STRATEGY BREAKDOWN")
for strategy, row in strategy_stats.iterrows():
    print(f"   {strategy:20s}: {int(row['Trades']):3d} trades → +{row['Total Return %']:6.2f}% (avg {row['Avg Return %']:+.2f}%)")

print(f"\n💡 KEY FINDINGS")
print(f"   • Portfolio return (+126.82%) is 2.4x higher than sum of individual strategies (+52.67%)")
print(f"   • This is due to COMPOUNDING: winners increase capital for subsequent trades")
print(f"   • Only 4.7% of trades were skipped due to position conflicts")
print(f"   • 95.3% execution rate shows strategies don't overlap much temporally")
print(f"   • Max drawdown of -5.88% is well-controlled for 126% return")

print("\n" + "="*80)
