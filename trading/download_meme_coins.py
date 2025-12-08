#!/usr/bin/env python3
"""
Download 1-minute candle data for meme coins from LBank using ccxt
Last 30 days of data
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time
from pathlib import Path

# Coins to download (excluding MELANIA due to low liquidity)
COINS = ['PNUT', 'GRIFFAIN', 'GOAT', 'PENGU', 'WIF', 'MOODENG']

def download_lbank_data(symbol: str, days: int = 30) -> pd.DataFrame:
    """Download historical data from LBank using ccxt"""

    # Initialize LBank exchange
    exchange = ccxt.lbank({
        'enableRateLimit': True,
    })

    # Format symbol for ccxt
    pair = f"{symbol}/USDT"

    # Calculate date range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    print(f"  Downloading {pair} from LBank...", end=" ", flush=True)

    all_candles = []
    current_start = start_time

    # LBank allows fetching 1000 candles at a time
    chunk_size = timedelta(minutes=1000)

    while current_start < end_time:
        try:
            since = int(current_start.timestamp() * 1000)

            candles = exchange.fetch_ohlcv(
                symbol=pair,
                timeframe='1m',
                since=since,
                limit=1000
            )

            if candles:
                all_candles.extend(candles)
                # Move forward based on last candle timestamp
                last_ts = candles[-1][0]
                current_start = datetime.fromtimestamp(last_ts / 1000) + timedelta(minutes=1)
            else:
                current_start += chunk_size

            time.sleep(exchange.rateLimit / 1000)

        except Exception as e:
            error_msg = str(e)
            if 'does not have market' in error_msg.lower() or 'not found' in error_msg.lower():
                print(f"✗ Not listed on LBank")
                return None
            print(f"✗ Error: {error_msg[:50]}")
            return None

    if not all_candles:
        print("✗ No data")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)

    days_actual = (df['timestamp'].max() - df['timestamp'].min()).days
    print(f"✓ {len(df):,} candles ({days_actual} days)")

    return df


def main():
    print("=" * 70)
    print("DOWNLOADING MEME COIN DATA - 1 MINUTE CANDLES, LAST 30 DAYS")
    print("Source: LBank via ccxt")
    print("=" * 70)
    print()

    output_dir = Path('/workspaces/Carebiuro_windykacja/trading')

    results = {}

    for coin in COINS:
        print(f"\n[{coin}]")

        df = download_lbank_data(coin, days=30)

        if df is not None and len(df) > 0:
            # Save to CSV
            filename = output_dir / f"{coin.lower()}_usdt_1m_lbank.csv"
            df.to_csv(filename, index=False)

            days_actual = (df['timestamp'].max() - df['timestamp'].min()).days
            results[coin] = {
                'candles': len(df),
                'days': days_actual,
                'start': df['timestamp'].min(),
                'end': df['timestamp'].max(),
                'file': str(filename)
            }
            print(f"  Saved to: {filename}")
        else:
            results[coin] = {'error': 'No data available'}

    # Summary
    print()
    print("=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Coin':<12} {'Candles':>10} {'Days':>6} {'Status':<20}")
    print("-" * 50)

    for coin, info in results.items():
        if 'error' in info:
            print(f"{coin:<12} {'N/A':>10} {'N/A':>6} ✗ {info['error']}")
        else:
            print(f"{coin:<12} {info['candles']:>10,} {info['days']:>6} ✓ Downloaded")

    print()
    print("Done!")


if __name__ == "__main__":
    main()
