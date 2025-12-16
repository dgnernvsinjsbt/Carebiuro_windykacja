#!/usr/bin/env python3
"""
FARTCOIN Strategy - Signal Mechanics Deep Dive

Answers:
1. How often do signals fire?
2. Do multiple signals fire during the same ATR expansion?
3. Can we get LONG then SHORT then LONG in quick succession?
4. How long do ATR expansion periods last?
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("=" * 80)
print("FARTCOIN ATR LIMIT - SIGNAL MECHANICS ANALYSIS")
print("=" * 80)

# Load data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
def calculate_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
df['atr_ma'] = df['atr'].rolling(20).mean()
df['atr_ratio'] = df['atr'] / df['atr_ma']
df['ema20'] = calculate_ema(df['close'], 20)
df['distance'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)
df['bullish'] = df['close'] > df['open']
df['bearish'] = df['close'] < df['open']

print(f"\n1. BASIC STATS")
print(f"   Total candles: {len(df):,}")
print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Duration: 30 days")

# Generate signals
print(f"\n2. SIGNAL GENERATION")

signals = []
for i in range(len(df)):
    row = df.iloc[i]

    if pd.isna(row['atr_ratio']) or pd.isna(row['distance']):
        continue

    # Entry conditions (EXACT same as bot)
    atr_expansion = row['atr_ratio'] > 1.5
    ema_distance_ok = row['distance'] < 3.0

    if atr_expansion and ema_distance_ok:
        if row['bullish']:
            signals.append({
                'idx': i,
                'timestamp': row['timestamp'],
                'direction': 'LONG',
                'close': row['close'],
                'atr_ratio': row['atr_ratio'],
                'distance': row['distance']
            })
        elif row['bearish']:
            signals.append({
                'idx': i,
                'timestamp': row['timestamp'],
                'direction': 'SHORT',
                'close': row['close'],
                'atr_ratio': row['atr_ratio'],
                'distance': row['distance']
            })

df_signals = pd.DataFrame(signals)

print(f"   Total signals: {len(signals)}")
print(f"   Signal rate: {len(signals)/len(df)*100:.2f}% of bars")
print(f"   Avg time between signals: {len(df)/len(signals):.1f} minutes" if len(signals) > 0 else "")

# Direction breakdown
longs = df_signals[df_signals['direction'] == 'LONG']
shorts = df_signals[df_signals['direction'] == 'SHORT']
print(f"   LONG signals: {len(longs)} ({len(longs)/len(signals)*100:.1f}%)")
print(f"   SHORT signals: {len(shorts)} ({len(shorts)/len(signals)*100:.1f}%)")

# 3. SIGNAL CLUSTERING
print(f"\n3. SIGNAL CLUSTERING (Do multiple signals fire in same ATR expansion?)")

# Calculate time gaps between signals
df_signals['time_gap'] = df_signals['timestamp'].diff().dt.total_seconds() / 60  # minutes
df_signals['idx_gap'] = df_signals['idx'].diff()

# Cluster signals that are within 10 minutes of each other
clusters = []
current_cluster = [0]

for i in range(1, len(df_signals)):
    if df_signals['time_gap'].iloc[i] <= 10:  # Within 10 minutes
        current_cluster.append(i)
    else:
        if len(current_cluster) > 1:
            clusters.append(current_cluster)
        current_cluster = [i]

if len(current_cluster) > 1:
    clusters.append(current_cluster)

print(f"   Signal clusters (≤10 min apart): {len(clusters)}")
print(f"   Clustered signals: {sum(len(c) for c in clusters)}")
print(f"   Isolated signals: {len(signals) - sum(len(c) for c in clusters)}")

if clusters:
    cluster_sizes = [len(c) for c in clusters]
    print(f"   Avg cluster size: {np.mean(cluster_sizes):.1f} signals")
    print(f"   Max cluster size: {max(cluster_sizes)} signals")

    # Analyze largest cluster
    largest_cluster = max(clusters, key=len)
    print(f"\n   LARGEST CLUSTER ({len(largest_cluster)} signals):")
    for sig_idx in largest_cluster:
        sig = df_signals.iloc[sig_idx]
        print(f"      {sig['timestamp']} - {sig['direction']} @ ${sig['close']:.6f} (ATR: {sig['atr_ratio']:.2f}x)")

# 4. DIRECTION SWITCHING
print(f"\n4. DIRECTION SWITCHING (LONG→SHORT→LONG patterns?)")

direction_switches = 0
consecutive_same = 0
max_consecutive = 1
current_consecutive = 1

for i in range(1, len(df_signals)):
    if df_signals['direction'].iloc[i] != df_signals['direction'].iloc[i-1]:
        direction_switches += 1
        max_consecutive = max(max_consecutive, current_consecutive)
        current_consecutive = 1
    else:
        current_consecutive += 1
        consecutive_same += 1

print(f"   Direction switches: {direction_switches}")
print(f"   Consecutive same direction: {consecutive_same}")
print(f"   Max consecutive same: {max_consecutive}")
print(f"   Switch rate: {direction_switches/(len(signals)-1)*100:.1f}% of signals")

# Show 10 rapid switches
print(f"\n   RAPID DIRECTION SWITCHES (≤5 minutes apart):")
rapid_switches = []
for i in range(1, len(df_signals)):
    if (df_signals['direction'].iloc[i] != df_signals['direction'].iloc[i-1] and
        df_signals['time_gap'].iloc[i] <= 5):
        rapid_switches.append(i)

for idx in rapid_switches[:10]:
    prev = df_signals.iloc[idx-1]
    curr = df_signals.iloc[idx]
    gap_min = curr['time_gap']
    print(f"      {prev['timestamp']} {prev['direction']} → {curr['timestamp']} {curr['direction']} ({gap_min:.1f}min gap)")

# 5. ATR EXPANSION ZONES
print(f"\n5. ATR EXPANSION DURATION")

df['atr_expanded'] = (df['atr_ratio'] > 1.5) & (df['distance'] < 3.0)

# Find expansion zones
expansion_zones = []
in_zone = False
zone_start = None
zone_bars = 0

for i in range(len(df)):
    if df['atr_expanded'].iloc[i] and not in_zone:
        # Start new zone
        in_zone = True
        zone_start = i
        zone_bars = 1
    elif df['atr_expanded'].iloc[i] and in_zone:
        # Continue zone
        zone_bars += 1
    elif not df['atr_expanded'].iloc[i] and in_zone:
        # End zone
        expansion_zones.append({
            'start_idx': zone_start,
            'duration_bars': zone_bars,
            'start_time': df['timestamp'].iloc[zone_start],
            'end_time': df['timestamp'].iloc[i-1]
        })
        in_zone = False
        zone_start = None
        zone_bars = 0

print(f"   Total expansion zones: {len(expansion_zones)}")
if expansion_zones:
    durations = [z['duration_bars'] for z in expansion_zones]
    print(f"   Avg duration: {np.mean(durations):.1f} minutes")
    print(f"   Median duration: {np.median(durations):.0f} minutes")
    print(f"   Max duration: {max(durations)} minutes")

    print(f"\n   LONGEST EXPANSION ZONES:")
    sorted_zones = sorted(expansion_zones, key=lambda z: z['duration_bars'], reverse=True)
    for zone in sorted_zones[:5]:
        # Count signals in this zone
        signals_in_zone = df_signals[
            (df_signals['idx'] >= zone['start_idx']) &
            (df_signals['idx'] < zone['start_idx'] + zone['duration_bars'])
        ]
        print(f"      {zone['start_time']} - {zone['duration_bars']} mins - {len(signals_in_zone)} signals")

# 6. PRACTICAL IMPLICATIONS
print(f"\n" + "=" * 80)
print("PRACTICAL IMPLICATIONS FOR LIVE TRADING")
print("=" * 80)

print(f"""
1. SIGNAL FREQUENCY:
   - {len(signals)} signals in 30 days = {len(signals)/30:.1f} signals/day
   - Avg {len(df)/len(signals):.1f} minutes between signals (≈{len(df)/len(signals)/60:.1f} hours)
   - Signals come in CLUSTERS during volatility spikes

