"""
PEPE Master Optimization - Final Visualization
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Read data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/PEPE_OPTIMIZATION_SUMMARY.csv')

print('='*80)
print('PEPE MASTER OPTIMIZATION RESULTS')
print('='*80)
print(df.to_string(index=False))
print('='*80)

# Create comprehensive visualization
fig = plt.figure(figsize=(18, 12))
gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3)

fig.suptitle('PEPE Master Optimization - Complete Analysis', fontsize=18, fontweight='bold', y=0.98)

configs = df['Configuration'].values
descriptions = df['Description'].values

# 1. Total Return Comparison
ax1 = fig.add_subplot(gs[0, :2])
colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E', '#06A77D']
bars = ax1.barh(configs, df['Total_Return_%'], color=colors, alpha=0.8, edgecolor='black', linewidth=2)
for i, (bar, val) in enumerate(zip(bars, df['Total_Return_%'])):
    ax1.text(val + 5, bar.get_y() + bar.get_height()/2, f'{val:.2f}%',
             va='center', ha='left', fontweight='bold', fontsize=10)
ax1.set_xlabel('Total Return (%)', fontweight='bold', fontsize=12)
ax1.set_title('Total Return Comparison (30 days)', fontweight='bold', fontsize=14)
ax1.grid(axis='x', alpha=0.3, linestyle='--')
ax1.axvline(x=38.79, color='red', linestyle='--', linewidth=2, label='Original Baseline', alpha=0.7)
ax1.legend()

# 2. Win Rate vs Return Scatter
ax2 = fig.add_subplot(gs[0, 2])
scatter = ax2.scatter(df['Win_Rate_%'], df['Total_Return_%'], 
                     s=df['Total_Trades']/2, alpha=0.6, c=range(len(df)), cmap='viridis',
                     edgecolors='black', linewidth=2)
for i, config in enumerate(configs):
    ax2.annotate(config, (df['Win_Rate_%'].iloc[i], df['Total_Return_%'].iloc[i]),
                fontsize=8, ha='center', va='bottom')
ax2.set_xlabel('Win Rate (%)', fontweight='bold')
ax2.set_ylabel('Total Return (%)', fontweight='bold')
ax2.set_title('Win Rate vs Return\n(size = trade count)', fontweight='bold')
ax2.grid(True, alpha=0.3, linestyle='--')

# 3. Sharpe Ratio Comparison
ax3 = fig.add_subplot(gs[1, 0])
bars = ax3.bar(range(len(configs)), df['Sharpe_Ratio'], color=colors, alpha=0.8, edgecolor='black', linewidth=2)
for i, (bar, val) in enumerate(zip(bars, df['Sharpe_Ratio'])):
    ax3.text(bar.get_x() + bar.get_width()/2, val + 0.02, f'{val:.2f}',
             ha='center', va='bottom', fontweight='bold', fontsize=9)
ax3.set_xticks(range(len(configs)))
ax3.set_xticklabels(configs, rotation=45, ha='right', fontsize=9)
ax3.set_ylabel('Sharpe Ratio', fontweight='bold')
ax3.set_title('Risk-Adjusted Returns (Sharpe)', fontweight='bold')
ax3.grid(axis='y', alpha=0.3, linestyle='--')
ax3.axhline(y=0.11, color='red', linestyle='--', linewidth=2, alpha=0.7)

# 4. Max Drawdown Comparison
ax4 = fig.add_subplot(gs[1, 1])
bars = ax4.bar(range(len(configs)), df['Max_DD_%'], color=colors, alpha=0.8, edgecolor='black', linewidth=2)
for i, (bar, val) in enumerate(zip(bars, df['Max_DD_%'])):
    ax4.text(bar.get_x() + bar.get_width()/2, val - 0.3, f'{val:.2f}%',
             ha='center', va='top', fontweight='bold', fontsize=9, color='white')
ax4.set_xticks(range(len(configs)))
ax4.set_xticklabels(configs, rotation=45, ha='right', fontsize=9)
ax4.set_ylabel('Max Drawdown (%)', fontweight='bold')
ax4.set_title('Maximum Drawdown (lower is better)', fontweight='bold')
ax4.grid(axis='y', alpha=0.3, linestyle='--')
ax4.axhline(y=-6.84, color='red', linestyle='--', linewidth=2, alpha=0.7)

# 5. Trade Count Comparison
ax5 = fig.add_subplot(gs[1, 2])
bars = ax5.bar(range(len(configs)), df['Total_Trades'], color=colors, alpha=0.8, edgecolor='black', linewidth=2)
for i, (bar, val) in enumerate(zip(bars, df['Total_Trades'])):
    ax5.text(bar.get_x() + bar.get_width()/2, val + 20, f'{val}',
             ha='center', va='bottom', fontweight='bold', fontsize=9)
ax5.set_xticks(range(len(configs)))
ax5.set_xticklabels(configs, rotation=45, ha='right', fontsize=9)
ax5.set_ylabel('Total Trades', fontweight='bold')
ax5.set_title('Trade Frequency (30 days)', fontweight='bold')
ax5.grid(axis='y', alpha=0.3, linestyle='--')
ax5.axhline(y=923, color='red', linestyle='--', linewidth=2, alpha=0.7)

# 6. Avg Trade % Comparison
ax6 = fig.add_subplot(gs[2, 0])
bars = ax6.bar(range(len(configs)), df['Avg_Trade_%'], color=colors, alpha=0.8, edgecolor='black', linewidth=2)
for i, (bar, val) in enumerate(zip(bars, df['Avg_Trade_%'])):
    ax6.text(bar.get_x() + bar.get_width()/2, val + 0.005, f'{val:.3f}%',
             ha='center', va='bottom', fontweight='bold', fontsize=9)
ax6.set_xticks(range(len(configs)))
ax6.set_xticklabels(configs, rotation=45, ha='right', fontsize=9)
ax6.set_ylabel('Avg Trade (%)', fontweight='bold')
ax6.set_title('Average Trade Return', fontweight='bold')
ax6.grid(axis='y', alpha=0.3, linestyle='--')
ax6.axhline(y=0.042, color='red', linestyle='--', linewidth=2, alpha=0.7)

# 7. Fee Comparison
ax7 = fig.add_subplot(gs[2, 1])
fees_data = df.groupby('Fees_%').size()
colors_fees = ['#C73E1D' if f == 0.07 else '#06A77D' for f in df['Fees_%']]
bars = ax7.bar(range(len(configs)), df['Fees_%'], color=colors_fees, alpha=0.8, edgecolor='black', linewidth=2)
for i, (bar, val) in enumerate(zip(bars, df['Fees_%'])):
    ax7.text(bar.get_x() + bar.get_width()/2, val + 0.002, f'{val:.2f}%',
             ha='center', va='bottom', fontweight='bold', fontsize=9)
ax7.set_xticks(range(len(configs)))
ax7.set_xticklabels(configs, rotation=45, ha='right', fontsize=9)
ax7.set_ylabel('Fees (%)', fontweight='bold')
ax7.set_title('Fee Structure (lower is better)', fontweight='bold')
ax7.grid(axis='y', alpha=0.3, linestyle='--')

# 8. Summary Table
ax8 = fig.add_subplot(gs[2, 2])
ax8.axis('off')
summary_text = "KEY FINDINGS\\n\\n"
summary_text += "🏆 BEST OVERALL:\\n"
summary_text += "   Limit -0.15%\\n"
summary_text += "   +190.93% return\\n"
summary_text += "   81.8% win rate\\n"
summary_text += "   Sharpe 0.60\\n\\n"
summary_text += "📊 vs BASELINE:\\n"
summary_text += "   +152% extra return\\n"
summary_text += "   +20% win rate\\n"
summary_text += "   5.5× Sharpe ratio\\n"
summary_text += "   -51% drawdown\\n\\n"
summary_text += "⚡ KEY INSIGHT:\\n"
summary_text += "   Limit orders are\\n"
summary_text += "   the game changer!"

ax8.text(0.1, 0.95, summary_text, transform=ax8.transAxes, fontsize=11,
        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
        fontfamily='monospace', fontweight='bold')

plt.savefig('/workspaces/Carebiuro_windykacja/trading/results/PEPE_optimization_final.png',
            dpi=300, bbox_inches='tight')
print('\\n✅ Saved: PEPE_optimization_final.png')
print('='*80)

