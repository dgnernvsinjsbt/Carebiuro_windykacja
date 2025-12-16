"""
Download MELANIA-USDT 15m data for ALL of 2025
Month by month (Jan-Dec)
"""
import ccxt
import pandas as pd
from datetime import datetime, timezone
import time

def download_month(month_num, year=2025):
    """Download fresh data for a specific month"""
    exchange = ccxt.bingx({'enableRateLimit': True})

    # Calculate date range
    if month_num == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month_num + 1
        next_year = year

    start = datetime(year, month_num, 1, tzinfo=timezone.utc)
    end = datetime(next_year, next_month, 1, tzinfo=timezone.utc)

    start_ts = int(start.timestamp() * 1000)
    end_ts = int(end.timestamp() * 1000)

    all_candles = []
    current_ts = start_ts

    print(f'Downloading {start.strftime("%B %Y")}...')

    while current_ts < end_ts:
        try:
            candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
            if not candles:
                break

            all_candles.extend(candles)
            current_ts = candles[-1][0] + (15 * 60 * 1000)
            time.sleep(0.5)

        except Exception as e:
            if 'not found' in str(e).lower() or 'too wide' in str(e).lower():
                print(f'  ⚠️  Data not available (too old or unavailable)')
                return None
            else:
                print(f'  Error: {e}')
                time.sleep(2)
                continue

    if not all_candles:
        return None

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= start.replace(tzinfo=None)) &
            (df['timestamp'] < end.replace(tzinfo=None))].copy()
    df = df.sort_values('timestamp').reset_index(drop=True)

    return df

print('=' * 80)
print('DOWNLOADING ALL MELANIA-USDT 2025 DATA (15m timeframe)')
print('=' * 80)

month_names = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

downloaded = []
unavailable = []

for month_num, month_name in enumerate(month_names, 1):
    df = download_month(month_num)

    if df is not None and len(df) > 0:
        filename = f'melania_{month_name.lower()}_2025_15m.csv'
        df.to_csv(filename, index=False)
        downloaded.append((month_name, filename, len(df)))
        print(f'  ✅ Saved: {filename} ({len(df)} bars)\n')
    else:
        unavailable.append(month_name)
        print(f'  ❌ Not available\n')

print('=' * 80)
print('DOWNLOAD SUMMARY')
print('=' * 80)

if downloaded:
    print(f'\n✅ DOWNLOADED ({len(downloaded)} months):')
    for month, filename, bars in downloaded:
        print(f'   {month:12} → {filename:40} ({bars:5} bars)')

if unavailable:
    print(f'\n❌ UNAVAILABLE ({len(unavailable)} months):')
    for month in unavailable:
        print(f'   {month}')

print(f'\n📊 Total: {len(downloaded)}/{len(month_names)} months available')
print('=' * 80)
