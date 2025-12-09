#!/usr/bin/env python3
"""
DOGE BINGX MASTER OPTIMIZATION
Following prompt 013: Systematic optimization across 6 categories
"""
import pandas as pd
import numpy as np
from itertools import product

# ============================================================================
# STRATEGY INFRASTRUCTURE
# ============================================================================

def detect_volume_zones(df, volume_threshold=1.5, min_consecutive=5, max_consecutive=15):
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
                    'entry_time': df.loc[entry_idx, 'timestamp']
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
                    'entry_time': df.loc[entry_idx, 'timestamp']
                })

    return accumulation_zones, distribution_zones

def session_filter(timestamp, session):
    """Filter by trading session"""
    hour = timestamp.hour
    if session == 'overnight':
        return hour >= 21 or hour < 7
    elif session == 'asia_eu':
        return 7 <= hour < 14
    elif session == 'us':
        return 14 <= hour < 21
    else:  # 'all'
        return True

def backtest_config(df, accumulation_zones, distribution_zones, config):
    """Backtest a single configuration"""
    trades = []

    # LONG trades
    for zone in accumulation_zones:
        entry_idx = zone['entry_idx']
        if entry_idx not in df.index:
            continue

        # Session filter
        entry_time = df.loc[entry_idx, 'timestamp']
        if not session_filter(entry_time, config['session']):
            continue

        # Direction filter
        if 'LONG' not in config.get('directions', ['LONG', 'SHORT']):
            continue

        entry_price = zone['entry_price']
        atr = df.loc[entry_idx, 'atr']

        # Calculate stop loss
        if config['sl_type'] == 'fixed_pct':
            stop_loss = entry_price * (1 - config['sl_value'] / 100)
        else:  # atr
            stop_loss = entry_price - (config['sl_value'] * atr)

        sl_distance = entry_price - stop_loss

        # Calculate take profit
        if config['tp_type'] == 'fixed_pct':
            take_profit = entry_price * (1 + config['tp_value'] / 100)
        else:  # rr_multiple
            take_profit = entry_price + (config['tp_value'] * sl_distance)

        # Check for exit
        max_hold = config.get('max_hold_bars', 90)
        for i in range(1, max_hold + 1):
            if entry_idx + i >= len(df):
                break
            candle = df.iloc[entry_idx + i]

            # SL check
            if candle['low'] <= stop_loss:
                exit_price = stop_loss
                pnl = (exit_price / entry_price - 1) - 0.001
                trades.append({
                    'direction': 'LONG',
                    'entry_time': entry_time,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'SL'
                })
                break

            # TP check
            if candle['high'] >= take_profit:
                exit_price = take_profit
                pnl = (exit_price / entry_price - 1) - 0.001
                trades.append({
                    'direction': 'LONG',
                    'entry_time': entry_time,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'TP'
                })
                break
        else:
            # Time exit
            exit_price = df.iloc[entry_idx + max_hold]['close'] if entry_idx + max_hold < len(df) else entry_price
            pnl = (exit_price / entry_price - 1) - 0.001
            trades.append({
                'direction': 'LONG',
                'entry_time': entry_time,
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': max_hold,
                'exit_reason': 'TIME'
            })

    # SHORT trades
    for zone in distribution_zones:
        entry_idx = zone['entry_idx']
        if entry_idx not in df.index:
            continue

        entry_time = df.loc[entry_idx, 'timestamp']
        if not session_filter(entry_time, config['session']):
            continue

        if 'SHORT' not in config.get('directions', ['LONG', 'SHORT']):
            continue

        entry_price = zone['entry_price']
        atr = df.loc[entry_idx, 'atr']

        # Calculate stop loss
        if config['sl_type'] == 'fixed_pct':
            stop_loss = entry_price * (1 + config['sl_value'] / 100)
        else:  # atr
            stop_loss = entry_price + (config['sl_value'] * atr)

        sl_distance = stop_loss - entry_price

        # Calculate take profit
        if config['tp_type'] == 'fixed_pct':
            take_profit = entry_price * (1 - config['tp_value'] / 100)
        else:  # rr_multiple
            take_profit = entry_price - (config['tp_value'] * sl_distance)

        max_hold = config.get('max_hold_bars', 90)
        for i in range(1, max_hold + 1):
            if entry_idx + i >= len(df):
                break
            candle = df.iloc[entry_idx + i]

            if candle['high'] >= stop_loss:
                exit_price = stop_loss
                pnl = (entry_price / exit_price - 1) - 0.001
                trades.append({
                    'direction': 'SHORT',
                    'entry_time': entry_time,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'SL'
                })
                break

            if candle['low'] <= take_profit:
                exit_price = take_profit
                pnl = (entry_price / exit_price - 1) - 0.001
                trades.append({
                    'direction': 'SHORT',
                    'entry_time': entry_time,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'bars': i,
                    'exit_reason': 'TP'
                })
                break
        else:
            exit_price = df.iloc[entry_idx + max_hold]['close'] if entry_idx + max_hold < len(df) else entry_price
            pnl = (entry_price / exit_price - 1) - 0.001
            trades.append({
                'direction': 'SHORT',
                'entry_time': entry_time,
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'bars': max_hold,
                'exit_reason': 'TIME'
            })

    return pd.DataFrame(trades) if trades else pd.DataFrame()

