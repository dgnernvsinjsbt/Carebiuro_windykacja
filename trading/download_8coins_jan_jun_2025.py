#!/usr/bin/env python3
"""
Download 1H data for 8 Donchian portfolio coins: Jan-Jun 2025
Auto-generated using bingx-data-download skill
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bingx-trading-bot'))

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from execution.bingx_client import BingXClient

# 8 coins from Donchian portfolio
COINS = [
    'PENGU-USDT',
    'DOGE-USDT',
    'FARTCOIN-USDT',
    'ETH-USDT',
    'UNI-USDT',
    'PI-USDT',
    'CRV-USDT',
    'AIXBT-USDT',
]

async def download_chunk(bingx, symbol, start_date, end_date, chunk_name):
    """Download one time chunk (max 1440 candles = 60 days for 1H)"""
    print(f"  {chunk_name}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    start_time = int(start_date.timestamp() * 1000)
    end_time = int(end_date.timestamp() * 1000)

    try:
        candles = await bingx.get_klines(
            symbol=symbol,
            interval='1h',
            start_time=start_time,
            end_time=end_time,
            limit=1440
        )
        print(f"     Got {len(candles)} candles")
    except Exception as e:
        print(f"     ERROR: {e}")
        candles = []

    await asyncio.sleep(0.2)  # Rate limit: 5 req/s
    return candles

async def download_coin(bingx, symbol):
    """Download all data for one coin"""
    print(f"\n{'='*60}")
    print(f"DOWNLOADING {symbol}")
    print(f"{'='*60}")

    # Jan-Jun 2025: Use 60-day chunks (1H = 24 candles/day, 60 days = 1440 candles)
    chunks = [
        (datetime(2025, 1, 1, tzinfo=timezone.utc), datetime(2025, 3, 1, tzinfo=timezone.utc), "Jan-Feb"),
        (datetime(2025, 3, 1, tzinfo=timezone.utc), datetime(2025, 5, 1, tzinfo=timezone.utc), "Mar-Apr"),
        (datetime(2025, 5, 1, tzinfo=timezone.utc), datetime(2025, 6, 1, tzinfo=timezone.utc), "May"),
        (datetime(2025, 6, 1, tzinfo=timezone.utc), datetime(2025, 7, 1, tzinfo=timezone.utc), "Jun"),
    ]

    all_candles = []

    for start_date, end_date, chunk_name in chunks:
        candles = await download_chunk(bingx, symbol, start_date, end_date, chunk_name)
        if candles:
            all_candles.extend(candles)

    if not all_candles:
        print(f"  No data for {symbol}")
        return None

    # Process DataFrame
    df = pd.DataFrame(all_candles)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp').drop_duplicates(subset=['time'])

    # Convert to float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Filter to Jan-Jun only
    df = df[(df['timestamp'] >= '2025-01-01') & (df['timestamp'] < '2025-07-01')]

    # Save
    coin_name = symbol.split('-')[0].lower()
    filename = f"trading/{coin_name}_1h_jan_jun_2025.csv"
    df.to_csv(filename, index=False)

    print(f"  Saved {len(df)} candles to {filename}")
    print(f"  Range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    return df

async def main():
    print("=" * 80)
    print("DOWNLOADING 8 COINS - 1H DATA - JAN-JUN 2025")
    print("=" * 80)

    bingx = BingXClient(api_key="", api_secret="", testnet=False)

    results = {}
    for symbol in COINS:
        df = await download_coin(bingx, symbol)
        if df is not None:
            results[symbol] = len(df)

    await bingx.close()

    print("\n" + "=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)
    for symbol, count in results.items():
        print(f"  {symbol}: {count} candles")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
