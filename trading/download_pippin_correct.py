#!/usr/bin/env python3
"""Download PIPPIN-USDT 1-minute data from BingX Futures - CORRECT VERSION"""

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
    # BingX futures returns list of dicts with keys: open, close, high, low, volume, time
    # Convert to DataFrame - pandas will use dict keys as columns
    df = pd.DataFrame(klines)

    # Rename 'time' to 'timestamp' and reorder columns
    df = df.rename(columns={'time': 'timestamp'})
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    # Convert timestamp from milliseconds to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Convert OHLCV to numeric
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Sort by timestamp and remove duplicates
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)

    # Calculate actual duration
    duration = df["timestamp"].max() - df["timestamp"].min()
    duration_days = duration.days
    duration_hours = duration.total_seconds() / 3600

    # Save to CSV
    filename = f'pippin_{duration_days}d_bingx.csv'
    df.to_csv(filename, index=False)

    print()
    print('=' * 80)
    print('DOWNLOAD COMPLETE')
    print('=' * 80)
    print(f'Total candles: {len(df):,}')
    print(f'Date range: {df["timestamp"].min()} to {df["timestamp"].max()}')
    print(f'Duration: {duration_days} days, {duration_hours:.1f} hours ({len(df)} minutes)')
    print(f'Expected candles for perfect data: {duration_days * 1440 + (duration_hours % 24) * 60:.0f}')
    print(f'Data completeness: {len(df) / (duration_hours * 60) * 100:.1f}%')
    print(f'File saved: {filename}')
    print()

    # Quick stats
    print('Price Statistics:')
    print(f'  Starting: ${df["close"].iloc[0]:.6f}')
    print(f'  Ending: ${df["close"].iloc[-1]:.6f}')
    print(f'  Change: {(df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100:+.2f}%')
    print(f'  High: ${df["high"].max():.6f}')
    print(f'  Low: ${df["low"].min():.6f}')
    print(f'  Price Range: {(df["high"].max() / df["low"].min() - 1) * 100:.1f}%')
    print()

    # Volume stats
    print('Volume Statistics:')
    print(f'  Avg Volume: {df["volume"].mean():,.0f} PIPPIN')
    print(f'  Total Volume: {df["volume"].sum():,.0f} PIPPIN')
    print(f'  Max Volume (1 candle): {df["volume"].max():,.0f} PIPPIN')
    print()

    # Volatility check
    df['pct_change'] = df['close'].pct_change().abs() * 100
    print('Volatility:')
    print(f'  Avg candle move: {df["pct_change"].mean():.3f}%')
    print(f'  Median candle move: {df["pct_change"].median():.3f}%')
    print(f'  Max candle move: {df["pct_change"].max():.3f}%')
    print(f'  Volatile candles (>0.5%): {(df["pct_change"] > 0.5).sum()} ({(df["pct_change"] > 0.5).sum() / len(df) * 100:.1f}%)')
    print(f'  Volatile candles (>1.0%): {(df["pct_change"] > 1.0).sum()} ({(df["pct_change"] > 1.0).sum() / len(df) * 100:.1f}%)')
    print(f'  Volatile candles (>2.0%): {(df["pct_change"] > 2.0).sum()} ({(df["pct_change"] > 2.0).sum() / len(df) * 100:.1f}%)')
    print()

    # ATR for reference
    df['range'] = df['high'] - df['low']
    atr_14 = df['range'].rolling(14).mean().iloc[-1]
    price = df['close'].iloc[-1]
    print(f'Recent Market Conditions:')
    print(f'  ATR(14): ${atr_14:.6f} ({atr_14 / price * 100:.2f}% of price)')
    print(f'  Avg candle range: ${df["range"].mean():.6f} ({df["range"].mean() / df["close"].mean() * 100:.2f}%)')
    print()
    print('=' * 80)

else:
    print()
    print("Failed to download data")