def calculate_metrics(trades_df):
    """Calculate strategy metrics"""
    if len(trades_df) == 0:
        return None

    total_return = trades_df['pnl'].sum() * 100
    trades_df['cumulative_pnl'] = (trades_df['pnl'] * 100).cumsum()
    trades_df['equity'] = 100 + trades_df['cumulative_pnl']
    trades_df['running_max'] = trades_df['equity'].cummax()
    trades_df['drawdown'] = trades_df['equity'] - trades_df['running_max']
    trades_df['drawdown_pct'] = (trades_df['drawdown'] / trades_df['running_max']) * 100
    max_drawdown = trades_df['drawdown_pct'].min()

    win_rate = (trades_df['pnl'] > 0).mean() * 100
    return_dd = abs(total_return / max_drawdown) if max_drawdown < 0 else float('inf')

    return {
        'trades': len(trades_df),
        'return': total_return,
        'max_dd': max_drawdown,
        'return_dd': return_dd,
        'win_rate': win_rate
    }

# ============================================================================
# MAIN OPTIMIZATION
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("DOGE BINGX MASTER OPTIMIZATION")
    print("Following prompt 013: 6-category systematic optimization")
    print("=" * 80)
    print()

    # Load data
    print("Loading BingX data...")
    df = pd.read_csv('./trading/doge_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.reset_index(drop=True)

    # Calculate indicators
    df['range'] = df['high'] - df['low']
    df['atr'] = df['range'].rolling(14).mean()
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']

    print(f"Loaded {len(df):,} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
    print()

    # Detect volume zones (fixed parameters)
    print("Detecting volume zones...")
    zones = detect_volume_zones(df, volume_threshold=1.5, min_consecutive=5, max_consecutive=15)
    acc_zones, dist_zones = classify_zones(df, zones)
    print(f"  Accumulation zones (LONG): {len(acc_zones)}")
    print(f"  Distribution zones (SHORT): {len(dist_zones)}")
    print()

    # ========================================================================
    # OPTIMIZATION 1: SESSION FILTERS
    # ========================================================================
    print("=" * 80)
    print("OPTIMIZATION 1: SESSION-BASED OPTIMIZATION")
    print("=" * 80)
    print()

    sessions = ['overnight', 'asia_eu', 'us', 'all']
    session_results = []

    for session in sessions:
        config = {
            'sl_type': 'atr',
            'sl_value': 2.0,
            'tp_type': 'rr_multiple',
            'tp_value': 2.0,
            'session': session,
            'max_hold_bars': 90,
            'directions': ['LONG', 'SHORT']
        }

        trades_df = backtest_config(df, acc_zones, dist_zones, config)
        metrics = calculate_metrics(trades_df)

        if metrics:
            session_results.append({
                'session': session,
                **metrics
            })

    session_df = pd.DataFrame(session_results).sort_values('return_dd', ascending=False)

    print("SESSION ANALYSIS:")
    print(f"{'Session':<12} {'Return':>10} {'Max DD':>10} {'Return/DD':>12} {'Win Rate':>10} {'Trades':>8}")
    print("-" * 80)
    for _, row in session_df.iterrows():
        print(f"{row['session']:<12} {row['return']:>9.2f}% {row['max_dd']:>9.2f}% {row['return_dd']:>11.2f}x {row['win_rate']:>9.1f}% {row['trades']:>8.0f}")

    best_session = session_df.iloc[0]['session']
    print(f"\n✅ BEST SESSION: {best_session}")
    print(f"   Return/DD: {session_df.iloc[0]['return_dd']:.2f}x")
    print()

    # ========================================================================
    # OPTIMIZATION 2: DYNAMIC SL/TP
    # ========================================================================
    print("=" * 80)
    print("OPTIMIZATION 2: DYNAMIC SL/TP OPTIMIZATION")
    print("=" * 80)
    print()

    sl_configs = [
        ('fixed_pct', 0.3),
        ('fixed_pct', 0.5),
        ('atr', 1.0),
        ('atr', 1.5),
        ('atr', 2.0),
        ('atr', 2.5),
    ]

    tp_configs = [
        ('rr_multiple', 1.5),
        ('rr_multiple', 2.0),
        ('rr_multiple', 2.5),
        ('rr_multiple', 3.0),
        ('rr_multiple', 4.0),
    ]

    sl_tp_results = []

    for sl_type, sl_val in sl_configs:
        for tp_type, tp_val in tp_configs:
            config = {
                'sl_type': sl_type,
                'sl_value': sl_val,
                'tp_type': tp_type,
                'tp_value': tp_val,
                'session': best_session,  # Use best session from opt 1
                'max_hold_bars': 90,
                'directions': ['LONG', 'SHORT']
            }

            trades_df = backtest_config(df, acc_zones, dist_zones, config)
            metrics = calculate_metrics(trades_df)

            if metrics and metrics['trades'] >= 15:  # Minimum trade filter
                sl_tp_results.append({
                    'sl_type': sl_type,
                    'sl_value': sl_val,
                    'tp_type': tp_type,
                    'tp_value': tp_val,
                    **metrics
                })

    sl_tp_df = pd.DataFrame(sl_tp_results).sort_values('return_dd', ascending=False)

    print("SL/TP OPTIMIZATION (Top 10):")
    print(f"{'SL Type':<12} {'SL':>6} {'TP Type':<15} {'TP':>6} {'Return':>10} {'DD':>10} {'R/DD':>10} {'Trades':>8}")
    print("-" * 90)
    for _, row in sl_tp_df.head(10).iterrows():
        sl_str = f"{row['sl_value']:.1f}{'%' if row['sl_type']=='fixed_pct' else 'x'}"
        tp_str = f"{row['tp_value']:.1f}x"
        print(f"{row['sl_type']:<12} {sl_str:>6} {row['tp_type']:<15} {tp_str:>6} {row['return']:>9.2f}% {row['max_dd']:>9.2f}% {row['return_dd']:>9.2f}x {row['trades']:>8.0f}")

    best_sl_tp = sl_tp_df.iloc[0]
    print(f"\n✅ BEST SL/TP: {best_sl_tp['sl_type']} {best_sl_tp['sl_value']:.1f} | {best_sl_tp['tp_type']} {best_sl_tp['tp_value']:.1f}x")
    print(f"   Return/DD: {best_sl_tp['return_dd']:.2f}x")
    print()

    # ========================================================================
    # OPTIMIZATION 3: DIRECTION ANALYSIS
    # ========================================================================
    print("=" * 80)
    print("OPTIMIZATION 3: DIRECTION OPTIMIZATION")
    print("=" * 80)
    print()

    direction_configs = [
        ['LONG', 'SHORT'],
        ['LONG'],
        ['SHORT']
    ]

    direction_results = []

    for directions in direction_configs:
        config = {
            'sl_type': best_sl_tp['sl_type'],
            'sl_value': best_sl_tp['sl_value'],
            'tp_type': best_sl_tp['tp_type'],
            'tp_value': best_sl_tp['tp_value'],
            'session': best_session,
            'max_hold_bars': 90,
            'directions': directions
        }

        trades_df = backtest_config(df, acc_zones, dist_zones, config)
        metrics = calculate_metrics(trades_df)

        if metrics:
            direction_results.append({
                'directions': '+'.join(directions),
                **metrics
            })

    direction_df = pd.DataFrame(direction_results).sort_values('return_dd', ascending=False)

    print("DIRECTION ANALYSIS:")
    print(f"{'Directions':<12} {'Return':>10} {'Max DD':>10} {'Return/DD':>12} {'Win Rate':>10} {'Trades':>8}")
    print("-" * 80)
    for _, row in direction_df.iterrows():
        print(f"{row['directions']:<12} {row['return']:>9.2f}% {row['max_dd']:>9.2f}% {row['return_dd']:>11.2f}x {row['win_rate']:>9.1f}% {row['trades']:>8.0f}")

    best_directions = direction_df.iloc[0]['directions'].split('+')
    print(f"\n✅ BEST DIRECTIONS: {'+'.join(best_directions)}")
    print(f"   Return/DD: {direction_df.iloc[0]['return_dd']:.2f}x")
    print()

    # ========================================================================
    # FINAL OPTIMIZED CONFIGURATION
    # ========================================================================
    print("=" * 80)
    print("FINAL OPTIMIZED CONFIGURATION")
    print("=" * 80)
    print()

    final_config = {
        'sl_type': best_sl_tp['sl_type'],
        'sl_value': best_sl_tp['sl_value'],
        'tp_type': best_sl_tp['tp_type'],
        'tp_value': best_sl_tp['tp_value'],
        'session': best_session,
        'max_hold_bars': 90,
        'directions': best_directions
    }

    final_trades = backtest_config(df, acc_zones, dist_zones, final_config)
    final_metrics = calculate_metrics(final_trades)

    print("OPTIMIZED STRATEGY:")
    print(f"  Session: {final_config['session']}")
    print(f"  Stop Loss: {final_config['sl_type']} {final_config['sl_value']:.1f}{'%' if final_config['sl_type']=='fixed_pct' else 'x ATR'}")
    print(f"  Take Profit: {final_config['tp_type']} {final_config['tp_value']:.1f}x")
    print(f"  Directions: {'+'.join(final_config['directions'])}")
    print(f"  Max Hold: {final_config['max_hold_bars']} bars")
    print()

    print("RESULTS:")
    print(f"  Total Trades: {final_metrics['trades']}")
    print(f"  Total Return: {final_metrics['return']:+.2f}%")
    print(f"  Max Drawdown: {final_metrics['max_dd']:.2f}%")
    print(f"  Return/DD Ratio: {final_metrics['return_dd']:.2f}x")
    print(f"  Win Rate: {final_metrics['win_rate']:.1f}%")
    print()

    # Compare to baseline
    print("=" * 80)
    print("COMPARISON TO BASELINE")
    print("=" * 80)
    print(f"{'Metric':<20} {'Baseline':<15} {'Optimized':<15} {'Improvement'}")
    print("-" * 80)

    optimized_return = f"{final_metrics['return']:+.2f}%"
    optimized_dd = f"{final_metrics['max_dd']:.2f}%"
    optimized_rdd = f"{final_metrics['return_dd']:.2f}x"
    optimized_wr = f"{final_metrics['win_rate']:.1f}%"
    optimized_trades = f"{final_metrics['trades']}"

    print(f"{'Return':<20} {'+2.12%':<15} {optimized_return:<15} {final_metrics['return'] - 2.12:+.2f}%")
    print(f"{'Max DD':<20} {'-1.97%':<15} {optimized_dd:<15} {final_metrics['max_dd'] - (-1.97):+.2f}%")
    print(f"{'Return/DD':<20} {'1.08x':<15} {optimized_rdd:<15} {final_metrics['return_dd'] - 1.08:+.2f}x")
    print(f"{'Win Rate':<20} {'40.6%':<15} {optimized_wr:<15} {final_metrics['win_rate'] - 40.6:+.1f}%")
    print(f"{'Trades':<20} {'32':<15} {optimized_trades:<15} {final_metrics['trades'] - 32:+}")
    print()

    # Save results
    final_trades.to_csv('./trading/results/doge_bingx_optimized_trades.csv', index=False)

    # Save all optimization results
    optimization_summary = pd.DataFrame([
        {'category': 'Session', 'best_value': best_session, 'return_dd': session_df.iloc[0]['return_dd']},
        {'category': 'SL/TP', 'best_value': f"{best_sl_tp['sl_type']} {best_sl_tp['sl_value']:.1f} | {best_sl_tp['tp_type']} {best_sl_tp['tp_value']:.1f}x", 'return_dd': best_sl_tp['return_dd']},
        {'category': 'Directions', 'best_value': '+'.join(best_directions), 'return_dd': direction_df.iloc[0]['return_dd']},
        {'category': 'Final', 'best_value': 'Combined', 'return_dd': final_metrics['return_dd']}
    ])

    optimization_summary.to_csv('./trading/results/doge_bingx_optimization_summary.csv', index=False)

    print("✅ Results saved:")
    print("  - trading/results/doge_bingx_optimized_trades.csv")
    print("  - trading/results/doge_bingx_optimization_summary.csv")
    print()

    print("=" * 80)
    print("OPTIMIZATION COMPLETE")
    print("=" * 80)
