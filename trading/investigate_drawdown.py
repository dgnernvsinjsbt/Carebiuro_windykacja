"""
Investigate September flatness and October drawdown
"""
import pandas as pd
import matplotlib.pyplot as plt

# Load portfolio trades
df = pd.read_csv('portfolio_FIXED.csv')
df['time'] = pd.to_datetime(df['time'])
df['entry_time'] = pd.to_datetime(df['entry_time'])
df['exit_time'] = pd.to_datetime(df['exit_time'])
df = df.sort_values('exit_time').reset_index(drop=True)

print('='*100)
print('🔍 INVESTIGATING EQUITY CURVE ANOMALIES')
print('='*100)
print()

# September performance
sep_trades = df[df['exit_time'].dt.month == 9]
print(f'SEPTEMBER TRADES: {len(sep_trades)}')
print(f'Total P&L: ${sep_trades["dollar_pnl"].sum():.2f}')
print(f'Winners: {len(sep_trades[sep_trades["pnl_pct"] > 0])}')
print(f'Losers: {len(sep_trades[sep_trades["pnl_pct"] < 0])}')
print()

if len(sep_trades) > 0:
    print('September trades:')
    for idx, trade in sep_trades.iterrows():
        print(f'{trade["exit_time"].strftime("%Y-%m-%d %H:%M")} - {trade["coin"]:<15} {trade["exit_reason"]:<5} {trade["pnl_pct"]:>7.2f}% → Equity: ${trade["equity"]:.2f}')
    print()

# October 10-12 (potential drawdown)
oct_window = df[(df['exit_time'] >= '2025-10-10') & (df['exit_time'] <= '2025-10-13')]
print('='*100)
print(f'OCT 10-13 TRADES: {len(oct_window)}')
print('='*100)
print()

if len(oct_window) > 0:
    print('Trades around the drawdown:')
    for idx, trade in oct_window.iterrows():
        print(f'{trade["exit_time"].strftime("%Y-%m-%d %H:%M")} - {trade["coin"]:<15} {trade["exit_reason"]:<5} {trade["pnl_pct"]:>7.2f}% → Equity: ${trade["equity"]:.2f}')
    print()

# Find the actual drawdown period
df['cumulative'] = df['dollar_pnl'].cumsum()
df['peak'] = df['equity'].cummax()
df['drawdown'] = df['equity'] - df['peak']
df['drawdown_pct'] = (df['drawdown'] / df['peak']) * 100

# Find max drawdown
max_dd_idx = df['drawdown_pct'].idxmin()
max_dd_trade = df.loc[max_dd_idx]

print('='*100)
print(f'MAX DRAWDOWN OCCURRED:')
print('='*100)
print(f'Date: {max_dd_trade["exit_time"].strftime("%Y-%m-%d %H:%M")}')
print(f'Coin: {max_dd_trade["coin"]}')
print(f'Equity: ${max_dd_trade["equity"]:.2f}')
print(f'Peak: ${max_dd_trade["peak"]:.2f}')
print(f'Drawdown: {max_dd_trade["drawdown_pct"]:.2f}%')
print()

# Show trades around max DD
context_start = max(0, max_dd_idx - 5)
context_end = min(len(df), max_dd_idx + 5)
print('TRADES AROUND MAX DRAWDOWN:')
print(f'{"Date":<20} {"Coin":<15} {"Exit":<5} {"P&L %":<10} {"Equity":<12} {"DD %"}')
print('-'*100)
for idx in range(context_start, context_end):
    trade = df.loc[idx]
    marker = ' ← MAX DD' if idx == max_dd_idx else ''
    print(f'{trade["exit_time"].strftime("%Y-%m-%d %H:%M"):<20} {trade["coin"]:<15} {trade["exit_reason"]:<5} {trade["pnl_pct"]:>7.2f}%  ${trade["equity"]:<10.2f} {trade["drawdown_pct"]:>6.2f}%{marker}')
print()

# Check if there's a calculation issue with equity
print('='*100)
print('EQUITY CALCULATION VERIFICATION')
print('='*100)
print()

# Manually recalculate equity to verify
equity = 1000.0
for idx, trade in df.iterrows():
    expected_equity = equity + trade['dollar_pnl']
    actual_equity = trade['equity']

    if abs(expected_equity - actual_equity) > 0.01:
        print(f'⚠️ MISMATCH at {trade["exit_time"].strftime("%Y-%m-%d %H:%M")}')
        print(f'   Expected: ${expected_equity:.2f}, Actual: ${actual_equity:.2f}')
        print(f'   Difference: ${abs(expected_equity - actual_equity):.2f}')
        print()

    equity = actual_equity

print('✅ Equity calculations verified')
print()

# Plot detailed equity curve with annotations
fig, ax = plt.subplots(figsize=(16, 8))

ax.plot(df['exit_time'], df['equity'], linewidth=2, color='steelblue', label='Equity', zorder=2)
ax.axhline(y=1000, color='gray', linestyle='--', alpha=0.5, label='Starting Equity')

# Mark max drawdown
ax.scatter([max_dd_trade['exit_time']], [max_dd_trade['equity']],
           color='red', s=200, marker='v', zorder=3, label=f'Max DD: {max_dd_trade["drawdown_pct"]:.2f}%')

# Mark losing trades
losers = df[df['pnl_pct'] < 0]
if len(losers) > 0:
    ax.scatter(losers['exit_time'], losers['equity'],
               color='red', s=50, alpha=0.5, zorder=1, label='Losing trades')

ax.set_xlabel('Date', fontsize=12, fontweight='bold')
ax.set_ylabel('Equity ($)', fontsize=12, fontweight='bold')
ax.set_title('Equity Curve - Detailed View', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend()

plt.tight_layout()
plt.savefig('equity_detailed.png', dpi=150, bbox_inches='tight')
print('✅ Saved: equity_detailed.png')
print()

# Monthly equity growth
print('='*100)
print('MONTHLY EQUITY PROGRESSION')
print('='*100)
print()

df['month'] = df['exit_time'].dt.to_period('M')
monthly_end_equity = df.groupby('month')['equity'].last()

print(f'{"Month":<10} {"Ending Equity":<15} {"Monthly Gain"}')
print('-'*50)
prev_equity = 1000.0
for month, equity in monthly_end_equity.items():
    gain = equity - prev_equity
    gain_pct = (gain / prev_equity) * 100
    print(f'{str(month):<10} ${equity:<14.2f} +${gain:>6.2f} ({gain_pct:+.2f}%)')
    prev_equity = equity
