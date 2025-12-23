#!/usr/bin/env python3
"""
Backtest with debug logging for Nov 7
"""
import pandas as pd
import numpy as np

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Filter to Nov-Dec 2025
df = df[(df['timestamp'] >= '2025-11-01') & (df['timestamp'] < '2026-01-01')].reset_index(drop=True)

# Calculate RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# State tracking
armed = False
arm_rsi = None
highest_high = None
divergence_count = 0
looking_for_entry = False

# Focus on Nov 7
nov7_start = pd.Timestamp('2025-11-07 17:00:00')
nov7_end = pd.Timestamp('2025-11-08 01:00:00')

for i in range(20, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']):
        continue

    # Only log Nov 7
    is_nov7 = nov7_start <= row['timestamp'] < nov7_end

    # ARM
    if not armed and not looking_for_entry:
        if row['rsi'] > 80:
            armed = True
            arm_rsi = row['rsi']
            highest_high = row['high']
            divergence_count = 0

            if is_nov7:
                print(f"🔫 ARM: {row['timestamp']} RSI={arm_rsi:.2f} High=${highest_high:.6f}")

    # Divergences
    if armed and divergence_count < 2:
        if row['high'] > highest_high:
            if row['rsi'] < arm_rsi:
                divergence_count += 1

                if is_nov7:
                    print(f"⚡ DIV #{divergence_count}: {row['timestamp']} High=${row['high']:.6f} RSI={row['rsi']:.2f} < {arm_rsi:.2f}")

                highest_high = row['high']

                if divergence_count >= 2:
                    looking_for_entry = True
                    if is_nov7:
                        print(f"   → Looking for entry (2 divs reached)")
            else:
                highest_high = row['high']

    # Entry
    if looking_for_entry:
        is_red = row['close'] < row['open']

        if is_red:
            lookback_start = max(0, i - 24)
            sl_price = df.iloc[lookback_start:i+1]['high'].max()
            sl_dist_pct = ((sl_price - row['close']) / row['close']) * 100

            if is_nov7:
                print(f"🎯 Entry attempt: {row['timestamp']} Close=${row['close']:.6f} SL=${sl_price:.6f} ({sl_dist_pct:.2f}%)")

            if sl_dist_pct > 0 and sl_dist_pct <= 15:
                if is_nov7:
                    print(f"   ✅ ENTERED!")

                # Reset
                armed = False
                looking_for_entry = False
                divergence_count = 0
            else:
                if is_nov7:
                    print(f"   ❌ SL too wide or invalid")
                armed = False
                looking_for_entry = False

print("\nDone")
