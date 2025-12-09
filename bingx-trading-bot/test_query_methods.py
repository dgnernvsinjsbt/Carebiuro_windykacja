#!/usr/bin/env python3
"""Test if query method affects data returned"""

import asyncio
import yaml
from datetime import datetime, timedelta, timezone
from execution.bingx_client import BingXClient

# Load credentials
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

async def test_query_methods():
    """Compare two ways of querying the same candle"""

    client = BingXClient(api_key=api_key, api_secret=api_secret)

    print("=" * 70)
    print("TESTING: Does query method affect data?")
    print("=" * 70)
    print()

    # Get current time - we'll query the PREVIOUS minute (latest closed candle)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    prev_minute = now.replace(second=0, microsecond=0) - timedelta(minutes=1)

    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Target candle: {prev_minute.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()

    # ========================================
    # METHOD 1: Just limit (like bot does)
    # ========================================
    print("📊 METHOD 1: Query with limit=5 only (NO time params)")
    print("-" * 70)

    klines1 = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        limit=5
    )

    print(f"Received {len(klines1)} candles")

    # Find our target candle
    target1 = None
    for k in klines1:
        ts = datetime.fromtimestamp(k['time'] / 1000)
        if ts == prev_minute:
            target1 = k
            print(f"✓ Found {prev_minute.strftime('%H:%M')} candle:")
            print(f"   Open:   ${float(k['open']):.6f}")
            print(f"   Close:  ${float(k['close']):.6f}")
            print(f"   Volume: {float(k['volume']):,.0f}")
            break

    if not target1:
        print(f"❌ {prev_minute.strftime('%H:%M')} not found")
        print("Available candles:")
        for k in klines1:
            ts = datetime.fromtimestamp(k['time'] / 1000)
            print(f"   {ts.strftime('%H:%M')}")

    print()

    # ========================================
    # METHOD 2: With time range (like my verification)
    # ========================================
    print("📊 METHOD 2: Query with startTime/endTime (specific range)")
    print("-" * 70)

    start_time = int((prev_minute - timedelta(minutes=2)).timestamp() * 1000)
    end_time = int((prev_minute + timedelta(minutes=2)).timestamp() * 1000)

    klines2 = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=10
    )

    print(f"Received {len(klines2)} candles")

    # Find our target candle
    target2 = None
    for k in klines2:
        ts = datetime.fromtimestamp(k['time'] / 1000)
        if ts == prev_minute:
            target2 = k
            print(f"✓ Found {prev_minute.strftime('%H:%M')} candle:")
            print(f"   Open:   ${float(k['open']):.6f}")
            print(f"   Close:  ${float(k['close']):.6f}")
            print(f"   Volume: {float(k['volume']):,.0f}")
            break

    if not target2:
        print(f"❌ {prev_minute.strftime('%H:%M')} not found")

    await client.close()

    print()

    # ========================================
    # COMPARISON
    # ========================================
    if target1 and target2:
        print("=" * 70)
        print("COMPARISON")
        print("=" * 70)
        print()

        open1 = float(target1['open'])
        close1 = float(target1['close'])
        vol1 = float(target1['volume'])

        open2 = float(target2['open'])
        close2 = float(target2['close'])
        vol2 = float(target2['volume'])

        print(f"OPEN:   ${open1:.6f} vs ${open2:.6f}  (diff: ${abs(open1-open2):.6f})")
        print(f"CLOSE:  ${close1:.6f} vs ${close2:.6f}  (diff: ${abs(close1-close2):.6f})")
        print(f"VOLUME: {vol1:,.0f} vs {vol2:,.0f}  (diff: {abs(vol1-vol2):,.0f})")
        print()

        if abs(open1 - open2) < 0.00001 and abs(close1 - close2) < 0.00001:
            print("✅ IDENTICAL DATA - Query method doesn't matter")
        else:
            print("❌ DIFFERENT DATA - Query method DOES affect results!")
            print()
            print("🔍 This explains the bug:")
            print("   - Bot uses limit=5 (no time params)")
            print("   - Might get unsettled/preliminary data")
            print("   - Backtest uses start_time/end_time")
            print("   - Gets fully settled historical data")
            print()
            print("FIX: Always use start_time/end_time, even for 'live' polling")

    print()
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_query_methods())
