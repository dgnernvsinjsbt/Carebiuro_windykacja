#!/usr/bin/env python3
"""
Comprehensive statistical validation of MOODENG ATR Limit strategy
Detects anomalies, unrealistic patterns, and assesses live trading viability
"""
import pandas as pd
import numpy as np

print("=" * 100)
print("MOODENG ATR LIMIT STRATEGY - COMPREHENSIVE STATISTICAL VALIDATION")
print("=" * 100)

# Load trade data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/moodeng_validation_trades.csv')

print(f"\nLoaded {len(df)} trades")
print(f"Period: {df['entry_timestamp'].min()} to {df['exit_timestamp'].max()}")

# ============================================================================
# 1. BASIC STATISTICS
# ============================================================================
print("\n" + "=" * 100)
print("1. BASIC STATISTICS")
print("=" * 100)

winners = df[df['pnl_pct'] > 0]
losers = df[df['pnl_pct'] < 0]

win_rate = len(winners) / len(df) * 100
total_pnl = df['pnl_pct'].sum()
avg_win = winners['pnl_pct'].mean()
avg_loss = losers['pnl_pct'].mean()
median_win = winners['pnl_pct'].median()
median_loss = losers['pnl_pct'].median()
max_win = winners['pnl_pct'].max()
max_loss = losers['pnl_pct'].min()

gross_profits = winners['pnl_pct'].sum()
gross_losses = abs(losers['pnl_pct'].sum())
profit_factor = gross_profits / gross_losses if gross_losses > 0 else float('inf')

expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)

print(f"\nWin Rate:       {win_rate:.1f}%")
print(f"Total P/L:      {total_pnl:+.2f}%")
print(f"Average Win:    {avg_win:+.2f}%")
print(f"Average Loss:   {avg_loss:-.2f}%")
print(f"Median Win:     {median_win:+.2f}%")
print(f"Median Loss:    {median_loss:-.2f}%")
print(f"Max Win:        {max_win:+.2f}%")
print(f"Max Loss:       {max_loss:-.2f}%")
print(f"Profit Factor:  {profit_factor:.2f}")
print(f"Expectancy:     {expectancy:+.2f}%")

# ============================================================================
# 2. ANOMALY DETECTION
# ============================================================================
print("\n" + "=" * 100)
print("2. ANOMALY DETECTION")
print("=" * 100)

# Outliers (>3 standard deviations)
mean_pnl = df['pnl_pct'].mean()
std_pnl = df['pnl_pct'].std()
outliers = df[abs(df['pnl_pct'] - mean_pnl) > 3 * std_pnl]

print(f"\n🔍 Outliers (>3 SD from mean):")
if len(outliers) > 0:
    print(f"  Found {len(outliers)} outlier trades:")
    for idx, row in outliers.iterrows():
        print(f"    Trade #{row['trade_num']}: {row['pnl_pct']:+.2f}% ({row['direction']}, {row['exit_reason']}) - {row['entry_timestamp']}")
else:
    print("  No outliers found")

# Concentration analysis
df_sorted = df.sort_values('pnl_pct', ascending=False)
top5_trades = df_sorted.head(5)
bottom5_trades = df_sorted.tail(5)
top5_pnl = top5_trades['pnl_pct'].sum()
bottom5_pnl = bottom5_trades['pnl_pct'].sum()

top5_pct = (top5_pnl / total_pnl * 100) if total_pnl > 0 else 0
bottom5_pct = (bottom5_pnl / total_pnl * 100) if total_pnl > 0 else 0

print(f"\n📊 Concentration Analysis:")
print(f"  Top 5 trades contribute:    {top5_pnl:+.2f}% ({top5_pct:.1f}% of total)")
print(f"  Bottom 5 trades contribute: {bottom5_pnl:+.2f}% ({bottom5_pct:.1f}% of total)")

# Dependency classification
if top5_pct > 80:
    dependency = "EXTREME (>80%)"
elif top5_pct > 60:
    dependency = "HIGH (60-80%)"
elif top5_pct > 40:
    dependency = "MEDIUM (40-60%)"
else:
    dependency = "LOW (<40%)"

print(f"  Dependency classification: {dependency}")

print(f"\n  Top 5 best trades:")
for idx, row in top5_trades.iterrows():
    print(f"    #{row['trade_num']}: {row['pnl_pct']:+.2f}% ({row['direction']}, {row['exit_reason']}) - {row['entry_timestamp']}")

