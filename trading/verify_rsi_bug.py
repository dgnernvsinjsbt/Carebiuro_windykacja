"""
Verify RSI Calculation Bug

Compare current bot RSI (SMA-based) vs correct Wilder's RSI (EMA-based)
"""

import pandas as pd
import asyncio
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'bingx-trading-bot'))

from execution.bingx_client import BingXClient
from data.indicators import rsi as rsi_sma  # Current buggy version


def rsi_correct(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Correct RSI implementation using Wilder's smoothing (EMA)

    This matches TradingView, BingX, and all standard RSI implementations
    """
    delta = data.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # First value: Simple average of first 'period' values
    avg_gain = pd.Series(index=data.index, dtype=float)
    avg_loss = pd.Series(index=data.index, dtype=float)

    # Initialize first average with SMA
    avg_gain.iloc[period] = gain.iloc[1:period+1].mean()
    avg_loss.iloc[period] = loss.iloc[1:period+1].mean()

    # Use Wilder's smoothing (EMA) for subsequent values
    for i in range(period + 1, len(data)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))

    return rsi_values


async def main():
    # Load config
    import yaml
    with open('bingx-trading-bot/config.yaml') as f:
        config = yaml.safe_load(f)

    # Initialize BingX client
    bingx = BingXClient(
        config['bingx']['api_key'],
        config['bingx']['api_secret'],
        config['bingx']['testnet'],
        config['bingx']['base_url']
    )

    # Fetch 1000PEPE last 300 hours
    symbol = '1000PEPE-USDT'
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (300 * 60 * 60 * 1000)

    print(f"Fetching {symbol} 1h candles...")
    klines = await bingx.get_klines(
        symbol=symbol,
        interval='1h',
        start_time=start_time,
        end_time=end_time,
        limit=300
    )

    if not klines:
        print("No data returned!")
        return

    # Build DataFrame
    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate both RSI versions
    print(f"\nCalculating RSI for {len(df)} candles...")
    df['rsi_buggy'] = rsi_sma(df['close'], 14)  # Current bot (SMA-based)
    df['rsi_correct'] = rsi_correct(df['close'], 14)  # Wilder's RSI (EMA-based)
    df['rsi_diff'] = df['rsi_correct'] - df['rsi_buggy']

    # Show last 24 hours
    print("\n" + "=" * 100)
    print("LAST 24 HOURS - RSI COMPARISON")
    print("=" * 100)
    print(f"{'Timestamp':<20} {'Close':<12} {'RSI (Buggy)':<15} {'RSI (Correct)':<15} {'Difference':<12}")
    print("-" * 100)

    for idx in range(-24, 0):
        row = df.iloc[idx]
        print(f"{row['timestamp'].strftime('%Y-%m-%d %H:%M'):<20} "
              f"${row['close']:<11.6f} "
              f"{row['rsi_buggy']:<15.2f} "
              f"{row['rsi_correct']:<15.2f} "
              f"{row['rsi_diff']:<+12.2f}")

    # Show statistics
    print("\n" + "=" * 100)
    print("STATISTICS")
    print("=" * 100)
    df_valid = df[df['rsi_buggy'].notna() & df['rsi_correct'].notna()]
    print(f"Mean absolute difference: {abs(df_valid['rsi_diff']).mean():.2f}")
    print(f"Max difference: {df_valid['rsi_diff'].max():.2f}")
    print(f"Min difference: {df_valid['rsi_diff'].min():.2f}")

    # Check if there was a SHORT signal in buggy version
    print("\n" + "=" * 100)
    print("CHECKING FOR FALSE SIGNALS")
    print("=" * 100)

    for i in range(-24, 0):
        curr = df.iloc[i]
        prev = df.iloc[i-1]

        # Check SHORT signal (RSI crosses below 65)
        if prev['rsi_buggy'] >= 65 and curr['rsi_buggy'] < 65:
            print(f"❌ BUGGY version: SHORT signal at {curr['timestamp']}")
            print(f"   RSI: {prev['rsi_buggy']:.2f} → {curr['rsi_buggy']:.2f}")
            print(f"   But correct RSI: {prev['rsi_correct']:.2f} → {curr['rsi_correct']:.2f}")
            print(f"   Max correct RSI in last 8h: {df.iloc[i-8:i+1]['rsi_correct'].max():.2f}")

        if prev['rsi_correct'] >= 65 and curr['rsi_correct'] < 65:
            print(f"✅ CORRECT version: SHORT signal at {curr['timestamp']}")
            print(f"   RSI: {prev['rsi_correct']:.2f} → {curr['rsi_correct']:.2f}")

        # Check LONG signal (RSI crosses above 30)
        if prev['rsi_buggy'] <= 30 and curr['rsi_buggy'] > 30:
            print(f"❌ BUGGY version: LONG signal at {curr['timestamp']}")
            print(f"   RSI: {prev['rsi_buggy']:.2f} → {curr['rsi_buggy']:.2f}")
            print(f"   But correct RSI: {prev['rsi_correct']:.2f} → {curr['rsi_correct']:.2f}")

        if prev['rsi_correct'] <= 27 and curr['rsi_correct'] > 27:  # PEPE uses 27 threshold
            print(f"✅ CORRECT version: LONG signal at {curr['timestamp']}")
            print(f"   RSI: {prev['rsi_correct']:.2f} → {curr['rsi_correct']:.2f}")


if __name__ == '__main__':
    asyncio.run(main())
