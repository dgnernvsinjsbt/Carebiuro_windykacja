#!/usr/bin/env python3
"""
Generate equity curve for BTC RSI 30/65 + 2x ATR stop
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# Load data
df = pd.read_csv('btc_1h_90d.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("BTC RSI 30/65 + 2x ATR STOP - EQUITY CURVE")
print("=" * 80)

# Calculate indicators
df['rsi'] = calculate_rsi(df['close'], 14)
df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)

print(f"\nTimeframe: 1h (hourly)")
print(f"Data period: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Total candles: {len(df):,}")

# Backtest with detailed trade tracking
trades = []

for i in range(50, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i-1]

    # LONG signal
    if prev['rsi'] <= 30 and row['rsi'] > 30:
        entry_price = row['close']
        entry_time = row['timestamp']
        atr_val = row['atr']
        sl_price = entry_price - (2.0 * atr_val)

        exit_found = False
        for j in range(i+1, min(i+168, len(df))):
            exit_row = df.iloc[j]

            # Stop loss
            if exit_row['low'] <= sl_price:
                exit_price = sl_price
                exit_time = exit_row['timestamp']
                exit_reason = 'SL'
                exit_found = True
                break

            # RSI target
            if exit_row['rsi'] >= 65:
                exit_price = exit_row['close']
                exit_time = exit_row['timestamp']
                exit_reason = 'TP'
                exit_found = True
                break

        if not exit_found:
            j = min(i+167, len(df)-1)
            exit_price = df.iloc[j]['close']
            exit_time = df.iloc[j]['timestamp']
            exit_reason = 'TIME'

        pnl_pct = (exit_price - entry_price) / entry_price * 100

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': 'LONG',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

    # SHORT signal
    elif prev['rsi'] >= 65 and row['rsi'] < 65:
        entry_price = row['close']
        entry_time = row['timestamp']
        atr_val = row['atr']
        sl_price = entry_price + (2.0 * atr_val)

        exit_found = False
        for j in range(i+1, min(i+168, len(df))):
            exit_row = df.iloc[j]

            if exit_row['high'] >= sl_price:
                exit_price = sl_price
                exit_time = exit_row['timestamp']
                exit_reason = 'SL'
                exit_found = True
                break

            if exit_row['rsi'] <= 30:
                exit_price = exit_row['close']
                exit_time = exit_row['timestamp']
                exit_reason = 'TP'
                exit_found = True
                break

        if not exit_found:
            j = min(i+167, len(df)-1)
            exit_price = df.iloc[j]['close']
            exit_time = df.iloc[j]['timestamp']
            exit_reason = 'TIME'

        pnl_pct = (entry_price - exit_price) / entry_price * 100

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': 'SHORT',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

df_trades = pd.DataFrame(trades)

# Calculate metrics
df_trades['cum_pnl'] = df_trades['pnl_pct'].cumsum()
equity = 100 + df_trades['cum_pnl']
running_max = equity.cummax()
drawdown = (equity - running_max) / running_max * 100

total_return = df_trades['pnl_pct'].sum()
max_dd = drawdown.min()
rdd = total_return / abs(max_dd)

print(f"\n" + "-" * 80)
print("PERFORMANCE SUMMARY")
print("-" * 80)

print(f"\nTotal trades: {len(df_trades)}")
print(f"  LONG: {len(df_trades[df_trades['direction'] == 'LONG'])}")
print(f"  SHORT: {len(df_trades[df_trades['direction'] == 'SHORT'])}")

print(f"\nReturns:")
print(f"  Total: {total_return:+.2f}%")
print(f"  Max DD: {max_dd:.2f}%")
print(f"  R/DD: {rdd:.2f}x")

print(f"\nWin Rate: {(df_trades['pnl_pct'] > 0).mean() * 100:.1f}%")
print(f"  Avg Winner: {df_trades[df_trades['pnl_pct'] > 0]['pnl_pct'].mean():.2f}%")
print(f"  Avg Loser: {df_trades[df_trades['pnl_pct'] <= 0]['pnl_pct'].mean():.2f}%")

print(f"\nExit Reasons:")
for reason, count in df_trades['exit_reason'].value_counts().items():
    pct = count / len(df_trades) * 100
    print(f"  {reason}: {count} ({pct:.1f}%)")

print(f"\nHolding Period:")
df_trades['hold_hours'] = (df_trades['exit_time'] - df_trades['entry_time']).dt.total_seconds() / 3600
print(f"  Avg: {df_trades['hold_hours'].mean():.1f}h ({df_trades['hold_hours'].mean()/24:.1f} days)")
print(f"  Min: {df_trades['hold_hours'].min():.1f}h")
print(f"  Max: {df_trades['hold_hours'].max():.1f}h")

# Create equity curve chart
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Plot 1: Equity curve
ax1.plot(df_trades['exit_time'], equity, linewidth=2, color='#2E86AB', label='Equity')
ax1.plot(df_trades['exit_time'], running_max, linewidth=1, color='#A23B72', linestyle='--', alpha=0.7, label='Running Max')
ax1.axhline(y=100, color='gray', linestyle='--', alpha=0.5)
ax1.fill_between(df_trades['exit_time'], 100, equity, where=(equity >= 100), alpha=0.3, color='green', label='Profit')
ax1.fill_between(df_trades['exit_time'], 100, equity, where=(equity < 100), alpha=0.3, color='red', label='Loss')

# Mark TP trades with stars
tp_trades = df_trades[df_trades['exit_reason'] == 'TP']
if len(tp_trades) > 0:
    tp_equity = 100 + tp_trades['cum_pnl']
    ax1.scatter(tp_trades['exit_time'], tp_equity, color='gold', s=100, marker='*',
                zorder=5, label=f'TP Exits ({len(tp_trades)})', edgecolors='black', linewidths=0.5)

ax1.set_ylabel('Equity (%)', fontsize=12, fontweight='bold')
ax1.set_title(f'BTC RSI 30/65 Swing Strategy - Equity Curve\n' +
              f'Timeframe: 1h | Period: {df["timestamp"].min().date()} to {df["timestamp"].max().date()}\n' +
              f'Return: {total_return:+.2f}% | Max DD: {max_dd:.2f}% | R/DD: {rdd:.2f}x | Trades: {len(df_trades)}',
              fontsize=14, fontweight='bold', pad=20)
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)

# Plot 2: Drawdown
ax2.fill_between(df_trades['exit_time'], 0, drawdown, color='red', alpha=0.4)
ax2.plot(df_trades['exit_time'], drawdown, color='darkred', linewidth=1.5)
ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
ax2.grid(True, alpha=0.3)

# Add max DD annotation
max_dd_idx = drawdown.idxmin()
max_dd_time = df_trades.loc[max_dd_idx, 'exit_time']
ax2.annotate(f'Max DD: {max_dd:.2f}%',
             xy=(max_dd_time, max_dd),
             xytext=(max_dd_time, max_dd - 2),
             fontsize=10, fontweight='bold', color='darkred',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))

plt.tight_layout()

# Save chart
output_path = 'results/btc_rsi_swing_equity_curve.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\n✅ Equity curve saved: {output_path}")

# Save trade details
df_trades.to_csv('results/btc_rsi_swing_trades_final.csv', index=False)
print(f"✅ Trade details saved: results/btc_rsi_swing_trades_final.csv")

print("\n" + "=" * 80)
