"""
Verify the exact data at 10:33 and 10:43 to prove signals are valid
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from execution.bingx_client import BingXClient
from data.indicators import IndicatorCalculator
import yaml

# Load API credentials
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

async def verify_moodeng_1033():
    """Verify MOODENG data at 10:33 UTC"""
    print("\n" + "="*70)
    print("VERIFYING MOODENG AT 10:33 UTC")
    print("="*70)

    client = BingXClient(api_key=api_key, api_secret=api_secret)

    # Fetch 24h of data ending well past 10:33 to ensure all indicators calculated
    end_time = int(datetime(2025, 12, 9, 12, 0).timestamp() * 1000)  # Noon
    start_time = int((datetime(2025, 12, 9, 12, 0) - timedelta(hours=24)).timestamp() * 1000)  # 24h before noon

    klines = await client.get_klines(
        symbol='MOODENG-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=1440  # 24 hours of 1-minute candles
    )

    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')  # CRITICAL: Sort ascending!
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    print(f"\n📦 Data fetched: {len(df)} candles")
    print(f"   From: {df['timestamp'].min()}")
    print(f"   To: {df['timestamp'].max()}")

    # Calculate indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    print(f"\n🔧 Indicators calculated")
    print(f"   RSI column exists: {'rsi' in df.columns}")
    print(f"   SMA20 column exists: {'sma_20' in df.columns}")
    if 'rsi' in df.columns:
        print(f"   RSI non-NaN count: {df['rsi'].notna().sum()}/{len(df)}")

    # Find 10:33 candle
    target = df[df['timestamp'] == '2025-12-09 10:33:00']

    if len(target) == 0:
        print("❌ No candle found at 10:33:00")
        print(f"\nAvailable timestamps:")
        print(df[['timestamp', 'close']].tail(10))
        return

    # Show RSI values around 10:33
    print(f"\n📈 RSI VALUES AROUND 10:33")
    window = df[df['timestamp'].between('2025-12-09 10:28:00', '2025-12-09 10:34:00')]
    for _, row in window.iterrows():
        rsi_val = row.get('rsi', float('nan'))
        print(f"   {row['timestamp']}: RSI={rsi_val:.2f}" if not pd.isna(rsi_val) else f"   {row['timestamp']}: RSI=NaN")

    candle = target.iloc[0]
    prev_idx = df.index[df['timestamp'] == '2025-12-09 10:33:00'][0] - 1
    prev_candle = df.iloc[prev_idx]

    print(f"\n📊 CANDLE AT 10:33:00 UTC")
    print(f"   Open: ${candle['open']:.6f}")
    print(f"   High: ${candle['high']:.6f}")
    print(f"   Low: ${candle['low']:.6f}")
    print(f"   Close: ${candle['close']:.6f}")
    print(f"   Volume: {candle['volume']:.0f}")

    body = abs(candle['close'] - candle['open'])
    body_pct = (body / candle['open']) * 100
    is_bullish = candle['close'] > candle['open']

    print(f"\n📈 CANDLE CHARACTERISTICS")
    print(f"   Body: {body_pct:.2f}%")
    print(f"   Direction: {'BULLISH' if is_bullish else 'BEARISH'}")

    print(f"\n🎯 MOODENG STRATEGY CONDITIONS")
    print(f"   Current RSI: {candle['rsi']:.2f}")
    print(f"   Previous RSI: {prev_candle['rsi']:.2f}")
    print(f"   RSI crossed 55? {prev_candle['rsi'] < 55 and candle['rsi'] >= 55}")
    print(f"   Bullish candle? {is_bullish}")
    print(f"   Body > 0.5%? {body_pct > 0.5}")
    print(f"   SMA(20): ${candle['sma_20']:.6f}")
    print(f"   Price > SMA(20)? {candle['close'] > candle['sma_20']}")

    # Check if signal qualifies
    qualifies = (
        prev_candle['rsi'] < 55 and
        candle['rsi'] >= 55 and
        is_bullish and
        body_pct > 0.5 and
        candle['close'] > candle['sma_20']
    )

    print(f"\n{'✅ SIGNAL QUALIFIES' if qualifies else '❌ SIGNAL DOES NOT QUALIFY'}")

    return candle

async def verify_uni_1043():
    """Verify UNI data at 10:43 UTC"""
    print("\n" + "="*70)
    print("VERIFYING UNI AT 10:43 UTC")
    print("="*70)

    client = BingXClient(api_key=api_key, api_secret=api_secret)

    # Fetch 24h of data ending well past 10:43
    end_time = int(datetime(2025, 12, 9, 12, 0).timestamp() * 1000)  # Noon
    start_time = int((datetime(2025, 12, 9, 12, 0) - timedelta(hours=24)).timestamp() * 1000)  # 24h before noon

    klines = await client.get_klines(
        symbol='UNI-USDT',
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=1440  # 24 hours of 1-minute candles
    )

    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')  # CRITICAL: Sort ascending!
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    print(f"\n📦 Data fetched: {len(df)} candles")
    print(f"   From: {df['timestamp'].min()}")
    print(f"   To: {df['timestamp'].max()}")

    # Calculate indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    print(f"\n🔧 Indicators calculated")
    print(f"   RSI column exists: {'rsi' in df.columns}")
    print(f"   SMA20 column exists: {'sma_20' in df.columns}")
    if 'rsi' in df.columns:
        print(f"   RSI non-NaN count: {df['rsi'].notna().sum()}/{len(df)}")

    # Show volume around 10:43
    print(f"\n📊 VOLUME DATA (20-bar average for vol_ratio)")
    window = df[df['timestamp'].between('2025-12-09 10:38:00', '2025-12-09 10:45:00')]

    for _, row in window.iterrows():
        vol_ratio = row.get('vol_ratio', 0)
        elevated = "✓ ELEVATED" if vol_ratio >= 1.3 else ""
        print(f"   {row['timestamp']}: vol={row['volume']:.0f}, ratio={vol_ratio:.2f}x {elevated}")

    # Find 10:43 candle
    target = df[df['timestamp'] == '2025-12-09 10:43:00']

    if len(target) == 0:
        print("❌ No candle found at 10:43:00")
        return

    candle = target.iloc[0]

    print(f"\n📊 CANDLE AT 10:43:00 UTC")
    print(f"   Close: ${candle['close']:.4f}")
    print(f"   Volume: {candle['volume']:.0f}")
    print(f"   Vol Ratio: {candle['vol_ratio']:.2f}x")

    # Count consecutive elevated volume bars ENDING at or before 10:43
    print(f"\n🔍 VOLUME ZONE ANALYSIS")
    print(f"   Looking for 3+ consecutive bars with vol_ratio >= 1.3x")
    print(f"   Zone must be at local low (accumulation)")

    # Check backwards from 10:43
    idx_1043 = df.index[df['timestamp'] == '2025-12-09 10:43:00'][0]

    # Count consecutive elevated volume bars ending at 10:42 (zone would end when volume drops)
    consecutive = 0
    zone_bars = []

    for i in range(idx_1043, max(0, idx_1043-10), -1):
        row = df.iloc[i]
        if row.get('vol_ratio', 0) >= 1.3:
            consecutive += 1
            zone_bars.insert(0, row['timestamp'].strftime('%H:%M'))
        else:
            break

    print(f"   Consecutive elevated bars: {consecutive}")
    print(f"   Zone bars: {zone_bars}")
    print(f"   Meets minimum (3)? {consecutive >= 3}")

    return candle

async def main():
    print("\n" + "="*70)
    print("SIGNAL VERIFICATION - RAW DATA ANALYSIS")
    print("Checking if signals at 10:33 and 10:43 are real")
    print("="*70)

    try:
        moodeng = await verify_moodeng_1033()
        uni = await verify_uni_1043()

        print("\n" + "="*70)
        print("CONCLUSION")
        print("="*70)
        print("If both signals qualify here but bot didn't take them,")
        print("then there's a bug in the live bot's signal processing.")
        print("\nIf signals DON'T qualify, then backtest has stale data.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
