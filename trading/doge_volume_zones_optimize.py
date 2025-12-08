#!/usr/bin/env python3
"""
DOGE Volume Zones Optimization
Test 96 configurations to find optimal volume zone parameters for DOGE
"""

import pandas as pd
import numpy as np

# Load DOGE data
print("Loading DOGE data...")
df = pd.read_csv('doge_usdt_1m_lbank.csv')
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

def is_asia_eu_session(timestamp):
    """Check if timestamp is in Asia/EU session (07:00-14:00 UTC)"""
    hour = timestamp.hour
    return 7 <= hour < 14

def is_us_session(timestamp):
    """Check if timestamp is in US session (14:00-21:00 UTC)"""
    hour = timestamp.hour
    return 14 <= hour < 21

def backtest_config(df, accumulation_zones, distribution_zones, config):
    """Backtest a single configuration"""
    sl_type = config['sl_type']
    sl_value = config['sl_value']
    tp_type = config['tp_type']
    tp_value = config['tp_value']
    session = config['session']
    max_hold_bars = config['max_hold_bars']

    trades = []

    # LONG trades from accumulation zones
    for zone in accumulation_zones:
        entry_idx = zone['entry_idx']
        if entry_idx not in df.index:
            continue

        # Session filter
        entry_time = df.loc[entry_idx, 'timestamp']
        if session == 'overnight' and not is_overnight_session(entry_time):
            continue
        elif session == 'asia_eu' and not is_asia_eu_session(entry_time):
            continue
        elif session == 'us' and not is_us_session(entry_time):
            continue

        entry_price = zone['entry_price']
        atr = df.loc[entry_idx, 'atr']

        # Calculate stop loss
        if sl_type == 'fixed_pct':
            stop_loss = entry_price * (1 - sl_value / 100)
        else:  # atr
            stop_loss = entry_price - (sl_value * atr)

        sl_distance = entry_price - stop_loss

        # Calculate take profit
        if tp_type == 'fixed_pct':
            take_profit = entry_price * (1 + tp_value / 100)
        else:  # rr_multiple
            take_profit = entry_price + (tp_value * sl_distance)

        # Check next bars for SL/TP
        for i in range(1, max_hold_bars + 1):
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
                    'exit_reason': 'SL'
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
                    'exit_reason': 'TP'
                })
                break
        else:
            # Time exit
            exit_price = df.iloc[entry_idx + max_hold_bars]['close'] if entry_idx + max_hold_bars < len(df) else entry_price
            pnl = (exit_price / entry_price - 1) - 0.001
            trades.append({
                'direction': 'LONG',
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': max_hold_bars,
                'exit_reason': 'TIME'
            })

    # SHORT trades from distribution zones
    for zone in distribution_zones:
        entry_idx = zone['entry_idx']
        if entry_idx not in df.index:
            continue

        # Session filter
        entry_time = df.loc[entry_idx, 'timestamp']
        if session == 'overnight' and not is_overnight_session(entry_time):
            continue
        elif session == 'asia_eu' and not is_asia_eu_session(entry_time):
            continue
        elif session == 'us' and not is_us_session(entry_time):
            continue

        entry_price = zone['entry_price']
        atr = df.loc[entry_idx, 'atr']

        # Calculate stop loss
        if sl_type == 'fixed_pct':
            stop_loss = entry_price * (1 + sl_value / 100)
        else:  # atr
            stop_loss = entry_price + (sl_value * atr)

        sl_distance = stop_loss - entry_price

        # Calculate take profit
        if tp_type == 'fixed_pct':
            take_profit = entry_price * (1 - tp_value / 100)
        else:  # rr_multiple
            take_profit = entry_price - (tp_value * sl_distance)

        for i in range(1, max_hold_bars + 1):
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
                    'exit_reason': 'SL'
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
                    'exit_reason': 'TP'
                })
                break
        else:
            exit_price = df.iloc[entry_idx + max_hold_bars]['close'] if entry_idx + max_hold_bars < len(df) else entry_price
            pnl = (entry_price / exit_price - 1) - 0.001
            trades.append({
                'direction': 'SHORT',
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': max_hold_bars,
                'exit_reason': 'TIME'
            })

    return trades