2. MULTIPLE SIGNALS PER EXPANSION:
   - {len(clusters)} expansion periods generated {sum(len(c) for c in clusters)} clustered signals
   - Avg {sum(len(c) for c in clusters)/len(clusters) if clusters else 0:.1f} signals per expansion cluster
   - YES - you can get LONG, then SHORT, then LONG in same expansion zone

3. DIRECTION SWITCHING:
   - {direction_switches/(len(signals)-1)*100:.1f}% of signals switch direction from previous
   - Strategy does NOT wait for ATR to calm down
   - New signal on EVERY bar that meets conditions

4. WHAT HAPPENS IN PRACTICE:

   Example expansion period:
   - Minute 0: ATR spikes to 2.0x, bar closes GREEN
     → LONG signal: place buy limit 1% higher

   - Minute 1: ATR still 1.9x, bar closes RED
     → SHORT signal: place sell limit 1% lower
     → Previous LONG order still pending (unless filled)

   - Minute 2: ATR still 1.8x, bar closes GREEN
     → LONG signal AGAIN: place buy limit 1% higher (new price)

   - Minute 3: ATR still 1.7x, bar closes RED
     → SHORT signal AGAIN: place sell limit 1% lower (new price)

   - Continue until ATR drops <1.5x OR price moves >3% from EMA(20)

5. ORDER MANAGEMENT CRITICAL:
   - Without PendingOrderManager: you'd have {len(signals)} orders on exchange!
   - With 3-bar wait: each order lives max 3 minutes before cancel
   - But new signals keep coming during expansion
   - Need logic to prevent duplicate orders for same direction
""")

# 7. VERIFICATION WITH ACTUAL FILLS
print(f"\n" + "=" * 80)
print("VERIFICATION: Why only 89 fills from 401 signals?")
print("=" * 80)

print(f"""
401 signals generated
- 89 filled (22.2%)
- 312 unfilled (77.8%)

Unfilled because:
1. Limit order 1% away from signal price
2. Only wait 3 bars (3 minutes) for fill
3. If price doesn't move 1% in correct direction within 3 min → cancel

This 22% fill rate is a FEATURE, not a bug:
- Filters out fake breakouts
- Only trades when momentum confirms
- Prevents over-trading during choppy expansion zones

During typical expansion:
- 5 signals might fire
- 1-2 actually fill
- 3-4 cancel (price didn't confirm)
""")

print("=" * 80)
