"""
Check if any signals would have been generated in the last 24 hours
for UNI and MOODENG strategies
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from execution.bingx_client import BingXClient
from data.indicators import IndicatorCalculator
from strategies.uni_volume_zones import UniVolumeZonesStrategy
from strategies.moodeng_rsi_momentum import MoodengRSIMomentumStrategy
import yaml
import os

# Load API credentials from config
with open('config.yaml', 'r') as f:
    full_config = yaml.safe_load(f)
    api_key = full_config['bingx']['api_key']
    api_secret = full_config['bingx']['api_secret']

async def fetch_24h_data(symbol: str):
    """Fetch last 24 hours of 1-minute data"""
    client = BingXClient(
        api_key=api_key,
        api_secret=api_secret
    )

    # Get current time and 24h ago
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)

    print(f"\n{'='*70}")
    print(f"Fetching 24h data for {symbol}")
    print(f"From: {datetime.fromtimestamp(start_time/1000)} UTC")
    print(f"To:   {datetime.fromtimestamp(end_time/1000)} UTC")
    print(f"{'='*70}")

    # Fetch klines
    klines = await client.get_klines(
        symbol=symbol,
        interval='1m',
        start_time=start_time,
        end_time=end_time,
        limit=1440  # 24h * 60min
    )

    print(f"✓ Fetched {len(klines)} candles")

    # Convert to DataFrame
    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    df = df.sort_values('timestamp')

    # Convert to float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    return df

async def check_uni_signals(df: pd.DataFrame):
    """Check for UNI Volume Zones signals"""
    print(f"\n{'='*70}")
    print("CHECKING UNI VOLUME ZONES SIGNALS")
    print(f"{'='*70}")

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Get UNI strategy config
    strategies = config.get('trading', {}).get('strategies', {})
    uni_config = strategies.get('uni_volume_zones')

    if not uni_config:
        print("❌ UNI strategy config not found!")
        return

    # Create strategy instance
    strategy = UniVolumeZonesStrategy(uni_config, symbol='UNI-USDT')

    # Calculate indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    print(f"\nData range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Total candles: {len(df)}")
    print(f"Session filter: {strategy.session_filter} (00:00-14:00 UTC)")

    # Check each candle for signals
    signals = []
    for i in range(50, len(df)):  # Need at least 50 candles for lookback
        # Get slice up to current candle
        df_slice = df.iloc[:i+1].copy()

        # Check for signal
        signal = strategy.analyze(df_slice, None)

        if signal:
            candle = df.iloc[i]
            signals.append({
                'timestamp': candle['timestamp'],
                'direction': signal['direction'],
                'entry': signal['entry_price'],
                'stop': signal['stop_loss'],
                'target': signal['take_profit'],
                'pattern': signal['pattern'],
                'zone_bars': signal.get('zone_bars', 0)
            })

            print(f"\n🚨 SIGNAL DETECTED!")
            print(f"   Time: {candle['timestamp']}")
            print(f"   Direction: {signal['direction']}")
            print(f"   Entry: ${signal['entry_price']:.4f}")
            print(f"   Stop: ${signal['stop_loss']:.4f}")
            print(f"   Target: ${signal['take_profit']:.4f}")
            print(f"   Pattern: {signal['pattern']}")

    if not signals:
        print(f"\n❌ No signals found in last 24 hours")
        print(f"   Strategy: UNI Volume Zones")
        print(f"   Session: Asia/EU only (00:00-14:00 UTC)")
        print(f"   Conditions: 3+ bars volume > 1.3x avg at local high/low")
    else:
        print(f"\n✅ Found {len(signals)} signal(s) in last 24 hours!")

    return signals

async def check_moodeng_signals(df: pd.DataFrame):
    """Check for MOODENG RSI Momentum signals"""
    print(f"\n{'='*70}")
    print("CHECKING MOODENG RSI MOMENTUM SIGNALS")
    print(f"{'='*70}")

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Get MOODENG strategy config
    strategies = config.get('trading', {}).get('strategies', {})
    moodeng_config = strategies.get('moodeng_rsi_momentum')

    if not moodeng_config:
        print("❌ MOODENG strategy config not found!")
        return

    # Create strategy instance
    strategy = MoodengRSIMomentumStrategy(moodeng_config, symbol='MOODENG-USDT')

    # Calculate indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    print(f"\nData range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Total candles: {len(df)}")
    print(f"Session filter: None (24/7 trading)")

    # Check each candle for signals
    signals = []
    for i in range(50, len(df)):  # Need at least 50 candles for indicators
        # Get slice up to current candle
        df_slice = df.iloc[:i+1].copy()

        # Check for signal
        signal = strategy.analyze(df_slice, None)

        if signal:
            candle = df.iloc[i]
            signals.append({
                'timestamp': candle['timestamp'],
                'direction': signal['direction'],
                'entry': signal['entry_price'],
                'stop': signal['stop_loss'],
                'target': signal['take_profit'],
                'pattern': signal['pattern']
            })

            print(f"\n🚨 SIGNAL DETECTED!")
            print(f"   Time: {candle['timestamp']}")
            print(f"   Direction: {signal['direction']}")
            print(f"   Entry: ${signal['entry_price']:.6f}")
            print(f"   Stop: ${signal['stop_loss']:.6f}")
            print(f"   Target: ${signal['take_profit']:.6f}")
            print(f"   Pattern: {signal['pattern']}")

    if not signals:
        print(f"\n❌ No signals found in last 24 hours")
        print(f"   Strategy: MOODENG RSI Momentum")
        print(f"   Conditions: RSI crosses above 55, bullish body >0.5%, price > SMA20")
    else:
        print(f"\n✅ Found {len(signals)} signal(s) in last 24 hours!")

    return signals

async def main():
    print("\n" + "="*70)
    print("24-HOUR SIGNAL CHECK")
    print("Testing UNI Volume Zones + MOODENG RSI Momentum")
    print("="*70)

    try:
        # Fetch UNI data
        df_uni = await fetch_24h_data('UNI-USDT')
        uni_signals = await check_uni_signals(df_uni)

        # Fetch MOODENG data
        df_moodeng = await fetch_24h_data('MOODENG-USDT')
        moodeng_signals = await check_moodeng_signals(df_moodeng)

        # Summary
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"UNI signals (last 24h): {len(uni_signals) if uni_signals else 0}")
        print(f"MOODENG signals (last 24h): {len(moodeng_signals) if moodeng_signals else 0}")
        print(f"Total signals: {(len(uni_signals) if uni_signals else 0) + (len(moodeng_signals) if moodeng_signals else 0)}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
