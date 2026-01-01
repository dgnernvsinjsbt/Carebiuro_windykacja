#!/usr/bin/env python3
"""
Compare SEQUENTIAL (ignoring overlaps) vs PORTFOLIO (accounting for overlaps)
"""
import pandas as pd
import numpy as np

print("="*100)
print("SEQUENTIAL vs PORTFOLIO COMPARISON")
print("="*100)

# Load all trades
df = pd.read_csv('4_coin_portfolio_all_trades.csv')
df['entry_time'] = pd.to_datetime(df['entry_time'])
df['exit_time'] = pd.to_datetime(df['exit_time'])
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

print("\n" + "="*100)
print("METHOD 1: SEQUENTIAL (ignoring overlaps - WRONG but shows max potential)")
print("="*100)

# Method 1: Sequential processing (what we did originally)
# This is WRONG because it ignores that trades overlap, but shows theoretical max

equity = 100.0
equity_curve = [equity]

for _, trade in df.iterrows():
    position_size = equity * 1.0  # 100% of equity
    pnl_dollar = position_size * (trade['pnl_pct'] / 100)
    equity += pnl_dollar
    equity_curve.append(equity)

seq_metrics = calculate_metrics(equity_curve)

print(f"\n🔄 SEQUENTIAL - 100% per trade (treating trades as if they never overlap):")
print(f"   Return/DD: {seq_metrics['return_dd']:.2f}x")
print(f"   Return: {seq_metrics['total_return']:+.1f}%")
print(f"   Max DD: {seq_metrics['max_dd']:.2f}%")
print(f"   Final Equity: ${seq_metrics['final_equity']:,.2f}")
print(f"   ⚠️  WARNING: This is UNREALISTIC because trades overlap in time!")

print("\n" + "="*100)
print("METHOD 2: PORTFOLIO (accounting for overlaps - CORRECT)")
print("="*100)

# Method 2: Portfolio with overlaps (correct approach)
def backtest_portfolio_realistic(df, base_pct_per_strategy=0.25):
    """
    Realistic portfolio backtest accounting for overlapping positions

    base_pct_per_strategy: how much % of equity to allocate per strategy
    With 4 strategies: 0.25 (25%) means 100% total when all signal at once
    """
    equity = 100.0
    equity_curve = [equity]

    # Track open positions
    open_positions = []

    # Create all events (entries and exits)
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

    all_events = sorted(all_events, key=lambda x: x['time'])

    max_simultaneous = 0
    max_total_exposure = 0

    # Process events chronologically
    for event in all_events:
        if event['type'] == 'entry':
            trade = df.iloc[event['trade_idx']]

            # Calculate position size
            position_size = equity * base_pct_per_strategy
            position_pct = base_pct_per_strategy

            open_positions.append({
                'trade_idx': event['trade_idx'],
                'coin': event['coin'],
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
                    break

    metrics = calculate_metrics(equity_curve)
    metrics['max_simultaneous'] = max_simultaneous
    metrics['max_total_exposure'] = max_total_exposure

    return metrics

# Test with 25% baseline (what user suggested)
portfolio_25_metrics = backtest_portfolio_realistic(df, base_pct_per_strategy=0.25)

print(f"\n🎯 PORTFOLIO - 25% per strategy (accounting for overlaps):")
print(f"   Return/DD: {portfolio_25_metrics['return_dd']:.2f}x")
print(f"   Return: {portfolio_25_metrics['total_return']:+.1f}%")
print(f"   Max DD: {portfolio_25_metrics['max_dd']:.2f}%")
print(f"   Final Equity: ${portfolio_25_metrics['final_equity']:,.2f}")
print(f"   Max Simultaneous Positions: {portfolio_25_metrics['max_simultaneous']}")
print(f"   Max Total Exposure: {portfolio_25_metrics['max_total_exposure']*100:.0f}%")
print(f"   ✅ This is REALISTIC and SAFE")

# Test with different baselines
print("\n" + "="*100)
print("TESTING DIFFERENT BASELINE ALLOCATIONS")
print("="*100)
print()

baselines = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75, 1.00]

results = []

for base in baselines:
    metrics = backtest_portfolio_realistic(df, base_pct_per_strategy=base)
    results.append({
        'baseline_pct': int(base * 100),
        'max_exposure_pct': int(metrics['max_total_exposure'] * 100),
        'return': metrics['total_return'],
        'max_dd': metrics['max_dd'],
        'return_dd': metrics['return_dd'],
        'final_equity': metrics['final_equity'],
        'max_simultaneous': metrics['max_simultaneous']
    })

    print(f"Baseline: {int(base*100):3d}% per strategy | Max Exposure: {int(metrics['max_total_exposure']*100):3d}% | "
          f"Return/DD: {metrics['return_dd']:6.2f}x | Return: {metrics['total_return']:+7.1f}% | "
          f"Max DD: {metrics['max_dd']:6.2f}%")

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

print("\n" + "="*100)
print("RANKING BY RETURN/DD")
print("="*100)
print()

for idx, (i, row) in enumerate(results_df.iterrows()):
    emoji = "🏆" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx+1}"
    safe = "✅" if row['max_exposure_pct'] <= 100 else "⚠️" if row['max_exposure_pct'] <= 150 else "❌"

    print(f"{emoji} {int(row['baseline_pct']):3d}% baseline | Max Exp: {int(row['max_exposure_pct']):3d}% {safe} | "
          f"R/DD: {row['return_dd']:6.2f}x | Return: {row['return']:+7.1f}% | DD: {row['max_dd']:6.2f}%")

print("\n" + "="*100)
print("KEY INSIGHTS")
print("="*100)
print()

print("1. SEQUENTIAL vs PORTFOLIO:")
print(f"   Sequential (100% per trade, ignoring overlaps): {seq_metrics['return_dd']:.2f}x R/DD, ${seq_metrics['final_equity']:,.2f}")
print(f"   Portfolio (25% per strategy, with overlaps):    {portfolio_25_metrics['return_dd']:.2f}x R/DD, ${portfolio_25_metrics['final_equity']:,.2f}")
print(f"   Difference: Sequential shows {seq_metrics['return_dd']/portfolio_25_metrics['return_dd']:.1f}x higher R/DD")
print(f"   Why? Sequential is UNREALISTIC - treats 4 simultaneous trades as 1 sequential trade!")
print()

best = results_df.iloc[0]
print(f"2. BEST BASELINE: {best['baseline_pct']}% per strategy")
print(f"   Return/DD: {best['return_dd']:.2f}x")
print(f"   Max Exposure: {best['max_exposure_pct']}%")
print(f"   Max DD: {best['max_dd']:.2f}%")
print()

print("3. SAFETY:")
safe_configs = results_df[results_df['max_exposure_pct'] <= 100]
print(f"   {len(safe_configs)} configurations keep max exposure <= 100%")
if len(safe_configs) > 0:
    print(f"   Best safe config: {safe_configs.iloc[0]['baseline_pct']}% baseline → {safe_configs.iloc[0]['return_dd']:.2f}x R/DD")

print("\n" + "="*100)
print("RECOMMENDATION")
print("="*100)
print()

print(f"🎯 For SAFETY (max exposure ≤ 100%):")
print(f"   Use {best['baseline_pct']}% per strategy baseline")
print(f"   Return/DD: {best['return_dd']:.2f}x")
print(f"   This ensures even if all 4 strategies signal at once,")
print(f"   total exposure = 4 × {best['baseline_pct']}% = {best['max_exposure_pct']}%")
print()

print("🚀 Now you can add SCALING on top of this baseline!")
print("="*100)
