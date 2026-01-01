"""
Plot portfolio equity curve from simulation
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Load equity curve
df = pd.read_csv('portfolio_equity_curve_10pct.csv')
df['timestamp'] = pd.to_datetime(df['time'])

# Create figure
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Plot 1: Equity curve
ax1.plot(df['timestamp'], df['equity'], linewidth=2, color='#2ecc71')
ax1.axhline(y=1000, color='gray', linestyle='--', alpha=0.5, label='Starting Equity')
ax1.fill_between(df['timestamp'], 1000, df['equity'], where=(df['equity'] >= 1000),
                  alpha=0.2, color='green', label='Profit')
ax1.fill_between(df['timestamp'], 1000, df['equity'], where=(df['equity'] < 1000),
                  alpha=0.2, color='red', label='Loss')
ax1.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax1.set_title('Portfolio Equity Curve - 9 Coins RSI Strategy (Optimized Parameters)',
              fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left')

# Add stats text
stats_text = f"Final: ${df['equity'].iloc[-1]:.2f}\n"
stats_text += f"Return: +{((df['equity'].iloc[-1] / 1000 - 1) * 100):.2f}%\n"
stats_text += f"Max DD: {df['drawdown_pct'].min():.2f}%\n"
stats_text += f"R/R: {abs((df['equity'].iloc[-1] / 1000 - 1) * 100 / df['drawdown_pct'].min()):.2f}x"
ax1.text(0.98, 0.02, stats_text, transform=ax1.transAxes,
         fontsize=10, verticalalignment='bottom', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# Plot 2: Drawdown
ax2.fill_between(df['timestamp'], 0, df['drawdown_pct'],
                  color='red', alpha=0.3, label='Drawdown')
ax2.plot(df['timestamp'], df['drawdown_pct'], color='darkred', linewidth=1.5)
ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(loc='lower left')

# Format x-axis
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.xticks(rotation=45)

plt.tight_layout()
plt.savefig('portfolio_equity_curve_optimized.png', dpi=150, bbox_inches='tight')
print('✅ Saved: portfolio_equity_curve_optimized.png')
plt.close()

# Load trades for additional analysis
trades_df = pd.read_csv('portfolio_trades_10pct.csv')
trades_df['timestamp'] = pd.to_datetime(trades_df['time'])

# Plot per-coin performance
fig, ax = plt.subplots(figsize=(12, 6))
coin_profits = trades_df.groupby('coin')['dollar_pnl'].sum().sort_values(ascending=True)
colors = ['red' if x < 0 else 'green' for x in coin_profits.values]
coin_profits.plot(kind='barh', ax=ax, color=colors, edgecolor='black', linewidth=1.5)
ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
ax.set_xlabel('Total Profit ($)', fontsize=12, fontweight='bold')
ax.set_title('Profit by Coin - 90 Days', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3, axis='x')

# Add value labels
for i, v in enumerate(coin_profits.values):
    ax.text(v, i, f' ${v:.2f}', va='center', fontweight='bold')

plt.tight_layout()
plt.savefig('portfolio_profit_by_coin.png', dpi=150, bbox_inches='tight')
print('✅ Saved: portfolio_profit_by_coin.png')
plt.close()

print()
print('='*80)
print('📊 SUMMARY STATISTICS')
print('='*80)
print(f'Total Trades: {len(trades_df)}')
print(f'Date Range: {trades_df["timestamp"].min().date()} to {trades_df["timestamp"].max().date()}')
print(f'Days: {(trades_df["timestamp"].max() - trades_df["timestamp"].min()).days}')
print(f'Avg Trades/Day: {len(trades_df) / (trades_df["timestamp"].max() - trades_df["timestamp"].min()).days:.2f}')
print()
print(f'Starting Equity: $1,000.00')
print(f'Final Equity: ${df["equity"].iloc[-1]:.2f}')
print(f'Total Return: +{((df["equity"].iloc[-1] / 1000 - 1) * 100):.2f}%')
print(f'Max Drawdown: {df["drawdown_pct"].min():.2f}%')
print(f'Return/DD Ratio: {abs((df["equity"].iloc[-1] / 1000 - 1) * 100 / df["drawdown_pct"].min()):.2f}x')
print()
print(f'Win Rate: {(trades_df["dollar_pnl"] > 0).sum() / len(trades_df) * 100:.1f}%')
print(f'Winners: {(trades_df["dollar_pnl"] > 0).sum()}')
print(f'Losers: {(trades_df["dollar_pnl"] < 0).sum()}')
print(f'Avg Winner: ${trades_df[trades_df["dollar_pnl"] > 0]["dollar_pnl"].mean():.2f}')
print(f'Avg Loser: ${trades_df[trades_df["dollar_pnl"] < 0]["dollar_pnl"].mean():.2f}')
print()
