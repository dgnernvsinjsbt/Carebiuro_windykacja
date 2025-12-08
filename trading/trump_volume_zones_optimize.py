#!/usr/bin/env python3
"""
TRUMP Volume Zones - COMPREHENSIVE OPTIMIZATION

Optimize every dimension:
1. Trading sessions (Asia/EU/US/Overnight)
2. SL/TP levels (ATR multipliers, fixed %, adaptive)
3. Zone filters (min length, volume threshold)
4. Time-based exits
5. Direction filters (long only, short only, both)
"""

import pandas as pd
import numpy as np
from itertools import product

# Load TRUMP data
print("Loading TRUMP data...")
df = pd.read_csv('trump_usdt_1m_mexc.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hour'] = df['timestamp'].dt.hour

# Calculate indicators
df['range'] = df['high'] - df['low']
df['atr'] = df['range'].rolling(14).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100
df['body'] = df['close'] - df['open']
df['vol_ma'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma']

# Session definitions
def get_session(hour):
    if 0 <= hour < 7:
        return 'overnight'
    elif 7 <= hour < 14:
        return 'asia_eu'
    elif 14 <= hour < 21:
        return 'us'
    else:
        return 'overnight'

df['session'] = df['hour'].apply(get_session)

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

    if in_zone and zone_bars >= min_consecutive:
        volume_zones.append({
            'start': zone_start,
            'end': len(df) - 1,
            'bars': zone_bars
        })

    return volume_zones

def classify_zones(df, volume_zones):
    """Classify zones as accumulation or distribution"""
    accumulation_zones = []
    distribution_zones = []

    for zone in volume_zones:
        start_idx = zone['start']
        end_idx = zone['end']

        if start_idx < 20 or end_idx >= len(df) - 60:
            continue

        zone_low = df.loc[start_idx:end_idx, 'low'].min()
        zone_high = df.loc[start_idx:end_idx, 'high'].max()

        lookback_start = max(0, start_idx - 20)
        lookahead_end = min(len(df), end_idx + 5)

        # Accumulation zone
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
                    'entry_session': df.loc[entry_idx, 'session'],
                })

        # Distribution zone
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
                    'entry_session': df.loc[entry_idx, 'session'],
                })

    return accumulation_zones, distribution_zones

