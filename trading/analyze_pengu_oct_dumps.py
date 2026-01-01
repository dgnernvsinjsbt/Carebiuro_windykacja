#!/usr/bin/env python3
"""
Analyze PENGU Oct 5-10 period to find dump patterns
"""
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

# Price changes
df['ret_1h'] = ((df['close'] - df['close'].shift(4)) / df['close'].shift(4)) * 100
df['ret_2h'] = ((df['close'] - df['close'].shift(8)) / df['close'].shift(8)) * 100
df['ret_4h'] = ((df['close'] - df['close'].shift(16)) / df['close'].shift(16)) * 100

# Future returns (to identify dumps)
df['fwd_1h'] = ((df['close'].shift(-4) - df['close']) / df['close']) * 100
df['fwd_2h'] = ((df['close'].shift(-8) - df['close']) / df['close']) * 100
df['fwd_4h'] = ((df['close'].shift(-16) - df['close']) / df['close']) * 100
df['fwd_6h'] = ((df['close'].shift(-24) - df['close']) / df['close']) * 100

# Filter to Oct 5-10
df_oct = df[(df['timestamp'] >= '2025-10-05') & (df['timestamp'] < '2025-10-11')].copy()

print("="*120)
print("PENGU OCTOBER 5-10 ANALYSIS - FINDING DUMP PATTERNS")
print("="*120)
print(f"\nPeriod: {df_oct['timestamp'].min()} to {df_oct['timestamp'].max()}")
print(f"Total candles: {len(df_oct)}")
print()

# Find big dumps (>5% drop in next 4-6 hours)
df_oct['big_dump'] = df_oct['fwd_6h'] < -5.0

dumps = df_oct[df_oct['big_dump']].copy()

print(f"🔍 Found {len(dumps)} candles followed by >5% dump within 6 hours")
print()

if len(dumps) > 0:
    print("="*120)
    print("DUMP EVENTS:")
    print("="*120)
    print()

    for idx, row in dumps.iterrows():
        print(f"📍 DUMP START: {row['timestamp']}")
        print(f"   Price: ${row['close']:.6f}")
        print(f"   RSI: {row['rsi']:.2f}")
        print(f"   ATR: {row['atr_pct']:.2f}%")
        print(f"   Recent gains: 1h={row['ret_1h']:.2f}%, 2h={row['ret_2h']:.2f}%, 4h={row['ret_4h']:.2f}%")
        print(f"   Future dump: 1h={row['fwd_1h']:.2f}%, 2h={row['fwd_2h']:.2f}%, 4h={row['fwd_4h']:.2f}%, 6h={row['fwd_6h']:.2f}%")
        print()

    print("="*120)
    print("STATISTICS OF DUMP SIGNALS:")
    print("="*120)
    print()

    print(f"RSI at dump start:")
    print(f"   Mean: {dumps['rsi'].mean():.2f}")
    print(f"   Min: {dumps['rsi'].min():.2f}")
    print(f"   Max: {dumps['rsi'].max():.2f}")
    print()

    print(f"Recent price action before dump:")
    print(f"   1h return mean: {dumps['ret_1h'].mean():.2f}%")
    print(f"   2h return mean: {dumps['ret_2h'].mean():.2f}%")
    print(f"   4h return mean: {dumps['ret_4h'].mean():.2f}%")
    print()

    print(f"ATR at dump start:")
    print(f"   Mean: {dumps['atr_pct'].mean():.2f}%")
    print(f"   Min: {dumps['atr_pct'].min():.2f}%")
    print(f"   Max: {dumps['atr_pct'].max():.2f}%")
    print()

    # Check if preceded by rally
    rallied_before = dumps[dumps['ret_4h'] > 3.0]
    print(f"Dumps preceded by >3% rally in 4h: {len(rallied_before)} / {len(dumps)} ({len(rallied_before)/len(dumps)*100:.1f}%)")
    print()

# Now let's look at the entire Oct 5-10 period visually
print("="*120)
print("FULL OCT 5-10 PRICE ACTION (Every 4 hours):")
print("="*120)
print()

df_oct_4h = df_oct.iloc[::4].copy()  # Every 4 hours

print(f"{'Time':>20} | {'Price':>10} | {'RSI':>6} | {'1h%':>7} | {'2h%':>7} | {'4h%':>7} | {'Fwd 6h%':>9}")
print("-"*120)

for _, row in df_oct_4h.iterrows():
    marker = "🔴" if row['fwd_6h'] < -5 else ("🟡" if row['fwd_6h'] < -3 else "")
    print(f"{str(row['timestamp'])[:19]:>20} | ${row['close']:>9.6f} | {row['rsi']:>6.2f} | {row['ret_1h']:>6.2f}% | {row['ret_2h']:>6.2f}% | {row['ret_4h']:>6.2f}% | {row['fwd_6h']:>8.2f}% {marker}")

print("="*120)
print("\n🔴 = >5% dump ahead")
print("🟡 = >3% dump ahead")
