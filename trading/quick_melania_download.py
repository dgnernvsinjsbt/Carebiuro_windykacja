#!/usr/bin/env python3
"""Quick download - just get max 1440 candles from BingX"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bingx-trading-bot'))

import asyncio
import pandas as pd
from datetime import datetime, timezone, timedelta
from execution.bingx_client import BingXClient

async def main():
    print("Downloading MELANIA-USDT 15m data from BingX (max 1440 candles)...")

    bingx = BingXClient(api_key="", api_secret="", testnet=False)

    # Just get the max candles available
    candles = await bingx.get_klines(
        symbol="MELANIA-USDT",
        interval='15m',
        limit=1440
    )

    await bingx.close()

    print(f"Got {len(candles)} candles")

    df = pd.DataFrame(candles)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')

    filename = "melania_bingx_15m.csv"
    df.to_csv(filename, index=False)

    print(f"Saved to {filename}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    days = (df['timestamp'].max() - df['timestamp'].min()).days
    print(f"Period: {days} days")

if __name__ == "__main__":
    asyncio.run(main())
