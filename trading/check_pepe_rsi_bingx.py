"""
Fetch 1000PEPE-USDT from BingX and calculate correct Wilder's RSI
Show last 4 hours
"""

import pandas as pd
import asyncio
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'bingx-trading-bot'))

from execution.bingx_client import BingXClient


def rsi_correct(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Correct Wilder's RSI implementation (EMA-based)
    Matches TradingView, BingX, and all standard charting platforms
    """
    delta = data.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Initialize series
    avg_gain = pd.Series(index=data.index, dtype=float)
    avg_loss = pd.Series(index=data.index, dtype=float)

    # First value: SMA of first 'period' values
    avg_gain.iloc[period] = gain.iloc[1:period+1].mean()
    avg_loss.iloc[period] = loss.iloc[1:period+1].mean()

    # Subsequent values: Wilder's smoothing (EMA with alpha=1/period)
    for i in range(period + 1, len(data)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))

    return rsi_values


async def main():
    # Load config
    import yaml
    config_files = [
        'bingx-trading-bot/config_rsi_swing.yaml',
        'bingx-trading-bot/config_portfolio_test.yaml',
        'bingx-trading-bot/config.example.yaml'
    ]

    config = None
    for config_file in config_files:
        try:
            with open(config_file) as f:
                config = yaml.safe_load(f)
                print(f"Loaded config from {config_file}")
                break
        except FileNotFoundError:
            continue

    if not config:
        print("Error: No config file found!")
        return

    # Initialize BingX client
    bingx = BingXClient(
        config['bingx']['api_key'],
        config['bingx']['api_secret'],
        config['bingx']['testnet'],
        config['bingx']['base_url']
    )

    # Fetch 1000PEPE-USDT last 50 hours (need at least 14 for RSI calculation)
    symbol = '1000PEPE-USDT'
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = end_time - (50 * 60 * 60 * 1000)  # 50 hours ago

    print(f"\nFetching {symbol} 1h candles from BingX...")
    print(f"Time range: {datetime.fromtimestamp(start_time/1000, tz=timezone.utc)} to {datetime.fromtimestamp(end_time/1000, tz=timezone.utc)}")

    klines = await bingx.get_klines(
        symbol=symbol,
        interval='1h',
        start_time=start_time,
        end_time=end_time,
        limit=50
    )

    if not klines:
        print("No data returned!")
        return

    print(f"Received {len(klines)} candles")

    # Build DataFrame
    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate correct RSI
    df['rsi'] = rsi_correct(df['close'], 14)

    # Show last 8 hours
    print("\n" + "=" * 100)
    print(f"1000PEPE-USDT - LAST 8 HOURS (Correct Wilder's RSI)")
    print("=" * 100)
    print(f"{'Time (UTC)':<20} {'Open':<12} {'High':<12} {'Low':<12} {'Close':<12} {'RSI(14)':<10}")
    print("-" * 100)

    now_utc = datetime.now(timezone.utc)
    for idx in range(-8, 0):
        row = df.iloc[idx]
        # Convert to UTC timezone aware
        ts = row['timestamp'].tz_localize('UTC') if row['timestamp'].tz is None else row['timestamp']
        time_str = ts.strftime('%Y-%m-%d %H:%M')

        print(f"{time_str:<20} "
              f"${row['open']:<11.6f} "
              f"${row['high']:<11.6f} "
              f"${row['low']:<11.6f} "
              f"${row['close']:<11.6f} "
              f"{row['rsi']:<10.2f}")

    # Show statistics for last 8 hours
    last_8h = df.iloc[-8:]
    print("\n" + "=" * 100)
    print("STATISTICS (Last 8 hours)")
    print("=" * 100)
    print(f"Highest RSI: {last_8h['rsi'].max():.2f}")
    print(f"Lowest RSI: {last_8h['rsi'].min():.2f}")
    print(f"Current RSI: {df.iloc[-1]['rsi']:.2f}")
    print(f"Previous RSI: {df.iloc[-2]['rsi']:.2f}")

    # Check for signals
    print("\n" + "=" * 100)
    print("SIGNAL ANALYSIS (Last 8 hours)")
    print("=" * 100)

    signals_found = False
    for i in range(-8, 0):
        curr = df.iloc[i]
        prev = df.iloc[i-1]

        # LONG signal: RSI crosses above 27
        if prev['rsi'] <= 27 and curr['rsi'] > 27:
            signals_found = True
            print(f"✅ LONG SIGNAL at {curr['timestamp']}")
            print(f"   RSI: {prev['rsi']:.2f} → {curr['rsi']:.2f} (crossed above 27)")
            print(f"   Price: ${prev['close']:.6f} → ${curr['close']:.6f}")

        # SHORT signal: RSI crosses below 65
        if prev['rsi'] >= 65 and curr['rsi'] < 65:
            signals_found = True
            print(f"✅ SHORT SIGNAL at {curr['timestamp']}")
            print(f"   RSI: {prev['rsi']:.2f} → {curr['rsi']:.2f} (crossed below 65)")
            print(f"   Price: ${prev['close']:.6f} → ${curr['close']:.6f}")

    if not signals_found:
        print("No signals in last 8 hours")
        print(f"(LONG threshold: RSI crosses above 27, SHORT threshold: RSI crosses below 65)")
        print(f"Current RSI is {df.iloc[-1]['rsi']:.2f}")

    print("=" * 100)


if __name__ == '__main__':
    asyncio.run(main())
