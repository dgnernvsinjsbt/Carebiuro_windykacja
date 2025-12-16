#!/usr/bin/env python3
"""
Compare bot's logged data vs actual BingX data to identify data corruption.
"""
import pandas as pd
import numpy as np

def compare_data():
    # Load both datasets
    bot_data = pd.read_csv('bot_data_extracted.csv')
    bingx_data = pd.read_csv('bingx_verification_data.csv')

    # Convert timestamps to datetime
    bot_data['timestamp'] = pd.to_datetime(bot_data['timestamp'])
    bingx_data['timestamp'] = pd.to_datetime(bingx_data['timestamp'])

    print("=" * 80)
    print("🔍 DATA CORRUPTION ANALYSIS - Bot vs BingX")
    print("=" * 80)

    for symbol in ['FARTCOIN-USDT', 'TRUMPSOL-USDT']:
        print(f"\n{'=' * 80}")
        print(f"📊 {symbol}")
        print('=' * 80)

        bot_sym = bot_data[bot_data['symbol'] == symbol].copy()
        bingx_sym = bingx_data[bingx_data['symbol'] == symbol].copy()

        # Merge on timestamp
        merged = pd.merge(
            bot_sym,
            bingx_sym,
            on='timestamp',
            suffixes=('_bot', '_bingx'),
            how='outer'
        )

        # Calculate differences
        merged['close_diff_pct'] = ((merged['close_bot'] - merged['close_bingx']) / merged['close_bingx'] * 100)
        merged['volume_diff_pct'] = ((merged['volume_bot'] - merged['volume_bingx']) / merged['volume_bingx'] * 100)

        print(f"\n📈 Data Coverage:")
        print(f"  Bot candles:   {len(bot_sym)}")
        print(f"  BingX candles: {len(bingx_sym)}")
        print(f"  Matching:      {merged['close_bot'].notna().sum()}")
        print(f"  Missing in bot: {merged['close_bot'].isna().sum()}")

        # Show first 10 matching candles
        matching = merged[merged['close_bot'].notna()].head(10)

        print(f"\n🔎 First 10 Matching Candles:")
        print(f"\n{'Timestamp':<20} {'Bot Close':>12} {'BingX Close':>12} {'Diff %':>10} {'Bot Vol':>15} {'BingX Vol':>15}")
        print("-" * 100)

        for _, row in matching.iterrows():
            print(f"{str(row['timestamp']):<20} "
                  f"${row['close_bot']:>11.6f} "
                  f"${row['close_bingx']:>11.6f} "
                  f"{row['close_diff_pct']:>9.2f}% "
                  f"{row['volume_bot']:>14,.0f} "
                  f"{row['volume_bingx']:>14,.0f}")

        # Summary stats
        matching_all = merged[merged['close_bot'].notna()]
        if len(matching_all) > 0:
            print(f"\n📊 Discrepancy Statistics:")
            print(f"  Avg close diff:   {matching_all['close_diff_pct'].mean():+.2f}%")
            print(f"  Max close diff:   {matching_all['close_diff_pct'].max():+.2f}%")
            print(f"  Min close diff:   {matching_all['close_diff_pct'].min():+.2f}%")
            print(f"  Avg volume diff:  {matching_all['volume_diff_pct'].mean():+.2f}%")

            # Flag major discrepancies
            major_discrepancies = matching_all[np.abs(matching_all['close_diff_pct']) > 5]
            if len(major_discrepancies) > 0:
                print(f"\n⚠️  {len(major_discrepancies)} MAJOR PRICE DISCREPANCIES (>5%):")
                for _, row in major_discrepancies.head(5).iterrows():
                    print(f"    {row['timestamp']}: Bot=${row['close_bot']:.6f}, "
                          f"BingX=${row['close_bingx']:.6f} ({row['close_diff_pct']:+.2f}%)")

    print(f"\n{'=' * 80}")
    print("🎯 CONCLUSION")
    print('=' * 80)

    # Overall assessment
    all_matching = pd.merge(bot_data, bingx_data, on=['timestamp', 'symbol'], suffixes=('_bot', '_bingx'))
    if len(all_matching) > 0:
        avg_diff = ((all_matching['close_bot'] - all_matching['close_bingx']) / all_matching['close_bingx'] * 100).abs().mean()

        if avg_diff < 0.01:
            print("✅ Data is ACCURATE - Bot is receiving correct prices from BingX")
        elif avg_diff < 1:
            print("⚠️  Data has MINOR DISCREPANCIES - Small differences detected")
        else:
            print(f"❌ DATA CORRUPTION DETECTED - Average price difference: {avg_diff:.2f}%")
            print("\n🔧 Possible causes:")
            print("  1. Bot is fetching from wrong symbol or contract")
            print("  2. Data is being corrupted during processing")
            print("  3. API response parsing error")
            print("  4. Timestamp synchronization issues")
    else:
        print("❌ NO MATCHING DATA - Bot and BingX have different timestamps!")

    print('=' * 80)

if __name__ == '__main__':
    compare_data()
