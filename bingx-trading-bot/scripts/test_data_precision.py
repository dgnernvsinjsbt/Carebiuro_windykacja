"""
Test if data corruption happens during storage or just logging/export
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from execution.bingx_client import BingXClient
from data.candle_builder import MultiTimeframeCandleManager
import yaml

# Load API credentials
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

async def test_precision():
    """Test data precision through the full pipeline"""
    print("\n" + "="*70)
    print("DATA PRECISION TEST")
    print("="*70)

    client = BingXClient(api_key=api_key, api_secret=api_secret)

    # Fetch a recent candle
    klines = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        limit=5
    )

    if not klines or len(klines) < 2:
        print("❌ Failed to fetch data")
        return

    # Get latest closed candle (like bot does)
    latest_closed = klines[1]
    timestamp = datetime.fromtimestamp(latest_closed['time'] / 1000)

    print(f"\n📡 STEP 1: Raw BingX API Response")
    print(f"   Candle: {timestamp.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Raw dict: {latest_closed}")
    print(f"   Open (string): '{latest_closed['open']}'")
    print(f"   Open (float):  {float(latest_closed['open']):.10f}")

    # Create manager and add candle (exactly like bot does)
    manager = MultiTimeframeCandleManager(
        base_interval=1,
        timeframes=[1, 5],
        buffer_size=500
    )

    print(f"\n🔧 STEP 2: After add_completed_candle()")
    manager.add_completed_candle(latest_closed)

    # Check what's stored in the Candle object
    last_candle_obj = manager.base_builder.candles[-1]
    print(f"   Candle object:")
    print(f"     timestamp: {last_candle_obj.timestamp}")
    print(f"     open:      {last_candle_obj.open:.10f}")
    print(f"     close:     {last_candle_obj.close:.10f}")
    print(f"     volume:    {last_candle_obj.volume:.2f}")

    # Get DataFrame (what strategies use)
    df = manager.get_dataframe(1)

    print(f"\n📊 STEP 3: After get_dataframe()")
    if len(df) > 0:
        row = df.iloc[-1]
        print(f"   DataFrame row:")
        print(f"     timestamp: {row.name}")  # timestamp is the index
        print(f"     open:      {row['open']:.10f}")
        print(f"     close:     {row['close']:.10f}")
        print(f"     volume:    {row['volume']:.2f}")

        # Check dtypes
        print(f"\n   DataFrame dtypes:")
        print(f"     {df.dtypes}")

    # Export to CSV and re-import (test CSV export precision)
    print(f"\n💾 STEP 4: After CSV Export/Import")
    csv_path = '/tmp/test_precision.csv'
    df.to_csv(csv_path)
    df_from_csv = pd.read_csv(csv_path)

    if len(df_from_csv) > 0:
        row = df_from_csv.iloc[-1]
        print(f"   After CSV roundtrip:")
        print(f"     open:  {row['open']:.10f}")
        print(f"     close: {row['close']:.10f}")

    # Compare original vs CSV
    print(f"\n🔍 STEP 5: Precision Check")
    original_open = float(latest_closed['open'])
    stored_open = last_candle_obj.open
    df_open = df.iloc[-1]['open']
    csv_open = df_from_csv.iloc[-1]['open']

    print(f"   Open price journey:")
    print(f"     BingX API:      {original_open:.10f}")
    print(f"     Candle object:  {stored_open:.10f}  {'✅' if abs(stored_open - original_open) < 0.0000000001 else '❌ LOSS'}")
    print(f"     DataFrame:      {df_open:.10f}  {'✅' if abs(df_open - original_open) < 0.0000000001 else '❌ LOSS'}")
    print(f"     CSV roundtrip:  {csv_open:.10f}  {'✅' if abs(csv_open - original_open) < 0.0000000001 else '❌ LOSS'}")

    if abs(csv_open - original_open) > 0.0000000001:
        print(f"\n🔴 PRECISION LOSS DETECTED!")
        print(f"   Difference: {abs(csv_open - original_open):.10f}")
        print(f"   This could explain CSV data mismatch!")
    else:
        print(f"\n✅ NO PRECISION LOSS!")
        print(f"   Data is identical throughout the pipeline.")

    await client.close()

if __name__ == '__main__':
    asyncio.run(test_precision())