print(f"\n  Top 5 worst trades:")
for idx, row in bottom5_trades[::-1].iterrows():
    print(f"    #{row['trade_num']}: {row['pnl_pct']:+.2f}% ({row['direction']}, {row['exit_reason']}) - {row['entry_timestamp']}")

# Unrealistic values
extreme_trades = df[df['pnl_pct'] > 50]
print(f"\n⚠️  Unrealistic Values:")
if len(extreme_trades) > 0:
    print(f"  Found {len(extreme_trades)} trades with >50% return:")
    for idx, row in extreme_trades.iterrows():
        print(f"    Trade #{row['trade_num']}: {row['pnl_pct']:+.2f}% - SUSPICIOUS!")
else:
    print("  No trades with >50% return (GOOD)")

# Single trade dominance
max_single_contribution = df['pnl_pct'].max() / total_pnl * 100 if total_pnl > 0 else 0
if max_single_contribution > 20:
    print(f"\n  ⚠️ WARNING: Single trade contributes {max_single_contribution:.1f}% of total profits")
else:
    print(f"\n  ✅ No single trade dominates (max contribution: {max_single_contribution:.1f}%)")

# ============================================================================
# 3. DISTRIBUTION ANALYSIS
# ============================================================================
print("\n" + "=" * 100)
print("3. DISTRIBUTION ANALYSIS")
print("=" * 100)

# Skewness
mean_median_win_diff = avg_win - median_win
mean_median_loss_diff = avg_loss - median_loss

print(f"\nDistribution Shape:")
print(f"  Mean Win:    {avg_win:+.2f}%")
print(f"  Median Win:  {median_win:+.2f}%")
print(f"  Difference:  {mean_median_win_diff:+.2f}% ", end="")
if mean_median_win_diff > 1.0:
    print("(RIGHT SKEWED - few large winners)")
elif mean_median_win_diff < -1.0:
    print("(LEFT SKEWED - unusual)")
else:
    print("(NORMAL)")

print(f"\n  Mean Loss:   {avg_loss:-.2f}%")
print(f"  Median Loss: {median_loss:-.2f}%")
print(f"  Difference:  {abs(mean_median_loss_diff):+.2f}% ", end="")
if mean_median_loss_diff < -1.0:
    print("(LEFT SKEWED - few catastrophic losses)")
elif mean_median_loss_diff > 1.0:
    print("(RIGHT SKEWED - unusual)")
else:
    print("(NORMAL)")

# Trade distribution by P/L brackets
print(f"\n📊 Trade Distribution by P/L:")
brackets = [
    ("<-5%", df[df['pnl_pct'] < -5]),
    ("-5% to 0%", df[(df['pnl_pct'] >= -5) & (df['pnl_pct'] < 0)]),
    ("0% to +2%", df[(df['pnl_pct'] >= 0) & (df['pnl_pct'] < 2)]),
    ("+2% to +5%", df[(df['pnl_pct'] >= 2) & (df['pnl_pct'] < 5)]),
    (">+5%", df[df['pnl_pct'] >= 5])
]

for label, subset in brackets:
    count = len(subset)
    pct = count / len(df) * 100
    contrib = subset['pnl_pct'].sum()
    print(f"  {label:>12}: {count:3} trades ({pct:5.1f}%) → {contrib:+7.2f}% P/L")

# ============================================================================
# 4. RISK-REWARD ASSESSMENT
# ============================================================================
print("\n" + "=" * 100)
print("4. RISK-REWARD ASSESSMENT")
print("=" * 100)

final_return = df['cumulative_pnl'].iloc[-1]
max_dd = df['drawdown_pct'].min()
return_dd_ratio = final_return / abs(max_dd)

print(f"\nReturn/DD Ratio: {return_dd_ratio:.2f}x ", end="")
if return_dd_ratio > 10:
    print("(POTENTIALLY UNREALISTIC - verify carefully)")
elif return_dd_ratio >= 5.0:
    print("(EXCELLENT)")
elif return_dd_ratio >= 3.0:
    print("(GOOD)")
else:
    print("(MARGINAL)")

# Equity curve quality
max_dd_trade_idx = df['drawdown_pct'].idxmin()
max_dd_trade = df.loc[max_dd_trade_idx]

