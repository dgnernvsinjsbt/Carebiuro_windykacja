#!/usr/bin/env python3
"""
PI/USDT Deep Dive Analysis
===========================
Understand WHY PI is hard to trade and find its unique edge.
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Load data
df = pd.read_csv('pi_30d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Basic features
df['returns'] = (df['close'] - df['open']) / df['open'] * 100
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['range_pct'] = (df['high'] - df['low']) / df['open'] * 100

# Volume
df['volume_ma_20'] = df['volume'].rolling(20).mean()
df['volume_ma_30'] = df['volume'].rolling(30).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma_30']

# ATR
df['tr'] = df[['high', 'low']].apply(lambda x: x['high'] - x['low'], axis=1)
df['atr_14'] = df['tr'].rolling(14).mean()
df['atr_pct'] = df['atr_14'] / df['close'] * 100

# EMA
df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
df['ema_dist_pct'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi_14'] = 100 - (100 / (1 + rs))

# Forward returns (prediction targets)
df['fwd_1'] = df['close'].shift(-1) / df['close'] - 1
df['fwd_5'] = df['close'].shift(-5) / df['close'] - 1
df['fwd_10'] = df['close'].shift(-10) / df['close'] - 1
df['fwd_20'] = df['close'].shift(-20) / df['close'] - 1

print("="*70)
print("PI/USDT DEEP DIVE ANALYSIS")
print("="*70)

# ==================== 1. VOLATILITY REGIMES ====================

print("\n1️⃣ VOLATILITY REGIME ANALYSIS")
print("-" * 70)

# Classify candles by volatility
df['vol_regime'] = pd.cut(df['body_pct'], bins=[0, 0.05, 0.1, 0.2, 999], labels=['DEAD', 'LOW', 'MED', 'HIGH'])

print("\nVolatility Distribution:")
print(df['vol_regime'].value_counts())

print("\nAverage Forward Returns by Volatility:")
for regime in ['DEAD', 'LOW', 'MED', 'HIGH']:
    subset = df[df['vol_regime'] == regime]
    if len(subset) > 0:
        print(f"\n{regime}:")
        print(f"  Fwd 1m:  {subset['fwd_1'].mean()*100:.4f}%")
        print(f"  Fwd 5m:  {subset['fwd_5'].mean()*100:.4f}%")
        print(f"  Fwd 10m: {subset['fwd_10'].mean()*100:.4f}%")
        print(f"  Fwd 20m: {subset['fwd_20'].mean()*100:.4f}%")

# ==================== 2. RSI EXTREMES ====================

print("\n\n2️⃣ RSI EXTREME ANALYSIS")
print("-" * 70)

# Test if RSI extremes predict reversals
rsi_oversold = df[df['rsi_14'] < 30]
rsi_overbought = df[df['rsi_14'] > 70]

print(f"\nRSI < 30 (Oversold): {len(rsi_oversold)} candles")
print(f"  Avg Fwd 5m:  {rsi_oversold['fwd_5'].mean()*100:.4f}%")
print(f"  Avg Fwd 10m: {rsi_oversold['fwd_10'].mean()*100:.4f}%")
print(f"  Avg Fwd 20m: {rsi_oversold['fwd_20'].mean()*100:.4f}%")

print(f"\nRSI > 70 (Overbought): {len(rsi_overbought)} candles")
print(f"  Avg Fwd 5m:  {rsi_overbought['fwd_5'].mean()*100:.4f}%")
print(f"  Avg Fwd 10m: {rsi_overbought['fwd_10'].mean()*100:.4f}%")
print(f"  Avg Fwd 20m: {rsi_overbought['fwd_20'].mean()*100:.4f}%")

# ==================== 3. VOLUME SPIKES ====================

print("\n\n3️⃣ VOLUME SPIKE ANALYSIS")
print("-" * 70)

# High volume candles
high_vol = df[df['volume_ratio'] > 3.0]
print(f"\nVolume > 3x Average: {len(high_vol)} candles ({len(high_vol)/len(df)*100:.2f}%)")
print(f"  Avg Fwd 5m:  {high_vol['fwd_5'].mean()*100:.4f}%")
print(f"  Avg Fwd 10m: {high_vol['fwd_10'].mean()*100:.4f}%")
print(f"  Avg Fwd 20m: {high_vol['fwd_20'].mean()*100:.4f}%")

# Very high volume
very_high_vol = df[df['volume_ratio'] > 5.0]
print(f"\nVolume > 5x Average: {len(very_high_vol)} candles")
print(f"  Avg Fwd 5m:  {very_high_vol['fwd_5'].mean()*100:.4f}%")
print(f"  Avg Fwd 10m: {very_high_vol['fwd_10'].mean()*100:.4f}%")
print(f"  Avg Fwd 20m: {very_high_vol['fwd_20'].mean()*100:.4f}%")

# ==================== 4. CONSOLIDATION BREAKOUTS ====================

print("\n\n4️⃣ CONSOLIDATION BREAKOUT ANALYSIS")
print("-" * 70)

# Find tight consolidation periods (low range for 10+ candles)
df['low_range'] = (df['range_pct'] < 0.1).astype(int)
df['consol_bars'] = df['low_range'].rolling(10).sum()

# Breakout = high range after consolidation
df['breakout'] = ((df['consol_bars'] >= 8) & (df['range_pct'] > 0.2)).astype(int)

breakouts = df[df['breakout'] == 1]
print(f"\nBreakouts after Consolidation: {len(breakouts)} events")
if len(breakouts) > 0:
    print(f"  Avg Fwd 5m:  {breakouts['fwd_5'].mean()*100:.4f}%")
    print(f"  Avg Fwd 10m: {breakouts['fwd_10'].mean()*100:.4f}%")
    print(f"  Avg Fwd 20m: {breakouts['fwd_20'].mean()*100:.4f}%")

    # Bullish vs Bearish breakouts
    bull_bo = breakouts[breakouts['returns'] > 0]
    bear_bo = breakouts[breakouts['returns'] < 0]

    print(f"\n  Bullish Breakouts: {len(bull_bo)}")
    print(f"    Avg Fwd 10m: {bull_bo['fwd_10'].mean()*100:.4f}%")

    print(f"\n  Bearish Breakouts: {len(bear_bo)}")
    print(f"    Avg Fwd 10m: {bear_bo['fwd_10'].mean()*100:.4f}%")

# ==================== 5. TIME-OF-DAY ANALYSIS ====================

print("\n\n5️⃣ TIME-OF-DAY ANALYSIS")
print("-" * 70)

df['hour'] = df['timestamp'].dt.hour

hourly_stats = df.groupby('hour').agg({
    'returns': ['mean', 'std'],
    'body_pct': 'mean',
    'volume': 'mean',
    'fwd_10': 'mean'
}).round(4)

print("\nHourly Statistics (Top 5 by Avg Fwd 10m):")
hourly_stats['fwd_10_pct'] = hourly_stats[('fwd_10', 'mean')] * 100
hourly_stats = hourly_stats.sort_values(('fwd_10', 'mean'), ascending=False)
print(hourly_stats.head(5))

print("\nHourly Statistics (Bottom 5 by Avg Fwd 10m):")
print(hourly_stats.tail(5))

# ==================== 6. TREND FOLLOWING ====================

print("\n\n6️⃣ TREND FOLLOWING ANALYSIS")
print("-" * 70)

# Price above/below EMA
df['above_ema'] = (df['close'] > df['ema_20']).astype(int)

above = df[df['above_ema'] == 1]
below = df[df['above_ema'] == 0]

print(f"\nPrice > EMA(20): {len(above)} candles ({len(above)/len(df)*100:.1f}%)")
print(f"  Avg Fwd 10m: {above['fwd_10'].mean()*100:.4f}%")

print(f"\nPrice < EMA(20): {len(below)} candles ({len(below)/len(df)*100:.1f}%)")
print(f"  Avg Fwd 10m: {below['fwd_10'].mean()*100:.4f}%")

# Strong trends (price far from EMA)
strong_uptrend = df[df['ema_dist_pct'] > 0.5]
strong_downtrend = df[df['ema_dist_pct'] < -0.5]

print(f"\nStrong Uptrend (>0.5% above EMA): {len(strong_uptrend)} candles")
print(f"  Avg Fwd 10m: {strong_uptrend['fwd_10'].mean()*100:.4f}%")

print(f"\nStrong Downtrend (<-0.5% below EMA): {len(strong_downtrend)} candles")
print(f"  Avg Fwd 10m: {strong_downtrend['fwd_10'].mean()*100:.4f}%")

# ==================== 7. MULTI-BAR PATTERNS ====================

print("\n\n7️⃣ MULTI-BAR PATTERN ANALYSIS")
print("-" * 70)

# Three consecutive up/down bars
df['up_bar'] = (df['close'] > df['open']).astype(int)
df['down_bar'] = (df['close'] < df['open']).astype(int)

df['three_up'] = ((df['up_bar'] == 1) &
                  (df['up_bar'].shift(1) == 1) &
                  (df['up_bar'].shift(2) == 1)).astype(int)

df['three_down'] = ((df['down_bar'] == 1) &
                    (df['down_bar'].shift(1) == 1) &
                    (df['down_bar'].shift(2) == 1)).astype(int)

three_up = df[df['three_up'] == 1]
three_down = df[df['three_down'] == 1]

print(f"\nThree Consecutive Up Bars: {len(three_up)} events")
print(f"  Avg Fwd 10m: {three_up['fwd_10'].mean()*100:.4f}%")

print(f"\nThree Consecutive Down Bars: {len(three_down)} events")
print(f"  Avg Fwd 10m: {three_down['fwd_10'].mean()*100:.4f}%")

# ==================== 8. RANGE COMPRESSION ====================

print("\n\n8️⃣ RANGE COMPRESSION ANALYSIS")
print("-" * 70)

# ATR declining = compression
df['atr_change'] = df['atr_14'].pct_change(5)

compression = df[df['atr_change'] < -0.1]  # ATR dropped >10% in 5 bars
print(f"\nATR Compression (>10% drop in 5 bars): {len(compression)} events")
if len(compression) > 0:
    print(f"  Avg Fwd 10m: {compression['fwd_10'].mean()*100:.4f}%")
    print(f"  Avg Fwd 20m: {compression['fwd_20'].mean()*100:.4f}%")

# ==================== SUMMARY ====================

print("\n\n" + "="*70)
print("🔍 KEY INSIGHTS")
print("="*70)

insights = []

# Check RSI
if len(rsi_oversold) > 0 and rsi_oversold['fwd_10'].mean() > 0.001:
    insights.append(f"✅ RSI < 30 predicts bounce (+{rsi_oversold['fwd_10'].mean()*100:.3f}% in 10m)")

if len(rsi_overbought) > 0 and rsi_overbought['fwd_10'].mean() < -0.001:
    insights.append(f"✅ RSI > 70 predicts decline ({rsi_overbought['fwd_10'].mean()*100:.3f}% in 10m)")

# Check volume
if len(very_high_vol) > 0 and abs(very_high_vol['fwd_10'].mean()) > 0.002:
    insights.append(f"✅ Volume >5x predicts move ({very_high_vol['fwd_10'].mean()*100:+.3f}% in 10m)")

# Check breakouts
if len(breakouts) > 0 and abs(breakouts['fwd_10'].mean()) > 0.002:
    insights.append(f"✅ Consolidation breakouts work ({breakouts['fwd_10'].mean()*100:+.3f}% in 10m)")

# Check trends
if len(strong_uptrend) > 0 and strong_uptrend['fwd_10'].mean() > 0.001:
    insights.append(f"✅ Strong uptrends continue (+{strong_uptrend['fwd_10'].mean()*100:.3f}% in 10m)")

if len(strong_downtrend) > 0 and strong_downtrend['fwd_10'].mean() < -0.001:
    insights.append(f"✅ Strong downtrends continue ({strong_downtrend['fwd_10'].mean()*100:.3f}% in 10m)")

if insights:
    print("\nPatterns with Edge:\n")
    for insight in insights:
        print(f"  {insight}")
else:
    print("\n⚠️  NO CLEAR EDGE FOUND")
    print("  PI may be too efficient/random to trade profitably")

print("\n" + "="*70 + "\n")
