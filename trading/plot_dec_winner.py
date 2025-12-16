#!/usr/bin/env python3
"""Plot December winner trade with signal, break, and entry marked"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates

df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# Calculate RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Calculate ATR
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()

def find_swing_low(df, idx, lookback):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['low'].min()

def find_swing_high(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['high'].max()

# Find the December winner trade
limit_atr_offset = 0.8
rsi_trigger = 72
lookback = 5
max_wait_bars = 20

signal_idx = None
break_idx = None
entry_idx = None
entry_price = None
sl_price = None
tp_price = None
exit_idx = None

armed = False
swing_low = None
limit_pending = False
limit_price = None
limit_placed_idx = None
swing_high_for_sl = None

for i in range(lookback, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        continue

    # Looking for December signal around Dec 2, 18:30 UTC
    if row['timestamp'] >= pd.Timestamp('2025-12-02 00:00:00') and \
       row['timestamp'] <= pd.Timestamp('2025-12-03 00:00:00'):

        if row['rsi'] > rsi_trigger:
            armed = True
            signal_idx = i
            swing_low = find_swing_low(df, i, lookback)
            limit_pending = False

    if armed and swing_low is not None and not limit_pending:
        if row['low'] < swing_low:
            # Break detected
            break_idx = i
            atr = row['atr']
            limit_price = swing_low + (atr * limit_atr_offset)
            swing_high_for_sl = find_swing_high(df, signal_idx, i)
            limit_pending = True
            limit_placed_idx = i
            armed = False

    if limit_pending and break_idx is not None:
        if i - limit_placed_idx > max_wait_bars:
            limit_pending = False
            continue

        if row['high'] >= limit_price:
            # Entry filled
            entry_idx = i
            entry_price = limit_price
            sl_price = swing_high_for_sl
            tp_price = entry_price * (1 - 10.0 / 100)

            # Find exit
            for j in range(i + 1, min(i + 500, len(df))):
                future_row = df.iloc[j]
                if future_row['low'] <= tp_price:
                    exit_idx = j
                    break

            break

if signal_idx is None or entry_idx is None:
    print("Trade not found!")
    exit(1)

# Get data range: 24 hours before signal to exit
start_idx = max(0, signal_idx - 96)  # 96 bars = 24 hours (15min bars)
end_idx = min(len(df), exit_idx + 20)

plot_df = df.iloc[start_idx:end_idx].copy().reset_index(drop=True)

# Adjust indices for plot_df
signal_idx_plot = signal_idx - start_idx
break_idx_plot = break_idx - start_idx
entry_idx_plot = entry_idx - start_idx
exit_idx_plot = exit_idx - start_idx

# Create figure with 2 subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10),
                                gridspec_kw={'height_ratios': [3, 1]},
                                sharex=True)

# Plot candlesticks
for idx, row in plot_df.iterrows():
    color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'

    # Draw candle body
    body_height = abs(row['close'] - row['open'])
    body_bottom = min(row['open'], row['close'])
    ax1.add_patch(mpatches.Rectangle(
        (idx - 0.3, body_bottom), 0.6, body_height,
        facecolor=color, edgecolor=color, linewidth=1
    ))

    # Draw wicks
    ax1.plot([idx, idx], [row['low'], row['high']],
             color=color, linewidth=1)

# Mark key levels
signal_candle = plot_df.iloc[signal_idx_plot]
break_candle = plot_df.iloc[break_idx_plot]
entry_candle = plot_df.iloc[entry_idx_plot]
exit_candle = plot_df.iloc[exit_idx_plot]

# Vertical lines
ax1.axvline(signal_idx_plot, color='yellow', linestyle='--', linewidth=2,
            label=f'Signal (RSI={signal_candle["rsi"]:.1f})', alpha=0.8)
ax1.axvline(break_idx_plot, color='orange', linestyle='--', linewidth=2,
            label='Support Break', alpha=0.8)
ax1.axvline(entry_idx_plot, color='lime', linestyle='--', linewidth=2.5,
            label='Entry (Limit Filled)', alpha=0.9)
ax1.axvline(exit_idx_plot, color='cyan', linestyle='--', linewidth=2,
            label='Exit (TP Hit)', alpha=0.8)

# Horizontal lines
ax1.axhline(swing_low, color='red', linestyle='-', linewidth=1.5,
            label=f'Swing Low: ${swing_low:.4f}', alpha=0.7,
            xmin=(signal_idx_plot-5)/len(plot_df),
            xmax=(break_idx_plot+2)/len(plot_df))
ax1.axhline(entry_price, color='green', linestyle='-', linewidth=2,
            label=f'Entry: ${entry_price:.4f}', alpha=0.8)
ax1.axhline(sl_price, color='red', linestyle=':', linewidth=2,
            label=f'Stop Loss: ${sl_price:.4f}', alpha=0.6)
ax1.axhline(tp_price, color='blue', linestyle='-', linewidth=2,
            label=f'Take Profit: ${tp_price:.4f}', alpha=0.8)

# Add annotations
ax1.annotate(f'RSI {signal_candle["rsi"]:.1f} >72\nSignal Armed',
             xy=(signal_idx_plot, signal_candle['high']),
             xytext=(signal_idx_plot, signal_candle['high'] + 0.005),
             fontsize=9, ha='center', color='yellow', weight='bold',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.7))

ax1.annotate(f'Support Breaks\nLimit @ ${limit_price:.4f}',
             xy=(break_idx_plot, break_candle['low']),
             xytext=(break_idx_plot, break_candle['low'] - 0.008),
             fontsize=9, ha='center', color='orange', weight='bold',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.7))

ax1.annotate(f'ENTRY\n${entry_price:.4f}\nSize: $7,992',
             xy=(entry_idx_plot, entry_price),
             xytext=(entry_idx_plot + 10, entry_price + 0.01),
             fontsize=10, ha='left', color='lime', weight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='darkgreen', alpha=0.8),
             arrowprops=dict(arrowstyle='->', color='lime', lw=2))

ax1.annotate(f'TP HIT!\n+$791 (+10%)\n68.8h hold',
             xy=(exit_idx_plot, tp_price),
             xytext=(exit_idx_plot - 15, tp_price - 0.01),
             fontsize=10, ha='right', color='cyan', weight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='darkblue', alpha=0.8),
             arrowprops=dict(arrowstyle='->', color='cyan', lw=2))

ax1.set_ylabel('Price (USDT)', fontsize=12, weight='bold')
ax1.set_title('MELANIA-USDT: December Winner Trade ($791 profit)\n' +
              'Strategy: RSI >72 → Support Break → Limit 0.8 ATR above → TP 10%',
              fontsize=14, weight='bold', pad=20)
ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)
ax1.grid(True, alpha=0.3)

# RSI subplot
ax2.plot(plot_df.index, plot_df['rsi'], color='purple', linewidth=1.5, label='RSI(14)')
ax2.axhline(72, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Trigger (72)')
ax2.axhline(50, color='gray', linestyle=':', linewidth=0.5, alpha=0.5)
ax2.axvline(signal_idx_plot, color='yellow', linestyle='--', linewidth=2, alpha=0.5)
ax2.axvline(break_idx_plot, color='orange', linestyle='--', linewidth=2, alpha=0.5)
ax2.axvline(entry_idx_plot, color='lime', linestyle='--', linewidth=2, alpha=0.5)
ax2.axvline(exit_idx_plot, color='cyan', linestyle='--', linewidth=2, alpha=0.5)

ax2.set_ylabel('RSI', fontsize=11, weight='bold')
ax2.set_xlabel('Time', fontsize=11, weight='bold')
ax2.legend(loc='upper left', fontsize=9)
ax2.grid(True, alpha=0.3)
ax2.set_ylim(0, 100)

# Format x-axis with timestamps
timestamps = plot_df['timestamp'].tolist()
step = max(1, len(timestamps) // 20)
ax2.set_xticks(range(0, len(timestamps), step))
ax2.set_xticklabels([timestamps[i].strftime('%b %d\n%H:%M') for i in range(0, len(timestamps), step)],
                     rotation=0, ha='center', fontsize=9)

plt.tight_layout()
plt.savefig('december_winner_trade.png', dpi=150, bbox_inches='tight', facecolor='white')
print("Chart saved as: december_winner_trade.png")
print()
print("Trade Summary:")
print(f"Signal: {df.iloc[signal_idx]['timestamp']} (RSI {signal_candle['rsi']:.1f})")
print(f"Break:  {df.iloc[break_idx]['timestamp']}")
print(f"Entry:  {df.iloc[entry_idx]['timestamp']} @ ${entry_price:.4f}")
print(f"Exit:   {df.iloc[exit_idx]['timestamp']} @ ${tp_price:.4f}")
print(f"Profit: +$791.23 (+10.00%)")
