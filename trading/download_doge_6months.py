#!/usr/bin/env python3
"""Download 6 months of DOGE-USDT 15-minute data from BingX"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

def download_bingx_klines(symbol, interval, start_time, end_time):
    """Download klines from BingX perpetual futures API"""
    url = "https://open-api.bingx.com/openApi/swap/v3/quote/klines"

    all_data = []
    current_start = start_time

    while current_start < end_time:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(current_start.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'limit': 1440  # Max per request
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('code') == 0 and 'data' in data:
                candles = data['data']
                if not candles:
                    break

                all_data.extend(candles)
                print(f"Downloaded {len(candles)} candles, total: {len(all_data)}")

                # Update start time to last candle + 1 interval
                last_time = int(candles[-1]['time'])
                current_start = datetime.fromtimestamp(last_time / 1000) + timedelta(minutes=15)

                if len(candles) < 1440:
                    break

                time.sleep(0.2)
            else:
                print(f"Error: {data}")
                break

        except Exception as e:
            print(f"Request failed: {e}")
            break

    return all_data

# Download 6 months of data (Jun 1 - Dec 16, 2025)
symbol = 'DOGE-USDT'
interval = '15m'
start_time = datetime(2025, 6, 1, 0, 0, 0)
end_time = datetime(2025, 12, 16, 23, 59, 59)

print(f"Downloading {symbol} {interval} data from BingX...")
print(f"Period: {start_time} to {end_time}")
print()

candles = download_bingx_klines(symbol, interval, start_time, end_time)

if candles:
    # Convert to DataFrame
    df = pd.DataFrame(candles)
    df = df.rename(columns={'time': 'time'})

    # Create timestamp column
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')

    # Select and order columns
    df = df[['open', 'close', 'high', 'low', 'volume', 'time', 'timestamp']]

    # Sort by time
    df = df.sort_values('time').reset_index(drop=True)

    # Save to CSV
    filename = 'doge_6months_bingx.csv'
    df.to_csv(filename, index=False)

    print()
    print(f"✅ Downloaded {len(df)} candles")
    print(f"📁 Saved to: {filename}")
    print(f"📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"💰 Price range: ${df['low'].min():.4f} - ${df['high'].max():.4f}")
else:
    print("❌ Failed to download data")
