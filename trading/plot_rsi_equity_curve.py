#!/usr/bin/env python3
"""
Create equity curve visualization for Daily RSI > 50 filtered strategy
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Load trades
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_rsi_filtered_trades.csv')
df['entry_time'] = pd.to_datetime(df['entry_time'])
df['exit_time'] = pd.to_datetime(df['exit_time'])

# Create figure with subplots
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1, 1]})
fig.suptitle('FARTCOIN LONG-only + Daily RSI > 50 Filter\n60-Day Performance',
             fontsize=16, fontweight='bold')

# === SUBPLOT 1: Equity Curve ===
ax1.plot(df['entry_time'], df['equity'], linewidth=2, color='#2E7D32', label='Equity')
ax1.fill_between(df['entry_time'], 100, df['equity'], alpha=0.3, color='#4CAF50')
ax1.axhline(y=100, color='gray', linestyle='--', alpha=0.5, label='Starting Capital')

# Mark wins and losses
wins = df[df['pnl_pct'] > 0]
losses = df[df['pnl_pct'] <= 0]

ax1.scatter(wins['entry_time'], wins['equity'], color='green', s=50, alpha=0.7, marker='^', label='Winner', zorder=5)
ax1.scatter(losses['entry_time'], losses['equity'], color='red', s=50, alpha=0.7, marker='v', label='Loser', zorder=5)

# Mark TP hits
tps = df[df['exit_reason'] == 'TP']
ax1.scatter(tps['entry_time'], tps['equity'], color='gold', s=100, alpha=0.9, marker='*', label='TP Hit', zorder=6)

ax1.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left', fontsize=10)
ax1.set_ylim(95, df['equity'].max() * 1.05)

# Add stats box
stats_text = f"""Trades: {len(df)}
Win Rate: {(df['pnl_pct'] > 0).mean() * 100:.1f}%
TP Rate: {(df['exit_reason'] == 'TP').sum() / len(df) * 100:.1f}%
Return: {df['pnl_pct'].sum():+.2f}%
Max DD: {df['drawdown'].min():.2f}%
R/DD: {df['pnl_pct'].sum() / abs(df['drawdown'].min()):.2f}x"""

ax1.text(0.98, 0.05, stats_text, transform=ax1.transAxes,
         fontsize=10, verticalalignment='bottom', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# === SUBPLOT 2: Drawdown ===
ax2.fill_between(df['entry_time'], 0, df['drawdown'], color='red', alpha=0.3)
ax2.plot(df['entry_time'], df['drawdown'], color='darkred', linewidth=1.5)
ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.set_ylim(df['drawdown'].min() * 1.2, 1)

# Highlight max DD
max_dd_idx = df['drawdown'].idxmin()
ax2.scatter(df['entry_time'].iloc[max_dd_idx], df['drawdown'].iloc[max_dd_idx],
           color='darkred', s=100, marker='o', zorder=5)
ax2.annotate(f'Max DD: {df["drawdown"].iloc[max_dd_idx]:.2f}%',
            xy=(df['entry_time'].iloc[max_dd_idx], df['drawdown'].iloc[max_dd_idx]),
            xytext=(20, -20), textcoords='offset points',
            bbox=dict(boxstyle='round', facecolor='red', alpha=0.7),
            arrowprops=dict(arrowstyle='->', color='darkred'))

# === SUBPLOT 3: Trade P&L ===
colors = ['green' if x > 0 else 'red' for x in df['pnl_pct']]
bars = ax3.bar(df['entry_time'], df['pnl_pct'], color=colors, alpha=0.7, width=0.5)

# Highlight TP hits
for i, row in tps.iterrows():
    ax3.bar(row['entry_time'], row['pnl_pct'], color='gold', alpha=0.9, width=0.5)

ax3.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
ax3.set_ylabel('Trade P&L (%)', fontsize=12, fontweight='bold')
ax3.set_xlabel('Date', fontsize=12, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')

# Format x-axis
for ax in [ax1, ax2, ax3]:
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

plt.tight_layout()

# Save
output_path = '/workspaces/Carebiuro_windykacja/trading/results/fartcoin_rsi_equity_curve.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"✅ Equity curve saved to: {output_path}")

# Also save a simple version
fig2, ax = plt.subplots(figsize=(12, 6))
ax.plot(df['entry_time'], df['equity'], linewidth=3, color='#2E7D32')
ax.fill_between(df['entry_time'], 100, df['equity'], alpha=0.3, color='#4CAF50')
ax.axhline(y=100, color='gray', linestyle='--', alpha=0.5)

# Mark key points
ax.scatter(wins['entry_time'], wins['equity'], color='green', s=60, alpha=0.7, marker='^', zorder=5)
ax.scatter(losses['entry_time'], losses['equity'], color='red', s=60, alpha=0.7, marker='v', zorder=5)
ax.scatter(tps['entry_time'], tps['equity'], color='gold', s=150, alpha=0.9, marker='*', zorder=6)

ax.set_title('FARTCOIN LONG-only + Daily RSI > 50 Filter\nEquity Curve (60 Days)',
            fontsize=14, fontweight='bold')
ax.set_xlabel('Date', fontsize=12, fontweight='bold')
ax.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Stats annotation
stats_text = f"""28 Trades | WR: 53.6% | TP: 28.6%
Return: +98.83% | DD: -3.77% | R/DD: 26.21x"""
ax.text(0.5, 0.95, stats_text, transform=ax.transAxes,
        fontsize=11, verticalalignment='top', horizontalalignment='center',
        bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))

plt.tight_layout()

output_path_simple = '/workspaces/Carebiuro_windykacja/trading/results/fartcoin_rsi_equity_curve_simple.png'
plt.savefig(output_path_simple, dpi=300, bbox_inches='tight')
print(f"✅ Simple equity curve saved to: {output_path_simple}")

print("\nDone!")
