#!/usr/bin/env python3
"""
Comprehensive position sizing analysis - test many combinations
"""
import pandas as pd
import numpy as np

print("="*100)
print("COMPREHENSIVE POSITION SIZING ANALYSIS")
print("="*100)

# Load all trades
df = pd.read_csv('4_coin_portfolio_all_trades.csv')
df['entry_time'] = pd.to_datetime(df['entry_time'])
df = df.sort_values('entry_time').reset_index(drop=True)

print(f"\n📊 Data: {len(df)} trades, {df['entry_time'].min()} to {df['entry_time'].max()}")

def calculate_metrics(equity_curve):
    """Calculate return, max DD, and Return/DD ratio"""
    eq_series = pd.Series(equity_curve)
    total_return = ((eq_series.iloc[-1] - eq_series.iloc[0]) / eq_series.iloc[0]) * 100
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    return {
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'final_equity': eq_series.iloc[-1]
    }

def backtest_scaling(df, scale_step, floor):
    """
    Backtest with scaling down after loss

    scale_step: % to reduce after each loss (e.g., 0.10 = 10%)
    floor: minimum position size (e.g., 0.50 = 50%)
    """
    equity = 100.0
    equity_curve = [equity]
    current_scale = 1.0
    max_consecutive_losses = 0
    consecutive_losses = 0

    for _, trade in df.iterrows():
        position_size = current_scale * equity
        pnl_dollar = position_size * (trade['pnl_pct'] / 100)
        equity += pnl_dollar
        equity_curve.append(equity)

        if pnl_dollar > 0:
            consecutive_losses = 0
            current_scale = 1.0  # Reset to 100%
        else:
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            current_scale = max(current_scale - scale_step, floor)

    metrics = calculate_metrics(equity_curve)
    metrics['max_consecutive_losses'] = max_consecutive_losses
    return metrics

def backtest_updown(df, scale_step, floor, ceiling):
    """
    Backtest with scaling UP after win, DOWN after loss
    """
    equity = 100.0
    equity_curve = [equity]
    current_scale = 1.0
    max_consecutive_losses = 0
    consecutive_losses = 0

    for _, trade in df.iterrows():
        position_size = current_scale * equity
        pnl_dollar = position_size * (trade['pnl_pct'] / 100)
        equity += pnl_dollar
        equity_curve.append(equity)

        if pnl_dollar > 0:
            consecutive_losses = 0
            current_scale = min(current_scale + scale_step, ceiling)
        else:
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            current_scale = max(current_scale - scale_step, floor)

    metrics = calculate_metrics(equity_curve)
    metrics['max_consecutive_losses'] = max_consecutive_losses
    return metrics

# Test configurations
results = []

print("\n🔄 Testing strategies...")

# 1. BASELINE
equity_curve = [100.0]
equity = 100.0
for _, trade in df.iterrows():
    pnl_dollar = equity * (trade['pnl_pct'] / 100)
    equity += pnl_dollar
    equity_curve.append(equity)

metrics = calculate_metrics(equity_curve)
results.append({
    'strategy': 'Baseline (100% fixed)',
    'type': 'baseline',
    'scale_step': 0,
    'floor': 1.0,
    'ceiling': 1.0,
    'return': metrics['total_return'],
    'max_dd': metrics['max_dd'],
    'return_dd': metrics['return_dd'],
    'final_equity': metrics['final_equity']
})

# 2. SCALE DOWN strategies (various step sizes and floors)
scale_steps = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]  # 5%, 10%, 15%, 20%, 25%, 30%
floors = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70]  # 20%, 30%, 40%, 50%, 60%, 70%

print(f"   Testing {len(scale_steps)} scale steps × {len(floors)} floors = {len(scale_steps) * len(floors)} combinations")

for step in scale_steps:
    for floor in floors:
        metrics = backtest_scaling(df, step, floor)
        results.append({
            'strategy': f'Scale Down ({int(step*100)}% step, {int(floor*100)}% floor)',
            'type': 'scale_down',
            'scale_step': step,
            'floor': floor,
            'ceiling': 1.0,
            'return': metrics['total_return'],
            'max_dd': metrics['max_dd'],
            'return_dd': metrics['return_dd'],
            'final_equity': metrics['final_equity']
        })

# 3. UP/DOWN strategies (various configurations)
ceilings = [1.0, 1.2, 1.5, 2.0]  # 100%, 120%, 150%, 200%

print(f"   Testing {len(scale_steps)} scale steps × {len(floors)} floors × {len(ceilings)} ceilings for Up/Down")

