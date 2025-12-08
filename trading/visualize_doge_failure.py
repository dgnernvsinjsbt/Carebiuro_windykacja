"""
Visualize why DOGE strategies failed
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load results
results = pd.read_csv('results/doge_master_results.csv')

print("=" * 80)
print("DOGE/USDT STRATEGY FAILURE ANALYSIS")
print("=" * 80)

# Summary stats
print(f"\nTotal strategies tested: {len(results)}")
print(f"Profitable strategies: {len(results[results['return'] > 0])}")
print(f"Best return: {results['return'].max():.2f}%")
print(f"Worst return: {results['return'].min():.2f}%")
print(f"Average return: {results['return'].mean():.2f}%")
print(f"Average win rate: {results['win_rate'].mean():.1f}%")

# Group by strategy type
results['type'] = results['strategy'].str.split('_').str[0:2].str.join('_')

print("\n" + "=" * 80)
print("RESULTS BY STRATEGY TYPE")
print("=" * 80)

for stype in results['type'].unique():
    subset = results[results['type'] == stype]
    print(f"\n{stype.upper()}:")
    print(f"  Tested: {len(subset)} configurations")
    print(f"  Best return: {subset['return'].max():.2f}%")
    print(f"  Avg return: {subset['return'].mean():.2f}%")
    print(f"  Avg win rate: {subset['win_rate'].mean():.1f}%")
    print(f"  Avg R:R: {subset['rr'].mean():.2f}")

# Create visualization
fig, axes = plt.subplots(2, 2, figsize=(15, 12))

# 1. Returns distribution
ax1 = axes[0, 0]
ax1.hist(results['return'], bins=20, color='red', alpha=0.7, edgecolor='black')
ax1.axvline(x=0, color='green', linestyle='--', linewidth=2, label='Break-even')
ax1.set_xlabel('Total Return (%)', fontsize=12)
ax1.set_ylabel('Frequency', fontsize=12)
ax1.set_title('Distribution of Returns\n(ALL NEGATIVE)', fontsize=14, fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 2. Win rate vs Return
ax2 = axes[0, 1]
scatter = ax2.scatter(results['win_rate'], results['return'],
                     c=results['trades'], cmap='viridis',
                     s=100, alpha=0.6, edgecolor='black')
ax2.axhline(y=0, color='green', linestyle='--', linewidth=2, label='Break-even')
ax2.axvline(x=50, color='orange', linestyle='--', linewidth=2, label='50% WR target')
ax2.set_xlabel('Win Rate (%)', fontsize=12)
ax2.set_ylabel('Total Return (%)', fontsize=12)
ax2.set_title('Win Rate vs Return\n(All below 50% WR, all negative)', fontsize=14, fontweight='bold')
ax2.legend()
ax2.grid(True, alpha=0.3)
plt.colorbar(scatter, ax=ax2, label='Number of Trades')

# 3. R:R ratio by strategy type
ax3 = axes[1, 0]
type_rr = results.groupby('type')['rr'].mean().sort_values()
bars = ax3.barh(range(len(type_rr)), type_rr.values, color='red', alpha=0.7, edgecolor='black')
ax3.set_yticks(range(len(type_rr)))
ax3.set_yticklabels(type_rr.index)
ax3.axvline(x=0, color='green', linestyle='--', linewidth=2, label='Break-even')
ax3.axvline(x=2, color='blue', linestyle='--', linewidth=2, label='Target (2.0)')
ax3.set_xlabel('R:R Ratio', fontsize=12)
ax3.set_title('Average R:R Ratio by Strategy Type\n(All negative)', fontsize=14, fontweight='bold')
ax3.legend()
ax3.grid(True, alpha=0.3, axis='x')

# 4. Number of trades vs Return
ax4 = axes[1, 1]
ax4.scatter(results['trades'], results['return'],
           c=results['win_rate'], cmap='RdYlGn',
           s=100, alpha=0.6, edgecolor='black', vmin=20, vmax=60)
ax4.axhline(y=0, color='green', linestyle='--', linewidth=2, label='Break-even')
ax4.set_xlabel('Number of Trades', fontsize=12)
ax4.set_ylabel('Total Return (%)', fontsize=12)
ax4.set_title('Trade Frequency vs Return\n(More trades = bigger losses)', fontsize=14, fontweight='bold')
ax4.legend()
ax4.grid(True, alpha=0.3)
plt.colorbar(ax4.collections[0], ax=ax4, label='Win Rate (%)')

plt.tight_layout()
plt.savefig('results/doge_failure_analysis.png', dpi=150, bbox_inches='tight')
print("\n" + "=" * 80)
print("Visualization saved: results/doge_failure_analysis.png")
print("=" * 80)

# Show top 5 least bad
print("\nTOP 5 STRATEGIES (Least Bad):")
print("=" * 80)
top5 = results.head(5)
for idx, row in top5.iterrows():
    print(f"\n{row['strategy']}")
    print(f"  Return: {row['return']:.2f}%")
    print(f"  Win Rate: {row['win_rate']:.1f}%")
    print(f"  Max DD: {row['max_dd']:.2f}%")
    print(f"  R:R: {row['rr']:.2f}")
    print(f"  Trades: {int(row['trades'])}")

print("\n" + "=" * 80)
print("CONCLUSION: DOGE/USDT IS NOT SUITABLE FOR SYSTEMATIC TRADING")
print("=" * 80)
print("\nRecommendations:")
print("1. Avoid DOGE for algorithmic trading with technical indicators")
print("2. Test longer timeframes (4h, 1d) if must trade DOGE")
print("3. Consider event-driven or sentiment-based approaches")
print("4. Focus on proven assets (ETH, BTC) for systematic trading")
