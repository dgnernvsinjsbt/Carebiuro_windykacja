#!/usr/bin/env python3
"""
Download 9 coins x 6 months x 15m data from BingX
Using bingx-data-download skill logic
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bingx-trading-bot'))

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from execution.bingx_client import BingXClient

# Coins to download
COINS = [
    'PI-USDT',
    'BTC-USDT',
    'ETH-USDT',
    'TRUMPSOL-USDT',
    'CRV-USDT',
    'PENGU-USDT',
    'UNI-USDT',
    'AIXBT-USDT',
    '1000PEPE-USDT'
]

# 15m interval = 96 candles/day, 1440 candles = 15 days (BingX max per request)
async def download_chunk(bingx, symbol, start_date, end_date, chunk_name):
    """Download one 15-day chunk"""
    print(f"   📅 {chunk_name}: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    start_time = int(start_date.timestamp() * 1000)
    end_time = int(end_date.timestamp() * 1000)

    try:
        candles = await bingx.get_klines(
            symbol=symbol,
            interval='15m',
            start_time=start_time,
            end_time=end_time,
            limit=1440
        )

        print(f"      Got {len(candles)} candles")
        await asyncio.sleep(0.2)  # Rate limit: 5 req/s (BingX max: 10 req/s)

        return candles
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return []

async def download_coin(bingx, symbol):
    """Download 6 months for one coin"""
    print(f"\n{'='*80}")
    print(f"🪙 {symbol}")
    print(f"{'='*80}")

    # Define 15-day chunks for 6 months (Jun-Dec 2025)
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
        (datetime(2025, 9, 1, tzinfo=timezone.utc), datetime(2025, 9, 15, 23, 59, tzinfo=timezone.utc), "Sep 1-15"),
        (datetime(2025, 9, 16, tzinfo=timezone.utc), datetime(2025, 9, 30, 23, 59, tzinfo=timezone.utc), "Sep 16-30"),

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

    if not all_candles:
        print(f"\n   ❌ No data downloaded for {symbol}")
        return None

    # Process DataFrame
    print(f"\n   💾 Processing {len(all_candles)} candles...")
    df = pd.DataFrame(all_candles)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp').drop_duplicates(subset=['time'])

    # Convert to float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate ATR
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
    symbol_clean = symbol.replace('-', '').lower()
    filename = f"{symbol_clean}_6months_bingx_15m.csv"
    df.to_csv(filename, index=False)

    print(f"\n   ✅ Saved to {filename}")
    print(f"      Total candles: {len(df)}")
    print(f"      Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"      Period: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
    print(f"      Avg Price: ${df['close'].mean():.4f}")
    print(f"      Avg ATR %: {df['atr_pct'].mean():.3f}%")
    print(f"      Price Range: ${df['close'].min():.4f} - ${df['close'].max():.4f}")

    return {
        'symbol': symbol,
        'candles': len(df),
        'atr_pct': df['atr_pct'].mean(),
        'filename': filename
    }

async def main():
    print("="*80)
    print("DOWNLOADING 9 COINS x 6 MONTHS x 15m FROM BINGX")
    print("="*80)
    print(f"\nCoins: {', '.join(COINS)}")
    print(f"Interval: 15m")
    print(f"Period: Jun 1 - Dec 17, 2025 (6 months)")
    print(f"Chunks: 14 x 15-day batches per coin")
    print(f"Rate limit: 0.2s sleep = 5 req/s (BingX max: 10 req/s)")
    print()

    bingx = BingXClient(api_key="", api_secret="", testnet=False)

    results = []

    for symbol in COINS:
        result = await download_coin(bingx, symbol)
        if result:
            results.append(result)

    await bingx.close()

    # Summary
    print(f"\n{'='*80}")
    print("📊 DOWNLOAD SUMMARY")
    print(f"{'='*80}\n")

    print(f"{'Symbol':<20} | {'Candles':<10} | {'ATR %':<10} | {'Filename':<30}")
    print("-"*80)

    for r in results:
        print(f"{r['symbol']:<20} | {r['candles']:<10} | {r['atr_pct']:<10.3f} | {r['filename']:<30}")

    print(f"\n✅ Downloaded {len(results)}/{len(COINS)} coins successfully!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
