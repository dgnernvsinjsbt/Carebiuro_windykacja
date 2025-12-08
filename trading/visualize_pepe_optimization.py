"""
Visualize PEPE Optimization Results - Before/After Comparison
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Read comparison data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/PEPE_optimization_comparison.csv')

print(df)

# Create comparison visualization
fig, axes = plt.subplots(2, 3, figsize=(16, 10))
fig.suptitle('PEPE Strategy Optimization - Before vs After', fontsize=16, fontweight='bold')

# Metrics to compare
metrics = [
    ('Total_Return_%', 'Total Return (%)', 'green'),
    ('Win_Rate_%', 'Win Rate (%)', 'blue'),
    ('Sharpe_Ratio', 'Sharpe Ratio', 'purple'),
    ('Max_DD_%', 'Max Drawdown (%)', 'red'),
    ('Total_Trades', 'Total Trades', 'orange'),
    ('Avg_Trade_%', 'Avg Trade (%)', 'teal')
]

for idx, (col, title, color) in enumerate(metrics):
    ax = axes[idx // 3, idx % 3]

    values = df[col].values
    configs = df['Configuration'].values

    bars = ax.bar(configs, values, color=[color, '#2E86AB'], alpha=0.7, edgecolor='black', linewidth=2)

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Calculate improvement
    if len(values) == 2:
        improvement = values[1] - values[0]
        improvement_pct = (improvement / abs(values[0]) * 100) if values[0] != 0 else 0
        ax.text(0.5, 0.95, f'Change: {improvement:+.2f} ({improvement_pct:+.1f}%)',
                transform=ax.transAxes, ha='center', va='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                fontweight='bold')

    ax.set_title(title, fontweight='bold', fontsize=12)
    ax.set_ylabel(title, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

plt.tight_layout()
plt.savefig('/workspaces/Carebiuro_windykacja/trading/results/PEPE_optimization_comparison.png',
            dpi=300, bbox_inches='tight')
print('\n✅ Saved: PEPE_optimization_comparison.png')

# Create summary text
print('\n' + '='*80)
print('OPTIMIZATION SUMMARY')
print('='*80)
print(df.to_string(index=False))
print('='*80)

