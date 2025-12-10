#!/usr/bin/env python3
"""
PI/USDT Strategy Visualization
===============================
Visualize the ultra-selective strategy performance.
"""

import pandas as pd
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# Load trades
trades = pd.read_csv('results/pi_ultra_selective_trades.csv')
trades['timestamp'] = pd.to_datetime(trades['timestamp'])

print("="*70)
print("PI/USDT ULTRA-SELECTIVE STRATEGY VISUALIZATION")
print("="*70)
print(f"\nTotal Trades: {len(trades)}")
print(f"Total Return: {trades['pnl_pct'].sum():.2f}%")
print(f"Win Rate: {(trades['pnl_pct'] > 0).mean()*100:.1f}%")
print(f"TP Rate: {(trades['exit_reason'] == 'TP').mean()*100:.1f}%")

# Calculate equity curve
trades['cumulative_pnl'] = (1 + trades['pnl_pct']/100).cumprod() - 1
trades['cumulative_pnl'] *= 100  # Convert to %

# Calculate drawdown
equity = (1 + trades['pnl_pct']/100).cumprod()
running_max = equity.expanding().max()
drawdown = (equity - running_max) / running_max * 100

trades['drawdown'] = drawdown

# Create visualization
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# 1. Equity Curve
ax = axes[0]
ax.plot(trades['timestamp'], trades['cumulative_pnl'], linewidth=2, color='#2ecc71')
ax.axhline(0, color='gray', linestyle='--', linewidth=0.5)
ax.fill_between(trades['timestamp'], 0, trades['cumulative_pnl'], alpha=0.3, color='#2ecc71')
ax.set_title('PI Extreme Mean Reversion - Equity Curve', fontsize=14, fontweight='bold')
ax.set_ylabel('Cumulative Return (%)', fontsize=12)
ax.grid(True, alpha=0.3)

# Add stats box
stats_text = f"Total Return: {trades['pnl_pct'].sum():.2f}%\n"
stats_text += f"Max DD: {drawdown.min():.2f}%\n"
stats_text += f"Return/DD: {trades['pnl_pct'].sum() / abs(drawdown.min()):.2f}x\n"
stats_text += f"Trades: {len(trades)}"
ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
        verticalalignment='top', fontsize=10,
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

# 2. Drawdown
ax = axes[1]
ax.fill_between(trades['timestamp'], 0, drawdown, alpha=0.5, color='#e74c3c')
ax.plot(trades['timestamp'], drawdown, linewidth=2, color='#c0392b')
ax.set_title('Drawdown Analysis', fontsize=14, fontweight='bold')
ax.set_ylabel('Drawdown (%)', fontsize=12)
ax.grid(True, alpha=0.3)

# Add max DD line
ax.axhline(drawdown.min(), color='red', linestyle='--', linewidth=1, label=f'Max DD: {drawdown.min():.2f}%')
ax.legend()

# 3. Individual Trades
ax = axes[2]
colors = ['#2ecc71' if pnl > 0 else '#e74c3c' for pnl in trades['pnl_pct']]
bars = ax.bar(range(len(trades)), trades['pnl_pct'], color=colors, alpha=0.7)

# Highlight TP vs SL
for i, (pnl, reason) in enumerate(zip(trades['pnl_pct'], trades['exit_reason'])):
    if reason == 'TP':
        bars[i].set_edgecolor('#27ae60')
        bars[i].set_linewidth(2)
    elif reason == 'SL':
        bars[i].set_edgecolor('#c0392b')
        bars[i].set_linewidth(2)

ax.axhline(0, color='gray', linestyle='-', linewidth=0.5)
ax.set_title('Individual Trade PnL', fontsize=14, fontweight='bold')
ax.set_xlabel('Trade Number', fontsize=12)
ax.set_ylabel('PnL (%)', fontsize=12)
ax.grid(True, alpha=0.3, axis='y')

