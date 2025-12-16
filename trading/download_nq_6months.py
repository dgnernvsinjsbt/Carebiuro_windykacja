"""
Download 6 months of NQ Futures data for walk-forward testing
Need extra historical data for 60-90 day lookback windows
"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

print('='*80)
print('📊 DOWNLOADING NQ FUTURES - 6 MONTHS (180 DAYS)')
print('='*80)
print()

# Download 180 days of data
end_date = datetime.now()
start_date = end_date - timedelta(days=180)

print(f'Downloading NQ=F from {start_date.date()} to {end_date.date()}...')
print()

try:
    # Download 1h data
    df = yf.download('NQ=F', start=start_date, end=end_date, interval='1h', progress=False)

    if df.empty:
        print('❌ No data returned')
    else:
        # Reset index and fix columns
        df = df.reset_index()

        # Handle MultiIndex columns (if present)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]

        df = df.rename(columns={'datetime': 'timestamp'})

        # Save to CSV
        filename = 'trading/nq_futures_1h_180d.csv'
        df.to_csv(filename, index=False)

        print(f'✅ Saved {len(df)} candles to {filename}')
        print(f'   Period: {df["timestamp"].min()} to {df["timestamp"].max()}')
        print(f'   Days covered: ~{(df["timestamp"].max() - df["timestamp"].min()).days}')
        print(f'   Candles per day: ~{len(df) / 180:.0f}')
        print()

        # Show data distribution
        print('Data breakdown:')
        print(f'   First 90 days: {len(df[df["timestamp"] < df["timestamp"].min() + timedelta(days=90)])} candles (optimization window)')
        print(f'   Last 90 days: {len(df[df["timestamp"] >= df["timestamp"].min() + timedelta(days=90)])} candles (trading window)')
        print()

except Exception as e:
    print(f'❌ Error downloading: {e}')

print('✅ Download complete!')
print()
print('Now you can run walk-forward with:')
print('  - 30-day lookback (original)')
print('  - 60-day lookback (2 months)')
print('  - 90-day lookback (3 months)')
