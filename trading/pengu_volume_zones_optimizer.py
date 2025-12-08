#!/usr/bin/env python3
"""
PENGU Volume Zone Strategy - Full Optimization

Optimize across all dimensions:
1. Trading sessions (Asian/EU/US)
2. SL/TP levels (ATR multipliers and R:R ratios)
3. Volume thresholds (1.3x, 1.5x, 2.0x)
4. Zone length filters (5+, 7+, 10+ bars)

Goal: Find the absolute best configuration
"""

import pandas as pd
import numpy as np
from itertools import product
import warnings
warnings.filterwarnings('ignore')

# Load PENGU data
print("Loading PENGU data...")
df = pd.read_csv('pengu_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hour'] = df['timestamp'].dt.hour

# Calculate indicators
df['range'] = df['high'] - df['low']
df['atr'] = df['range'].rolling(14).mean()
df['vol_ma'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma']

print(f"Total candles: {len(df)}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print()

# Define optimization grid
OPTIMIZATION_GRID = {
    'volume_threshold': [1.3, 1.5, 2.0],
    'min_zone_bars': [5, 7, 10],
    'sl_atr_mult': [0.5, 1.0, 1.5, 2.0],
    'rr_ratio': [2.0, 3.0, 4.0, 5.0, 7.0],
    'session': ['all', 'asian', 'eu', 'us', 'eu_us'],
}

# Session definitions (UTC)
SESSIONS = {
    'all': list(range(24)),
    'asian': list(range(0, 8)),      # 0-8 UTC
    'eu': list(range(8, 16)),         # 8-16 UTC
    'us': list(range(14, 22)),        # 14-22 UTC
    'eu_us': list(range(8, 22)),      # 8-22 UTC (overlap)
}

def detect_volume_zones(df, volume_threshold, min_bars, max_bars=15):
    """Detect volume zones with given threshold and min bars"""
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
                if zone_bars > max_bars:
                    if zone_bars >= min_bars:
                        zones.append({
                            'start': zone_start,
                            'end': i - 1,
                            'bars': zone_bars - 1
                        })
                    zone_start = i
                    zone_bars = 1
        else:
            if in_zone:
                if zone_bars >= min_bars:
                    zones.append({
                        'start': zone_start,
                        'end': i - 1,
                        'bars': zone_bars
                    })
                in_zone = False
                zone_start = None
                zone_bars = 0

    if in_zone and zone_bars >= min_bars:
        zones.append({
            'start': zone_start,
            'end': len(df) - 1,
            'bars': zone_bars
        })

    return zones

def classify_zones(df, zones):
    """Classify zones as accumulation or distribution"""
    accumulation = []
    distribution = []

    for zone in zones:
        start_idx = zone['start']
        end_idx = zone['end']

        if start_idx < 20 or end_idx >= len(df) - 30:
            continue

        zone_low = df.loc[start_idx:end_idx, 'low'].min()
        zone_high = df.loc[start_idx:end_idx, 'high'].max()

        lookback_start = max(0, start_idx - 20)
        lookahead_end = min(len(df), end_idx + 5)

        # Accumulation: zone at local low
        if zone_low == df.loc[lookback_start:lookahead_end, 'low'].min():
            entry_idx = end_idx + 1
            if entry_idx < len(df):
                accumulation.append({
                    'zone_start': start_idx,
                    'zone_end': end_idx,
                    'zone_bars': zone['bars'],
                    'zone_low': zone_low,
                    'entry_idx': entry_idx,
                    'entry_price': df.loc[entry_idx, 'close'],
                    'entry_hour': df.loc[entry_idx, 'hour']
                })

        # Distribution: zone at local high
        elif zone_high == df.loc[lookback_start:lookahead_end, 'high'].max():
            entry_idx = end_idx + 1
            if entry_idx < len(df):
                distribution.append({
                    'zone_start': start_idx,
                    'zone_end': end_idx,
                    'zone_bars': zone['bars'],
                    'zone_high': zone_high,
                    'entry_idx': entry_idx,
                    'entry_price': df.loc[entry_idx, 'close'],
                    'entry_hour': df.loc[entry_idx, 'hour']
                })

    return accumulation, distribution

def backtest_config(df, acc_zones, dist_zones, sl_atr_mult, rr_ratio, session_hours):
    """Backtest with given SL/TP config and session filter"""
    trades = []

    # LONG trades
    for zone in acc_zones:
        entry_idx = zone['entry_idx']
        entry_hour = zone['entry_hour']

        # Session filter
        if entry_hour not in session_hours:
            continue

        if entry_idx not in df.index or pd.isna(df.loc[entry_idx, 'atr']):
            continue

        entry_price = zone['entry_price']
        zone_low = zone['zone_low']
        atr = df.loc[entry_idx, 'atr']

        # Stop loss
        stop_loss = max(zone_low - (0.5 * atr), entry_price - (sl_atr_mult * atr))
        sl_distance = entry_price - stop_loss

        # Take profit
        take_profit = entry_price + (rr_ratio * sl_distance)

        # Check next 30 bars
        for i in range(1, 31):
            if entry_idx + i >= len(df):
                break
            candle = df.iloc[entry_idx + i]

            if candle['low'] <= stop_loss:
                pnl = (stop_loss / entry_price - 1) - 0.001
                trades.append({
                    'direction': 'LONG',
                    'pnl': pnl,
                    'bars': i,
                    'exit': 'SL',
                    'zone_bars': zone['zone_bars']
                })
                break
            elif candle['high'] >= take_profit:
                pnl = (take_profit / entry_price - 1) - 0.001
                trades.append({
                    'direction': 'LONG',
                    'pnl': pnl,
                    'bars': i,
                    'exit': 'TP',
                    'zone_bars': zone['zone_bars']
                })
                break
        else:
            exit_price = df.iloc[entry_idx + 30]['close'] if entry_idx + 30 < len(df) else entry_price
            pnl = (exit_price / entry_price - 1) - 0.001
            trades.append({
                'direction': 'LONG',
                'pnl': pnl,
                'bars': 30,
                'exit': 'TIME',
                'zone_bars': zone['zone_bars']
            })

    # SHORT trades
    for zone in dist_zones:
        entry_idx = zone['entry_idx']
        entry_hour = zone['entry_hour']

        if entry_hour not in session_hours:
            continue

        if entry_idx not in df.index or pd.isna(df.loc[entry_idx, 'atr']):
            continue

        entry_price = zone['entry_price']
        zone_high = zone['zone_high']
        atr = df.loc[entry_idx, 'atr']

        stop_loss = min(zone_high + (0.5 * atr), entry_price + (sl_atr_mult * atr))
        sl_distance = stop_loss - entry_price
        take_profit = entry_price - (rr_ratio * sl_distance)

        for i in range(1, 31):
            if entry_idx + i >= len(df):
                break
            candle = df.iloc[entry_idx + i]

            if candle['high'] >= stop_loss:
                pnl = (entry_price / stop_loss - 1) - 0.001
                trades.append({
                    'direction': 'SHORT',
                    'pnl': pnl,
                    'bars': i,
                    'exit': 'SL',
                    'zone_bars': zone['zone_bars']
                })
                break
            elif candle['low'] <= take_profit:
                pnl = (entry_price / take_profit - 1) - 0.001
                trades.append({
                    'direction': 'SHORT',
                    'pnl': pnl,
                    'bars': i,
                    'exit': 'TP',
                    'zone_bars': zone['zone_bars']
                })
                break
        else:
            exit_price = df.iloc[entry_idx + 30]['close'] if entry_idx + 30 < len(df) else entry_price
            pnl = (entry_price / exit_price - 1) - 0.001
            trades.append({
                'direction': 'SHORT',
                'pnl': pnl,
                'bars': 30,
                'exit': 'TIME',
                'zone_bars': zone['zone_bars']
            })

    return trades

# Run optimization
print("=" * 80)
print("RUNNING FULL OPTIMIZATION")
print("=" * 80)
print(f"Configurations to test: {np.prod([len(v) for v in OPTIMIZATION_GRID.values()])}")
print()

results = []
config_num = 0
total_configs = np.prod([len(v) for v in OPTIMIZATION_GRID.values()])

for vol_thresh, min_bars, sl_mult, rr, session in product(
    OPTIMIZATION_GRID['volume_threshold'],
    OPTIMIZATION_GRID['min_zone_bars'],
    OPTIMIZATION_GRID['sl_atr_mult'],
    OPTIMIZATION_GRID['rr_ratio'],
    OPTIMIZATION_GRID['session']
):
    config_num += 1
    if config_num % 50 == 0:
        print(f"Progress: {config_num}/{total_configs} ({config_num/total_configs*100:.1f}%)")

    # Detect and classify zones
    zones = detect_volume_zones(df, vol_thresh, min_bars)
    if len(zones) == 0:
        continue

    acc_zones, dist_zones = classify_zones(df, zones)
    if len(acc_zones) + len(dist_zones) < 10:  # Minimum trades filter
        continue

    # Backtest
    session_hours = SESSIONS[session]
    trades = backtest_config(df, acc_zones, dist_zones, sl_mult, rr, session_hours)

    if len(trades) < 10:  # Skip configs with <10 trades
        continue

    trades_df = pd.DataFrame(trades)
    total_return = trades_df['pnl'].sum() * 100
    avg_trade = trades_df['pnl'].mean() * 100
    win_rate = (trades_df['pnl'] > 0).mean() * 100

    avg_winner = trades_df[trades_df['pnl'] > 0]['pnl'].mean() * 100 if (trades_df['pnl'] > 0).any() else 0
    avg_loser = trades_df[trades_df['pnl'] < 0]['pnl'].mean() * 100 if (trades_df['pnl'] < 0).any() else 0
    actual_rr = abs(avg_winner / avg_loser) if avg_loser != 0 else 0

    tp_count = (trades_df['exit'] == 'TP').sum()
    sl_count = (trades_df['exit'] == 'SL').sum()

    results.append({
        'vol_threshold': vol_thresh,
        'min_zone_bars': min_bars,
        'sl_atr_mult': sl_mult,
        'rr_target': rr,
        'session': session,
        'total_trades': len(trades),
        'total_return': total_return,
        'avg_trade': avg_trade,
        'win_rate': win_rate,
        'actual_rr': actual_rr,
        'tp_count': tp_count,
        'sl_count': sl_count,
        'zones_found': len(zones),
        'acc_zones': len(acc_zones),
        'dist_zones': len(dist_zones)
    })

print()
print("=" * 80)
print("OPTIMIZATION COMPLETE")
print("=" * 80)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('total_return', ascending=False)

# Save all results
results_df.to_csv('results/PENGU_volume_zones_optimization.csv', index=False)
print(f"✅ All results saved: {len(results_df)} configurations tested")
print()

# Top 10 by total return
print("=" * 80)
print("TOP 10 CONFIGURATIONS BY TOTAL RETURN")
print("=" * 80)
top10 = results_df.head(10)
for idx, row in top10.iterrows():
    print(f"\n#{list(top10.index).index(idx) + 1}:")
    print(f"  Vol Threshold: {row['vol_threshold']:.1f}x")
    print(f"  Min Zone Bars: {row['min_zone_bars']}")
    print(f"  SL ATR Mult: {row['sl_atr_mult']:.1f}x")
    print(f"  R:R Target: {row['rr_target']:.1f}:1")
    print(f"  Session: {row['session']}")
    print(f"  Total Return: {row['total_return']:+.2f}%")
    print(f"  Trades: {row['total_trades']}")
    print(f"  Win Rate: {row['win_rate']:.1f}%")
    print(f"  Actual R:R: {row['actual_rr']:.2f}:1")
    print(f"  TP/SL: {row['tp_count']}/{row['sl_count']}")

print()
print("=" * 80)
print("BEST CONFIGURATION")
print("=" * 80)
best = results_df.iloc[0]
print(f"Configuration:")
print(f"  volume_threshold = {best['vol_threshold']:.1f}x")
print(f"  min_zone_bars = {best['min_zone_bars']}")
print(f"  sl_atr_mult = {best['sl_atr_mult']:.1f}x")
print(f"  rr_ratio = {best['rr_target']:.1f}:1")
print(f"  session = '{best['session']}'")
print()
print(f"Performance:")
print(f"  Total Return: {best['total_return']:+.2f}%")
print(f"  Total Trades: {best['total_trades']}")
print(f"  Win Rate: {best['win_rate']:.1f}%")
print(f"  Avg Trade: {best['avg_trade']:+.3f}%")
print(f"  Actual R:R: {best['actual_rr']:.2f}:1")
print(f"  TP Hits: {best['tp_count']} ({best['tp_count']/best['total_trades']*100:.1f}%)")

print()
print("=" * 80)
print("SESSION COMPARISON (Best config per session)")
print("=" * 80)
for session in ['all', 'asian', 'eu', 'us', 'eu_us']:
    session_results = results_df[results_df['session'] == session]
    if len(session_results) > 0:
        best_session = session_results.iloc[0]
        print(f"{session.upper()}: {best_session['total_return']:+.2f}% ({best_session['total_trades']} trades, {best_session['win_rate']:.1f}% WR)")
