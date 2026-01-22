#!/usr/bin/env python3
"""
Find all coins listed on BingX in 2025
Use 1D candles - LAST candle in array = listing date (BingX returns newest first)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bingx-trading-bot'))

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timezone
from execution.bingx_client import BingXClient
from config import load_config

async def get_all_contracts():
    """Get all perpetual contracts from BingX"""
    url = "https://open-api.bingx.com/openApi/swap/v2/quote/contracts"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if data.get('code') == 0:
                return [c['symbol'] for c in data.get('data', []) if c['symbol'].endswith('-USDT')]
    return []

async def get_listing_info(bingx, symbol, semaphore):
    """Get listing date from 1D candles (last candle = oldest = listing)"""
    async with semaphore:
        try:
            candles = await bingx.get_klines(symbol=symbol, interval='1d', limit=1000)
            if candles and len(candles) > 10:
                oldest = candles[-1]
                newest = candles[0]

                listing_date = datetime.fromtimestamp(oldest['time'] / 1000, tz=timezone.utc)
                first_price = float(oldest['open'])
                current_price = float(newest['close'])

                return {
                    'symbol': symbol,
                    'listing_date': listing_date,
                    'days_listed': len(candles),
                    'first_price': first_price,
                    'current_price': current_price,
                    'change_pct': (current_price / first_price - 1) * 100 if first_price > 0 else 0
                }
        except:
            pass
        return None

async def main():
    config = load_config(os.path.join(os.path.dirname(__file__), '..', 'bingx-trading-bot', 'config_donchian.yaml'))
    bingx = BingXClient(api_key=config.bingx.api_key, api_secret=config.bingx.api_secret, testnet=False)

    print("="*80)
    print("FINDING ALL BINGX COINS LISTED IN 2025")
    print("="*80)

    symbols = await get_all_contracts()
    print(f"Found {len(symbols)} USDT perpetuals")

    # Use semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(10)

    print("Fetching listing dates (parallel)...")
    tasks = [get_listing_info(bingx, s, semaphore) for s in symbols]
    results = await asyncio.gather(*tasks)

    await bingx.close()

    # Filter results
    results = [r for r in results if r is not None]
    listings_2025 = [r for r in results if r['listing_date'].year == 2025]
    listings_2025.sort(key=lambda x: x['listing_date'])

    print(f"\n{'='*80}")
    print(f"COINS LISTED IN 2025: {len(listings_2025)}")
    print(f"{'='*80}")

    print(f"\n{'Symbol':<18} {'Listed':<12} {'Days':>6} {'First $':>12} {'Now $':>12} {'Change':>10}")
    print("-" * 78)

    for coin in listings_2025:
        print(f"{coin['symbol']:<18} {coin['listing_date'].strftime('%Y-%m-%d'):<12} "
              f"{coin['days_listed']:>6} {coin['first_price']:>12.6f} "
              f"{coin['current_price']:>12.6f} {coin['change_pct']:>+9.1f}%")

    # Save
    df = pd.DataFrame(listings_2025)
    df['listing_date'] = df['listing_date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    df.to_csv('trading/listings_2025.csv', index=False)
    print(f"\n✅ Saved to trading/listings_2025.csv")

    # Stats
    if listings_2025:
        dumped = [c for c in listings_2025 if c['change_pct'] < -30]
        pumped = [c for c in listings_2025 if c['change_pct'] > 50]
        avg_change = sum(c['change_pct'] for c in listings_2025) / len(listings_2025)

        print(f"\n{'='*80}")
        print("STATISTICS")
        print(f"{'='*80}")
        print(f"Total 2025 listings: {len(listings_2025)}")
        print(f"Dumped >30%: {len(dumped)} ({len(dumped)/len(listings_2025)*100:.1f}%)")
        print(f"Pumped >50%: {len(pumped)} ({len(pumped)/len(listings_2025)*100:.1f}%)")
        print(f"Avg change: {avg_change:+.1f}%")

        print(f"\nListings by month:")
        months = {}
        for c in listings_2025:
            month = c['listing_date'].strftime('%Y-%m')
            months[month] = months.get(month, 0) + 1
        for m, count in sorted(months.items()):
            print(f"  {m}: {count} coins")

if __name__ == '__main__':
    asyncio.run(main())
