#!/usr/bin/env python3
"""
Re-verify UNI 10:43 signal RIGHT NOW
Compare to what we saw earlier today
"""

import asyncio
import yaml
import pandas as pd
from datetime import datetime, timedelta
from execution.bingx_client import BingXClient
from data.indicators import IndicatorCalculator

# Load credentials
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

async def verify_1043_uni():
    """Verify if 10:43 UNI signal data is still the same"""

    client = BingXClient(api_key=api_key, api_secret=api_secret)

    print("=" * 80)
    print("RE-VERIFYING UNI 10:43 SIGNAL")
    print("=" * 80)
    print()

    # Fetch data around 10:43 with 24h of history for indicators
    end_time = int(datetime(2025, 12, 9, 12, 0).timestamp() * 1000)  # Noon
    start_time = int((datetime(2025, 12, 9, 12, 0) - timedelta(hours=24)).timestamp() * 1000)  # 24h before

    klines = await client.get_klines(
        symbol='UNI-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=1440
    )

    print(f"✓ Fetched {len(klines)} candles from BingX")
    print()

    # Build DataFrame
    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    # Find 10:43 candle
    target = df[df['timestamp'] == '2025-12-09 10:43:00']

    if len(target) == 0:
        print("❌ 10:43 candle not found!")
        await client.close()
        return

    candle = target.iloc[0]

    print("📊 CURRENT DATA FROM BINGX (Dec 9, ~12:35 UTC)")
    print("-" * 80)
    print(f"10:43 Candle:")
    print(f"  Close:  ${candle['close']:.4f}")
    print(f"  Volume: {candle['volume']:,.0f}")
    print(f"  Vol Ratio: {candle.get('vol_ratio', 0):.2f}x")
    print()

    # Show volume around 10:43
    print("📊 VOLUME DATA AROUND 10:43:")
    print("-" * 80)
    window = df[df['timestamp'].between('2025-12-09 10:38:00', '2025-12-09 10:45:00')]

    for _, row in window.iterrows():
        vol_ratio = row.get('vol_ratio', 0)
        elevated = "✓ ELEVATED" if vol_ratio >= 1.3 else ""
        print(f"  {row['timestamp'].strftime('%H:%M')}: vol={row['volume']:,.0f}, ratio={vol_ratio:.2f}x {elevated}")

    print()

    # Check volume zone
    print("🎯 UNI VOLUME ZONES STRATEGY CONDITIONS:")
    print("-" * 80)

    # Count consecutive elevated volume bars ending at or before 10:43
    idx_1043 = df.index[df['timestamp'] == '2025-12-09 10:43:00'][0]

    consecutive = 0
    zone_bars = []

    for i in range(idx_1043, max(0, idx_1043-10), -1):
        row = df.iloc[i]
        if row.get('vol_ratio', 0) >= 1.3:
            consecutive += 1
            zone_bars.insert(0, row['timestamp'].strftime('%H:%M'))
        else:
            break

    print(f"  Consecutive elevated bars (>= 1.3x): {consecutive}")
    print(f"  Zone bars: {zone_bars}")
    print(f"  Meets minimum (3)?  {consecutive >= 3}")
    print()

    qualifies = consecutive >= 3

    print(f"  {'✅ SIGNAL QUALIFIES' if qualifies else '❌ SIGNAL DOES NOT QUALIFY'}")
    print()

    await client.close()

if __name__ == "__main__":
    asyncio.run(verify_1043_uni())
