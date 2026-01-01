#!/usr/bin/env python3
"""
Analyze dumps using MULTIPLE indicators - not just RSI
Look for patterns in: ATR, momentum, candle bodies, breakdowns, velocity
"""
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# === INDICATORS ===

# RSI
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

# Candle body %
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['is_red'] = df['close'] < df['open']

# Momentum (velocity of price change)
df['ret_15m'] = ((df['close'] - df['close'].shift(1)) / df['close'].shift(1)) * 100
df['ret_1h'] = ((df['close'] - df['close'].shift(4)) / df['close'].shift(4)) * 100
df['ret_2h'] = ((df['close'] - df['close'].shift(8)) / df['close'].shift(8)) * 100

# Acceleration (change in momentum)
df['accel_1h'] = df['ret_1h'].diff()

# Rolling high/low (support/resistance)
df['high_20'] = df['high'].rolling(window=20).max()
df['low_20'] = df['low'].rolling(window=20).min()
df['dist_from_high_pct'] = ((df['close'] - df['high_20']) / df['high_20']) * 100

# ATR ratio (current vs average)
df['atr_ma'] = df['atr_pct'].rolling(window=20).mean()
df['atr_ratio'] = df['atr_pct'] / df['atr_ma']

# Future returns (for labeling dumps)
df['fwd_2h'] = ((df['close'].shift(-8) - df['close']) / df['close']) * 100
df['fwd_4h'] = ((df['close'].shift(-16) - df['close']) / df['close']) * 100
df['fwd_6h'] = ((df['close'].shift(-24) - df['close']) / df['close']) * 100

# Filter to October
df_oct = df[(df['timestamp'] >= '2025-10-01') & (df['timestamp'] < '2025-11-01')].copy()

# Find dumps (>5% down in next 4h)
df_oct['dump'] = df_oct['fwd_4h'] < -5.0

dumps = df_oct[df_oct['dump']].copy()
non_dumps = df_oct[~df_oct['dump']].copy()

print("="*120)
print("DUMP TRIGGER ANALYSIS - COMPARING DUMPS VS NON-DUMPS")
print("="*120)
print(f"\nOctober data: {len(df_oct)} candles")
print(f"Dumps (>5% drop in 4h): {len(dumps)} candles")
print(f"Non-dumps: {len(non_dumps)} candles")
print()

# === STATISTICAL COMPARISON ===
print("="*120)
print("INDICATOR COMPARISON: DUMPS vs NON-DUMPS")
print("="*120)
print()

indicators = {
    'RSI': 'rsi',
    'ATR %': 'atr_pct',
    'ATR Ratio': 'atr_ratio',
    'Body %': 'body_pct',
    'Red Candle %': 'is_red',
    '15m Return %': 'ret_15m',
    '1h Return %': 'ret_1h',
    '2h Return %': 'ret_2h',
    '1h Accel': 'accel_1h',
    'Dist from High %': 'dist_from_high_pct'
}

print(f"{'Indicator':<20} | {'Dumps Mean':<12} | {'Non-Dumps Mean':<15} | {'Difference':<12}")
print("-"*120)

for name, col in indicators.items():
    if col == 'is_red':
        dump_val = dumps[col].mean() * 100
        non_dump_val = non_dumps[col].mean() * 100
        diff = dump_val - non_dump_val
        print(f"{name:<20} | {dump_val:<11.1f}% | {non_dump_val:<14.1f}% | {diff:+.1f}%")
    else:
        dump_val = dumps[col].mean()
        non_dump_val = non_dumps[col].mean()
        diff = dump_val - non_dump_val
        print(f"{name:<20} | {dump_val:<12.2f} | {non_dump_val:<15.2f} | {diff:+.2f}")

print()
print("="*120)
print("FINDING BEST INDICATORS (Highest Difference)")
print("="*120)
print()

# Find indicators with biggest difference
differences = []
for name, col in indicators.items():
    if col == 'is_red':
        continue
    dump_val = dumps[col].mean()
    non_dump_val = non_dumps[col].mean()
    diff_pct = abs((dump_val - non_dump_val) / non_dump_val * 100) if non_dump_val != 0 else 0
    differences.append((name, diff_pct, dump_val, non_dump_val))

differences.sort(key=lambda x: x[1], reverse=True)

print("Top indicators by relative difference:")
print()
for name, diff_pct, dump_val, non_dump_val in differences[:5]:
    print(f"{name}: {diff_pct:.1f}% difference (Dumps={dump_val:.2f}, Non-dumps={non_dump_val:.2f})")

print()
print("="*120)
print("ANALYZING CANDLE PATTERNS BEFORE DUMPS")
print("="*120)
print()