def backtest_optimized(df, acc_zones, dist_zones, config):
    """
    Backtest with flexible configuration

    config = {
        'sl_type': 'atr', 'fixed_pct', 'zone_based'
        'sl_value': ATR multiplier or % value
        'tp_type': 'atr', 'fixed_pct', 'rr_multiple'
        'tp_value': ATR multiplier, % value, or R:R ratio
        'max_hold_bars': 60 (time exit)
        'session_filter': None, 'asia_eu', 'us', 'overnight'
        'trade_longs': True/False
        'trade_shorts': True/False
    }
    """
    trades = []

    session_filter = config.get('session_filter', None)
    trade_longs = config.get('trade_longs', True)
    trade_shorts = config.get('trade_shorts', True)
    max_hold = config.get('max_hold_bars', 60)

    # LONG trades
    if trade_longs:
        for zone in acc_zones:
            entry_idx = zone['entry_idx']

            # Session filter
            if session_filter and zone['entry_session'] != session_filter:
                continue

            if entry_idx not in df.index or pd.isna(df.loc[entry_idx, 'atr']):
                continue

            entry_price = zone['entry_price']
            zone_low = zone['zone_low']
            atr = df.loc[entry_idx, 'atr']

            # Calculate stop loss
            if config['sl_type'] == 'atr':
                sl_distance = config['sl_value'] * atr
                stop_loss = entry_price - sl_distance
            elif config['sl_type'] == 'fixed_pct':
                sl_distance = entry_price * (config['sl_value'] / 100)
                stop_loss = entry_price - sl_distance
            elif config['sl_type'] == 'zone_based':
                # Below zone low + buffer
                stop_loss = zone_low - (config['sl_value'] * atr)
                sl_distance = entry_price - stop_loss

            # Calculate take profit
            if config['tp_type'] == 'atr':
                take_profit = entry_price + (config['tp_value'] * atr)
            elif config['tp_type'] == 'fixed_pct':
                take_profit = entry_price * (1 + config['tp_value'] / 100)
            elif config['tp_type'] == 'rr_multiple':
                take_profit = entry_price + (config['tp_value'] * sl_distance)

            # Simulate trade
            for i in range(1, max_hold + 1):
                if entry_idx + i >= len(df):
                    break
                candle = df.iloc[entry_idx + i]

                if candle['low'] <= stop_loss:
                    pnl = (stop_loss / entry_price - 1) - 0.001
                    trades.append({
                        'direction': 'LONG',
                        'pnl': pnl,
                        'bars': i,
                        'exit_reason': 'SL',
                        'zone_bars': zone['zone_bars'],
                        'session': zone['entry_session']
                    })
                    break

                if candle['high'] >= take_profit:
                    pnl = (take_profit / entry_price - 1) - 0.001
                    trades.append({
                        'direction': 'LONG',
                        'pnl': pnl,
                        'bars': i,
                        'exit_reason': 'TP',
                        'zone_bars': zone['zone_bars'],
                        'session': zone['entry_session']
                    })
                    break
            else:
                exit_price = df.iloc[entry_idx + max_hold]['close'] if entry_idx + max_hold < len(df) else entry_price
                pnl = (exit_price / entry_price - 1) - 0.001
                trades.append({
                    'direction': 'LONG',
                    'pnl': pnl,
                    'bars': max_hold,
                    'exit_reason': 'TIME',
                    'zone_bars': zone['zone_bars'],
                    'session': zone['entry_session']
                })

    # SHORT trades
    if trade_shorts:
        for zone in dist_zones:
            entry_idx = zone['entry_idx']

            if session_filter and zone['entry_session'] != session_filter:
                continue

            if entry_idx not in df.index or pd.isna(df.loc[entry_idx, 'atr']):
                continue

            entry_price = zone['entry_price']
            zone_high = zone['zone_high']
            atr = df.loc[entry_idx, 'atr']

            # Calculate stop loss
            if config['sl_type'] == 'atr':
                sl_distance = config['sl_value'] * atr
                stop_loss = entry_price + sl_distance
            elif config['sl_type'] == 'fixed_pct':
                sl_distance = entry_price * (config['sl_value'] / 100)
                stop_loss = entry_price + sl_distance
            elif config['sl_type'] == 'zone_based':
                stop_loss = zone_high + (config['sl_value'] * atr)
                sl_distance = stop_loss - entry_price

            # Calculate take profit
            if config['tp_type'] == 'atr':
                take_profit = entry_price - (config['tp_value'] * atr)
            elif config['tp_type'] == 'fixed_pct':
                take_profit = entry_price * (1 - config['tp_value'] / 100)
            elif config['tp_type'] == 'rr_multiple':
                take_profit = entry_price - (config['tp_value'] * sl_distance)

            # Simulate trade
            for i in range(1, max_hold + 1):
                if entry_idx + i >= len(df):
                    break
                candle = df.iloc[entry_idx + i]

                if candle['high'] >= stop_loss:
                    pnl = (entry_price / stop_loss - 1) - 0.001
                    trades.append({
                        'direction': 'SHORT',
                        'pnl': pnl,
                        'bars': i,
                        'exit_reason': 'SL',
                        'zone_bars': zone['zone_bars'],
                        'session': zone['entry_session']
                    })
                    break

                if candle['low'] <= take_profit:
                    pnl = (entry_price / take_profit - 1) - 0.001
                    trades.append({
                        'direction': 'SHORT',
                        'pnl': pnl,
                        'bars': i,
                        'exit_reason': 'TP',
                        'zone_bars': zone['zone_bars'],
                        'session': zone['entry_session']
                    })
                    break
            else:
                exit_price = df.iloc[entry_idx + max_hold]['close'] if entry_idx + max_hold < len(df) else entry_price
                pnl = (entry_price / exit_price - 1) - 0.001
                trades.append({
                    'direction': 'SHORT',
                    'pnl': pnl,
                    'bars': max_hold,
                    'exit_reason': 'TIME',
                    'zone_bars': zone['zone_bars'],
                    'session': zone['entry_session']
                })

    return trades

