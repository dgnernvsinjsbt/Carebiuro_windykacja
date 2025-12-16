"""
Download fresh 90-day 1h data for all 9 coins
"""
import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time

def download_ohlcv(symbol, timeframe='1h', days=90):
    """Download OHLCV data from BingX"""
    exchange = ccxt.bingx({
        'enableRateLimit': True,
    })

    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    print(f'Downloading {symbol} {timeframe} from {start_time.date()} to {end_time.date()}...')

    all_candles = []
    since = int(start_time.timestamp() * 1000)

    while True:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)

            if not candles:
                break

            all_candles.extend(candles)

            # Update since to last candle time + 1ms
            since = candles[-1][0] + 1

            # Check if we've reached the end
            if candles[-1][0] >= int(end_time.timestamp() * 1000):
                break

            print(f'  Downloaded {len(all_candles)} candles...', end='\r')
            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f'\n  Error: {e}')
            time.sleep(2)
            continue

    if not all_candles:
        return None

    # Convert to DataFrame
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Remove duplicates
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)

    # Filter to exact date range
    df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]

    print(f'\n  ✅ Downloaded {len(df)} candles ({df["timestamp"].min()} to {df["timestamp"].max()})')

    return df

# Coins to download
COINS = {
    'CRV-USDT': 'CRV/USDT:USDT',
    'MELANIA-USDT': 'MELANIA/USDT:USDT',
    'AIXBT-USDT': 'AIXBT/USDT:USDT',
    'TRUMPSOL-USDT': 'TRUMP/USDT:USDT',
    'UNI-USDT': 'UNI/USDT:USDT',
    'DOGE-USDT': 'DOGE/USDT:USDT',
    'XLM-USDT': 'XLM/USDT:USDT',
    'MOODENG-USDT': 'MOODENG/USDT:USDT',
    'PEPE-USDT': '1000PEPE/USDT:USDT',
}

print('='*100)
print('📥 DOWNLOADING 90-DAY 1H DATA FOR ALL COINS')
print('='*100)
print()

success_count = 0
failed = []

for coin_name, symbol in COINS.items():
    print(f'\n{coin_name}:')
    print('-'*100)

    try:
        df = download_ohlcv(symbol, timeframe='1h', days=90)

        if df is not None and len(df) > 0:
            # Calculate expected candles (90 days * 24 hours = 2160)
            expected_candles = 90 * 24
            actual_candles = len(df)
            coverage_pct = (actual_candles / expected_candles) * 100

            print(f'  Coverage: {actual_candles}/{expected_candles} candles ({coverage_pct:.1f}%)')

            # Save
            filename = f'bingx-trading-bot/trading/{coin_name.lower().replace("-", "_")}_90d_1h.csv'
            df.to_csv(filename, index=False)
            print(f'  💾 Saved: {filename}')

            success_count += 1
        else:
            print(f'  ❌ No data downloaded')
            failed.append(coin_name)

    except Exception as e:
        print(f'  ❌ Error: {e}')
        failed.append(coin_name)

    time.sleep(1)  # Rate limiting between coins

print()
print('='*100)
print('📊 DOWNLOAD SUMMARY')
print('='*100)
print()
print(f'✅ Successful: {success_count}/{len(COINS)}')
if failed:
    print(f'❌ Failed: {", ".join(failed)}')
print()