# ============================================================================
# OPTIMIZATION
# ============================================================================
print("=" * 80)
print("DOGE VOLUME ZONES OPTIMIZATION")
print("=" * 80)
print()

# Test configurations
sl_configs = [
    {'sl_type': 'fixed_pct', 'sl_value': 0.5},
    {'sl_type': 'atr', 'sl_value': 1.0},
    {'sl_type': 'atr', 'sl_value': 1.5},
    {'sl_type': 'atr', 'sl_value': 2.0},
]

tp_configs = [
    {'tp_type': 'rr_multiple', 'tp_value': 2.0},
    {'tp_type': 'rr_multiple', 'tp_value': 3.0},
    {'tp_type': 'rr_multiple', 'tp_value': 4.0},
]

sessions = ['overnight', 'asia_eu', 'us', 'all']

# Fixed volume zone detection
volume_threshold = 1.5
min_consecutive = 5

zones = detect_volume_zones(df, volume_threshold, min_consecutive, max_consecutive=15)
acc_zones, dist_zones = classify_zones(df, zones)

print(f"Volume zones detected (1.5x threshold, 5+ bars):")
print(f"  Accumulation zones (LONG): {len(acc_zones)}")
print(f"  Distribution zones (SHORT): {len(dist_zones)}")
print()

results = []

for sl_config in sl_configs:
    for tp_config in tp_configs:
        for session in sessions:
            config = {
                **sl_config,
                **tp_config,
                'session': session,
                'max_hold_bars': 90
            }

            trades = backtest_config(df, acc_zones, dist_zones, config)

            if len(trades) == 0:
                continue

            trades_df = pd.DataFrame(trades)

            # Calculate metrics
            total_return = trades_df['pnl'].sum() * 100

            # Drawdown
            trades_df['cumulative_pnl'] = (trades_df['pnl'] * 100).cumsum()
            trades_df['equity'] = 100 + trades_df['cumulative_pnl']
            trades_df['running_max'] = trades_df['equity'].cummax()
            trades_df['drawdown'] = trades_df['equity'] - trades_df['running_max']
            trades_df['drawdown_pct'] = (trades_df['drawdown'] / trades_df['running_max']) * 100
            max_drawdown = trades_df['drawdown_pct'].min()

            win_rate = (trades_df['pnl'] > 0).mean() * 100
            return_dd = abs(total_return / max_drawdown) if max_drawdown < 0 else float('inf')

            results.append({
                'sl_type': sl_config['sl_type'],
                'sl_value': sl_config['sl_value'],
                'tp_type': tp_config['tp_type'],
                'tp_value': tp_config['tp_value'],
                'session': session,
                'return': total_return,
                'max_dd': max_drawdown,
                'return_dd': return_dd,
                'win_rate': win_rate,
                'trades': len(trades_df)
            })

# Sort by Return/DD ratio
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

print("=" * 100)
print("TOP 10 CONFIGURATIONS (by Return/DD ratio)")
print("=" * 100)
print(f"{'Rank':<6} {'SL Type':<12} {'SL Val':<8} {'TP Type':<15} {'TP Val':<8} {'Session':<12} {'Return':>10} {'Max DD':>10} {'R/DD':>10} {'WR':>8} {'Trades':>8}")
print("-" * 100)

for i, row in results_df.head(10).iterrows():
    sl_str = f"{row['sl_type']}"
    sl_val = f"{row['sl_value']:.1f}"
    tp_str = f"{row['tp_type']}"
    tp_val = f"{row['tp_value']:.1f}"

    print(f"{results_df.index.get_loc(i)+1:<6} {sl_str:<12} {sl_val:<8} {tp_str:<15} {tp_val:<8} {row['session']:<12} {row['return']:>9.2f}% {row['max_dd']:>9.2f}% {row['return_dd']:>9.2f}x {row['win_rate']:>7.1f}% {row['trades']:>8}")

print()

# Best config details
best = results_df.iloc[0]

