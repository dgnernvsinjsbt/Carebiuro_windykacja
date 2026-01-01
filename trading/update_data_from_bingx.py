#!/usr/bin/env python3
"""
Update historical data from BingX public API
Run this on your server to refresh CSV files with latest candles
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time

BASE_URL = "https://open-api.bingx.com"
DATA_DIR = Path(__file__).parent

# Coins to update
COINS = {
    'DOGE-USDT': 'doge_1h_jun_dec_2025.csv',
    'FARTCOIN-USDT': 'fartcoin_1h_jun_dec_2025.csv',
    'PENGU-USDT': 'pengu_1h_jun_dec_2025.csv',
    'ETH-USDT': 'eth_1h_2025.csv',
    'UNI-USDT': 'uni_1h_jun_dec_2025.csv',
    'PI-USDT': 'pi_1h_jun_dec_2025.csv',
    'CRV-USDT': 'crv_1h_jun_dec_2025.csv',
    'AIXBT-USDT': 'aixbt_1h_jun_dec_2025.csv',
}


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 500, start_time: int = None):
    """Fetch klines from BingX public API"""
    endpoint = f"{BASE_URL}/openApi/swap/v3/quote/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    if start_time:
        params["startTime"] = start_time

    resp = requests.get(endpoint, params=params, timeout=30)
    data = resp.json()

    if 'data' in data and data['data']:
        return data['data']
    else:
        print(f"  Error fetching {symbol}: {data}")
        return None


def update_coin(symbol: str, filename: str):
    """Update CSV file with latest candles"""
    filepath = DATA_DIR / filename

    # Load existing data
    if filepath.exists():
        df_existing = pd.read_csv(filepath)
        df_existing['timestamp'] = pd.to_datetime(df_existing['timestamp'])
        last_ts = df_existing['timestamp'].max()
        print(f"  Existing data ends: {last_ts}")

        # Fetch from last timestamp
        start_time = int(last_ts.timestamp() * 1000) + 3600000  # +1 hour
    else:
        print(f"  No existing file, fetching last 500 candles")
        df_existing = None
        start_time = None

    # Fetch new data
    klines = fetch_klines(symbol, "1h", 500, start_time)

    if not klines:
        print(f"  No new data available")
        return False

    # Convert to DataFrame
    rows = []
    for k in klines:
        rows.append({
            'timestamp': datetime.fromtimestamp(k['time'] / 1000),
            'open': float(k['open']),
            'high': float(k['high']),
            'low': float(k['low']),
            'close': float(k['close']),
            'volume': float(k['volume'])
        })

    df_new = pd.DataFrame(rows)
    print(f"  Fetched {len(df_new)} new candles")
    print(f"  New data range: {df_new['timestamp'].min()} to {df_new['timestamp'].max()}")

    # Merge with existing
    if df_existing is not None:
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined = df_combined.drop_duplicates(subset=['timestamp'], keep='last')
        df_combined = df_combined.sort_values('timestamp').reset_index(drop=True)
    else:
        df_combined = df_new

    # Save
    df_combined.to_csv(filepath, index=False)
    print(f"  ✅ Saved {len(df_combined)} total candles to {filename}")

    return True


if __name__ == '__main__':
    print("=" * 60)
    print("UPDATING DATA FROM BINGX")
    print("=" * 60)
    print(f"Current time: {datetime.now()}")

    success = 0
    for symbol, filename in COINS.items():
        print(f"\n{symbol}:")
        try:
            if update_coin(symbol, filename):
                success += 1
            time.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"\n{'=' * 60}")
    print(f"Updated {success}/{len(COINS)} coins")
    print("=" * 60)
