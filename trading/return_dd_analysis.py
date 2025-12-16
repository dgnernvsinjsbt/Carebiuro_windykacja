#!/usr/bin/env python3
"""
Calculate Return/DD ratio for each coin (100% position sizing)
"""

import pandas as pd

# Data from simulation
coins_data = [
    {'symbol': 'MELANIA-USDT', 'return_pct': 123.76, 'max_dd_pct': -2.86, 'final': 22.38, 'trades': 10, 'win_rate': 80.0},
    {'symbol': 'XLM-USDT', 'return_pct': 33.78, 'max_dd_pct': -2.06, 'final': 13.38, 'trades': 16, 'win_rate': 81.2},
    {'symbol': 'DOGE-USDT', 'return_pct': 32.92, 'max_dd_pct': -2.19, 'final': 13.29, 'trades': 17, 'win_rate': 94.1},
    {'symbol': 'UNI-USDT', 'return_pct': 29.95, 'max_dd_pct': -3.88, 'final': 12.99, 'trades': 21, 'win_rate': 76.2},
    {'symbol': 'CRV-USDT', 'return_pct': 29.16, 'max_dd_pct': -1.70, 'final': 12.92, 'trades': 14, 'win_rate': 85.7},
    {'symbol': 'PEPE-USDT', 'return_pct': 27.92, 'max_dd_pct': -9.41, 'final': 12.79, 'trades': 26, 'win_rate': 73.1},
    {'symbol': 'MOODENG-USDT', 'return_pct': 26.64, 'max_dd_pct': -13.44, 'final': 12.66, 'trades': 27, 'win_rate': 63.0},
    {'symbol': 'AIXBT-USDT', 'return_pct': 26.30, 'max_dd_pct': -12.10, 'final': 12.63, 'trades': 33, 'win_rate': 63.6},
    {'symbol': 'TRUMPSOL-USDT', 'return_pct': 13.78, 'max_dd_pct': -6.22, 'final': 11.38, 'trades': 14, 'win_rate': 78.6},
]

df = pd.DataFrame(coins_data)

# Calculate Return/DD ratio
df['return_dd_ratio'] = df['return_pct'] / abs(df['max_dd_pct'])

# Sort by Return/DD ratio
df = df.sort_values('return_dd_ratio', ascending=False)

print("=" * 100)
print("RETURN/DD RATIO ANALYSIS (100% Position Sizing per Coin)")
print("=" * 100)
print("\nHigher ratio = Better risk-adjusted returns\n")

print(f"{'Rank':<5} {'Coin':<15} {'Return%':>10} {'Max DD%':>10} {'R/DD Ratio':>12} {'Final $':>10} {'Trades':>8} {'Win%':>7}")
print("-" * 100)

for idx, (_, row) in enumerate(df.iterrows(), 1):
    # Rating based on R/DD ratio
    if row['return_dd_ratio'] > 15:
        rating = "🏆 EXCELLENT"
    elif row['return_dd_ratio'] > 10:
        rating = "⭐ GREAT"
    elif row['return_dd_ratio'] > 5:
        rating = "✅ GOOD"
    elif row['return_dd_ratio'] > 3:
        rating = "⚠️ OKAY"
    else:
        rating = "❌ POOR"

    print(f"{idx:<5} {row['symbol']:<15} {row['return_pct']:>9.2f}% {row['max_dd_pct']:>9.2f}% "
          f"{row['return_dd_ratio']:>11.2f}x ${row['final']:>9.2f} {row['trades']:>8} {row['win_rate']:>6.1f}%  {rating}")

print("-" * 100)

# Portfolio totals
total_return = 38.25
total_dd = -5.98
portfolio_ratio = total_return / abs(total_dd)

print(f"{'PORTFOLIO':<5} {'(Weighted Avg)':<15} {total_return:>9.2f}% {total_dd:>9.2f}% "
      f"{portfolio_ratio:>11.2f}x ${'124.42':>9} {168:>8} {74.4:>6.1f}%")

print("\n" + "=" * 100)
print("INSIGHTS:")
print("=" * 100)

best = df.iloc[0]
worst = df.iloc[-1]

print(f"\n🏆 BEST RISK-ADJUSTED: {best['symbol']}")
print(f"   Return: {best['return_pct']:.2f}% | Max DD: {best['max_dd_pct']:.2f}% | Ratio: {best['return_dd_ratio']:.2f}x")
print(f"   → Every 1% of risk generated {best['return_dd_ratio']:.2f}% of return")

