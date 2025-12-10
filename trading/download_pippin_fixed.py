#!/usr/bin/env python3
"""Download PIPPIN-USDT 1-minute data from BingX Futures"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time

def fetch_bingx_futures_klines(symbol, interval, start_time, end_time):
    """Fetch kline data from BingX perpetual futures API"""
    url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"
    all_data = []
    current_end = end_time
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

        print(f"Fetching {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}...", end=' ')

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('code') != 0:
                print(f"Error: {data.get('msg')}")
                break

            klines = data.get('data', [])
            if not klines:
                print("No data")
                break
            else:
                all_data.extend(klines)
                print(f"{len(klines)} candles")

            current_end = current_start - timedelta(minutes=1)
            time.sleep(0.3)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)
            continue

    return all_data

# Download all available data for PIPPIN
symbol = 'PIPPIN-USDT'
interval = '1m'
end_time = datetime.now()
start_time = end_time - timedelta(days=10)

print('=' * 80)
print(f'Downloading {symbol} 1-minute data from BingX Futures')
print(f'Period: {start_time.strftime("%Y-%m-%d")} to {end_time.strftime("%Y-%m-%d")} (10 days max)')
print('=' * 80)
print()

klines = fetch_bingx_futures_klines(symbol, interval, start_time, end_time)

if klines:
    # Debug: Check first row structure
    print(f"\nDebug - First row: {klines[0]}")
    print(f"Debug - Row length: {len(klines[0])}")

    # Convert to DataFrame
    df = pd.DataFrame(klines)

    # BingX futures format: [time, open, high, low, close, volume, ...]
    # The 'time' field might be an object/dict - let's check
    print(f"Debug - DataFrame shape: {df.shape}")
    print(f"Debug - DataFrame columns: {df.columns.tolist()}")
    print(f"Debug - First row:\n{df.iloc[0]}")

    # Try to extract timestamp correctly
    # If time is nested, extract it
    if isinstance(df.iloc[0, 0], dict):
        df['timestamp'] = df.iloc[:, 0].apply(lambda x: x.get('time', x) if isinstance(x, dict) else x)
    else:
        df['timestamp'] = df.iloc[:, 0]

    # Now extract OHLCV - try different column positions
    if len(df.columns) >= 6:
        df = df.iloc[:, :6]
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    else:
        # Might be nested structure - extract differently
        print(f"\nWarning: Unexpected data structure, columns: {df.columns.tolist()}")

    # Handle timestamp - could be in seconds or milliseconds
    # First, ensure it's numeric
    try:
        df['timestamp'] = pd.to_numeric(df['timestamp'])

        # Check if it's in seconds (smaller numbers) or milliseconds (larger)
        if df['timestamp'].iloc[0] < 10000000000:  # Likely in seconds
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        else:  # In milliseconds
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    except:
        print("\nError parsing timestamps, trying alternative method...")
        # Try direct conversion
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Convert prices to float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Sort by timestamp and remove duplicates
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)

    # Save to CSV
    duration_days = (df["timestamp"].max() - df["timestamp"].min()).days
    filename = f'pippin_{duration_days}d_bingx.csv'
    df.to_csv(filename, index=False)

    print()
    print('=' * 80)
    print('DOWNLOAD COMPLETE')
    print('=' * 80)
    print(f'Total candles: {len(df):,}')
    print(f'Date range: {df["timestamp"].min()} to {df["timestamp"].max()}')
    print(f'Duration: {duration_days} days ({len(df) / 1440:.1f} days of 1m data)')
    print(f'File saved: {filename}')
    print()

    # Quick stats
    print('Price Statistics:')
    print(f'  Starting: ${df["close"].iloc[0]:.6f}')
    print(f'  Ending: ${df["close"].iloc[-1]:.6f}')
    print(f'  Change: {(df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100:+.2f}%')
    print(f'  High: ${df["high"].max():.6f}')
    print(f'  Low: ${df["low"].min():.6f}')
    print(f'  Avg Volume: {df["volume"].mean():.2f}')
    print()

    # Volatility check
    df['pct_change'] = df['close'].pct_change().abs() * 100
    print('Volatility:')
    print(f'  Avg candle move: {df["pct_change"].mean():.3f}%')
    print(f'  Max candle move: {df["pct_change"].max():.3f}%')
    print(f'  Volatile candles (>1%): {(df["pct_change"] > 1.0).sum()} ({(df["pct_change"] > 1.0).sum() / len(df) * 100:.1f}%)')
    print()
    print('=' * 80)

else:
    print()
    print("Failed to download data")
