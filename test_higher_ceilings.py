#!/usr/bin/env python3
"""
Test UP/DOWN strategies with higher ceilings (250%, 300%, 400%, 500%)
"""
import pandas as pd
import numpy as np

print("="*100)
print("TESTING HIGHER CEILINGS - UP/DOWN STRATEGIES")
print("="*100)

# Load all trades
df = pd.read_csv('4_coin_portfolio_all_trades.csv')
df['entry_time'] = pd.to_datetime(df['entry_time'])
df = df.sort_values('entry_time').reset_index(drop=True)

print(f"\n📊 Data: {len(df)} trades")

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

def backtest_updown(df, scale_step, floor, ceiling):
    """
    Backtest with scaling UP after win, DOWN after loss
    """
    equity = 100.0
    equity_curve = [equity]
    current_scale = 1.0
    max_consecutive_losses = 0
    consecutive_losses = 0
    max_scale_reached = 1.0

    for _, trade in df.iterrows():
        position_size = current_scale * equity
        pnl_dollar = position_size * (trade['pnl_pct'] / 100)
        equity += pnl_dollar
        equity_curve.append(equity)

        if pnl_dollar > 0:
            consecutive_losses = 0
            current_scale = min(current_scale + scale_step, ceiling)
            max_scale_reached = max(max_scale_reached, current_scale)
        else:
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            current_scale = max(current_scale - scale_step, floor)

    metrics = calculate_metrics(equity_curve)
    metrics['max_consecutive_losses'] = max_consecutive_losses
    metrics['max_scale_reached'] = max_scale_reached
    return metrics

# Test configurations
results = []

# Baseline
equity_curve = [100.0]
equity = 100.0
for _, trade in df.iterrows():
    pnl_dollar = equity * (trade['pnl_pct'] / 100)
    equity += pnl_dollar
    equity_curve.append(equity)

metrics = calculate_metrics(equity_curve)
results.append({
    'step': 0,
    'floor': 100,
    'ceiling': 100,
    'strategy': 'Baseline (100% fixed)',
    'return': metrics['total_return'],
    'max_dd': metrics['max_dd'],
    'return_dd': metrics['return_dd'],
    'final_equity': metrics['final_equity'],
    'max_scale': 1.0
})

# Test various UP/DOWN configurations
scale_steps = [0.10, 0.15, 0.20, 0.25, 0.30]  # 10%, 15%, 20%, 25%, 30%
floors = [0.30, 0.40, 0.50, 0.60]  # 30%, 40%, 50%, 60%
ceilings = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]  # 150%, 200%, 250%, 300%, 350%, 400%, 450%, 500%

print(f"\n🔄 Testing {len(scale_steps)} steps × {len(floors)} floors × {len(ceilings)} ceilings = {len(scale_steps)*len(floors)*len(ceilings)} combinations")

for step in scale_steps:
    for floor in floors:
        for ceiling in ceilings:
            metrics = backtest_updown(df, step, floor, ceiling)
            results.append({
                'step': int(step*100),
                'floor': int(floor*100),
                'ceiling': int(ceiling*100),
                'strategy': f'Up/Down ({int(step*100)}%, {int(floor*100)}%-{int(ceiling*100)}%)',
                'return': metrics['total_return'],
                'max_dd': metrics['max_dd'],
                'return_dd': metrics['return_dd'],
                'final_equity': metrics['final_equity'],
                'max_scale': metrics['max_scale_reached']
            })

print(f"✅ Tested {len(results)} strategies")

# Sort by Return/DD
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

# Display TOP 30
print("\n" + "="*100)
print("🏆 TOP 30 STRATEGIES BY RETURN/MAX DD RATIO")
print("="*100)
print()

for idx, (i, row) in enumerate(results_df.head(30).iterrows()):
    emoji = "🏆" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx+1:2d}"

    print(f"{emoji} {row['strategy']:<50}")
    print(f"    Return/DD: {row['return_dd']:7.2f}x | Return: {row['return']:+9.1f}% | Max DD: {row['max_dd']:7.2f}%")
    print(f"    Final Equity: ${row['final_equity']:,.2f} | Max Scale Reached: {row['max_scale']:.1f}x")
    print()

# Analysis by ceiling
print("="*100)
print("📊 ANALYSIS BY CEILING HEIGHT")
print("="*100)
print()

for ceiling in sorted(results_df[results_df['ceiling'] > 100]['ceiling'].unique()):
    ceiling_data = results_df[results_df['ceiling'] == ceiling]
    best = ceiling_data.iloc[0]

    print(f"Ceiling: {ceiling}% ({ceiling/100:.1f}x)")
    print(f"  Best Config: {best['step']}% step, {best['floor']}% floor")
    print(f"  Return/DD: {best['return_dd']:.2f}x | Return: {best['return']:+.1f}% | Max DD: {best['max_dd']:.2f}%")
    print(f"  Avg Return/DD for this ceiling: {ceiling_data['return_dd'].mean():.2f}x")
    print(f"  Max scale actually reached: {best['max_scale']:.1f}x")
    print()

# Compare best vs baseline
best = results_df.iloc[0]
baseline = results_df[results_df['ceiling'] == 100].iloc[0]

print("="*100)
print("🎯 BEST STRATEGY vs BASELINE")
print("="*100)
print()
print(f"🏆 WINNER: {best['strategy']}")
print(f"   Return/DD: {best['return_dd']:.2f}x")
print(f"   Return: {best['return']:+.1f}%")
print(f"   Max DD: {best['max_dd']:.2f}%")
print(f"   Final Equity: ${best['final_equity']:,.2f}")
print(f"   Max Scale Reached: {best['max_scale']:.1f}x (out of {best['ceiling']/100:.1f}x possible)")
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

# Find sweet spot (best avg R/DD by ceiling)
print("="*100)
print("🎯 SWEET SPOT ANALYSIS - Which ceiling gives best AVERAGE performance?")
print("="*100)
print()

ceiling_avg = results_df[results_df['ceiling'] > 100].groupby('ceiling').agg({
    'return_dd': ['mean', 'max', 'std'],
    'return': 'mean',
    'max_dd': 'mean'
}).round(2)

ceiling_avg.columns = ['Avg R/DD', 'Max R/DD', 'Std R/DD', 'Avg Return', 'Avg Max DD']
ceiling_avg = ceiling_avg.sort_values('Avg R/DD', ascending=False)

print(ceiling_avg)
print()
print(f"Best Average R/DD: {ceiling_avg.index[0]}% ceiling ({ceiling_avg.iloc[0]['Avg R/DD']:.2f}x avg)")

# Save results
results_df.to_csv('higher_ceilings_results.csv', index=False)
print("\n💾 Full results saved to: higher_ceilings_results.csv")
print("="*100)
