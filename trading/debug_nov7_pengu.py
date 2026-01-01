#!/usr/bin/env python3
"""
Debug Nov 7 PENGU - trace the exact setup from screenshot
Focus: Nov 7, 19:00-midnight Warsaw time (18:00-23:00 UTC)
"""
import pandas as pd
import numpy as np

print("="*90)
print("DEBUG: NOV 7 PENGU RSI DIVERGENCE")
print("="*90)

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Filter to Nov 7, 2025 - wider window
start_time = pd.Timestamp('2025-11-07 00:00:00')
end_time = pd.Timestamp('2025-11-08 06:00:00')
df_nov7 = df[(df['timestamp'] >= start_time) & (df['timestamp'] < end_time)].copy().reset_index(drop=True)

print(f"\n📊 Nov 7 Data:")
print(f"   Total candles: {len(df_nov7)}")
print(f"   Time range: {df_nov7['timestamp'].min()} to {df_nov7['timestamp'].max()}")

# Calculate RSI
delta = df_nov7['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

# Need to calculate RSI with more context - use full dataset
delta_full = df['close'].diff()
gain_full = delta_full.clip(lower=0)
loss_full = -delta_full.clip(upper=0)
avg_gain = gain_full.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss_full.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Get Nov 7 with RSI
df_nov7 = df[(df['timestamp'] >= start_time) & (df['timestamp'] < end_time)].copy().reset_index(drop=True)

print(f"\n📈 Price & RSI Summary:")
print(f"   Price range: ${df_nov7['low'].min():.6f} - ${df_nov7['high'].max():.6f}")
print(f"   RSI range: {df_nov7['rsi'].min():.2f} - {df_nov7['rsi'].max():.2f}")
print(f"   Max RSI: {df_nov7['rsi'].max():.2f} at {df_nov7.loc[df_nov7['rsi'].idxmax(), 'timestamp']}")

# Show candles with RSI >75
high_rsi = df_nov7[df_nov7['rsi'] > 75]
print(f"\n🔥 Candles with RSI >75: {len(high_rsi)}")
if len(high_rsi) > 0:
    print(f"   First: {high_rsi.iloc[0]['timestamp']} (RSI {high_rsi.iloc[0]['rsi']:.2f})")
    print(f"   Last:  {high_rsi.iloc[-1]['timestamp']} (RSI {high_rsi.iloc[-1]['rsi']:.2f})")

# Show candles with RSI >80
very_high_rsi = df_nov7[df_nov7['rsi'] > 80]
print(f"\n🔥🔥 Candles with RSI >80: {len(very_high_rsi)}")
if len(very_high_rsi) > 0:
    print(f"   First: {very_high_rsi.iloc[0]['timestamp']} (RSI {very_high_rsi.iloc[0]['rsi']:.2f})")
    print(f"   Last:  {very_high_rsi.iloc[-1]['timestamp']} (RSI {very_high_rsi.iloc[-1]['rsi']:.2f})")

# Focus on 18:00-23:00 UTC (19:00-midnight Warsaw)
focus_start = pd.Timestamp('2025-11-07 18:00:00')
focus_end = pd.Timestamp('2025-11-08 00:00:00')
df_focus = df_nov7[(df_nov7['timestamp'] >= focus_start) & (df_nov7['timestamp'] < focus_end)].copy()

print(f"\n" + "="*90)
print(f"📅 FOCUS PERIOD: Nov 7, 18:00-23:59 UTC (19:00-00:59 Warsaw)")
print("="*90)
print()

print(f"{'Time (UTC)':>20} | {'Open':>10} | {'High':>10} | {'Low':>10} | {'Close':>10} | {'RSI':>7} | {'Color':>5}")
print("-" * 95)

for _, row in df_focus.iterrows():
    color = "🟢" if row['close'] > row['open'] else "🔴"
    print(f"{str(row['timestamp'])[:19]:>20} | ${row['open']:>9.6f} | ${row['high']:>9.6f} | ${row['low']:>9.6f} | ${row['close']:>9.6f} | {row['rsi']:>7.2f} | {color:>5}")

# Find price highs during RSI >75 period
print(f"\n" + "="*90)
print("🔍 DIVERGENCE ANALYSIS")
print("="*90)
print()

rsi_armed_period = df_focus[df_focus['rsi'] > 75]
if len(rsi_armed_period) > 0:
    print(f"RSI >75 period: {rsi_armed_period.iloc[0]['timestamp']} to {rsi_armed_period.iloc[-1]['timestamp']}")
    print(f"Duration: {len(rsi_armed_period)} candles")
    print()

    # Find local highs (peaks) in this period
    print("Price highs during RSI >75:")
    print(f"{'Time':>20} | {'Price High':>12} | {'RSI at High':>12}")
    print("-" * 50)

    peaks = []
    for i in range(len(rsi_armed_period)):
        if i == 0 or i == len(rsi_armed_period) - 1:
            continue

        curr = rsi_armed_period.iloc[i]
        prev = rsi_armed_period.iloc[i-1]
        next_row = rsi_armed_period.iloc[i+1]

        # Peak if higher than both neighbors
        if curr['high'] > prev['high'] and curr['high'] > next_row['high']:
            peaks.append({
                'time': curr['timestamp'],
                'price': curr['high'],
                'rsi': curr['rsi']
            })
            print(f"{str(curr['timestamp'])[:19]:>20} | ${curr['high']:>11.6f} | {curr['rsi']:>12.2f}")

    # Check for divergences
    print(f"\n🎯 Checking for divergences (higher price, lower RSI):")
    if len(peaks) >= 2:
        for i in range(1, len(peaks)):
            prev_peak = peaks[i-1]
            curr_peak = peaks[i]

            price_higher = curr_peak['price'] > prev_peak['price']
            rsi_lower = curr_peak['rsi'] < prev_peak['rsi']

            divergence = "✅ DIVERGENCE!" if (price_higher and rsi_lower) else "❌ No divergence"

            print(f"\n   Peak {i-1} → Peak {i}:")
            print(f"      Price: ${prev_peak['price']:.6f} → ${curr_peak['price']:.6f} ({'+' if price_higher else '-'})")
            print(f"      RSI:   {prev_peak['rsi']:.2f} → {curr_peak['rsi']:.2f} ({'-' if rsi_lower else '+'})")
            print(f"      {divergence}")

        # Count total divergences
        divergence_count = sum(1 for i in range(1, len(peaks))
                              if peaks[i]['price'] > peaks[i-1]['price']
                              and peaks[i]['rsi'] < peaks[i-1]['rsi'])

        print(f"\n   Total divergences found: {divergence_count}")

    else:
        print("   Not enough peaks to check divergences")

else:
    print("❌ No RSI >75 period found in focus window")

print("="*90)
