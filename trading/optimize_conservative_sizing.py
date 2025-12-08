"""
Optimize the "Conservative (Win only)" position sizing strategy
Test various win multipliers and caps
"""

import pandas as pd
import numpy as np

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
print("OPTIMIZING CONSERVATIVE POSITION SIZING")
print("="*100)

def backtest_conservative(trades, win_mult=1.1, max_cap=1.5, loss_mult=1.0, min_size=0.5):
    """
    Conservative sizing: increase on wins, reset/maintain on losses
    """
    equity = 1.0
    equity_curve = [equity]
    position_size = 1.0
    consecutive_wins = 0
    consecutive_losses = 0

    for _, trade in trades.iterrows():
        # Calculate position size based on streak
        if consecutive_wins > 0:
            position_size = min(win_mult ** consecutive_wins, max_cap)
        elif consecutive_losses > 0:
            position_size = max(loss_mult ** consecutive_losses, min_size)
        else:
            position_size = 1.0

        # Apply trade P&L
        trade_pnl = trade['pnl_pct'] * position_size
        equity *= (1 + trade_pnl / 100)
        equity_curve.append(equity)

        # Update streaks
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
        'total_return': total_return,
        'max_dd': max_dd,
        'final_equity': equity,
        'rr_ratio': total_return / abs(max_dd)
    }

# Test grid of parameters
variations = []

# Test different win multipliers and caps
for win_mult in [1.05, 1.08, 1.10, 1.12, 1.15, 1.20]:
    for max_cap in [1.3, 1.5, 1.8, 2.0, 2.5, 3.0]:
        result = backtest_conservative(filtered, win_mult=win_mult, max_cap=max_cap, loss_mult=1.0)
        variations.append({
            'strategy': f'Win {win_mult}x Cap {max_cap}x',
            'win_mult': win_mult,
            'max_cap': max_cap,
            'loss_mult': 1.0,
            'return': result['total_return'],
            'max_dd': result['max_dd'],
            'final_equity': result['final_equity'],
            'rr_ratio': result['rr_ratio']
        })

# Also test slight loss reduction variants
for win_mult in [1.10, 1.15]:
    for loss_mult in [0.95, 0.98]:
        for max_cap in [1.5, 2.0, 2.5]:
            result = backtest_conservative(filtered, win_mult=win_mult, max_cap=max_cap,
                                         loss_mult=loss_mult, min_size=0.7)
            variations.append({
                'strategy': f'Win {win_mult}x Loss {loss_mult}x Cap {max_cap}x',
                'win_mult': win_mult,
                'max_cap': max_cap,
                'loss_mult': loss_mult,
                'return': result['total_return'],
                'max_dd': result['max_dd'],
                'final_equity': result['final_equity'],
                'rr_ratio': result['rr_ratio']
            })

results_df = pd.DataFrame(variations)

# Add baseline
baseline = backtest_conservative(filtered, win_mult=1.0, max_cap=1.0, loss_mult=1.0)
results_df = pd.concat([pd.DataFrame([{
    'strategy': 'Fixed 100% (Baseline)',
    'win_mult': 1.0,
    'max_cap': 1.0,
    'loss_mult': 1.0,
    'return': baseline['total_return'],
    'max_dd': baseline['max_dd'],
    'final_equity': baseline['final_equity'],
    'rr_ratio': baseline['rr_ratio']
}]), results_df], ignore_index=True)

# Sort by R:R ratio
results_df = results_df.sort_values('rr_ratio', ascending=False)

print("\n" + "="*100)
print("TOP 20 STRATEGIES BY RISK-REWARD RATIO")
print("="*100)
print(f"\n{'Strategy':<40} {'Return':<12} {'Max DD':<12} {'R:R Ratio':<10} {'Final Eq':<10}")
print("-"*100)

for _, row in results_df.head(20).iterrows():
    print(f"{row['strategy']:<40} {row['return']:<11.2f}% {row['max_dd']:<11.2f}% {row['rr_ratio']:<9.2f} {row['final_equity']:<9.2f}x")

print("\n" + "="*100)
print("BEST BY ABSOLUTE RETURN")
print("="*100)

best_return = results_df.sort_values('return', ascending=False).head(10)
print(f"\n{'Strategy':<40} {'Return':<12} {'Max DD':<12} {'R:R Ratio':<10}")
print("-"*100)

for _, row in best_return.iterrows():
    print(f"{row['strategy']:<40} {row['return']:<11.2f}% {row['max_dd']:<11.2f}% {row['rr_ratio']:<9.2f}")

print("\n" + "="*100)
print("BEST BY LOWEST DRAWDOWN (while still beating baseline return)")
print("="*100)

# Filter for strategies that beat baseline return
better_than_baseline = results_df[results_df['return'] > baseline['total_return']].copy()
better_than_baseline = better_than_baseline.sort_values('max_dd', ascending=False)  # Higher DD is better (less negative)

print(f"\n{'Strategy':<40} {'Return':<12} {'Max DD':<12} {'R:R Ratio':<10}")
print("-"*100)

for _, row in better_than_baseline.head(10).iterrows():
    print(f"{row['strategy']:<40} {row['return']:<11.2f}% {row['max_dd']:<11.2f}% {row['rr_ratio']:<9.2f}")

print("\n" + "="*100)
print("FINAL RECOMMENDATION")
print("="*100)

best = results_df.iloc[0]
print(f"\nBEST Strategy: {best['strategy']}")
print(f"  Return: {best['return']:.2f}%")
print(f"  Max Drawdown: {best['max_dd']:.2f}%")
print(f"  Risk-Reward Ratio: {best['rr_ratio']:.2f}")
print(f"  Final Equity: {best['final_equity']:.2f}x")
print(f"\nvs Baseline (Fixed 100%):")
print(f"  Return improvement: +{best['return'] - baseline['total_return']:.2f}%")
print(f"  Drawdown change: {best['max_dd'] - baseline['max_dd']:+.2f}%")

# Find "sweet spot" - good return with better DD than baseline
sweet_spot = better_than_baseline[(better_than_baseline['max_dd'] > baseline['max_dd'])].iloc[0] if len(better_than_baseline[better_than_baseline['max_dd'] > baseline['max_dd']]) > 0 else None

if sweet_spot is not None:
    print(f"\nSWEET SPOT (Better return + Better DD): {sweet_spot['strategy']}")
    print(f"  Return: {sweet_spot['return']:.2f}% (+{sweet_spot['return'] - baseline['total_return']:.2f}% vs baseline)")
    print(f"  Max Drawdown: {sweet_spot['max_dd']:.2f}% ({sweet_spot['max_dd'] - baseline['max_dd']:+.2f}% vs baseline)")
    print(f"  Risk-Reward Ratio: {sweet_spot['rr_ratio']:.2f}")

# Save results
results_df.to_csv('results/conservative_sizing_optimization.csv', index=False)
print("\n✓ Saved optimization results to results/conservative_sizing_optimization.csv")

print("\n" + "="*100)
