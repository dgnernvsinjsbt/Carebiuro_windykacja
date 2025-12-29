#!/usr/bin/env python3
"""Download FARTCOIN 1h data for entire year 2025"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time

base_url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"

# Year 2025: Jan 1 to Dec 29
start_date = datetime(2025, 1, 1)
end_date = datetime(2025, 12, 29, 23, 59, 59)

# Calculate batches - each batch gets 1440 candles (60 days of 1h data)
# We need ~6-7 batches to cover full year
num_batches = 7
batch_duration = timedelta(days=60)

# Create end times for each batch, working backwards from end_date
end_times = []
current_end = end_date
for i in range(num_batches):
    end_times.append(int(current_end.timestamp() * 1000))
    current_end -= batch_duration

def fetch_batch(symbol, end_time):
    params = {"symbol": symbol, "interval": "1h", "endTime": end_time, "limit": 1440}
    try:
        response = requests.get(base_url, params=params, timeout=30)
        data = response.json().get('data', [])
        print(f"  Batch ending {datetime.fromtimestamp(end_time/1000)}: {len(data)} candles")
        return data
    except Exception as e:
        print(f"  Error: {e}")
        return []

def download_fartcoin():
    symbol = "FARTCOIN-USDT"
    print(f"\nDownloading {symbol} 1h data (full year 2025)...")
    print(f"Date range: {start_date} to {end_date}")
    start = time.time()

    with ThreadPoolExecutor(max_workers=7) as executor:
        results = list(executor.map(lambda et: fetch_batch(symbol, et), end_times))

    all_data = []
    for batch in results:
        all_data.extend(batch)

    if not all_data:
        print(f"❌ {symbol}: No data")
        return None

    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['time'].astype(int), unit='ms')

    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Filter to year 2025 only
    df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]

    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)

    elapsed = time.time() - start

    output_path = 'fartcoin_1h_2025.csv'
    df.to_csv(output_path, index=False)

    print(f"\n✅ {symbol}: {len(df):,} candles in {elapsed:.1f}s")
    print(f"   Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Price: ${df['close'].min():.6f} - ${df['close'].max():.6f}")
    print(f"   Expected: ~8,760 candles (365 days × 24 hours)")
    print(f"   File: {output_path}")

    return df

if __name__ == "__main__":
    print("=" * 80)
    download_fartcoin()
    print("=" * 80)
