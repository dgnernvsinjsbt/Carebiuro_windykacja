"""
Test simple gradual position sizing: +10%/-10% per trade
Responsive to market regimes (3 phases observed: up, down, up)
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
print("GRADUAL POSITION SIZING TEST")
print("="*100)

def backtest_gradual(trades, win_adj, loss_adj, min_cap, max_cap):
    """
    Simple gradual adjustment:
    - Each win: size += win_adj
    - Each loss: size -= loss_adj
    - Capped at min_cap and max_cap
    """
    equity = 1.0
    equity_curve = [equity]
    position_size = 1.0
    position_sizes = [position_size]

    for _, trade in trades.iterrows():
        # Apply trade with current position size
        trade_pnl = trade['pnl_pct'] * position_size
        equity *= (1 + trade_pnl / 100)
        equity_curve.append(equity)

        # Adjust position size for next trade
        if trade['pnl_pct'] > 0:
            position_size = min(position_size + win_adj, max_cap)
        else:
            position_size = max(position_size - loss_adj, min_cap)

        position_sizes.append(position_size)

    # Calculate metrics
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_dd = drawdown.min()
    total_return = (equity - 1) * 100

    return {
        'equity_curve': equity_curve,
        'position_sizes': position_sizes,
        'drawdown': drawdown,
        'total_return': total_return,
        'max_dd': max_dd,
        'final_equity': equity,
        'rr_ratio': total_return / abs(max_dd)
    }

# Test various gradual strategies
strategies = [
    ('Fixed 100%', 0, 0, 1.0, 1.0),
    ('±10% (0.5-1.5x)', 0.10, 0.10, 0.5, 1.5),
    ('±10% (0.6-1.4x)', 0.10, 0.10, 0.6, 1.4),
    ('±10% (0.7-1.3x)', 0.10, 0.10, 0.7, 1.3),
    ('±15% (0.5-1.5x)', 0.15, 0.15, 0.5, 1.5),
    ('±15% (0.6-1.4x)', 0.15, 0.15, 0.6, 1.4),
    ('±8% (0.5-1.5x)', 0.08, 0.08, 0.5, 1.5),
    ('+15%/-10% (0.5-1.5x)', 0.15, 0.10, 0.5, 1.5),
    ('+10%/-15% (0.5-1.5x)', 0.10, 0.15, 0.5, 1.5),
    ('+12%/-8% (0.5-1.5x)', 0.12, 0.08, 0.5, 1.5),
    ('+10%/-5% (0.5-1.5x)', 0.10, 0.05, 0.5, 1.5),
    ('+20%/-10% (0.5-2.0x)', 0.20, 0.10, 0.5, 2.0),
    ('+15%/-5% (0.6-1.8x)', 0.15, 0.05, 0.6, 1.8),
]

results = []
equity_curves = {}
position_size_histories = {}

for name, win_adj, loss_adj, min_cap, max_cap in strategies:
    result = backtest_gradual(filtered, win_adj, loss_adj, min_cap, max_cap)

    results.append({
        'strategy': name,
        'return': result['total_return'],
        'max_dd': result['max_dd'],
        'final_equity': result['final_equity'],
        'rr_ratio': result['rr_ratio'],
        'return_vs_fixed': result['total_return'] - 288.40,
        'dd_vs_fixed': result['max_dd'] - (-30.45)
    })

    equity_curves[name] = result['equity_curve']
    position_size_histories[name] = result['position_sizes']

results_df = pd.DataFrame(results)

print("\n" + "="*100)
print("RESULTS BY RISK-REWARD RATIO")
print("="*100)

results_df_sorted = results_df.sort_values('rr_ratio', ascending=False)
print(f"\n{'Strategy':<25} {'Return':<12} {'Max DD':<12} {'R:R Ratio':<10} {'Ret Δ':<12} {'DD Δ':<12}")
print("-"*100)

for _, row in results_df_sorted.iterrows():
    print(f"{row['strategy']:<25} {row['return']:<11.2f}% {row['max_dd']:<11.2f}% {row['rr_ratio']:<9.2f} {row['return_vs_fixed']:>+11.2f}% {row['dd_vs_fixed']:>+11.2f}%")

print("\n" + "="*100)
print("TOP 3 RECOMMENDATIONS")
print("="*100)

for idx, (_, row) in enumerate(results_df_sorted.head(3).iterrows(), 1):
    print(f"\n#{idx}: {row['strategy']}")
    print(f"  Return: {row['return']:.2f}% ({row['return_vs_fixed']:+.2f}% vs Fixed)")
    print(f"  Max DD: {row['max_dd']:.2f}% ({row['dd_vs_fixed']:+.2f}% vs Fixed)")
    print(f"  R:R Ratio: {row['rr_ratio']:.2f}")
    print(f"  Final Equity: {row['final_equity']:.2f}x")

# Visualize top 4
fig = plt.figure(figsize=(16, 12))
gs = fig.add_gridspec(3, 2, height_ratios=[2, 1, 1])

ax1 = fig.add_subplot(gs[0, :])  # Equity curve (full width)
ax2 = fig.add_subplot(gs[1, :])  # Position size (full width)
ax3 = fig.add_subplot(gs[2, 0])  # Drawdown
ax4 = fig.add_subplot(gs[2, 1])  # Return vs DD scatter

colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']

# Plot top 5 equity curves
for idx, (_, row) in enumerate(results_df_sorted.head(5).iterrows()):
    strategy = row['strategy']
    ec = equity_curves[strategy]
    ax1.plot(range(len(ec)), ec, linewidth=2, label=strategy, color=colors[idx], alpha=0.9)

ax1.axhline(y=1, color='gray', linestyle='--', alpha=0.5, linewidth=1)
ax1.set_title('FARTCOIN - Gradual Position Sizing Comparison (Top 5 by R:R)',
              fontsize=14, fontweight='bold', pad=20)
ax1.set_ylabel('Equity Multiple', fontsize=11)
ax1.set_xlabel('Trade Number', fontsize=11)
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)

# Plot position sizes for top 3
for idx, (_, row) in enumerate(results_df_sorted.head(3).iterrows()):
    strategy = row['strategy']
    if strategy == 'Fixed 100%':
        continue
    ps = position_size_histories[strategy]
    ax2.plot(range(len(ps)), ps, linewidth=1.5, label=strategy, color=colors[idx], alpha=0.8)

ax2.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
ax2.set_title('Position Size Over Time', fontsize=11, fontweight='bold')
ax2.set_ylabel('Position Size (x)', fontsize=10)
ax2.set_xlabel('Trade Number', fontsize=10)
ax2.legend(loc='best', fontsize=9)
ax2.grid(True, alpha=0.3)

# Drawdown comparison
for idx, (_, row) in enumerate(results_df_sorted.head(4).iterrows()):
    strategy = row['strategy']
    ec = equity_curves[strategy]
    equity_series = pd.Series(ec)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    ax3.plot(range(len(drawdown)), drawdown, linewidth=1.5, label=strategy, color=colors[idx])

ax3.set_title('Drawdown Comparison', fontsize=11, fontweight='bold')
ax3.set_ylabel('Drawdown %', fontsize=10)
ax3.set_xlabel('Trade Number', fontsize=10)
ax3.legend(loc='lower left', fontsize=8)
ax3.grid(True, alpha=0.3)

# Scatter: Return vs DD
for idx, (_, row) in enumerate(results_df.iterrows()):
    ax4.scatter(abs(row['max_dd']), row['return'], s=100, alpha=0.7, color=colors[min(idx, len(colors)-1)])
    ax4.annotate(row['strategy'], (abs(row['max_dd']), row['return']),
                fontsize=7, ha='left', alpha=0.7)

ax4.set_xlabel('Max Drawdown (abs %)', fontsize=10)
ax4.set_ylabel('Total Return %', fontsize=10)
ax4.set_title('Risk-Return Scatter', fontsize=11, fontweight='bold')
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('results/gradual_sizing_analysis.png', dpi=300, bbox_inches='tight')
print("\n✓ Saved analysis to results/gradual_sizing_analysis.png")

results_df.to_csv('results/gradual_sizing_results.csv', index=False)
print("✓ Saved results to results/gradual_sizing_results.csv")

print("\n" + "="*100)
print("FINAL VERDICT")
print("="*100)

best = results_df_sorted.iloc[0]
print(f"\nBest Strategy: {best['strategy']}")
print(f"  Achieves {best['return']:.2f}% return with {best['max_dd']:.2f}% max DD")
print(f"  R:R Ratio: {best['rr_ratio']:.2f} (return per unit of risk)")
print(f"  vs Fixed 100%: {best['return_vs_fixed']:+.2f}% return, {best['dd_vs_fixed']:+.2f}% DD")

print("\n" + "="*100)
