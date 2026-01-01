"""
Download July 1 - August 31, 2025 data for all coins
to test strategies on out-of-sample period BEFORE training
"""

import ccxt
import pandas as pd
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({
    'enableRateLimit': True,
})

# All coins to download
coins = [
    'MOODENG-USDT',
    'PEPE-USDT',
    'DOGE-USDT',
    'AIXBT-USDT',
    'MELANIA-USDT',
    'XLM-USDT',
    'TRUMPSOL-USDT',
    'UNI-USDT',
    'CRV-USDT',
    'FARTCOIN-USDT'
]

# Date range
start_date = datetime(2025, 7, 1, tzinfo=timezone.utc)
end_date = datetime(2025, 8, 31, 23, 59, 59, tzinfo=timezone.utc)

start_ts = int(start_date.timestamp() * 1000)
end_ts = int(end_date.timestamp() * 1000)

print(f"Downloading data from {start_date} to {end_date}")
print("=" * 80)

for symbol in coins:
    print(f"\n{symbol}...")

    try:
        # Download 1-hour data for RSI strategies
        all_candles = []
        current_ts = start_ts

        while current_ts < end_ts:
            candles = exchange.fetch_ohlcv(
                symbol,
                timeframe='1h',
                since=current_ts,
                limit=1000
            )

            if not candles:
                break

            all_candles.extend(candles)
            current_ts = candles[-1][0] + 3600000  # +1 hour in ms

            time.sleep(0.5)  # Rate limit

        # Convert to DataFrame
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

        # Filter to exact date range
        df = df[(df['timestamp'] >= pd.Timestamp(start_date)) & (df['timestamp'] <= pd.Timestamp(end_date))]

        # Save
        filename = f"trading/{symbol.lower().replace('-', '_')}_july_aug_2025_1h.csv"
        df.to_csv(filename, index=False)

        print(f"  ✅ {len(df)} bars saved to {filename}")
        print(f"     Range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    except Exception as e:
        print(f"  ❌ Error downloading {symbol}: {e}")

print("\n" + "=" * 80)
print("Download complete!")
