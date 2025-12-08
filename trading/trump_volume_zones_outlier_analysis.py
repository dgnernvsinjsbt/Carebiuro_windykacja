"""
Analyze TRUMP Volume Zones Best Risk-Adjusted Config
Check if profits are from outliers or consistent
"""
import pandas as pd
import numpy as np

# Load best risk-adjusted trades
trades = pd.read_csv('results/TRUMP_volume_zones_best_riskadj_trades.csv')

print("="*80)
print("TRUMP VOLUME ZONES - OUTLIER & CONSISTENCY ANALYSIS")
print("Best Risk-Adjusted Config (10.56x R/DD)")
print("="*80)
print()

total_trades = len(trades)
total_return = (trades['pnl'] * 100).sum()

print(f"Total Trades: {total_trades}")
print(f"Total Return: {total_return:.2f}%")
print()

# Sort trades by PnL
trades_sorted = trades.sort_values('pnl', ascending=False).reset_index(drop=True)
trades_sorted['cumulative_pnl'] = (trades_sorted['pnl'] * 100).cumsum()
trades_sorted['cumulative_pct'] = (trades_sorted['cumulative_pnl'] / total_return) * 100

# Top contributors
print("="*80)
print("TOP 5 TRADES (by profit)")
print("="*80)
top_5 = trades_sorted.head(5)
for idx, row in top_5.iterrows():
    pnl_pct = row['pnl'] * 100
    contribution = (pnl_pct / total_return) * 100
    print(f"#{idx+1}: {row['direction']:5} {pnl_pct:+.2f}% ({row['bars']} bars, {row['exit_reason']}) "
          f"→ {contribution:.1f}% of total profit")

print()

# Bottom contributors
print("="*80)
print("BOTTOM 5 TRADES (biggest losses)")
print("="*80)
bottom_5 = trades_sorted.tail(5).sort_values('pnl')
for idx, row in bottom_5.iterrows():
    pnl_pct = row['pnl'] * 100
    impact = (pnl_pct / total_return) * 100
    print(f"{row['direction']:5} {pnl_pct:+.2f}% ({row['bars']} bars, {row['exit_reason']}) "
          f"→ {impact:.1f}% impact on total")

print()

# Concentration analysis
print("="*80)
print("PROFIT CONCENTRATION ANALYSIS")
print("="*80)

top_20_pct_count = int(total_trades * 0.2)
top_20_pct_profit = trades_sorted.head(top_20_pct_count)['pnl'].sum() * 100
top_20_pct_contribution = (top_20_pct_profit / total_return) * 100

top_50_pct_count = int(total_trades * 0.5)
top_50_pct_profit = trades_sorted.head(top_50_pct_count)['pnl'].sum() * 100
top_50_pct_contribution = (top_50_pct_profit / total_return) * 100

print(f"Top 20% of trades ({top_20_pct_count} trades):")
print(f"  Generated: {top_20_pct_profit:.2f}%")
print(f"  Contribution: {top_20_pct_contribution:.1f}% of total profit")
print()

print(f"Top 50% of trades ({top_50_pct_count} trades):")
print(f"  Generated: {top_50_pct_profit:.2f}%")
print(f"  Contribution: {top_50_pct_contribution:.1f}% of total profit")
print()

# Check if strategy is outlier-driven
if top_20_pct_contribution > 80:
    print("⚠️  OUTLIER-DRIVEN: Top 20% of trades generate >80% of profit")
    print("    Strategy relies on a few big winners")
elif top_20_pct_contribution > 60:
    print("⚠️  MODERATELY CONCENTRATED: Top 20% generate 60-80% of profit")
    print("    Some concentration, but not extreme")
elif top_20_pct_contribution > 40:
    print("✅ WELL-DISTRIBUTED: Top 20% generate 40-60% of profit")
    print("    Profits spread across many trades (good)")
else:
    print("✅ HIGHLY CONSISTENT: Top 20% generate <40% of profit")
    print("    Very evenly distributed profits (excellent)")

print()

# Statistical consistency metrics
winners = trades[trades['pnl'] > 0]['pnl'] * 100
losers = trades[trades['pnl'] <= 0]['pnl'] * 100

