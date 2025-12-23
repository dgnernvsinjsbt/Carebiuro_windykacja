#!/usr/bin/env python3
"""
Analyze different position sizing strategies to optimize Return/Max DD ratio
"""
import pandas as pd
import numpy as np

print("="*100)
print("POSITION SIZING ANALYSIS - OPTIMIZING RETURN/MAX DD RATIO")
print("="*100)

# Load all trades
df = pd.read_csv('4_coin_portfolio_all_trades.csv')
df['entry_time'] = pd.to_datetime(df['entry_time'])
df = df.sort_values('entry_time').reset_index(drop=True)

print(f"\n📊 Data Loaded:")
print(f"   Total Trades: {len(df)}")
print(f"   Period: {df['entry_time'].min()} to {df['entry_time'].max()}")
print(f"   Coins: {df['coin'].unique()}")

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

def backtest_strategy(df, strategy_name, scale_func):
    """
    Backtest with custom scaling function

    scale_func(consecutive_wins, consecutive_losses, current_scale) -> new_scale
    """
    equity = 100.0
    equity_curve = [equity]

    consecutive_wins = 0
    consecutive_losses = 0
    current_scale = 1.0  # 100%

    max_consecutive_losses = 0

    for _, trade in df.iterrows():
        # Position size = current_scale * equity
        position_size = current_scale * equity

        # P&L in dollars
        pnl_dollar = position_size * (trade['pnl_pct'] / 100)

        equity += pnl_dollar
        equity_curve.append(equity)

        # Update consecutive counters
        if pnl_dollar > 0:
            consecutive_wins += 1
            consecutive_losses = 0
        else:
            consecutive_losses += 1
            consecutive_wins = 0
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

        # Update scale for next trade
        current_scale = scale_func(consecutive_wins, consecutive_losses, current_scale)

    metrics = calculate_metrics(equity_curve)
    metrics['max_consecutive_losses'] = max_consecutive_losses
    metrics['equity_curve'] = equity_curve

    return metrics

# Define scaling strategies
strategies = {}

# 1. BASELINE: 100% every trade (no scaling)
def baseline(cw, cl, scale):
    return 1.0

strategies['Baseline (100% fixed)'] = baseline

# 2. Scale DOWN after loss (floor 50%)
def scale_down_50(cw, cl, scale):
    if cl > 0:  # Just had a loss
        return max(scale - 0.10, 0.50)  # Reduce by 10%, floor at 50%
    else:  # Win - reset to 100%
        return 1.0

strategies['Scale Down (50% floor)'] = scale_down_50

# 3. Scale DOWN after loss (floor 30%)
def scale_down_30(cw, cl, scale):
    if cl > 0:
        return max(scale - 0.10, 0.30)  # Floor at 30%
    else:
        return 1.0

strategies['Scale Down (30% floor)'] = scale_down_30

# 4. Scale UP/DOWN (100% ceiling)
def scale_updown_100(cw, cl, scale):
    if cl > 0:  # Loss
        return max(scale - 0.10, 0.30)
    else:  # Win
        return min(scale + 0.10, 1.0)  # Ceiling at 100%

strategies['Scale Up/Down (100% ceiling)'] = scale_updown_100

# 5. Scale UP/DOWN (150% ceiling)
def scale_updown_150(cw, cl, scale):
    if cl > 0:  # Loss
        return max(scale - 0.10, 0.30)
    else:  # Win
        return min(scale + 0.10, 1.5)  # Ceiling at 150%

strategies['Scale Up/Down (150% ceiling)'] = scale_updown_150

# 6. Aggressive scale down (20% floor)
def scale_down_20(cw, cl, scale):
    if cl > 0:
        return max(scale - 0.10, 0.20)  # Floor at 20%
    else:
        return 1.0

strategies['Scale Down (20% floor)'] = scale_down_20

# 7. Conservative scale down (60% floor)
def scale_down_60(cw, cl, scale):
    if cl > 0:
        return max(scale - 0.10, 0.60)  # Floor at 60%
    else:
        return 1.0

