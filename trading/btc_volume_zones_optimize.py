#!/usr/bin/env python3
"""
BTC Volume Zones Optimization
Test volume zones approach on BTC 1-minute data
"""

import pandas as pd
import numpy as np

# Load BTC data
print("Loading BTC data...")
df = pd.read_csv('btc_usdt_1m_lbank.csv')
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

def get_session(timestamp):
    """Determine trading session"""
    hour = timestamp.hour
    if hour >= 21 or hour < 7:
        return 'overnight'
    elif 7 <= hour < 14:
        return 'asia_eu'
    else:  # 14 <= hour < 21
        return 'us'

def backtest_config(df, accumulation_zones, distribution_zones, config):
    """Backtest with given configuration"""
    trades = []

    # LONG trades from accumulation zones
    if config['trade_longs']:
        for zone in accumulation_zones:
            entry_idx = zone['entry_idx']
            if entry_idx not in df.index:
                continue

            # Session filter
            entry_time = df.loc[entry_idx, 'timestamp']
            session = get_session(entry_time)
            if config['session_filter'] != 'all' and session != config['session_filter']:
                continue

            entry_price = zone['entry_price']

            # Stop loss
            if config['sl_type'] == 'fixed_pct':
                stop_loss = entry_price * (1 - config['sl_value'] / 100)
            else:  # ATR-based
                atr = df.loc[entry_idx, 'atr']
                if pd.isna(atr):
                    continue
                stop_loss = entry_price - (config['sl_value'] * atr)

            sl_distance = entry_price - stop_loss

            # Take profit
            if config['tp_type'] == 'rr_multiple':
                take_profit = entry_price + (config['tp_value'] * sl_distance)
            else:  # fixed_pct
                take_profit = entry_price * (1 + config['tp_value'] / 100)

            # Check next bars for SL/TP
            max_hold = config.get('max_hold_bars', 90)
            for i in range(1, max_hold + 1):
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
                # Time exit
                exit_idx = entry_idx + max_hold
                if exit_idx < len(df):
                    exit_price = df.iloc[exit_idx]['close']
                    pnl = (exit_price / entry_price - 1) - 0.001
                    trades.append({
                        'direction': 'LONG',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl': pnl,
                        'bars': max_hold,
                        'exit_reason': 'TIME',
                        'zone_bars': zone['zone_bars']
                    })

    # SHORT trades from distribution zones
    if config['trade_shorts']:
        for zone in distribution_zones:
            entry_idx = zone['entry_idx']
            if entry_idx not in df.index:
                continue

            # Session filter
            entry_time = df.loc[entry_idx, 'timestamp']
            session = get_session(entry_time)
            if config['session_filter'] != 'all' and session != config['session_filter']:
                continue

            entry_price = zone['entry_price']

            # Stop loss
            if config['sl_type'] == 'fixed_pct':
                stop_loss = entry_price * (1 + config['sl_value'] / 100)
            else:  # ATR-based
                atr = df.loc[entry_idx, 'atr']
                if pd.isna(atr):
                    continue
                stop_loss = entry_price + (config['sl_value'] * atr)

            sl_distance = stop_loss - entry_price

            # Take profit
            if config['tp_type'] == 'rr_multiple':
                take_profit = entry_price - (config['tp_value'] * sl_distance)
            else:  # fixed_pct
                take_profit = entry_price * (1 - config['tp_value'] / 100)

            max_hold = config.get('max_hold_bars', 90)
            for i in range(1, max_hold + 1):
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
                # Time exit
                exit_idx = entry_idx + max_hold
                if exit_idx < len(df):
                    exit_price = df.iloc[exit_idx]['close']
                    pnl = (entry_price / exit_price - 1) - 0.001
                    trades.append({
                        'direction': 'SHORT',
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl': pnl,
                        'bars': max_hold,
                        'exit_reason': 'TIME',
                        'zone_bars': zone['zone_bars']
                    })

    return trades

# ============================================================================
# OPTIMIZATION GRID
# ============================================================================
print("=" * 80)
print("BTC VOLUME ZONES OPTIMIZATION")
print("=" * 80)
print()

