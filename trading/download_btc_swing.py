#!/usr/bin/env python3
"""Download BTC 1-minute data for swing trading strategy (30-60 days)"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time

print("=" * 80)
print("DOWNLOADING BTC 1-MINUTE DATA FOR SWING TRADING")
print("=" * 80)

base_url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"

# Download 60 days for enough swing trades
now = datetime.now()
num_batches = 62  # 60 days = ~62 batches of 1440 candles
end_times = [int((now - timedelta(minutes=i*1440)).timestamp() * 1000) for i in range(num_batches)]

def fetch_batch(end_time):
    params = {"symbol": "BTC-USDT", "interval": "1m", "endTime": end_time, "limit": 1440}
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
    print("❌ No data received")
    exit(1)

df = pd.DataFrame(all_data)
df['timestamp'] = pd.to_datetime(df['time'].astype(int), unit='ms')

for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# Filter to exactly 60 days
cutoff = datetime.now() - timedelta(days=60)
df = df[df['timestamp'] >= cutoff]

df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].sort_values('timestamp').reset_index(drop=True)

# Save
output_path = '/workspaces/Carebiuro_windykacja/trading/btc_swing_60d.csv'
df.to_csv(output_path, index=False)

print(f"\n✅ BTC-USDT: {len(df):,} candles in {elapsed:.1f}s")
print(f"   Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Price: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
print(f"   File: {output_path}")
