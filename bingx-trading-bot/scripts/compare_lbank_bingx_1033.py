#!/usr/bin/env python3
"""Compare LBank vs BingX data for MOODENG at 10:33 UTC"""

import ccxt
import asyncio
import yaml
from datetime import datetime, timedelta
from execution.bingx_client import BingXClient

# Load BingX credentials
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

async def compare_exchanges():
    """Compare LBank vs BingX for the 10:33 candle"""

    print("=" * 70)
    print("COMPARING LBANK VS BINGX - MOODENG 10:33 UTC")
    print("=" * 70)
    print()

    # ========================================
    # LBANK DATA
    # ========================================
    print("📊 LBANK DATA")
    print("-" * 70)

    lbank = ccxt.lbank({'enableRateLimit': True})

    # Fetch data around 10:33
    target_time = datetime(2025, 12, 9, 10, 33)
    since = int((target_time - timedelta(minutes=5)).timestamp() * 1000)

    try:
        candles = lbank.fetch_ohlcv(
            symbol='MOODENG/USDT',
            timeframe='1m',
            since=since,
            limit=20
        )

        print(f"Fetched {len(candles)} candles from LBank")
        print()

        # Find 10:33 candle
        lbank_1033 = None
        for candle in candles:
            ts = datetime.fromtimestamp(candle[0] / 1000)
            if ts.hour == 10 and ts.minute == 33 and ts.day == 9:
                lbank_1033 = candle
                print(f"✓ Found 10:33 candle:")
                print(f"   Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                print(f"   Open:   ${candle[1]:.6f}")
                print(f"   High:   ${candle[2]:.6f}")
                print(f"   Low:    ${candle[3]:.6f}")
                print(f"   Close:  ${candle[4]:.6f}")
                print(f"   Volume: {candle[5]:,.0f}")
                break

        if not lbank_1033:
            print("❌ 10:33 candle not found in LBank data")
            return

    except Exception as e:
        print(f"❌ Error fetching from LBank: {e}")
        return

    print()

    # ========================================
    # BINGX DATA
    # ========================================
    print("📊 BINGX DATA")
    print("-" * 70)

    bingx = BingXClient(api_key=api_key, api_secret=api_secret)

    start_time = int(datetime(2025, 12, 9, 10, 30).timestamp() * 1000)
    end_time = int(datetime(2025, 12, 9, 10, 40).timestamp() * 1000)

    try:
        klines = await bingx.get_klines(
            symbol='MOODENG-USDT',
            interval='1m',
            start_time=start_time,
            end_time=end_time,
            limit=20
        )

        print(f"Fetched {len(klines)} candles from BingX")
        print()

        # Find 10:33 candle
        bingx_1033 = None
        for kline in klines:
            ts = datetime.fromtimestamp(kline['time'] / 1000)
            if ts.hour == 10 and ts.minute == 33 and ts.day == 9:
                bingx_1033 = kline
                print(f"✓ Found 10:33 candle:")
                print(f"   Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                print(f"   Open:   ${float(kline['open']):.6f}")
                print(f"   High:   ${float(kline['high']):.6f}")
                print(f"   Low:    ${float(kline['low']):.6f}")
                print(f"   Close:  ${float(kline['close']):.6f}")
                print(f"   Volume: {float(kline['volume']):,.0f}")
                break

        if not bingx_1033:
            print("❌ 10:33 candle not found in BingX data")
            await bingx.close()
            return

        await bingx.close()

    except Exception as e:
        print(f"❌ Error fetching from BingX: {e}")
        return

    print()

    # ========================================
    # BOT'S CSV DATA (from previous investigation)
    # ========================================
    print("📊 BOT'S CSV DATA (from commit 86338a1)")
    print("-" * 70)
    print(f"   Timestamp: 2025-12-09 10:33:00 UTC")
    print(f"   Open:   $0.089800")
    print(f"   High:   $0.089830")
    print(f"   Low:    $0.089720")
    print(f"   Close:  $0.089800")
    print(f"   Volume: 96,198.92")
    print()

    # ========================================
    # COMPARISON
    # ========================================
    print("=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print()

    # Compare LBank vs BingX
    lbank_open = lbank_1033[1]
    lbank_close = lbank_1033[4]
    lbank_volume = lbank_1033[5]

    bingx_open = float(bingx_1033['open'])
    bingx_close = float(bingx_1033['close'])
    bingx_volume = float(bingx_1033['volume'])

    bot_open = 0.089800
    bot_close = 0.089800
    bot_volume = 96198.92

    print("📈 OPEN PRICE:")
    print(f"   LBank:  ${lbank_open:.6f}")
    print(f"   BingX:  ${bingx_open:.6f}")
    print(f"   Bot CSV: ${bot_open:.6f}")
    print(f"   LBank vs BingX diff: ${abs(lbank_open - bingx_open):.6f}")
    print(f"   Bot vs BingX diff:   ${abs(bot_open - bingx_open):.6f}")
    print()

    print("📈 CLOSE PRICE:")
    print(f"   LBank:  ${lbank_close:.6f}")
    print(f"   BingX:  ${bingx_close:.6f}")
    print(f"   Bot CSV: ${bot_close:.6f}")
    print(f"   LBank vs BingX diff: ${abs(lbank_close - bingx_close):.6f}")
    print(f"   Bot vs BingX diff:   ${abs(bot_close - bingx_close):.6f}")
    print()

    print("📈 VOLUME:")
    print(f"   LBank:  {lbank_volume:,.0f}")
    print(f"   BingX:  {bingx_volume:,.0f}")
    print(f"   Bot CSV: {bot_volume:,.0f}")
    print(f"   LBank vs BingX diff: {abs(lbank_volume - bingx_volume):,.0f}")
    print(f"   Bot vs BingX diff:   {abs(bot_volume - bingx_volume):,.0f}")
    print()

    # Check if exchanges match
    exchanges_match = (
        abs(lbank_open - bingx_open) < 0.00001 and
        abs(lbank_close - bingx_close) < 0.00001
    )

    # Check if bot matches exchanges
    bot_matches = (
        abs(bot_open - bingx_open) < 0.00001 and
        abs(bot_close - bingx_close) < 0.00001
    )

    print("=" * 70)
    print("VERDICT:")
    print("=" * 70)

    if exchanges_match:
        print("✅ LBank and BingX return IDENTICAL data")
        print("   Both exchanges agree on what happened at 10:33")
    else:
        print("❌ LBank and BingX return DIFFERENT data")
        print("   Exchanges disagree on what happened at 10:33")

    print()

    if bot_matches:
        print("✅ Bot's CSV matches current exchange data")
        print("   Bot stored correct data at the time")
    else:
        print("❌ Bot's CSV DOES NOT match exchange data")
        print("   Bot stored WRONG data at 10:33")
        print()
        print("🔍 POSSIBLE CAUSES:")
        print("   1. Bot queried too early (candle not settled)")
        print("   2. Data corruption bug (cross-symbol pollution)")
        print("   3. BingX revised historical data after the fact")
        print("   4. CSV export bug mixed symbols")

    print()
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(compare_exchanges())
