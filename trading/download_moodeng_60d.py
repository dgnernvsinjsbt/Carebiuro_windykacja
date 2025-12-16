#!/usr/bin/env python3
"""Download 60 days of MOODENG 1m data from BingX"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time

def download_moodeng():
    print("\nDownloading MOODENG-USDT...")
    
    base_url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"
    
    # Calculate batch times (60 days = ~62 batches of 1440 candles)
    now = datetime.now()
    num_batches = 62
    end_times = [int((now - timedelta(minutes=i*1440)).timestamp() * 1000) for i in range(num_batches)]
    
    def fetch_batch(end_time):
        params = {"symbol": "MOODENG-USDT", "interval": "1m", "endTime": end_time, "limit": 1440}
        response = requests.get(base_url, params=params, timeout=30)
        return response.json().get('data', [])
    
    start = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_batch, end_times))
    
    elapsed = time.time() - start
    
    # Combine data
    all_data = []
    for batch in results:
        all_data.extend(batch)
    
    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['time'].astype(int), unit='ms')
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    # Filter to exactly 60 days
    cutoff = datetime.now() - timedelta(days=60)
    df = df[df['timestamp'] >= cutoff]
    
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].sort_values('timestamp').reset_index(drop=True)
    
    # Save
    output_path = '/workspaces/Carebiuro_windykacja/trading/moodeng_usdt_60d_bingx.csv'
    df.to_csv(output_path, index=False)
    
    print(f"✅ MOODENG: {len(df):,} candles in {elapsed:.1f}s")
    print(f"   Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Price: ${df['close'].min():.6f} - ${df['close'].max():.6f}")
    
    return df

print("=" * 80)
print("DOWNLOADING MOODENG 60-DAY DATA")
print("=" * 80)

df = download_moodeng()

print("\n✅ Done!")
