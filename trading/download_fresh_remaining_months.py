"""
Download fresh Sep-Dec 2025 data from BingX API
Verify completeness and save each month separately
"""
import pandas as pd
import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

months = [
    ('September', datetime(2025, 9, 1, tzinfo=timezone.utc), datetime(2025, 9, 30, 23, 59, tzinfo=timezone.utc), 'melania_september_2025_15m_fresh.csv'),
    ('October', datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2025, 10, 31, 23, 59, tzinfo=timezone.utc), 'melania_october_2025_15m_fresh.csv'),
    ('November', datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2025, 11, 30, 23, 59, tzinfo=timezone.utc), 'melania_november_2025_15m_fresh.csv'),
    ('December', datetime(2025, 12, 1, tzinfo=timezone.utc), datetime(2025, 12, 15, 23, 59, tzinfo=timezone.utc), 'melania_december_2025_15m_fresh.csv'),
]

all_results = []

for month_name, start, end, filename in months:
    print('=' * 100)
    print(f'DOWNLOADING FRESH {month_name.upper()} 2025 DATA FROM BINGX')
    print('=' * 100)

    start_ts = int(start.timestamp() * 1000)
    end_ts = int(end.timestamp() * 1000)

    print(f'\nDownloading: {start.date()} to {end.date()}')
    print(f'Timeframe: 15m')
    print(f'Symbol: MELANIA-USDT')
    print()

    all_candles = []
    current_ts = start_ts
    errors = 0

    while current_ts < end_ts:
        try:
            candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
            if not candles:
                print(f'\n⚠️  No more candles returned at timestamp {current_ts}')
                break

            all_candles.extend(candles)
            current_ts = candles[-1][0] + (15 * 60 * 1000)
            print(f'Downloaded {len(all_candles)} candles...', end='\r')
            time.sleep(0.5)

        except Exception as e:
            errors += 1
            print(f'\n⚠️  Error #{errors}: {e}')
            if errors > 10:
                print(f'\n❌ Too many errors, stopping.')
                break
            print(f'Retrying in 2 seconds...')
            time.sleep(2)
            continue

    print(f'\n\nTotal downloaded: {len(all_candles)} raw candles')

    # Convert to DataFrame
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)

    # Filter to exact date range
    df = df[(df['timestamp'] >= start.replace(tzinfo=None)) &
            (df['timestamp'] <= end.replace(tzinfo=None))].copy()
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f'\nFiltered to {month_name} 2025: {len(df)} bars')
    print(f'Date range: {df["timestamp"].min()} to {df["timestamp"].max()}')

    # Verify data quality
    print('\n' + '=' * 100)
    print('DATA QUALITY CHECKS')
    print('=' * 100)

    # 1. Check for duplicates
    duplicates = df.duplicated(subset=['timestamp']).sum()
    print(f'\n1. Duplicates: {duplicates}')
    if duplicates > 0:
        print(f'   ⚠️  Found {duplicates} duplicate timestamps!')
        df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
        print(f'   Removed duplicates, now {len(df)} bars')
    else:
        print(f'   ✅ No duplicates')

    # 2. Check for gaps
    df_sorted = df.sort_values('timestamp').reset_index(drop=True)
    time_diffs = df_sorted['timestamp'].diff()
    expected_diff = pd.Timedelta(minutes=15)
    gaps = time_diffs[time_diffs > expected_diff]

    print(f'\n2. Gaps (missing bars):')
    if len(gaps) > 0:
        print(f'   ⚠️  Found {len(gaps)} gaps in data')
        for idx in gaps.index[:5]:  # Show first 5
            prev_time = df_sorted.iloc[idx-1]['timestamp']
            curr_time = df_sorted.iloc[idx]['timestamp']
            gap_minutes = (curr_time - prev_time).total_seconds() / 60
            print(f'      Gap at {curr_time}: {gap_minutes:.0f} minutes missing')
        if len(gaps) > 5:
            print(f'      ... and {len(gaps) - 5} more gaps')
    else:
        print(f'   ✅ No gaps - continuous data')

    # 3. Expected bars
    month_minutes = (end.replace(tzinfo=None) - start.replace(tzinfo=None)).total_seconds() / 60
    expected_bars = int(month_minutes / 15)

    # For December, calculate days properly (Dec 1-15)
    if month_name == 'December':
        days = 15
    else:
        days = (end.replace(tzinfo=None) - start.replace(tzinfo=None)).days + 1

    print(f'\n3. Expected bars: ~{expected_bars} ({days} days)')
    print(f'   Actual bars: {len(df)}')
    coverage = (len(df) / expected_bars) * 100 if expected_bars > 0 else 0
    print(f'   Coverage: {coverage:.1f}%')
    if coverage < 95:
        print(f'   ⚠️  Less than 95% coverage')
    else:
        print(f'   ✅ Good coverage')

    # 4. Price sanity checks
    print(f'\n4. Price range:')
    print(f'   Low: ${df["low"].min():.6f}')
    print(f'   High: ${df["high"].max():.6f}')
    print(f'   First close: ${df.iloc[0]["close"]:.6f}')
    print(f'   Last close: ${df.iloc[-1]["close"]:.6f}')

    # Check for zeros or invalid prices
    zero_prices = (df['close'] == 0).sum()
    if zero_prices > 0:
        print(f'   ❌ Found {zero_prices} bars with zero close price!')
    else:
        print(f'   ✅ No zero prices')

    # Save
    df.to_csv(filename, index=False)

    print('\n' + '=' * 100)
    print('SUMMARY')
    print('=' * 100)
    print(f'\n✅ Downloaded {len(df)} bars for {month_name} 2025')
    print(f'✅ Saved to: {filename}')
    print(f'✅ Date range: {df["timestamp"].min()} to {df["timestamp"].max()}')
    print(f'✅ Coverage: {coverage:.1f}%')

    quality = 'EXCELLENT'
    if duplicates > 0 or len(gaps) > 0 or coverage < 95 or zero_prices > 0:
        if coverage > 90:
            quality = 'GOOD'
        else:
            quality = 'POOR'

    if quality == 'EXCELLENT':
        print(f'\n🎉 DATA QUALITY: EXCELLENT')
    elif quality == 'GOOD':
        print(f'\n⚠️  DATA QUALITY: GOOD (minor issues)')
    else:
        print(f'\n❌ DATA QUALITY: POOR (needs review)')

    all_results.append({
        'month': month_name,
        'bars': len(df),
        'coverage': coverage,
        'gaps': len(gaps),
        'quality': quality,
        'filename': filename
    })

    print('\n\n')

# Final summary
print('=' * 100)
print('FINAL SUMMARY - ALL MONTHS')
print('=' * 100)

for result in all_results:
    status = '🎉' if result['quality'] == 'EXCELLENT' else ('⚠️' if result['quality'] == 'GOOD' else '❌')
    print(f"{status} {result['month']:<10} {result['bars']:>4} bars, {result['coverage']:>5.1f}% coverage, {result['gaps']} gaps - {result['quality']}")

print('\nAll files saved successfully!')
