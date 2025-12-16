#!/usr/bin/env python3
"""
Verify MELANIA RSI calculation matches BingX exactly
Fetches latest 15m candles and calculates RSI using Wilder's EMA
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import pandas as pd
import numpy as np
import os
from execution.bingx_client import BingXClient
from datetime import datetime, timezone

async def calculate_rsi_wilders(candles, period=14):
    """Calculate RSI using Wilder's EMA (same as strategy)"""
    df = pd.DataFrame(candles)
    df['close'] = df['close'].astype(float)

    # Price changes
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's EMA (alpha = 1/14)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    # RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    df['rsi'] = rsi
    return df

async def main():
    print("=" * 70)
    print("MELANIA RSI VERIFICATION")
    print("Comparing bot calculation vs BingX chart")
    print("=" * 70)

    # Initialize BingX client (market data doesn't need API keys)
    bingx = BingXClient(
        api_key="",  # Not needed for market data
        api_secret="",
        testnet=False  # Production
    )

    symbol = "MELANIA-USDT"

    # Fetch latest 300 15m candles
    print(f"\n📊 Fetching 15m candles for {symbol}...")
    now = datetime.now(timezone.utc)
    end_time = int(now.timestamp() * 1000)
    start_time = end_time - (300 * 15 * 60 * 1000)  # 300 candles

    candles = await bingx.get_klines(
        symbol=symbol,
        interval='15m',
        start_time=start_time,
        end_time=end_time,
        limit=300
    )

    print(f"   Fetched {len(candles)} candles")

    if len(candles) < 100:
        print(f"❌ Not enough candles (got {len(candles)})")
        return

    # Calculate RSI
    print(f"\n🔢 Calculating RSI using Wilder's EMA...")
    df = await calculate_rsi_wilders(candles, period=14)

    # Show last 5 candles with RSI
    print(f"\n📈 Last 5 Candles (15m):")
    print("-" * 70)

    for i in range(-5, 0):
        row = df.iloc[i]
        timestamp = pd.to_datetime(row['time'], unit='ms')
        print(f"   {timestamp} UTC")
        print(f"      Close: ${float(row['close']):.6f}")
        print(f"      RSI(14): {row['rsi']:.2f}")
        print()

    # Latest closed candle (second to last, as last might be forming)
    latest = df.iloc[-2]
    forming = df.iloc[-1]

    latest_time = pd.to_datetime(latest['time'], unit='ms')
    forming_time = pd.to_datetime(forming['time'], unit='ms')

    print("=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print(f"\n🕐 Latest CLOSED candle: {latest_time} UTC")
    print(f"   Close Price: ${float(latest['close']):.6f}")
    print(f"   RSI(14): {latest['rsi']:.2f}")
    print()
    print(f"🕐 FORMING candle: {forming_time} UTC")
    print(f"   Close Price: ${float(forming['close']):.6f}")
    print(f"   RSI(14): {forming['rsi']:.2f}")
    print()
    print("=" * 70)
    print("⚠️  Check BingX chart - are you looking at the closed or forming candle?")
    print("⚠️  Bot uses the second-to-last candle (latest CLOSED)")
    print("=" * 70)

    await bingx.close()

if __name__ == "__main__":
    asyncio.run(main())
