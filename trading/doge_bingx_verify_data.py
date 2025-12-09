#!/usr/bin/env python3
"""
DOGE BINGX DATA VERIFICATION
Step 1: Pre-optimization data integrity check (MANDATORY before ANY optimization)
"""
import pandas as pd
import numpy as np

# ============================================================================
# SCRIPT 1: DATA INTEGRITY CHECK
# ============================================================================

def verify_data_integrity(csv_path, expected_interval_minutes=1):
    """
    Returns: (passed: bool, report: str)
    """
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    issues = []

    # 1. Check for missing columns
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        issues.append(f"❌ MISSING COLUMNS: {missing}")

    # 2. Check for NaN/null values
    null_counts = df[required_cols].isnull().sum()
    if null_counts.sum() > 0:
        issues.append(f"❌ NULL VALUES FOUND:\n{null_counts[null_counts > 0]}")

    # 3. Check for zero/negative prices
    invalid_prices = df[(df['close'] <= 0) | (df['open'] <= 0) |
                        (df['high'] <= 0) | (df['low'] <= 0)]
    if len(invalid_prices) > 0:
        issues.append(f"❌ INVALID PRICES (<=0): {len(invalid_prices)} rows")

    # 4. Check OHLC logic (high >= low, high >= open/close, low <= open/close)
    ohlc_errors = df[(df['high'] < df['low']) |
                     (df['high'] < df['open']) | (df['high'] < df['close']) |
                     (df['low'] > df['open']) | (df['low'] > df['close'])]
    if len(ohlc_errors) > 0:
        issues.append(f"❌ OHLC LOGIC ERRORS: {len(ohlc_errors)} rows where high<low or similar")

    # 5. Check for duplicate timestamps
    duplicates = df[df['timestamp'].duplicated()]
    if len(duplicates) > 0:
        issues.append(f"❌ DUPLICATE TIMESTAMPS: {len(duplicates)} rows")

    # 6. Check for data gaps
    expected_interval = pd.Timedelta(minutes=expected_interval_minutes)
    df['time_diff'] = df['timestamp'].diff()
    gaps = df[df['time_diff'] > expected_interval * 2]  # Allow some tolerance
    if len(gaps) > 0:
        gap_pct = len(gaps) / len(df) * 100
        issues.append(f"⚠️  DATA GAPS: {len(gaps)} gaps ({gap_pct:.2f}% of data)")
        # Show largest gaps
        largest_gaps = gaps.nlargest(5, 'time_diff')[['timestamp', 'time_diff']]
        issues.append(f"   Largest gaps:\n{largest_gaps.to_string()}")

    # 7. Check for suspicious price spikes (>15% single candle)
    df['pct_change'] = df['close'].pct_change().abs()
    spikes = df[df['pct_change'] > 0.15]
    if len(spikes) > 0:
        issues.append(f"⚠️  SUSPICIOUS SPIKES (>15%): {len(spikes)} candles")
        issues.append(f"   Spike times: {spikes['timestamp'].head(10).tolist()}")

    # 8. Check data range
    date_range = df['timestamp'].max() - df['timestamp'].min()
    expected_candles = date_range.total_seconds() / (expected_interval_minutes * 60)
    actual_candles = len(df)
    completeness = actual_candles / expected_candles * 100

    if completeness < 95:
        issues.append(f"⚠️  DATA COMPLETENESS: {completeness:.1f}% (expected ~{int(expected_candles)}, got {actual_candles})")

    # Generate report
    report = f"""
================================================================================
DATA INTEGRITY REPORT: {csv_path.split('/')[-1]}
================================================================================
Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}
Total Candles: {len(df):,}
Expected Interval: {expected_interval_minutes} min
Data Completeness: {completeness:.1f}%

CHECKS:
"""

    if not issues:
        report += "✅ ALL CHECKS PASSED\n"
        return True, report
    else:
        for issue in issues:
            report += f"\n{issue}\n"
        report += "\n❌ DATA INTEGRITY CHECK FAILED - FIX BEFORE PROCEEDING\n"
        return False, report

# ============================================================================
# COMPARISON TO LBANK BASELINE
# ============================================================================