# Detect zones
volume_threshold = 1.5
min_consecutive = 5
zones = detect_volume_zones(df, volume_threshold, min_consecutive, max_consecutive=15)
acc_zones, dist_zones = classify_zones(df, zones)

print(f"Zones detected: {len(zones)} (Acc: {len(acc_zones)}, Dist: {len(dist_zones)})")
print()

results = []

# Parameter grid (focused based on ETH learnings)
sl_configs = [
    {'sl_type': 'fixed_pct', 'sl_value': 0.5},   # TRUMP's config
    {'sl_type': 'fixed_pct', 'sl_value': 1.0},
    {'sl_type': 'atr', 'sl_value': 1.0},
    {'sl_type': 'atr', 'sl_value': 1.5},         # ETH's best
]

tp_configs = [
    {'tp_type': 'rr_multiple', 'tp_value': 2.0},  # ETH's best
    {'tp_type': 'rr_multiple', 'tp_value': 3.0},
    {'tp_type': 'rr_multiple', 'tp_value': 4.0},  # TRUMP's config
]

session_filters = ['all', 'overnight', 'asia_eu', 'us']
direction_configs = [
    {'trade_longs': True, 'trade_shorts': False},   # LONGS only
    {'trade_longs': True, 'trade_shorts': True},    # Both
]

print("Testing configurations...")
tested = 0
total = len(sl_configs) * len(tp_configs) * len(session_filters) * len(direction_configs)

for sl_cfg in sl_configs:
    for tp_cfg in tp_configs:
        for session in session_filters:
            for dir_cfg in direction_configs:
                tested += 1
                if tested % 10 == 0:
                    print(f"  Progress: {tested}/{total}...")

                config = {
                    **sl_cfg,
                    **tp_cfg,
                    'session_filter': session,
                    **dir_cfg,
                    'max_hold_bars': 90
                }

                trades = backtest_config(df, acc_zones, dist_zones, config)

                if len(trades) < 10:  # Minimum 10 trades
                    continue

                trades_df = pd.DataFrame(trades)
                total_return = trades_df['pnl'].sum() * 100

                # Drawdown
                trades_df['cumulative_pnl'] = (trades_df['pnl'] * 100).cumsum()
                trades_df['equity'] = 100 + trades_df['cumulative_pnl']
                trades_df['running_max'] = trades_df['equity'].cummax()
                trades_df['drawdown'] = trades_df['equity'] - trades_df['running_max']
                trades_df['drawdown_pct'] = (trades_df['drawdown'] / trades_df['running_max']) * 100
                max_drawdown = trades_df['drawdown_pct'].min()

                if max_drawdown >= 0:
                    continue

                return_dd = abs(total_return / max_drawdown)
                win_rate = (trades_df['pnl'] > 0).mean() * 100

                winners = trades_df[trades_df['pnl'] > 0]
                losers = trades_df[trades_df['pnl'] < 0]
                avg_winner = winners['pnl'].mean() * 100 if len(winners) > 0 else 0
                avg_loser = losers['pnl'].mean() * 100 if len(losers) > 0 else 0
                profit_factor = abs(winners['pnl'].sum() / losers['pnl'].sum()) if len(losers) > 0 else 0

                results.append({
                    'sl_type': sl_cfg['sl_type'],
                    'sl_value': sl_cfg['sl_value'],
                    'tp_type': tp_cfg['tp_type'],
                    'tp_value': tp_cfg['tp_value'],
                    'session': session,
                    'longs': dir_cfg['trade_longs'],
                    'shorts': dir_cfg['trade_shorts'],
                    'trades': len(trades_df),
                    'return': total_return,
                    'max_dd': max_drawdown,
                    'return_dd': return_dd,
                    'win_rate': win_rate,
                    'avg_winner': avg_winner,
                    'avg_loser': avg_loser,
                    'profit_factor': profit_factor,
                    'trades_df': trades_df
                })

print(f"Completed: {tested}/{total} configurations tested")
print(f"Valid results: {len(results)}")
print()

# Sort by Return/DD ratio
results = sorted(results, key=lambda x: x['return_dd'], reverse=True)

