#!/usr/bin/env python3
"""
Dec 16 with CORRECT fill detection (HIGH >= limit)
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

is_busy = False
pending_limit_price = None
pending_signal_bar = None
pending_sl_price = None
pending_tp_price = None

i = 32
while i < len(df_dec16):
    row = df_dec16.iloc[i]

    if pd.isna(row['atr']):
        i += 1
        continue

    # If pending limit
    if is_busy and pending_limit_price is not None:
        bars_waiting = i - pending_signal_bar

        # CORRECT: Check if HIGH reached limit (price bounced up)
        if row['high'] >= pending_limit_price:
            entry_price = pending_limit_price
            sl_dist_pct = ((pending_sl_price - entry_price) / entry_price) * 100

            if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                # Find exit
                exit_idx = None
                exit_reason = None

                for k in range(i + 1, min(i + 100, len(df_dec16))):
                    exit_row = df_dec16.iloc[k]

                    if exit_row['high'] >= pending_sl_price:
                        exit_idx = k
                        exit_reason = 'SL'
                        break
                    elif exit_row['low'] <= pending_tp_price:
                        exit_idx = k
                        exit_reason = 'TP'
                        break

                if exit_idx:
                    trades.append({
                        'signal_candle': pending_signal_bar,
                        'signal_time': df_dec16.iloc[pending_signal_bar]['timestamp'],
                        'limit_price': pending_limit_price,
                        'fill_candle': i,
                        'fill_time': row['timestamp'],
                        'fill_high': row['high'],
                        'sl_price': pending_sl_price,
                        'tp_price': pending_tp_price,
                        'exit_candle': exit_idx,
                        'exit_time': df_dec16.iloc[exit_idx]['timestamp'],
                        'exit_reason': exit_reason
                    })

                    # JUMP to exit (position occupied)
                    i = exit_idx

            is_busy = False
            pending_limit_price = None

        elif row['high'] >= pending_sl_price:
            is_busy = False
            pending_limit_price = None

        elif bars_waiting >= 16:
            is_busy = False
            pending_limit_price = None

        i += 1
        continue

    # Check for new signal (only if NOT busy)
    if not is_busy:
        high_8h = df_dec16.iloc[max(0, i-32):i]['high'].max()
        dist_pct = ((row['close'] - high_8h) / high_8h) * 100

        if dist_pct <= -2.5:
            signal_price = row['close']
            sl_price = high_8h
            tp_price = signal_price * (1 - 0.05)
            limit_price = signal_price * (1 + offset_pct / 100)

            if limit_price < sl_price:
                is_busy = True
                pending_limit_price = limit_price
                pending_signal_bar = i
                pending_sl_price = sl_price
                pending_tp_price = tp_price

    i += 1

# Print
print("="*140)
print(f"DEC 16 - CORRECT FILLS (HIGH >= limit) - {len(trades)} trades")
print("="*140)
print()

for idx, t in enumerate(trades, 1):
    signal_candle = df_dec16.iloc[t['signal_candle']]
    fill_candle = df_dec16.iloc[t['fill_candle']]

    wait_bars = t['fill_candle'] - t['signal_candle']

    print(f"TRADE #{idx}")
    print("-" * 140)
    print(f"Signal: C{t['signal_candle']} ({t['signal_time'].strftime('%H:%M')}) @ ${signal_candle['close']:.6f}")
    print(f"Limit:  ${t['limit_price']:.6f} (0.8% above signal)")
    print(f"Filled: C{t['fill_candle']} ({t['fill_time'].strftime('%H:%M')}) - waited {wait_bars} bars ({wait_bars * 15} min)")
    print(f"  Candle HIGH: ${t['fill_high']:.6f} >= Limit ${t['limit_price']:.6f} ✅")
    print(f"Exit:   C{t['exit_candle']} ({t['exit_time'].strftime('%H:%M')}) - {t['exit_reason']}")
    print()

# Chart
fig, ax = plt.subplots(figsize=(26, 12))

# Candlesticks
for idx, row in df_dec16.iterrows():
    color = 'green' if row['close'] >= row['open'] else 'red'
    ax.plot([idx, idx], [row['low'], row['high']], color='black', linewidth=0.5)
    body_height = abs(row['close'] - row['open'])
    body_bottom = min(row['open'], row['close'])
    rect = mpatches.Rectangle((idx - 0.3, body_bottom), 0.6, body_height,
                               facecolor=color, edgecolor='black', linewidth=0.5, alpha=0.7)
    ax.add_patch(rect)

# Trades
for idx, t in enumerate(trades, 1):
    # Signal (star)
    signal_price = df_dec16.iloc[t['signal_candle']]['close']
    ax.plot(t['signal_candle'], signal_price, '*', color='blue', markersize=16, zorder=5)
    ax.text(t['signal_candle'], signal_price, f"  SIGNAL #{idx}\n  C{t['signal_candle']}",
            fontsize=8, color='blue', fontweight='bold', verticalalignment='bottom')

    # Limit line (from signal to fill)
    ax.plot([t['signal_candle'], t['fill_candle']], [t['limit_price'], t['limit_price']],
            ':', color='purple', linewidth=3, alpha=0.7)
    ax.text((t['signal_candle'] + t['fill_candle']) / 2, t['limit_price'],
            f"  Limit ${t['limit_price']:.6f}", fontsize=7, color='purple', fontweight='bold',
            verticalalignment='bottom')

    # Fill (circle at candle HIGH)
    ax.plot(t['fill_candle'], t['fill_high'], 'o', color='orange', markersize=14, zorder=6,
            markeredgecolor='black', markeredgewidth=2)
    ax.text(t['fill_candle'], t['fill_high'], f"  FILLED\n  C{t['fill_candle']}",
            fontsize=8, color='orange', fontweight='bold', verticalalignment='bottom')

    # SL/TP
    ax.plot([t['fill_candle'], t['exit_candle']], [t['sl_price'], t['sl_price']],
            '--', color='red', linewidth=2, alpha=0.6)
    ax.plot([t['fill_candle'], t['exit_candle']], [t['tp_price'], t['tp_price']],
            '--', color='green', linewidth=2, alpha=0.6)

    # Exit
    exit_color = 'green' if t['exit_reason'] == 'TP' else 'red'
    exit_marker = '^' if t['exit_reason'] == 'TP' else 'v'
    exit_price = t['tp_price'] if t['exit_reason'] == 'TP' else t['sl_price']
    ax.plot(t['exit_candle'], exit_price, exit_marker, color=exit_color, markersize=14, zorder=5)
    ax.text(t['exit_candle'], exit_price, f"  {t['exit_reason']}\n  C{t['exit_candle']}",
            fontsize=8, color=exit_color, fontweight='bold', verticalalignment='top')

ax.set_xlabel('Candle Number', fontsize=12, fontweight='bold')
ax.set_ylabel('Price ($)', fontsize=12, fontweight='bold')
ax.set_title(f'Dec 16 - CORRECT Fills (HIGH >= limit) - {len(trades)} trades', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('dec16_correct_fills.png', dpi=200, bbox_inches='tight')
print("✅ Chart saved: dec16_correct_fills.png")
print("="*140)
