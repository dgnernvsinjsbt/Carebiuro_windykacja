#!/usr/bin/env python3
"""
Test: Do live candles match when re-fetched later as historical data?

Run for 5 minutes:
- Every minute: Download 300 candles, calculate indicators, log results
- After 5 minutes: Re-download same period, compare if data matches
"""

import asyncio
import yaml
import pandas as pd
from datetime import datetime, timedelta, timezone
from execution.bingx_client import BingXClient
from data.indicators import IndicatorCalculator

# Load credentials
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

# Store live snapshots
live_snapshots = []

async def fetch_and_analyze(client, label=""):
    """Fetch 300 candles and calculate indicators"""

    # Fetch last 300 minutes
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = end_time - (300 * 60 * 1000)  # 300 minutes ago

    klines = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=300
    )

    # Build DataFrame
    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    # Get latest closed candle (second to last, since last might be incomplete)
    if len(df) >= 2:
        latest = df.iloc[-2]
    else:
        latest = df.iloc[-1]

    return {
        'label': label,
        'timestamp': latest['timestamp'],
        'open': latest['open'],
        'high': latest['high'],
        'low': latest['low'],
        'close': latest['close'],
        'volume': latest['volume'],
        'rsi': latest.get('rsi', None),
        'sma_20': latest.get('sma_20', None),
        'candles_fetched': len(klines)
    }

