"""
Visualize TRUE best FARTCOIN strategy using post-filtered trades
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load trades and apply best filter
trades_df = pd.read_csv('results/fartcoin_30m_trade_analysis.csv')

# Best filter combination
filtered = trades_df[
    (trades_df['entry_momentum_7d'] < 0) &
    (trades_df['entry_atr_pct'] < 6) &
    (trades_df['entry_rsi'] < 60)
].copy()

filtered = filtered.sort_values('exit_date').reset_index(drop=True)

print("="*80)
print("FARTCOIN TRUE BEST STRATEGY - POST-FILTERED")
print("="*80)

# Build equity curve
equity = 1.0
equity_curve = [equity]
dates = []

for _, trade in filtered.iterrows():
    equity *= (1 + trade['pnl_pct'] / 100)
    equity_curve.append(equity)
    dates.append(pd.to_datetime(trade['exit_date']))

# Calculate metrics
equity_series = pd.Series(equity_curve)
running_max = equity_series.expanding().max()
drawdown = (equity_series - running_max) / running_max * 100
max_dd = drawdown.min()
total_return = (equity - 1) * 100

winners = len(filtered[filtered['pnl_pct'] > 0])
win_rate = winners / len(filtered) * 100

print(f"\nFinal Results:")
print(f"  Total Trades: {len(filtered)} (from {len(trades_df)} original)")
print(f"  Trades Removed: {len(trades_df) - len(filtered)} ({(1-len(filtered)/len(trades_df))*100:.1f}%)")
print(f"  Win Rate: {win_rate:.1f}%")
print(f"  Total Return: {total_return:.2f}%")
print(f"  Max Drawdown: {max_dd:.2f}%")
print(f"  Final Equity: {equity:.2f}x")
print(f"\nImprovement vs Original:")
print(f"  Return: +{total_return - 170:.2f}%")
print(f"  Max DD: +{max_dd - (-38.10):.2f}%")

# Create visualization
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})

# Equity curve
ax1.plot(range(len(equity_curve)), equity_curve, linewidth=2.5, color='#2E86AB', label='Equity')
ax1.fill_between(range(len(equity_curve)), 1, equity_curve, alpha=0.3, color='#2E86AB')
ax1.axhline(y=1, color='gray', linestyle='--', alpha=0.5, linewidth=1)

# Mark winning and losing trades
for idx, (_, trade) in enumerate(filtered.iterrows()):
    color = 'green' if trade['pnl_pct'] > 0 else 'red'
    marker = '^' if trade['pnl_pct'] > 0 else 'v'
    ax1.scatter(idx+1, equity_curve[idx+1], color=color, marker=marker,
                s=40, alpha=0.7, zorder=5)

ax1.set_title(f'FARTCOIN 30M - BEST Strategy (Post-Filtered)\n' +
              f'Return: {total_return:.2f}% | Max DD: {max_dd:.2f}% | Win Rate: {win_rate:.1f}% | Trades: {len(filtered)}/{len(trades_df)}',
              fontsize=14, fontweight='bold', pad=20)
ax1.set_ylabel('Equity (Multiple of Starting Capital)', fontsize=11)
ax1.set_xlabel('Trade Number', fontsize=11)
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)

# Add strategy info text box
strategy_text = (
    'Strategy: EMA 3/15 SHORT Crossover\n'
    'Original Filter: Mom7d<5% & Mom14d<10%\n'
    'BEST Filter: Mom7d<0 & ATR<6% & RSI<60\n'
    'Risk: SL=3% | TP=5% | Fee=0.01%\n'
    f'Method: Post-filtering ({(1-len(filtered)/len(trades_df))*100:.1f}% trades removed)'
)
ax1.text(0.02, 0.98, strategy_text, transform=ax1.transAxes,
         fontsize=9, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))

# Add comparison box
comparison_text = (
    f'vs Original Strategy:\n'
    f'Return: +{total_return - 170:.1f}%\n'
    f'Max DD: {max_dd - (-38.10):+.1f}%\n'
    f'Final Equity: {equity:.2f}x vs 2.70x'
)
ax1.text(0.98, 0.98, comparison_text, transform=ax1.transAxes,
         fontsize=9, verticalalignment='top', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

# Drawdown
ax2.fill_between(range(len(drawdown)), drawdown, 0, color='red', alpha=0.3)
ax2.plot(range(len(drawdown)), drawdown, color='darkred', linewidth=1.5)
ax2.set_title('Drawdown (%)', fontsize=11, fontweight='bold')
ax2.set_ylabel('Drawdown %', fontsize=10)
ax2.set_xlabel('Trade Number', fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.axhline(y=max_dd, color='red', linestyle='--', alpha=0.5, linewidth=1)
ax2.text(len(drawdown)*0.95, max_dd*0.9, f'Max: {max_dd:.2f}%',
         ha='right', fontsize=9, color='darkred', fontweight='bold')

plt.tight_layout()
plt.savefig('results/fartcoin_TRUE_BEST_equity_curve.png', dpi=300, bbox_inches='tight')
print(f"\n✓ Saved TRUE BEST equity curve to results/fartcoin_TRUE_BEST_equity_curve.png")
print("="*80)
