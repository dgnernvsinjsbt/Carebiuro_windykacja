#!/usr/bin/env python3
"""
MOODENG BingX Data Verification - Step 1 of Master Optimization Framework
Verifies data integrity before running optimizations
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def verify_moodeng_bingx_data():
    """Run all 5 verification checks on MOODENG BingX data"""

    print("="*80)
    print("MOODENG BINGX DATA VERIFICATION")
    print("="*80)

    # Load data
    df = pd.read_csv('./trading/moodeng_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f"\n1. BASIC STATISTICS")
    print(f"   Total candles: {len(df):,}")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

    # Check 1: Missing timestamps
    print(f"\n2. MISSING TIMESTAMPS CHECK")
    df['time_diff'] = df['timestamp'].diff()
    expected_diff = timedelta(minutes=1)
    gaps = df[df['time_diff'] > expected_diff]

    if len(gaps) > 0:
        print(f"   ⚠️  Found {len(gaps)} gaps in timestamps:")
        for idx, row in gaps.head(10).iterrows():
            gap_size = (row['time_diff'].total_seconds() / 60) - 1
            print(f"      Gap at {row['timestamp']}: {gap_size:.0f} missing candles")
    else:
        print(f"   ✅ No gaps found - perfect 1-minute intervals")

    # Check 2: Price anomalies
    print(f"\n3. PRICE ANOMALY CHECK")
    df['pct_change'] = df['close'].pct_change() * 100
    df['wick_upper'] = ((df['high'] - df[['open', 'close']].max(axis=1)) / df['close']) * 100
    df['wick_lower'] = ((df[['open', 'close']].min(axis=1) - df['low']) / df['close']) * 100

    extreme_moves = df[abs(df['pct_change']) > 10]
    extreme_wicks = df[(df['wick_upper'] > 5) | (df['wick_lower'] > 5)]

    print(f"   Price change stats:")
    print(f"      Mean: {df['pct_change'].mean():.3f}%")
    print(f"      Std: {df['pct_change'].std():.3f}%")
    print(f"      Max: {df['pct_change'].max():.3f}%")
    print(f"      Min: {df['pct_change'].min():.3f}%")

    if len(extreme_moves) > 0:
        print(f"   ⚠️  {len(extreme_moves)} extreme price moves (>10%):")
        for idx, row in extreme_moves.head(5).iterrows():
            print(f"      {row['timestamp']}: {row['pct_change']:.2f}%")
    else:
        print(f"   ✅ No extreme price moves detected")

    if len(extreme_wicks) > 0:
        print(f"   ⚠️  {len(extreme_wicks)} candles with extreme wicks (>5%):")
        for idx, row in extreme_wicks.head(5).iterrows():
            print(f"      {row['timestamp']}: upper={row['wick_upper']:.2f}%, lower={row['wick_lower']:.2f}%")
    else:
        print(f"   ✅ No extreme wicks detected")

    # Check 3: Volume anomalies
    print(f"\n4. VOLUME ANOMALY CHECK")
    df['volume_zscore'] = (df['volume'] - df['volume'].mean()) / df['volume'].std()
    volume_outliers = df[df['volume_zscore'].abs() > 5]

    print(f"   Volume stats:")
    print(f"      Mean: {df['volume'].mean():,.0f}")
    print(f"      Median: {df['volume'].median():,.0f}")
    print(f"      Max: {df['volume'].max():,.0f}")
    print(f"      Min: {df['volume'].min():,.0f}")

    if len(volume_outliers) > 0:
        print(f"   ⚠️  {len(volume_outliers)} volume outliers (>5 std dev):")
        for idx, row in volume_outliers.head(5).iterrows():
            print(f"      {row['timestamp']}: {row['volume']:,.0f} (z={row['volume_zscore']:.2f})")
    else:
        print(f"   ✅ No extreme volume outliers")

    # Check 4: OHLC consistency
    print(f"\n5. OHLC CONSISTENCY CHECK")
    invalid_high = df[df['high'] < df[['open', 'close']].max(axis=1)]
    invalid_low = df[df['low'] > df[['open', 'close']].min(axis=1)]
    invalid_ohlc = len(invalid_high) + len(invalid_low)

    if invalid_ohlc > 0:
        print(f"   ❌ CRITICAL: {invalid_ohlc} candles with invalid OHLC relationships!")
        if len(invalid_high) > 0:
            print(f"      {len(invalid_high)} candles where high < max(open,close)")
        if len(invalid_low) > 0:
            print(f"      {len(invalid_low)} candles where low > min(open,close)")
    else:
        print(f"   ✅ All OHLC relationships valid")

    # Check 5: Compare to LBank wicks (critical for understanding SL differences)
    print(f"\n6. WICK ANALYSIS (BingX vs LBank)")
    df['body'] = abs(df['close'] - df['open']) / df['open'] * 100

    print(f"   Average wick sizes:")
    print(f"      Upper wick: {df['wick_upper'].mean():.3f}%")
    print(f"      Lower wick: {df['wick_lower'].mean():.3f}%")
    print(f"      Body size: {df['body'].mean():.3f}%")

    print(f"\n   Wick distribution:")
    print(f"      90th percentile upper wick: {df['wick_upper'].quantile(0.9):.3f}%")
    print(f"      90th percentile lower wick: {df['wick_lower'].quantile(0.9):.3f}%")

    # Critical insight: count how many candles have large wicks
    large_wicks = df[(df['wick_upper'] > 0.5) | (df['wick_lower'] > 0.5)]
    print(f"\n   Candles with wicks >0.5%: {len(large_wicks)} ({len(large_wicks)/len(df)*100:.1f}%)")

    print(f"\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)

    # Summary
    issues = []
    if len(gaps) > 0:
        issues.append(f"{len(gaps)} timestamp gaps")
    if len(extreme_moves) > 0:
        issues.append(f"{len(extreme_moves)} extreme price moves")
    if invalid_ohlc > 0:
        issues.append(f"{invalid_ohlc} OHLC consistency errors")

    if len(issues) == 0:
        print("\n✅ DATA QUALITY: EXCELLENT - Ready for optimization")
    else:
        print(f"\n⚠️  DATA QUALITY: {len(issues)} issues found:")
        for issue in issues:
            print(f"   - {issue}")
        print("\nRecommendation: Review and clean data before optimization")

    return df

if __name__ == '__main__':
    df = verify_moodeng_bingx_data()
