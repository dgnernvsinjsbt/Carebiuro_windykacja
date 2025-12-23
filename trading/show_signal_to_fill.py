#!/usr/bin/env python3
"""
Show SIGNAL → LIMIT → FILL flow for Dec 16
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
                        'signal_candle': pending_signal_bar,
                        'signal_time': df_dec16.iloc[pending_signal_bar]['timestamp'],
                        'signal_price': df_dec16.iloc[pending_signal_bar]['close'],
                        'limit_price': pending_limit,
                        'fill_candle': i,
                        'fill_time': row['timestamp'],
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
print("="*140)
print("SIGNAL → LIMIT → FILL FLOW - DEC 16")
print("="*140)
print()

for idx, t in enumerate(trades, 1):
    signal_candle = df_dec16.iloc[t['signal_candle']]
    fill_candle = df_dec16.iloc[t['fill_candle']]
    exit_candle = df_dec16.iloc[t['exit_candle']]

    print(f"TRADE #{idx}")
    print(f"{'='*140}")
    print(f"1️⃣  SIGNAL at Candle #{t['signal_candle']} | {t['signal_time'].strftime('%H:%M')}")
    print(f"    Price: ${t['signal_price']:.6f} | Breakdown detected (-2.5% from 8h high)")
    print()
    print(f"2️⃣  LIMIT ORDER placed at ${t['limit_price']:.6f} (0.8% above signal)")
    print(f"    SL: ${t['sl_price']:.6f} | TP: ${t['tp_price']:.6f}")
    print()
    print(f"3️⃣  FILLED at Candle #{t['fill_candle']} | {t['fill_time'].strftime('%H:%M')}")
    print(f"    Candle Low: ${fill_candle['low']:.6f} touched limit ${t['limit_price']:.6f}")
    print(f"    Waited: {t['fill_candle'] - t['signal_candle']} bars ({(t['fill_candle'] - t['signal_candle']) * 15} min)")
    print()
    print(f"4️⃣  EXIT at Candle #{t['exit_candle']} | {t['exit_time'].strftime('%H:%M')} | {t['exit_reason']}")
    print(f"    Held: {t['exit_candle'] - t['fill_candle']} bars ({(t['exit_candle'] - t['fill_candle']) * 15} min)")
    print()

# Create detailed chart
fig, ax = plt.subplots(figsize=(28, 14))

# Plot candlesticks
for idx, row in df_dec16.iterrows():
    color = 'green' if row['close'] >= row['open'] else 'red'

    ax.plot([idx, idx], [row['low'], row['high']], color='black', linewidth=0.5)
    body_height = abs(row['close'] - row['open'])
    body_bottom = min(row['open'], row['close'])
    rect = mpatches.Rectangle((idx - 0.3, body_bottom), 0.6, body_height,
                               facecolor=color, edgecolor='black', linewidth=0.5, alpha=0.7)
    ax.add_patch(rect)

# Plot each trade's flow
colors = ['blue', 'purple', 'orange', 'brown']
for idx, t in enumerate(trades):
    color = colors[idx % len(colors)]

    # 1. Signal candle (star)
    ax.plot(t['signal_candle'], t['signal_price'], '*', color=color, markersize=18, zorder=5,
            markeredgecolor='black', markeredgewidth=1)
    ax.text(t['signal_candle'], t['signal_price'], f"  #{idx+1} SIGNAL\n  C{t['signal_candle']}",
            fontsize=8, fontweight='bold', color=color, verticalalignment='top')

    # 2. Limit order line (horizontal dashed)
    ax.plot([t['signal_candle'], t['fill_candle']], [t['limit_price'], t['limit_price']],
            ':', color=color, linewidth=3, alpha=0.8, label=f"Trade {idx+1} Limit")
    ax.text((t['signal_candle'] + t['fill_candle']) / 2, t['limit_price'],
            f"  LIMIT ${t['limit_price']:.6f}", fontsize=7, color=color,
            verticalalignment='bottom', fontweight='bold')

    # 3. Fill candle (circle)
    ax.plot(t['fill_candle'], t['limit_price'], 'o', color=color, markersize=14, zorder=5,
            markeredgecolor='black', markeredgewidth=2)
    ax.text(t['fill_candle'], t['limit_price'], f"  FILLED\n  C{t['fill_candle']}",
            fontsize=8, fontweight='bold', color=color, verticalalignment='bottom')

    # 4. SL/TP lines after fill
    ax.plot([t['fill_candle'], t['exit_candle']], [t['sl_price'], t['sl_price']],
            '--', color='red', linewidth=1.5, alpha=0.6)
    ax.plot([t['fill_candle'], t['exit_candle']], [t['tp_price'], t['tp_price']],
            '--', color='green', linewidth=1.5, alpha=0.6)

    # 5. Exit
    exit_color = 'green' if t['exit_reason'] == 'TP' else 'red'
    exit_marker = '^' if t['exit_reason'] == 'TP' else 'v'
    exit_price = t['tp_price'] if t['exit_reason'] == 'TP' else t['sl_price']
    ax.plot(t['exit_candle'], exit_price, exit_marker, color=exit_color, markersize=16, zorder=5,
            markeredgecolor='black', markeredgewidth=2)
    ax.text(t['exit_candle'], exit_price, f"  {t['exit_reason']}\n  C{t['exit_candle']}",
            fontsize=8, fontweight='bold', color=exit_color, verticalalignment='top')

ax.set_xlabel('Candle Number (15-min intervals)', fontsize=13, fontweight='bold')
ax.set_ylabel('Price ($)', fontsize=13, fontweight='bold')
ax.set_title('Dec 16 - SIGNAL → LIMIT → FILL Flow (All 4 Trades)', fontsize=16, fontweight='bold')
ax.grid(True, alpha=0.3, linestyle='--')

legend_elements = [
    mpatches.Patch(color='blue', label='⭐ Signal (Breakdown -2.5%)'),
    mpatches.Patch(color='blue', label='⭕ Fill (Limit touched)'),
    mpatches.Patch(color='red', label='▼ Stop Loss Hit'),
    mpatches.Patch(color='green', label='▲ Take Profit Hit'),
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=11, framealpha=0.95)

plt.tight_layout()
plt.savefig('signal_to_fill_flow.png', dpi=200, bbox_inches='tight')
print("="*140)
print("✅ Chart saved: signal_to_fill_flow.png")
print("="*140)
