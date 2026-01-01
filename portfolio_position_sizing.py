#!/usr/bin/env python3
"""
Portfolio Position Sizing - 4 strategies with 25% baseline each
Account for simultaneous positions to avoid over-leverage
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*100)
print("PORTFOLIO POSITION SIZING - 4 STRATEGIES, 25% BASELINE EACH")
print("="*100)

# Load all trades
df = pd.read_csv('4_coin_portfolio_all_trades.csv')
df['entry_time'] = pd.to_datetime(df['entry_time'])
df['exit_time'] = pd.to_datetime(df['exit_time'])
df = df.sort_values('entry_time').reset_index(drop=True)

print(f"\n📊 Data: {len(df)} trades from {len(df['coin'].unique())} strategies")
print(f"   Period: {df['entry_time'].min()} to {df['exit_time'].max()}")
print(f"   Coins: {', '.join(df['coin'].unique())}")

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

def backtest_portfolio(df, scale_step, floor, ceiling, base_pct=0.25):
    """
    Backtest with portfolio risk management

    base_pct: baseline % per strategy (0.25 = 25%)
    scale_step: % to scale up/down per win/loss
    floor: minimum scale multiplier (e.g., 0.60 = 60% of baseline)
    ceiling: maximum scale multiplier (e.g., 5.0 = 500% of baseline)
    """
    equity = 100.0
    equity_curve = [equity]

    # Track scale multiplier per strategy
    strategy_scales = {
        'FARTCOIN': 1.0,
        'MOODENG': 1.0,
        'MELANIA': 1.0,
        'DOGE': 1.0
    }

    # Track consecutive wins/losses per strategy
    consecutive_losses = {coin: 0 for coin in strategy_scales.keys()}
    max_consecutive_losses = 0

    # Track open positions
    open_positions = []

    # Track max simultaneous exposure
    max_total_exposure = 0
    max_simultaneous_positions = 0

    # Process all trades chronologically
    all_events = []

    for idx, trade in df.iterrows():
        all_events.append({
            'time': trade['entry_time'],
            'type': 'entry',
            'trade_idx': idx,
            'coin': trade['coin']
        })
        all_events.append({
            'time': trade['exit_time'],
            'type': 'exit',
            'trade_idx': idx,
            'coin': trade['coin']
        })

    # Sort by time
    all_events = sorted(all_events, key=lambda x: x['time'])

    # Process events
    for event in all_events:
        coin = event['coin']

        if event['type'] == 'entry':
            trade = df.iloc[event['trade_idx']]

            # Calculate position size for this strategy
            strategy_scale = strategy_scales[coin]
            position_pct = base_pct * strategy_scale  # e.g., 25% * 1.5 = 37.5%
            position_size = equity * position_pct

            # Store position info
            open_positions.append({
                'trade_idx': event['trade_idx'],
                'coin': coin,
                'entry_time': trade['entry_time'],
                'exit_time': trade['exit_time'],
                'position_size': position_size,
                'position_pct': position_pct,
                'pnl_pct': trade['pnl_pct'],
                'equity_at_entry': equity
            })

            # Track max exposure
            total_exposure = sum([p['position_pct'] for p in open_positions])
            max_total_exposure = max(max_total_exposure, total_exposure)
            max_simultaneous_positions = max(max_simultaneous_positions, len(open_positions))

        elif event['type'] == 'exit':
            # Find the position to close
            position = None
            for i, pos in enumerate(open_positions):
                if pos['trade_idx'] == event['trade_idx']:
                    position = open_positions.pop(i)
                    break

            if position:
                # Calculate P&L
                pnl_dollar = position['position_size'] * (position['pnl_pct'] / 100)
                equity += pnl_dollar
                equity_curve.append(equity)

                # Update strategy scale
                if pnl_dollar > 0:  # WIN
                    consecutive_losses[coin] = 0
                    strategy_scales[coin] = min(strategy_scales[coin] + scale_step, ceiling)
                else:  # LOSS
                    consecutive_losses[coin] += 1
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses[coin])
                    strategy_scales[coin] = max(strategy_scales[coin] - scale_step, floor)

    metrics = calculate_metrics(equity_curve)
    metrics['max_consecutive_losses'] = max_consecutive_losses
    metrics['max_total_exposure'] = max_total_exposure
    metrics['max_simultaneous_positions'] = max_simultaneous_positions

    return metrics

# Test configurations
results = []

print("\n🔄 Testing strategies with 25% baseline per strategy...")

# Baseline (25% per strategy, no scaling)
equity = 100.0
equity_curve = [equity]
open_positions = []

all_events = []
for idx, trade in df.iterrows():
    all_events.append({'time': trade['entry_time'], 'type': 'entry', 'trade_idx': idx})
    all_events.append({'time': trade['exit_time'], 'type': 'exit', 'trade_idx': idx})

all_events = sorted(all_events, key=lambda x: x['time'])

for event in all_events:
    if event['type'] == 'entry':
        trade = df.iloc[event['trade_idx']]
        position_size = equity * 0.25  # 25% per strategy
        open_positions.append({
            'trade_idx': event['trade_idx'],
            'position_size': position_size,
            'pnl_pct': trade['pnl_pct']
        })
    elif event['type'] == 'exit':
        for i, pos in enumerate(open_positions):
            if pos['trade_idx'] == event['trade_idx']:
                position = open_positions.pop(i)
                pnl_dollar = position['position_size'] * (position['pnl_pct'] / 100)
                equity += pnl_dollar
                equity_curve.append(equity)
                break

metrics = calculate_metrics(equity_curve)
results.append({
    'strategy': 'Baseline (25% per strategy, no scaling)',
    'step': 0,
    'floor': 25,
    'ceiling': 25,
    'return': metrics['total_return'],
    'max_dd': metrics['max_dd'],
    'return_dd': metrics['return_dd'],
    'final_equity': metrics['final_equity']
})

# Test various configurations
scale_steps = [0.10, 0.15, 0.20, 0.25, 0.30]  # 10%, 15%, 20%, 25%, 30%
floors = [0.40, 0.50, 0.60, 0.70]  # 40%, 50%, 60%, 70% of baseline (10%, 12.5%, 15%, 17.5% of equity)
ceilings = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]  # 200%, 250%, 300%, 350%, 400%, 450%, 500%

print(f"   Testing {len(scale_steps)} steps × {len(floors)} floors × {len(ceilings)} ceilings = {len(scale_steps)*len(floors)*len(ceilings)} combinations")

for step in scale_steps:
    for floor in floors:
        for ceiling in ceilings:
            metrics = backtest_portfolio(df, step, floor, ceiling, base_pct=0.25)

            # Calculate actual % ranges
            min_pct = 25 * floor  # e.g., 25% × 0.60 = 15%
            max_pct = 25 * ceiling  # e.g., 25% × 5.0 = 125%

            results.append({
                'strategy': f'Up/Down ({int(step*100)}%, {int(floor*100)}%-{int(ceiling*100)}%) [{min_pct:.0f}%-{max_pct:.0f}% per strategy]',
                'step': int(step*100),
                'floor_pct': min_pct,
                'ceiling_pct': max_pct,
                'return': metrics['total_return'],
                'max_dd': metrics['max_dd'],
                'return_dd': metrics['return_dd'],
                'final_equity': metrics['final_equity'],
                'max_exposure': metrics['max_total_exposure'] * 100,
                'max_positions': metrics['max_simultaneous_positions']
            })

print(f"   ✅ Tested {len(results)} strategies")

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

    print(f"{emoji} {row['strategy']:<75}")
    print(f"    Return/DD: {row['return_dd']:7.2f}x | Return: {row['return']:+8.1f}% | Max DD: {row['max_dd']:7.2f}%")
    print(f"    Final Equity: ${row['final_equity']:,.2f}", end="")

    if 'max_exposure' in row and pd.notna(row['max_exposure']):
        print(f" | Max Total Exposure: {row['max_exposure']:.0f}% | Max Simultaneous: {int(row['max_positions'])}")
    else:
        print()
    print()

# Compare best vs baseline
best = results_df.iloc[0]
baseline = results_df[results_df['strategy'].str.contains('Baseline')].iloc[0]

print("="*100)
print("🎯 BEST STRATEGY vs BASELINE")
print("="*100)
print()
print(f"🏆 WINNER: {best['strategy']}")
print(f"   Return/DD: {best['return_dd']:.2f}x")
print(f"   Return: {best['return']:+.1f}%")
print(f"   Max DD: {best['max_dd']:.2f}%")
print(f"   Final Equity: ${best['final_equity']:,.2f}")
if 'max_exposure' in best and pd.notna(best['max_exposure']):
    print(f"   Max Total Portfolio Exposure: {best['max_exposure']:.0f}%")
    print(f"   Max Simultaneous Positions: {int(best['max_positions'])}")
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

# Show safe configurations (max exposure < 150%)
print("="*100)
print("🛡️ SAFE CONFIGURATIONS (Max Total Exposure < 150%)")
print("="*100)
print()

safe_configs = results_df[results_df['max_exposure'] < 150].head(10)

for idx, (i, row) in enumerate(safe_configs.iterrows()):
    print(f"#{idx+1} {row['strategy']:<75}")
    print(f"    Return/DD: {row['return_dd']:7.2f}x | Max Exposure: {row['max_exposure']:.0f}% | Max DD: {row['max_dd']:.2f}%")
    print()

# Save results
results_df.to_csv('portfolio_sizing_results.csv', index=False)
print("\n💾 Full results saved to: portfolio_sizing_results.csv")
print("="*100)
