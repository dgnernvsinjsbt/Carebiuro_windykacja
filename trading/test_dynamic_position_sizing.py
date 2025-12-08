"""
Test dynamic position sizing strategies on FARTCOIN
Reduce size on consecutive losses, increase on consecutive wins
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load filtered trades
trades_df = pd.read_csv('results/fartcoin_30m_trade_analysis.csv')

# Apply best filter
filtered = trades_df[
    (trades_df['entry_momentum_7d'] < 0) &
    (trades_df['entry_atr_pct'] < 6) &
    (trades_df['entry_rsi'] < 60)
].copy()

filtered = filtered.sort_values('exit_date').reset_index(drop=True)

print("="*100)
print("DYNAMIC POSITION SIZING TEST - FARTCOIN")
print("="*100)

def backtest_with_position_sizing(trades, sizing_method='fixed', **params):
    """
    sizing_method options:
    - 'fixed': Always 100% position
    - 'anti_martingale': Increase on wins, decrease on losses
    - 'streak_based': Scale based on consecutive win/loss streak
    """

    equity = 1.0
    equity_curve = [equity]
    position_size = 1.0  # Start with 100%
    consecutive_wins = 0
    consecutive_losses = 0

    position_sizes_used = []

    for _, trade in trades.iterrows():
        # Determine position size based on method
        if sizing_method == 'fixed':
            position_size = 1.0

        elif sizing_method == 'anti_martingale':
            # Increase on wins, decrease on losses
            win_multiplier = params.get('win_mult', 1.2)
            loss_multiplier = params.get('loss_mult', 0.8)
            min_size = params.get('min_size', 0.25)
            max_size = params.get('max_size', 2.0)

            if consecutive_wins > 0:
                position_size = min(position_size * (win_multiplier ** consecutive_wins), max_size)
            elif consecutive_losses > 0:
                position_size = max(position_size * (loss_multiplier ** consecutive_losses), min_size)
            else:
                position_size = 1.0

        elif sizing_method == 'streak_based':
            # Simple: reduce 20% per consecutive loss, increase 20% per win
            win_step = params.get('win_step', 0.2)
            loss_step = params.get('loss_step', 0.2)
            min_size = params.get('min_size', 0.25)
            max_size = params.get('max_size', 2.0)

            if consecutive_wins > 0:
                position_size = min(1.0 + (consecutive_wins * win_step), max_size)
            elif consecutive_losses > 0:
                position_size = max(1.0 - (consecutive_losses * loss_step), min_size)
            else:
                position_size = 1.0

        elif sizing_method == 'gradual':
            # Gradual adjustment
            adjustment = params.get('adjustment', 0.15)
            min_size = params.get('min_size', 0.4)
            max_size = params.get('max_size', 1.5)

            if consecutive_wins > 0:
                position_size = min(position_size + adjustment, max_size)
            elif consecutive_losses > 0:
                position_size = max(position_size - adjustment, min_size)

        position_sizes_used.append(position_size)

        # Calculate P&L with position sizing
        trade_pnl = trade['pnl_pct'] * position_size
        equity *= (1 + trade_pnl / 100)
        equity_curve.append(equity)

        # Update streak counters
        if trade['pnl_pct'] > 0:
            consecutive_wins += 1
            consecutive_losses = 0
        else:
            consecutive_losses += 1
            consecutive_wins = 0

    # Calculate metrics
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_dd = drawdown.min()
    total_return = (equity - 1) * 100

    return {
        'equity_curve': equity_curve,
        'drawdown': drawdown,
        'total_return': total_return,
        'max_dd': max_dd,
        'final_equity': equity,
        'position_sizes': position_sizes_used
    }

# Test different position sizing strategies
strategies = [
    ('Fixed 100%', 'fixed', {}),

    ('Anti-Martingale (1.2x/0.8x)', 'anti_martingale', {
        'win_mult': 1.2, 'loss_mult': 0.8, 'min_size': 0.25, 'max_size': 2.0
    }),

    ('Anti-Martingale (1.15x/0.85x)', 'anti_martingale', {
        'win_mult': 1.15, 'loss_mult': 0.85, 'min_size': 0.3, 'max_size': 1.8
    }),

    ('Streak-Based (20% steps)', 'streak_based', {
        'win_step': 0.2, 'loss_step': 0.2, 'min_size': 0.25, 'max_size': 2.0
    }),

    ('Streak-Based (15% steps)', 'streak_based', {
        'win_step': 0.15, 'loss_step': 0.15, 'min_size': 0.3, 'max_size': 1.8
    }),

    ('Gradual (15% adjust)', 'gradual', {
        'adjustment': 0.15, 'min_size': 0.4, 'max_size': 1.5
    }),

    ('Gradual (10% adjust)', 'gradual', {
        'adjustment': 0.10, 'min_size': 0.5, 'max_size': 1.3
    }),

    ('Conservative (Win only)', 'anti_martingale', {
        'win_mult': 1.1, 'loss_mult': 1.0, 'min_size': 0.5, 'max_size': 1.5
    }),
]

results = []
equity_curves = {}

for name, method, params in strategies:
    result = backtest_with_position_sizing(filtered, method, **params)

    results.append({
        'strategy': name,
        'return': result['total_return'],
        'max_dd': result['max_dd'],
        'final_equity': result['final_equity'],
        'return_improvement': result['total_return'] - 288.40,
        'dd_improvement': result['max_dd'] - (-30.45)
    })

    equity_curves[name] = result['equity_curve']

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return', ascending=False)

print("\n" + "="*100)
print("POSITION SIZING STRATEGY RESULTS")
print("="*100)
print(f"\n{'Strategy':<30} {'Return':<12} {'Max DD':<12} {'Final Eq':<12} {'Ret Δ':<12} {'DD Δ':<12}")
print("-"*100)

for _, row in results_df.iterrows():
    print(f"{row['strategy']:<30} {row['return']:<11.2f}% {row['max_dd']:<11.2f}% {row['final_equity']:<11.2f}x {row['return_improvement']:>+11.2f}% {row['dd_improvement']:>+11.2f}%")

print("\n" + "="*100)
print("TOP 3 STRATEGIES")
print("="*100)

for idx, row in results_df.head(3).iterrows():
    print(f"\n#{idx+1}: {row['strategy']}")
    print(f"  Total Return: {row['return']:.2f}% ({row['return_improvement']:+.2f}% vs Fixed)")
    print(f"  Max Drawdown: {row['max_dd']:.2f}% ({row['dd_improvement']:+.2f}% vs Fixed)")
    print(f"  Final Equity: {row['final_equity']:.2f}x (Fixed: 3.88x)")

    # Calculate sharpe-like ratio
    ret_dd_ratio = row['return'] / abs(row['max_dd'])
    print(f"  Return/DD Ratio: {ret_dd_ratio:.2f}")

# Visualize top 3 strategies
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']

for idx, (_, row) in enumerate(results_df.head(4).iterrows()):
    strategy = row['strategy']
    ec = equity_curves[strategy]
    ax1.plot(range(len(ec)), ec, linewidth=2, label=strategy, color=colors[idx])

ax1.axhline(y=1, color='gray', linestyle='--', alpha=0.5, linewidth=1)
ax1.set_title('FARTCOIN - Position Sizing Strategy Comparison', fontsize=14, fontweight='bold', pad=20)
ax1.set_ylabel('Equity (Multiple of Starting Capital)', fontsize=11)
ax1.set_xlabel('Trade Number', fontsize=11)
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)

# Drawdown comparison
for idx, (_, row) in enumerate(results_df.head(4).iterrows()):
    strategy = row['strategy']
    ec = equity_curves[strategy]
    equity_series = pd.Series(ec)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    ax2.plot(range(len(drawdown)), drawdown, linewidth=1.5, label=strategy, color=colors[idx])

ax2.set_title('Drawdown Comparison', fontsize=11, fontweight='bold')
ax2.set_ylabel('Drawdown %', fontsize=10)
ax2.set_xlabel('Trade Number', fontsize=10)
ax2.legend(loc='lower left', fontsize=9)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('results/fartcoin_position_sizing_comparison.png', dpi=300, bbox_inches='tight')
print("\n✓ Saved comparison chart to results/fartcoin_position_sizing_comparison.png")

# Save results
results_df.to_csv('results/position_sizing_results.csv', index=False)
print("✓ Saved results to results/position_sizing_results.csv")

print("\n" + "="*100)
print("RECOMMENDATION")
print("="*100)

best = results_df.iloc[0]
print(f"\nBest Strategy: {best['strategy']}")
print(f"  Improves return by {best['return_improvement']:+.2f}%")
print(f"  Improves drawdown by {best['dd_improvement']:+.2f}%")
print(f"  Final return: {best['return']:.2f}%")
print(f"  Max drawdown: {best['max_dd']:.2f}%")

print("\n" + "="*100)
