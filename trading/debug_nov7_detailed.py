#!/usr/bin/env python3
"""
Debug Nov 7 with detailed divergence tracking
Show all events in Warsaw time
"""
import pandas as pd
import numpy as np

print("="*100)
print("NOV 7 DETAILED DIVERGENCE TRACE (WARSAW TIME)")
print("="*100)

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate RSI with full context
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Filter to Nov 7-8
df_nov7 = df[(df['timestamp'] >= '2025-11-07 17:00:00') &
             (df['timestamp'] < '2025-11-08 01:00:00')].copy().reset_index(drop=True)

# Convert to Warsaw time for display (UTC+1)
df_nov7['warsaw_time'] = df_nov7['timestamp'] + pd.Timedelta(hours=1)

print(f"\n📅 Showing Nov 7, 18:00-00:00 Warsaw time")
print()

# State tracking (matching the strategy logic)
armed = False
arm_rsi = None
arm_time = None
highest_high = None
highest_high_time = None
divergence_count = 0
divergences = []

print(f"{'Warsaw Time':>18} | {'UTC Time':>18} | {'High':>10} | {'Close':>10} | {'RSI':>6} | {'Event':<50}")
print("-" * 130)

for idx, row in df_nov7.iterrows():
    events = []

    # Check for ARM
    if not armed and row['rsi'] > 80:
        armed = True
        arm_rsi = row['rsi']
        arm_time = row['warsaw_time']
        highest_high = row['high']
        highest_high_time = row['warsaw_time']
        divergence_count = 0
        events.append(f"🔫 ARM! RSI={arm_rsi:.2f}, Track High=${highest_high:.6f}")

    # Check for divergence (if armed)
    if armed and divergence_count < 2:
        if row['high'] > highest_high:
            # New high!
            if row['rsi'] < arm_rsi:
                # Divergence!
                divergence_count += 1
                divergences.append({
                    'num': divergence_count,
                    'time': row['warsaw_time'],
                    'high': row['high'],
                    'rsi': row['rsi'],
                    'prev_high': highest_high,
                    'arm_rsi': arm_rsi
                })
                events.append(f"⚡ DIVERGENCE #{divergence_count}! High=${row['high']:.6f} RSI={row['rsi']:.2f} < ARM RSI={arm_rsi:.2f}")

                # Update highest high
                highest_high = row['high']
                highest_high_time = row['warsaw_time']
            else:
                events.append(f"📈 New high ${row['high']:.6f} but RSI={row['rsi']:.2f} NOT lower than ARM={arm_rsi:.2f}")
                highest_high = row['high']
                highest_high_time = row['warsaw_time']

    # Check for entry (after 2 divergences)
    if armed and divergence_count >= 2:
        is_red = row['close'] < row['open']
        if is_red:
            # Calculate SL as highest high in last 6 hours (24 bars)
            lookback_start = max(0, idx - 24)
            sl_from_6h = df_nov7.iloc[lookback_start:idx+1]['high'].max()
            events.append(f"🎯 ENTRY SIGNAL! Red candle close=${row['close']:.6f}, SL (6h high)=${sl_from_6h:.6f}")

    # Print row
    event_str = " | ".join(events) if events else ""
    color = "🔴" if row['close'] < row['open'] else "🟢"

    print(f"{str(row['warsaw_time'])[:19]:>18} | {str(row['timestamp'])[:19]:>18} | ${row['high']:>9.6f} | ${row['close']:>9.6f} | {row['rsi']:>6.2f} | {color} {event_str}")

# Summary
print()
print("="*100)
print("📊 DIVERGENCE SUMMARY")
print("="*100)
print()

if armed:
    print(f"ARM Time: {arm_time} (Warsaw)")
    print(f"ARM RSI: {arm_rsi:.2f}")
    print(f"Initial High: ${highest_high:.6f}")
    print()

if len(divergences) > 0:
    print(f"Divergences Found: {len(divergences)}")
    print()
    for div in divergences:
        print(f"  Divergence #{div['num']}:")
        print(f"    Time: {div['time']} (Warsaw)")
        print(f"    New High: ${div['high']:.6f}")
        print(f"    RSI: {div['rsi']:.2f} (vs ARM RSI {div['arm_rsi']:.2f})")
        print(f"    Previous High: ${div['prev_high']:.6f}")
        print()

print("="*100)
