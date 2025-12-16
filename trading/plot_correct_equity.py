"""
Generate correct equity curve from simple portfolio
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# Load simple portfolio results
df = pd.read_csv('portfolio_SIMPLE.csv')
df['exit_time'] = pd.to_datetime(df['exit_time'])

print('Generating equity curve...')

# Create figure with 3 subplots
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True)

# Add starting point
start_time = df['exit_time'].min()
equity_with_start = pd.concat([
    pd.DataFrame({'exit_time': [start_time], 'equity': [1000.0], 'drawdown_pct': [0.0]}),
    df[['exit_time', 'equity', 'drawdown_pct']]
], ignore_index=True)

# Plot 1: Equity Curve
ax1.plot(equity_with_start['exit_time'], equity_with_start['equity'],
         linewidth=2, color='#2ecc71', label='Equity', zorder=2)
ax1.axhline(y=1000, color='gray', linestyle='--', alpha=0.5, label='Starting Equity')

# Fill areas
ax1.fill_between(equity_with_start['exit_time'], 1000, equity_with_start['equity'],
                  where=(equity_with_start['equity'] >= 1000),
                  alpha=0.2, color='green', label='Profit')
ax1.fill_between(equity_with_start['exit_time'], 1000, equity_with_start['equity'],
                  where=(equity_with_start['equity'] < 1000),
                  alpha=0.2, color='red', label='Loss')

# Mark max drawdown
max_dd_idx = df['drawdown_pct'].idxmin()
max_dd_point = df.loc[max_dd_idx]
ax1.scatter([max_dd_point['exit_time']], [max_dd_point['equity']],
           color='red', s=200, marker='v', zorder=3,
           label=f'Max DD: {max_dd_point["drawdown_pct"]:.2f}%')

# Mark losing trades
losers = df[df['pnl_pct'] < 0]
ax1.scatter(losers['exit_time'], losers['equity'],
           color='red', s=30, alpha=0.4, zorder=1)

ax1.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax1.set_title('Portfolio Equity Curve - 9 Coins RSI Strategy (CORRECTED)',
              fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left')

# Add stats box
final_equity = df['equity'].iloc[-1]
total_return = ((final_equity - 1000) / 1000) * 100
max_dd = df['drawdown_pct'].min()

stats_text = f"Final: ${final_equity:,.2f}\n"
stats_text += f"Return: +{total_return:.2f}%\n"
stats_text += f"Max DD: {max_dd:.2f}%\n"
stats_text += f"R/R: {abs(total_return/max_dd):.2f}x\n"
stats_text += f"Trades: {len(df)}\n"
stats_text += f"Win%: {len(df[df['pnl_pct']>0])/len(df)*100:.1f}%"

ax1.text(0.98, 0.02, stats_text, transform=ax1.transAxes,
         fontsize=10, verticalalignment='bottom', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))

# Plot 2: Drawdown
ax2.fill_between(equity_with_start['exit_time'], 0, equity_with_start['drawdown_pct'],
                  color='red', alpha=0.3, label='Drawdown')
ax2.plot(equity_with_start['exit_time'], equity_with_start['drawdown_pct'],
         color='darkred', linewidth=1.5)

# Mark max DD on drawdown chart
ax2.scatter([max_dd_point['exit_time']], [max_dd_point['drawdown_pct']],
           color='darkred', s=150, marker='v', zorder=3)
ax2.text(max_dd_point['exit_time'], max_dd_point['drawdown_pct'] - 0.2,
         f"{max_dd_point['drawdown_pct']:.2f}%\n{max_dd_point['exit_time'].strftime('%b %d')}",
         ha='center', fontsize=9, fontweight='bold')

ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(loc='lower left')

# Plot 3: Trade Distribution
bins = pd.date_range(df['exit_time'].min(), df['exit_time'].max(), freq='3D')
trade_counts, _ = np.histogram(df['exit_time'], bins=bins)

# Also show winners vs losers
winners = df[df['pnl_pct'] > 0]
losers = df[df['pnl_pct'] < 0]
winner_counts, _ = np.histogram(winners['exit_time'], bins=bins)
loser_counts, _ = np.histogram(losers['exit_time'], bins=bins)

ax3.bar(bins[:-1], winner_counts, width=2.5, color='green', alpha=0.7,
        label='Winners', edgecolor='darkgreen')
ax3.bar(bins[:-1], -loser_counts, width=2.5, color='red', alpha=0.7,
        label='Losers', edgecolor='darkred')
ax3.axhline(y=0, color='black', linewidth=0.8)
ax3.set_ylabel('Trades per 3 Days', fontsize=12, fontweight='bold')
ax3.set_xlabel('Date', fontsize=12, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')
ax3.legend()

# Format x-axis
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax3.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.xticks(rotation=45)

plt.tight_layout()
plt.savefig('equity_curve_CORRECT.png', dpi=150, bbox_inches='tight')
print('✅ Saved: equity_curve_CORRECT.png')
plt.close()

# Also create a zoomed view of the October spike
fig, ax = plt.subplots(figsize=(14, 8))

# Filter to September - October
oct_data = df[(df['exit_time'] >= '2025-09-01') & (df['exit_time'] <= '2025-10-31')]

ax.plot(oct_data['exit_time'], oct_data['equity'], linewidth=2.5,
        color='steelblue', marker='o', markersize=4, label='Equity')
ax.axhline(y=1000, color='gray', linestyle='--', alpha=0.5)

# Mark the big October spike
oct_spike = oct_data[(oct_data['exit_time'] >= '2025-10-11') &
                      (oct_data['exit_time'] <= '2025-10-13')]
if len(oct_spike) > 0:
    ax.scatter(oct_spike['exit_time'], oct_spike['equity'],
              color='gold', s=150, marker='*', zorder=3,
              edgecolor='darkred', linewidth=1.5,
              label='Oct 11-12 Spike')

# Annotate major events
for idx, row in oct_spike.iterrows():
    if row['pnl_pct'] > 5:  # Big winners only
        ax.annotate(f"{row['coin'].split('-')[0]}\n+{row['pnl_pct']:.1f}%",
                   xy=(row['exit_time'], row['equity']),
                   xytext=(10, 10), textcoords='offset points',
                   fontsize=8, ha='left',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                   arrowprops=dict(arrowstyle='->', color='black', lw=1))

ax.set_xlabel('Date', fontsize=12, fontweight='bold')
ax.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax.set_title('September-October Detail: The Mean Reversion Jackpot',
             fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend()
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
plt.xticks(rotation=45)

plt.tight_layout()
plt.savefig('equity_october_spike.png', dpi=150, bbox_inches='tight')
print('✅ Saved: equity_october_spike.png')
plt.close()

print()
print('='*80)
print('📊 EQUITY CURVE SUMMARY')
print('='*80)
print()
print(f'Starting Equity: $1,000.00')
print(f'Final Equity: ${final_equity:,.2f}')
print(f'Total Return: +{total_return:.2f}%')
print(f'Max Drawdown: {max_dd:.2f}%')
print(f'Return/DD Ratio: {abs(total_return/max_dd):.2f}x')
print()
print(f'Max DD occurred on: {max_dd_point["exit_time"].strftime("%Y-%m-%d %H:%M")}')
print(f'  Coin: {max_dd_point["coin"]}')
print(f'  Exit: {max_dd_point["exit_reason"]} ({max_dd_point["pnl_pct"]:.2f}%)')
print()
print('Files generated:')
print('  - equity_curve_CORRECT.png (full 3-panel view)')
print('  - equity_october_spike.png (Sep-Oct detail)')
