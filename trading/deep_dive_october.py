#!/usr/bin/env python3
"""
Deep dive: What ACTUALLY predicts October dumps?
Test: Patterns, Volatility, Momentum, Price Action
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate ALL indicators
# RSI
delta = df['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.rolling(window=14, min_periods=14).mean()
avg_loss = loss.rolling(window=14, min_periods=14).mean()
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
df['atr_pct'] = (df['atr'] / df['close']) * 100

# ATR change (volatility expansion)
df['atr_change'] = df['atr_pct'].pct_change() * 100

# Body size (volume proxy)
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

# Momentum
df['change_pct'] = ((df['close'] - df['open']) / df['open']) * 100
df['momentum_4h'] = ((df['close'] - df['close'].shift(16)) / df['close'].shift(16)) * 100
df['momentum_1h'] = ((df['close'] - df['close'].shift(4)) / df['close'].shift(4)) * 100

# Rate of change acceleration
df['roc_4h'] = df['momentum_4h'].diff()

# Consecutive candles
df['is_red'] = (df['close'] < df['open']).astype(int)
df['consecutive_red'] = 0
for i in range(1, len(df)):
    if df.iloc[i]['is_red']:
        df.loc[i, 'consecutive_red'] = df.loc[i-1, 'consecutive_red'] + 1

# Distance from moving average
df['ma_20'] = df['close'].rolling(window=20).mean()
df['dist_from_ma'] = ((df['close'] - df['ma_20']) / df['ma_20']) * 100

# Forward returns (target variable)
df['fwd_6h'] = ((df['close'].shift(-24) - df['close']) / df['close']) * 100

# October only
df_oct = df[(df['timestamp'] >= '2025-10-01') & (df['timestamp'] < '2025-11-01')].copy()

print("="*140)
print("OCTOBER DEEP DIVE: What Predicts Dumps?")
print("="*140)
print()

# Define dump as >5% drop in next 6 hours
df_oct['is_dump'] = df_oct['fwd_6h'] < -5.0

dump_bars = df_oct[df_oct['is_dump']].copy()
no_dump_bars = df_oct[~df_oct['is_dump']].copy()

print(f"Total bars in October: {len(df_oct)}")
print(f"Bars before dumps: {len(dump_bars)} ({len(dump_bars)/len(df_oct)*100:.1f}%)")
print()

# Compare characteristics
print("="*140)
print("1. VOLATILITY EXPANSION (ATR)")
print("-"*140)
print(f"{'Metric':<40} | {'Before Dump':<15} | {'Normal':<15} | {'Difference':<15}")
print("-"*140)
print(f"{'ATR %':<40} | {dump_bars['atr_pct'].mean():>13.2f}% | {no_dump_bars['atr_pct'].mean():>13.2f}% | {dump_bars['atr_pct'].mean() - no_dump_bars['atr_pct'].mean():>13.2f}%")
print(f"{'ATR Change (expansion %)':<40} | {dump_bars['atr_change'].mean():>13.2f}% | {no_dump_bars['atr_change'].mean():>13.2f}% | {dump_bars['atr_change'].mean() - no_dump_bars['atr_change'].mean():>13.2f}%")
print()

# Test ATR expansion signal
atr_expansion_threshold = 5  # ATR increased by 5%
df_oct['atr_signal'] = df_oct['atr_change'] > atr_expansion_threshold
atr_precision = len(df_oct[(df_oct['atr_signal']) & (df_oct['is_dump'])]) / len(df_oct[df_oct['atr_signal']]) * 100 if len(df_oct[df_oct['atr_signal']]) > 0 else 0
atr_recall = len(df_oct[(df_oct['atr_signal']) & (df_oct['is_dump'])]) / len(dump_bars) * 100 if len(dump_bars) > 0 else 0
print(f"ATR Expansion >5% Signal:")
print(f"  Precision: {atr_precision:.1f}% (how many signals led to dumps)")
print(f"  Recall: {atr_recall:.1f}% (how many dumps were caught)")
print()

print("="*140)
print("2. MOMENTUM & ACCELERATION")
print("-"*140)
print(f"{'Metric':<40} | {'Before Dump':<15} | {'Normal':<15} | {'Difference':<15}")
print("-"*140)
print(f"{'4h Momentum %':<40} | {dump_bars['momentum_4h'].mean():>13.2f}% | {no_dump_bars['momentum_4h'].mean():>13.2f}% | {dump_bars['momentum_4h'].mean() - no_dump_bars['momentum_4h'].mean():>13.2f}%")
print(f"{'1h Momentum %':<40} | {dump_bars['momentum_1h'].mean():>13.2f}% | {no_dump_bars['momentum_1h'].mean():>13.2f}% | {dump_bars['momentum_1h'].mean() - no_dump_bars['momentum_1h'].mean():>13.2f}%")
print(f"{'ROC Acceleration':<40} | {dump_bars['roc_4h'].mean():>13.2f}% | {no_dump_bars['roc_4h'].mean():>13.2f}% | {dump_bars['roc_4h'].mean() - no_dump_bars['roc_4h'].mean():>13.2f}%")
print()

# Test momentum signal
momentum_threshold = -2.0  # Already falling 2% in 4h
df_oct['momentum_signal'] = df_oct['momentum_4h'] < momentum_threshold
mom_precision = len(df_oct[(df_oct['momentum_signal']) & (df_oct['is_dump'])]) / len(df_oct[df_oct['momentum_signal']]) * 100 if len(df_oct[df_oct['momentum_signal']]) > 0 else 0
mom_recall = len(df_oct[(df_oct['momentum_signal']) & (df_oct['is_dump'])]) / len(dump_bars) * 100 if len(dump_bars) > 0 else 0
print(f"Momentum <-2% in 4h Signal:")
print(f"  Precision: {mom_precision:.1f}%")
print(f"  Recall: {mom_recall:.1f}%")
print()

print("="*140)
print("3. CONSECUTIVE RED CANDLES (Pattern)")
print("-"*140)
print(f"{'Metric':<40} | {'Before Dump':<15} | {'Normal':<15} | {'Difference':<15}")
print("-"*140)
print(f"{'Consecutive Red Candles':<40} | {dump_bars['consecutive_red'].mean():>13.2f} | {no_dump_bars['consecutive_red'].mean():>13.2f} | {dump_bars['consecutive_red'].mean() - no_dump_bars['consecutive_red'].mean():>13.2f}")
print()

# Test consecutive red signal
consecutive_threshold = 2
df_oct['consecutive_signal'] = df_oct['consecutive_red'] >= consecutive_threshold
cons_precision = len(df_oct[(df_oct['consecutive_signal']) & (df_oct['is_dump'])]) / len(df_oct[df_oct['consecutive_signal']]) * 100 if len(df_oct[df_oct['consecutive_signal']]) > 0 else 0
cons_recall = len(df_oct[(df_oct['consecutive_signal']) & (df_oct['is_dump'])]) / len(dump_bars) * 100 if len(dump_bars) > 0 else 0
print(f"2+ Consecutive Red Candles Signal:")
print(f"  Precision: {cons_precision:.1f}%")
print(f"  Recall: {cons_recall:.1f}%")
print()

print("="*140)
print("4. BODY SIZE / VOLUME PROXY")
print("-"*140)
print(f"{'Metric':<40} | {'Before Dump':<15} | {'Normal':<15} | {'Difference':<15}")
print("-"*140)
print(f"{'Body Size %':<40} | {dump_bars['body_pct'].mean():>13.2f}% | {no_dump_bars['body_pct'].mean():>13.2f}% | {dump_bars['body_pct'].mean() - no_dump_bars['body_pct'].mean():>13.2f}%")
print()

# Test body size signal
body_threshold = 1.0
df_oct['body_signal'] = df_oct['body_pct'] > body_threshold
body_precision = len(df_oct[(df_oct['body_signal']) & (df_oct['is_dump'])]) / len(df_oct[df_oct['body_signal']]) * 100 if len(df_oct[df_oct['body_signal']]) > 0 else 0
body_recall = len(df_oct[(df_oct['body_signal']) & (df_oct['is_dump'])]) / len(dump_bars) * 100 if len(dump_bars) > 0 else 0
print(f"Body >1% Signal:")
print(f"  Precision: {body_precision:.1f}%")
print(f"  Recall: {body_recall:.1f}%")
print()

print("="*140)
print("5. DISTANCE FROM MA (Trend)")
print("-"*140)
print(f"{'Metric':<40} | {'Before Dump':<15} | {'Normal':<15} | {'Difference':<15}")
print("-"*140)
print(f"{'Distance from 20 MA %':<40} | {dump_bars['dist_from_ma'].mean():>13.2f}% | {no_dump_bars['dist_from_ma'].mean():>13.2f}% | {dump_bars['dist_from_ma'].mean() - no_dump_bars['dist_from_ma'].mean():>13.2f}%")
print()

# Test below MA signal
df_oct['ma_signal'] = df_oct['dist_from_ma'] < -1.0
ma_precision = len(df_oct[(df_oct['ma_signal']) & (df_oct['is_dump'])]) / len(df_oct[df_oct['ma_signal']]) * 100 if len(df_oct[df_oct['ma_signal']]) > 0 else 0
ma_recall = len(df_oct[(df_oct['ma_signal']) & (df_oct['is_dump'])]) / len(dump_bars) * 100 if len(dump_bars) > 0 else 0
print(f"Price <-1% below 20 MA Signal:")
print(f"  Precision: {ma_precision:.1f}%")
print(f"  Recall: {ma_recall:.1f}%")
print()

print("="*140)
print("SUMMARY: Signal Quality Ranking")
print("="*140)
print(f"{'Signal':<40} | {'Precision':<12} | {'Recall':<12} | {'F1 Score':<12}")
print("-"*140)

signals = [
    ('ATR Expansion >5%', atr_precision, atr_recall),
    ('Momentum <-2% (4h)', mom_precision, mom_recall),
    ('2+ Consecutive Red', cons_precision, cons_recall),
    ('Body >1%', body_precision, body_recall),
    ('Below 20 MA', ma_precision, ma_recall)
]

for name, prec, rec in signals:
    f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0
    print(f"{name:<40} | {prec:>10.1f}% | {rec:>10.1f}% | {f1:>10.1f}%")

print()
print("="*140)
print()
print("RECOMMENDATION: Focus on signal with highest F1 score (balance of precision & recall)")
print("="*140)
