#!/usr/bin/env python3
"""
Download 90 days of 1h data for MOODENG and TRUMP
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from execution.bingx_client import BingXClient

def load_env():
    env_path = Path(__file__).parent.parent / '.env'
    env = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    return env

async def download_data(symbol, days=90):
    """Download 1h candles for specified days"""

    env = load_env()
    client = BingXClient(env['BINGX_API_KEY'], env['BINGX_API_SECRET'], testnet=False)

    try:
        print(f"\n{'='*80}")
        print(f"Downloading {days} days of 1h data for {symbol}")
        print(f"{'='*80}")

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)

        end_ms = int(end_time.timestamp() * 1000)
        start_ms = int(start_time.timestamp() * 1000)

        all_candles = []
        current_start = start_ms

        while current_start < end_ms:
            # Fetch in batches of 1000 (BingX limit)
            klines = await client.get_klines(
                symbol=symbol,
                interval='1h',
                start_time=current_start,
                end_time=end_ms,
                limit=1000
            )

            if not klines:
                break

            all_candles.extend(klines)

            # Move to next batch
            last_time = klines[-1]['time']
            current_start = last_time + (60 * 60 * 1000)  # +1 hour

            print(f"  Fetched {len(klines)} candles, total: {len(all_candles)}")

            if len(klines) < 1000:
                break

            await asyncio.sleep(0.1)  # Rate limit

        # Build DataFrame
        df = pd.DataFrame(all_candles)
        df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
        df = df.sort_values('timestamp')

        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        # Keep only needed columns
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

        # Save
        filename = f"trading/{symbol.lower().replace('-', '_')}_90d_1h.csv"
        df.to_csv(filename, index=False)

        print(f"\n✅ Saved {len(df)} candles to {filename}")
        print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"   Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

        return df

    finally:
        await client.close()

async def main():
    symbols = ['MOODENG-USDT', 'TRUMP-USDT']

    for symbol in symbols:
        await download_data(symbol, days=90)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
