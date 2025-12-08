"""
Analyze the drawdown period to find patterns in losing trades
"""

import pandas as pd
import numpy as np

# Load original trades with all entry conditions
trades_df = pd.read_csv('results/fartcoin_30m_trade_analysis.csv')

# Apply best filter
filtered = trades_df[
    (trades_df['entry_momentum_7d'] < 0) &
    (trades_df['entry_atr_pct'] < 6) &
    (trades_df['entry_rsi'] < 60)
].copy()

filtered = filtered.sort_values('exit_date').reset_index(drop=True)
filtered['trade_num'] = range(len(filtered))

print("="*100)
print("DRAWDOWN PERIOD ANALYSIS - Trades 90-160")
print("="*100)

# Focus on the drawdown period (trades 90-160 based on the chart)
drawdown_trades = filtered[(filtered['trade_num'] >= 90) & (filtered['trade_num'] <= 160)]

print(f"\nDrawdown Period Stats:")
print(f"  Total Trades: {len(drawdown_trades)}")
print(f"  Winners: {len(drawdown_trades[drawdown_trades['win']])} ({len(drawdown_trades[drawdown_trades['win']])/len(drawdown_trades)*100:.1f}%)")
print(f"  Losers: {len(drawdown_trades[~drawdown_trades['win']])} ({len(drawdown_trades[~drawdown_trades['win']])/len(drawdown_trades)*100:.1f}%)")
print(f"  Total P&L: {drawdown_trades['pnl_pct'].sum():.2f}%")

# Compare with non-drawdown periods
other_trades = filtered[(filtered['trade_num'] < 90) | (filtered['trade_num'] > 160)]

print(f"\nNon-Drawdown Period Stats:")
print(f"  Total Trades: {len(other_trades)}")
print(f"  Winners: {len(other_trades[other_trades['win']])} ({len(other_trades[other_trades['win']])/len(other_trades)*100:.1f}%)")
print(f"  Losers: {len(other_trades[~other_trades['win']])} ({len(other_trades[~other_trades['win']])/len(other_trades)*100:.1f}%)")
print(f"  Total P&L: {other_trades['pnl_pct'].sum():.2f}%")

# Analyze entry conditions - drawdown winners vs losers
dd_winners = drawdown_trades[drawdown_trades['win']]
dd_losers = drawdown_trades[~drawdown_trades['win']]

print("\n" + "="*100)
print("DRAWDOWN PERIOD - ENTRY CONDITIONS COMPARISON")
print("="*100)

metrics = [
    ('RSI', 'entry_rsi'),
    ('ATR %', 'entry_atr_pct'),
    ('Volume Ratio', 'entry_volume_ratio'),
    ('BB Width %', 'entry_bb_width'),
    ('7d Momentum', 'entry_momentum_7d'),
    ('14d Momentum', 'entry_momentum_14d'),
    ('Above EMA50', 'entry_above_ema50'),
    ('Above EMA100', 'entry_above_ema100'),
]

print(f"\n{'Metric':<20} {'Winners (avg)':<18} {'Losers (avg)':<18} {'Difference':<15}")
print("-"*75)

significant_diffs = []

for name, col in metrics:
    if col in ['entry_above_ema50', 'entry_above_ema100']:
        w_avg = dd_winners[col].sum() / len(dd_winners) * 100 if len(dd_winners) > 0 else 0
        l_avg = dd_losers[col].sum() / len(dd_losers) * 100 if len(dd_losers) > 0 else 0
        diff = w_avg - l_avg
        print(f"{name:<20} {w_avg:<17.1f}% {l_avg:<17.1f}% {diff:+.1f}%")
    else:
        w_avg = dd_winners[col].mean() if len(dd_winners) > 0 else 0
        l_avg = dd_losers[col].mean() if len(dd_losers) > 0 else 0
        diff = w_avg - l_avg
        print(f"{name:<20} {w_avg:<18.2f} {l_avg:<18.2f} {diff:+.2f}")

    if abs(diff) > 0:
        significant_diffs.append({
            'name': name,
            'col': col,
            'w_avg': w_avg,
            'l_avg': l_avg,
            'diff': diff
        })

# Test additional filters on drawdown period
print("\n" + "="*100)
print("TESTING ADDITIONAL FILTERS ON DRAWDOWN PERIOD")
print("="*100)