# Look at the candle right before each dump
dumps_with_prev = []
for idx in dumps.index:
    if idx > 0:
        prev_idx = idx - 1
        if prev_idx in df_oct.index:
            prev = df_oct.loc[prev_idx]
            curr = df_oct.loc[idx]

            dumps_with_prev.append({
                'prev_body_pct': prev['body_pct'],
                'prev_is_red': prev['is_red'],
                'prev_ret_15m': prev['ret_15m'],
                'curr_body_pct': curr['body_pct'],
                'curr_is_red': curr['is_red'],
                'curr_ret_15m': curr['ret_15m'],
                'breakdown': curr['low'] < prev['low']
            })

dumps_prev_df = pd.DataFrame(dumps_with_prev)

print(f"Analyzing {len(dumps_prev_df)} dump entry candles:")
print()
print(f"Current candle (dump start):")
print(f"  Red candles: {dumps_prev_df['curr_is_red'].mean()*100:.1f}%")
print(f"  Avg body: {dumps_prev_df['curr_body_pct'].mean():.2f}%")
print(f"  Avg 15m return: {dumps_prev_df['curr_ret_15m'].mean():.2f}%")
print()
print(f"Previous candle:")
print(f"  Red candles: {dumps_prev_df['prev_is_red'].mean()*100:.1f}%")
print(f"  Avg body: {dumps_prev_df['prev_body_pct'].mean():.2f}%")
print(f"  Breakdown (new low): {dumps_prev_df['breakdown'].mean()*100:.1f}%")
print()

print("="*120)
print("STRATEGY IDEAS FROM DATA")
print("="*120)
print()

# Test simple momentum strategy
print("💡 Idea 1: Enter SHORT when 15m return < -1.5% (momentum dump)")
strategy1_signals = df_oct[df_oct['ret_15m'] < -1.5].copy()
strategy1_signals['fwd_4h_actual'] = strategy1_signals['fwd_4h']
profitable = strategy1_signals[strategy1_signals['fwd_4h_actual'] < -2.0]
print(f"   Signals: {len(strategy1_signals)}")
print(f"   Profitable (>2% down): {len(profitable)} ({len(profitable)/len(strategy1_signals)*100:.1f}%)")
print(f"   Avg fwd 4h return: {strategy1_signals['fwd_4h_actual'].mean():.2f}%")
print()

# Test ATR expansion
print("💡 Idea 2: Enter SHORT when ATR ratio > 1.3 (volatility spike)")
strategy2_signals = df_oct[df_oct['atr_ratio'] > 1.3].copy()
strategy2_signals['fwd_4h_actual'] = strategy2_signals['fwd_4h']
profitable2 = strategy2_signals[strategy2_signals['fwd_4h_actual'] < -2.0]
print(f"   Signals: {len(strategy2_signals)}")
print(f"   Profitable (>2% down): {len(profitable2)} ({len(profitable2)/len(strategy2_signals)*100:.1f}%)")
print(f"   Avg fwd 4h return: {strategy2_signals['fwd_4h_actual'].mean():.2f}%")
print()

# Test breakdown + red candle
print("💡 Idea 3: Enter SHORT on big red candle (body >1%) making new 20-bar low")
strategy3_signals = df_oct[(df_oct['is_red']) &
                            (df_oct['body_pct'] > 1.0) &
                            (df_oct['low'] <= df_oct['low_20'].shift(1))].copy()
strategy3_signals['fwd_4h_actual'] = strategy3_signals['fwd_4h']
profitable3 = strategy3_signals[strategy3_signals['fwd_4h_actual'] < -2.0]
print(f"   Signals: {len(strategy3_signals)}")
print(f"   Profitable (>2% down): {len(profitable3)} ({len(profitable3)/len(strategy3_signals)*100:.1f}%)")
print(f"   Avg fwd 4h return: {strategy3_signals['fwd_4h_actual'].mean():.2f}%")
print()

# Test combined
print("💡 Idea 4: COMBO - Big red (>1%) + ATR spike (>1.2) + momentum (-1%)")
strategy4_signals = df_oct[(df_oct['is_red']) &
                            (df_oct['body_pct'] > 1.0) &
                            (df_oct['atr_ratio'] > 1.2) &
                            (df_oct['ret_15m'] < -1.0)].copy()
strategy4_signals['fwd_4h_actual'] = strategy4_signals['fwd_4h']
profitable4 = strategy4_signals[strategy4_signals['fwd_4h_actual'] < -2.0]
print(f"   Signals: {len(strategy4_signals)}")
print(f"   Profitable (>2% down): {len(profitable4)} ({len(profitable4)/len(strategy4_signals)*100:.1f}%)")
if len(strategy4_signals) > 0:
    print(f"   Avg fwd 4h return: {strategy4_signals['fwd_4h_actual'].mean():.2f}%")
print()

print("="*120)
