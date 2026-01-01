"""
Compare BingX data NOW vs what bot saw at 10:33
"""

import asyncio
import pandas as pd
from datetime import datetime
from execution.bingx_client import BingXClient
from data.indicators import IndicatorCalculator
import yaml

# Load API credentials
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

async def fetch_exact_candles():
    """Fetch the exact candles the bot saw at 10:33"""
    client = BingXClient(api_key=api_key, api_secret=api_secret)

    print("="*70)
    print("QUERYING BINGX FOR EXACT 10:33 CANDLE")
    print("="*70)

    # Query 1: Fetch around 10:33 with small window (like bot would have)
    print("\n🔍 Query 1: Narrow window around 10:33")
    end_time = int(datetime(2025, 12, 9, 10, 34).timestamp() * 1000)
    start_time = int(datetime(2025, 12, 9, 10, 30).timestamp() * 1000)

    klines = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=10
    )

    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    print(f"Fetched {len(df)} candles")
    print("\nCandles around 10:33:")
    for _, row in df.iterrows():
        print(f"  {row['timestamp']}: O={row['open']:.6f} C={row['close']:.6f} V={row['volume']:.0f}")

    # Find 10:33 specifically
    target = df[df['timestamp'] == '2025-12-09 10:33:00']
    if len(target) > 0:
        candle = target.iloc[0]
        print(f"\n📊 10:33 CANDLE FROM BINGX NOW:")
        print(f"   Open:   ${candle['open']:.6f}")
        print(f"   Close:  ${candle['close']:.6f}")
        print(f"   Volume: {candle['volume']:.0f}")
        body_pct = abs(candle['close'] - candle['open']) / candle['open'] * 100
        print(f"   Body:   {body_pct:.2f}%")
        print(f"   Direction: {'BULLISH' if candle['close'] > candle['open'] else 'BEARISH' if candle['close'] < candle['open'] else 'DOJI'}")
    else:
        print("❌ 10:33 candle not found!")

    # Query 2: Get more history for RSI calculation
    print("\n\n🔍 Query 2: With enough history for RSI")
    end_time = int(datetime(2025, 12, 9, 10, 35).timestamp() * 1000)
    start_time = int(datetime(2025, 12, 9, 9, 0).timestamp() * 1000)  # 1.5 hours

    klines = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=200
    )

    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate RSI
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    print(f"Fetched {len(df)} candles with indicators")

    # Show RSI around 10:33
    print("\n📈 RSI VALUES AROUND 10:33:")
    window = df[df['timestamp'].between('2025-12-09 10:30:00', '2025-12-09 10:34:00')]
    for _, row in window.iterrows():
        rsi_val = row.get('rsi', float('nan'))
        if pd.notna(rsi_val):
            print(f"   {row['timestamp']}: RSI={rsi_val:.2f}, Close=${row['close']:.6f}")
        else:
            print(f"   {row['timestamp']}: RSI=NaN, Close=${row['close']:.6f}")

    # Now compare to bot's data
    print("\n\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    print("\nBOT SAW (from CSV you provided):")
    print("  10:33: Open=$0.08980, Close=$0.08980 (0% body), RSI=44.62")

    target = df[df['timestamp'] == '2025-12-09 10:33:00']
    if len(target) > 0:
        candle = target.iloc[0]
        body_pct = abs(candle['close'] - candle['open']) / candle['open'] * 100
        rsi = candle.get('rsi', float('nan'))
        print("\nBINGX RETURNS NOW:")
        print(f"  10:33: Open=${candle['open']:.6f}, Close=${candle['close']:.6f} ({body_pct:.2f}% body), RSI={rsi:.2f if pd.notna(rsi) else 'NaN'}")

        # Check if they match
        if abs(candle['open'] - 0.08980) < 0.00001 and abs(candle['close'] - 0.08980) < 0.00001:
            print("\n✅ DATA MATCHES! BingX consistently returns the same candle.")
        else:
            print("\n❌ DATA MISMATCH! BingX returns different data now vs what bot saw!")

if __name__ == '__main__':
    asyncio.run(fetch_exact_candles())
