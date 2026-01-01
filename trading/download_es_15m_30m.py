"""
Download ES Futures 15-minute and 30-minute data
Test if faster timeframes capture more volatility
"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

print('='*80)
print('📊 DOWNLOADING ES FUTURES - 15MIN & 30MIN DATA')
print('='*80)
print()

# Download 60 days (yfinance limit for 15m/30m intervals)
end_date = datetime.now()
start_date = end_date - timedelta(days=60)

timeframes = {
    '15m': '15-minute',
    '30m': '30-minute'
}

for interval, name in timeframes.items():
    print(f'Downloading ES Futures {name} data...')

    try:
        # Download data
        df = yf.download('ES=F', start=start_date, end=end_date, interval=interval, progress=False)

        if df.empty:
            print(f'  ❌ No data returned for {interval}')
            continue

        # Reset index and fix columns
        df = df.reset_index()

        # Handle MultiIndex columns (if present)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]

        df = df.rename(columns={'datetime': 'timestamp'})

        # Save to CSV
        filename = f'trading/es_futures_{interval}_60d.csv'
        df.to_csv(filename, index=False)

        print(f'  ✅ Saved {len(df)} candles to {filename}')
        print(f'     Period: {df["timestamp"].min()} to {df["timestamp"].max()}')
        print(f'     Candles per day: ~{len(df) / 60:.0f}')
        print()

    except Exception as e:
        print(f'  ❌ Error downloading {interval}: {e}')
        print()

print('✅ Download complete!')
