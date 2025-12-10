#!/usr/bin/env python3
"""
Extract candle data from bot logs and compare with BingX API data.
"""
import re
import pandas as pd
from datetime import datetime

def extract_candles_from_logs(log_file: str) -> pd.DataFrame:
    """Extract candle data from trading-engine.log"""

    candles = []
    current_candle = {}

    with open(log_file, 'r') as f:
        for line in f:
            # Match symbol and timestamp line
            symbol_match = re.search(r'(FARTCOIN-USDT|TRUMPSOL-USDT) - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if symbol_match:
                if current_candle:
                    candles.append(current_candle)
                current_candle = {
                    'symbol': symbol_match.group(1),
                    'timestamp': symbol_match.group(2)
                }

            # Extract OHLCV data
            if 'Open:' in line:
                current_candle['open'] = float(re.search(r'\$([0-9.]+)', line).group(1))
            elif 'High:' in line:
                current_candle['high'] = float(re.search(r'\$([0-9.]+)', line).group(1))
            elif 'Low:' in line:
                current_candle['low'] = float(re.search(r'\$([0-9.]+)', line).group(1))
            elif 'Close:' in line:
                current_candle['close'] = float(re.search(r'\$([0-9.]+)', line).group(1))
            elif 'Volume:' in line:
                vol_match = re.search(r'Volume:\s+([\d,]+)', line)
                if vol_match:
                    current_candle['volume'] = float(vol_match.group(1).replace(',', ''))

    # Add last candle
    if current_candle and len(current_candle) > 2:
        candles.append(current_candle)

    df = pd.DataFrame(candles)

    # Filter out incomplete candles
    df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Sort by symbol and timestamp
    df = df.sort_values(['symbol', 'timestamp'])

    return df

if __name__ == '__main__':
    log_file = '/workspaces/Carebiuro_windykacja/bingx-trading-bot/logs/trading-engine.log'

    print("📊 Extracting candle data from bot logs...")
    df = extract_candles_from_logs(log_file)

    print(f"\n✅ Extracted {len(df)} candles")
    print(f"\nSymbols: {df['symbol'].unique()}")
    print(f"\nTime range:")
    print(f"  Start: {df['timestamp'].min()}")
    print(f"  End:   {df['timestamp'].max()}")
    print(f"  Duration: {df['timestamp'].max() - df['timestamp'].min()}")

    # Save to CSV
    output_file = 'bot_data_extracted.csv'
    df.to_csv(output_file, index=False)
    print(f"\n💾 Saved to {output_file}")

    # Show sample
    print(f"\n📋 Sample data:")
    print(df.head(10).to_string(index=False))

    # Show stats per symbol
    print(f"\n📈 Stats per symbol:")
    for symbol in df['symbol'].unique():
        symbol_df = df[df['symbol'] == symbol]
        print(f"\n{symbol}:")
        print(f"  Candles: {len(symbol_df)}")
        print(f"  First: {symbol_df['timestamp'].min()}")
        print(f"  Last: {symbol_df['timestamp'].max()}")
