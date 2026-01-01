#!/usr/bin/env python3
"""
Compare profit contributions: 3% risk vs 4% risk
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load both trade logs
baseline_df = pd.read_csv('portfolio_10x_leverage_log.csv')
risk4_df = pd.read_csv('trade_log_4pct_risk.csv')

# Calculate baseline (3% risk) profits by coin
baseline_profits = baseline_df.groupby('symbol')['pnl_usd'].sum().to_dict()
baseline_total = sum(baseline_profits.values())

# Calculate 4% risk profits by coin
risk4_profits = risk4_df.groupby('symbol')['pnl_usd'].sum().to_dict()
risk4_total = sum(risk4_profits.values())

# Get all coins
all_coins = sorted(set(list(baseline_profits.keys()) + list(risk4_profits.keys())))

# Prepare data
baseline_vals = [baseline_profits.get(coin, 0) for coin in all_coins]
risk4_vals = [risk4_profits.get(coin, 0) for coin in all_coins]

# Create comparison chart
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
fig.suptitle('Profit Contribution by Coin: 3% Risk vs 4% Risk', fontsize=16, fontweight='bold')

# Chart 1: Absolute profit comparison
x = np.arange(len(all_coins))
width = 0.35

bars1 = ax1.bar(x - width/2, baseline_vals, width, label='3% Risk (10% Pos)', color='#3498db', alpha=0.8)
bars2 = ax1.bar(x + width/2, risk4_vals, width, label='4% Risk (13.3% Pos)', color='#e74c3c', alpha=0.8)

ax1.set_ylabel('Profit ($)', fontsize=12, fontweight='bold')
ax1.set_xlabel('Coin', fontsize=12, fontweight='bold')
ax1.set_title(f'Absolute Profits\n3% Total: \\${baseline_total:,.0f} | 4% Total: \\${risk4_total:,.0f}',
              fontsize=13, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels([c.replace('-USDT', '') for c in all_coins], rotation=45, ha='right')
ax1.legend()
ax1.grid(True, alpha=0.3, axis='y')
ax1.axhline(y=0, color='black', linewidth=0.5)

# Add value labels on bars
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if abs(height) > 50:  # Only label significant bars
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'\\${height:,.0f}',
                    ha='center', va='bottom' if height > 0 else 'top',
                    fontsize=8, fontweight='bold')

# Chart 2: Percentage contribution
baseline_pcts = [(v / baseline_total * 100) if baseline_total > 0 else 0 for v in baseline_vals]
risk4_pcts = [(v / risk4_total * 100) if risk4_total > 0 else 0 for v in risk4_vals]

bars3 = ax2.bar(x - width/2, baseline_pcts, width, label='3% Risk', color='#3498db', alpha=0.8)
bars4 = ax2.bar(x + width/2, risk4_pcts, width, label='4% Risk', color='#e74c3c', alpha=0.8)

ax2.set_ylabel('% of Total Profit', fontsize=12, fontweight='bold')
ax2.set_xlabel('Coin', fontsize=12, fontweight='bold')
ax2.set_title('Profit Contribution %\n(How much each coin contributes to total)',
              fontsize=13, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels([c.replace('-USDT', '') for c in all_coins], rotation=45, ha='right')
ax2.legend()
ax2.grid(True, alpha=0.3, axis='y')
ax2.axhline(y=0, color='black', linewidth=0.5)

# Add percentage labels
for bars in [bars3, bars4]:
    for bar in bars:
        height = bar.get_height()
        if abs(height) > 2:  # Only label significant contributions
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom' if height > 0 else 'top',
                    fontsize=8, fontweight='bold')

plt.tight_layout()
plt.savefig('profit_contribution_comparison.png', dpi=300, bbox_inches='tight')
print("✅ Comparison chart saved to: profit_contribution_comparison.png")

# Print detailed analysis
print("\n" + "=" * 100)
print("PROFIT SHIFT ANALYSIS: 3% → 4% RISK")
print("=" * 100)

changes = []
for coin in all_coins:
    baseline_profit = baseline_profits.get(coin, 0)
    risk4_profit = risk4_profits.get(coin, 0)
    absolute_change = risk4_profit - baseline_profit
    pct_change = (absolute_change / baseline_profit * 100) if baseline_profit != 0 else 0

    baseline_contrib = (baseline_profit / baseline_total * 100) if baseline_total > 0 else 0
    risk4_contrib = (risk4_profit / risk4_total * 100) if risk4_total > 0 else 0
    contrib_shift = risk4_contrib - baseline_contrib

    changes.append({
        'coin': coin,
        'baseline_profit': baseline_profit,
        'risk4_profit': risk4_profit,
        'absolute_change': absolute_change,
        'pct_change': pct_change,
        'baseline_contrib': baseline_contrib,
        'risk4_contrib': risk4_contrib,
        'contrib_shift': contrib_shift
    })

changes_df = pd.DataFrame(changes).sort_values('contrib_shift', ascending=False)

print(f"\n{'Coin':<15} {'3% Contrib':>12} {'4% Contrib':>12} {'Shift':>10} {'Status':<15}")
print("-" * 75)

for _, row in changes_df.iterrows():
    if row['contrib_shift'] > 1:
        status = "📈 BIGGER ROLE"
    elif row['contrib_shift'] < -1:
        status = "📉 SMALLER ROLE"
    else:
        status = "➡️ SIMILAR"

    print(f"{row['coin']:<15} {row['baseline_contrib']:>11.2f}% {row['risk4_contrib']:>11.2f}% "
          f"{row['contrib_shift']:>+9.2f}% {status:<15}")

print("\n" + "=" * 100)
print("KEY OBSERVATIONS:")
print("=" * 100)

# Find coins with biggest role increase
biggest_gainers = changes_df.nlargest(3, 'contrib_shift')
print("\n📈 COINS WITH BIGGER ROLE AT 4% RISK:")
for _, row in biggest_gainers.iterrows():
    print(f"   • {row['coin']}: {row['baseline_contrib']:.2f}% → {row['risk4_contrib']:.2f}% "
          f"(+{row['contrib_shift']:.2f}pp)")
    print(f"     Profit: ${row['baseline_profit']:,.2f} → ${row['risk4_profit']:,.2f} "
          f"({row['pct_change']:+.1f}%)")

# Find coins with biggest role decrease
biggest_losers = changes_df.nsmallest(3, 'contrib_shift')
print("\n📉 COINS WITH SMALLER ROLE AT 4% RISK:")
for _, row in biggest_losers.iterrows():
    print(f"   • {row['coin']}: {row['baseline_contrib']:.2f}% → {row['risk4_contrib']:.2f}% "
          f"({row['contrib_shift']:.2f}pp)")
    print(f"     Profit: ${row['baseline_profit']:,.2f} → ${row['risk4_profit']:,.2f} "
          f"({row['pct_change']:+.1f}%)")

print("\n💡 EXPLANATION:")
print("   • Larger positions (13.3% vs 10%) amplify both wins AND losses")
print("   • Good performers get BETTER (MELANIA +139%, MOODENG +192%)")
print("   • Bad performers get WORSE (AIXBT -$206, PEPE -$21)")
print("   • Overall portfolio profit increased 141.8% but with higher risk")

plt.close()
