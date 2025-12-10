#!/usr/bin/env python3
"""
Download BingX candle data for the same time period as bot logs to verify data accuracy.
"""
import requests
import pandas as pd
from datetime import datetime, timezone
import time

def download_bingx_klines(symbol: str, start_time: datetime, end_time: datetime, interval: str = '1m'):
    """
    Download klines from BingX API.

    Args:
        symbol: Trading pair (e.g., 'FARTCOIN-USDT')
        start_time: Start datetime (UTC)
        end_time: End datetime (UTC)
        interval: Kline interval (1m, 5m, etc.)
    """

    base_url = 'https://open-api.bingx.com'
    endpoint = '/openApi/swap/v2/quote/klines'

    # Convert to milliseconds
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)

    all_candles = []
    current_start = start_ms

    print(f"📥 Downloading {symbol} from {start_time} to {end_time}...")

    while current_start < end_ms:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_start,
            'endTime': end_ms,
            'limit': 1000  # Max per request
        }

        try:
            response = requests.get(base_url + endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != 0:
                print(f"❌ API Error: {data}")
                break

            candles = data.get('data', [])
            if not candles:
                break

            all_candles.extend(candles)

            # Update start time for next batch
            last_time = int(candles[-1]['time'])
            if last_time <= current_start:
                break
            current_start = last_time + 60000  # +1 minute

            print(f"  Downloaded {len(candles)} candles (total: {len(all_candles)})")
            time.sleep(0.2)  # Rate limit

        except Exception as e:
            print(f"❌ Error: {e}")
            break

    # Convert to DataFrame
    df = pd.DataFrame(all_candles)

    if len(df) > 0:
        df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
        df = df.rename(columns={
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        })

        # Convert to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        df['symbol'] = symbol
        df = df[['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.sort_values('timestamp')

    return df

if __name__ == '__main__':
    # Download for the same period as bot logs
    start_time = datetime(2025, 12, 9, 21, 42, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 12, 9, 22, 31, 0, tzinfo=timezone.utc)

    # Download both symbols
    symbols = ['FARTCOIN-USDT', 'TRUMPSOL-USDT']

    all_data = []
    for symbol in symbols:
        df = download_bingx_klines(symbol, start_time, end_time, '1m')
        all_data.append(df)

    # Combine
    combined = pd.concat(all_data, ignore_index=True)

    print(f"\n✅ Downloaded {len(combined)} candles total")
    print(f"\nSymbols: {combined['symbol'].unique()}")
    print(f"\nTime range:")
    print(f"  Start: {combined['timestamp'].min()}")
    print(f"  End:   {combined['timestamp'].max()}")

    # Save to CSV
    output_file = 'bingx_verification_data.csv'
    combined.to_csv(output_file, index=False)
    print(f"\n💾 Saved to {output_file}")

    # Show sample
    print(f"\n📋 Sample BingX data:")
    print(combined.head(10).to_string(index=False))

    # Show stats per symbol
    print(f"\n📈 Stats per symbol:")
    for symbol in combined['symbol'].unique():
        symbol_df = combined[combined['symbol'] == symbol]
        print(f"\n{symbol}:")
        print(f"  Candles: {len(symbol_df)}")
        print(f"  Price range: ${symbol_df['low'].min():.6f} - ${symbol_df['high'].max():.6f}")
        print(f"  First: {symbol_df['timestamp'].min()}")
        print(f"  Last: {symbol_df['timestamp'].max()}")
