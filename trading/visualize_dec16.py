#!/usr/bin/env python3
"""
Visualize Dec 16 trades on candlestick chart
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.dates import DateFormatter
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

# Dec 16 only
df_dec16 = df[df['timestamp'].dt.date == pd.to_datetime('2025-12-16').date()].copy().reset_index(drop=True)

print(f"Dec 16: {len(df_dec16)} candles")

# Run strategy with 0.8% offset
offset_pct = 0.8
trades = []

has_pending = False
pending_limit = None
pending_signal_bar = None
pending_sl = None
pending_tp = None

i = 32
while i < len(df_dec16):
    row = df_dec16.iloc[i]
    
    if pd.isna(row['atr']):
        i += 1
        continue
    
    if has_pending:
        bars_waiting = i - pending_signal_bar
        
        if row['low'] <= pending_limit:
            entry_price = pending_limit
            sl_dist_pct = ((pending_sl - entry_price) / entry_price) * 100
            
            if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                # Find exit
                hit_sl = False
                hit_tp = False
                exit_idx = None
                
                for k in range(i + 1, min(i + 100, len(df_dec16))):
                    exit_row = df_dec16.iloc[k]
                    
                    if exit_row['high'] >= pending_sl:
                        hit_sl = True
                        exit_idx = k
                        break
                    elif exit_row['low'] <= pending_tp:
                        hit_tp = True
                        exit_idx = k
                        break
                
                if exit_idx:
                    trades.append({
                        'entry_time': row['timestamp'],
                        'entry_idx': i,
                        'entry_price': entry_price,
                        'sl_price': pending_sl,
                        'tp_price': pending_tp,
                        'exit_time': df_dec16.iloc[exit_idx]['timestamp'],
                        'exit_idx': exit_idx,
                        'exit_reason': 'TP' if hit_tp else 'SL'
                    })
            
            has_pending = False
        
        elif row['high'] >= pending_sl:
            has_pending = False
        
        elif bars_waiting >= 16:
            has_pending = False
        
        i += 1
        continue
    
    # Check for signal
    high_8h = df_dec16.iloc[max(0, i-32):i]['high'].max()
    dist_pct = ((row['close'] - high_8h) / high_8h) * 100
    
    if dist_pct <= -2.5:
        signal_price = row['close']
        sl_price = high_8h
        tp_price = signal_price * (1 - 0.05)
        limit_price = signal_price * (1 + offset_pct / 100)
        
        if limit_price < sl_price:
            has_pending = True
            pending_limit = limit_price
            pending_signal_bar = i
            pending_sl = sl_price
            pending_tp = tp_price
    
    i += 1

print(f"Total trades on Dec 16: {len(trades)}")

# Create candlestick chart
fig, ax = plt.subplots(figsize=(20, 10))

# Plot candlesticks
for idx, row in df_dec16.iterrows():
    color = 'green' if row['close'] >= row['open'] else 'red'
    
    # Candle body
    ax.plot([idx, idx], [row['low'], row['high']], color='black', linewidth=0.5)
    body_height = abs(row['close'] - row['open'])
    body_bottom = min(row['open'], row['close'])
    rect = mpatches.Rectangle((idx - 0.3, body_bottom), 0.6, body_height, 
                               facecolor=color, edgecolor='black', linewidth=0.5)
    ax.add_patch(rect)

# Plot trades
for trade_num, t in enumerate(trades, 1):
    # Entry point
    ax.plot(t['entry_idx'], t['entry_price'], 'o', color='blue', markersize=8, zorder=5)
    
    # SL line
    ax.plot([t['entry_idx'], t['exit_idx']], [t['sl_price'], t['sl_price']], 
            '--', color='red', linewidth=1, alpha=0.7)
    
    # TP line
    ax.plot([t['entry_idx'], t['exit_idx']], [t['tp_price'], t['tp_price']], 
            '--', color='green', linewidth=1, alpha=0.7)
    
    # Exit point
    exit_color = 'green' if t['exit_reason'] == 'TP' else 'red'
    exit_marker = '^' if t['exit_reason'] == 'TP' else 'v'
    ax.plot(t['exit_idx'], t['tp_price'] if t['exit_reason'] == 'TP' else t['sl_price'], 
            exit_marker, color=exit_color, markersize=10, zorder=5)

ax.set_xlabel('Time (15-min candles)', fontsize=12)
ax.set_ylabel('Price ($)', fontsize=12)
ax.set_title(f'Dec 16, 2025 - PENGU 0.8% Offset Strategy ({len(trades)} trades)', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)

# Legend
legend_elements = [
    mpatches.Patch(color='blue', label='Entry (Limit Fill)'),
    mpatches.Patch(color='green', label='Take Profit'),
    mpatches.Patch(color='red', label='Stop Loss'),
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

plt.tight_layout()
plt.savefig('dec16_trades.png', dpi=150, bbox_inches='tight')
print("\n✅ Chart saved: dec16_trades.png")

# Print trade details
print(f"\nTrade Summary:")
winners = [t for t in trades if t['exit_reason'] == 'TP']
losers = [t for t in trades if t['exit_reason'] == 'SL']
print(f"Winners: {len(winners)}")
print(f"Losers: {len(losers)}")
