"""
Visualize equity curve for optimized FARTCOIN 30M strategy
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def calculate_ema(df, span):
    return df['close'].ewm(span=span, adjust=False).mean()

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    tr = ranges.max(axis=1)
    return tr.rolling(period).mean()

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Load data
df = pd.read_csv('fartcoin_30m_jan2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("="*80)
print("FARTCOIN OPTIMIZED STRATEGY - EQUITY CURVE")
print("="*80)
print(f"\nData: {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")

# Calculate indicators
df['ema_3'] = calculate_ema(df, 3)
df['ema_15'] = calculate_ema(df, 15)
df['momentum_7d'] = df['close'].pct_change(336) * 100
df['atr'] = calculate_atr(df)
df['atr_pct'] = (df['atr'] / df['close']) * 100
df['rsi'] = calculate_rsi(df)

# Optimized filter
df['allow_short'] = (df['momentum_7d'] < 0) & (df['atr_pct'] < 6) & (df['rsi'] < 60)

# Run backtest
trades = []
in_position = False
entry_price = 0
entry_date = None
stop_loss = 0
take_profit = 0
fee = 0.0001

for i in range(1, len(df)):
    row = df.iloc[i]
    prev_row = df.iloc[i-1]

    if not in_position:
        if (row['ema_3'] < row['ema_15'] and
            prev_row['ema_3'] >= prev_row['ema_15'] and
            row['allow_short']):

            in_position = True
            entry_price = row['close']
            entry_date = row['timestamp']
            stop_loss = entry_price * 1.03
            take_profit = entry_price * 0.95
    else:
        exit_type = None
        exit_price = None

        if row['high'] >= stop_loss:
            exit_price = stop_loss
            exit_type = 'SL'
            pnl = (entry_price - stop_loss) / entry_price - fee
        elif row['low'] <= take_profit:
            exit_price = take_profit
            exit_type = 'TP'
            pnl = (entry_price - take_profit) / entry_price - fee

        if exit_type:
            trades.append({
                'exit_date': row['timestamp'],
                'pnl_pct': pnl * 100,
                'exit_type': exit_type
            })
            in_position = False

# Build equity curve
trades_df = pd.DataFrame(trades)
trades_df = trades_df.sort_values('exit_date').reset_index(drop=True)

equity = 1.0
equity_curve = [equity]
dates = [df['timestamp'].min()]

for _, trade in trades_df.iterrows():
    equity *= (1 + trade['pnl_pct'] / 100)
    equity_curve.append(equity)
    dates.append(trade['exit_date'])

# Calculate metrics
equity_series = pd.Series(equity_curve)
running_max = equity_series.expanding().max()
drawdown = (equity_series - running_max) / running_max * 100
max_dd = drawdown.min()
total_return = (equity - 1) * 100

winners = len(trades_df[trades_df['pnl_pct'] > 0])
win_rate = winners / len(trades_df) * 100

print(f"\nFinal Results:")
print(f"  Total Trades: {len(trades_df)}")
print(f"  Win Rate: {win_rate:.1f}%")
print(f"  Total Return: {total_return:.2f}%")
print(f"  Max Drawdown: {max_dd:.2f}%")
print(f"  Final Equity: {equity:.2f}x")

# Create visualization
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})

# Equity curve
ax1.plot(dates, equity_curve, linewidth=2, color='#2E86AB', label='Equity')
ax1.fill_between(dates, 1, equity_curve, alpha=0.3, color='#2E86AB')
ax1.axhline(y=1, color='gray', linestyle='--', alpha=0.5, linewidth=1)

# Mark winning and losing trades
for _, trade in trades_df.iterrows():
    idx = dates.index(trade['exit_date'])
    color = 'green' if trade['pnl_pct'] > 0 else 'red'
    marker = '^' if trade['pnl_pct'] > 0 else 'v'
    ax1.scatter(trade['exit_date'], equity_curve[idx], color=color, marker=marker,
                s=30, alpha=0.6, zorder=5)

ax1.set_title(f'FARTCOIN 30M - Optimized Strategy Equity Curve\n' +
              f'Return: {total_return:.2f}% | Max DD: {max_dd:.2f}% | Win Rate: {win_rate:.1f}% | Trades: {len(trades_df)}',
              fontsize=14, fontweight='bold', pad=20)
ax1.set_ylabel('Equity (Multiple of Starting Capital)', fontsize=11)
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.set_xlim(dates[0], dates[-1])

# Add strategy info text box
strategy_text = (
    'Strategy: EMA 3/15 SHORT Crossover\n'
    'Filters: Mom7d<0 + ATR<6% + RSI<60\n'
    'Risk: SL=3% | TP=5%\n'
    'Fees: 0.01% per trade'
)
ax1.text(0.02, 0.98, strategy_text, transform=ax1.transAxes,
         fontsize=9, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

# Drawdown
ax2.fill_between(range(len(drawdown)), drawdown, 0, color='red', alpha=0.3)
ax2.plot(range(len(drawdown)), drawdown, color='darkred', linewidth=1.5)
ax2.set_title('Drawdown (%)', fontsize=11, fontweight='bold')
ax2.set_ylabel('Drawdown %', fontsize=10)
ax2.set_xlabel('Trade Number', fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.axhline(y=max_dd, color='red', linestyle='--', alpha=0.5, linewidth=1)
ax2.text(len(drawdown)*0.95, max_dd*0.9, f'Max: {max_dd:.2f}%',
         ha='right', fontsize=9, color='darkred')

plt.tight_layout()
plt.savefig('results/fartcoin_optimized_equity_curve.png', dpi=300, bbox_inches='tight')
print(f"\n✓ Saved equity curve to results/fartcoin_optimized_equity_curve.png")

plt.show()
print("="*80)
