"""
Diagnose EXACT data flow from BingX API → Candle Storage → DataFrame
to identify where data corruption occurs
"""

import asyncio
import pandas as pd
from datetime import datetime
from execution.bingx_client import BingXClient
from data.candle_builder import MultiTimeframeCandleManager
from data.indicators import IndicatorCalculator
import yaml

# Load API credentials
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

async def diagnose_exact_flow():
    """Replicate EXACTLY what the bot does"""
    print("\n" + "="*70)
    print("DATA FLOW DIAGNOSIS: BingX API → Storage → DataFrame")
    print("="*70)

    client = BingXClient(api_key=api_key, api_secret=api_secret)

    # ====================
    # STEP 1: Query BingX API for 10:33 candle
    # ====================
    print("\n📡 STEP 1: Query BingX API for 10:33 candle")

    # Fetch around 10:33 with time range
    start_time = int(datetime(2025, 12, 9, 10, 30).timestamp() * 1000)
    end_time = int(datetime(2025, 12, 9, 10, 40).timestamp() * 1000)

    klines = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=20
    )

    print(f"✓ Received {len(klines)} candles from BingX")

    # Find 10:33 in the response
    target_candle = None
    for k in klines:
        ts = datetime.fromtimestamp(k['time'] / 1000)
        if ts.hour == 10 and ts.minute == 33 and ts.day == 9:
            target_candle = k
            print(f"\n✓ Found 10:33 candle in response:")
            print(f"   Raw BingX data: {k}")
            break

    if not target_candle:
        print("\n❌ 10:33 candle not in response")
        print("Available timestamps:")
        for k in klines[:5]:
            ts = datetime.fromtimestamp(k['time'] / 1000)
            print(f"   {ts}")
        return

    # ====================
    # STEP 2: Simulate add_completed_candle()
    # ====================
    print("\n🔧 STEP 2: Process through add_completed_candle()")
    print("Converting BingX data to Candle object...")

    # This is EXACTLY what add_completed_candle() does
    from data.candle_builder import Candle

    timestamp = datetime.fromtimestamp(target_candle['time'] / 1000)
    candle_obj = Candle(
        timestamp=timestamp.replace(second=0, microsecond=0),
        open_price=float(target_candle['open'])
    )
    candle_obj.high = float(target_candle['high'])
    candle_obj.low = float(target_candle['low'])
    candle_obj.close = float(target_candle['close'])
    candle_obj.volume = float(target_candle['volume'])
    candle_obj.close_candle()

    print(f"✓ Candle object created:")
    print(f"   Timestamp: {candle_obj.timestamp}")
    print(f"   Open:  {candle_obj.open_price}")
    print(f"   High:  {candle_obj.high}")
    print(f"   Low:   {candle_obj.low}")
    print(f"   Close: {candle_obj.close}")
    print(f"   Volume: {candle_obj.volume}")

    # ====================
    # STEP 3: Simulate get_dataframe()
    # ====================
    print("\n📊 STEP 3: Convert to DataFrame (via get_dataframe())")

    # Create a test manager and add our candle
    manager = MultiTimeframeCandleManager(
        base_interval=1,
        timeframes=[1, 5],
        buffer_size=500
    )

    # Add the candle using the EXACT same method the bot uses
    manager.add_completed_candle(target_candle)

    # Get DataFrame (this is what _process_signal uses)
    df = manager.get_dataframe(1)

    if len(df) > 0:
        row = df.iloc[-1]
        print(f"✓ DataFrame row:")
        print(f"   Timestamp: {row['timestamp']}")
        print(f"   Open:  {row['open']}")
        print(f"   High:  {row['high']}")
        print(f"   Low:   {row['low']}")
        print(f"   Close: {row['close']}")
        print(f"   Volume: {row['volume']}")
    else:
        print("❌ DataFrame is empty!")

    # ====================
    # STEP 4: Compare to bot's CSV
    # ====================
    print("\n🔍 STEP 4: Compare to bot's stored data")
    print("Bot's CSV shows:")
    print("   Timestamp: 2025-12-09 10:33:00")
    print("   Open:  0.08980")
    print("   High:  0.08983")
    print("   Low:   0.08972")
    print("   Close: 0.08980")
    print("   Volume: 96198.92")

    if len(df) > 0:
        row = df.iloc[-1]
        open_match = abs(row['open'] - 0.08980) < 0.00001
        close_match = abs(row['close'] - 0.08980) < 0.00001

        print("\n" + "="*70)
        print("COMPARISON")
        print("="*70)
        print(f"Open matches bot CSV:  {'✅ YES' if open_match else '❌ NO'}")
        print(f"Close matches bot CSV: {'✅ YES' if close_match else '❌ NO'}")

        if not open_match or not close_match:
            print("\n🔴 DATA MISMATCH DETECTED!")
            print("BingX NOW returns different data than bot saw at 10:33")
            print("\nPossible causes:")
            print("1. BingX candle 'settled' after bot queried (first query ≠ later query)")
            print("2. Bot queried too early (before candle fully closed)")
            print("3. Bot has a data processing bug")
        else:
            print("\n✅ Data matches! No corruption in storage/retrieval.")

    # ====================
    # STEP 5: Test with full historical data
    # ====================
    print("\n📦 STEP 5: Test with full 24h historical data")
    print("Fetching 24h history and checking 10:33...")

    end_time = int(datetime(2025, 12, 9, 12, 0).timestamp() * 1000)
    start_time = int(datetime(2025, 12, 9, 0, 0).timestamp() * 1000)

    historical_klines = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=1000
    )

    print(f"✓ Fetched {len(historical_klines)} candles")

    # Find 10:33 in historical data
    for k in historical_klines:
        ts = datetime.fromtimestamp(k['time'] / 1000)
        if ts.hour == 10 and ts.minute == 33 and ts.day == 9:
            print(f"\n✓ Found 10:33 in historical query:")
            print(f"   Open:  {float(k['open'])}")
            print(f"   Close: {float(k['close'])}")
            print(f"   Volume: {float(k['volume'])}")

            # Calculate RSI
            df_hist = pd.DataFrame(historical_klines)
            df_hist['timestamp'] = pd.to_datetime(df_hist['time'], unit='ms')
            df_hist = df_hist.sort_values('timestamp')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df_hist[col] = df_hist[col].astype(float)

            calc = IndicatorCalculator(df_hist)
            df_hist = calc.add_all_indicators()

            target_row = df_hist[df_hist['timestamp'] == '2025-12-09 10:33:00']
            if len(target_row) > 0:
                rsi = target_row.iloc[0]['rsi']
                print(f"   RSI: {rsi:.2f}")

            break

if __name__ == '__main__':
    asyncio.run(diagnose_exact_flow())
