#!/usr/bin/env python3
"""
Download XLM-USDT 15m data from BingX (last 3 months)
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

print("="*80)
print("DOWNLOADING XLM-USDT 15m DATA FROM BINGX")
print("="*80)

# BingX public API endpoint
base_url = "https://open-api.bingx.com"
endpoint = "/openApi/swap/v2/quote/klines"

symbol = "XLM-USDT"
interval = "15m"

# Calculate time range (last 3 months)
end_time = datetime.now()
start_time = end_time - timedelta(days=90)

# Convert to milliseconds
start_ts = int(start_time.timestamp() * 1000)
end_ts = int(end_time.timestamp() * 1000)

print(f"\n📊 Fetching data:")
print(f"   Symbol: {symbol}")
print(f"   Interval: {interval}")
print(f"   Period: {start_time.date()} to {end_time.date()}")
print(f"   Start TS: {start_ts}")
print(f"   End TS: {end_ts}")

all_candles = []
current_start = start_ts
batch_count = 0

# BingX returns max 1440 candles per request
# 15m candles: 96 per day, 1440 = 15 days worth
max_candles_per_request = 1440

while current_start < end_ts:
    batch_count += 1

    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': current_start,
        'endTime': end_ts,
        'limit': max_candles_per_request
    }

    print(f"\n   Batch {batch_count}: Fetching from {datetime.fromtimestamp(current_start/1000).date()}...", end=" ")

    try:
        response = requests.get(base_url + endpoint, params=params)

        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            break

        data = response.json()

        if 'data' not in data or not data['data']:
            print("No more data")
            break

        candles = data['data']
        print(f"Got {len(candles)} candles")

        if len(candles) == 0:
            break

        # Add to collection
        all_candles.extend(candles)

        # Update start time for next batch (last candle's time + 1ms)
        last_candle_time = int(candles[-1]['time'])
        current_start = last_candle_time + 1

        # Check if we got less than limit (means we're done)
        if len(candles) < max_candles_per_request:
            print(f"   Got less than limit, done!")
            break

        # Rate limiting
        time.sleep(0.2)

    except Exception as e:
        print(f"❌ Exception: {e}")
        break

print(f"\n✅ Total candles fetched: {len(all_candles)}")

if len(all_candles) == 0:
    print("❌ No data fetched!")
    exit(1)

# Convert to DataFrame
df = pd.DataFrame(all_candles)

# BingX format: [time, open, high, low, close, volume, ...]
df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
df = df.rename(columns={
    'open': 'open',
    'high': 'high',
    'low': 'low',
    'close': 'close',
    'volume': 'volume'
})

df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
df = df.sort_values('timestamp').reset_index(drop=True)

# Convert to float
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# Calculate ATR for stats
import numpy as np
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
output_file = 'trading/xlm_3months_bingx_15m.csv'
df.to_csv(output_file, index=False)

print(f"\n💾 Saved to: {output_file}")
print(f"\n📊 XLM-USDT Stats:")
print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Candles: {len(df)}")
print(f"   Avg Price: ${df['close'].mean():.4f}")
print(f"   Avg ATR: ${df['atr'].mean():.6f}")
print(f"   Avg ATR %: {df['atr_pct'].mean():.3f}%")
print(f"   Min Price: ${df['close'].min():.4f}")
print(f"   Max Price: ${df['close'].max():.4f}")

# Compare to other assets
print(f"\n🔥 VOLATILITY COMPARISON:")
print(f"   XLM ATR%:      {df['atr_pct'].mean():.3f}%")
print(f"   MELANIA ATR%:  0.943%")
print(f"   NASDAQ ATR%:   0.202%")
print(f"   S&P 500 ATR%:  0.151%")

print("\n✅ XLM data ready for backtesting!")
print("="*80)
