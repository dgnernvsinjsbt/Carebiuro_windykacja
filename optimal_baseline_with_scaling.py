#!/usr/bin/env python3
"""
Test SCALING on top of different baseline allocations
Find optimal: high R/DD + safe max exposure
"""
import pandas as pd
import numpy as np

print("="*110)
print("OPTIMAL BASELINE + SCALING ANALYSIS")
print("="*110)

# Load all trades
df = pd.read_csv('4_coin_portfolio_all_trades.csv')
df['entry_time'] = pd.to_datetime(df['entry_time'])
df['exit_time'] = pd.to_datetime(df['exit_time'])
df = df.sort_values('entry_time').reset_index(drop=True)

print(f"\n📊 Data: {len(df)} trades")

def calculate_metrics(equity_curve):
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

def backtest_with_scaling(df, base_pct, scale_step, floor, ceiling):
    """
    base_pct: baseline % per strategy (e.g., 0.20 = 20%)
    scale_step: % to scale up/down (e.g., 0.20 = 20%)
    floor: min scale multiplier (e.g., 0.60 = 60% of baseline)
    ceiling: max scale multiplier (e.g., 3.0 = 300% of baseline)
    """
    equity = 100.0
    equity_curve = [equity]

    # Track scale per strategy
    strategy_scales = {coin: 1.0 for coin in df['coin'].unique()}

    # Track open positions
    open_positions = []
    max_total_exposure = 0
    max_simultaneous = 0

    # Create events
    all_events = []
    for idx, trade in df.iterrows():
        all_events.append({'time': trade['entry_time'], 'type': 'entry', 'trade_idx': idx, 'coin': trade['coin']})
        all_events.append({'time': trade['exit_time'], 'type': 'exit', 'trade_idx': idx, 'coin': trade['coin']})

    all_events = sorted(all_events, key=lambda x: x['time'])

    # Process events
    for event in all_events:
        coin = event['coin']

        if event['type'] == 'entry':
            trade = df.iloc[event['trade_idx']]

            # Calculate position size with scaling
            strategy_scale = strategy_scales[coin]
            position_pct = base_pct * strategy_scale
            position_size = equity * position_pct

            open_positions.append({
                'trade_idx': event['trade_idx'],
                'coin': coin,
                'position_size': position_size,
                'position_pct': position_pct,
                'pnl_pct': trade['pnl_pct']
            })

            # Track max exposure
            total_exposure = sum([p['position_pct'] for p in open_positions])
            max_total_exposure = max(max_total_exposure, total_exposure)
            max_simultaneous = max(max_simultaneous, len(open_positions))

        elif event['type'] == 'exit':
            # Find and close position
            for i, pos in enumerate(open_positions):
                if pos['trade_idx'] == event['trade_idx']:
                    position = open_positions.pop(i)

                    # Calculate P&L
                    pnl_dollar = position['position_size'] * (position['pnl_pct'] / 100)
                    equity += pnl_dollar
                    equity_curve.append(equity)

                    # Update strategy scale
                    if pnl_dollar > 0:  # WIN
                        strategy_scales[coin] = min(strategy_scales[coin] + scale_step, ceiling)
                    else:  # LOSS
                        strategy_scales[coin] = max(strategy_scales[coin] - scale_step, floor)
                    break

    metrics = calculate_metrics(equity_curve)
    metrics['max_total_exposure'] = max_total_exposure
    metrics['max_simultaneous'] = max_simultaneous

    return metrics

# Test grid
results = []

baselines = [0.15, 0.20, 0.25, 0.30, 0.40, 0.50]  # 15%, 20%, 25%, 30%, 40%, 50%
scale_steps = [0.15, 0.20, 0.25, 0.30]  # 15%, 20%, 25%, 30%
floors = [0.50, 0.60, 0.70]  # 50%, 60%, 70%
ceilings = [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]  # 200%, 250%, 300%, 350%, 400%, 500%

print(f"\n🔄 Testing {len(baselines)} baselines × {len(scale_steps)} steps × {len(floors)} floors × {len(ceilings)} ceilings")
print(f"   = {len(baselines) * len(scale_steps) * len(floors) * len(ceilings)} total combinations\n")

