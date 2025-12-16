#!/usr/bin/env python3
"""
Download MELANIA-USDT 15m data from BingX Perpetual Futures
Jun-Dec 2025 (same period as LBank backtest)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bingx-trading-bot'))

import asyncio
import pandas as pd
from datetime import datetime, timezone
from execution.bingx_client import BingXClient

async def download_month(bingx, symbol, year, month, month_name):
    """Download one month of 15m data"""
    print(f"\n📅 Downloading {month_name} {year}...")

    # Calculate start/end timestamps
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    start_time = int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end_time = int(datetime(next_year, next_month, 1, tzinfo=timezone.utc).timestamp() * 1000)

    all_candles = []
    current_start = start_time

    while current_start < end_time:
        print(f"   Fetching from {datetime.fromtimestamp(current_start/1000, tz=timezone.utc)}")

        candles = await bingx.get_klines(
            symbol=symbol,
            interval='15m',
            start_time=current_start,
            end_time=end_time,
            limit=1440  # Max per request
        )

        if not candles:
            print(f"   No more data")
            break

        all_candles.extend(candles)

        # Move to next batch (last candle timestamp + 15 min)
        last_time = candles[-1]['time']
        current_start = last_time + (15 * 60 * 1000)

        # Small delay to avoid rate limits
        await asyncio.sleep(0.2)

    print(f"   ✅ Downloaded {len(all_candles)} candles")
    return all_candles

async def main():
    print("=" * 70)
    print("DOWNLOADING MELANIA-USDT 15m DATA FROM BINGX PERPETUAL FUTURES")
    print("Period: June - December 2025")
    print("=" * 70)

    # Initialize BingX client (no API keys needed for market data)
    bingx = BingXClient(
        api_key="",
        api_secret="",
        testnet=False
    )

    symbol = "MELANIA-USDT"

    months = [
        (2025, 6, 'june'),
        (2025, 7, 'july'),
        (2025, 8, 'august'),
        (2025, 9, 'september'),
        (2025, 10, 'october'),
        (2025, 11, 'november'),
        (2025, 12, 'december'),
    ]

    for year, month, month_name in months:
        candles = await download_month(bingx, symbol, year, month, month_name)

        if not candles:
            print(f"   ⚠️  No data for {month_name}")
            continue

        # Convert to DataFrame
        df = pd.DataFrame(candles)
        df['timestamp'] = pd.to_datetime(df['time'], unit='ms')

        # Save to CSV
        filename = f"melania_{month_name}_2025_15m_bingx.csv"
        df.to_csv(filename, index=False)
        print(f"   💾 Saved to {filename}")

    await bingx.close()

    print("\n" + "=" * 70)
    print("✅ DOWNLOAD COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
