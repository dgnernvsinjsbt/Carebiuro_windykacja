#!/usr/bin/env python3
"""
Download last 90 days of MELANIA-USDT 15m data from BingX Perpetual Futures
Fast version - single request for recent data
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bingx-trading-bot'))

import asyncio
import pandas as pd
from datetime import datetime, timezone, timedelta
from execution.bingx_client import BingXClient

async def main():
    print("=" * 70)
    print("DOWNLOADING MELANIA-USDT 15m DATA - LAST 90 DAYS")
    print("Source: BingX Perpetual Futures")
    print("=" * 70)

    # Initialize BingX client
    bingx = BingXClient(
        api_key="",
        api_secret="",
        testnet=False
    )

    symbol = "MELANIA-USDT"

    # Last 90 days
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=90)

    print(f"\n📅 Period: {start_date.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
    print(f"   ({90} days)")

    # Fetch in chunks (1440 candles max per request)
    all_candles = []
    current_start = int(start_date.timestamp() * 1000)
    end_time = int(now.timestamp() * 1000)

    print(f"\n📊 Downloading candles...")
    chunk_num = 0

    while current_start < end_time:
        chunk_num += 1
        print(f"   Chunk {chunk_num}: From {datetime.fromtimestamp(current_start/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')}")

        candles = await bingx.get_klines(
            symbol=symbol,
            interval='15m',
            start_time=current_start,
            end_time=end_time,
            limit=1440
        )

        if not candles or len(candles) == 0:
            print(f"      No data returned, stopping")
            break

        all_candles.extend(candles)
        print(f"      Got {len(candles)} candles (total: {len(all_candles)})")

        # Move to next batch (use last timestamp + 1 to avoid duplicates)
        current_start = candles[-1]['time'] + (15 * 60 * 1000)

        # Delay to avoid rate limits
        await asyncio.sleep(0.5)

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
    filename = "melania_90d_bingx_futures.csv"
    df.to_csv(filename, index=False)

    print(f"\n✅ Saved to {filename}")
    print(f"   Total candles: {len(df)}")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
