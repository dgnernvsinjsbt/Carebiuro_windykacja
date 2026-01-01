#!/usr/bin/env python3
"""
Test historical warmup feature
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from data.candle_builder import MultiTimeframeCandleManager
from execution.bingx_client import BingXClient
from datetime import datetime

async def test_warmup():
    print("=" * 80)
    print("TESTING HISTORICAL WARMUP FEATURE")
    print("=" * 80)
    print()

    # Load config
    config = load_config('config.yaml')

    # Create BingX client
    bingx = BingXClient(
        api_key=config.bingx.api_key,
        api_secret=config.bingx.api_secret,
        testnet=config.bingx.testnet
    )

    # Create candle manager
    candle_manager = MultiTimeframeCandleManager(
        base_interval=1,
        timeframes=[1, 5],
        buffer_size=300
    )

    print("📥 Starting warmup for FARTCOIN-USDT...")
    start_time = datetime.now()

    try:
        await candle_manager.warmup_from_history(
            bingx_client=bingx,
            symbol='FARTCOIN-USDT',
            candles_count=300
        )

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        print()
        print("=" * 80)
        print("✅ WARMUP SUCCESSFUL")
        print("=" * 80)
        print(f"Time taken: {elapsed:.2f} seconds")
        print()

        # Verify data
        df_1m = candle_manager.get_dataframe(1)
        df_5m = candle_manager.get_dataframe(5)

        print("Data verification:")
        print(f"  1-min candles: {len(df_1m)}")
        print(f"  5-min candles: {len(df_5m)}")
        print()

        if len(df_1m) > 0:
            print("Sample 1-min candles (last 5):")
            print(df_1m[['open', 'high', 'low', 'close', 'volume']].tail())
            print()

        if len(df_5m) > 0:
            print("Sample 5-min candles (last 5):")
            print(df_5m[['open', 'high', 'low', 'close', 'volume']].tail())
            print()

        # Test that indicators can be calculated
        from data.indicators import IndicatorCalculator
        calc = IndicatorCalculator(df_1m)
        df_with_indicators = calc.add_all_indicators()

        print(f"Indicators calculated successfully:")
        print(f"  RSI: {df_with_indicators['rsi'].iloc[-1]:.2f}")
        print(f"  SMA20: {df_with_indicators['sma_20'].iloc[-1]:.6f}")
        print(f"  ATR: {df_with_indicators['atr'].iloc[-1]:.6f}")
        print()

        print("=" * 80)
        print("🎉 ALL TESTS PASSED")
        print("=" * 80)
        print("Bot is ready to trade immediately after startup!")

    except Exception as e:
        print(f"❌ Error during warmup: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await bingx.close()

if __name__ == "__main__":
    asyncio.run(test_warmup())
