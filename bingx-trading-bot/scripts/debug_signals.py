"""
Debug script to analyze why signals were missed

Analyzes the exact DataFrame state at specific timestamps
to compare with backtest results
"""
import sys
import pandas as pd
from datetime import datetime
from data.candle_builder import MultiTimeframeCandleManager
from data.indicators import IndicatorCalculator
from strategies.moodeng_rsi_momentum import MoodengRSIMomentumStrategy
from strategies.uni_volume_zones import UniVolumeZonesStrategy
from config import load_config
import asyncio
from execution.bingx_client import BingXClient

async def analyze_historical_signals():
    """Fetch historical data and check for missed signals"""

    # Load config
    config = load_config('config.yaml')

    # Initialize BingX client
    client = BingXClient(
        api_key=config.bingx.api_key,
        api_secret=config.bingx.api_secret,
        testnet=config.bingx.testnet
    )

    print("=" * 80)
    print("SIGNAL DEBUG ANALYSIS")
    print("=" * 80)

    # Analyze MOODENG at 10:33
    print("\n[1] MOODENG-USDT at 10:33 UTC")
    print("-" * 80)

    moodeng_manager = MultiTimeframeCandleManager(base_interval=1, timeframes=[1, 5])
    await moodeng_manager.warmup_from_history(client, 'MOODENG-USDT', 300)

    df_1min = moodeng_manager.get_dataframe(1)
    df_5min = moodeng_manager.get_dataframe(5)

    # Add indicators
    calc = IndicatorCalculator(df_1min)
    df_1min = calc.add_all_indicators()

    # Find candle at 10:33 (or closest)
    target_time = pd.Timestamp('2025-12-09 10:33:00')
    time_diffs = [(idx - target_time).total_seconds() for idx in df_1min.index]
    closest_idx = min(range(len(time_diffs)), key=lambda i: abs(time_diffs[i]))

    print(f"\nTarget timestamp: {target_time}")
    print(f"Closest candle: {df_1min.index[closest_idx]}")
    print(f"\nLast 5 candles around 10:33:")
    print(df_1min.iloc[closest_idx-2:closest_idx+3][['open', 'high', 'low', 'close', 'rsi', 'sma_20', 'atr']])

    # Check MOODENG strategy
    strategy_config = config.get_strategy_config('moodeng_rsi_momentum')
    strategy = MoodengRSIMomentumStrategy(strategy_config.__dict__)

    print(f"\nStrategy enabled: {strategy.enabled}")
    print(f"Strategy symbol: {strategy.symbol}")
    print(f"RSI cross level: {strategy.rsi_cross_level}")
    print(f"Min body pct: {strategy.min_body_pct}")

    # Analyze at that timestamp
    df_subset = df_1min.iloc[:closest_idx+1]
    signal = strategy.analyze(df_subset)

    print(f"\nSignal at {df_1min.index[closest_idx]}: {signal}")

    if signal:
        print(f"✓ SIGNAL GENERATED: {signal['direction']} @ {signal['entry_price']}")
    else:
        # Debug why no signal
        current = df_1min.iloc[closest_idx]
        previous = df_1min.iloc[closest_idx-1]

        print("\n[DEBUG] Why no signal:")
        print(f"  Previous RSI: {previous['rsi']:.2f}")
        print(f"  Current RSI: {current['rsi']:.2f}")
        print(f"  RSI crossed 55? {previous['rsi'] < 55 and current['rsi'] >= 55}")

        body_pct = abs(current['close'] - current['open']) / current['open'] * 100
        is_bullish = current['close'] > current['open']

        print(f"  Body %: {body_pct:.2f}%")
        print(f"  Is bullish? {is_bullish}")
        print(f"  Strong body (>{strategy.min_body_pct}%)? {body_pct > strategy.min_body_pct}")
        print(f"  Close: {current['close']:.6f}")
        print(f"  SMA(20): {current['sma_20']:.6f}")
        print(f"  Above SMA? {current['close'] > current['sma_20']}")

    # Analyze UNI at 10:43
    print("\n\n[2] UNI-USDT at 10:43 UTC")
    print("-" * 80)

    uni_manager = MultiTimeframeCandleManager(base_interval=1, timeframes=[1, 5])
    await uni_manager.warmup_from_history(client, 'UNI-USDT', 300)

    df_1min_uni = uni_manager.get_dataframe(1)

    # Add indicators
    calc_uni = IndicatorCalculator(df_1min_uni)
    df_1min_uni = calc_uni.add_all_indicators()

    # Find candle at 10:43
    target_time_uni = pd.Timestamp('2025-12-09 10:43:00')
    time_diffs_uni = [(idx - target_time_uni).total_seconds() for idx in df_1min_uni.index]
    closest_idx_uni = min(range(len(time_diffs_uni)), key=lambda i: abs(time_diffs_uni[i]))

    print(f"\nTarget timestamp: {target_time_uni}")
    print(f"Closest candle: {df_1min_uni.index[closest_idx_uni]}")
    print(f"\nLast 10 candles around 10:43 (check volume):")
    print(df_1min_uni.iloc[closest_idx_uni-5:closest_idx_uni+5][['close', 'volume', 'atr']])

    # Check UNI strategy
    strategy_config_uni = config.get_strategy_config('uni_volume_zones')
    strategy_uni = UniVolumeZonesStrategy(strategy_config_uni.__dict__)

    print(f"\nStrategy enabled: {strategy_uni.enabled}")
    print(f"Strategy symbol: {strategy_uni.symbol}")
    print(f"Volume threshold: {strategy_uni.volume_threshold}x")
    print(f"Min zone bars: {strategy_uni.min_zone_bars}")
    print(f"Session filter: {strategy_uni.session_filter}")

    # Check session
    candle_time = df_1min_uni.index[closest_idx_uni]
    in_session = strategy_uni.check_session(candle_time)
    print(f"10:43 in {strategy_uni.session_filter} session? {in_session}")

    # Analyze at that timestamp
    df_subset_uni = df_1min_uni.iloc[:closest_idx_uni+1]
    signal_uni = strategy_uni.analyze(df_subset_uni)

    print(f"\nSignal at {df_1min_uni.index[closest_idx_uni]}: {signal_uni}")

    if signal_uni:
        print(f"✓ SIGNAL GENERATED: {signal_uni['direction']} @ {signal_uni['entry_price']}")
    else:
        print("\n[DEBUG] No signal - check volume zones")
        print(f"  Current zone bars: {strategy_uni.zone_bars}")
        print(f"  In zone: {strategy_uni.in_zone}")

        # Check volume ratios for last 10 candles
        print(f"\n  Last 10 candles volume analysis:")
        for i in range(closest_idx_uni-9, closest_idx_uni+1):
            if i < 0:
                continue
            candle = df_1min_uni.iloc[i]
            vol_ma = df_1min_uni['volume'].iloc[:i+1].rolling(20).mean().iloc[-1]
            vol_ratio = candle['volume'] / vol_ma if vol_ma > 0 else 0
            elevated = vol_ratio >= strategy_uni.volume_threshold
            print(f"    {df_1min_uni.index[i]}: vol={candle['volume']:.0f}, vol_ratio={vol_ratio:.2f}x {'✓' if elevated else ''}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(analyze_historical_signals())
