#!/usr/bin/env python3
"""
Visual analysis of MOODENG ATR Limit validation results
Create equity curve with outlier annotations
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Load trade data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/moodeng_validation_trades.csv')
df['entry_timestamp'] = pd.to_datetime(df['entry_timestamp'])

print("Creating equity curve visualization...")

# Create figure
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[2, 1])

# ============================================================================
# EQUITY CURVE (Top panel)
# ============================================================================

# Plot equity
ax1.plot(df['entry_timestamp'], df['equity'], linewidth=2, color='#2E86AB', label='Equity')
ax1.plot(df['entry_timestamp'], df['running_max'], linewidth=1, color='#A23B72',
         linestyle='--', alpha=0.6, label='Peak Equity')

# Fill drawdown area
ax1.fill_between(df['entry_timestamp'], df['equity'], df['running_max'],
                  where=(df['equity'] < df['running_max']),
                  color='red', alpha=0.2, label='Drawdown')

# Mark outlier trades (>3 SD)
mean_pnl = df['pnl_pct'].mean()
std_pnl = df['pnl_pct'].std()
outliers = df[abs(df['pnl_pct'] - mean_pnl) > 3 * std_pnl]

for idx, row in outliers.iterrows():
    ax1.scatter(row['entry_timestamp'], row['equity'],
               s=200, color='gold', edgecolors='black', linewidths=2,
               zorder=5, marker='*')
    ax1.annotate(f"#{row['trade_num']}: {row['pnl_pct']:+.1f}%",
                xy=(row['entry_timestamp'], row['equity']),
                xytext=(10, 10), textcoords='offset points',
                fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5))

# Mark max drawdown point
max_dd_idx = df['drawdown_pct'].idxmin()
max_dd_row = df.loc[max_dd_idx]
ax1.scatter(max_dd_row['entry_timestamp'], max_dd_row['equity'],
           s=200, color='red', edgecolors='black', linewidths=2,
           zorder=5, marker='v')
ax1.annotate(f"Max DD: {max_dd_row['drawdown_pct']:.2f}%\nTrade #{max_dd_row['trade_num']}",
            xy=(max_dd_row['entry_timestamp'], max_dd_row['equity']),
            xytext=(-60, -30), textcoords='offset points',
            fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightcoral', alpha=0.8),
            arrowprops=dict(arrowstyle='->', color='red', lw=1.5))

ax1.set_title('MOODENG ATR Limit - Equity Curve with Outliers', fontsize=16, fontweight='bold', pad=20)
ax1.set_ylabel('Equity (%)', fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3, linestyle='--')
ax1.legend(loc='upper left', fontsize=10)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax1.xaxis.set_major_locator(mdates.DayLocator(interval=3))

# Add summary text
summary_text = f"""
Return: +{df['cumulative_pnl'].iloc[-1]:.2f}%
Max DD: {df['drawdown_pct'].min():.2f}%
R/DD: {df['cumulative_pnl'].iloc[-1] / abs(df['drawdown_pct'].min()):.2f}x
Trades: {len(df)}
Win Rate: {(df['pnl_pct'] > 0).sum() / len(df) * 100:.1f}%
"""
ax1.text(0.02, 0.98, summary_text, transform=ax1.transAxes,
        fontsize=11, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# ============================================================================
# TRADE P/L BARS (Bottom panel)
# ============================================================================

colors = ['green' if x > 0 else 'red' for x in df['pnl_pct']]
ax2.bar(df['entry_timestamp'], df['pnl_pct'], color=colors, alpha=0.7, width=0.5)

# Mark outliers
for idx, row in outliers.iterrows():
    ax2.bar(row['entry_timestamp'], row['pnl_pct'],
           color='gold', edgecolor='black', linewidth=2, width=0.5)

ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax2.set_title('Individual Trade P/L (Outliers in Gold)', fontsize=14, fontweight='bold', pad=10)
ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
ax2.set_ylabel('Trade P/L (%)', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax2.xaxis.set_major_locator(mdates.DayLocator(interval=3))

plt.tight_layout()
plt.savefig('/workspaces/Carebiuro_windykacja/trading/results/moodeng_validation_equity_curve.png',
            dpi=150, bbox_inches='tight')
print("✅ Saved: trading/results/moodeng_validation_equity_curve.png")

# ============================================================================
# CONCENTRATION ANALYSIS CHART
# ============================================================================

fig2, (ax3, ax4) = plt.subplots(1, 2, figsize=(16, 6))

# Top 5 vs Rest breakdown
df_sorted = df.sort_values('pnl_pct', ascending=False)
top5_pnl = df_sorted.head(5)['pnl_pct'].sum()
rest_pnl = df_sorted.iloc[5:]['pnl_pct'].sum()

labels = ['Top 5 Trades', 'Remaining 121 Trades']
sizes = [top5_pnl, rest_pnl]
colors_pie = ['gold', 'lightblue']
explode = (0.1, 0)

ax3.pie(sizes, explode=explode, labels=labels, colors=colors_pie, autopct='%1.1f%%',
        shadow=True, startangle=90, textprops={'fontsize': 12, 'fontweight': 'bold'})
ax3.set_title('Profit Contribution\n(EXTREME Outlier Dependency)',
             fontsize=14, fontweight='bold', pad=20)

# Add text annotations
ax3.text(0, -1.5, f'Top 5: {top5_pnl:+.2f}% (85.3% of total)',
        ha='center', fontsize=11, style='italic')
ax3.text(0, -1.7, f'Rest: {rest_pnl:+.2f}% (14.7% of total)',
        ha='center', fontsize=11, style='italic')

# P/L distribution histogram
ax4.hist(df['pnl_pct'], bins=30, color='steelblue', edgecolor='black', alpha=0.7)
ax4.axvline(x=df['pnl_pct'].mean(), color='red', linestyle='--', linewidth=2,
           label=f'Mean: {df["pnl_pct"].mean():.2f}%')
ax4.axvline(x=df['pnl_pct'].median(), color='orange', linestyle='--', linewidth=2,
           label=f'Median: {df["pnl_pct"].median():.2f}%')
ax4.set_title('Trade P/L Distribution\n(Right-Skewed)', fontsize=14, fontweight='bold', pad=20)
ax4.set_xlabel('Trade P/L (%)', fontsize=12, fontweight='bold')
ax4.set_ylabel('Frequency', fontsize=12, fontweight='bold')
ax4.legend(fontsize=10)
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('/workspaces/Carebiuro_windykacja/trading/results/moodeng_validation_distribution.png',
            dpi=150, bbox_inches='tight')
print("✅ Saved: trading/results/moodeng_validation_distribution.png")

# ============================================================================
# SUMMARY STATISTICS TABLE
# ============================================================================

print("\n" + "=" * 80)
print("VISUAL SUMMARY CREATED")
print("=" * 80)
print("\nFiles generated:")
print("  1. moodeng_validation_equity_curve.png")
print("  2. moodeng_validation_distribution.png")
print("\nKey visual findings:")
print(f"  - 4 outlier trades (gold stars) in 7-minute window")
print(f"  - Max drawdown (red marker) at trade #{max_dd_row['trade_num']}")
print(f"  - Top 5 trades = 85.3% of profits (pie chart)")
print(f"  - Right-skewed P/L distribution (histogram)")
print("\n✅ Validation complete - see MOODENG_STATISTICAL_VALIDATION_REPORT.md for details")
