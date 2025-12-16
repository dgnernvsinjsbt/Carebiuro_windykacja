#!/usr/bin/env python3
"""Download PEPE 1h data - 90 days"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time

print("Downloading PEPE-USDT 1h data (90 days)...")

base_url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"

now = datetime.now()
num_batches = 4  # 90 days / ~22 days per batch

end_times = [int((now - timedelta(hours=i*1440)).timestamp() * 1000) for i in range(num_batches)]

def fetch_batch(end_time):
    params = {"symbol": "PEPE-USDT", "interval": "1h", "endTime": end_time, "limit": 1440}
    try:
        response = requests.get(base_url, params=params, timeout=30)
        return response.json().get('data', [])
    except:
        return []

start = time.time()
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(fetch_batch, end_times))

elapsed = time.time() - start

all_data = []
for batch in results:
    all_data.extend(batch)

if not all_data:
    print("❌ No data")
    exit(1)

df = pd.DataFrame(all_data)
df['timestamp'] = pd.to_datetime(df['time'].astype(int), unit='ms')

for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

cutoff = datetime.now() - timedelta(days=90)
df = df[df['timestamp'] >= cutoff]

df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)

output_path = 'pepe_1h_90d.csv'
df.to_csv(output_path, index=False)

print(f"✅ PEPE-USDT: {len(df):,} candles in {elapsed:.1f}s")
print(f"   Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Price: ${df['close'].min():.8f} - ${df['close'].max():.8f}")
print(f"   File: {output_path}")
