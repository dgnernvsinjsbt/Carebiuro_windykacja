#!/usr/bin/env python3
"""
Brainstorm: Analyze October dumps to find patterns
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
df['rsi'] = 50.0  # Placeholder, will calculate properly

# RSI (Wilder's method)
delta = df['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)

# First values
avg_gain = gain.rolling(window=14, min_periods=14).mean()
avg_loss = loss.rolling(window=14, min_periods=14).mean()

# Wilder's smoothing
for i in range(14, len(df)):
    avg_gain.iloc[i] = (avg_gain.iloc[i-1] * 13 + gain.iloc[i]) / 14
    avg_loss.iloc[i] = (avg_loss.iloc[i-1] * 13 + loss.iloc[i]) / 14

rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

# Volume (body size as proxy since we don't have real volume)
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

# Price changes
df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100
df['fwd_4h'] = ((df['close'].shift(-16) - df['close']) / df['close']) * 100
df['fwd_6h'] = ((df['close'].shift(-24) - df['close']) / df['close']) * 100

# Volatility
df['atr_pct'] = (df['atr'] / df['close']) * 100

# October only
df_oct = df[(df['timestamp'] >= '2025-10-01') & (df['timestamp'] < '2025-11-01')].copy()

print("="*140)
print("BRAINSTORMING: OCTOBER DUMP ANALYSIS")
print("="*140)
print()

# Find all dumps >5% in next 4-6 hours
df_oct['big_dump'] = df_oct['fwd_6h'] < -5.0
dumps = df_oct[df_oct['big_dump']].copy()

print(f"Found {len(dumps)} candles before >5% dumps in October")
print()

if len(dumps) > 0:
    print("ANALYZING CHARACTERISTICS BEFORE DUMPS:")
    print("-"*140)
    print()

    # RSI analysis
    print("1. RSI LEVELS:")
    rsi_bins = [0, 30, 40, 50, 60, 70, 80, 100]
    rsi_labels = ['<30', '30-40', '40-50', '50-60', '60-70', '70-80', '>80']
    rsi_dist = pd.cut(dumps['rsi'], bins=rsi_bins, labels=rsi_labels).value_counts().sort_index()
    print(rsi_dist)
    print(f"   Avg RSI before dump: {dumps['rsi'].mean():.1f}")
    print()

    # Price action
    print("2. PRICE ACTION:")
    print(f"   Avg body size: {dumps['body_pct'].mean():.2f}%")
    print(f"   Red candles: {len(dumps[dumps['change_pct'] < 0])} ({len(dumps[dumps['change_pct'] < 0])/len(dumps)*100:.1f}%)")
    print(f"   Green candles: {len(dumps[dumps['change_pct'] > 0])} ({len(dumps[dumps['change_pct'] > 0])/len(dumps)*100:.1f}%)")
    print()

    # ATR / Volatility
    print("3. VOLATILITY (ATR %):")
    print(f"   Avg ATR: {dumps['atr_pct'].mean():.2f}%")
    print(f"   Min ATR: {dumps['atr_pct'].min():.2f}%")
    print(f"   Max ATR: {dumps['atr_pct'].max():.2f}%")
    print()

    # Recent price action (looking back)
    dumps['prev_4h_change'] = ((dumps['close'] - dumps['close'].shift(16)) / dumps['close'].shift(16)) * 100
    dumps['prev_1h_change'] = ((dumps['close'] - dumps['close'].shift(4)) / dumps['close'].shift(4)) * 100

    print("4. RECENT PRICE MOVEMENT:")
    print(f"   Avg change last 1h: {dumps['prev_1h_change'].mean():.2f}%")
    print(f"   Avg change last 4h: {dumps['prev_4h_change'].mean():.2f}%")
    print()

    # Time patterns
    dumps['hour'] = dumps['timestamp'].dt.hour
    print("5. TIME PATTERNS (by hour):")
    hour_dist = dumps['hour'].value_counts().sort_index()
    for hour, count in hour_dist.items():
        print(f"   {hour:02d}:00 - {count} dumps ({count/len(dumps)*100:.1f}%)")
    print()

print("="*140)
print()
print("POTENTIAL STRATEGIES TO TEST:")
print("="*140)
print()

strategies = [
    "1. VOLATILITY EXPANSION: ATR% spikes above threshold → SHORT",
    "2. FAILED BOUNCE: Price tries to rally (green candles) but fails to hold → SHORT",
    "3. LOWER HIGH PATTERN: Each bounce makes lower high than previous → SHORT when confirmed",
    "4. TIME-BASED: Focus on high-probability dump hours only",
    "5. MULTI-TIMEFRAME: 15m breakdown + 1h trend confirmation",
    "6. VOLUME PROXY: Large body candles (>1.5%) as volume spike → SHORT",
    "7. ATR BANDS: Price breaking below (Price - 2*ATR) → SHORT",
    "8. MOMENTUM: Price falling faster than average (compare to 4h average change)",
    "9. BREAKDOWN + RETEST: Break support, bounce back to retest, then continue SHORT",
    "10. INVERSE RSI: SHORT when RSI is LOW (30-40) in downtrend = oversold bounces fail"
]

for s in strategies:
    print(s)

print()
print("="*140)