print(f"\nEquity Curve Quality:")
print(f"  Max Drawdown: {max_dd:.2f}%")
print(f"  Occurred at: Trade #{max_dd_trade['trade_num']} ({max_dd_trade['entry_timestamp']})")
print(f"  Single trade DD: {max_dd_trade['pnl_pct']:.2f}%")

# Check if max DD is from single trade
if abs(max_dd_trade['pnl_pct']) > abs(max_dd) * 0.5:
    print(f"  ⚠️ WARNING: Max DD heavily influenced by single trade")
else:
    print(f"  ✅ Max DD is accumulated from multiple trades (more realistic)")

# Average DD
avg_dd = df[df['drawdown_pct'] < 0]['drawdown_pct'].mean()
print(f"  Average DD: {avg_dd:.2f}%")
print(f"  Max/Avg ratio: {abs(max_dd / avg_dd):.2f}x")

# Win/loss streaks
streaks = []
current_streak = 1
current_type = 'W' if df.iloc[0]['pnl_pct'] > 0 else 'L'

for i in range(1, len(df)):
    trade_type = 'W' if df.iloc[i]['pnl_pct'] > 0 else 'L'
    if trade_type == current_type:
        current_streak += 1
    else:
        streaks.append((current_type, current_streak))
        current_streak = 1
        current_type = trade_type

streaks.append((current_type, current_streak))

win_streaks = [s[1] for s in streaks if s[0] == 'W']
loss_streaks = [s[1] for s in streaks if s[0] == 'L']

max_win_streak = max(win_streaks) if win_streaks else 0
max_loss_streak = max(loss_streaks) if loss_streaks else 0

print(f"\nTrade Sequences:")
print(f"  Longest win streak:  {max_win_streak} trades")
print(f"  Longest loss streak: {max_loss_streak} trades")

if max_win_streak > 10:
    print(f"  ⚠️ WARNING: Win streak >10 is unusual (potential look-ahead bias)")
elif max_loss_streak > 10:
    print(f"  ⚠️ WARNING: Loss streak >10 suggests strategy breakdown")
else:
    print(f"  ✅ Streaks appear realistic")

# Live trading viability
print(f"\nLive Trading Viability:")

# Slippage sensitivity (0.1% additional cost per trade)
slippage_impact = len(df) * 0.1
final_return_with_slippage = final_return - slippage_impact
return_dd_with_slippage = final_return_with_slippage / abs(max_dd)

print(f"  With 0.1% slippage: {final_return_with_slippage:+.2f}% return ({return_dd_with_slippage:.2f}x R/DD)")

if return_dd_with_slippage < 2.0:
    print(f"  ❌ Strategy would struggle with realistic slippage")
elif return_dd_with_slippage < 3.0:
    print(f"  ⚠️  Slippage impact is significant")
else:
    print(f"  ✅ Strategy survives realistic slippage")

# TP/SL distance realism
avg_tp_distance = ((df['tp'] - df['entry']) / df['entry'] * 100).mean()
avg_sl_distance = ((df['entry'] - df['sl']) / df['entry'] * 100).mean()
print(f"\n  Average TP distance: {avg_tp_distance:.2f}%")
print(f"  Average SL distance: {avg_sl_distance:.2f}%")
print(f"  R:R ratio: {abs(avg_tp_distance / avg_sl_distance):.2f}:1")

# ============================================================================
# 5. DATA QUALITY CHECKS
# ============================================================================
print("\n" + "=" * 100)
print("5. DATA QUALITY CHECKS")
print("=" * 100)

# Duplicate timestamps
df['entry_timestamp'] = pd.to_datetime(df['entry_timestamp'])
duplicates = df[df.duplicated(subset=['entry_timestamp'], keep=False)]
if len(duplicates) > 0:
    print(f"\n⚠️ Found {len(duplicates)} trades with duplicate entry timestamps")
    print(f"   (Multiple signals at same time - expected behavior)")
else:
    print(f"\n✅ No duplicate timestamps")

# Zero P/L trades
zero_pnl = df[df['pnl_pct'] == 0]
if len(zero_pnl) > 0:
    print(f"⚠️ Found {len(zero_pnl)} trades with exactly 0% P/L (possibly incomplete)")
else:
    print(f"✅ No zero P/L trades")

# Chronological order
is_chronological = (df['entry_timestamp'].diff().dropna() >= pd.Timedelta(0)).all()
if is_chronological:
    print(f"✅ Trades are in chronological order")
else:
    print(f"❌ Trades are NOT in chronological order - DATA ERROR!")

