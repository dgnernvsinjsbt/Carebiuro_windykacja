#!/usr/bin/env python3
"""
Plot equity curve for 10x leverage portfolio over full 3-month period
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Load trade log
df = pd.read_csv('portfolio_10x_leverage_log.csv')
df['date'] = pd.to_datetime(df['date'])

# Calculate peak and drawdown
df['peak'] = df['capital_after'].cummax()
df['drawdown_pct'] = ((df['capital_after'] - df['peak']) / df['peak']) * 100

# Find key points
start_capital = 100.0
final_capital = df['capital_after'].iloc[-1]
peak_capital = df['peak'].max()
peak_idx = df['capital_after'].idxmax()
peak_date = df.loc[peak_idx, 'date']

worst_dd_idx = df['drawdown_pct'].idxmin()
worst_dd = df.loc[worst_dd_idx, 'drawdown_pct']
worst_dd_capital = df.loc[worst_dd_idx, 'capital_after']
worst_dd_date = df.loc[worst_dd_idx, 'date']

# Create figure with 2 subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[2, 1])
fig.suptitle('10x Leverage Portfolio - Full 3-Month Equity Curve (Sep 15 - Dec 15, 2025)',
             fontsize=16, fontweight='bold')

# Top subplot: Equity curve
ax1.plot(df['date'], df['capital_after'], linewidth=2, color='#2E86DE', label='Portfolio Equity')
ax1.axhline(y=start_capital, color='gray', linestyle='--', alpha=0.5, label='Starting Capital ($100)')
ax1.fill_between(df['date'], start_capital, df['capital_after'],
                  where=(df['capital_after'] >= start_capital),
                  color='green', alpha=0.1, label='Profit Zone')
ax1.fill_between(df['date'], start_capital, df['capital_after'],
                  where=(df['capital_after'] < start_capital),
                  color='red', alpha=0.1, label='Loss Zone')

# Mark key points
ax1.scatter([peak_date], [peak_capital], color='gold', s=200, zorder=5, marker='*',
            edgecolors='black', linewidths=2, label=f'Peak: ${peak_capital:.0f}')
ax1.scatter([worst_dd_date], [worst_dd_capital], color='red', s=200, zorder=5, marker='v',
            edgecolors='black', linewidths=2, label=f'Max DD: ${worst_dd_capital:.0f} ({worst_dd:.1f}%)')
ax1.scatter([df['date'].iloc[-1]], [final_capital], color='blue', s=200, zorder=5, marker='o',
            edgecolors='black', linewidths=2, label=f'Final: ${final_capital:.0f}')

# Add annotations
ax1.annotate(f'Peak\n${peak_capital:.0f}',
             xy=(peak_date, peak_capital),
             xytext=(10, 30), textcoords='offset points',
             fontsize=10, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='gold', alpha=0.7),
             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='black', lw=2))

ax1.annotate(f'Max DD\n${worst_dd_capital:.0f}\n({worst_dd:.1f}%)',
             xy=(worst_dd_date, worst_dd_capital),
             xytext=(10, -50), textcoords='offset points',
             fontsize=10, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='red', alpha=0.7),
             arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='black', lw=2))

ax1.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
ax1.set_title(f'Equity Growth: ${start_capital:.0f} → ${final_capital:.0f} (+{((final_capital-start_capital)/start_capital*100):.1f}%)',
              fontsize=13, fontweight='bold', pad=10)
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.set_xlim(df['date'].min(), df['date'].max())

# Format x-axis
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Bottom subplot: Drawdown from peak
ax2.fill_between(df['date'], 0, df['drawdown_pct'],
                  color='red', alpha=0.3, label='Drawdown from Peak')
ax2.plot(df['date'], df['drawdown_pct'], linewidth=2, color='darkred')
ax2.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
ax2.axhline(y=worst_dd, color='red', linestyle='--', alpha=0.5)

# Mark worst DD point
ax2.scatter([worst_dd_date], [worst_dd], color='red', s=150, zorder=5, marker='v',
            edgecolors='black', linewidths=2)

ax2.set_ylabel('Drawdown %', fontsize=12, fontweight='bold')
ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
ax2.set_title(f'Drawdown from Peak (Max: {worst_dd:.2f}%)', fontsize=13, fontweight='bold', pad=10)
ax2.legend(loc='lower left', fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.set_xlim(df['date'].min(), df['date'].max())

# Format x-axis
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

# Add performance stats box
stats_text = f"""PERFORMANCE STATS:
Starting: ${start_capital:.0f}
Peak: ${peak_capital:.0f} ({((peak_capital-start_capital)/start_capital*100):.1f}%)
Final: ${final_capital:.0f} (+{((final_capital-start_capital)/start_capital*100):.1f}%)
Max DD: {worst_dd:.2f}%
Return/DD: {abs((final_capital-start_capital)/start_capital*100 / worst_dd):.1f}x
Win Rate: {(df['pnl_usd'] > 0).sum() / len(df) * 100:.1f}%
Trades: {len(df)}"""

props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=10,
         verticalalignment='top', bbox=props, family='monospace')

plt.tight_layout()
plt.savefig('equity_curve_10x_leverage.png', dpi=300, bbox_inches='tight')
print("✅ Equity curve saved to: equity_curve_10x_leverage.png")

# Also create a zoomed view of the Dec 8-15 crash
fig2, ax = plt.subplots(figsize=(14, 8))

# Filter to Nov 20 - Dec 15 for detail
detail_start = pd.Timestamp('2025-11-20')
detail_end = pd.Timestamp('2025-12-15')
df_detail = df[(df['date'] >= detail_start) & (df['date'] <= detail_end)]

ax.plot(df_detail['date'], df_detail['capital_after'], linewidth=2, color='#2E86DE', marker='o', markersize=4)
ax.axhline(y=peak_capital, color='gold', linestyle='--', linewidth=2, alpha=0.7, label=f'Peak: ${peak_capital:.0f}')

# Shade the Dec 8-15 crash period
crash_start = pd.Timestamp('2025-12-08')
crash_end = pd.Timestamp('2025-12-15')
ax.axvspan(crash_start, crash_end, alpha=0.2, color='red', label='Dec 8-15 Crash Period')

# Mark key points in detail
detail_peak_idx = df_detail['capital_after'].idxmax()
detail_peak = df_detail.loc[detail_peak_idx]
ax.scatter([detail_peak['date']], [detail_peak['capital_after']],
           color='gold', s=200, zorder=5, marker='*', edgecolors='black', linewidths=2)

# Mark worst point
detail_worst_idx = df_detail['capital_after'].idxmin()
detail_worst = df_detail.loc[detail_worst_idx]
ax.scatter([detail_worst['date']], [detail_worst['capital_after']],
           color='red', s=200, zorder=5, marker='v', edgecolors='black', linewidths=2)

ax.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
ax.set_xlabel('Date', fontsize=12, fontweight='bold')
ax.set_title('Detailed View: The Dec 8-15 Drawdown (Nov 20 - Dec 15)', fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=10)
ax.grid(True, alpha=0.3)

# Format x-axis
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

plt.tight_layout()
plt.savefig('equity_curve_10x_detail.png', dpi=300, bbox_inches='tight')
print("✅ Detailed view saved to: equity_curve_10x_detail.png")

plt.close('all')

# Print summary
print("\n" + "=" * 80)
print("EQUITY CURVE SUMMARY")
print("=" * 80)
print(f"\nStarting Capital: ${start_capital:.2f}")
print(f"Peak Capital:     ${peak_capital:.2f} on {peak_date.strftime('%Y-%m-%d')}")
print(f"Final Capital:    ${final_capital:.2f}")
print(f"\nMax Drawdown:     {worst_dd:.2f}% on {worst_dd_date.strftime('%Y-%m-%d')}")
print(f"Drawdown Amount:  ${peak_capital - worst_dd_capital:.2f}")
print(f"\nTotal Return:     +{((final_capital-start_capital)/start_capital*100):.2f}%")
print(f"Peak Return:      +{((peak_capital-start_capital)/start_capital*100):.2f}%")
print(f"Return from Peak: {((final_capital-peak_capital)/peak_capital*100):.2f}%")
