#!/usr/bin/env python3
"""Download FARTCOIN 15m data - 6 months"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time

base_url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"
start_date = datetime(2025, 6, 1)
end_date = datetime(2025, 12, 16, 23, 59, 59)
days_total = (end_date - start_date).days
num_batches = (days_total // 15) + 1

print(f"Downloading FARTCOIN-USDT 15m data from {start_date} to {end_date}")

end_times = []
for i in range(num_batches):
    batch_end = end_date - timedelta(days=i*15)
    end_times.append(int(batch_end.timestamp() * 1000))

def fetch_batch(end_time):
    params = {"symbol": "FARTCOIN-USDT", "interval": "15m", "endTime": end_time, "limit": 1440}
    try:
        response = requests.get(base_url, params=params, timeout=30)
        data = response.json()
        if data.get('code') == 0:
            return data.get('data', [])
        return []
    except:
        return []

start_time = time.time()
with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(fetch_batch, end_times))

all_data = []
for batch in results:
    all_data.extend(batch)

if not all_data:
    print("❌ No data received")
    exit(1)

df = pd.DataFrame(all_data)
df['timestamp'] = pd.to_datetime(df['time'].astype(int), unit='ms')
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

df = df[df['timestamp'] >= start_date]
df = df[df['timestamp'] <= end_date]
df = df.sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)
df = df[['open', 'close', 'high', 'low', 'volume', 'time', 'timestamp']]

filename = 'fartcoin_6months_bingx_15m.csv'
df.to_csv(filename, index=False)

print(f"✅ {len(df):,} candles | {time.time() - start_time:.1f}s")
print(f"📅 {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"💰 ${df['low'].min():.4f} - ${df['high'].max():.4f}")