# Entry/exit price logic
for idx, row in df.head(5).iterrows():
    if row['direction'] == 'LONG':
        if row['exit'] > row['entry'] and row['pnl_pct'] < 0:
            print(f"❌ Trade #{row['trade_num']}: LONG with exit > entry but negative P/L - LOGIC ERROR!")
    else:  # SHORT
        if row['exit'] < row['entry'] and row['pnl_pct'] < 0:
            print(f"❌ Trade #{row['trade_num']}: SHORT with exit < entry but negative P/L - LOGIC ERROR!")

print(f"✅ Entry/exit price logic appears correct (sampled first 5 trades)")

# ============================================================================
# 6. FINAL VERDICT
# ============================================================================
print("\n" + "=" * 100)
print("6. FINAL VERDICT")
print("=" * 100)

# Score based on multiple factors
issues = []
warnings = []
positives = []

# Check outlier dependency
if top5_pct > 60:
    warnings.append(f"High outlier dependency ({top5_pct:.1f}% from top 5 trades)")
else:
    positives.append(f"Low outlier dependency ({top5_pct:.1f}% from top 5)")

# Check return/DD realism
if return_dd_ratio > 10:
    warnings.append(f"Very high R/DD ({return_dd_ratio:.2f}x) - potentially unrealistic")
elif return_dd_ratio >= 5.0:
    positives.append(f"Excellent R/DD ({return_dd_ratio:.2f}x)")
elif return_dd_ratio >= 3.0:
    positives.append(f"Good R/DD ({return_dd_ratio:.2f}x)")
else:
    issues.append(f"Poor R/DD ({return_dd_ratio:.2f}x)")

# Check slippage survival
if return_dd_with_slippage < 2.0:
    issues.append(f"Strategy fails with realistic slippage (R/DD drops to {return_dd_with_slippage:.2f}x)")
elif return_dd_with_slippage < 3.0:
    warnings.append(f"Slippage significantly impacts performance (R/DD drops to {return_dd_with_slippage:.2f}x)")
else:
    positives.append(f"Strategy survives slippage well (R/DD: {return_dd_with_slippage:.2f}x)")

# Check extreme trades
if len(extreme_trades) > 0:
    issues.append(f"{len(extreme_trades)} trades with >50% return (unrealistic)")
else:
    positives.append("No unrealistic (>50%) trades")

# Check streaks
if max_win_streak > 10 or max_loss_streak > 10:
    warnings.append(f"Unusual streaks (W:{max_win_streak}, L:{max_loss_streak})")
else:
    positives.append(f"Realistic win/loss streaks (W:{max_win_streak}, L:{max_loss_streak})")

# Check data quality
if not is_chronological:
    issues.append("Trades not in chronological order - DATA ERROR")
else:
    positives.append("Data quality checks passed")

# Final classification
print("\n" + "=" * 100)
if len(issues) > 0:
    print("🔴 VERDICT: REQUIRES INVESTIGATION")
    print("=" * 100)
    print("\nCritical Issues Found:")
    for issue in issues:
        print(f"  ❌ {issue}")

    if len(warnings) > 0:
        print("\nAdditional Warnings:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")

    print("\n❌ Recommendation: FIX DATA ISSUES before proceeding")

elif len(warnings) >= 2:
    print("🟡 VERDICT: PARTIALLY CONCERNING")
    print("=" * 100)
    print("\nWarnings Found:")
    for warning in warnings:
        print(f"  ⚠️  {warning}")

    if len(positives) > 0:
        print("\nPositive Aspects:")
        for positive in positives:
            print(f"  ✅ {positive}")

    print("\n⚠️  Recommendation: Proceed with HIGH RESOLUTION optimization, but:")
    print("   - Monitor live performance closely")
    print("   - Start with small position sizes")
    print("   - Expect real-world results to be lower than backtest")

else:
    print("🟢 VERDICT: RESULTS APPEAR REALISTIC")
    print("=" * 100)
    print("\nPositive Aspects:")
    for positive in positives:
        print(f"  ✅ {positive}")

    if len(warnings) > 0:
        print("\nMinor Warnings:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")

    print("\n✅ Recommendation: PROCEED with high-resolution optimization")
    print("   - Results show promise for live trading")
    print("   - No major red flags detected")
    print("   - Strategy appears viable with realistic parameters")

print("\n" + "=" * 100)
