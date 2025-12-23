#!/usr/bin/env python3
import requests
import pandas as pd
import time
from datetime import datetime, timezone

print("Downloading FARTCOIN 1m data for December 2025 from BingX...")

symbol = "FARTCOIN-USDT"
interval = "1m"
start_time = int(datetime(2025, 12, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
end_time = int(datetime(2025, 12, 17, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)

url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"

all_candles = []
current_start = start_time

while current_start < end_time:
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': current_start,
        'limit': 1440  # Max 1440
    }
    
    print(f"Fetching from {datetime.fromtimestamp(current_start/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}...")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == 0 and data.get('data'):
            candles = data['data']
            if not candles:
                break
            
            all_candles.extend(candles)
            last_time = candles[-1]['time']
            current_start = last_time + 60000
            
            print(f"  Got {len(candles)} candles, total: {len(all_candles)}")
            
            if len(candles) < 1440:
                break
                
        else:
            print(f"Error: {data}")
            break
            
    except Exception as e:
        print(f"Error: {e}")
        break
    
    time.sleep(0.5)

if all_candles:
    df = pd.DataFrame(all_candles)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.rename(columns={'open': 'open_str', 'close': 'close_str', 'high': 'high_str', 'low': 'low_str'})
    df['open'] = df['open_str'].astype(float)
    df['close'] = df['close_str'].astype(float)
    df['high'] = df['high_str'].astype(float)
    df['low'] = df['low_str'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    df.to_csv('fartcoin_december_1m_bingx.csv', index=False)
    
    print(f"\n✅ Downloaded {len(df)} candles")
    print(f"   From: {df['timestamp'].min()}")
    print(f"   To: {df['timestamp'].max()}")
    print(f"   File: fartcoin_december_1m_bingx.csv")
else:
    print("❌ No data downloaded")
