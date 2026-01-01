"""Download DOGE, FARTCOIN, PEPE data from BingX"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient


async def download_klines(symbol, days=90):
    """Download historical 1h klines"""

    # Load API keys from .env
    api_key = None
    api_secret = None

    if Path('.env').exists():
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('BINGX_API_KEY='):
                    api_key = line.split('=', 1)[1]
                elif line.startswith('BINGX_API_SECRET='):
                    api_secret = line.split('=', 1)[1]

    client = BingXClient(api_key, api_secret, testnet=False, base_url='https://open-api.bingx.com')

    print(f"\nDownloading {symbol} ({days} days, 1h candles)...")

    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (days * 24 * 60 * 60 * 1000)

    klines = await client.get_klines(
        symbol=symbol,
        interval='1h',
        start_time=start_time,
        end_time=end_time,
        limit=1500
    )

    if not klines:
        print(f"❌ No data received for {symbol}")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Save to CSV
    output_file = Path('trading') / f"{symbol.replace('-', '_').lower()}_90d_1h.csv"
    df.to_csv(output_file, index=False)

    print(f"✅ Saved {len(df)} candles to {output_file}")
    print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")

    return df


async def main():
    """Download missing coins"""

    coins = [
        'DOGE-USDT',
        'FARTCOIN-USDT',
        '1000PEPE-USDT'
    ]

    for symbol in coins:
        await download_klines(symbol, days=90)
        await asyncio.sleep(1)  # Rate limit


if __name__ == '__main__':
    asyncio.run(main())
