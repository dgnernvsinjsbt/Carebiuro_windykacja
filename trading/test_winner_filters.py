"""
Test filter combinations designed to KEEP the 48 winners, REMOVE the 48 losers

Based on winner analysis:
- Range20 > 8-12% (winners 11.84% vs losers 5.79%)
- ATR% > 1.2-1.5% (winners 1.62% vs losers 1.07%)
- Range96 > 12-18% (winners 19.05% vs losers 10.52%)
- ret_5 > 0% (positive momentum - winners +0.78% vs losers +0.15%)
- ema_dist: price slightly above EMA (winners +0.09% vs losers -0.10%)
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("WINNER-BASED FILTER TESTING")
print("Test filters designed from winner characteristics")
print("=" * 80)

# Load the ranked trades
trades_df = pd.read_csv('all_trades_ranked.csv')

print(f"\nTotal trades: {len(trades_df)}")
print(f"Winners: {len(trades_df[trades_df['pnl_pct'] > 0])}")
print(f"Losers: {len(trades_df[trades_df['pnl_pct'] < 0])}")

# Define filter test scenarios based on winner analysis
filter_tests = [
    # Single filters
    {'name': 'ATR > 1.2%', 'filters': [('entry_atr_pct', '>', 1.2)]},
    {'name': 'ATR > 1.4%', 'filters': [('entry_atr_pct', '>', 1.4)]},
    {'name': 'Range20 > 8%', 'filters': [('entry_range_20', '>', 8.0)]},
    {'name': 'Range20 > 10%', 'filters': [('entry_range_20', '>', 10.0)]},
    {'name': 'Range96 > 12%', 'filters': [('entry_range_96', '>', 12.0)]},
    {'name': 'Range96 > 15%', 'filters': [('entry_range_96', '>', 15.0)]},
    {'name': 'ret_5 > 0%', 'filters': [('entry_ret_5', '>', 0.0)]},
    {'name': 'ret_5 > 0.5%', 'filters': [('entry_ret_5', '>', 0.5)]},
    {'name': 'ret_20 > 0%', 'filters': [('entry_ret_20', '>', 0.0)]},

    # Two-filter combos (most powerful)
    {'name': 'ATR>1.2% + Range20>8%', 'filters': [('entry_atr_pct', '>', 1.2), ('entry_range_20', '>', 8.0)]},
    {'name': 'ATR>1.4% + Range20>8%', 'filters': [('entry_atr_pct', '>', 1.4), ('entry_range_20', '>', 8.0)]},
    {'name': 'Range20>8% + ret_5>0%', 'filters': [('entry_range_20', '>', 8.0), ('entry_ret_5', '>', 0.0)]},
    {'name': 'Range20>10% + ret_5>0%', 'filters': [('entry_range_20', '>', 10.0), ('entry_ret_5', '>', 0.0)]},
    {'name': 'ATR>1.2% + ret_5>0%', 'filters': [('entry_atr_pct', '>', 1.2), ('entry_ret_5', '>', 0.0)]},
    {'name': 'Range96>12% + ret_5>0%', 'filters': [('entry_range_96', '>', 12.0), ('entry_ret_5', '>', 0.0)]},

    # Three-filter combos
    {'name': 'ATR>1.2% + R20>8% + ret_5>0%', 'filters': [('entry_atr_pct', '>', 1.2), ('entry_range_20', '>', 8.0), ('entry_ret_5', '>', 0.0)]},
    {'name': 'ATR>1.4% + R20>8% + ret_5>0%', 'filters': [('entry_atr_pct', '>', 1.4), ('entry_range_20', '>', 8.0), ('entry_ret_5', '>', 0.0)]},
    {'name': 'ATR>1.2% + R96>12% + ret_5>0%', 'filters': [('entry_atr_pct', '>', 1.2), ('entry_range_96', '>', 12.0), ('entry_ret_5', '>', 0.0)]},

    # Aggressive four-filter
    {'name': 'ATR>1.4% + R20>10% + R96>15% + ret_5>0%', 'filters': [('entry_atr_pct', '>', 1.4), ('entry_range_20', '>', 10.0), ('entry_range_96', '>', 15.0), ('entry_ret_5', '>', 0.0)]},
]

results = []

for test in filter_tests:
    filtered = trades_df.copy()

    # Apply filters
    for col, op, val in test['filters']:
        if op == '>':
            filtered = filtered[filtered[col] > val]
        elif op == '<':
            filtered = filtered[filtered[col] < val]
        elif op == '>=':
            filtered = filtered[filtered[col] >= val]
        elif op == '<=':
            filtered = filtered[filtered[col] <= val]

    if len(filtered) == 0:
        continue

    winners_kept = len(filtered[filtered['pnl_pct'] > 0])
    losers_kept = len(filtered[filtered['pnl_pct'] < 0])

    # Calculate percentage of top 48 winners retained
    top_48_winners = trades_df.head(48)  # Top 48 trades (sorted by profit)
    top_winners_kept = len(filtered[filtered.index.isin(top_48_winners.index)])
    top_retention_pct = (top_winners_kept / 48) * 100

    total_trades = len(filtered)
    win_rate = (winners_kept / total_trades * 100) if total_trades > 0 else 0

    # Calculate performance metrics
    total_profit = filtered['pnl_pct'].sum()
    avg_profit = filtered['pnl_pct'].mean()

    # Quality score: prioritize keeping top winners while removing losers
    quality_score = (top_retention_pct * 2) + (win_rate * 1) - (losers_kept * 2)

    results.append({
        'name': test['name'],
        'trades': total_trades,
        'winners': winners_kept,
        'losers': losers_kept,
        'win_rate': win_rate,
        'top48_kept': top_winners_kept,
        'top48_retention': top_retention_pct,
        'total_profit_pct': total_profit,
        'avg_profit': avg_profit,
        'quality_score': quality_score
    })

results_df = pd.DataFrame(results)

# Sort by quality score (keeps top winners, high win rate, removes losers)
results_df = results_df.sort_values('quality_score', ascending=False)

print("\n" + "=" * 80)
print("FILTER TEST RESULTS (sorted by quality score):")
print("=" * 80)

print(f"\n| # | Filter Combo | Trades | W/L | Win% | Top48 | Avg P | Total P | Score |")
print("|---|--------------|--------|-----|------|-------|-------|---------|-------|")

for i, (idx, row) in enumerate(results_df.head(15).iterrows(), 1):
    highlight = "🏆" if i == 1 else ("✅" if row['trades'] >= 40 and row['win_rate'] >= 65 else "")
    print(f"| {i:2d} | {row['name']:<28s} | {row['trades']:3.0f} | "
          f"{row['winners']:2.0f}/{row['losers']:2.0f} | {row['win_rate']:4.1f}% | "
          f"{row['top48_kept']:2.0f} ({row['top48_retention']:3.0f}%) | "
          f"{row['avg_profit']:+5.2f}% | {row['total_profit_pct']:+6.0f}% | "
          f"{row['quality_score']:5.0f} | {highlight}")

# Best filter
best = results_df.iloc[0]

print("\n" + "=" * 80)
print("🏆 BEST FILTER COMBO:")
print("=" * 80)

print(f"\nFilter: {best['name']}")
print(f"\n📊 RESULTS:")
print(f"  Trades: {best['trades']:.0f} ({best['trades']/3:.1f} per month)")
print(f"  Winners: {best['winners']:.0f}")
print(f"  Losers: {best['losers']:.0f}")
print(f"  Win Rate: {best['win_rate']:.1f}%")
print(f"\n🎯 TOP WINNER RETENTION:")
print(f"  Kept {best['top48_kept']:.0f}/48 of best trades ({best['top48_retention']:.1f}%)")
print(f"\n💰 PERFORMANCE:")
print(f"  Avg Profit: {best['avg_profit']:+.2f}% per trade")
print(f"  Total Profit: {best['total_profit_pct']:+.0f}%")
print(f"  Quality Score: {best['quality_score']:.0f}")

if best['trades'] >= 40 and best['win_rate'] >= 60:
    print(f"\n✅ MEETS TARGETS: {best['trades']:.0f} trades with {best['win_rate']:.1f}% win rate!")
else:
    print(f"\n⚠️  Trades: {best['trades']:.0f} (target: 40+)")
    print(f"   Win%: {best['win_rate']:.1f}% (target: 60+)")

# Show best filter details
print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)

# Get top 3 filters by different criteria
print("\n🎯 Best for TOP WINNER RETENTION:")
top_retention = results_df.nlargest(3, 'top48_retention')
for idx, row in top_retention.iterrows():
    print(f"  - {row['name']}: {row['top48_kept']:.0f}/48 kept ({row['top48_retention']:.0f}%), "
          f"{row['trades']:.0f} trades, {row['win_rate']:.1f}% win")

print("\n📈 Best for HIGH WIN RATE:")
high_winrate = results_df[results_df['trades'] >= 30].nlargest(3, 'win_rate')
for idx, row in high_winrate.iterrows():
    print(f"  - {row['name']}: {row['win_rate']:.1f}% win, "
          f"{row['trades']:.0f} trades, {row['top48_kept']:.0f}/48 top kept")

print("\n⚖️  Best BALANCED (40+ trades + 60%+ win):")
balanced = results_df[(results_df['trades'] >= 40) & (results_df['win_rate'] >= 60)]
if len(balanced) > 0:
    for idx, row in balanced.head(3).iterrows():
        print(f"  - {row['name']}: {row['trades']:.0f} trades, {row['win_rate']:.1f}% win, "
              f"{row['top48_kept']:.0f}/48 top kept")
else:
    print(f"  ⚠️  No filters meet both 40+ trades AND 60%+ win rate")
    print(f"  Need to choose: More trades OR better quality")

results_df.to_csv('filter_test_results.csv', index=False)
print(f"\n💾 Saved {len(results_df)} filter test results to: filter_test_results.csv")
