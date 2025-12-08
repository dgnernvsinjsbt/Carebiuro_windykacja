"""
Create visual comparison for TRUMP optimization
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load optimization results
results = pd.read_csv('results/TRUMP_optimization_comparison.csv')

# Create comparison chart
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Plot 1: Return Comparison
configs = results['config'].head(10)
returns = results['return'].head(10)

colors = ['green' if r > 0 else 'red' for r in returns]

ax1.barh(range(len(configs)), returns, color=colors, alpha=0.7)
ax1.set_yticks(range(len(configs)))
ax1.set_yticklabels(configs, fontsize=9)
ax1.set_xlabel('Return (%)', fontsize=12)
ax1.set_title('TRUMP Optimization Results\n(Top 10 Configurations)', fontsize=14, fontweight='bold')
ax1.axvline(x=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
ax1.grid(axis='x', alpha=0.3)

# Add base strategy line
ax1.axvline(x=-0.62, color='blue', linestyle='--', linewidth=2, label='Base Strategy (-0.62%)')
ax1.legend()

# Plot 2: Win Rate vs Return scatter
ax2.scatter(results['win_rate'], results['return'], s=results['trades']*2, alpha=0.6, c=results['return'], cmap='RdYlGn')
ax2.set_xlabel('Win Rate (%)', fontsize=12)
ax2.set_ylabel('Return (%)', fontsize=12)
ax2.set_title('Win Rate vs Return\n(Bubble size = # of trades)', fontsize=14, fontweight='bold')
ax2.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
ax2.axvline(x=33.3, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='Breakeven WR (33.3% for 1:2 R:R)')
ax2.grid(alpha=0.3)
ax2.legend()

# Annotate best config
best_idx = results['return'].idxmax()
best = results.loc[best_idx]
ax2.annotate(f"Best: {best['config']}\n{best['return']:.2f}%",
             xy=(best['win_rate'], best['return']),
             xytext=(best['win_rate']+5, best['return']+5),
             fontsize=9,
             bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.5),
             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

plt.tight_layout()
plt.savefig('results/TRUMP_optimization_comparison.png', dpi=300, bbox_inches='tight')
print("✓ Chart saved to: results/TRUMP_optimization_comparison.png")

# Create summary CSV
summary = {
    'Metric': [
        'Base Strategy Return',
        'Best Optimized Return',
        'Improvement',
        'Base Win Rate',
        'Best Win Rate',
        'Base Trades',
        'Best Trades',
        'Status'
    ],
    'Value': [
        '-0.62%',
        f"{best['return']:.2f}%",
        f"{best['return'] - (-0.62):.2f}%",
        '42.5%',
        f"{best['win_rate']:.1f}%",
        '287',
        f"{best['trades']:.0f}",
        'UNTRADEABLE' if best['return'] < 0 else 'TRADEABLE'
    ]
}

summary_df = pd.DataFrame(summary)
summary_df.to_csv('results/TRUMP_optimization_summary.csv', index=False)
print("✓ Summary saved to: results/TRUMP_optimization_summary.csv")

print("\nFINAL VERDICT:")
print("="*60)
print(f"Base Strategy:      -0.62% ({-0.62:.2f}%)")
print(f"Best Optimized:     {best['config']} → {best['return']:.2f}%")
print(f"Win Rate:           {best['win_rate']:.1f}%")
print(f"Total Trades:       {best['trades']:.0f}")
print("="*60)
if best['return'] > 0:
    print("✅ TRUMP IS TRADEABLE")
else:
    print("❌ TRUMP IS UNTRADEABLE - All configs unprofitable")
print("="*60)
