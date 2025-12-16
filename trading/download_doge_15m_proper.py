#!/usr/bin/env python3
"""Download DOGE 15m data - 6 months using proper batching"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time

base_url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"

# Download from Jun 1 to Dec 16, 2025
start_date = datetime(2025, 6, 1)
end_date = datetime(2025, 12, 16, 23, 59, 59)

# Calculate number of batches (1440 candles per batch = 15 days of 15m data)
days_total = (end_date - start_date).days
num_batches = (days_total // 15) + 1

print(f"Downloading DOGE-USDT 15m data from {start_date} to {end_date}")
print(f"Total days: {days_total}, Batches: {num_batches}")
print()

# Generate end times for each batch
end_times = []
for i in range(num_batches):
    batch_end = end_date - timedelta(days=i*15)
    end_times.append(int(batch_end.timestamp() * 1000))

def fetch_batch(end_time):
    params = {
        "symbol": "DOGE-USDT",
        "interval": "15m",
        "endTime": end_time,
        "limit": 1440
    }
    try:
        response = requests.get(base_url, params=params, timeout=30)
        data = response.json()
        if data.get('code') == 0:
            return data.get('data', [])
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

print("Fetching batches...")
start_time = time.time()

with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(fetch_batch, end_times))

all_data = []
for batch in results:
    all_data.extend(batch)

if not all_data:
    print("❌ No data received")
    exit(1)

print(f"✅ Downloaded {len(all_data)} candles in {time.time() - start_time:.1f}s")

# Convert to DataFrame
df = pd.DataFrame(all_data)
df['timestamp'] = pd.to_datetime(df['time'].astype(int), unit='ms')

for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# Filter to exact date range and remove duplicates
df = df[df['timestamp'] >= start_date]
df = df[df['timestamp'] <= end_date]
df = df.sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)

# Select columns to match MELANIA format
df = df[['open', 'close', 'high', 'low', 'volume', 'time', 'timestamp']]

# Save
filename = 'doge_6months_bingx_15m.csv'
df.to_csv(filename, index=False)

print()
print(f"📁 Saved to: {filename}")
print(f"📊 Total candles: {len(df):,}")
print(f"📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"💰 Price range: ${df['low'].min():.4f} - ${df['high'].max():.4f}")
print()

# Show monthly breakdown
df['month'] = df['timestamp'].dt.to_period('M')
monthly_counts = df['month'].value_counts().sort_index()
print("Monthly candle counts:")
for month, count in monthly_counts.items():
    print(f"  {month}: {count:,} candles")
