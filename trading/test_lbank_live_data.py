#!/usr/bin/env python3
"""Test if LBank provides live/recent data"""

import ccxt
from datetime import datetime, timedelta

def test_lbank_live_data():
    """Check how recent LBank data is"""

    # Initialize LBank exchange
    exchange = ccxt.lbank({
        'enableRateLimit': True,
    })

    print("=" * 70)
    print("TESTING LBANK LIVE DATA AVAILABILITY")
    print("=" * 70)
    print()

    # Test MOODENG
    print("🔍 Fetching MOODENG/USDT last 10 candles...")
    try:
        candles = exchange.fetch_ohlcv(
            symbol='MOODENG/USDT',
            timeframe='1m',
            limit=10
        )

        if candles:
            print(f"✓ Received {len(candles)} candles")
            print()

            # Show the last 5 candles
            print("Last 5 candles:")
            for i, candle in enumerate(candles[-5:]):
                timestamp_ms = candle[0]
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
                open_price = candle[1]
                close_price = candle[4]
                volume = candle[5]

                print(f"  {timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC: "
                      f"O={open_price:.6f}, C={close_price:.6f}, V={volume:.0f}")

            # Check how recent the latest candle is
            latest_candle_time = datetime.fromtimestamp(candles[-1][0] / 1000)
            now = datetime.utcnow()
            lag = now - latest_candle_time

            print()
            print(f"📊 Data Freshness:")
            print(f"   Latest candle: {latest_candle_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"   Current time:  {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"   Lag: {lag.total_seconds():.0f} seconds ({lag.total_seconds()/60:.1f} minutes)")

            if lag.total_seconds() < 120:  # Less than 2 minutes old
                print(f"   ✅ LIVE DATA - Less than 2 minutes lag!")
            elif lag.total_seconds() < 300:  # Less than 5 minutes
                print(f"   ⚠️  NEAR-LIVE - {lag.total_seconds()/60:.1f} minute lag")
            else:
                print(f"   ❌ DELAYED - {lag.total_seconds()/60:.1f} minute lag")
        else:
            print("❌ No data received")

    except Exception as e:
        print(f"❌ Error fetching MOODENG: {e}")

    print()
    print("-" * 70)
    print()

    # Test UNI
    print("🔍 Fetching UNI/USDT last 10 candles...")
    try:
        candles = exchange.fetch_ohlcv(
            symbol='UNI/USDT',
            timeframe='1m',
            limit=10
        )

        if candles:
            print(f"✓ Received {len(candles)} candles")
            print()

            # Show the last 5 candles
            print("Last 5 candles:")
            for i, candle in enumerate(candles[-5:]):
                timestamp_ms = candle[0]
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
                open_price = candle[1]
                close_price = candle[4]
                volume = candle[5]

                print(f"  {timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC: "
                      f"O={open_price:.4f}, C={close_price:.4f}, V={volume:.0f}")

            # Check how recent the latest candle is
            latest_candle_time = datetime.fromtimestamp(candles[-1][0] / 1000)
            now = datetime.utcnow()
            lag = now - latest_candle_time

            print()
            print(f"📊 Data Freshness:")
            print(f"   Latest candle: {latest_candle_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"   Current time:  {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"   Lag: {lag.total_seconds():.0f} seconds ({lag.total_seconds()/60:.1f} minutes)")

            if lag.total_seconds() < 120:  # Less than 2 minutes old
                print(f"   ✅ LIVE DATA - Less than 2 minutes lag!")
            elif lag.total_seconds() < 300:  # Less than 5 minutes
                print(f"   ⚠️  NEAR-LIVE - {lag.total_seconds()/60:.1f} minute lag")
            else:
                print(f"   ❌ DELAYED - {lag.total_seconds()/60:.1f} minute lag")
        else:
            print("❌ No data received")

    except Exception as e:
        print(f"❌ Error fetching UNI: {e}")

    print()
    print("=" * 70)
    print("CONCLUSION:")
    print("If lag < 2 minutes: LBank can be used for live trading verification")
    print("If lag > 5 minutes: LBank data is historical only")
    print("=" * 70)

if __name__ == "__main__":
    test_lbank_live_data()
