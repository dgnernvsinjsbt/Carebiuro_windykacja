#!/usr/bin/env python3
"""
Validate 9 downloaded coin datasets for gaps, errors, and consistency
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

COINS = [
    'piusdt', 'btcusdt', 'ethusdt', 'trumpsolusdt',
    'crvusdt', 'penguusdt', 'uniusdt', 'aixbtusdt', '1000pepeusdt'
]

print("="*100)
print("DATA VALIDATION - 9 COINS x 6 MONTHS x 15m")
print("="*100)
print()

all_valid = True
issues = []

for coin in COINS:
    filename = f"{coin}_6months_bingx_15m.csv"
    print(f"{'='*100}")
    print(f"📊 {coin.upper()}")
    print(f"{'='*100}")

    try:
        df = pd.read_csv(filename)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # 1. Basic stats
        print(f"\n✅ File loaded: {len(df)} candles")
        print(f"   Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
        print(f"   Period: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

        # 2. Check for timestamp gaps
        df['time_diff'] = df['timestamp'].diff()
        expected_diff = timedelta(minutes=15)
        gaps = df[df['time_diff'] > expected_diff]

        if len(gaps) > 0:
            all_valid = False
            print(f"\n⚠️  GAPS FOUND: {len(gaps)} missing intervals")
            for idx, row in gaps.head(5).iterrows():
                prev_time = df.iloc[idx-1]['timestamp']
                curr_time = row['timestamp']
                gap_minutes = (curr_time - prev_time).total_seconds() / 60
                print(f"      {prev_time} → {curr_time} (gap: {gap_minutes:.0f} min)")
                issues.append(f"{coin}: {len(gaps)} gaps")
        else:
            print(f"\n✅ No timestamp gaps - perfect 15m intervals")

        # 3. Check for duplicate timestamps
        dupes = df[df.duplicated(subset=['timestamp'], keep=False)]
        if len(dupes) > 0:
            all_valid = False
            print(f"\n❌ DUPLICATES: {len(dupes)} duplicate timestamps")
            issues.append(f"{coin}: {len(dupes)} duplicates")
        else:
            print(f"✅ No duplicate timestamps")

        # 4. Check OHLCV validity
        errors = []

        # Check for zeros
        zero_open = (df['open'] == 0).sum()
        zero_high = (df['high'] == 0).sum()
        zero_low = (df['low'] == 0).sum()
        zero_close = (df['close'] == 0).sum()

        if zero_open > 0 or zero_high > 0 or zero_low > 0 or zero_close > 0:
            all_valid = False
            errors.append(f"Zero prices: O={zero_open} H={zero_high} L={zero_low} C={zero_close}")

        # Check OHLC logic: high >= low, high >= open, high >= close, etc.
        invalid_high_low = (df['high'] < df['low']).sum()
        invalid_high_open = (df['high'] < df['open']).sum()
        invalid_high_close = (df['high'] < df['close']).sum()
        invalid_low_open = (df['low'] > df['open']).sum()
        invalid_low_close = (df['low'] > df['close']).sum()

        if invalid_high_low > 0:
            all_valid = False
            errors.append(f"High < Low: {invalid_high_low} candles")
        if invalid_high_open > 0:
            all_valid = False
            errors.append(f"High < Open: {invalid_high_open} candles")
        if invalid_high_close > 0:
            all_valid = False
            errors.append(f"High < Close: {invalid_high_close} candles")
        if invalid_low_open > 0:
            all_valid = False
            errors.append(f"Low > Open: {invalid_low_open} candles")
        if invalid_low_close > 0:
            all_valid = False
            errors.append(f"Low > Close: {invalid_low_close} candles")

        # Check for extreme price spikes (> 50% from previous close)
        df['price_change_pct'] = (df['close'] - df['close'].shift(1)).abs() / df['close'].shift(1) * 100
        extreme_moves = df[df['price_change_pct'] > 50]

        if len(extreme_moves) > 0:
            print(f"\n⚠️  EXTREME MOVES: {len(extreme_moves)} candles with >50% price change")
            for idx, row in extreme_moves.head(3).iterrows():
                prev_close = df.iloc[idx-1]['close']
                curr_close = row['close']
                change_pct = row['price_change_pct']
                print(f"      {row['timestamp']}: ${prev_close:.4f} → ${curr_close:.4f} ({change_pct:+.1f}%)")
            # Don't mark as invalid - meme coins can have extreme moves

        # Check volume
        zero_volume = (df['volume'] == 0).sum()
        if zero_volume > 0:
            print(f"\n⚠️  Zero volume: {zero_volume} candles ({zero_volume/len(df)*100:.1f}%)")
            # Don't mark as invalid - some candles can have zero volume

        if errors:
            all_valid = False
            print(f"\n❌ DATA ERRORS:")
            for err in errors:
                print(f"      {err}")
                issues.append(f"{coin}: {err}")
        else:
            print(f"✅ OHLCV data valid")

        # 5. Statistical summary
        print(f"\n📈 Price Statistics:")
        print(f"   Min: ${df['close'].min():.6f}")
        print(f"   Max: ${df['close'].max():.6f}")
        print(f"   Mean: ${df['close'].mean():.6f}")
        print(f"   Std: ${df['close'].std():.6f}")

        print(f"\n📊 Volume Statistics:")
        print(f"   Mean: {df['volume'].mean():.2f}")
        print(f"   Zero volume candles: {zero_volume} ({zero_volume/len(df)*100:.1f}%)")

        # 6. ATR verification
        if 'atr_pct' in df.columns:
            avg_atr_pct = df['atr_pct'].mean()
            print(f"\n📐 ATR: {avg_atr_pct:.3f}% (verified)")

    except Exception as e:
        all_valid = False
        print(f"\n❌ ERROR loading file: {e}")
        issues.append(f"{coin}: Failed to load - {e}")

    print()

# Summary
print("="*100)
print("📋 VALIDATION SUMMARY")
print("="*100)
print()

if all_valid:
    print("✅ ALL DATA VALID - No issues found!")
    print()
    print("Safe to proceed with backtesting.")
else:
    print("⚠️  ISSUES FOUND:")
    print()
    for issue in issues:
        print(f"   • {issue}")
    print()
    print("Review issues above before backtesting.")

print("="*100)