print(f"\n❌ WORST RISK-ADJUSTED: {worst['symbol']}")
print(f"   Return: {worst['return_pct']:.2f}% | Max DD: {worst['max_dd_pct']:.2f}% | Ratio: {worst['return_dd_ratio']:.2f}x")
print(f"   → Every 1% of risk only generated {worst['return_dd_ratio']:.2f}% of return")

# Tier analysis
excellent = df[df['return_dd_ratio'] > 15]
great = df[(df['return_dd_ratio'] > 10) & (df['return_dd_ratio'] <= 15)]
good = df[(df['return_dd_ratio'] > 5) & (df['return_dd_ratio'] <= 10)]
okay = df[(df['return_dd_ratio'] > 3) & (df['return_dd_ratio'] <= 5)]
poor = df[df['return_dd_ratio'] <= 3]

print(f"\n📊 TIER BREAKDOWN:")
print(f"   🏆 EXCELLENT (>15x):  {len(excellent)} coins - {', '.join(excellent['symbol'].str.replace('-USDT', '').tolist())}")
print(f"   ⭐ GREAT (10-15x):    {len(great)} coins - {', '.join(great['symbol'].str.replace('-USDT', '').tolist()) if len(great) > 0 else 'None'}")
print(f"   ✅ GOOD (5-10x):      {len(good)} coins - {', '.join(good['symbol'].str.replace('-USDT', '').tolist()) if len(good) > 0 else 'None'}")
print(f"   ⚠️ OKAY (3-5x):       {len(okay)} coins - {', '.join(okay['symbol'].str.replace('-USDT', '').tolist()) if len(okay) > 0 else 'None'}")
print(f"   ❌ POOR (<3x):        {len(poor)} coins - {', '.join(poor['symbol'].str.replace('-USDT', '').tolist()) if len(poor) > 0 else 'None'}")

print(f"\n💡 KEY TAKEAWAYS:")

print(f"\n1. TOP 3 RISK-ADJUSTED PERFORMERS:")
for i, (_, row) in enumerate(df.head(3).iterrows(), 1):
    print(f"   {i}. {row['symbol']:15} {row['return_dd_ratio']:5.2f}x  (Return: {row['return_pct']:6.2f}%, DD: {row['max_dd_pct']:6.2f}%)")

print(f"\n2. HIGH RETURN BUT RISKY:")
risky = df[df['max_dd_pct'] < -10]
if len(risky) > 0:
    for _, row in risky.iterrows():
        print(f"   • {row['symbol']:15} DD: {row['max_dd_pct']:.2f}% (ratio: {row['return_dd_ratio']:.2f}x)")
        print(f"     → With 10x leverage: {row['max_dd_pct'] * 10:.1f}% account loss!")

print(f"\n3. SAFEST COINS (Lowest Max DD):")
safest = df.nsmallest(3, 'max_dd_pct', keep='first')
for _, row in safest.iterrows():
    print(f"   • {row['symbol']:15} DD: {row['max_dd_pct']:.2f}% | Return: {row['return_pct']:.2f}% | Ratio: {row['return_dd_ratio']:.2f}x")

print(f"\n4. PORTFOLIO EFFICIENCY:")
print(f"   Portfolio R/DD: {portfolio_ratio:.2f}x")
avg_individual = df['return_dd_ratio'].mean()
print(f"   Avg Individual: {avg_individual:.2f}x")
if portfolio_ratio > avg_individual:
    print(f"   ✅ Portfolio diversification IMPROVED risk-adjusted returns by {((portfolio_ratio/avg_individual - 1) * 100):.1f}%")
else:
    print(f"   ⚠️ Portfolio diversification REDUCED risk-adjusted returns by {((1 - portfolio_ratio/avg_individual) * 100):.1f}%")

print(f"\n💀 LEVERAGE SAFETY:")
print(f"   Safest coin:  {df.nsmallest(1, 'max_dd_pct')['symbol'].values[0]} (DD: {df.nsmallest(1, 'max_dd_pct')['max_dd_pct'].values[0]:.2f}%)")
print(f"   Riskiest coin: {df.nlargest(1, 'max_dd_pct')['symbol'].values[0]} (DD: {df.nlargest(1, 'max_dd_pct')['max_dd_pct'].values[0]:.2f}%)")
print(f"\n   With 10x leverage on riskiest coin: {df.nlargest(1, 'max_dd_pct')['max_dd_pct'].values[0] * 10:.1f}% account loss")
print(f"   With 5x leverage on riskiest coin: {df.nlargest(1, 'max_dd_pct')['max_dd_pct'].values[0] * 5:.1f}% account loss")
print(f"   With 3x leverage on riskiest coin: {df.nlargest(1, 'max_dd_pct')['max_dd_pct'].values[0] * 3:.1f}% account loss")
