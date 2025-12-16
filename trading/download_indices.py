"""
Download S&P 500 and NASDAQ 100 hourly data for RSI backtesting
"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

print('='*80)
print('📊 DOWNLOADING S&P 500 & NASDAQ 100 DATA')
print('='*80)
print()

# Download 3 months of 1h data
end_date = datetime.now()
start_date = end_date - timedelta(days=90)

tickers = {
    'ES=F': 'S&P 500 Futures (ES)',
    'NQ=F': 'NASDAQ 100 Futures (NQ)',
}

for ticker, name in tickers.items():
    print(f'Downloading {name}...')

    try:
        # Download 1h data
        df = yf.download(ticker, start=start_date, end=end_date, interval='1h', progress=False)

        if df.empty:
            print(f'  ❌ No data returned for {ticker}')
            continue

        # Rename columns to match our format
        df = df.reset_index()

        # Handle MultiIndex columns (if present)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0].lower() if isinstance(col, tuple) else col.lower() for col in df.columns]
        else:
            df.columns = [col.lower() for col in df.columns]

        df = df.rename(columns={'datetime': 'timestamp'})

        # Add indicators will be done in backtest
        # Clean ticker name for filename (remove =F)
        clean_ticker = ticker.replace('=F', '').lower()
        filename = f'trading/{clean_ticker}_futures_1h_90d.csv'
        df.to_csv(filename, index=False)

        print(f'  ✅ Saved {len(df)} candles to {filename}')
        print(f'     Period: {df["timestamp"].min()} to {df["timestamp"].max()}')

    except Exception as e:
        print(f'  ❌ Error downloading {ticker}: {e}')

print()
print('✅ Download complete!')
