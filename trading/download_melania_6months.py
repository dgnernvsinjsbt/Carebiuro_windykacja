#!/usr/bin/env python3
"""
Download MELANIA-USDT 15m data from BingX in 15-day chunks
June-Dec 2025 (6 months)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bingx-trading-bot'))

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

    await asyncio.sleep(0.5)  # Rate limit

    return candles

async def main():
    print("=" * 70)
    print("DOWNLOADING MELANIA-USDT 15m DATA - 6 MONTHS")
    print("June 1 - Dec 16, 2025")
    print("=" * 70)

    bingx = BingXClient(api_key="", api_secret="", testnet=False)

    symbol = "MELANIA-USDT"

    # Define 15-day chunks
    chunks = [
        # June
        (datetime(2025, 6, 1, tzinfo=timezone.utc), datetime(2025, 6, 15, 23, 59, tzinfo=timezone.utc), "Jun 1-15"),
        (datetime(2025, 6, 16, tzinfo=timezone.utc), datetime(2025, 6, 30, 23, 59, tzinfo=timezone.utc), "Jun 16-30"),

        # July
        (datetime(2025, 7, 1, tzinfo=timezone.utc), datetime(2025, 7, 15, 23, 59, tzinfo=timezone.utc), "Jul 1-15"),
        (datetime(2025, 7, 16, tzinfo=timezone.utc), datetime(2025, 7, 31, 23, 59, tzinfo=timezone.utc), "Jul 16-31"),

        # August
        (datetime(2025, 8, 1, tzinfo=timezone.utc), datetime(2025, 8, 15, 23, 59, tzinfo=timezone.utc), "Aug 1-15"),
        (datetime(2025, 8, 16, tzinfo=timezone.utc), datetime(2025, 8, 31, 23, 59, tzinfo=timezone.utc), "Aug 16-31"),

        # September
        (datetime(2025, 9, 1, tzinfo=timezone.utc), datetime(2025, 9, 15, 23, 59, tzinfo=timezone.utc), "Sept 1-15"),
        (datetime(2025, 9, 16, tzinfo=timezone.utc), datetime(2025, 9, 30, 23, 59, tzinfo=timezone.utc), "Sept 16-30"),

        # October
        (datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2025, 10, 15, 23, 59, tzinfo=timezone.utc), "Oct 1-15"),
        (datetime(2025, 10, 16, tzinfo=timezone.utc), datetime(2025, 10, 31, 23, 59, tzinfo=timezone.utc), "Oct 16-31"),

        # November
        (datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2025, 11, 15, 23, 59, tzinfo=timezone.utc), "Nov 1-15"),
        (datetime(2025, 11, 16, tzinfo=timezone.utc), datetime(2025, 11, 30, 23, 59, tzinfo=timezone.utc), "Nov 16-30"),

        # December
        (datetime(2025, 12, 1, tzinfo=timezone.utc), datetime(2025, 12, 15, 23, 59, tzinfo=timezone.utc), "Dec 1-15"),
        (datetime(2025, 12, 16, tzinfo=timezone.utc), datetime(2025, 12, 16, 23, 59, tzinfo=timezone.utc), "Dec 16"),
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

    # Save
    filename = "melania_6months_bingx.csv"
    df.to_csv(filename, index=False)

    print(f"\n✅ Saved to {filename}")
    print(f"   Total candles: {len(df)}")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Period: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
