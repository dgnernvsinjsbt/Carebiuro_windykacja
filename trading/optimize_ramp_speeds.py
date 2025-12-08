"""
Optimize ramp speeds for position sizing with fixed 0.5x-2.0x caps
Test various win/loss adjustment rates
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load filtered trades
trades_df = pd.read_csv('results/fartcoin_30m_trade_analysis.csv')
filtered = trades_df[
    (trades_df['entry_momentum_7d'] < 0) &
    (trades_df['entry_atr_pct'] < 6) &
    (trades_df['entry_rsi'] < 60)
].copy()
filtered = filtered.sort_values('exit_date').reset_index(drop=True)

print("="*100)
print("OPTIMIZING RAMP SPEEDS - Fixed Caps (0.5x - 2.0x)")
print("="*100)

def backtest_gradual(trades, win_adj, loss_adj, min_cap=0.5, max_cap=2.0):
    """Simple gradual position sizing"""
    equity = 1.0
    position_size = 1.0

    for _, trade in trades.iterrows():
        trade_pnl = trade['pnl_pct'] * position_size
        equity *= (1 + trade_pnl / 100)

        if trade['pnl_pct'] > 0:
            position_size = min(position_size + win_adj, max_cap)
        else:
            position_size = max(position_size - loss_adj, min_cap)

    # Calculate metrics
    equity_curve = []
    position_size = 1.0
    equity_temp = 1.0
    equity_curve.append(equity_temp)

    for _, trade in trades.iterrows():
        trade_pnl = trade['pnl_pct'] * position_size
        equity_temp *= (1 + trade_pnl / 100)
        equity_curve.append(equity_temp)

        if trade['pnl_pct'] > 0:
            position_size = min(position_size + win_adj, max_cap)
        else:
            position_size = max(position_size - loss_adj, min_cap)

    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_dd = drawdown.min()
    total_return = (equity - 1) * 100

    return {
        'total_return': total_return,
        'max_dd': max_dd,
        'final_equity': equity,
        'rr_ratio': total_return / abs(max_dd),
        'equity_curve': equity_curve
    }

# Test grid of ramp speeds
win_speeds = [0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.22, 0.25, 0.30, 0.35]
loss_speeds = [0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20]

results = []

print("\nTesting grid of ramp speeds...")
for win_adj in win_speeds:
    for loss_adj in loss_speeds:
        result = backtest_gradual(filtered, win_adj, loss_adj)
        results.append({
            'win_adj': win_adj,
            'loss_adj': loss_adj,
            'strategy': f'+{int(win_adj*100)}%/-{int(loss_adj*100)}%',
            'return': result['total_return'],
            'max_dd': result['max_dd'],
            'final_equity': result['final_equity'],
            'rr_ratio': result['rr_ratio'],
            'equity_curve': result['equity_curve']
        })

results_df = pd.DataFrame(results)

# Add baseline
baseline_result = backtest_gradual(filtered, 0, 0)
baseline = {
    'win_adj': 0,
    'loss_adj': 0,
    'strategy': 'Fixed 100%',
    'return': baseline_result['total_return'],
    'max_dd': baseline_result['max_dd'],
    'final_equity': baseline_result['final_equity'],
    'rr_ratio': baseline_result['rr_ratio'],
    'equity_curve': baseline_result['equity_curve']
}

results_df = pd.concat([pd.DataFrame([baseline]), results_df], ignore_index=True)
results_df = results_df.sort_values('rr_ratio', ascending=False)

print("\n" + "="*100)
print("TOP 20 STRATEGIES BY RISK-REWARD RATIO")
print("="*100)
print(f"\n{'Strategy':<20} {'Win%':<8} {'Loss%':<8} {'Return':<12} {'Max DD':<12} {'R:R':<8} {'Final Eq':<10}")
print("-"*100)

for _, row in results_df.head(20).iterrows():
    print(f"{row['strategy']:<20} {row['win_adj']*100:<7.0f}% {row['loss_adj']*100:<7.0f}% "
          f"{row['return']:<11.2f}% {row['max_dd']:<11.2f}% {row['rr_ratio']:<7.2f} {row['final_equity']:<9.2f}x")

print("\n" + "="*100)
print("TOP 10 BY ABSOLUTE RETURN")
print("="*100)

best_return = results_df.sort_values('return', ascending=False).head(10)
print(f"\n{'Strategy':<20} {'Return':<12} {'Max DD':<12} {'R:R':<8}")
print("-"*75)

for _, row in best_return.iterrows():
    print(f"{row['strategy']:<20} {row['return']:<11.2f}% {row['max_dd']:<11.2f}% {row['rr_ratio']:<7.2f}")

print("\n" + "="*100)
print("BEST WITH LOWER DRAWDOWN (DD better than -45%)")
print("="*100)

low_dd = results_df[results_df['max_dd'] > -45].sort_values('return', ascending=False).head(10)
print(f"\n{'Strategy':<20} {'Return':<12} {'Max DD':<12} {'R:R':<8}")
print("-"*75)

for _, row in low_dd.iterrows():
    print(f"{row['strategy']:<20} {row['return']:<11.2f}% {row['max_dd']:<11.2f}% {row['rr_ratio']:<7.2f}")

# Create heatmap
print("\n" + "="*100)
print("HEATMAP ANALYSIS")
print("="*100)

# Pivot tables for visualization
pivot_return = results_df.pivot_table(values='return', index='loss_adj', columns='win_adj')
pivot_dd = results_df.pivot_table(values='max_dd', index='loss_adj', columns='win_adj')
pivot_rr = results_df.pivot_table(values='rr_ratio', index='loss_adj', columns='win_adj')

# Create visualization
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Heatmap 1: R:R Ratio
im1 = axes[0, 0].imshow(pivot_rr, cmap='RdYlGn', aspect='auto')
axes[0, 0].set_title('Risk-Reward Ratio Heatmap', fontsize=12, fontweight='bold')
axes[0, 0].set_xlabel('Win Adjustment %')
axes[0, 0].set_ylabel('Loss Adjustment %')
axes[0, 0].set_xticks(range(len(pivot_rr.columns)))
axes[0, 0].set_xticklabels([f'{int(x*100)}' for x in pivot_rr.columns], rotation=45)
axes[0, 0].set_yticks(range(len(pivot_rr.index)))
axes[0, 0].set_yticklabels([f'{int(x*100)}' for x in pivot_rr.index])
fig.colorbar(im1, ax=axes[0, 0], label='R:R Ratio')

# Heatmap 2: Total Return
im2 = axes[0, 1].imshow(pivot_return, cmap='YlOrRd', aspect='auto')
axes[0, 1].set_title('Total Return % Heatmap', fontsize=12, fontweight='bold')
axes[0, 1].set_xlabel('Win Adjustment %')
axes[0, 1].set_ylabel('Loss Adjustment %')
axes[0, 1].set_xticks(range(len(pivot_return.columns)))
axes[0, 1].set_xticklabels([f'{int(x*100)}' for x in pivot_return.columns], rotation=45)
axes[0, 1].set_yticks(range(len(pivot_return.index)))
axes[0, 1].set_yticklabels([f'{int(x*100)}' for x in pivot_return.index])
fig.colorbar(im2, ax=axes[0, 1], label='Return %')

# Heatmap 3: Max DD
im3 = axes[1, 0].imshow(pivot_dd, cmap='RdYlGn_r', aspect='auto')
axes[1, 0].set_title('Max Drawdown % Heatmap', fontsize=12, fontweight='bold')
axes[1, 0].set_xlabel('Win Adjustment %')
axes[1, 0].set_ylabel('Loss Adjustment %')
axes[1, 0].set_xticks(range(len(pivot_dd.columns)))
axes[1, 0].set_xticklabels([f'{int(x*100)}' for x in pivot_dd.columns], rotation=45)
axes[1, 0].set_yticks(range(len(pivot_dd.index)))
axes[1, 0].set_yticklabels([f'{int(x*100)}' for x in pivot_dd.index])
fig.colorbar(im3, ax=axes[1, 0], label='Max DD %')

# Equity curves for top 5
ax4 = axes[1, 1]
colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']

for idx, (_, row) in enumerate(results_df.head(6).iterrows()):
    if row['strategy'] == 'Fixed 100%':
        continue
    ec = row['equity_curve']
    ax4.plot(range(len(ec)), ec, linewidth=2, label=row['strategy'],
             color=colors[min(idx, len(colors)-1)], alpha=0.9)

ax4.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
ax4.set_title('Equity Curves - Top 5 by R:R', fontsize=12, fontweight='bold')
ax4.set_xlabel('Trade Number')
ax4.set_ylabel('Equity Multiple')
ax4.legend(loc='upper left', fontsize=8)
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('results/ramp_speed_optimization.png', dpi=300, bbox_inches='tight')
print("\n✓ Saved heatmaps to results/ramp_speed_optimization.png")

# Save results
results_df.to_csv('results/ramp_speed_results.csv', index=False)
print("✓ Saved results to results/ramp_speed_results.csv")

print("\n" + "="*100)
print("FINAL RECOMMENDATIONS")
print("="*100)

best = results_df.iloc[0]
print(f"\n🏆 BEST R:R: {best['strategy']}")
print(f"   Return: {best['return']:.2f}%")
print(f"   Max DD: {best['max_dd']:.2f}%")
print(f"   R:R Ratio: {best['rr_ratio']:.2f}")

best_ret = results_df.sort_values('return', ascending=False).iloc[0]
print(f"\n💰 HIGHEST RETURN: {best_ret['strategy']}")
print(f"   Return: {best_ret['return']:.2f}%")
print(f"   Max DD: {best_ret['max_dd']:.2f}%")
print(f"   R:R Ratio: {best_ret['rr_ratio']:.2f}")

balanced = results_df[(results_df['max_dd'] > -45) & (results_df['return'] > 400)].sort_values('rr_ratio', ascending=False)
if len(balanced) > 0:
    bal = balanced.iloc[0]
    print(f"\n⚖️  BALANCED (High return + DD<45%): {bal['strategy']}")
    print(f"   Return: {bal['return']:.2f}%")
    print(f"   Max DD: {bal['max_dd']:.2f}%")
    print(f"   R:R Ratio: {bal['rr_ratio']:.2f}")

print("\n" + "="*100)