strategies['Scale Down (60% floor)'] = scale_down_60

# 8. Gradual UP/DOWN (100% ceiling, slower)
def scale_gradual_100(cw, cl, scale):
    if cl > 0:
        return max(scale - 0.05, 0.30)  # Reduce by 5%
    else:
        return min(scale + 0.05, 1.0)   # Increase by 5%

strategies['Gradual Up/Down (5% steps, 100% ceiling)'] = scale_gradual_100

# 9. Aggressive UP/DOWN (200% ceiling)
def scale_updown_200(cw, cl, scale):
    if cl > 0:
        return max(scale - 0.10, 0.30)
    else:
        return min(scale + 0.10, 2.0)  # Ceiling at 200%

strategies['Scale Up/Down (200% ceiling)'] = scale_updown_200

# Run all strategies
print("\n" + "="*100)
print("TESTING STRATEGIES")
print("="*100)

results = []

for name, func in strategies.items():
    print(f"\n🔄 Testing: {name}")
    metrics = backtest_strategy(df, name, func)

    results.append({
        'strategy': name,
        'return': metrics['total_return'],
        'max_dd': metrics['max_dd'],
        'return_dd': metrics['return_dd'],
        'final_equity': metrics['final_equity'],
        'max_consec_losses': metrics['max_consecutive_losses']
    })

    print(f"   Return: {metrics['total_return']:+.1f}%")
    print(f"   Max DD: {metrics['max_dd']:.2f}%")
    print(f"   Return/DD: {metrics['return_dd']:.2f}x 🎯")
    print(f"   Final Equity: ${metrics['final_equity']:.2f}")

# Sort by Return/DD ratio
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

# Display results
print("\n" + "="*100)
print("RANKING BY RETURN/MAX DD RATIO (OPTIMIZED FOR RISK-ADJUSTED RETURNS)")
print("="*100)
print()

for i, row in results_df.iterrows():
    rank = list(results_df.index).index(i) + 1
    emoji = "🏆" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "  "

    print(f"{emoji} #{rank} {row['strategy']:<45}")
    print(f"      Return/DD: {row['return_dd']:7.2f}x | Return: {row['return']:+8.1f}% | Max DD: {row['max_dd']:7.2f}%")
    print(f"      Final Equity: ${row['final_equity']:,.2f} | Max Consecutive Losses: {row['max_consec_losses']}")
    print()

# Best strategy analysis
best = results_df.iloc[0]
baseline = results_df[results_df['strategy'] == 'Baseline (100% fixed)'].iloc[0]

print("="*100)
print("🎯 BEST STRATEGY vs BASELINE")
print("="*100)
print()
print(f"BEST: {best['strategy']}")
print(f"  Return/DD: {best['return_dd']:.2f}x")
print(f"  Return: {best['return']:+.1f}%")
print(f"  Max DD: {best['max_dd']:.2f}%")
print(f"  Final Equity: ${best['final_equity']:,.2f}")
print()
print(f"BASELINE: {baseline['strategy']}")
print(f"  Return/DD: {baseline['return_dd']:.2f}x")
print(f"  Return: {baseline['return']:+.1f}%")
print(f"  Max DD: {baseline['max_dd']:.2f}%")
print(f"  Final Equity: ${baseline['final_equity']:,.2f}")
print()
print(f"IMPROVEMENT:")
improvement_return_dd = ((best['return_dd'] - baseline['return_dd']) / baseline['return_dd']) * 100
improvement_dd = ((abs(best['max_dd']) - abs(baseline['max_dd'])) / abs(baseline['max_dd'])) * 100
print(f"  Return/DD: {improvement_return_dd:+.1f}%")
print(f"  Max DD: {improvement_dd:+.1f}% (negative = better)")
print(f"  Return: {best['return'] - baseline['return']:+.1f} percentage points")
print()

# Save results
results_df.to_csv('position_sizing_results.csv', index=False)
print("💾 Results saved to: position_sizing_results.csv")
print("="*100)
