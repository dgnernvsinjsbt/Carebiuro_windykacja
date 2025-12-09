"""
Test if BingX returns identical data for:
1. Live poll at :00 (immediately after candle closes)
2. Retroactive fetch 30 seconds later

This tests the "candle settling" hypothesis.
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from execution.bingx_client import BingXClient
import yaml

# Load API credentials
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

async def test_live_vs_retroactive():
    """Compare live polling vs retroactive fetch"""
    print("\n" + "="*70)
    print("LIVE POLL vs RETROACTIVE FETCH TEST")
    print("="*70)

    client = BingXClient(api_key=api_key, api_secret=api_secret)

    # ====================
    # STEP 1: Wait until :00 of next minute
    # ====================
    now = datetime.now()
    seconds_until_next_minute = 60 - now.second - (now.microsecond / 1_000_000)
    if seconds_until_next_minute <= 0:
        seconds_until_next_minute += 60

    print(f"\n⏰ Current time: {now.strftime('%H:%M:%S')}")
    print(f"⏰ Waiting {seconds_until_next_minute:.1f}s until :00...")
    await asyncio.sleep(seconds_until_next_minute)

    # ====================
    # STEP 2: Poll IMMEDIATELY at :00 (like bot does)
    # ====================
    poll_time = datetime.now()
    expected_candle_time = (poll_time - timedelta(minutes=1)).replace(second=0, microsecond=0)

    print(f"\n📡 LIVE POLL at {poll_time.strftime('%H:%M:%S')}")
    print(f"   Expecting candle: {expected_candle_time.strftime('%H:%M')}")

    # Fetch last 5 candles (exactly like bot does in main.py line 396)
    live_klines = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        limit=5
    )

    if not live_klines or len(live_klines) < 2:
        print("❌ Failed to fetch live data")
        return

    # Get latest CLOSED candle (exactly like bot does in main.py line 408)
    live_candle = live_klines[1] if len(live_klines) > 1 else live_klines[0]
    live_timestamp = datetime.fromtimestamp(live_candle['time'] / 1000)

    print(f"✓ Live candle timestamp: {live_timestamp.strftime('%H:%M:%S')}")
    print(f"   Open:   {float(live_candle['open']):.6f}")
    print(f"   High:   {float(live_candle['high']):.6f}")
    print(f"   Low:    {float(live_candle['low']):.6f}")
    print(f"   Close:  {float(live_candle['close']):.6f}")
    print(f"   Volume: {float(live_candle['volume']):.0f}")

    # ====================
    # STEP 3: Wait 30 seconds
    # ====================
    print(f"\n⏳ Waiting 30 seconds for candle to 'settle'...")
    await asyncio.sleep(30)

    # ====================
    # STEP 4: Fetch retroactively with time range
    # ====================
    retroactive_time = datetime.now()
    print(f"\n📦 RETROACTIVE FETCH at {retroactive_time.strftime('%H:%M:%S')}")

    # Use time range to fetch the exact same candle
    start_time = int((live_timestamp - timedelta(minutes=2)).timestamp() * 1000)
    end_time = int((live_timestamp + timedelta(minutes=2)).timestamp() * 1000)

    retroactive_klines = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=10
    )

    # Find the exact same candle by timestamp
    retroactive_candle = None
    for k in retroactive_klines:
        ts = datetime.fromtimestamp(k['time'] / 1000)
        if ts == live_timestamp:
            retroactive_candle = k
            break

    if not retroactive_candle:
        print("❌ Failed to find matching candle in retroactive fetch")
        return

    print(f"✓ Retroactive candle timestamp: {live_timestamp.strftime('%H:%M:%S')}")
    print(f"   Open:   {float(retroactive_candle['open']):.6f}")
    print(f"   High:   {float(retroactive_candle['high']):.6f}")
    print(f"   Low:    {float(retroactive_candle['low']):.6f}")
    print(f"   Close:  {float(retroactive_candle['close']):.6f}")
    print(f"   Volume: {float(retroactive_candle['volume']):.0f}")

    # ====================
    # STEP 5: Compare
    # ====================
    print(f"\n" + "="*70)
    print("COMPARISON")
    print("="*70)

    live_open = float(live_candle['open'])
    live_close = float(live_candle['close'])
    live_volume = float(live_candle['volume'])

    retro_open = float(retroactive_candle['open'])
    retro_close = float(retroactive_candle['close'])
    retro_volume = float(retroactive_candle['volume'])

    open_diff = abs(live_open - retro_open)
    close_diff = abs(live_close - retro_close)
    volume_diff = abs(live_volume - retro_volume)

    print(f"\nOpen:")
    print(f"   Live:        {live_open:.6f}")
    print(f"   Retroactive: {retro_open:.6f}")
    print(f"   Difference:  {open_diff:.6f} ({'✅ MATCH' if open_diff < 0.000001 else '❌ MISMATCH'})")

    print(f"\nClose:")
    print(f"   Live:        {live_close:.6f}")
    print(f"   Retroactive: {retro_close:.6f}")
    print(f"   Difference:  {close_diff:.6f} ({'✅ MATCH' if close_diff < 0.000001 else '❌ MISMATCH'})")

    print(f"\nVolume:")
    print(f"   Live:        {live_volume:.0f}")
    print(f"   Retroactive: {retro_volume:.0f}")
    print(f"   Difference:  {volume_diff:.0f} ({'✅ MATCH' if volume_diff < 1 else '❌ MISMATCH'})")

    if open_diff < 0.000001 and close_diff < 0.000001 and volume_diff < 1:
        print(f"\n✅ PERFECT MATCH!")
        print("BingX returns identical data for live poll vs retroactive fetch.")
        print("Candle data does NOT change after initial query.")
    else:
        print(f"\n🔴 DATA MISMATCH!")
        print("BingX returns DIFFERENT data for live poll vs retroactive fetch!")
        print("This explains why bot's data doesn't match historical queries.")

    await client.close()

if __name__ == '__main__':
    asyncio.run(test_live_vs_retroactive())
