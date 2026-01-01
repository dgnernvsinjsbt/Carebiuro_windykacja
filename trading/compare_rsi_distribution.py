#!/usr/bin/env python3
"""
Compare RSI distribution between MELANIA and PENGU
Count how many candle closes with RSI >70, >72, etc.
"""
import pandas as pd
import numpy as np

print("="*100)
print("RSI DISTRIBUTION COMPARISON - MELANIA vs PENGU")
print("="*100)

# Load MELANIA data
melania = pd.read_csv('melania_6months_bingx.csv')
melania['timestamp'] = pd.to_datetime(melania['timestamp'])

# Calculate MELANIA RSI
delta = melania['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
melania['rsi'] = 100 - (100 / (1 + rs))

# Load PENGU data
pengu = pd.read_csv('penguusdt_6months_bingx_15m.csv')
pengu['timestamp'] = pd.to_datetime(pengu['timestamp'])

# Calculate PENGU RSI
delta = pengu['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
pengu['rsi'] = 100 - (100 / (1 + rs))

print(f"\n📊 Dataset Info:")
print(f"   MELANIA: {len(melania)} candles, {melania['timestamp'].min()} to {melania['timestamp'].max()}")
print(f"   PENGU:   {len(pengu)} candles, {pengu['timestamp'].min()} to {pengu['timestamp'].max()}")

# Count RSI levels
rsi_thresholds = [60, 62, 65, 68, 70, 72, 75, 80]

print(f"\n" + "="*100)
print("RSI CANDLE COUNTS (how many closes above each threshold)")
print("="*100)
print()

print(f"{'RSI Threshold':>15} | {'MELANIA Candles':>16} | {'MELANIA %':>12} | {'PENGU Candles':>14} | {'PENGU %':>10}")
print("-" * 100)

for threshold in rsi_thresholds:
    melania_count = (melania['rsi'] > threshold).sum()
    melania_pct = (melania_count / len(melania)) * 100

    pengu_count = (pengu['rsi'] > threshold).sum()
    pengu_pct = (pengu_count / len(pengu)) * 100

    print(f"{'RSI >' + str(threshold):>15} | {melania_count:>16} | {melania_pct:>11.2f}% | {pengu_count:>14} | {pengu_pct:>9.2f}%")

# RSI statistics
print(f"\n" + "="*100)
print("RSI STATISTICS")
print("="*100)
print()

print(f"{'Metric':>20} | {'MELANIA':>15} | {'PENGU':>15}")
print("-" * 60)
print(f"{'Mean RSI':>20} | {melania['rsi'].mean():>15.2f} | {pengu['rsi'].mean():>15.2f}")
print(f"{'Median RSI':>20} | {melania['rsi'].median():>15.2f} | {pengu['rsi'].median():>15.2f}")
print(f"{'Max RSI':>20} | {melania['rsi'].max():>15.2f} | {pengu['rsi'].max():>15.2f}")
print(f"{'Min RSI':>20} | {melania['rsi'].min():>15.2f} | {pengu['rsi'].min():>15.2f}")
print(f"{'Std Dev':>20} | {melania['rsi'].std():>15.2f} | {pengu['rsi'].std():>15.2f}")

# Check consecutive RSI >72 periods (potential signal clusters)
print(f"\n" + "="*100)
print("RSI >72 PERIODS (clusters of consecutive candles)")
print("="*100)
print()

def count_rsi_periods(df, threshold=72):
    """Count how many separate periods of RSI > threshold"""
    above_threshold = df['rsi'] > threshold
    periods = (above_threshold != above_threshold.shift()).cumsum()
    period_groups = df[above_threshold].groupby(periods)

    period_data = []
    for period_id, group in period_groups:
        period_data.append({
            'start': group['timestamp'].min(),
            'end': group['timestamp'].max(),
            'duration_bars': len(group),
            'max_rsi': group['rsi'].max()
        })

    return period_data

melania_periods = count_rsi_periods(melania, 72)
pengu_periods = count_rsi_periods(pengu, 72)

print(f"MELANIA: {len(melania_periods)} separate RSI >72 periods")
print(f"PENGU:   {len(pengu_periods)} separate RSI >72 periods")
print()

# Show first 10 periods for each
print("MELANIA - First 10 RSI >72 periods:")
print(f"{'Start':>20} | {'End':>20} | {'Duration':>10} | {'Max RSI':>10}")
print("-" * 70)
for period in melania_periods[:10]:
    print(f"{str(period['start'])[:19]:>20} | {str(period['end'])[:19]:>20} | {period['duration_bars']:>10} | {period['max_rsi']:>10.2f}")

print()
print("PENGU - First 10 RSI >72 periods:")
print(f"{'Start':>20} | {'End':>20} | {'Duration':>10} | {'Max RSI':>10}")
print("-" * 70)
for period in pengu_periods[:10]:
    print(f"{str(period['start'])[:19]:>20} | {str(period['end'])[:19]:>20} | {period['duration_bars']:>10} | {period['max_rsi']:>10.2f}")

# Average period duration
if melania_periods:
    melania_avg_duration = sum(p['duration_bars'] for p in melania_periods) / len(melania_periods)
else:
    melania_avg_duration = 0

if pengu_periods:
    pengu_avg_duration = sum(p['duration_bars'] for p in pengu_periods) / len(pengu_periods)
else:
    pengu_avg_duration = 0

print(f"\n💡 Analysis:")
print(f"   MELANIA avg period duration: {melania_avg_duration:.1f} bars")
print(f"   PENGU avg period duration:   {pengu_avg_duration:.1f} bars")
print()

print(f"🎯 Expected vs Actual Trades:")
print(f"   MELANIA: {len(melania_periods)} RSI >72 periods → 45 actual trades (1 trade per {len(melania_periods)/45:.1f} periods)")
print(f"   PENGU:   {len(pengu_periods)} RSI >72 periods → 10 actual trades (1 trade per {len(pengu_periods)/10 if len(pengu_periods) > 0 else 0:.1f} periods)")
print()
print("   Note: Not every RSI >72 period generates a trade because:")
print("         1. Need swing low break after RSI trigger")
print("         2. Limit order must fill within 20 bars")
print("         3. SL distance must be <10%")

print("="*100)
