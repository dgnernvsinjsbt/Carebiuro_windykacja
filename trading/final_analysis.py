"""
FINAL ANALYSIS - Trade frequency, timing, and equity curve
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Load fixed portfolio results
portfolio = pd.read_csv('portfolio_FIXED.csv')
portfolio['time'] = pd.to_datetime(portfolio['time'])
portfolio['entry_time'] = pd.to_datetime(portfolio['entry_time'])
portfolio['exit_time'] = pd.to_datetime(portfolio['exit_time'])

print('='*100)
print('📊 FINAL PORTFOLIO ANALYSIS')
print('='*100)
print()

# Overall stats
total_trades = len(portfolio)
start_date = portfolio['entry_time'].min()
end_date = portfolio['exit_time'].max()
total_days = (end_date - start_date).days
total_hours = (end_date - start_date).total_seconds() / 3600

print(f'Total Portfolio Trades: {total_trades}')
print(f'Date Range: {start_date.date()} to {end_date.date()}')
print(f'Duration: {total_days} days ({total_hours:.0f} hours)')
print()

# Time between trades
portfolio_sorted = portfolio.sort_values('exit_time').reset_index(drop=True)
portfolio_sorted['time_since_prev'] = portfolio_sorted['exit_time'].diff()
avg_hours = portfolio_sorted['time_since_prev'].dt.total_seconds().mean() / 3600
median_hours = portfolio_sorted['time_since_prev'].dt.total_seconds().median() / 3600

print(f'Avg Time Between Trades: {avg_hours:.1f} hours ({avg_hours/24:.1f} days)')
print(f'Median Time Between Trades: {median_hours:.1f} hours ({median_hours/24:.1f} days)')
print(f'Trades Per Day: {total_trades / total_days:.2f}')
print(f'Trades Per Week: {total_trades / (total_days/7):.1f}')
print()

# Per coin analysis
print('='*100)
print('📈 TRADES PER STRATEGY')
print('='*100)
print()
print(f'{"Coin":<15} {"Portfolio":<12} {"Backtest":<12} {"Executed %":<12} {"Avg Between":<15} {"Median Between"}')
print('-'*100)

# Load individual backtest counts
import sys
sys.path.insert(0, '/workspaces/Carebiuro_windykacja')
from portfolio_simulation_FIXED import backtest_coin_FIXED, COINS

coin_stats = []
for coin, config in COINS.items():
    # Individual backtest
    df = pd.read_csv(config['file'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    backtest_trades = backtest_coin_FIXED(
        df, coin,
        rsi_low=config['rsi_low'],
        rsi_high=config['rsi_high'],
        limit_offset_pct=config['offset'],
        stop_atr_mult=config['sl'],
        tp_atr_mult=config['tp']
    )

    backtest_count = len(backtest_trades)

    # Portfolio trades
    coin_portfolio = portfolio[portfolio['coin'] == coin].sort_values('exit_time')
    portfolio_count = len(coin_portfolio)

    executed_pct = (portfolio_count / backtest_count * 100) if backtest_count > 0 else 0

    # Time between trades
    if portfolio_count > 1:
        coin_portfolio['time_diff'] = coin_portfolio['exit_time'].diff()
        avg_time = coin_portfolio['time_diff'].dt.total_seconds().mean() / 3600
        median_time = coin_portfolio['time_diff'].dt.total_seconds().median() / 3600
    else:
        avg_time = None
        median_time = None

    coin_stats.append({
        'coin': coin,
        'backtest': backtest_count,
        'portfolio': portfolio_count,
        'executed_pct': executed_pct,
        'avg_hours': avg_time,
        'median_hours': median_time
    })

    if avg_time:
        print(f'{coin:<15} {portfolio_count:<12} {backtest_count:<12} {executed_pct:<11.1f}% {avg_time:<14.1f}h {median_time:.1f}h')
    else:
        print(f'{coin:<15} {portfolio_count:<12} {backtest_count:<12} {executed_pct:<11.1f}% {"N/A":<14} N/A')

print()
print(f'TOTALS: Portfolio {total_trades}, Backtest {sum(c["backtest"] for c in coin_stats)}, Executed {total_trades/sum(c["backtest"] for c in coin_stats)*100:.1f}%')
print()

# Create equity curve plot
print('='*100)
print('📈 GENERATING EQUITY CURVE')
print('='*100)
print()

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True)

# Prepare equity data
portfolio_sorted = portfolio.sort_values('exit_time').reset_index(drop=True)
equity_data = []

starting_equity = 1000.0
equity = starting_equity

equity_data.append({
    'time': portfolio_sorted['entry_time'].min(),
    'equity': starting_equity,
    'cumulative_return': 0
})

for idx, trade in portfolio_sorted.iterrows():
    equity_data.append({
        'time': trade['exit_time'],
        'equity': trade['equity'],
        'cumulative_return': ((trade['equity'] - starting_equity) / starting_equity) * 100
    })

equity_df = pd.DataFrame(equity_data)

# Calculate drawdown
equity_df['peak'] = equity_df['equity'].cummax()
equity_df['drawdown'] = equity_df['equity'] - equity_df['peak']
equity_df['drawdown_pct'] = (equity_df['drawdown'] / equity_df['peak']) * 100

# Plot 1: Equity curve
ax1.plot(equity_df['time'], equity_df['equity'], linewidth=2, color='#2ecc71', label='Equity')
ax1.axhline(y=starting_equity, color='gray', linestyle='--', alpha=0.5, label='Starting Equity')
ax1.fill_between(equity_df['time'], starting_equity, equity_df['equity'],
                  where=(equity_df['equity'] >= starting_equity),
                  alpha=0.2, color='green', label='Profit')
ax1.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax1.set_title('Portfolio Equity Curve - 9 Coins RSI Strategy (FIXED)',
              fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left')

# Stats text
final_equity = equity_df['equity'].iloc[-1]
total_return = ((final_equity - starting_equity) / starting_equity) * 100
max_dd = equity_df['drawdown_pct'].min()

stats_text = f"Final: ${final_equity:.2f}\n"
stats_text += f"Return: +{total_return:.2f}%\n"
stats_text += f"Max DD: {max_dd:.2f}%\n"
stats_text += f"R/R: {abs(total_return/max_dd):.2f}x\n"
stats_text += f"Trades: {total_trades}"

ax1.text(0.98, 0.02, stats_text, transform=ax1.transAxes,
         fontsize=10, verticalalignment='bottom', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

# Plot 2: Drawdown
ax2.fill_between(equity_df['time'], 0, equity_df['drawdown_pct'],
                  color='red', alpha=0.3, label='Drawdown')
ax2.plot(equity_df['time'], equity_df['drawdown_pct'], color='darkred', linewidth=1.5)
ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(loc='lower left')

# Plot 3: Trade distribution over time
bins = pd.date_range(start_date, end_date, freq='3D')
trade_counts, _ = np.histogram(portfolio_sorted['exit_time'], bins=bins)
ax3.bar(bins[:-1], trade_counts, width=2.5, color='steelblue', alpha=0.7, edgecolor='black')
ax3.set_ylabel('Trades per 3 Days', fontsize=12, fontweight='bold')
ax3.set_xlabel('Date', fontsize=12, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')

# Format x-axis
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax3.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.xticks(rotation=45)

plt.tight_layout()
plt.savefig('portfolio_equity_curve_FINAL.png', dpi=150, bbox_inches='tight')
print('✅ Saved: portfolio_equity_curve_FINAL.png')
plt.close()

# Trade breakdown by exit reason
print()
print('='*100)
print('🎯 EXIT REASON BREAKDOWN')
print('='*100)
print()

exit_summary = portfolio.groupby('exit_reason').agg({
    'pnl_pct': ['count', 'mean'],
    'dollar_pnl': 'sum'
}).round(2)

print(exit_summary)
print()

# Monthly breakdown
portfolio_sorted['month'] = portfolio_sorted['exit_time'].dt.to_period('M')
monthly = portfolio_sorted.groupby('month').agg({
    'dollar_pnl': 'sum',
    'coin': 'count'
}).rename(columns={'coin': 'trades'})

print('='*100)
print('📅 MONTHLY BREAKDOWN')
print('='*100)
print()
print(monthly)
print()

print('='*100)
print('✅ ANALYSIS COMPLETE')
print('='*100)