print("="*80)
print("TRADE DISTRIBUTION STATISTICS")
print("="*80)
print(f"Winners: {len(winners)}")
print(f"  Mean: {winners.mean():.2f}%")
print(f"  Median: {winners.median():.2f}%")
print(f"  Std Dev: {winners.std():.2f}%")
print(f"  Max: {winners.max():.2f}%")
print(f"  Min: {winners.min():.2f}%")
print()
print(f"Losers: {len(losers)}")
print(f"  Mean: {losers.mean():.2f}%")
print(f"  Median: {losers.median():.2f}%")
print(f"  Std Dev: {losers.std():.2f}%")
print(f"  Max (least bad): {losers.max():.2f}%")
print(f"  Min (worst): {losers.min():.2f}%")
print()

# Coefficient of variation (CV) - measures relative consistency
cv_winners = (winners.std() / winners.mean()) if winners.mean() > 0 else 0
cv_losers = abs(losers.std() / losers.mean()) if losers.mean() < 0 else 0

print(f"Coefficient of Variation (lower = more consistent):")
print(f"  Winners CV: {cv_winners:.2f}")
print(f"  Losers CV: {cv_losers:.2f}")
print()

if cv_winners < 0.5:
    print("✅ Winners are VERY CONSISTENT (CV < 0.5)")
elif cv_winners < 1.0:
    print("✅ Winners are MODERATELY CONSISTENT (CV < 1.0)")
else:
    print("⚠️  Winners are VARIABLE (CV > 1.0)")

print()

# Equity curve smoothness
print("="*80)
print("EQUITY CURVE SMOOTHNESS")
print("="*80)

trades_seq = trades.copy()
trades_seq['cumulative'] = (trades_seq['pnl'] * 100).cumsum()
trades_seq['rolling_avg_5'] = trades_seq['cumulative'].rolling(5).mean()

# Count how many times we had 3+ consecutive losers
trades_seq['is_loser'] = trades_seq['pnl'] <= 0
consecutive_losers = []
count = 0
for is_loser in trades_seq['is_loser']:
    if is_loser:
        count += 1
    else:
        if count >= 3:
            consecutive_losers.append(count)
        count = 0

if count >= 3:
    consecutive_losers.append(count)

max_consecutive_losers = max(consecutive_losers) if consecutive_losers else 0

print(f"Max consecutive losers: {max_consecutive_losers}")
print(f"Times hit 3+ losing streak: {len(consecutive_losers)}")
print()

if max_consecutive_losers <= 3:
    print("✅ EXCELLENT: Max 3 consecutive losers (very smooth)")
elif max_consecutive_losers <= 5:
    print("✅ GOOD: Max 5 consecutive losers (acceptable)")
else:
    print("⚠️  CHOPPY: 6+ consecutive losers (psychological challenge)")

print()

# Remove single trade and see impact
print("="*80)
print("ROBUSTNESS TEST: Impact of Removing Best Trade")
print("="*80)

best_trade_pnl = trades_sorted.iloc[0]['pnl'] * 100
return_without_best = total_return - best_trade_pnl
impact_pct = ((total_return - return_without_best) / total_return) * 100

print(f"Current return: {total_return:.2f}%")
print(f"Best trade contribution: {best_trade_pnl:.2f}% ({impact_pct:.1f}% of total)")
print(f"Return without best trade: {return_without_best:.2f}%")
print()

if impact_pct > 50:
    print("⚠️  FRAGILE: Best trade contributes >50% (strategy depends on one trade)")
elif impact_pct > 30:
    print("⚠️  CONCENTRATED: Best trade contributes 30-50% (moderate dependency)")
elif impact_pct > 15:
    print("✅ SOLID: Best trade contributes 15-30% (acceptable)")
else:
    print("✅ ROBUST: Best trade contributes <15% (highly diversified)")

print()

# Summary verdict
print("="*80)
print("CONSISTENCY VERDICT")
print("="*80)

if top_20_pct_contribution < 60 and cv_winners < 1.0 and impact_pct < 30:
    print("✅ HIGHLY CONSISTENT STRATEGY")
    print("   - Profits well-distributed across trades")
    print("   - Winners are similar in size (low CV)")
    print("   - No single trade dependency")
    print("   → Strategy is ROBUST and REPEATABLE")
elif top_20_pct_contribution < 80 and impact_pct < 50:
    print("✅ MODERATELY CONSISTENT STRATEGY")
    print("   - Some concentration but acceptable")
    print("   - Strategy has reasonable robustness")
    print("   → Strategy is TRADEABLE but watch for outliers")
else:
    print("⚠️  OUTLIER-DEPENDENT STRATEGY")
    print("   - Profits heavily concentrated in few trades")
    print("   - High variability in trade outcomes")
    print("   → Strategy may not be robust in different market conditions")

print()
print("="*80)
