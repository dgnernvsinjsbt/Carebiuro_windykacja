"""
FARTCOIN BingX Data Verification Script
Checks for gaps, duplicates, OHLC errors, and data corruption
Based on prompt 013 verification framework
"""

import pandas as pd
import numpy as np
from datetime import timedelta

def verify_fartcoin_bingx_data(filepath):
    """Run all data integrity checks"""

    print("=" * 80)
    print("FARTCOIN BINGX DATA VERIFICATION REPORT")
    print("=" * 80)

    # Load data
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f"\n1. BASIC STATISTICS")
    print(f"   Total rows: {len(df):,}")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
    print(f"   Expected rows (1-min): {(df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 60:.0f}")

    # Check for duplicates
    print(f"\n2. DUPLICATE TIMESTAMP CHECK")
    duplicates = df[df.duplicated(subset=['timestamp'], keep=False)]
    if len(duplicates) > 0:
        print(f"   ❌ FOUND {len(duplicates)} DUPLICATE TIMESTAMPS!")
        print(f"   First 10 duplicates:")
        print(duplicates.head(10)[['timestamp', 'open', 'close', 'volume']])
    else:
        print(f"   ✅ No duplicate timestamps")

    # Check for gaps
    print(f"\n3. GAP DETECTION")
    df['time_diff'] = df['timestamp'].diff()
    gaps = df[df['time_diff'] > timedelta(minutes=1)]

    if len(gaps) > 0:
        print(f"   ⚠️  FOUND {len(gaps)} GAPS (>1 minute)")
        total_missing = 0
        for idx, row in gaps.head(20).iterrows():
            gap_minutes = row['time_diff'].total_seconds() / 60
            missing_candles = int(gap_minutes - 1)
            total_missing += missing_candles
            print(f"   Gap at {row['timestamp']}: {gap_minutes:.0f} min ({missing_candles} missing candles)")

        if len(gaps) > 20:
            print(f"   ... and {len(gaps) - 20} more gaps")
        print(f"   Total missing candles: {total_missing:,}")
    else:
        print(f"   ✅ No gaps detected")

    # Check OHLC integrity
    print(f"\n4. OHLC INTEGRITY CHECK")

    # High should be >= max(open, close)
    invalid_high = df[df['high'] < df[['open', 'close']].max(axis=1)]
    if len(invalid_high) > 0:
        print(f"   ❌ {len(invalid_high)} candles with HIGH < max(OPEN, CLOSE)")
        print(f"   Sample:")
        print(invalid_high.head(5)[['timestamp', 'open', 'high', 'low', 'close']])
    else:
        print(f"   ✅ All HIGH values valid")

    # Low should be <= min(open, close)
    invalid_low = df[df['low'] > df[['open', 'close']].min(axis=1)]
    if len(invalid_low) > 0:
        print(f"   ❌ {len(invalid_low)} candles with LOW > min(OPEN, CLOSE)")
        print(f"   Sample:")
        print(invalid_low.head(5)[['timestamp', 'open', 'high', 'low', 'close']])
    else:
        print(f"   ✅ All LOW values valid")

    # High >= Low
    invalid_hl = df[df['high'] < df['low']]
    if len(invalid_hl) > 0:
        print(f"   ❌ {len(invalid_hl)} candles with HIGH < LOW")
        print(invalid_hl[['timestamp', 'open', 'high', 'low', 'close']])
    else:
        print(f"   ✅ All HIGH >= LOW")

    # Check for zeros
    print(f"\n5. ZERO VALUE CHECK")
    zero_prices = df[(df['open'] == 0) | (df['high'] == 0) | (df['low'] == 0) | (df['close'] == 0)]
    if len(zero_prices) > 0:
        print(f"   ❌ {len(zero_prices)} candles with ZERO prices")
        print(zero_prices[['timestamp', 'open', 'high', 'low', 'close']])
    else:
        print(f"   ✅ No zero prices")

    zero_volume = df[df['volume'] == 0]
    print(f"   Zero volume candles: {len(zero_volume)} ({len(zero_volume)/len(df)*100:.2f}%)")

    # Check for NaN
    print(f"\n6. MISSING VALUE CHECK")
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print(f"   ❌ FOUND MISSING VALUES:")
        print(missing[missing > 0])
    else:
        print(f"   ✅ No missing values")

    # Price consistency check
    print(f"\n7. PRICE CONSISTENCY")
    df['price_range'] = df['high'] - df['low']
    df['range_pct'] = (df['price_range'] / df['close']) * 100

    print(f"   Average range: {df['price_range'].mean():.6f} ({df['range_pct'].mean():.3f}%)")
    print(f"   Median range: {df['price_range'].median():.6f} ({df['range_pct'].median():.3f}%)")
    print(f"   Max range: {df['price_range'].max():.6f} ({df['range_pct'].max():.3f}%)")

    extreme_ranges = df[df['range_pct'] > 10]
    if len(extreme_ranges) > 0:
        print(f"   ⚠️  {len(extreme_ranges)} candles with >10% range (possible errors)")
        print(extreme_ranges.head(10)[['timestamp', 'open', 'high', 'low', 'close', 'range_pct']])
    else:
        print(f"   ✅ No extreme ranges detected")

    # Volume analysis
    print(f"\n8. VOLUME ANALYSIS")
    print(f"   Average volume: {df['volume'].mean():,.2f}")
    print(f"   Median volume: {df['volume'].median():,.2f}")
    print(f"   Max volume: {df['volume'].max():,.2f}")
    print(f"   Min volume (non-zero): {df[df['volume'] > 0]['volume'].min():,.2f}")

    # Price continuity check
    print(f"\n9. PRICE CONTINUITY CHECK")
    df['price_change'] = df['close'].diff().abs()
    df['price_change_pct'] = (df['price_change'] / df['close'].shift(1)) * 100

    print(f"   Average 1-min change: {df['price_change_pct'].mean():.3f}%")
    print(f"   Median 1-min change: {df['price_change_pct'].median():.3f}%")
    print(f"   Max 1-min change: {df['price_change_pct'].max():.3f}%")

    large_jumps = df[df['price_change_pct'] > 5]
    if len(large_jumps) > 0:
        print(f"   ⚠️  {len(large_jumps)} candles with >5% jump (possible gaps/errors)")
        print(large_jumps.head(10)[['timestamp', 'close', 'price_change_pct']])
    else:
        print(f"   ✅ No extreme jumps detected")

    # Final verdict
    print(f"\n" + "=" * 80)
    print("VERIFICATION VERDICT")
    print("=" * 80)

    issues = []
    if len(duplicates) > 0:
        issues.append(f"❌ {len(duplicates)} duplicate timestamps")
    if len(gaps) > 0:
        issues.append(f"⚠️  {len(gaps)} gaps in data")
    if len(invalid_high) > 0:
        issues.append(f"❌ {len(invalid_high)} invalid HIGH values")
    if len(invalid_low) > 0:
        issues.append(f"❌ {len(invalid_low)} invalid LOW values")
    if len(invalid_hl) > 0:
        issues.append(f"❌ {len(invalid_hl)} HIGH < LOW violations")
    if len(zero_prices) > 0:
        issues.append(f"❌ {len(zero_prices)} zero prices")
    if missing.sum() > 0:
        issues.append(f"❌ Missing values detected")
    if len(extreme_ranges) > 0:
        issues.append(f"⚠️  {len(extreme_ranges)} extreme price ranges")
    if len(large_jumps) > 0:
        issues.append(f"⚠️  {len(large_jumps)} large price jumps")

    if len(issues) == 0:
        print("✅ DATA IS CLEAN - Ready for backtesting")
    else:
        print("Issues found:")
        for issue in issues:
            print(f"   {issue}")

        if any("❌" in issue for issue in issues):
            print("\n⚠️  CRITICAL ERRORS DETECTED - DO NOT PROCEED WITH OPTIMIZATION")
        else:
            print("\n⚠️  Minor issues detected - Proceed with caution")

    return df

if __name__ == "__main__":
    filepath = "/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv"
    df = verify_fartcoin_bingx_data(filepath)

    # Save cleaned data
    print(f"\nData verification complete. Shape: {df.shape}")
