#!/usr/bin/env python3
"""
Debug ALL armed periods on Nov 7
Show every ARM, divergence, and entry attempt
"""
import pandas as pd
import numpy as np

print("="*120)
print("NOV 7 - ALL ARMED PERIODS TRACE")
print("="*120)

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Filter to Nov 6-8 (wider window to catch any earlier arms)
df_nov7 = df[(df['timestamp'] >= '2025-11-06 12:00:00') &
             (df['timestamp'] < '2025-11-08 06:00:00')].copy().reset_index(drop=True)

# Add global index for reference
df_nov7['global_idx'] = df_nov7.index + df[df['timestamp'] < '2025-11-07 00:00:00'].index.max() + 1

# Convert to Warsaw
df_nov7['warsaw_time'] = df_nov7['timestamp'] + pd.Timedelta(hours=1)

# State tracking
armed = False
arm_rsi = None
arm_time = None
arm_idx = None
highest_high = None
divergence_count = 0
looking_for_entry = False

armed_periods = []
current_arm_data = None

for idx, row in df_nov7.iterrows():
    # Check for ARM
    if not armed and not looking_for_entry and row['rsi'] > 80:
        armed = True
        arm_rsi = row['rsi']
        arm_time = row['warsaw_time']
        arm_idx = idx
        highest_high = row['high']
        divergence_count = 0

        current_arm_data = {
            'arm_time': row['warsaw_time'],
            'arm_rsi': arm_rsi,
            'arm_high': highest_high,
            'divergences': [],
            'entry_time': None,
            'entry_price': None,
            'entry_sl': None,
            'reason_ended': None
        }

    # Track divergences
    if armed and divergence_count < 2:
        if row['high'] > highest_high:
            if row['rsi'] < arm_rsi:
                divergence_count += 1
                current_arm_data['divergences'].append({
                    'num': divergence_count,
                    'time': row['warsaw_time'],
                    'high': row['high'],
                    'rsi': row['rsi']
                })
                highest_high = row['high']

                if divergence_count >= 2:
                    looking_for_entry = True
            else:
                highest_high = row['high']

    # Check for entry
    if looking_for_entry and not current_arm_data['entry_time']:
        is_red = row['close'] < row['open']
        if is_red:
            # Calculate 6h SL
            lookback_start = max(0, idx - 24)
            sl_6h = df_nov7.iloc[lookback_start:idx+1]['high'].max()
            sl_dist = ((sl_6h - row['close']) / row['close']) * 100

            if sl_dist > 0 and sl_dist <= 15:
                current_arm_data['entry_time'] = row['warsaw_time']
                current_arm_data['entry_price'] = row['close']
                current_arm_data['entry_sl'] = sl_6h
                current_arm_data['reason_ended'] = 'ENTERED'
                armed_periods.append(current_arm_data)

                # Reset
                armed = False
                looking_for_entry = False
                current_arm_data = None
            else:
                current_arm_data['reason_ended'] = f'SL too wide ({sl_dist:.2f}%)'
                armed_periods.append(current_arm_data)
                armed = False
                looking_for_entry = False
                current_arm_data = None

# Print results
print(f"\nFound {len(armed_periods)} armed period(s) on Nov 7\n")

for i, arm in enumerate(armed_periods, 1):
    print(f"="*120)
    print(f"ARMED PERIOD #{i}")
    print(f"="*120)
    print(f"ARM Time:  {arm['arm_time']} (Warsaw)")
    print(f"ARM RSI:   {arm['arm_rsi']:.2f}")
    print(f"ARM High:  ${arm['arm_high']:.6f}")
    print()

    print(f"Divergences: {len(arm['divergences'])}")
    for div in arm['divergences']:
        print(f"  Div #{div['num']}: {div['time']} - High ${div['high']:.6f}, RSI {div['rsi']:.2f}")
    print()

    if arm['entry_time']:
        print(f"✅ ENTRY:")
        print(f"  Time:  {arm['entry_time']} (Warsaw)")
        print(f"  Price: ${arm['entry_price']:.6f}")
        print(f"  SL:    ${arm['entry_sl']:.6f}")
        print(f"  SL %:  {((arm['entry_sl'] - arm['entry_price']) / arm['entry_price'] * 100):.2f}%")
    else:
        print(f"❌ NO ENTRY: {arm['reason_ended']}")

    print()

print("="*120)
