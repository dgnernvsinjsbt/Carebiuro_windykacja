#!/usr/bin/env python3
"""Download FARTCOIN 1-minute data from BingX"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time

def fetch_bingx_klines(symbol, interval, start_time, end_time):
    """Fetch kline data from BingX spot API"""
    url = "https://open-api.bingx.com/openApi/spot/v1/market/kline"

    all_data = []
    current_end = end_time

    # Work backwards in chunks of 1000 candles (BingX limit)
    # 1000 minutes = ~16.7 hours
    chunk_size = timedelta(minutes=1000)

    while current_end > start_time:
        current_start = max(start_time, current_end - chunk_size)

        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(current_start.timestamp() * 1000),
            'endTime': int(current_end.timestamp() * 1000),
            'limit': 1000
        }

        print(f"Fetching from {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}...", end=' ')

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != 0:
                print(f"Error: {data.get('msg')}")
                break

            klines = data.get('data', [])
            if not klines:
                print("No data")
            else:
                all_data.extend(klines)
                print(f"Got {len(klines)} candles")

            # Move to next chunk
            current_end = current_start - timedelta(minutes=1)

            # Rate limiting
            time.sleep(0.3)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)
            continue

    return all_data

# Download 3 months of data
symbol = 'FARTCOIN-USDT'
interval = '1m'
end_time = datetime.now()
start_time = end_time - timedelta(days=90)

print('=' * 80)
print(f'Downloading {symbol} 1-minute data from BingX')
print(f'Period: {start_time.strftime("%Y-%m-%d")} to {end_time.strftime("%Y-%m-%d")} (90 days)')
print('=' * 80)
print()

klines = fetch_bingx_klines(symbol, interval, start_time, end_time)

if klines:
    # Convert to DataFrame
    # BingX format: [timestamp, open, high, low, close, volume, close_time, quote_volume]
    df = pd.DataFrame(klines)

    # Take only first 6 columns
    df = df.iloc[:, :6]
    df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Convert prices to float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Sort by timestamp (oldest first) and remove duplicates
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)

    # Save to CSV
    filename = 'fartcoin_1m_90days.csv'
    df.to_csv(filename, index=False)

    print()
    print('=' * 80)
    print('DOWNLOAD COMPLETE')
    print('=' * 80)
    print(f'Total candles: {len(df):,}')
    print(f'Date range: {df["timestamp"].min()} to {df["timestamp"].max()}')
    print(f'Duration: {(df["timestamp"].max() - df["timestamp"].min()).days} days')
    print(f'File saved: {filename}')
    print()

    # Quick stats
    print('Price Statistics:')
    print(f'  Starting: ${df["close"].iloc[0]:.4f}')
    print(f'  Ending: ${df["close"].iloc[-1]:.4f}')
    print(f'  Change: {(df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100:+.2f}%')
    print(f'  High: ${df["high"].max():.4f}')
    print(f'  Low: ${df["low"].min():.4f}')
    print(f'  Avg Volume: {df["volume"].mean():.2f}')
    print()
    print('=' * 80)

else:
    print()
    print("Failed to download data")