# Display top 15 configs
print("=" * 120)
print(f"{'SL Type':<10} {'SL Val':>7} {'TP Type':<12} {'TP Val':>7} {'Session':<10} {'L/S':<6} {'Trades':>7} {'Return':>8} {'MaxDD':>8} {'R/DD':>8} {'WR':>6} {'PF':>6}")
print("=" * 120)

for r in results[:15]:
    direction = 'L' if r['longs'] and not r['shorts'] else 'L+S'
    print(f"{r['sl_type']:<10} {r['sl_value']:>7.1f} {r['tp_type']:<12} {r['tp_value']:>7.1f} {r['session']:<10} {direction:<6} "
          f"{r['trades']:>7} {r['return']:>7.2f}% {r['max_dd']:>7.2f}% {r['return_dd']:>7.2f}x {r['win_rate']:>5.1f}% {r['profit_factor']:>5.2f}")

if len(results) > 0:
    print()
    print("=" * 80)
    print("BEST CONFIG (by Return/DD)")
    print("=" * 80)
    best = results[0]

    print(f"Stop Loss: {best['sl_type']} {best['sl_value']:.1f}{'%' if best['sl_type']=='fixed_pct' else 'x ATR'}")
    print(f"Take Profit: {best['tp_type']} {best['tp_value']:.1f}{'x' if best['tp_type']=='rr_multiple' else '%'}")
    print(f"Session: {best['session']}")
    print(f"Direction: {'LONGS only' if best['longs'] and not best['shorts'] else 'LONGS + SHORTS'}")
    print()
    print(f"Trades: {best['trades']}")
    print(f"Return: {best['return']:+.2f}%")
    print(f"Max DD: {best['max_dd']:.2f}%")
    print(f"Return/DD: {best['return_dd']:.2f}x")
    print(f"Win Rate: {best['win_rate']:.1f}%")
    print(f"Profit Factor: {best['profit_factor']:.2f}")
    print()

    # Exit reasons
    exit_counts = best['trades_df']['exit_reason'].value_counts()
    print("Exit reasons:")
    for reason, count in exit_counts.items():
        pct = count / len(best['trades_df']) * 100
        print(f"  {reason}: {count} ({pct:.1f}%)")
    print()

    # Compare to TRUMP & ETH
    print("=" * 80)
    print("COMPARISON TO OTHER VOLUME ZONES")
    print("=" * 80)
    print(f"{'Token':<10} {'Return':>10} {'Max DD':>10} {'Return/DD':>12} {'Trades':>8} {'Win Rate':>10}")
    print("-" * 80)
    print(f"{'TRUMP':<10} {'+8.06%':>10} {'-0.76%':>10} {'10.56x':>12} {21:>8} {'61.9%':>10}")
    print(f"{'ETH':<10} {'+3.78%':>10} {'-1.05%':>10} {'3.60x':>12} {17:>8} {'52.9%':>10}")
    btc_return = f"{best['return']:+.2f}%"
    btc_dd = f"{best['max_dd']:.2f}%"
    btc_rdd = f"{best['return_dd']:.2f}x"
    btc_wr = f"{best['win_rate']:.1f}%"
    print(f"{'BTC':<10} {btc_return:>10} {btc_dd:>10} {btc_rdd:>12} {best['trades']:>8} {btc_wr:>10}")
    print()

    if best['return_dd'] > 8.0:
        print("🎯 EXCELLENT: BTC volume zones competitive with TRUMP!")
    elif best['return_dd'] > 5.0:
        print("✅ GOOD: BTC has solid risk-adjusted returns")
    elif best['return_dd'] > 3.0:
        print("⚠️  MODERATE: Tradeable but lower R/DD than TRUMP")
    else:
        print("❌ POOR: BTC volume zones underperform")

    # Save best
    best['trades_df'].to_csv('results/BTC_volume_zones_optimized_trades.csv', index=False)
    print(f"\n✅ Best config trades saved to: results/BTC_volume_zones_optimized_trades.csv")
else:
    print("\n❌ No valid configurations found")
