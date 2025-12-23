#!/usr/bin/env python3
"""
Debug PENGU signal flow - trace where trades are blocked
Compare ARM signals → Break → Limit placed → Limit filled
"""
import pandas as pd
import numpy as np

print("="*90)
print("PENGU SIGNAL FLOW DIAGNOSTIC")
print("="*90)

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

# Calculate ATR
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

# MELANIA Parameters
rsi_trigger = 72
lookback = 5
limit_atr_offset = 0.8
tp_pct = 10.0
max_wait_bars = 20
max_sl_pct = 10.0
risk_pct = 5.0

print(f"\n📊 Strategy Parameters:")
print(f"   RSI Trigger: {rsi_trigger}")
print(f"   Lookback: {lookback}")
print(f"   Limit Offset: {limit_atr_offset} ATR")
print(f"   Max SL: {max_sl_pct}%")
print(f"   Max Wait: {max_wait_bars} bars")

# Diagnostic counters
stats = {
    'rsi_arms': 0,
    'swing_low_breaks': 0,
    'limits_placed': 0,
    'limits_filled': 0,
    'limits_timeout': 0,
    'rejected_sl_too_wide': 0,
    'rejected_sl_negative': 0
}

# Detailed logs
arm_log = []
break_log = []
limit_log = []

armed = False
signal_idx = None
swing_low = None
limit_pending = False
limit_placed_idx = None
swing_high_for_sl = None
limit_price = None

