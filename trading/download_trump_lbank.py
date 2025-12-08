#!/usr/bin/env python3
"""Download TRUMP/USDT 1-minute data from LBank exchange using ccxt"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time

def download_lbank_data(symbol='TRUMP/USDT', timeframe='1m', days=90):
    """Download historical data from LBank"""

    # Initialize LBank exchange
    exchange = ccxt.lbank({
        'enableRateLimit': True,
    })

    # Calculate date range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    print('=' * 80)
    print(f'Downloading {symbol} {timeframe} data from LBank')
    print(f'Period: {start_time.strftime("%Y-%m-%d %H:%M")} to {end_time.strftime("%Y-%m-%d %H:%M")}')
    print(f'Duration: {days} days')
    print('=' * 80)
    print()

    all_candles = []
    current_start = start_time

    # LBank allows fetching 1000 candles at a time
    chunk_size = timedelta(minutes=1000)  # 1000 minutes for 1m timeframe

    while current_start < end_time:
        current_end = min(current_start + chunk_size, end_time)

        print(f"Fetching from {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}...", end=' ')

        try:
            # Fetch OHLCV data
            since = int(current_start.timestamp() * 1000)

            candles = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=1000
            )

            if candles:
                all_candles.extend(candles)
                print(f"Got {len(candles)} candles")
            else:
                print("No data")

            # Move to next chunk
            current_start = current_end

            # Rate limiting
            time.sleep(exchange.rateLimit / 1000)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)
            continue

    if not all_candles:
        print("\nFailed to download data")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Add exchange and symbol columns
    df['exchange'] = 'lbank'
    df['symbol'] = symbol

    # Reorder columns
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'exchange', 'symbol']]

    # Sort and remove duplicates
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)

    # Save to CSV
    filename = 'trump_usdt_1m_lbank.csv'
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
    print(f'  Avg Volume: {df["volume"].mean():,.2f}')
    print()
    print('=' * 80)

    return df


if __name__ == "__main__":
    # Download 90 days for pattern analysis
    download_lbank_data(symbol='TRUMP/USDT', timeframe='1m', days=90)
