#!/usr/bin/env python3
"""
Download MOODENG/USDT 1-minute data from LBank and BingX and compare
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time
import numpy as np

def download_from_exchange(exchange_name: str, exchange_class, symbol: str, days: int = 7):
    """Download 1m candles from an exchange"""
    print(f"\n{'='*60}")
    print(f"Downloading from {exchange_name.upper()}...")
    print(f"{'='*60}")

    try:
        exchange = exchange_class({
            'enableRateLimit': True,
            'options': {'defaultType': 'swap' if exchange_name == 'bingx' else 'spot'}
        })

        # Load markets
        markets = exchange.load_markets()

        # Check symbol availability
        if symbol not in markets:
            # Try alternative symbols
            alt_symbols = [
                symbol.replace('/', ''),
                f"{symbol}:USDT",
                symbol.replace('USDT', '/USDT'),
            ]
            found = None
            for alt in alt_symbols:
                if alt in markets:
                    found = alt
                    break
            if not found:
                # List available MOODENG pairs
                moodeng_pairs = [s for s in markets.keys() if 'MOODENG' in s.upper()]
                print(f"Available MOODENG pairs: {moodeng_pairs}")
                if moodeng_pairs:
                    symbol = moodeng_pairs[0]
                else:
                    print(f"No MOODENG pair found on {exchange_name}")
                    return None
            else:
                symbol = found

        print(f"Using symbol: {symbol}")

        # Fetch OHLCV data - 7 days
        since = exchange.parse8601((datetime.utcnow() - timedelta(days=days)).isoformat())

        all_candles = []
        batch = 0

        while True:
            try:
                candles = exchange.fetch_ohlcv(
                    symbol,
                    timeframe='1m',
                    since=since,
                    limit=1000
                )

                if not candles:
                    break

                all_candles.extend(candles)
                batch += 1
                print(f"  Batch {batch}: {len(candles)} candles (total: {len(all_candles):,})")

                # Update since to last candle timestamp
                since = candles[-1][0] + 1

                # Check if we've reached current time
                if candles[-1][0] >= exchange.milliseconds() - 60000:
                    break

                time.sleep(exchange.rateLimit / 1000)

            except Exception as e:
                print(f"  Error fetching: {e}")
                break

        if not all_candles:
            print(f"No data from {exchange_name}")
            return None

        # Convert to DataFrame
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)

        print(f"\n{exchange_name.upper()} Summary:")
        print(f"  Candles: {len(df):,}")
        print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Price range: ${df['close'].min():.6f} - ${df['close'].max():.6f}")
        print(f"  Current price: ${df['close'].iloc[-1]:.6f}")
        print(f"  Avg volume: {df['volume'].mean():,.2f}")

        return df

    except Exception as e:
        print(f"Error with {exchange_name}: {e}")
        return None


def compare_data(df_lbank: pd.DataFrame, df_bingx: pd.DataFrame):
    """Compare data from two exchanges"""
    print(f"\n{'='*60}")
    print("DATA COMPARISON: LBank vs BingX")
    print(f"{'='*60}")

    # Find overlapping time range
    start = max(df_lbank['timestamp'].min(), df_bingx['timestamp'].min())
    end = min(df_lbank['timestamp'].max(), df_bingx['timestamp'].max())

    print(f"\nOverlapping period: {start} to {end}")

    # Filter to overlapping period
    lb = df_lbank[(df_lbank['timestamp'] >= start) & (df_lbank['timestamp'] <= end)].copy()
    bx = df_bingx[(df_bingx['timestamp'] >= start) & (df_bingx['timestamp'] <= end)].copy()

    print(f"LBank candles in overlap: {len(lb):,}")
    print(f"BingX candles in overlap: {len(bx):,}")

    # Merge on timestamp
    lb = lb.set_index('timestamp')
    bx = bx.set_index('timestamp')

    merged = lb.join(bx, how='inner', lsuffix='_lb', rsuffix='_bx')
    print(f"Matched candles: {len(merged):,}")

    if len(merged) == 0:
        print("No overlapping candles to compare!")
        return

    # Calculate differences
    merged['close_diff'] = merged['close_lb'] - merged['close_bx']
    merged['close_diff_pct'] = (merged['close_diff'] / merged['close_lb']) * 100
    merged['high_diff_pct'] = ((merged['high_lb'] - merged['high_bx']) / merged['high_lb']) * 100
    merged['low_diff_pct'] = ((merged['low_lb'] - merged['low_bx']) / merged['low_lb']) * 100
    merged['volume_ratio'] = merged['volume_lb'] / merged['volume_bx'].replace(0, np.nan)

    print(f"\n{'='*60}")
    print("CLOSE PRICE DIFFERENCES")
    print(f"{'='*60}")
    print(f"Mean diff: {merged['close_diff'].mean():.6f} ({merged['close_diff_pct'].mean():.4f}%)")
    print(f"Std diff: {merged['close_diff'].std():.6f} ({merged['close_diff_pct'].std():.4f}%)")
    print(f"Max diff: {merged['close_diff'].abs().max():.6f} ({merged['close_diff_pct'].abs().max():.4f}%)")
    print(f"Median diff: {merged['close_diff'].median():.6f} ({merged['close_diff_pct'].median():.4f}%)")

    print(f"\n{'='*60}")
    print("HIGH/LOW PRICE DIFFERENCES")
    print(f"{'='*60}")
    print(f"High mean diff: {merged['high_diff_pct'].mean():.4f}%")
    print(f"Low mean diff: {merged['low_diff_pct'].mean():.4f}%")

    print(f"\n{'='*60}")
    print("VOLUME COMPARISON")
    print(f"{'='*60}")
    print(f"LBank avg volume: {merged['volume_lb'].mean():,.2f}")
    print(f"BingX avg volume: {merged['volume_bx'].mean():,.2f}")
    print(f"Volume ratio (LBank/BingX): {merged['volume_ratio'].median():.2f}x")

    # Correlation
    print(f"\n{'='*60}")
    print("CORRELATION ANALYSIS")
    print(f"{'='*60}")
    close_corr = merged['close_lb'].corr(merged['close_bx'])
    volume_corr = merged['volume_lb'].corr(merged['volume_bx'])
    print(f"Close price correlation: {close_corr:.6f}")
    print(f"Volume correlation: {volume_corr:.6f}")

    # Percentile analysis of differences
    print(f"\n{'='*60}")
    print("PRICE DIFF PERCENTILES")
    print(f"{'='*60}")
    for p in [50, 75, 90, 95, 99]:
        val = merged['close_diff_pct'].abs().quantile(p/100)
        print(f"  {p}th percentile: {val:.4f}%")

    # Count significant differences
    thresholds = [0.01, 0.05, 0.1, 0.5, 1.0]
    print(f"\n{'='*60}")
    print("CANDLES WITH SIGNIFICANT PRICE DIFF")
    print(f"{'='*60}")
    for t in thresholds:
        count = (merged['close_diff_pct'].abs() > t).sum()
        pct = count / len(merged) * 100
        print(f"  >{t}% diff: {count:,} candles ({pct:.2f}%)")

    # Verdict
    print(f"\n{'='*60}")
    print("VERDICT")
    print(f"{'='*60}")

    avg_diff = merged['close_diff_pct'].abs().mean()
    max_diff = merged['close_diff_pct'].abs().max()

    if avg_diff < 0.05 and max_diff < 0.5:
        print("EXCELLENT: Data is nearly identical (<0.05% avg diff)")
        print("Backtests should be highly comparable between exchanges.")
    elif avg_diff < 0.1 and max_diff < 1.0:
        print("GOOD: Data is very similar (<0.1% avg diff)")
        print("Minor differences unlikely to affect strategy signals.")
    elif avg_diff < 0.5:
        print("ACCEPTABLE: Data has small differences (<0.5% avg diff)")
        print("Some edge cases may differ, but overall strategy should work.")
    else:
        print("CAUTION: Data has notable differences (>0.5% avg diff)")
        print("May need to validate strategy on both data sources.")

    # Save comparison results
    merged.to_csv('/workspaces/Carebiuro_windykacja/trading/results/moodeng_lbank_vs_bingx_comparison.csv')
    print(f"\nDetailed comparison saved to: trading/results/moodeng_lbank_vs_bingx_comparison.csv")

    return merged


def main():
    print("="*60)
    print("MOODENG DATA COMPARISON: LBank vs BingX")
    print("="*60)
    print(f"Date: {datetime.now()}")
    print(f"Period: Last 7 days of 1-minute data")

    # Download from LBank
    df_lbank = download_from_exchange('lbank', ccxt.lbank, 'MOODENG/USDT', days=7)

    # Download from BingX
    df_bingx = download_from_exchange('bingx', ccxt.bingx, 'MOODENG/USDT', days=7)

    # Compare if both succeeded
    if df_lbank is not None and df_bingx is not None:
        compare_data(df_lbank, df_bingx)

        # Save individual files
        df_lbank.to_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_7d_lbank.csv', index=False)
        df_bingx.to_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_7d_bingx.csv', index=False)
        print(f"\nData files saved:")
        print(f"  - trading/moodeng_7d_lbank.csv")
        print(f"  - trading/moodeng_7d_bingx.csv")
    else:
        print("\nCould not compare - missing data from one or both exchanges")
        if df_lbank is not None:
            df_lbank.to_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_7d_lbank.csv', index=False)
            print("LBank data saved to: trading/moodeng_7d_lbank.csv")
        if df_bingx is not None:
            df_bingx.to_csv('/workspaces/Carebiuro_windykacja/trading/moodeng_7d_bingx.csv', index=False)
            print("BingX data saved to: trading/moodeng_7d_bingx.csv")


if __name__ == "__main__":
    main()
