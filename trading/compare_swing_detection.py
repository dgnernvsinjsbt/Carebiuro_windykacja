#!/usr/bin/env python3
"""
PORÓWNANIE: Lookback=5 vs ZigZag indicator
Pokaż ile swing points wykrywa każda metoda na September
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# September only
df_sep = df[(df['timestamp'] >= '2025-09-01') & (df['timestamp'] < '2025-10-01')].copy().reset_index(drop=True)

print("="*140)
print("PORÓWNANIE METOD DETEKCJI SWING POINTS - SEPTEMBER 2025")
print("="*140)
print()

# ============================================
# METODA 1: Lookback = 5 (OBECNA)
# ============================================
lookback = 5
swing_points_old = []

for i in range(lookback, len(df_sep) - lookback):
    is_swing_high = True
    for j in range(1, lookback + 1):
        if df_sep.iloc[i]['high'] <= df_sep.iloc[i-j]['high'] or df_sep.iloc[i]['high'] <= df_sep.iloc[i+j]['high']:
            is_swing_high = False
            break

    if is_swing_high:
        swing_points_old.append({'bar': i, 'price': df_sep.iloc[i]['high'], 'type': 'HIGH', 'time': df_sep.iloc[i]['timestamp']})
        continue

    is_swing_low = True
    for j in range(1, lookback + 1):
        if df_sep.iloc[i]['low'] >= df_sep.iloc[i-j]['low'] or df_sep.iloc[i]['low'] >= df_sep.iloc[i+j]['low']:
            is_swing_low = False
            break

    if is_swing_low:
        swing_points_old.append({'bar': i, 'price': df_sep.iloc[i]['low'], 'type': 'LOW', 'time': df_sep.iloc[i]['timestamp']})

print("METODA 1: Lookback = 5")
print(f"  Wykryto {len(swing_points_old)} swing points")
highs_old = [p for p in swing_points_old if p['type'] == 'HIGH']
lows_old = [p for p in swing_points_old if p['type'] == 'LOW']
print(f"    - {len(highs_old)} swing HIGHS")
print(f"    - {len(lows_old)} swing LOWS")
print()

# ============================================
# METODA 2: ZigZag Indicator (min 2% move)
# ============================================
def zigzag_indicator(df, min_pct=2.0):
    """
    ZigZag indicator: wykrywa swing points tylko jeśli move >= min_pct%

    Działa "live" - w każdym barze sprawdza czy poprzedni swing jest potwierdzony
    przez wystarczająco duży ruch w przeciwnym kierunku.
    """
    swings = []

    # Start from first bar
    current_price = df.iloc[0]['close']
    current_type = None  # HIGH or LOW
    current_bar = 0

    # Track extremes since last confirmed swing
    extreme_high = df.iloc[0]['high']
    extreme_high_bar = 0
    extreme_low = df.iloc[0]['low']
    extreme_low_bar = 0

    for i in range(1, len(df)):
        high = df.iloc[i]['high']
        low = df.iloc[i]['low']

        # Update extremes
        if high > extreme_high:
            extreme_high = high
            extreme_high_bar = i
        if low < extreme_low:
            extreme_low = low
            extreme_low_bar = i

        # If no current swing, wait for first significant move
        if current_type is None:
            up_move = ((extreme_high - extreme_low) / extreme_low) * 100
            down_move = ((extreme_high - extreme_low) / extreme_high) * 100

            if up_move >= min_pct:
                # Confirmed swing LOW at extreme_low_bar, now at HIGH
                swings.append({
                    'bar': extreme_low_bar,
                    'price': extreme_low,
                    'type': 'LOW',
                    'time': df.iloc[extreme_low_bar]['timestamp']
                })
                current_type = 'HIGH'
                current_bar = extreme_high_bar
                current_price = extreme_high
                # Reset tracking for next swing
                extreme_low = high
                extreme_low_bar = i
            elif down_move >= min_pct:
                # Confirmed swing HIGH at extreme_high_bar, now at LOW
                swings.append({
                    'bar': extreme_high_bar,
                    'price': extreme_high,
                    'type': 'HIGH',
                    'time': df.iloc[extreme_high_bar]['timestamp']
                })
                current_type = 'LOW'
                current_bar = extreme_low_bar
                current_price = extreme_low
                # Reset tracking
                extreme_high = low
                extreme_high_bar = i

        # If currently at HIGH, wait for significant down move to confirm LOW
        elif current_type == 'HIGH':
            down_move = ((current_price - extreme_low) / current_price) * 100
            if down_move >= min_pct:
                # Confirmed new swing LOW
                swings.append({
                    'bar': extreme_low_bar,
                    'price': extreme_low,
                    'type': 'LOW',
                    'time': df.iloc[extreme_low_bar]['timestamp']
                })
                current_type = 'LOW'
                current_bar = extreme_low_bar
                current_price = extreme_low
                # Reset tracking
                extreme_high = high
                extreme_high_bar = i

        # If currently at LOW, wait for significant up move to confirm HIGH
        elif current_type == 'LOW':
            up_move = ((extreme_high - current_price) / current_price) * 100
            if up_move >= min_pct:
                # Confirmed new swing HIGH
                swings.append({
                    'bar': extreme_high_bar,
                    'price': extreme_high,
                    'type': 'HIGH',
                    'time': df.iloc[extreme_high_bar]['timestamp']
                })
                current_type = 'HIGH'
                current_bar = extreme_high_bar
                current_price = extreme_high
                # Reset tracking
                extreme_low = low
                extreme_low_bar = i

    return swings

swing_points_zigzag = zigzag_indicator(df_sep, min_pct=2.0)

print("METODA 2: ZigZag (min 2% move)")
print(f"  Wykryto {len(swing_points_zigzag)} swing points")
highs_zz = [p for p in swing_points_zigzag if p['type'] == 'HIGH']
lows_zz = [p for p in swing_points_zigzag if p['type'] == 'LOW']
print(f"    - {len(highs_zz)} swing HIGHS")
print(f"    - {len(lows_zz)} swing LOWS")
print()

print("="*140)
print("RÓŻNICA:")
print(f"  Lookback=5: {len(swing_points_old)} points (HAŁAS - zbyt dużo małych peaków)")
print(f"  ZigZag 2%:  {len(swing_points_zigzag)} points (STRUKTURA - major swings)")
print(f"  Redukcja: {len(swing_points_old) - len(swing_points_zigzag)} punktów ({(1 - len(swing_points_zigzag)/len(swing_points_old))*100:.1f}%)")
print()

# ============================================
# WIZUALIZACJA: First 10 ZigZag swings
# ============================================
print("="*140)
print("ZIGZAG SWING POINTS (pierwsze 10):")
print("="*140)
print(f"{'#':<4} | {'Date':<16} | {'Type':<5} | {'Price':<10} | {'Bar':<6}")
print("-"*140)

for idx, swing in enumerate(swing_points_zigzag[:10]):
    print(f"{idx+1:<4} | {swing['time'].strftime('%m-%d %H:%M'):<16} | {swing['type']:<5} | ${swing['price']:<9.6f} | {swing['bar']:<6}")

print()

# ============================================
# TEST: Ile downtrend patterns wykryje każda metoda?
# ============================================
print("="*140)
print("DOWNTREND STRUCTURES (HIGH → LOW → lower HIGH):")
print("="*140)

def count_downtrend_patterns(swings):
    count = 0
    i = 0
    while i < len(swings) - 2:
        if swings[i]['type'] != 'HIGH':
            i += 1
            continue

        j = i + 1
        while j < len(swings) and swings[j]['type'] != 'LOW':
            j += 1
        if j >= len(swings):
            break

        k = j + 1
        while k < len(swings) and swings[k]['type'] != 'HIGH':
            k += 1
        if k >= len(swings):
            break

        if swings[k]['price'] < swings[i]['price']:
            count += 1

        i = k

    return count

patterns_old = count_downtrend_patterns(swing_points_old)
patterns_zz = count_downtrend_patterns(swing_points_zigzag)

print(f"  Lookback=5: {patterns_old} downtrend patterns")
print(f"  ZigZag 2%:  {patterns_zz} downtrend patterns")
print()

print("="*140)
print("WNIOSEK:")
print("="*140)
print(f"✅ ZigZag wykrywa {len(swing_points_zigzag)} major swings (jak na screenshocie użytkownika)")
print(f"❌ Lookback=5 wykrywa {len(swing_points_old)} swings (za dużo hałasu)")
print()
print("ZigZag indicator działa LIVE (bar-by-bar) i filtruje małe ruchy <2%")
print("Teraz używamy ZigZag w strategii structure + scaling...")
print("="*140)
