"""
Dump current candle data that the bot sees (with indicators)
Export to CSV for comparison with backtest
"""
import sys
import pandas as pd
from datetime import datetime
from data.candle_builder import MultiTimeframeCandleManager
from data.indicators import IndicatorCalculator
from config import load_config
import asyncio
from execution.bingx_client import BingXClient

async def dump_candle_data():
    """Fetch and dump current candle data with indicators"""

    # Load config
    config = load_config('config.yaml')

    # Initialize BingX client
    client = BingXClient(
        api_key=config.bingx.api_key,
        api_secret=config.bingx.api_secret,
        testnet=config.bingx.testnet
    )

    print("Fetching live candle data from BingX...")
    print("=" * 80)

    # MOODENG-USDT
    print("\n[1] Fetching MOODENG-USDT data...")
    moodeng_manager = MultiTimeframeCandleManager(base_interval=1, timeframes=[1, 5])
    await moodeng_manager.warmup_from_history(client, 'MOODENG-USDT', 300)

    df_moodeng = moodeng_manager.get_dataframe(1)

    # Add indicators
    calc_moodeng = IndicatorCalculator(df_moodeng)
    df_moodeng = calc_moodeng.add_all_indicators()

    print(f"✓ Fetched {len(df_moodeng)} candles for MOODENG-USDT")
    print(f"  Time range: {df_moodeng.index[0]} to {df_moodeng.index[-1]}")

    # Export to CSV
    output_file_moodeng = '/root/bingx-trading-bot/moodeng_candles_with_indicators.csv'
    df_moodeng.to_csv(output_file_moodeng)
    print(f"  ✓ Saved to: {output_file_moodeng}")

    # Show last 20 rows
    print("\n  Last 20 candles:")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    print(df_moodeng.tail(20)[['open', 'high', 'low', 'close', 'volume', 'rsi', 'sma_20', 'atr']])

    # UNI-USDT
    print("\n\n[2] Fetching UNI-USDT data...")
    uni_manager = MultiTimeframeCandleManager(base_interval=1, timeframes=[1, 5])
    await uni_manager.warmup_from_history(client, 'UNI-USDT', 300)

    df_uni = uni_manager.get_dataframe(1)

    # Add indicators (including volume ratio for UNI strategy)
    calc_uni = IndicatorCalculator(df_uni)
    df_uni = calc_uni.add_all_indicators()

    # Add volume ratio manually for volume zone analysis
    df_uni['vol_ma_20'] = df_uni['volume'].rolling(20).mean()
    df_uni['vol_ratio'] = df_uni['volume'] / df_uni['vol_ma_20']

    print(f"✓ Fetched {len(df_uni)} candles for UNI-USDT")
    print(f"  Time range: {df_uni.index[0]} to {df_uni.index[-1]}")

    # Export to CSV
    output_file_uni = '/root/bingx-trading-bot/uni_candles_with_indicators.csv'
    df_uni.to_csv(output_file_uni)
    print(f"  ✓ Saved to: {output_file_uni}")

    # Show last 20 rows
    print("\n  Last 20 candles:")
    print(df_uni.tail(20)[['open', 'high', 'low', 'close', 'volume', 'vol_ratio', 'atr']])

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"MOODENG CSV: {output_file_moodeng}")
    print(f"UNI CSV: {output_file_uni}")
    print("\nColumns in CSVs:")
    print(f"  - timestamp (index)")
    print(f"  - open, high, low, close, volume")
    print(f"  - rsi (14-period)")
    print(f"  - sma_20, sma_50, sma_200")
    print(f"  - ema_20, ema_50")
    print(f"  - atr (14-period)")
    print(f"  - bb_upper, bb_middle, bb_lower (Bollinger Bands)")
    print(f"  - vol_ma_20, vol_ratio (UNI only)")
    print("\nYou can download these files to compare with your backtest data.")

    await client.close()

if __name__ == "__main__":
    asyncio.run(dump_candle_data())
