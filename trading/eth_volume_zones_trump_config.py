#!/usr/bin/env python3
"""
Test TRUMP Volume Zones Best Config on ETH
Apply exact same configuration that worked for TRUMP (10.56x R/DD)
"""

import pandas as pd
import numpy as np

# Load ETH data
print("Loading ETH data...")
df = pd.read_csv('eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Calculate indicators
df['range'] = df['high'] - df['low']
df['atr'] = df['range'].rolling(14).mean()

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

def is_overnight_session(timestamp):
    """Check if timestamp is in overnight session (21:00-07:00 UTC)"""
    hour = timestamp.hour
    return hour >= 21 or hour < 7

def backtest_trump_config(df, accumulation_zones, distribution_zones):
    """
    Backtest using TRUMP's best config:
    - 0.5% fixed SL
    - 4:1 R:R (2.0% TP)
    - Overnight session only (21:00-07:00 UTC)
    - Max hold: 90 bars
    """
    trades = []

    # LONG trades from accumulation zones
    for zone in accumulation_zones:
        entry_idx = zone['entry_idx']
        if entry_idx not in df.index:
            continue

        # Session filter: overnight only
        entry_time = df.loc[entry_idx, 'timestamp']
        if not is_overnight_session(entry_time):
            continue

        entry_price = zone['entry_price']

        # Fixed 0.5% stop
        stop_loss = entry_price * 0.995
        sl_distance = entry_price - stop_loss

        # 4:1 R:R target (2.0% TP)
        take_profit = entry_price + (4.0 * sl_distance)

        # Check next 90 bars for SL/TP
        for i in range(1, 91):
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
            # Time exit after 90 bars
            exit_price = df.iloc[entry_idx + 90]['close'] if entry_idx + 90 < len(df) else entry_price
            pnl = (exit_price / entry_price - 1) - 0.001
            trades.append({
                'direction': 'LONG',
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': 90,
                'exit_reason': 'TIME',
                'zone_bars': zone['zone_bars']
            })

    # SHORT trades from distribution zones
    for zone in distribution_zones:
        entry_idx = zone['entry_idx']
        if entry_idx not in df.index:
            continue

        # Session filter: overnight only
        entry_time = df.loc[entry_idx, 'timestamp']
        if not is_overnight_session(entry_time):
            continue

        entry_price = zone['entry_price']

        # Fixed 0.5% stop
        stop_loss = entry_price * 1.005
        sl_distance = stop_loss - entry_price

        # 4:1 R:R target (2.0% TP)
        take_profit = entry_price - (4.0 * sl_distance)

        for i in range(1, 91):
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
            exit_price = df.iloc[entry_idx + 90]['close'] if entry_idx + 90 < len(df) else entry_price
            pnl = (entry_price / exit_price - 1) - 0.001
            trades.append({
                'direction': 'SHORT',
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': 90,
                'exit_reason': 'TIME',
                'zone_bars': zone['zone_bars']
            })

    return trades

# ============================================================================
# APPLY TRUMP'S BEST CONFIG TO ETH
# ============================================================================
print("=" * 80)
print("ETH VOLUME ZONES - TRUMP'S BEST CONFIG (10.56x R/DD)")
print("=" * 80)
print()
print("Configuration:")
print("  - Volume threshold: 1.5x")
print("  - Min zone bars: 5")
print("  - SL: 0.5% fixed")
print("  - TP: 4:1 R:R (2.0%)")
print("  - Session: Overnight (21:00-07:00 UTC)")
print("  - Max hold: 90 bars")
print()

# TRUMP's best config
volume_threshold = 1.5
min_consecutive = 5

# Detect zones
zones = detect_volume_zones(df, volume_threshold, min_consecutive, max_consecutive=15)
acc_zones, dist_zones = classify_zones(df, zones)

print(f"Total zones detected: {len(zones)}")
print(f"  Accumulation zones (LONG): {len(acc_zones)}")
print(f"  Distribution zones (SHORT): {len(dist_zones)}")
print()

# Backtest
trades = backtest_trump_config(df, acc_zones, dist_zones)

if len(trades) == 0:
    print("❌ No trades generated - config may not fit ETH's characteristics")
else:
    trades_df = pd.DataFrame(trades)

    # Calculate metrics
    total_return = trades_df['pnl'].sum() * 100

    # Drawdown calculation
    trades_df['cumulative_pnl'] = (trades_df['pnl'] * 100).cumsum()
    trades_df['equity'] = 100 + trades_df['cumulative_pnl']
    trades_df['running_max'] = trades_df['equity'].cummax()
    trades_df['drawdown'] = trades_df['equity'] - trades_df['running_max']
    trades_df['drawdown_pct'] = (trades_df['drawdown'] / trades_df['running_max']) * 100
    max_drawdown = trades_df['drawdown_pct'].min()

    win_rate = (trades_df['pnl'] > 0).mean() * 100

    winners = trades_df[trades_df['pnl'] > 0]
    losers = trades_df[trades_df['pnl'] < 0]

    avg_winner = winners['pnl'].mean() * 100 if len(winners) > 0 else 0
    avg_loser = losers['pnl'].mean() * 100 if len(losers) > 0 else 0

    profit_factor = abs(winners['pnl'].sum() / losers['pnl'].sum()) if len(losers) > 0 else float('inf')

    return_dd = abs(total_return / max_drawdown) if max_drawdown < 0 else float('inf')

    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total trades: {len(trades_df)}")
    print(f"Total return: {total_return:+.2f}%")
    print(f"Max drawdown: {max_drawdown:.2f}%")
    print(f"Return/DD ratio: {return_dd:.2f}x")
    print()
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Winners: {len(winners)} | Avg: {avg_winner:+.2f}%")
    print(f"Losers: {len(losers)} | Avg: {avg_loser:+.2f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print()

    # Exit reasons
    print("Exit reasons:")
    exit_counts = trades_df['exit_reason'].value_counts()
    for reason, count in exit_counts.items():
        print(f"  {reason}: {count} ({count/len(trades_df)*100:.1f}%)")
    print()

    # Direction breakdown
    print("By direction:")
    for direction in ['LONG', 'SHORT']:
        dir_trades = trades_df[trades_df['direction'] == direction]
        if len(dir_trades) > 0:
            dir_return = dir_trades['pnl'].sum() * 100
            dir_wr = (dir_trades['pnl'] > 0).mean() * 100
            print(f"  {direction}: {len(dir_trades)} trades, {dir_return:+.2f}%, WR: {dir_wr:.1f}%")
    print()

    # Compare to TRUMP
    print("=" * 80)
    print("COMPARISON TO TRUMP")
    print("=" * 80)
    print(f"{'Token':<10} {'Return':>10} {'Max DD':>10} {'Return/DD':>12} {'Trades':>8} {'Win Rate':>10}")
    print("-" * 80)
    print(f"{'TRUMP':<10} {'+8.06%':>10} {'-0.76%':>10} {'10.56x':>12} {21:>8} {'61.9%':>10}")
    print(f"{'ETH':<10} {f'{total_return:+.2f}%':>10} {f'{max_drawdown:.2f}%':>10} {f'{return_dd:.2f}x':>12} {len(trades_df):>8} {f'{win_rate:.1f}%':>10}")
    print()

    if return_dd > 10.0:
        print("🎯 EXCELLENT: ETH has even better Return/DD than TRUMP!")
    elif return_dd > 5.0:
        print("✅ GOOD: ETH shows solid risk-adjusted returns")
    elif return_dd > 3.0:
        print("⚠️  MODERATE: ETH has lower Return/DD than TRUMP")
    else:
        print("❌ POOR: ETH doesn't work well with TRUMP's config")

    # Save results
    trades_df.to_csv('results/ETH_volume_zones_trump_config_trades.csv', index=False)
    print(f"\n✅ Trades saved to: results/ETH_volume_zones_trump_config_trades.csv")
