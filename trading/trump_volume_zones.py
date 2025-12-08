#!/usr/bin/env python3
"""
TRUMP Volume Zone Analysis - Adapted from PENGU Breakthrough

Hypothesis: TRUMP failed with patterns/scalping/mean-reversion because we were
looking for price patterns. Volume zones detect SUSTAINED whale activity
(5-10+ consecutive bars with elevated volume) at price extremes.

Test parameters:
- volume_threshold: 1.3, 1.5, 2.0
- min_consecutive: 5, 7, 10
- R:R ratios: 3:1, 5:1, 7:1
"""

import pandas as pd
import numpy as np

# Load TRUMP data
print("Loading TRUMP data...")
df = pd.read_csv('trump_usdt_1m_mexc.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Calculate indicators
df['range'] = df['high'] - df['low']
df['atr'] = df['range'].rolling(14).mean()
df['body'] = df['close'] - df['open']

# Volume analysis
df['vol_ma'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma']

print(f"Total candles: {len(df)}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print()

def detect_volume_zones(df, volume_threshold, min_consecutive, max_consecutive=15):
    """Detect sustained volume zones"""
    volume_zones = []
    in_zone = False
    zone_start = None
    zone_bars = 0

    for i in range(len(df)):
        if pd.isna(df.loc[i, 'vol_ratio']):
            continue

        is_elevated = df.loc[i, 'vol_ratio'] >= volume_threshold

        if is_elevated:
            if not in_zone:
                in_zone = True
                zone_start = i
                zone_bars = 1
            else:
                zone_bars += 1

                if zone_bars > max_consecutive:
                    if zone_bars >= min_consecutive:
                        volume_zones.append({
                            'start': zone_start,
                            'end': i - 1,
                            'bars': zone_bars - 1
                        })
                    zone_start = i
                    zone_bars = 1
        else:
            if in_zone:
                if zone_bars >= min_consecutive:
                    volume_zones.append({
                        'start': zone_start,
                        'end': i - 1,
                        'bars': zone_bars
                    })
                in_zone = False
                zone_start = None
                zone_bars = 0

    # Close final zone if needed
    if in_zone and zone_bars >= min_consecutive:
        volume_zones.append({
            'start': zone_start,
            'end': len(df) - 1,
            'bars': zone_bars
        })

    return volume_zones

def classify_zones(df, volume_zones):
    """Classify zones as accumulation (at lows) or distribution (at highs)"""
    accumulation_zones = []
    distribution_zones = []

    for zone in volume_zones:
        start_idx = zone['start']
        end_idx = zone['end']

        if start_idx < 20 or end_idx >= len(df) - 30:
            continue

        zone_low = df.loc[start_idx:end_idx, 'low'].min()
        zone_high = df.loc[start_idx:end_idx, 'high'].max()

        lookback_start = max(0, start_idx - 20)
        lookahead_end = min(len(df), end_idx + 5)

        # Accumulation zone: volume at local low
        if zone_low == df.loc[lookback_start:lookahead_end, 'low'].min():
            entry_idx = end_idx + 1
            if entry_idx < len(df):
                accumulation_zones.append({
                    'zone_start': start_idx,
                    'zone_end': end_idx,
                    'zone_bars': zone['bars'],
                    'zone_low': zone_low,
                    'entry_idx': entry_idx,
                    'entry_price': df.loc[entry_idx, 'close'],
                })

        # Distribution zone: volume at local high
        elif zone_high == df.loc[lookback_start:lookahead_end, 'high'].max():
            entry_idx = end_idx + 1
            if entry_idx < len(df):
                distribution_zones.append({
                    'zone_start': start_idx,
                    'zone_end': end_idx,
                    'zone_bars': zone['bars'],
                    'zone_high': zone_high,
                    'entry_idx': entry_idx,
                    'entry_price': df.loc[entry_idx, 'close'],
                })

    return accumulation_zones, distribution_zones

def backtest_volume_zones(df, accumulation_zones, distribution_zones, rr_ratio=3.0):
    """Backtest volume zone strategy"""
    trades = []

    # LONG trades from accumulation zones
    for zone in accumulation_zones:
        entry_idx = zone['entry_idx']
        if entry_idx not in df.index or pd.isna(df.loc[entry_idx, 'atr']):
            continue

        entry_price = zone['entry_price']
        zone_low = zone['zone_low']
        atr = df.loc[entry_idx, 'atr']

        # Stop: below zone low with 0.5 ATR buffer
        stop_loss = max(zone_low - (0.5 * atr), entry_price - (1.0 * atr))
        sl_distance = entry_price - stop_loss

        # Target: X:1 R:R
        take_profit = entry_price + (rr_ratio * sl_distance)

        # Check next 60 bars for SL/TP
        for i in range(1, 61):
            if entry_idx + i >= len(df):
                break
            candle = df.iloc[entry_idx + i]

            # Check SL first
            if candle['low'] <= stop_loss:
                exit_price = stop_loss
                pnl = (exit_price / entry_price - 1) - 0.001
                trades.append({
                    'direction': 'LONG',
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'SL',
                    'zone_bars': zone['zone_bars']
                })
                break

            # Check TP
            if candle['high'] >= take_profit:
                exit_price = take_profit
                pnl = (exit_price / entry_price - 1) - 0.001
                trades.append({
                    'direction': 'LONG',
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'TP',
                    'zone_bars': zone['zone_bars']
                })
                break
        else:
            # Time exit after 60 bars
            exit_price = df.iloc[entry_idx + 60]['close'] if entry_idx + 60 < len(df) else entry_price
            pnl = (exit_price / entry_price - 1) - 0.001
            trades.append({
                'direction': 'LONG',
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': 60,
                'exit_reason': 'TIME',
                'zone_bars': zone['zone_bars']
            })

    # SHORT trades from distribution zones
    for zone in distribution_zones:
        entry_idx = zone['entry_idx']
        if entry_idx not in df.index or pd.isna(df.loc[entry_idx, 'atr']):
            continue

        entry_price = zone['entry_price']
        zone_high = zone['zone_high']
        atr = df.loc[entry_idx, 'atr']

        # Stop: above zone high
        stop_loss = min(zone_high + (0.5 * atr), entry_price + (1.0 * atr))
        sl_distance = stop_loss - entry_price

        # Target: X:1 R:R
        take_profit = entry_price - (rr_ratio * sl_distance)

        for i in range(1, 61):
            if entry_idx + i >= len(df):
                break
            candle = df.iloc[entry_idx + i]

            # Check SL first
            if candle['high'] >= stop_loss:
                exit_price = stop_loss
                pnl = (entry_price / exit_price - 1) - 0.001
                trades.append({
                    'direction': 'SHORT',
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'SL',
                    'zone_bars': zone['zone_bars']
                })
                break

            # Check TP
            if candle['low'] <= take_profit:
                exit_price = take_profit
                pnl = (entry_price / exit_price - 1) - 0.001
                trades.append({
                    'direction': 'SHORT',
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'TP',
                    'zone_bars': zone['zone_bars']
                })
                break
        else:
            exit_price = df.iloc[entry_idx + 60]['close'] if entry_idx + 60 < len(df) else entry_price
            pnl = (entry_price / exit_price - 1) - 0.001
            trades.append({
                'direction': 'SHORT',
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': 60,
                'exit_reason': 'TIME',
                'zone_bars': zone['zone_bars']
            })

    return trades

# ============================================================================
# PARAMETER GRID SEARCH
# ============================================================================
print("=" * 80)
print("TRUMP VOLUME ZONE PARAMETER OPTIMIZATION")
print("=" * 80)
print()

results = []

# Test different parameter combinations
vol_thresholds = [1.3, 1.5, 2.0]
min_consecutives = [5, 7, 10]
rr_ratios = [3.0, 5.0, 7.0]

for vol_thresh in vol_thresholds:
    for min_consec in min_consecutives:
        for rr in rr_ratios:
            # Detect zones
            zones = detect_volume_zones(df, vol_thresh, min_consec, max_consecutive=15)
            acc_zones, dist_zones = classify_zones(df, zones)

            if len(acc_zones) + len(dist_zones) == 0:
                continue

            # Backtest
            trades = backtest_volume_zones(df, acc_zones, dist_zones, rr)

            if len(trades) == 0:
                continue

            trades_df = pd.DataFrame(trades)
            total_return = trades_df['pnl'].sum() * 100
            win_rate = (trades_df['pnl'] > 0).mean() * 100
            avg_winner = trades_df[trades_df['pnl'] > 0]['pnl'].mean() * 100 if (trades_df['pnl'] > 0).any() else 0
            avg_loser = trades_df[trades_df['pnl'] < 0]['pnl'].mean() * 100 if (trades_df['pnl'] < 0).any() else 0

            results.append({
                'vol_thresh': vol_thresh,
                'min_consec': min_consec,
                'rr': rr,
                'trades': len(trades_df),
                'return': total_return,
                'win_rate': win_rate,
                'avg_winner': avg_winner,
                'avg_loser': avg_loser,
                'zones_total': len(zones),
                'acc_zones': len(acc_zones),
                'dist_zones': len(dist_zones),
                'trades_df': trades_df
            })

# Sort by return
results = sorted(results, key=lambda x: x['return'], reverse=True)

# Display top 10 configs
print(f"{'Vol Thresh':>10} {'MinBars':>8} {'R:R':>5} {'Trades':>7} {'Return':>8} {'WinRate':>8} {'AvgWin':>8} {'AvgLoss':>9}")
print("-" * 85)
for r in results[:15]:
    print(f"{r['vol_thresh']:>10.1f}x {r['min_consec']:>8} {r['rr']:>5.1f}:1 {r['trades']:>7} {r['return']:>7.2f}% {r['win_rate']:>7.1f}% {r['avg_winner']:>7.2f}% {r['avg_loser']:>8.2f}%")

if len(results) > 0:
    best = results[0]
    print("\n" + "=" * 80)
    print(f"BEST CONFIG: Vol={best['vol_thresh']}x, MinBars={best['min_consec']}, R:R={best['rr']}:1")
    print("=" * 80)
    print(f"Trades: {best['trades']}")
    print(f"Return: {best['return']:+.2f}%")
    print(f"Win Rate: {best['win_rate']:.1f}%")
    print(f"Avg Winner: {best['avg_winner']:+.2f}%")
    print(f"Avg Loser: {best['avg_loser']:+.2f}%")
    print(f"\nZones detected: {best['zones_total']}")
    print(f"  Accumulation (longs): {best['acc_zones']}")
    print(f"  Distribution (shorts): {best['dist_zones']}")

    # Exit reasons
    print("\nExit reasons:")
    exit_counts = best['trades_df']['exit_reason'].value_counts()
    for reason, count in exit_counts.items():
        print(f"  {reason}: {count}")

    # Direction breakdown
    print("\nBy direction:")
    for direction in ['LONG', 'SHORT']:
        dir_trades = best['trades_df'][best['trades_df']['direction'] == direction]
        if len(dir_trades) > 0:
            dir_return = dir_trades['pnl'].sum() * 100
            dir_wr = (dir_trades['pnl'] > 0).mean() * 100
            print(f"  {direction}: {len(dir_trades)} trades, {dir_return:+.2f}%, WR: {dir_wr:.1f}%")

    # Compare to previous approaches
    print("\n" + "=" * 80)
    print("COMPARISON TO ALL PREVIOUS APPROACHES")
    print("=" * 80)
    print(f"Scalping (Momentum 1:3):          -0.59% | 160 trades")
    print(f"Mean-Reversion (RSI < 20):        -2.91% | 64 trades")
    print(f"Patterns Filtered (Double Top):   -1.05% | 18 trades")
    print(f"Volume Zones (Best Config):       {best['return']:+.2f}% | {best['trades']} trades")

    # Save best
    best['trades_df'].to_csv('results/TRUMP_volume_zones_trades.csv', index=False)
    print(f"\n✅ Best config trades saved to: results/TRUMP_volume_zones_trades.csv")
else:
    print("\n❌ No trades generated across all parameter combinations")
    print("TRUMP may be too low-volume/low-volatility for volume zone detection")
