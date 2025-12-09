#!/usr/bin/env python3
"""
DOGE BINGX COMPREHENSIVE RE-OPTIMIZATION
Goal: Maximize Return/DD ratio with 20+ trades and minimal outlier dependency
"""

import pandas as pd
import numpy as np
from itertools import product

print("=" * 80)
print("DOGE BINGX COMPREHENSIVE RE-OPTIMIZATION")
print("Metric: Return/DD (with 20+ trade minimum)")
print("=" * 80)
print()

# Load data
df = pd.read_csv('./trading/doge_30d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.reset_index(drop=True)

# Calculate indicators
df['range'] = df['high'] - df['low']
df['atr'] = df['range'].rolling(14).mean()
df['vol_ma'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma']

print(f"Loaded {len(df):,} candles")
print()

def detect_volume_zones(df, volume_threshold, min_consecutive, max_consecutive=15):
    """Detect sustained volume zones"""
    zones = []
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
                        zones.append({'start': zone_start, 'end': i - 1, 'bars': zone_bars - 1})
                    zone_start = i
                    zone_bars = 1
        else:
            if in_zone:
                if zone_bars >= min_consecutive:
                    zones.append({'start': zone_start, 'end': i - 1, 'bars': zone_bars})
                in_zone = False
                zone_start = None
                zone_bars = 0

    if in_zone and zone_bars >= min_consecutive:
        zones.append({'start': zone_start, 'end': len(df) - 1, 'bars': zone_bars})

    return zones

def classify_zones(df, zones):
    """Classify as accumulation (LONG) or distribution (SHORT) zones"""
    acc_zones = []
    dist_zones = []

    for zone in zones:
        start_idx = zone['start']
        end_idx = zone['end']

        if start_idx < 20 or end_idx >= len(df) - 30:
            continue

        zone_low = df.loc[start_idx:end_idx, 'low'].min()
        zone_high = df.loc[start_idx:end_idx, 'high'].max()

        lookback_start = max(0, start_idx - 20)
        lookahead_end = min(len(df), end_idx + 5)

        # Accumulation: volume at local low
        if zone_low == df.loc[lookback_start:lookahead_end, 'low'].min():
            entry_idx = end_idx + 1
            if entry_idx < len(df):
                acc_zones.append({
                    'entry_idx': entry_idx,
                    'entry_price': df.loc[entry_idx, 'close'],
                    'entry_time': df.loc[entry_idx, 'timestamp']
                })

        # Distribution: volume at local high
        elif zone_high == df.loc[lookback_start:lookahead_end, 'high'].max():
            entry_idx = end_idx + 1
            if entry_idx < len(df):
                dist_zones.append({
                    'entry_idx': entry_idx,
                    'entry_price': df.loc[entry_idx, 'close'],
                    'entry_time': df.loc[entry_idx, 'timestamp']
                })

    return acc_zones, dist_zones

def is_session(timestamp, session):
    """Check if timestamp is in specified session"""
    hour = timestamp.hour
    if session == 'overnight':
        return hour >= 21 or hour < 7
    elif session == 'asia_eu':
        return 7 <= hour < 14
    elif session == 'us':
        return 14 <= hour < 21
    else:  # 'all'
        return True

def backtest_config(df, acc_zones, dist_zones, config):
    """Run backtest with given configuration"""
    trades = []

    # LONG trades
    for zone in acc_zones:
        entry_idx = zone['entry_idx']
        if entry_idx not in df.index:
            continue

        entry_time = df.loc[entry_idx, 'timestamp']
        if not is_session(entry_time, config['session']):
            continue

        entry_price = zone['entry_price']
        atr = df.loc[entry_idx, 'atr']

        # Calculate SL
        if config['sl_type'] == 'fixed_pct':
            stop_loss = entry_price * (1 - config['sl_value'] / 100)
        else:  # atr
            stop_loss = entry_price - (config['sl_value'] * atr)

        sl_distance = entry_price - stop_loss

        # Calculate TP
        if config['tp_type'] == 'fixed_pct':
            take_profit = entry_price * (1 + config['tp_value'] / 100)
        elif config['tp_type'] == 'rr_multiple':
            take_profit = entry_price + (config['tp_value'] * sl_distance)
        else:  # atr_multiple
            take_profit = entry_price + (config['tp_value'] * atr)

        # Check for SL/TP
        for i in range(1, config['max_hold_bars'] + 1):
            if entry_idx + i >= len(df):
                break
            candle = df.iloc[entry_idx + i]

            if candle['low'] <= stop_loss:
                exit_price = stop_loss
                pnl = (exit_price / entry_price - 1) - 0.001
                trades.append({'direction': 'LONG', 'entry': entry_price, 'exit': exit_price,
                              'pnl': pnl, 'bars': i, 'exit_reason': 'SL', 'entry_time': entry_time})
                break

            if candle['high'] >= take_profit:
                exit_price = take_profit
                pnl = (exit_price / entry_price - 1) - 0.001
                trades.append({'direction': 'LONG', 'entry': entry_price, 'exit': exit_price,
                              'pnl': pnl, 'bars': i, 'exit_reason': 'TP', 'entry_time': entry_time})
                break
        else:
            exit_price = df.iloc[entry_idx + config['max_hold_bars']]['close'] if entry_idx + config['max_hold_bars'] < len(df) else entry_price
            pnl = (exit_price / entry_price - 1) - 0.001
            trades.append({'direction': 'LONG', 'entry': entry_price, 'exit': exit_price,
                          'pnl': pnl, 'bars': config['max_hold_bars'], 'exit_reason': 'TIME', 'entry_time': entry_time})

    # SHORT trades
    for zone in dist_zones:
        entry_idx = zone['entry_idx']
        if entry_idx not in df.index:
            continue

        entry_time = df.loc[entry_idx, 'timestamp']
        if not is_session(entry_time, config['session']):
            continue

        entry_price = zone['entry_price']
        atr = df.loc[entry_idx, 'atr']

        # Calculate SL
        if config['sl_type'] == 'fixed_pct':
            stop_loss = entry_price * (1 + config['sl_value'] / 100)
        else:  # atr
            stop_loss = entry_price + (config['sl_value'] * atr)

        sl_distance = stop_loss - entry_price

        # Calculate TP
        if config['tp_type'] == 'fixed_pct':
            take_profit = entry_price * (1 - config['tp_value'] / 100)
        elif config['tp_type'] == 'rr_multiple':
            take_profit = entry_price - (config['tp_value'] * sl_distance)
        else:  # atr_multiple
            take_profit = entry_price - (config['tp_value'] * atr)

        for i in range(1, config['max_hold_bars'] + 1):
            if entry_idx + i >= len(df):
                break
            candle = df.iloc[entry_idx + i]

            if candle['high'] >= stop_loss:
                exit_price = stop_loss
                pnl = (entry_price / exit_price - 1) - 0.001
                trades.append({'direction': 'SHORT', 'entry': entry_price, 'exit': exit_price,
                              'pnl': pnl, 'bars': i, 'exit_reason': 'SL', 'entry_time': entry_time})
                break

            if candle['low'] <= take_profit:
                exit_price = take_profit
                pnl = (entry_price / exit_price - 1) - 0.001
                trades.append({'direction': 'SHORT', 'entry': entry_price, 'exit': exit_price,
                              'pnl': pnl, 'bars': i, 'exit_reason': 'TP', 'entry_time': entry_time})
                break
        else:
            exit_price = df.iloc[entry_idx + config['max_hold_bars']]['close'] if entry_idx + config['max_hold_bars'] < len(df) else entry_price
            pnl = (entry_price / exit_price - 1) - 0.001
            trades.append({'direction': 'SHORT', 'entry': entry_price, 'exit': exit_price,
                          'pnl': pnl, 'bars': config['max_hold_bars'], 'exit_reason': 'TIME', 'entry_time': entry_time})

    return pd.DataFrame(trades) if trades else None

def calculate_metrics(trades_df):
    """Calculate all metrics including outlier concentration"""
    if trades_df is None or len(trades_df) == 0:
        return None

    total_pnl = trades_df['pnl'].sum() * 100

    # Drawdown
    trades_df['cumulative_pnl'] = (trades_df['pnl'] * 100).cumsum()
    trades_df['equity'] = 100 + trades_df['cumulative_pnl']
    trades_df['running_max'] = trades_df['equity'].cummax()
    trades_df['drawdown'] = trades_df['equity'] - trades_df['running_max']
    trades_df['drawdown_pct'] = (trades_df['drawdown'] / trades_df['running_max']) * 100
    max_dd = trades_df['drawdown_pct'].min()

    win_rate = (trades_df['pnl'] > 0).mean() * 100
    return_dd = abs(total_pnl / max_dd) if max_dd < 0 else 999

    # Outlier analysis
    sorted_pnl = trades_df['pnl'].sort_values(ascending=False) * 100
    top5_pct = sorted_pnl.head(min(5, len(trades_df))).sum() / total_pnl * 100 if total_pnl > 0 else 0
    without_top5 = sorted_pnl.iloc[5:].sum() if len(trades_df) > 5 else 0

    return {
        'trades': len(trades_df),
        'return': total_pnl,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'win_rate': win_rate,
        'top5_pct': top5_pct,
        'without_top5': without_top5
    }

# ============================================================================
# COMPREHENSIVE PARAMETER GRID
# ============================================================================

print("Setting up parameter grid...")
print()

# Volume zone detection parameters (FOCUSED)
volume_thresholds = [1.2, 1.3, 1.5]  # Reduced from 4 to 3
min_zone_bars = [3, 4, 5]  # Reduced from 5 to 3 (most important range)

# Stop loss configurations (FOCUSED)
sl_configs = [
    ('atr', 1.0),
    ('atr', 1.5),
    ('atr', 2.0),
]

# Take profit configurations (ATR-based + best R:R)
tp_configs = [
    ('rr_multiple', 2.0),
    ('rr_multiple', 2.5),
    ('atr_multiple', 2.0),  # NEW
    ('atr_multiple', 3.0),  # NEW
    ('atr_multiple', 4.0),  # NEW
    ('atr_multiple', 5.0),  # NEW
    ('atr_multiple', 6.0),  # NEW
]

# Sessions (FOCUSED - only best sessions)
sessions = ['asia_eu', 'overnight', 'all']  # Skip 'us' (was worst)

# Max hold times
max_hold_bars_list = [90]  # Fixed at 90 (was optimal before)

total_configs = (len(volume_thresholds) * len(min_zone_bars) *
                 len(sl_configs) * len(tp_configs) *
                 len(sessions) * len(max_hold_bars_list))

print(f"Total configurations to test: {total_configs:,}")
print()

# ============================================================================
# RUN OPTIMIZATION
# ============================================================================

all_results = []
tested = 0

print("Running optimization...")
print(f"Progress: ", end='', flush=True)

for vol_thresh, min_bars in product(volume_thresholds, min_zone_bars):
    # Detect zones for this volume config
    zones = detect_volume_zones(df, vol_thresh, min_bars)
    acc_zones, dist_zones = classify_zones(df, zones)

    for (sl_type, sl_val), (tp_type, tp_val), session, max_hold in product(
        sl_configs, tp_configs, sessions, max_hold_bars_list
    ):
        config = {
            'sl_type': sl_type,
            'sl_value': sl_val,
            'tp_type': tp_type,
            'tp_value': tp_val,
            'session': session,
            'max_hold_bars': max_hold
        }

        trades_df = backtest_config(df, acc_zones, dist_zones, config)
        metrics = calculate_metrics(trades_df)

        if metrics and metrics['trades'] >= 20:  # MINIMUM 20 TRADES
            all_results.append({
                'vol_thresh': vol_thresh,
                'min_bars': min_bars,
                'sl_type': sl_type,
                'sl_value': sl_val,
                'tp_type': tp_type,
                'tp_value': tp_val,
                'session': session,
                'max_hold': max_hold,
                **metrics
            })

        tested += 1
        if tested % 500 == 0:
            print(f"{tested:,}...", end='', flush=True)

print(f" {tested:,} done!")
print()

# ============================================================================
# RESULTS
# ============================================================================

if not all_results:
    print("❌ No configurations produced 20+ trades!")
    exit(1)

results_df = pd.DataFrame(all_results)
results_df = results_df.sort_values('return_dd', ascending=False)

print("=" * 140)
print("TOP 20 CONFIGURATIONS (by Return/DD ratio)")
print("=" * 140)
print(f"{'#':<4} {'Vol':>5} {'Bars':>5} {'SL':>10} {'TP':>12} {'Session':>10} {'Hold':>5} {'Return':>8} {'MaxDD':>8} {'R/DD':>8} {'WR':>6} {'Trades':>7} {'Top5%':>7} {'No5':>7}")
print("-" * 140)

for i, row in results_df.head(20).iterrows():
    sl_str = f"{row['sl_value']:.1f}x ATR"
    tp_str = f"{row['tp_value']:.1f}x" if row['tp_type'] == 'atr_multiple' else f"{row['tp_value']:.1f}:1"
    tp_label = 'ATR' if row['tp_type'] == 'atr_multiple' else 'R:R'

    print(f"{len(results_df) - results_df.index.get_loc(i):<4} "
          f"{row['vol_thresh']:>5.1f} {row['min_bars']:>5.0f} "
          f"{sl_str:>10} {tp_str:>8} {tp_label:>3} "
          f"{row['session']:>10} {row['max_hold']:>5.0f} "
          f"{row['return']:>7.2f}% {row['max_dd']:>7.2f}% "
          f"{row['return_dd']:>7.2f}x {row['win_rate']:>5.1f}% "
          f"{row['trades']:>7.0f} {row['top5_pct']:>6.1f}% "
          f"{row['without_top5']:>6.2f}%")

print()

# Best configuration details
best = results_df.iloc[0]

print("=" * 80)
print("BEST CONFIGURATION")
print("=" * 80)
print(f"Volume Threshold: {best['vol_thresh']}x")
print(f"Min Zone Bars: {best['min_bars']:.0f}")
print(f"Stop Loss: {best['sl_value']:.1f}x ATR")
tp_label = "ATR" if best['tp_type'] == 'atr_multiple' else "R:R"
print(f"Take Profit: {best['tp_value']:.1f}x {tp_label}")
print(f"Session: {best['session']}")
print(f"Max Hold: {best['max_hold']:.0f} bars")
print()
print(f"Total Trades: {best['trades']:.0f}")
print(f"Total Return: {best['return']:+.2f}%")
print(f"Max Drawdown: {best['max_dd']:.2f}%")
print(f"Return/DD Ratio: {best['return_dd']:.2f}x")
print(f"Win Rate: {best['win_rate']:.1f}%")
print()
print("OUTLIER ANALYSIS:")
print(f"  Top 5 trades: {best['top5_pct']:.1f}% of profit")
print(f"  Without top 5: {best['without_top5']:+.2f}%")

if best['top5_pct'] > 80:
    print("  ⚠️  SEVERE outlier dependency (>80%)")
elif best['top5_pct'] > 60:
    print("  ⚠️  HIGH outlier dependency (>60%)")
elif best['top5_pct'] > 40:
    print("  ✅ MODERATE outlier dependency (<60%)")
else:
    print("  ✅ LOW outlier dependency (<40%)")

print()

# Save results
results_df.to_csv('trading/results/doge_bingx_comprehensive_optimization.csv', index=False)
print(f"✅ Full results saved to: trading/results/doge_bingx_comprehensive_optimization.csv")
print(f"   Total configs with 20+ trades: {len(results_df)}")
