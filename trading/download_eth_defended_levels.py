import requests
import pandas as pd
from datetime import datetime, timedelta
import time

def download_lbank_1m_data(symbol='eth_usdt', days=30):
    """Download 1-minute data from LBank API"""
    print(f"Downloading {symbol} 1m data for last {days} days from LBank...")

    # LBank uses millisecond timestamps
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

    all_candles = []
    current_end = end_time

    while current_end > start_time:
        try:
            url = f"https://www.lbkex.net/v2/supplement/kline.do"
            params = {
                'symbol': symbol,
                'type': 'minute1',
                'time': current_end,
                'size': 2000  # Max per request
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if 'data' not in data or not data['data']:
                print("No more data available")
                break

            candles = data['data']
            all_candles.extend(candles)

            # Update end time for next batch
            oldest_timestamp = min([int(c[0]) for c in candles])
            current_end = oldest_timestamp - 60000  # Move back 1 minute

            print(f"Downloaded {len(all_candles)} candles so far... (oldest: {datetime.fromtimestamp(oldest_timestamp/1000)})")

            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)
            continue

    # Convert to DataFrame
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms')

    # Convert prices and volume to float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Sort by timestamp ascending
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Remove duplicates
    df = df.drop_duplicates(subset='timestamp', keep='first')

    print(f"\nTotal candles downloaded: {len(df)}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

    return df

if __name__ == '__main__':
    # Download 60 days to have more data for pattern detection
    df = download_lbank_1m_data('eth_usdt', days=60)

    # Save to CSV
    output_file = '/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank_fresh.csv'
    df.to_csv(output_file, index=False)
    print(f"\nSaved to {output_file}")

    # Show sample
    print("\nFirst 5 rows:")
    print(df.head())
    print("\nLast 5 rows:")
    print(df.tail())
