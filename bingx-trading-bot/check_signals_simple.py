#!/usr/bin/env python3
"""Simple check for signals using public BingX API"""

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timezone

async def main():
    print("📊 Fetching today's FARTCOIN data...\n")

    url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"
    params = {
        'symbol': 'FARTCOIN-USDT',
        'interval': '1m',
        'limit': 500  # Last ~8 hours
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                print(f"❌ API Error: {resp.status}")
                return

            data = await resp.json()
            klines = data.get('data', [])

            if not klines:
                print("❌ No data returned")
                return

    # Convert to DataFrame
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate indicators
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
    df['volume_avg'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_avg']

    print(f"✅ Loaded {len(df)} candles")
    print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Current price: ${df['close'].iloc[-1]:.6f}\n")

    # Check for explosive candles
    print("=" * 60)
    print("CHECKING FOR SIGNAL CONDITIONS")
    print("=" * 60)

    explosive = df[(df['body_pct'] > 1.2) & (df['volume_ratio'] > 3.0)]

    if len(explosive) > 0:
        print(f"\n✅ Found {len(explosive)} explosive candles (>1.2% body + >3x volume):\n")
        for _, row in explosive.tail(10).iterrows():
            direction = "UP" if row['close'] > row['open'] else "DOWN"
            print(f"  {row['timestamp']}: {direction} {row['body_pct']:.2f}%, "
                  f"Vol={row['volume_ratio']:.1f}x")
    else:
        print("\n❌ No explosive candles found in last ~8 hours")
        print("   (Requires: body >1.2% AND volume >3x average)")

    print(f"\n📊 Market Stats (last {len(df)} candles):")
    print(f"   Avg candle body: {df['body_pct'].mean():.3f}%")
    print(f"   Max candle body: {df['body_pct'].max():.3f}%")
    print(f"   Avg volume ratio: {df['volume_ratio'].mean():.2f}x")
    print(f"   Max volume ratio: {df['volume_ratio'].max():.2f}x")

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)

    if len(explosive) > 0:
        print("✅ Signal conditions MET - bot should have generated signals")
        print("   (If bot was connected during these times)")
    else:
        print("⚠️ NO signals - market too quiet for strategy conditions")
        print("   Strategies wait for explosive breakouts (>1.2% + volume)")
        print("   This is NORMAL during low volatility periods")

    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