print("=" * 80)
print("BEST CONFIGURATION DETAILS")
print("=" * 80)
print(f"Stop Loss: {best['sl_type']} {best['sl_value']:.1f}{'%' if best['sl_type'] == 'fixed_pct' else 'x ATR'}")
print(f"Take Profit: {best['tp_type']} {best['tp_value']:.1f}{'%' if best['tp_type'] == 'fixed_pct' else 'x'}")
print(f"Session: {best['session']}")
print(f"Max Hold: 90 bars")
print()
print(f"Total Trades: {best['trades']}")
print(f"Total Return: {best['return']:+.2f}%")
print(f"Max Drawdown: {best['max_dd']:.2f}%")
print(f"Return/DD Ratio: {best['return_dd']:.2f}x")
print(f"Win Rate: {best['win_rate']:.1f}%")
print()

# Run best config to get trade details
best_config = {
    'sl_type': best['sl_type'],
    'sl_value': best['sl_value'],
    'tp_type': best['tp_type'],
    'tp_value': best['tp_value'],
    'session': best['session'],
    'max_hold_bars': 90
}

best_trades = backtest_config(df, acc_zones, dist_zones, best_config)
best_trades_df = pd.DataFrame(best_trades)

# Exit reasons
print("Exit Reasons:")
exit_counts = best_trades_df['exit_reason'].value_counts()
for reason, count in exit_counts.items():
    print(f"  {reason}: {count} ({count/len(best_trades_df)*100:.1f}%)")
print()

# Direction breakdown
print("By Direction:")
for direction in ['LONG', 'SHORT']:
    dir_trades = best_trades_df[best_trades_df['direction'] == direction]
    if len(dir_trades) > 0:
        dir_return = dir_trades['pnl'].sum() * 100
        dir_wr = (dir_trades['pnl'] > 0).mean() * 100
        print(f"  {direction}: {len(dir_trades)} trades, {dir_return:+.2f}%, WR: {dir_wr:.1f}%")
print()

# Compare to other tokens
print("=" * 80)
print("COMPARISON TO OTHER VOLUME ZONE STRATEGIES")
print("=" * 80)
print(f"{'Token':<10} {'Return':>10} {'Max DD':>10} {'Return/DD':>12} {'Trades':>8} {'Win Rate':>10}")
print("-" * 80)
print(f"{'TRUMP':<10} {'+8.06%':>10} {'-0.76%':>10} {'10.56x':>12} {21:>8} {'61.9%':>10}")
print(f"{'PEPE':<10} {'+2.57%':>10} {'-0.38%':>10} {'6.80x':>12} {15:>8} {'66.7%':>10}")
print(f"{'ETH':<10} {'+3.78%':>10} {'-1.05%':>10} {'3.60x':>12} {17:>8} {'52.9%':>10}")
doge_return = f"{best['return']:+.2f}%"
doge_dd = f"{best['max_dd']:.2f}%"
doge_rdd = f"{best['return_dd']:.2f}x"
doge_wr = f"{best['win_rate']:.1f}%"
print(f"{'DOGE':<10} {doge_return:>10} {doge_dd:>10} {doge_rdd:>12} {best['trades']:>8} {doge_wr:>10}")
print()

if best['return_dd'] > 8.0:
    print("🎯 EXCELLENT: DOGE volume zones competitive with TRUMP!")
elif best['return_dd'] > 5.0:
    print("✅ GOOD: DOGE has solid risk-adjusted returns")
elif best['return_dd'] > 3.0:
    print("⚠️  MODERATE: Tradeable but lower R/DD than top strategies")
else:
    print("❌ POOR: DOGE volume zones underperform other tokens")

# Save results
best_trades_df.to_csv('results/DOGE_volume_zones_optimized_trades.csv', index=False)
results_df.to_csv('results/DOGE_volume_zones_all_configs.csv', index=False)

print(f"\n✅ Results saved:")
print(f"  - results/DOGE_volume_zones_optimized_trades.csv")
print(f"  - results/DOGE_volume_zones_all_configs.csv")