test_filters = [
    # Tighter thresholds
    ('RSI < 55', lambda df: df['entry_rsi'] < 55),
    ('RSI < 50', lambda df: df['entry_rsi'] < 50),
    ('ATR < 5%', lambda df: df['entry_atr_pct'] < 5),
    ('ATR < 4%', lambda df: df['entry_atr_pct'] < 4),

    # Volume filters
    ('Volume > 0.8x', lambda df: df['entry_volume_ratio'] > 0.8),
    ('Volume > 1.0x', lambda df: df['entry_volume_ratio'] > 1.0),

    # Momentum filters
    ('Mom7d < -5%', lambda df: df['entry_momentum_7d'] < -5),
    ('Mom7d < -10%', lambda df: df['entry_momentum_7d'] < -10),
    ('Mom14d < 0%', lambda df: df['entry_momentum_14d'] < 0),
    ('Mom14d < -5%', lambda df: df['entry_momentum_14d'] < -5),

    # BB Width
    ('BB Width < 12%', lambda df: df['entry_bb_width'] < 12),
    ('BB Width < 10%', lambda df: df['entry_bb_width'] < 10),

    # EMA position
    ('Below EMA50', lambda df: ~df['entry_above_ema50']),
    ('Below EMA100', lambda df: ~df['entry_above_ema100']),
]

results = []

for name, filter_func in test_filters:
    # Apply to drawdown period only
    dd_filtered = drawdown_trades[filter_func(drawdown_trades)]

    if len(dd_filtered) == 0:
        continue

    dd_winners_new = len(dd_filtered[dd_filtered['win']])
    dd_losers_new = len(dd_filtered[~dd_filtered['win']])
    dd_pnl = dd_filtered['pnl_pct'].sum()

    # Apply to entire filtered dataset
    all_filtered = filtered[filter_func(filtered)]

    if len(all_filtered) == 0:
        continue

    all_winners = len(all_filtered[all_filtered['win']])
    all_pnl = all_filtered['pnl_pct'].sum()

    # Calculate equity with new filter
    equity = 1.0
    for _, trade in all_filtered.iterrows():
        equity *= (1 + trade['pnl_pct'] / 100)
    total_return = (equity - 1) * 100

    results.append({
        'filter': name,
        'dd_trades': len(dd_filtered),
        'dd_losers_removed': len(dd_losers) - dd_losers_new,
        'dd_winners_kept': dd_winners_new,
        'dd_pnl': dd_pnl,
        'total_trades': len(all_filtered),
        'total_return': total_return,
        'return_vs_current': total_return - 288.40,
    })

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_vs_current', ascending=False)

print(f"\n{'Filter':<18} {'DD Trades':<11} {'DD L.Rem':<11} {'DD W.Kept':<11} {'Total Ret':<12} {'vs Current':<12}")
print("-"*100)

for _, row in results_df.head(15).iterrows():
    print(f"{row['filter']:<18} {row['dd_trades']:<11.0f} {row['dd_losers_removed']:<11.0f} {row['dd_winners_kept']:<11.0f} {row['total_return']:<11.1f}% {row['return_vs_current']:>+11.1f}%")

print("\n" + "="*100)
print("TOP 3 RECOMMENDATIONS")
print("="*100)

for idx, row in results_df.head(3).iterrows():
    print(f"\n{row['filter']}:")
    print(f"  Impact on DD Period:")
    print(f"    Trades: {row['dd_trades']:.0f}/{len(drawdown_trades)} ({row['dd_trades']/len(drawdown_trades)*100:.1f}% kept)")
    print(f"    Losers Removed: {row['dd_losers_removed']:.0f}/{len(dd_losers)} ({row['dd_losers_removed']/len(dd_losers)*100:.1f}%)")
    print(f"    Winners Kept: {row['dd_winners_kept']:.0f}/{len(dd_winners)} ({row['dd_winners_kept']/len(dd_winners)*100:.1f}%)")
    print(f"  Overall Strategy:")
    print(f"    Total Trades: {row['total_trades']:.0f}/189 (original filtered)")
    print(f"    Total Return: {row['total_return']:.2f}% (current: 288.40%)")
    print(f"    Improvement: {row['return_vs_current']:+.2f}%")

print("\n" + "="*100)

# Save detailed analysis
drawdown_trades.to_csv('results/drawdown_period_trades.csv', index=False)
results_df.to_csv('results/drawdown_filter_tests.csv', index=False)

print("\n✓ Saved analysis to results/")
print("="*100)
