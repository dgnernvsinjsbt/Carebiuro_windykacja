#!/usr/bin/env python3
"""
Download XLM-USDT 15m data from BingX in 15-day chunks
Sept-Dec 2025 (3 months)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bingx-trading-bot'))

import asyncio
import pandas as pd
from datetime import datetime, timezone
from execution.bingx_client import BingXClient

async def download_chunk(bingx, symbol, start_date, end_date, chunk_name):
    """Download one 15-day chunk"""
    print(f"\n📅 {chunk_name}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    start_time = int(start_date.timestamp() * 1000)
    end_time = int(end_date.timestamp() * 1000)

    candles = await bingx.get_klines(
        symbol=symbol,
        interval='15m',
        start_time=start_time,
        end_time=end_time,
        limit=1440
    )

    print(f"   Got {len(candles)} candles")

    await asyncio.sleep(0.2)  # Rate limit: 5 req/s (BingX max: 10 req/s)

    return candles

async def main():
    print("=" * 70)
    print("DOWNLOADING XLM-USDT 15m DATA - 3 MONTHS")
    print("Sept 18 - Dec 17, 2025")
    print("=" * 70)

    bingx = BingXClient(api_key="", api_secret="", testnet=False)

    symbol = "XLM-USDT"

    # Define 15-day chunks for last 3 months
    chunks = [
        # September (partial - from Sept 18)
        (datetime(2025, 9, 18, tzinfo=timezone.utc), datetime(2025, 9, 30, 23, 59, tzinfo=timezone.utc), "Sept 18-30"),

        # October
        (datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2025, 10, 15, 23, 59, tzinfo=timezone.utc), "Oct 1-15"),
        (datetime(2025, 10, 16, tzinfo=timezone.utc), datetime(2025, 10, 31, 23, 59, tzinfo=timezone.utc), "Oct 16-31"),

        # November
        (datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2025, 11, 15, 23, 59, tzinfo=timezone.utc), "Nov 1-15"),
        (datetime(2025, 11, 16, tzinfo=timezone.utc), datetime(2025, 11, 30, 23, 59, tzinfo=timezone.utc), "Nov 16-30"),

        # December
        (datetime(2025, 12, 1, tzinfo=timezone.utc), datetime(2025, 12, 15, 23, 59, tzinfo=timezone.utc), "Dec 1-15"),
        (datetime(2025, 12, 16, tzinfo=timezone.utc), datetime(2025, 12, 17, 23, 59, tzinfo=timezone.utc), "Dec 16-17"),
    ]

    all_candles = []

    for start_date, end_date, chunk_name in chunks:
        candles = await download_chunk(bingx, symbol, start_date, end_date, chunk_name)
        if candles:
            all_candles.extend(candles)

    await bingx.close()

    if not all_candles:
        print("\n❌ No data downloaded")
        return

    # Convert to DataFrame
    print(f"\n💾 Processing {len(all_candles)} candles...")
    df = pd.DataFrame(all_candles)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp').drop_duplicates(subset=['time'])

    # Convert to float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate stats
    import numpy as np
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = (df['atr'] / df['close']) * 100

    # Save
    filename = "xlm_3months_bingx_15m.csv"
    df.to_csv(filename, index=False)

    print(f"\n✅ Saved to {filename}")
    print(f"   Total candles: {len(df)}")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Period: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
    print(f"\n📊 XLM-USDT Stats:")
    print(f"   Avg Price: ${df['close'].mean():.4f}")
    print(f"   Avg ATR: ${df['atr'].mean():.6f}")
    print(f"   Avg ATR %: {df['atr_pct'].mean():.3f}%")
    print(f"   Min Price: ${df['close'].min():.4f}")
    print(f"   Max Price: ${df['close'].max():.4f}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
