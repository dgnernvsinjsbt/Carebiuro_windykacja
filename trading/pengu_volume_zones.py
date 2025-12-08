#!/usr/bin/env python3
"""
PENGU Volume Zone Analysis - Sustained Accumulation/Distribution

Hypothesis: Single-candle volume spikes are noise, but when volume is elevated
across multiple consecutive bars (5-10+) at a price extreme, it signals real
accumulation (at lows) or distribution (at highs) by whales.

Pattern:
- Volume zone: 5-10 consecutive bars with volume > 1.5x average
- At price low (accumulation zone) → Long entry on breakout
- At price high (distribution zone) → Short entry on breakdown
- Target: 7:1 R:R as observed by user
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load PENGU data
print("Loading PENGU data...")
df = pd.read_csv('pengu_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Calculate indicators
df['range'] = df['high'] - df['low']
df['atr'] = df['range'].rolling(14).mean()
df['body'] = df['close'] - df['open']

# Volume analysis
df['vol_ma'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma']

# Price extremes (20-bar lookback)
df['local_low'] = df['low'].rolling(20, center=True).min() == df['low']
df['local_high'] = df['high'].rolling(20, center=True).max() == df['high']

# Forward returns
for i in [5, 10, 20, 30]:
    df[f'fwd_{i}'] = df['close'].shift(-i) / df['close'] - 1

print(f"Total candles: {len(df)}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print()

# ============================================================================
# DETECT VOLUME ZONES
# ============================================================================
print("=" * 80)
print("DETECTING VOLUME ZONES")
print("=" * 80)

# Find consecutive bars with elevated volume (> 1.5x average)
volume_threshold = 1.5  # 50% above average
min_consecutive = 5     # At least 5 bars
max_consecutive = 15    # Up to 15 bars

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
            # Start new zone
            in_zone = True
            zone_start = i
            zone_bars = 1
        else:
            # Continue zone
            zone_bars += 1

            # Cap at max_consecutive to avoid merging separate zones
            if zone_bars > max_consecutive:
                # Close current zone and start new one
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
            # Close zone
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

print(f"Volume zones found: {len(volume_zones)}")
print(f"Avg zone length: {np.mean([z['bars'] for z in volume_zones]):.1f} bars")
print()

# ============================================================================
# CLASSIFY ZONES: ACCUMULATION (at lows) vs DISTRIBUTION (at highs)
# ============================================================================
print("=" * 80)
print("CLASSIFYING ZONES")
print("=" * 80)

accumulation_zones = []  # Volume zones at price lows (bullish)
distribution_zones = []  # Volume zones at price highs (bearish)

for zone in volume_zones:
    start_idx = zone['start']
    end_idx = zone['end']

    if start_idx < 20 or end_idx >= len(df) - 30:
        continue  # Skip edge zones

    # Get price during zone
    zone_low = df.loc[start_idx:end_idx, 'low'].min()
    zone_high = df.loc[start_idx:end_idx, 'high'].max()
    zone_mid = (zone_low + zone_high) / 2

    # Look back 20 bars before zone
    lookback_start = max(0, start_idx - 20)
    lookback_data = df.loc[lookback_start:start_idx]

    # Look forward 5 bars after zone for entry
    lookahead_end = min(len(df), end_idx + 5)
    lookahead_data = df.loc[end_idx:lookahead_end]

    # Check if zone is at a local low (accumulation)
    if zone_low == df.loc[lookback_start:lookahead_end, 'low'].min():
        # This is the lowest point in the window → ACCUMULATION
        entry_idx = end_idx + 1  # Enter after zone closes
        if entry_idx < len(df):
            accumulation_zones.append({
                'zone_start': start_idx,
                'zone_end': end_idx,
                'zone_bars': zone['bars'],
                'zone_low': zone_low,
                'entry_idx': entry_idx,
                'entry_price': df.loc[entry_idx, 'close'],
                'avg_volume': df.loc[start_idx:end_idx, 'volume'].mean()
            })

    # Check if zone is at a local high (distribution)
    elif zone_high == df.loc[lookback_start:lookahead_end, 'high'].max():
        # This is the highest point in the window → DISTRIBUTION
        entry_idx = end_idx + 1
        if entry_idx < len(df):
            distribution_zones.append({
                'zone_start': start_idx,
                'zone_end': end_idx,
                'zone_bars': zone['bars'],
                'zone_high': zone_high,
                'entry_idx': entry_idx,
                'entry_price': df.loc[entry_idx, 'close'],
                'avg_volume': df.loc[start_idx:end_idx, 'volume'].mean()
            })

print(f"Accumulation zones (at lows): {len(accumulation_zones)}")
print(f"Distribution zones (at highs): {len(distribution_zones)}")
print()

# ============================================================================
# ANALYZE FORWARD RETURNS AFTER ZONES
# ============================================================================
if len(accumulation_zones) > 0:
    print("=" * 80)
    print("ACCUMULATION ZONES (Volume at lows → Long entry)")
    print("=" * 80)

    acc_df = pd.DataFrame(accumulation_zones)
    for col in ['fwd_5', 'fwd_10', 'fwd_20', 'fwd_30']:
        acc_df[col] = acc_df['entry_idx'].apply(lambda idx: df.loc[idx, col] if idx in df.index else np.nan)

    print(f"Total zones: {len(acc_df)}")
    print(f"Avg zone length: {acc_df['zone_bars'].mean():.1f} bars")
    print(f"Avg zone volume: {acc_df['avg_volume'].mean():,.0f}")
    print()
    print("Forward returns after accumulation zone:")
    for i in [5, 10, 20, 30]:
        fwd_ret = acc_df[f'fwd_{i}'].mean() * 100
        win_rate = (acc_df[f'fwd_{i}'] > 0).mean() * 100
        max_ret = acc_df[f'fwd_{i}'].max() * 100 if not acc_df[f'fwd_{i}'].isna().all() else 0
        print(f"  +{i} bars: {fwd_ret:+.3f}% (WR: {win_rate:.1f}%, Max: {max_ret:+.2f}%)")
    print()

if len(distribution_zones) > 0:
    print("=" * 80)
    print("DISTRIBUTION ZONES (Volume at highs → Short entry)")
    print("=" * 80)

    dist_df = pd.DataFrame(distribution_zones)
    for col in ['fwd_5', 'fwd_10', 'fwd_20', 'fwd_30']:
        dist_df[col] = dist_df['entry_idx'].apply(lambda idx: df.loc[idx, col] if idx in df.index else np.nan)

    print(f"Total zones: {len(dist_df)}")
    print(f"Avg zone length: {dist_df['zone_bars'].mean():.1f} bars")
    print(f"Avg zone volume: {dist_df['avg_volume'].mean():,.0f}")
    print()
    print("Forward returns after distribution zone (negative = short profit):")
    for i in [5, 10, 20, 30]:
        fwd_ret = dist_df[f'fwd_{i}'].mean() * 100
        win_rate = (dist_df[f'fwd_{i}'] < 0).mean() * 100  # Negative = short profit
        min_ret = dist_df[f'fwd_{i}'].min() * 100 if not dist_df[f'fwd_{i}'].isna().all() else 0
        print(f"  +{i} bars: {fwd_ret:+.3f}% (Short WR: {win_rate:.1f}%, Best: {min_ret:+.2f}%)")
    print()

# ============================================================================
# BACKTEST WITH 7:1 R:R (as user observed)
# ============================================================================
print("=" * 80)
print("BACKTEST: VOLUME ZONE STRATEGY (3:1 R:R)")
print("=" * 80)

trades = []

# LONG trades from accumulation zones
if len(accumulation_zones) > 0:
    for zone in accumulation_zones:
        entry_idx = zone['entry_idx']
        if entry_idx not in df.index or pd.isna(df.loc[entry_idx, 'atr']):
            continue

        entry_price = zone['entry_price']
        zone_low = zone['zone_low']
        atr = df.loc[entry_idx, 'atr']

        # Entry: breakout above zone
        # Stop: below zone low (or 1x ATR, whichever is tighter)
        stop_loss = max(zone_low - (0.5 * atr), entry_price - (1.0 * atr))
        sl_distance = entry_price - stop_loss

        # Target: 3:1 R:R (profitable with 35% WR)
        take_profit = entry_price + (3.0 * sl_distance)

        # Check next 30 bars for SL/TP
        for i in range(1, 31):
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
            # Neither hit - exit at market after 30 bars
            exit_price = df.iloc[entry_idx + 30]['close'] if entry_idx + 30 < len(df) else entry_price
            pnl = (exit_price / entry_price - 1) - 0.001
            trades.append({
                'direction': 'LONG',
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': 30,
                'exit_reason': 'TIME',
                'zone_bars': zone['zone_bars']
            })

# SHORT trades from distribution zones
if len(distribution_zones) > 0:
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

        # Target: 3:1 R:R (profitable with 35% WR)
        take_profit = entry_price - (3.0 * sl_distance)

        for i in range(1, 31):
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
            exit_price = df.iloc[entry_idx + 30]['close'] if entry_idx + 30 < len(df) else entry_price
            pnl = (entry_price / exit_price - 1) - 0.001
            trades.append({
                'direction': 'SHORT',
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': 30,
                'exit_reason': 'TIME',
                'zone_bars': zone['zone_bars']
            })

# Backtest results
trades_df = pd.DataFrame(trades)

if len(trades_df) > 0:
    total_return = trades_df['pnl'].sum() * 100
    avg_trade = trades_df['pnl'].mean() * 100
    win_rate = (trades_df['pnl'] > 0).mean() * 100
    avg_winner = trades_df[trades_df['pnl'] > 0]['pnl'].mean() * 100 if (trades_df['pnl'] > 0).any() else 0
    avg_loser = trades_df[trades_df['pnl'] < 0]['pnl'].mean() * 100 if (trades_df['pnl'] < 0).any() else 0

    print(f"Total trades: {len(trades_df)}")
    print(f"Total return: {total_return:+.2f}%")
    print(f"Avg trade: {avg_trade:+.3f}%")
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Avg winner: {avg_winner:+.3f}%")
    print(f"Avg loser: {avg_loser:+.3f}%")

    if avg_loser != 0:
        actual_rr = abs(avg_winner / avg_loser)
        print(f"Actual R:R: {actual_rr:.2f}:1")
    print()

    # Exit reason breakdown
    print("Exit reasons:")
    print(trades_df['exit_reason'].value_counts())
    print()

    # Direction breakdown
    print("By direction:")
    for direction in ['LONG', 'SHORT']:
        direction_trades = trades_df[trades_df['direction'] == direction]
        if len(direction_trades) > 0:
            direction_return = direction_trades['pnl'].sum() * 100
            direction_wr = (direction_trades['pnl'] > 0).mean() * 100
            print(f"  {direction}: {len(direction_trades)} trades, {direction_return:+.2f}%, WR: {direction_wr:.1f}%")
    print()

    # Zone length analysis
    print("Performance by zone length:")
    for min_bars in [5, 7, 10]:
        zone_trades = trades_df[trades_df['zone_bars'] >= min_bars]
        if len(zone_trades) > 0:
            zone_return = zone_trades['pnl'].sum() * 100
            zone_wr = (zone_trades['pnl'] > 0).mean() * 100
            print(f"  {min_bars}+ bars: {len(zone_trades)} trades, {zone_return:+.2f}%, WR: {zone_wr:.1f}%")
    print()

    # Save results
    trades_df.to_csv('results/PENGU_volume_zones_trades.csv', index=False)
    print("✅ Trades saved to: results/PENGU_volume_zones_trades.csv")
else:
    print("❌ No trades generated")

print()
print("=" * 80)
print("CONCLUSION")
print("=" * 80)
print("Volume zones test the hypothesis:")
print("  - Single-candle volume spikes = noise")
print("  - Multi-bar volume accumulation at extremes = real whale activity")
print("  - Accumulation zones at lows → Long")
print("  - Distribution zones at highs → Short")
print("  - Target: 3:1 R:R (profitable with 35% WR)")