# Add legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#2ecc71', edgecolor='#27ae60', linewidth=2, label='TP (Take Profit)'),
    Patch(facecolor='#e74c3c', edgecolor='#c0392b', linewidth=2, label='SL (Stop Loss)')
]
ax.legend(handles=legend_elements, loc='upper right')

plt.tight_layout()
plt.savefig('results/pi_ultra_selective_equity.png', dpi=150, bbox_inches='tight')
print(f"\n✅ Saved chart to results/pi_ultra_selective_equity.png")

# ==================== TRADE DISTRIBUTION ====================

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Direction Distribution
ax = axes[0, 0]
direction_counts = trades['direction'].value_counts()
direction_pnl = trades.groupby('direction')['pnl_pct'].sum()

bars = ax.bar(direction_counts.index, direction_counts.values, alpha=0.7, color=['#3498db', '#e67e22'])
ax.set_title('Trade Direction Distribution', fontsize=14, fontweight='bold')
ax.set_ylabel('Count', fontsize=12)
ax.grid(True, alpha=0.3, axis='y')

# Add PnL labels
for i, (direction, count) in enumerate(direction_counts.items()):
    pnl = direction_pnl[direction]
    ax.text(i, count + 0.3, f"{count} trades\n{pnl:+.2f}%",
            ha='center', va='bottom', fontsize=10)

# 2. RSI Distribution
ax = axes[0, 1]
colors = ['#2ecc71' if pnl > 0 else '#e74c3c' for pnl in trades['pnl_pct']]
ax.scatter(trades['rsi'], trades['pnl_pct'], c=colors, alpha=0.7, s=100)
ax.axhline(0, color='gray', linestyle='--', linewidth=0.5)
ax.axvline(15, color='blue', linestyle='--', linewidth=1, alpha=0.5, label='RSI 15')
ax.axvline(85, color='red', linestyle='--', linewidth=1, alpha=0.5, label='RSI 85')
ax.set_title('PnL vs RSI', fontsize=14, fontweight='bold')
ax.set_xlabel('RSI', fontsize=12)
ax.set_ylabel('PnL (%)', fontsize=12)
ax.grid(True, alpha=0.3)
ax.legend()

# 3. Volume Ratio Distribution
ax = axes[1, 0]
colors = ['#2ecc71' if pnl > 0 else '#e74c3c' for pnl in trades['pnl_pct']]
ax.scatter(trades['volume_ratio'], trades['pnl_pct'], c=colors, alpha=0.7, s=100)
ax.axhline(0, color='gray', linestyle='--', linewidth=0.5)
ax.axvline(5.0, color='purple', linestyle='--', linewidth=1, alpha=0.5, label='Vol 5x')
ax.set_title('PnL vs Volume Ratio', fontsize=14, fontweight='bold')
ax.set_xlabel('Volume Ratio (vs 30-bar MA)', fontsize=12)
ax.set_ylabel('PnL (%)', fontsize=12)
ax.grid(True, alpha=0.3)
ax.legend()

# 4. EMA Distance Distribution
ax = axes[1, 1]
colors = ['#2ecc71' if pnl > 0 else '#e74c3c' for pnl in trades['pnl_pct']]
ax.scatter(trades['ema_dist'].abs(), trades['pnl_pct'], c=colors, alpha=0.7, s=100)
ax.axhline(0, color='gray', linestyle='--', linewidth=0.5)
ax.axvline(1.0, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='1% from EMA')
ax.set_title('PnL vs EMA Distance', fontsize=14, fontweight='bold')
ax.set_xlabel('Distance from EMA(20) (%)', fontsize=12)
ax.set_ylabel('PnL (%)', fontsize=12)
ax.grid(True, alpha=0.3)
ax.legend()

plt.tight_layout()
plt.savefig('results/pi_ultra_selective_analysis.png', dpi=150, bbox_inches='tight')
print(f"✅ Saved analysis charts to results/pi_ultra_selective_analysis.png")

print("\n" + "="*70)
print("VISUALIZATION COMPLETE")
print("="*70 + "\n")