def compare_to_baseline(bingx_csv, lbank_csv):
    """Compare BingX data characteristics to LBank baseline"""

    bingx = pd.read_csv(bingx_csv)
    lbank = pd.read_csv(lbank_csv)

    bingx['timestamp'] = pd.to_datetime(bingx['timestamp'])
    lbank['timestamp'] = pd.to_datetime(lbank['timestamp'])

    # Calculate key metrics
    def calc_metrics(df, name):
        df['range'] = df['high'] - df['low']
        df['range_pct'] = df['range'] / df['close'] * 100
        df['volume_usd'] = df['volume'] * df['close']

        metrics = {
            'source': name,
            'candles': len(df),
            'days': (df['timestamp'].max() - df['timestamp'].min()).days,
            'avg_price': df['close'].mean(),
            'price_std': df['close'].std(),
            'avg_range_pct': df['range_pct'].mean(),
            'avg_volume': df['volume'].mean(),
            'avg_volume_usd': df['volume_usd'].mean(),
        }
        return metrics

    bingx_metrics = calc_metrics(bingx, 'BingX')
    lbank_metrics = calc_metrics(lbank, 'LBank')

    report = f"""
================================================================================
BINGX VS LBANK COMPARISON
================================================================================

| Metric              | BingX           | LBank           | Difference |
|---------------------|-----------------|-----------------|------------|
| Candles             | {bingx_metrics['candles']:>13,} | {lbank_metrics['candles']:>13,} | {bingx_metrics['candles'] - lbank_metrics['candles']:+,} |
| Days                | {bingx_metrics['days']:>15} | {lbank_metrics['days']:>15} | {bingx_metrics['days'] - lbank_metrics['days']:+} |
| Avg Price           | ${bingx_metrics['avg_price']:>14.5f} | ${lbank_metrics['avg_price']:>14.5f} | {(bingx_metrics['avg_price']/lbank_metrics['avg_price']-1)*100:+.2f}% |
| Price Volatility    | ${bingx_metrics['price_std']:>14.5f} | ${lbank_metrics['price_std']:>14.5f} | {(bingx_metrics['price_std']/lbank_metrics['price_std']-1)*100:+.2f}% |
| Avg Range %         | {bingx_metrics['avg_range_pct']:>14.3f}% | {lbank_metrics['avg_range_pct']:>14.3f}% | {bingx_metrics['avg_range_pct'] - lbank_metrics['avg_range_pct']:+.3f}% |
| Avg Volume          | {bingx_metrics['avg_volume']:>13,.0f} | {lbank_metrics['avg_volume']:>13,.0f} | {(bingx_metrics['avg_volume']/lbank_metrics['avg_volume']-1)*100:+.1f}% |
| Avg Volume USD      | ${bingx_metrics['avg_volume_usd']:>13,.0f} | ${lbank_metrics['avg_volume_usd']:>13,.0f} | {(bingx_metrics['avg_volume_usd']/lbank_metrics['avg_volume_usd']-1)*100:+.1f}% |

KEY DIFFERENCES:
"""

    warnings = []

    # Check for major differences
    price_diff = abs(bingx_metrics['avg_price'] / lbank_metrics['avg_price'] - 1)
    if price_diff > 0.05:
        warnings.append(f"⚠️  Average price differs by {price_diff*100:.1f}% - check if same time period")

    vol_diff = abs(bingx_metrics['price_std'] / lbank_metrics['price_std'] - 1)
    if vol_diff > 0.20:
        warnings.append(f"⚠️  Volatility differs by {vol_diff*100:.1f}% - market conditions may be different")

    range_diff = abs(bingx_metrics['avg_range_pct'] - lbank_metrics['avg_range_pct'])
    if range_diff > 0.1:
        warnings.append(f"⚠️  Average range differs by {range_diff:.3f}% - liquidity may be different")

    if warnings:
        for w in warnings:
            report += f"\n{w}"
        report += "\n\n⚠️  SIGNIFICANT DIFFERENCES - Strategy performance may vary from baseline\n"
    else:
        report += "\n✅ Data characteristics similar - strategy should transfer well\n"

    return report

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("DOGE BINGX DATA VERIFICATION")
    print("=" * 80)
    print()

    # Step 1: Data Integrity
    print("Step 1: Checking BingX data integrity...")
    passed, integrity_report = verify_data_integrity('./trading/doge_30d_bingx.csv')
    print(integrity_report)

    if not passed:
        print("\n🛑 STOP: Fix data integrity issues before proceeding!")
        exit(1)

    # Step 2: Compare to LBank baseline
    print("\nStep 2: Comparing to LBank baseline...")
    comparison_report = compare_to_baseline('./trading/doge_30d_bingx.csv', './trading/doge_usdt_1m_lbank.csv')
    print(comparison_report)

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print("✅ Data integrity check: PASSED")
    print("✅ BingX vs LBank comparison: COMPLETE")
    print("\n✅ Data verified - ready for strategy backtesting")
    print("=" * 80)
