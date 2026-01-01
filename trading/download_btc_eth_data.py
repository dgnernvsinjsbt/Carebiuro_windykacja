#!/usr/bin/env python3
"""
Download BTC/USDT and ETH/USDT 1-minute chart data from LBank
Same format as existing PI, PENGU, FARTCOIN data
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time

def download_lbank_data(symbol, days=30):
    """
    Download historical 1m candles from LBank

    Args:
        symbol: Trading pair (e.g., 'BTC/USDT', 'ETH/USDT')
        days: Number of days to fetch (default 30)
    """
    print(f"\n{'='*80}")
    print(f"Downloading {symbol} data from LBank")
    print(f"{'='*80}\n")

    # Initialize LBank exchange
    exchange = ccxt.lbank({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot',
        }
    })

    # Calculate date range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    print(f"Period: {start_time} to {end_time}")
    print(f"Timeframe: 1 minute")
    print(f"Estimated candles: ~{days * 24 * 60:,}")
    print()

    # Fetch data in chunks (LBank limit is 2000 candles per request)
    all_candles = []
    current_time = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)

    chunk_count = 0
    while current_time < end_timestamp:
        try:
            chunk_count += 1
            print(f"Fetching chunk #{chunk_count}... ", end='', flush=True)

            # Fetch OHLCV data
            candles = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe='1m',
                since=current_time,
                limit=2000
            )

            if not candles:
                print("No more data")
                break

            print(f"Got {len(candles)} candles")
            all_candles.extend(candles)

            # Move to next chunk
            current_time = candles[-1][0] + 60000  # +1 minute in milliseconds

            # Rate limiting
            time.sleep(exchange.rateLimit / 1000)

        except Exception as e:
            print(f"Error: {e}")
            break

    print(f"\nTotal candles fetched: {len(all_candles):,}")

    # Convert to DataFrame
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Remove duplicates
    df = df.drop_duplicates(subset=['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    print(f"After deduplication: {len(df):,} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"First candle: O={df['open'].iloc[0]:.2f} H={df['high'].iloc[0]:.2f} L={df['low'].iloc[0]:.2f} C={df['close'].iloc[0]:.2f}")
    print(f"Last candle:  O={df['open'].iloc[-1]:.2f} H={df['high'].iloc[-1]:.2f} L={df['low'].iloc[-1]:.2f} C={df['close'].iloc[-1]:.2f}")

    return df

def main():
    # Download BTC/USDT
    btc_df = download_lbank_data('BTC/USDT', days=30)
    btc_filename = 'btc_usdt_1m_lbank.csv'
    btc_df.to_csv(btc_filename, index=False)
    print(f"\n✓ Saved to {btc_filename}")

    # Download ETH/USDT
    eth_df = download_lbank_data('ETH/USDT', days=30)
    eth_filename = 'eth_usdt_1m_lbank.csv'
    eth_df.to_csv(eth_filename, index=False)
    print(f"\n✓ Saved to {eth_filename}")

    print("\n" + "="*80)
    print("DOWNLOAD COMPLETE")
    print("="*80)
    print(f"\nBTC/USDT: {len(btc_df):,} candles → {btc_filename}")
    print(f"ETH/USDT: {len(eth_df):,} candles → {eth_filename}")
    print()

if __name__ == '__main__':
    main()