async def run_live_test():
    """Run 5-minute live test"""

    client = BingXClient(api_key=api_key, api_secret=api_secret)

    print("=" * 80)
    print("LIVE vs HISTORICAL DATA TEST")
    print("=" * 80)
    print(f"Start time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()
    print("Will run for 5 minutes, fetching data every minute...")
    print("Then re-fetch historically and compare.")
    print("=" * 80)
    print()

    # Run for 5 iterations (5 minutes)
    for i in range(5):
        # Wait until :05 seconds of the next minute (candle should be closed)
        now = datetime.now(timezone.utc)
        next_minute = (now + timedelta(minutes=1)).replace(second=5, microsecond=0)
        wait_seconds = (next_minute - now).total_seconds()

        if wait_seconds > 0:
            print(f"⏳ Waiting {wait_seconds:.0f}s until {next_minute.strftime('%H:%M:%S')}...")
            await asyncio.sleep(wait_seconds)

        # Fetch and analyze
        snapshot = await fetch_and_analyze(client, label=f"LIVE_FETCH_{i+1}")
        live_snapshots.append(snapshot)

        # Log results
        print()
        print("=" * 80)
        print(f"📊 LIVE FETCH #{i+1} - {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC")
        print("=" * 80)
        print(f"Latest closed candle: {snapshot['timestamp']}")
        print(f"  Open:   ${snapshot['open']:.6f}")
        print(f"  High:   ${snapshot['high']:.6f}")
        print(f"  Low:    ${snapshot['low']:.6f}")
        print(f"  Close:  ${snapshot['close']:.6f}")
        print(f"  Volume: {snapshot['volume']:,.0f}")
        if snapshot['rsi'] is not None and not pd.isna(snapshot['rsi']):
            print(f"  RSI(14): {snapshot['rsi']:.2f}")
        else:
            print(f"  RSI(14): N/A")
        if snapshot['sma_20'] is not None and not pd.isna(snapshot['sma_20']):
            print(f"  SMA(20): ${snapshot['sma_20']:.6f}")
        else:
            print(f"  SMA(20): N/A")
        print(f"  Candles fetched: {snapshot['candles_fetched']}")
        print()

    print()
    print("=" * 80)
    print("⏳ LIVE PHASE COMPLETE - Now re-fetching historically...")
    print("=" * 80)
    print()

    # Wait a bit to ensure all data is settled
    await asyncio.sleep(10)

    # Now re-fetch the same candles as historical data
    print("🔍 RE-FETCHING HISTORICAL DATA")
    print()

    historical_snapshots = []

    for snapshot in live_snapshots:
        # Fetch a window around this timestamp
        target_time = pd.to_datetime(snapshot['timestamp'])
        start_time = int((target_time - timedelta(minutes=150)).timestamp() * 1000)
        end_time = int((target_time + timedelta(minutes=150)).timestamp() * 1000)

        klines = await client.get_klines(
            symbol='MOODENG-USDT',
            interval='1m',
            start_time=start_time,
            end_time=end_time,
            limit=300
        )

        # Build DataFrame
        df = pd.DataFrame(klines)
        df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
        df = df.sort_values('timestamp')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        # Calculate indicators
        calc = IndicatorCalculator(df)
        df = calc.add_all_indicators()

        # Find the exact candle
        target_candle = df[df['timestamp'] == snapshot['timestamp']]

        if len(target_candle) > 0:
            candle = target_candle.iloc[0]
            historical_snapshots.append({
                'label': f"HISTORICAL_{snapshot['label']}",
                'timestamp': candle['timestamp'],
                'open': candle['open'],
                'high': candle['high'],
                'low': candle['low'],
                'close': candle['close'],
                'volume': candle['volume'],
                'rsi': candle.get('rsi', None),
                'sma_20': candle.get('sma_20', None),
            })
        else:
            print(f"⚠️  Could not find {snapshot['timestamp']} in historical data")
            historical_snapshots.append(None)

    await client.close()

    # Compare results
    print()
    print("=" * 80)
    print("📊 COMPARISON: LIVE vs HISTORICAL")
    print("=" * 80)
    print()

    all_match = True

    for i, (live, hist) in enumerate(zip(live_snapshots, historical_snapshots)):
        if hist is None:
            print(f"❌ Snapshot {i+1}: Historical data not found")
            all_match = False
            continue

        print(f"Snapshot {i+1}: {live['timestamp']}")
        print("-" * 80)

        # Compare OHLC
        open_match = abs(live['open'] - hist['open']) < 0.00001
        high_match = abs(live['high'] - hist['high']) < 0.00001
        low_match = abs(live['low'] - hist['low']) < 0.00001
        close_match = abs(live['close'] - hist['close']) < 0.00001
        volume_match = abs(live['volume'] - hist['volume']) < 0.01

        # Compare indicators (handle NaN)
        if pd.notna(live['rsi']) and pd.notna(hist['rsi']):
            rsi_match = abs(live['rsi'] - hist['rsi']) < 0.01
        else:
            rsi_match = (pd.isna(live['rsi']) and pd.isna(hist['rsi']))

        if pd.notna(live['sma_20']) and pd.notna(hist['sma_20']):
            sma_match = abs(live['sma_20'] - hist['sma_20']) < 0.00001
        else:
            sma_match = (pd.isna(live['sma_20']) and pd.isna(hist['sma_20']))

        print(f"  Open:   ${live['open']:.6f} vs ${hist['open']:.6f}  {'✅' if open_match else '❌'}")
        print(f"  High:   ${live['high']:.6f} vs ${hist['high']:.6f}  {'✅' if high_match else '❌'}")
        print(f"  Low:    ${live['low']:.6f} vs ${hist['low']:.6f}  {'✅' if low_match else '❌'}")
        print(f"  Close:  ${live['close']:.6f} vs ${hist['close']:.6f}  {'✅' if close_match else '❌'}")
        print(f"  Volume: {live['volume']:,.0f} vs {hist['volume']:,.0f}  {'✅' if volume_match else '❌'}")

        if pd.notna(live['rsi']) and pd.notna(hist['rsi']):
            print(f"  RSI:    {live['rsi']:.2f} vs {hist['rsi']:.2f}  {'✅' if rsi_match else '❌'}")

        if pd.notna(live['sma_20']) and pd.notna(hist['sma_20']):
            print(f"  SMA(20): ${live['sma_20']:.6f} vs ${hist['sma_20']:.6f}  {'✅' if sma_match else '❌'}")

        snapshot_match = (open_match and high_match and low_match and
                         close_match and volume_match and rsi_match and sma_match)

        if snapshot_match:
            print(f"  ✅ PERFECT MATCH")
        else:
            print(f"  ❌ MISMATCH DETECTED")
            all_match = False

        print()

    print("=" * 80)
    print("FINAL VERDICT:")
    print("=" * 80)

    if all_match:
        print("✅ ALL SNAPSHOTS MATCH!")
        print("   Live data is identical to historical data.")
        print("   This approach is reliable for live trading.")
    else:
        print("❌ MISMATCHES DETECTED!")
        print("   Live data differs from historical data.")
        print("   This indicates a data settling/revision issue.")

    print()
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_live_test())
