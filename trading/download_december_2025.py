"""
Download December 2025 data up to today (Dec 16)
"""
import ccxt
import pandas as pd
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

# Dec 1 to Dec 16
start = datetime(2025, 12, 1, tzinfo=timezone.utc)
end = datetime(2025, 12, 16, tzinfo=timezone.utc)

start_ts = int(start.timestamp() * 1000)
end_ts = int(end.timestamp() * 1000)

all_candles = []
current_ts = start_ts

print('Downloading December 1-16, 2025...')

while current_ts < end_ts:
    try:
        candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
        if not candles:
            break

        all_candles.extend(candles)
        current_ts = candles[-1][0] + (15 * 60 * 1000)
        print(f'  Downloaded {len(all_candles)} bars...')
        time.sleep(0.5)

    except Exception as e:
        print(f'  Error: {e}')
        time.sleep(2)
        continue

if all_candles:
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= start.replace(tzinfo=None)) &
            (df['timestamp'] < end.replace(tzinfo=None))].copy()
    df = df.sort_values('timestamp').reset_index(drop=True)

    df.to_csv('melania_december_2025_15m.csv', index=False)
    print(f'✅ Saved: melania_december_2025_15m.csv ({len(df)} bars)')
else:
    print('❌ No data available')