for base in baselines:
    for step in scale_steps:
        for floor in floors:
            for ceiling in ceilings:
                metrics = backtest_with_scaling(df, base, step, floor, ceiling)

                # Calculate actual % ranges
                min_pct = base * floor * 100  # e.g., 20% × 0.60 = 12%
                max_pct = base * ceiling * 100  # e.g., 20% × 5.0 = 100%
                max_exposure = metrics['max_total_exposure'] * 100

                results.append({
                    'baseline_pct': int(base * 100),
                    'step_pct': int(step * 100),
                    'floor_mult': floor,
                    'ceiling_mult': ceiling,
                    'min_position_pct': min_pct,
                    'max_position_pct': max_pct,
                    'max_total_exposure': max_exposure,
                    'return': metrics['total_return'],
                    'max_dd': metrics['max_dd'],
                    'return_dd': metrics['return_dd'],
                    'final_equity': metrics['final_equity']
                })

print(f"✅ Tested {len(results)} strategies")

# Convert to DataFrame and sort
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

# Show TOP 30
print("\n" + "="*110)
print("🏆 TOP 30 STRATEGIES BY RETURN/DD RATIO")
print("="*110)
print()

for idx, (i, row) in enumerate(results_df.head(30).iterrows()):
    emoji = "🏆" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx+1:2d}"
    safe = "✅" if row['max_total_exposure'] <= 150 else "⚠️" if row['max_total_exposure'] <= 200 else "❌"

    print(f"{emoji} Base:{int(row['baseline_pct']):2d}%, Step:{int(row['step_pct']):2d}%, Floor:{row['floor_mult']:.1f}, Ceil:{row['ceiling_mult']:.1f} "
          f"[{row['min_position_pct']:.0f}%-{row['max_position_pct']:.0f}% per strategy]")
    print(f"    R/DD: {row['return_dd']:6.2f}x | Return: {row['return']:+7.1f}% | Max DD: {row['max_dd']:6.2f}% | "
          f"Max Exposure: {row['max_total_exposure']:3.0f}% {safe}")
    print()

# Find best SAFE config (max exposure ≤ 150%)
print("="*110)
print("🛡️ BEST SAFE CONFIGURATIONS (Max Exposure ≤ 150%)")
print("="*110)
print()

safe_configs = results_df[results_df['max_total_exposure'] <= 150].head(15)

for idx, (i, row) in enumerate(safe_configs.iterrows()):
    emoji = "🏆" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx+1:2d}"

    print(f"{emoji} Base:{int(row['baseline_pct']):2d}%, Step:{int(row['step_pct']):2d}%, Floor:{row['floor_mult']:.1f}, Ceil:{row['ceiling_mult']:.1f} "
          f"[{row['min_position_pct']:.0f}%-{row['max_position_pct']:.0f}% per strategy]")
    print(f"    R/DD: {row['return_dd']:6.2f}x | Return: {row['return']:+7.1f}% | Max DD: {row['max_dd']:6.2f}% | "
          f"Max Exposure: {row['max_total_exposure']:3.0f}%")
    print()

# Summary
print("="*110)
print("📊 SUMMARY")
print("="*110)
print()

best_overall = results_df.iloc[0]
best_safe = safe_configs.iloc[0]

print("🚀 BEST OVERALL (ignoring safety):")
print(f"   Config: {int(best_overall['baseline_pct'])}% base, {int(best_overall['step_pct'])}% step, "
      f"{best_overall['floor_mult']:.1f} floor, {best_overall['ceiling_mult']:.1f} ceiling")
print(f"   Position Range: {best_overall['min_position_pct']:.0f}%-{best_overall['max_position_pct']:.0f}% per strategy")
print(f"   Return/DD: {best_overall['return_dd']:.2f}x")
print(f"   Return: {best_overall['return']:+.1f}%")
print(f"   Max DD: {best_overall['max_dd']:.2f}%")
print(f"   Max Total Exposure: {best_overall['max_total_exposure']:.0f}% ⚠️")
print()

print("🛡️ BEST SAFE (max exposure ≤ 150%):")
print(f"   Config: {int(best_safe['baseline_pct'])}% base, {int(best_safe['step_pct'])}% step, "
      f"{best_safe['floor_mult']:.1f} floor, {best_safe['ceiling_mult']:.1f} ceiling")
print(f"   Position Range: {best_safe['min_position_pct']:.0f}%-{best_safe['max_position_pct']:.0f}% per strategy")
print(f"   Return/DD: {best_safe['return_dd']:.2f}x")
print(f"   Return: {best_safe['return']:+.1f}%")
print(f"   Max DD: {best_safe['max_dd']:.2f}%")
print(f"   Max Total Exposure: {best_safe['max_total_exposure']:.0f}% ✅")
print()

# Save results
results_df.to_csv('baseline_scaling_optimization.csv', index=False)
print("💾 Full results saved to: baseline_scaling_optimization.csv")
print("="*110)
