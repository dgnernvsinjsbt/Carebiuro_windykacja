#!/usr/bin/env python3
"""
Re-verify MOODENG 10:33 signal RIGHT NOW
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

async def verify_1033_signal():
    """Verify if 10:33 signal data is still the same"""

    client = BingXClient(api_key=api_key, api_secret=api_secret)

    print("=" * 80)
    print("RE-VERIFYING MOODENG 10:33 SIGNAL")
    print("=" * 80)
    print()

    # Fetch data around 10:33 with 24h of history for indicators
    end_time = int(datetime(2025, 12, 9, 12, 0).timestamp() * 1000)  # Noon
    start_time = int((datetime(2025, 12, 9, 12, 0) - timedelta(hours=24)).timestamp() * 1000)  # 24h before

    klines = await client.get_klines(
        symbol='MOODENG-USDT',
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

    # Find 10:33 candle
    target = df[df['timestamp'] == '2025-12-09 10:33:00']

    if len(target) == 0:
        print("❌ 10:33 candle not found!")
        await client.close()
        return

    candle = target.iloc[0]

    # Also get 10:32 for RSI crossover check
    target_prev = df[df['timestamp'] == '2025-12-09 10:32:00']
    if len(target_prev) > 0:
        prev_candle = target_prev.iloc[0]
    else:
        prev_candle = None

    print("📊 CURRENT DATA FROM BINGX (Dec 9, ~12:35 UTC)")
    print("-" * 80)
    print(f"10:33 Candle:")
    print(f"  Open:   ${candle['open']:.6f}")
    print(f"  High:   ${candle['high']:.6f}")
    print(f"  Low:    ${candle['low']:.6f}")
    print(f"  Close:  ${candle['close']:.6f}")
    print(f"  Volume: {candle['volume']:,.0f}")
    print(f"  RSI(14): {candle['rsi']:.2f}")
    print(f"  SMA(20): ${candle['sma_20']:.6f}")
    print()

    if prev_candle is not None:
        print(f"10:32 Candle (previous):")
        print(f"  RSI(14): {prev_candle['rsi']:.2f}")
        print()

    # Check MOODENG strategy conditions
    body = abs(candle['close'] - candle['open'])
    body_pct = (body / candle['open']) * 100
    is_bullish = candle['close'] > candle['open']

    print("🎯 MOODENG STRATEGY CONDITIONS:")
    print("-" * 80)
    if prev_candle is not None:
        print(f"  Previous RSI < 55?  {prev_candle['rsi']:.2f} < 55 = {prev_candle['rsi'] < 55}")
        print(f"  Current RSI >= 55?  {candle['rsi']:.2f} >= 55 = {candle['rsi'] >= 55}")
        print(f"  RSI Crossed 55?     {prev_candle['rsi'] < 55 and candle['rsi'] >= 55}")
    print(f"  Bullish candle?     {is_bullish}")
    print(f"  Body > 0.5%?        {body_pct:.2f}% > 0.5% = {body_pct > 0.5}")
    print(f"  Price > SMA(20)?    ${candle['close']:.6f} > ${candle['sma_20']:.6f} = {candle['close'] > candle['sma_20']}")
    print()

    # Check qualification
    if prev_candle is not None:
        qualifies = (
            prev_candle['rsi'] < 55 and
            candle['rsi'] >= 55 and
            is_bullish and
            body_pct > 0.5 and
            candle['close'] > candle['sma_20']
        )
        print(f"  {'✅ SIGNAL QUALIFIES' if qualifies else '❌ SIGNAL DOES NOT QUALIFY'}")
    print()

    # Compare to earlier verification
    print("=" * 80)
    print("COMPARISON TO EARLIER VERIFICATION")
    print("=" * 80)
    print()
    print("Earlier today (~11:00 UTC) I verified:")
    print("  Open:   $0.089810")
    print("  Close:  $0.090350")
    print("  Volume: 5,943,093")
    print("  RSI:    61.14")
    print()

    print("Current BingX data (now):")
    print(f"  Open:   ${candle['open']:.6f}")
    print(f"  Close:  ${candle['close']:.6f}")
    print(f"  Volume: {candle['volume']:,.0f}")
    print(f"  RSI:    {candle['rsi']:.2f}")
    print()

    # Check if matches
    open_match = abs(candle['open'] - 0.089810) < 0.00001
    close_match = abs(candle['close'] - 0.090350) < 0.00001
    volume_match = abs(candle['volume'] - 5943093) < 1
    rsi_match = abs(candle['rsi'] - 61.14) < 0.1

    if open_match and close_match and volume_match and rsi_match:
        print("✅ DATA MATCHES MY EARLIER VERIFICATION")
        print("   BingX consistently returns the same historical data")
    else:
        print("❌ DATA DIFFERENT FROM EARLIER VERIFICATION")
        print("   BingX may have revised the historical data")
        print()
        print("Differences:")
        if not open_match:
            print(f"  Open:  {abs(candle['open'] - 0.089810):.6f} difference")
        if not close_match:
            print(f"  Close: {abs(candle['close'] - 0.090350):.6f} difference")
        if not volume_match:
            print(f"  Volume: {abs(candle['volume'] - 5943093):,.0f} difference")
        if not rsi_match:
            print(f"  RSI: {abs(candle['rsi'] - 61.14):.2f} difference")

    print()

    # Compare to bot's CSV
    print("=" * 80)
    print("COMPARISON TO BOT'S STORED DATA")
    print("=" * 80)
    print()
    print("Bot's CSV (from commit 86338a1):")
    print("  Open:   $0.089800")
    print("  Close:  $0.089800")
    print("  Volume: 96,199")
    print("  RSI:    44.62")
    print()

    print("Current BingX data:")
    print(f"  Open:   ${candle['open']:.6f}")
    print(f"  Close:  ${candle['close']:.6f}")
    print(f"  Volume: {candle['volume']:,.0f}")
    print(f"  RSI:    {candle['rsi']:.2f}")
    print()

    bot_open_match = abs(candle['open'] - 0.089800) < 0.00001
    bot_close_match = abs(candle['close'] - 0.089800) < 0.00001

    if bot_open_match and bot_close_match:
        print("⚠️  Bot's data matches current BingX (unlikely)")
    else:
        print("❌ Bot's data DOES NOT match current BingX")
        print("   Bot stored corrupted data at 10:33")
        print()
        print("   This confirms the data corruption bug")
        print("   where shared candle_manager mixed symbol data")

    print()
    print("=" * 80)

    await client.close()

if __name__ == "__main__":
    asyncio.run(verify_1033_signal())
