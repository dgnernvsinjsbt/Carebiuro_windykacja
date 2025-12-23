#!/usr/bin/env python3
"""
Show exact fill candles and details for Dec 16
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

# Dec 16
df_dec16 = df[df['timestamp'].dt.date == pd.to_datetime('2025-12-16').date()].copy().reset_index(drop=True)

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
        if row['low'] <= pending_limit:
            sl_dist_pct = ((pending_sl - pending_limit) / pending_limit) * 100
            
            if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                # Find exit
                exit_idx = None
                exit_reason = None
                
                for k in range(i + 1, min(i + 100, len(df_dec16))):
                    exit_row = df_dec16.iloc[k]
                    
                    if exit_row['high'] >= pending_sl:
                        exit_idx = k
                        exit_reason = 'SL'
                        break
                    elif exit_row['low'] <= pending_tp:
                        exit_idx = k
                        exit_reason = 'TP'
                        break
                
                if exit_idx:
                    trades.append({
                        'entry_candle': i,
                        'entry_time': row['timestamp'],
                        'entry_price': pending_limit,
                        'sl_price': pending_sl,
                        'tp_price': pending_tp,
                        'exit_candle': exit_idx,
                        'exit_time': df_dec16.iloc[exit_idx]['timestamp'],
                        'exit_reason': exit_reason
                    })
            
            has_pending = False
        
        elif row['high'] >= pending_sl:
            has_pending = False
        
        elif i - pending_signal_bar >= 16:
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

# Print details
print("="*120)
print("DEC 16 TRADE DETAILS")
print("="*120)
print()

for idx, t in enumerate(trades, 1):
    entry_candle = df_dec16.iloc[t['entry_candle']]
    exit_candle = df_dec16.iloc[t['exit_candle']]
    
    print(f"TRADE #{idx}")
    print(f"{'='*120}")
    print(f"Entry Candle: #{t['entry_candle']} | Time: {t['entry_time'].strftime('%Y-%m-%d %H:%M')}")
    print(f"  Candle: O=${entry_candle['open']:.6f} H=${entry_candle['high']:.6f} L=${entry_candle['low']:.6f} C=${entry_candle['close']:.6f}")
    print(f"  Entry Price: ${t['entry_price']:.6f}")
    print(f"  SL: ${t['sl_price']:.6f} | TP: ${t['tp_price']:.6f}")
    print()
    print(f"Exit Candle: #{t['exit_candle']} | Time: {t['exit_time'].strftime('%Y-%m-%d %H:%M')}")
    print(f"  Candle: O=${exit_candle['open']:.6f} H=${exit_candle['high']:.6f} L=${exit_candle['low']:.6f} C=${exit_candle['close']:.6f}")
    print(f"  Result: {t['exit_reason']}")
    print(f"  Bars held: {t['exit_candle'] - t['entry_candle']} ({(t['exit_candle'] - t['entry_candle']) * 15} minutes)")
    print()

# Create clearer chart
fig, ax = plt.subplots(figsize=(24, 12))

# Plot candlesticks
for idx, row in df_dec16.iterrows():
    color = 'green' if row['close'] >= row['open'] else 'red'
    
    ax.plot([idx, idx], [row['low'], row['high']], color='black', linewidth=0.5)
    body_height = abs(row['close'] - row['open'])
    body_bottom = min(row['open'], row['close'])
    rect = mpatches.Rectangle((idx - 0.3, body_bottom), 0.6, body_height, 
                               facecolor=color, edgecolor='black', linewidth=0.5, alpha=0.7)
    ax.add_patch(rect)

# Plot trades with labels
for idx, t in enumerate(trades, 1):
    # Entry
    ax.plot(t['entry_candle'], t['entry_price'], 'o', color='blue', markersize=12, zorder=5)
    ax.text(t['entry_candle'], t['entry_price'], f"  #{idx} ENTRY\n  Candle {t['entry_candle']}", 
            fontsize=9, fontweight='bold', color='blue', verticalalignment='bottom')
    
    # SL line
    ax.plot([t['entry_candle'], t['exit_candle']], [t['sl_price'], t['sl_price']], 
            '--', color='red', linewidth=2, alpha=0.7)
    
    # TP line  
    ax.plot([t['entry_candle'], t['exit_candle']], [t['tp_price'], t['tp_price']], 
            '--', color='green', linewidth=2, alpha=0.7)
    
    # Exit
    exit_color = 'green' if t['exit_reason'] == 'TP' else 'red'
    exit_marker = '^' if t['exit_reason'] == 'TP' else 'v'
    exit_price = t['tp_price'] if t['exit_reason'] == 'TP' else t['sl_price']
    ax.plot(t['exit_candle'], exit_price, exit_marker, color=exit_color, markersize=14, zorder=5)
    ax.text(t['exit_candle'], exit_price, f"  EXIT {t['exit_reason']}\n  Candle {t['exit_candle']}", 
            fontsize=9, fontweight='bold', color=exit_color, verticalalignment='top')

ax.set_xlabel('Candle Number (15-min intervals)', fontsize=12)
ax.set_ylabel('Price ($)', fontsize=12)
ax.set_title(f'Dec 16, 2025 - All 4 Trades with Candle Numbers', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)

legend_elements = [
    mpatches.Patch(color='blue', label='Entry (Limit Fill)'),
    mpatches.Patch(color='green', label='Take Profit Line'),
    mpatches.Patch(color='red', label='Stop Loss Line'),
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=11)

plt.tight_layout()
plt.savefig('dec16_detailed.png', dpi=150, bbox_inches='tight')
print("✅ Detailed chart saved: dec16_detailed.png")