# ============================================================================
# COMPREHENSIVE PARAMETER OPTIMIZATION
# ============================================================================
print("=" * 80)
print("TRUMP VOLUME ZONES - COMPREHENSIVE OPTIMIZATION")
print("=" * 80)
print()

# First, detect zones with baseline config
baseline_zones = detect_volume_zones(df, volume_threshold=1.5, min_consecutive=5)
baseline_acc, baseline_dist = classify_zones(df, baseline_zones)

print(f"Baseline zones detected: {len(baseline_zones)}")
print(f"  Accumulation: {len(baseline_acc)}")
print(f"  Distribution: {len(baseline_dist)}")
print()

results = []

# Optimization grid
sl_configs = [
    {'sl_type': 'atr', 'sl_value': 0.5},
    {'sl_type': 'atr', 'sl_value': 0.75},
    {'sl_type': 'atr', 'sl_value': 1.0},
    {'sl_type': 'atr', 'sl_value': 1.5},
    {'sl_type': 'zone_based', 'sl_value': 0.3},
    {'sl_type': 'zone_based', 'sl_value': 0.5},
    {'sl_type': 'fixed_pct', 'sl_value': 0.3},
    {'sl_type': 'fixed_pct', 'sl_value': 0.5},
]

tp_configs = [
    {'tp_type': 'rr_multiple', 'tp_value': 3.0},
    {'tp_type': 'rr_multiple', 'tp_value': 4.0},
    {'tp_type': 'rr_multiple', 'tp_value': 5.0},
    {'tp_type': 'rr_multiple', 'tp_value': 7.0},
    {'tp_type': 'atr', 'tp_value': 3.0},
    {'tp_type': 'atr', 'tp_value': 4.0},
    {'tp_type': 'fixed_pct', 'tp_value': 0.8},
    {'tp_type': 'fixed_pct', 'tp_value': 1.2},
]

session_configs = [None, 'asia_eu', 'us', 'overnight']
direction_configs = [
    {'trade_longs': True, 'trade_shorts': True},
    {'trade_longs': True, 'trade_shorts': False},
    {'trade_longs': False, 'trade_shorts': True},
]
max_hold_configs = [45, 60, 90]

print(f"Testing {len(sl_configs) * len(tp_configs) * len(session_configs) * len(direction_configs) * len(max_hold_configs)} configurations...")
print()

config_count = 0
for sl_cfg, tp_cfg, session, dir_cfg, max_hold in product(
    sl_configs, tp_configs, session_configs, direction_configs, max_hold_configs
):
    config_count += 1

    config = {
        **sl_cfg,
        **tp_cfg,
        'session_filter': session,
        **dir_cfg,
        'max_hold_bars': max_hold
    }

    trades = backtest_optimized(df, baseline_acc, baseline_dist, config)

    if len(trades) < 10:  # Need at least 10 trades
        continue

    trades_df = pd.DataFrame(trades)
    total_return = trades_df['pnl'].sum() * 100
    win_rate = (trades_df['pnl'] > 0).mean() * 100

    winners = trades_df[trades_df['pnl'] > 0]
    losers = trades_df[trades_df['pnl'] <= 0]

    avg_winner = winners['pnl'].mean() * 100 if len(winners) > 0 else 0
    avg_loser = losers['pnl'].mean() * 100 if len(losers) > 0 else 0
    profit_factor = abs(winners['pnl'].sum() / losers['pnl'].sum()) if len(losers) > 0 and losers['pnl'].sum() != 0 else 0

    # Calculate max drawdown
    cumulative = (trades_df['pnl'] * 100).cumsum()
    running_max = cumulative.cummax()
    drawdown = cumulative - running_max
    max_dd = drawdown.min()

    results.append({
        'config': config,
        'trades': len(trades_df),
        'return': total_return,
        'win_rate': win_rate,
        'avg_winner': avg_winner,
        'avg_loser': avg_loser,
        'profit_factor': profit_factor,
        'max_dd': max_dd,
        'return_dd_ratio': abs(total_return / max_dd) if max_dd != 0 else 0,
        'trades_df': trades_df
    })