for step in [0.05, 0.10, 0.15, 0.20]:  # Limit to avoid too many combinations
    for floor in [0.30, 0.40, 0.50]:
        for ceiling in ceilings:
            metrics = backtest_updown(df, step, floor, ceiling)
            results.append({
                'strategy': f'Up/Down ({int(step*100)}% step, {int(floor*100)}%-{int(ceiling*100)}%)',
                'type': 'updown',
                'scale_step': step,
                'floor': floor,
                'ceiling': ceiling,
                'return': metrics['total_return'],
                'max_dd': metrics['max_dd'],
                'return_dd': metrics['return_dd'],
                'final_equity': metrics['final_equity']
            })

print(f"   ✅ Tested {len(results)} strategies total")

# Sort by Return/DD
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

# Display TOP 20
print("\n" + "="*100)
print("🏆 TOP 20 STRATEGIES BY RETURN/MAX DD RATIO")
print("="*100)
print()

for idx, (i, row) in enumerate(results_df.head(20).iterrows()):
    emoji = "🏆" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx+1:2d}"

    print(f"{emoji} {row['strategy']:<55}")
    print(f"    Return/DD: {row['return_dd']:7.2f}x | Return: {row['return']:+8.1f}% | Max DD: {row['max_dd']:7.2f}%")
    print(f"    Final Equity: ${row['final_equity']:,.2f}")
    print()

# Analysis by scale step (for Scale Down strategies only)
print("="*100)
print("📊 SCALE DOWN ANALYSIS - BY STEP SIZE")
print("="*100)
print()

scale_down = results_df[results_df['type'] == 'scale_down']

for step in sorted(scale_down['scale_step'].unique()):
    step_data = scale_down[scale_down['scale_step'] == step]
    best = step_data.iloc[0]

    print(f"Step Size: {int(step*100)}% reduction per loss")
    print(f"  Best Config: {int(best['floor']*100)}% floor")
    print(f"  Return/DD: {best['return_dd']:.2f}x | Return: {best['return']:+.1f}% | Max DD: {best['max_dd']:.2f}%")
    print(f"  Avg Return/DD for this step: {step_data['return_dd'].mean():.2f}x")
    print()

# Analysis by floor (for Scale Down strategies only)
print("="*100)
print("📊 SCALE DOWN ANALYSIS - BY FLOOR LEVEL")
print("="*100)
print()

for floor in sorted(scale_down['floor'].unique()):
    floor_data = scale_down[scale_down['floor'] == floor]
    best = floor_data.iloc[0]

    print(f"Floor: {int(floor*100)}% minimum position size")
    print(f"  Best Config: {int(best['scale_step']*100)}% step")
    print(f"  Return/DD: {best['return_dd']:.2f}x | Return: {best['return']:+.1f}% | Max DD: {best['max_dd']:.2f}%")
    print(f"  Avg Return/DD for this floor: {floor_data['return_dd'].mean():.2f}x")
    print()

# Compare best vs baseline
best = results_df.iloc[0]
baseline = results_df[results_df['type'] == 'baseline'].iloc[0]

print("="*100)
print("🎯 BEST STRATEGY vs BASELINE")
print("="*100)
print()
print(f"🏆 WINNER: {best['strategy']}")
print(f"   Return/DD: {best['return_dd']:.2f}x")
print(f"   Return: {best['return']:+.1f}%")
print(f"   Max DD: {best['max_dd']:.2f}%")
print(f"   Final Equity: ${best['final_equity']:,.2f}")
print()
print(f"📊 BASELINE: {baseline['strategy']}")
print(f"   Return/DD: {baseline['return_dd']:.2f}x")
print(f"   Return: {baseline['return']:+.1f}%")
print(f"   Max DD: {baseline['max_dd']:.2f}%")
print(f"   Final Equity: ${baseline['final_equity']:,.2f}")
print()
print(f"📈 IMPROVEMENT:")
improvement_rdd = ((best['return_dd'] - baseline['return_dd']) / baseline['return_dd']) * 100
improvement_dd = ((abs(best['max_dd']) - abs(baseline['max_dd'])) / abs(baseline['max_dd'])) * 100
print(f"   Return/DD: {improvement_rdd:+.1f}%")
print(f"   Max DD: {improvement_dd:+.1f}% (negative = safer)")
print(f"   Return: {best['return'] - baseline['return']:+.1f} pp")
print()

# Save full results
results_df.to_csv('comprehensive_scaling_results.csv', index=False)
print("💾 Full results saved to: comprehensive_scaling_results.csv")
print("="*100)
