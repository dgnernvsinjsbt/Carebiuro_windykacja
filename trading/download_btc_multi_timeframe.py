#!/usr/bin/env python3
"""Download BTC data - 3 months, multiple timeframes (1m, 5m, 15m, 1h)"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time

def download_timeframe(interval, days=90):
    """Download data for specific timeframe"""

    print(f"\nDownloading {interval} data...")

    base_url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"

    # Calculate batches based on interval
    if interval == "1m":
        candles_per_batch = 1440  # 1 day
        num_batches = days
    elif interval == "5m":
        candles_per_batch = 1440  # ~5 days
        num_batches = days // 5 + 1
    elif interval == "15m":
        candles_per_batch = 1440  # ~15 days
        num_batches = days // 15 + 1
    elif interval == "1h":
        candles_per_batch = 1440  # ~60 days
        num_batches = days // 60 + 1

    now = datetime.now()

    # Calculate end times for batches
    if interval == "1m":
        end_times = [int((now - timedelta(minutes=i*1440)).timestamp() * 1000) for i in range(num_batches)]
    elif interval == "5m":
        end_times = [int((now - timedelta(minutes=i*1440*5)).timestamp() * 1000) for i in range(num_batches)]
    elif interval == "15m":
        end_times = [int((now - timedelta(minutes=i*1440*15)).timestamp() * 1000) for i in range(num_batches)]
    elif interval == "1h":
        end_times = [int((now - timedelta(hours=i*1440)).timestamp() * 1000) for i in range(num_batches)]

    def fetch_batch(end_time):
        params = {"symbol": "BTC-USDT", "interval": interval, "endTime": end_time, "limit": 1440}
        try:
            response = requests.get(base_url, params=params, timeout=30)
            return response.json().get('data', [])
        except:
            return []

    start = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_batch, end_times))

    elapsed = time.time() - start

    # Combine data
    all_data = []
    for batch in results:
        all_data.extend(batch)

    if not all_data:
        print(f"  ❌ No data for {interval}")
        return None

    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['time'].astype(int), unit='ms')

    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Filter to exactly 90 days
    cutoff = datetime.now() - timedelta(days=days)
    df = df[df['timestamp'] >= cutoff]

    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)

    # Save
    output_path = f'/workspaces/Carebiuro_windykacja/trading/btc_{interval}_90d.csv'
    df.to_csv(output_path, index=False)

    print(f"  ✅ {interval}: {len(df):,} candles in {elapsed:.1f}s")
    print(f"     Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"     File: btc_{interval}_90d.csv")

    return df

print("=" * 80)
print("DOWNLOADING BTC MULTI-TIMEFRAME DATA (90 DAYS)")
print("=" * 80)

# Download all timeframes
timeframes = ["1h", "15m", "5m", "1m"]

for tf in timeframes:
    download_timeframe(tf, days=90)

print("\n" + "=" * 80)
print("✅ ALL TIMEFRAMES DOWNLOADED")
print("=" * 80)
