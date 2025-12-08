#!/usr/bin/env python3
"""
Download GOAT/USDT 1-minute data from various exchanges
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time

def download_goat_data():
    """Try to download GOAT data from multiple exchanges"""

    exchanges_to_try = [
        ('gate', ccxt.gate),
        ('mexc', ccxt.mexc),
        ('kucoin', ccxt.kucoin),
        ('bybit', ccxt.bybit),
    ]

    for exchange_name, exchange_class in exchanges_to_try:
        try:
            print(f"\n{'='*60}")
            print(f"Trying {exchange_name.upper()}...")
            print(f"{'='*60}")

            exchange = exchange_class({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })

            # Load markets
            markets = exchange.load_markets()

            # Check if GOAT/USDT exists
            symbol = 'GOAT/USDT'
            if symbol not in markets:
                print(f"❌ {symbol} not available on {exchange_name}")
                continue

            print(f"✅ {symbol} found on {exchange_name}")

            # Fetch OHLCV data
            # Try to get 30 days of 1m data
            since = exchange.parse8601((datetime.now() - timedelta(days=30)).isoformat())

            print(f"Fetching 1m candles...")
            all_candles = []

            while True:
                try:
                    candles = exchange.fetch_ohlcv(
                        symbol,
                        timeframe='1m',
                        since=since,
                        limit=1000
                    )

                    if not candles:
                        break

                    all_candles.extend(candles)
                    print(f"  Downloaded {len(all_candles):,} candles...")

                    # Update since to last candle timestamp
                    since = candles[-1][0] + 1

                    # Check if we've reached current time
                    if candles[-1][0] >= exchange.milliseconds() - 60000:
                        break

                    time.sleep(exchange.rateLimit / 1000)

                except Exception as e:
                    print(f"  Error fetching: {e}")
                    break

            if not all_candles:
                print(f"❌ No data downloaded from {exchange_name}")
                continue

            # Convert to DataFrame
            df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)

            print(f"\n✅ Successfully downloaded {len(df):,} candles from {exchange_name}")
            print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            print(f"   Days: {(df['timestamp'].max() - df['timestamp'].min()).days}")

            # Save to CSV
            filename = f'/workspaces/Carebiuro_windykacja/trading/goat_usdt_1m_{exchange_name}.csv'
            df.to_csv(filename, index=False)
            print(f"\n💾 Saved to: {filename}")

            # Show sample stats
            print(f"\nSample statistics:")
            print(f"  Price range: ${df['close'].min():.6f} - ${df['close'].max():.6f}")
            print(f"  Current price: ${df['close'].iloc[-1]:.6f}")
            print(f"  Avg volume: {df['volume'].mean():,.0f}")

            return df

        except Exception as e:
            print(f"❌ Error with {exchange_name}: {e}")
            continue

    print("\n❌ Could not download GOAT data from any exchange")
    return None

if __name__ == "__main__":
    df = download_goat_data()
    if df is not None:
        print("\n✅ SUCCESS! GOAT data downloaded and ready for backtesting")
    else:
        print("\n❌ FAILED to download GOAT data")