for i in range(lookback + 14, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        continue

    # STEP 1: ARM on RSI > trigger
    if row['rsi'] > rsi_trigger and not armed and not limit_pending:
        armed = True
        signal_idx = i
        swing_low = df.iloc[i-lookback:i+1]['low'].min()
        stats['rsi_arms'] += 1

        arm_log.append({
            'time': row['timestamp'],
            'rsi': row['rsi'],
            'price': row['close'],
            'swing_low': swing_low
        })

    # STEP 2: Wait for break below swing low
    if armed and swing_low is not None and not limit_pending:
        if row['low'] < swing_low:
            stats['swing_low_breaks'] += 1

            # Calculate limit order
            atr = row['atr']
            limit_price = swing_low + (atr * limit_atr_offset)
            swing_high_for_sl = df.iloc[signal_idx:i+1]['high'].max()

            sl_dist_pct = ((swing_high_for_sl - limit_price) / limit_price) * 100

            break_log.append({
                'time': row['timestamp'],
                'break_price': row['low'],
                'swing_low': swing_low,
                'limit_price': limit_price,
                'swing_high': swing_high_for_sl,
                'sl_dist_pct': sl_dist_pct,
                'atr': atr,
                'atr_pct': (atr / row['close']) * 100
            })

            # Check SL distance
            if sl_dist_pct <= 0:
                stats['rejected_sl_negative'] += 1
                armed = False
                continue

            if sl_dist_pct > max_sl_pct:
                stats['rejected_sl_too_wide'] += 1
                armed = False
                continue

            # Valid - place limit
            limit_pending = True
            limit_placed_idx = i
            stats['limits_placed'] += 1
            armed = False

    # STEP 3: Check limit fill
    if limit_pending:
        bars_waiting = i - limit_placed_idx

        # Timeout
        if bars_waiting > max_wait_bars:
            stats['limits_timeout'] += 1
            limit_log.append({
                'placed_time': df.iloc[limit_placed_idx]['timestamp'],
                'limit_price': limit_price,
                'filled': False,
                'reason': 'timeout',
                'bars_waited': bars_waiting
            })
            limit_pending = False
            swing_low = None
            swing_high_for_sl = None
            continue

        # Check fill
        if row['low'] <= limit_price:
            stats['limits_filled'] += 1
            limit_log.append({
                'placed_time': df.iloc[limit_placed_idx]['timestamp'],
                'filled_time': row['timestamp'],
                'limit_price': limit_price,
                'filled': True,
                'bars_waited': bars_waiting
            })
            limit_pending = False
            swing_low = None
            swing_high_for_sl = None

# Results
print(f"\n" + "="*90)
print("📊 SIGNAL FLOW BREAKDOWN")
print("="*90)
print()

total_rsi_periods = 182  # From previous analysis
print(f"Step 1 - RSI >72 Periods:        {total_rsi_periods} (from RSI analysis)")
print(f"Step 2 - ARM Signals:            {stats['rsi_arms']} ({stats['rsi_arms']/total_rsi_periods*100:.1f}% of periods)")
print(f"Step 3 - Swing Low Breaks:       {stats['swing_low_breaks']} ({stats['swing_low_breaks']/stats['rsi_arms']*100 if stats['rsi_arms'] > 0 else 0:.1f}% of ARMs)")
print()
print(f"Step 4 - Limit Orders Placed:    {stats['limits_placed']}")
print(f"         ❌ Rejected (SL >10%):   {stats['rejected_sl_too_wide']}")
print(f"         ❌ Rejected (SL ≤0%):    {stats['rejected_sl_negative']}")
print(f"         Total attempts:          {stats['limits_placed'] + stats['rejected_sl_too_wide'] + stats['rejected_sl_negative']}")
print()
print(f"Step 5 - Limit Fill Results:     ")
print(f"         ✅ Filled:               {stats['limits_filled']} ({stats['limits_filled']/stats['limits_placed']*100 if stats['limits_placed'] > 0 else 0:.1f}% fill rate)")
print(f"         ⏱️  Timeout:              {stats['limits_timeout']} ({stats['limits_timeout']/stats['limits_placed']*100 if stats['limits_placed'] > 0 else 0:.1f}%)")

# Conversion funnel
print(f"\n" + "="*90)
print("📉 CONVERSION FUNNEL")
print("="*90)
print()

print(f"182 RSI periods")
print(f"  ↓ {stats['rsi_arms']/total_rsi_periods*100:.1f}%")
print(f"{stats['rsi_arms']} ARM signals")
print(f"  ↓ {stats['swing_low_breaks']/stats['rsi_arms']*100 if stats['rsi_arms'] > 0 else 0:.1f}%")
print(f"{stats['swing_low_breaks']} Swing low breaks")
print(f"  ↓ {stats['limits_placed']/stats['swing_low_breaks']*100 if stats['swing_low_breaks'] > 0 else 0:.1f}% (SL filter)")
print(f"{stats['limits_placed']} Limits placed")
print(f"  ↓ {stats['limits_filled']/stats['limits_placed']*100 if stats['limits_placed'] > 0 else 0:.1f}% (fill rate)")
print(f"{stats['limits_filled']} ✅ FINAL TRADES")

# Analysis of rejected trades
if stats['rejected_sl_too_wide'] > 0:
    break_df = pd.DataFrame(break_log)
    rejected = break_df[break_df['sl_dist_pct'] > max_sl_pct]

    print(f"\n" + "="*90)
    print(f"🔍 REJECTED TRADES ANALYSIS (SL >{max_sl_pct}%)")
    print("="*90)
    print()
    print(f"Total rejected: {len(rejected)}")
    print(f"Avg SL distance: {rejected['sl_dist_pct'].mean():.2f}%")
    print(f"Max SL distance: {rejected['sl_dist_pct'].max():.2f}%")
    print(f"Min SL distance: {rejected['sl_dist_pct'].min():.2f}%")
    print()
    print("First 10 rejected trades:")
    print(f"{'Time':>20} | {'SL Dist %':>10} | {'ATR %':>8} | {'Limit Price':>12}")
    print("-" * 60)
    for _, row in rejected.head(10).iterrows():
        print(f"{str(row['time'])[:19]:>20} | {row['sl_dist_pct']:>10.2f} | {row['atr_pct']:>8.3f} | ${row['limit_price']:>11.6f}")

# Timeout analysis
if stats['limits_timeout'] > 0:
    limit_df = pd.DataFrame(limit_log)
    timeouts = limit_df[limit_df['filled'] == False]

    print(f"\n" + "="*90)
    print(f"⏱️  TIMEOUT ANALYSIS")
    print("="*90)
    print()
    print(f"Total timeouts: {len(timeouts)} ({len(timeouts)/len(limit_df)*100:.1f}% of limit orders)")
    print()
    print("First 10 timeouts:")
    print(f"{'Placed Time':>20} | {'Limit Price':>12} | {'Bars Waited':>12}")
    print("-" * 50)
    for _, row in timeouts.head(10).iterrows():
        print(f"{str(row['placed_time'])[:19]:>20} | ${row['limit_price']:>11.6f} | {row['bars_waited']:>12}")

# Fill analysis
if stats['limits_filled'] > 0:
    limit_df = pd.DataFrame(limit_log)
    fills = limit_df[limit_df['filled'] == True]

    print(f"\n" + "="*90)
    print(f"✅ FILL ANALYSIS")
    print("="*90)
    print()
    print(f"Total fills: {len(fills)}")
    print(f"Avg bars to fill: {fills['bars_waited'].mean():.1f}")
    print(f"Max bars to fill: {fills['bars_waited'].max()}")
    print(f"Min bars to fill: {fills['bars_waited'].min()}")

print(f"\n" + "="*90)
print("💡 KEY FINDINGS")
print("="*90)
print()

# Identify biggest bottleneck
bottlenecks = [
    ('ARM signal generation', stats['rsi_arms'] / total_rsi_periods),
    ('Swing low breaks', stats['swing_low_breaks'] / stats['rsi_arms'] if stats['rsi_arms'] > 0 else 0),
    ('SL distance filter', stats['limits_placed'] / stats['swing_low_breaks'] if stats['swing_low_breaks'] > 0 else 0),
    ('Limit fill rate', stats['limits_filled'] / stats['limits_placed'] if stats['limits_placed'] > 0 else 0)
]

bottlenecks.sort(key=lambda x: x[1])

print("Bottlenecks (from worst to best):")
for name, rate in bottlenecks:
    print(f"   {name:.<40} {rate*100:>6.1f}%")

print(f"\n🎯 Biggest issue: {bottlenecks[0][0]} ({bottlenecks[0][1]*100:.1f}% conversion)")

print("="*90)