# Sort by return
results = sorted(results, key=lambda x: x['return'], reverse=True)

print(f"Generated {len(results)} valid configurations")
print()
print("=" * 120)
print("TOP 20 CONFIGURATIONS BY TOTAL RETURN")
print("=" * 120)
print(f"{'Rank':<5} {'SL Type':<12} {'SL Val':<7} {'TP Type':<12} {'TP Val':<7} {'Session':<10} {'Dir':<6} {'Hold':<5} {'Trades':<7} {'Return':<8} {'WR':<6} {'MaxDD':<8} {'R/DD':<6}")
print("-" * 120)

for i, r in enumerate(results[:20], 1):
    cfg = r['config']
    direction = 'BOTH' if cfg['trade_longs'] and cfg['trade_shorts'] else ('LONG' if cfg['trade_longs'] else 'SHORT')
    session_str = cfg['session_filter'] or 'ALL'

    print(f"{i:<5} {cfg['sl_type']:<12} {cfg['sl_value']:<7.2f} {cfg['tp_type']:<12} {cfg['tp_value']:<7.1f} "
          f"{session_str:<10} {direction:<6} {cfg['max_hold_bars']:<5} {r['trades']:<7} "
          f"{r['return']:<7.2f}% {r['win_rate']:<5.1f}% {r['max_dd']:<7.2f}% {r['return_dd_ratio']:<6.2f}")

# Best config details
best = results[0]
print("\n" + "=" * 80)
print("BEST CONFIGURATION DETAILS")
print("=" * 80)
print(f"Stop Loss: {best['config']['sl_type']} @ {best['config']['sl_value']}")
print(f"Take Profit: {best['config']['tp_type']} @ {best['config']['tp_value']}")
print(f"Session Filter: {best['config']['session_filter'] or 'ALL'}")
print(f"Direction: {'BOTH' if best['config']['trade_longs'] and best['config']['trade_shorts'] else ('LONG ONLY' if best['config']['trade_longs'] else 'SHORT ONLY')}")
print(f"Max Hold: {best['config']['max_hold_bars']} bars")
print()
print(f"Total Trades: {best['trades']}")
print(f"Total Return: {best['return']:+.2f}%")
print(f"Win Rate: {best['win_rate']:.1f}%")
print(f"Avg Winner: {best['avg_winner']:+.2f}%")
print(f"Avg Loser: {best['avg_loser']:+.2f}%")
print(f"Profit Factor: {best['profit_factor']:.2f}")
print(f"Max Drawdown: {best['max_dd']:.2f}%")
print(f"Return/DD Ratio: {best['return_dd_ratio']:.2f}x")

# Save best config
best['trades_df'].to_csv('results/TRUMP_volume_zones_optimized_trades.csv', index=False)
print(f"\n✅ Best config trades saved to: results/TRUMP_volume_zones_optimized_trades.csv")

# Compare to baseline
print("\n" + "=" * 80)
print("IMPROVEMENT VS BASELINE")
print("=" * 80)
print(f"Baseline (5:1 R:R, no filters):  +9.89% | 54 trades | -1.54% DD")
print(f"Optimized (best config):         {best['return']:+.2f}% | {best['trades']} trades | {best['max_dd']:.2f}% DD")
print(f"Improvement: {best['return'] - 9.89:+.2f}%")
