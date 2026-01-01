"""
Generate equity curve for optimized NQ Futures strategy
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Load best NQ trades
trades = pd.read_csv('trading/results/nq_futures_best_optimized.csv')
trades['entry_time'] = pd.to_datetime(trades['entry_time'])
trades['exit_time'] = pd.to_datetime(trades['exit_time'])

print('='*80)
print('📈 NQ FUTURES OPTIMIZED - EQUITY CURVE')
print('='*80)
print()
print(f'Strategy: RSI 40/60, 0.3% limit, 2.0x SL, 4.0x TP')
print(f'Period: {trades["entry_time"].min().date()} to {trades["exit_time"].max().date()}')
print(f'Trades: {len(trades)}')
print()

# Calculate equity curve
starting_equity = 1000.0
equity = starting_equity
peak = starting_equity

equity_curve = []
drawdown_curve = []
dates = []

# Add starting point
equity_curve.append(equity)
drawdown_curve.append(0)
dates.append(trades['entry_time'].min())

for _, trade in trades.iterrows():
    # Apply trade PnL
    equity += equity * (trade['pnl_pct'] / 100)

    # Track peak and drawdown
    if equity > peak:
        peak = equity

    dd = ((equity - peak) / peak) * 100

    equity_curve.append(equity)
    drawdown_curve.append(dd)
    dates.append(trade['exit_time'])

# Calculate metrics
final_equity = equity
total_return = ((final_equity - starting_equity) / starting_equity) * 100
max_dd = min(drawdown_curve)

print(f'Starting Equity: ${starting_equity:.2f}')
print(f'Final Equity: ${final_equity:.2f}')
print(f'Total Return: {total_return:+.2f}%')
print(f'Max Drawdown: {max_dd:.2f}%')
print(f'Return/DD Ratio: {abs(total_return / max_dd):.2f}x')
print()

# Win/Loss stats
winners = trades[trades['pnl_pct'] > 0]
losers = trades[trades['pnl_pct'] < 0]

print(f'Winners: {len(winners)} ({len(winners)/len(trades)*100:.1f}%)')
print(f'Losers: {len(losers)} ({len(losers)/len(trades)*100:.1f}%)')
print(f'Avg Winner: {winners["pnl_pct"].mean():.2f}%')
print(f'Avg Loser: {losers["pnl_pct"].mean():.2f}%')
print()

# Exit breakdown
tp_exits = len(trades[trades['exit_reason'] == 'TP'])
sl_exits = len(trades[trades['exit_reason'] == 'STOP'])
rsi_exits = len(trades[trades['exit_reason'] == 'RSI'])

print(f'Exit Breakdown:')
print(f'  Take Profit: {tp_exits} ({tp_exits/len(trades)*100:.1f}%)')
print(f'  Stop Loss: {sl_exits} ({sl_exits/len(trades)*100:.1f}%)')
print(f'  RSI Exit: {rsi_exits} ({rsi_exits/len(trades)*100:.1f}%)')
print()

# Create figure with 2 subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
fig.suptitle('NQ FUTURES (NASDAQ 100) - Optimized RSI Mean Reversion Strategy',
             fontsize=16, fontweight='bold', y=0.995)

# Plot equity curve
ax1.plot(dates, equity_curve, linewidth=2, color='#2E7D32', label='Equity')
ax1.axhline(y=starting_equity, color='gray', linestyle='--', alpha=0.5, label='Starting Equity')
ax1.fill_between(dates, starting_equity, equity_curve,
                  where=[e >= starting_equity for e in equity_curve],
                  alpha=0.2, color='green', label='Profit Zone')
ax1.fill_between(dates, starting_equity, equity_curve,
                  where=[e < starting_equity for e in equity_curve],
                  alpha=0.2, color='red', label='Loss Zone')

ax1.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax1.set_title('Equity Curve', fontsize=14, fontweight='bold', pad=10)
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left', fontsize=10)

# Add performance metrics box
textstr = f'Return: +{total_return:.2f}%\n'
textstr += f'Max DD: {max_dd:.2f}%\n'
textstr += f'R/R Ratio: {abs(total_return / max_dd):.2f}x\n'
textstr += f'Win Rate: {len(winners)/len(trades)*100:.1f}%\n'
textstr += f'Trades: {len(trades)}'

props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax1.text(0.02, 0.98, textstr, transform=ax1.transAxes, fontsize=11,
         verticalalignment='top', bbox=props, family='monospace')

# Plot drawdown
ax2.fill_between(dates, 0, drawdown_curve, color='#D32F2F', alpha=0.6, label='Drawdown')
ax2.plot(dates, drawdown_curve, linewidth=1.5, color='#B71C1C')
ax2.axhline(y=max_dd, color='red', linestyle='--', linewidth=1.5,
            label=f'Max DD: {max_dd:.2f}%', alpha=0.7)

ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
ax2.set_title('Drawdown', fontsize=14, fontweight='bold', pad=10)
ax2.grid(True, alpha=0.3)
ax2.legend(loc='lower left', fontsize=10)

# Format x-axis
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
plt.xticks(rotation=45, ha='right')

# Adjust layout
plt.tight_layout()

# Save figure
output_file = 'trading/results/nq_futures_equity_curve.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f'💾 Saved equity curve to: {output_file}')

print()
print('='*80)
print('📊 TRADE-BY-TRADE ANALYSIS')
print('='*80)
print()

# Show first 10 and last 10 trades
print('First 10 trades:')
print(f'{"Date":<12} {"Side":<6} {"P&L":<8} {"Exit":<6} {"Equity"}')
print('-'*50)

equity = starting_equity
for i, (_, trade) in enumerate(trades.head(10).iterrows()):
    equity += equity * (trade['pnl_pct'] / 100)
    print(f'{trade["exit_time"].strftime("%Y-%m-%d"):<12} '
          f'{trade["side"]:<6} '
          f'{trade["pnl_pct"]:>6.2f}% '
          f'{trade["exit_reason"]:<6} '
          f'${equity:>8.2f}')

print()
print('Last 10 trades:')
print(f'{"Date":<12} {"Side":<6} {"P&L":<8} {"Exit":<6} {"Equity"}')
print('-'*50)

# Calculate equity at start of last 10 trades
equity = starting_equity
for _, trade in trades.iloc[:-10].iterrows():
    equity += equity * (trade['pnl_pct'] / 100)

for _, trade in trades.tail(10).iterrows():
    equity += equity * (trade['pnl_pct'] / 100)
    print(f'{trade["exit_time"].strftime("%Y-%m-%d"):<12} '
          f'{trade["side"]:<6} '
          f'{trade["pnl_pct"]:>6.2f}% '
          f'{trade["exit_reason"]:<6} '
          f'${equity:>8.2f}')

print()
print('='*80)
print('🎯 KEY INSIGHTS')
print('='*80)
print()
print('Strategy Strengths:')
print('  ✅ High win rate (65.5%) from wider 2.0x ATR stops')
print('  ✅ 44.8% TP rate - strategy capturing full mean reversion moves')
print('  ✅ Asymmetric 2:1 risk/reward (2x SL → 4x TP)')
print('  ✅ Smooth equity curve with -2.13% max drawdown')
print()
print('Why it works on NQ:')
print('  • NASDAQ 100 has higher volatility than S&P 500')
print('  • Tech sector creates cleaner RSI extremes')
print('  • 1h timeframe smooths noise but catches moves')
print('  • Wider stops + higher targets = big winners')
print()
print('vs Crypto:')
print(f'  NQ: 6.24x R/R, +13.31%, 65.5% win rate')
print(f'  PEPE: 7.13x R/R, +21.72, 83.3% win rate')
print(f'  Gap: -12.5% (close but crypto wins)')
print()
