#!/usr/bin/env python3
"""
TRUMP Volume Zones - ADAPTIVE OPTIMIZER for BingX Data

Key Changes:
1. Test multiple volume thresholds (1.2x, 1.3x, 1.4x, 1.5x)
2. Test multiple min_consecutive bars (3, 4, 5)
3. Compare against MEXC results
4. Focus on finding tradeable setups even if fewer than MEXC
"""

import pandas as pd
import numpy as np
from itertools import product
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

def get_session(hour):
    """Classify UTC hour into trading session"""
    if 0 <= hour < 7 or hour >= 21:
        return 'overnight'
    elif 7 <= hour < 14:
        return 'asia_eu'
    elif 14 <= hour < 21:
        return 'us'

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
    """Classify zones as accumulation (lows) or distribution (highs)"""
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
                    'atr': df.loc[entry_idx, 'atr']
                })

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
                    'atr': df.loc[entry_idx, 'atr']
                })

    return accumulation_zones, distribution_zones

def backtest_strategy(df, acc_zones, dist_zones, config):
    """Backtest with configurable parameters"""
    trades = []

    session_filter = config.get('session_filter', None)
    trade_longs = config.get('trade_longs', True)
    trade_shorts = config.get('trade_shorts', True)
    max_hold = config.get('max_hold_bars', 90)
    use_limit_orders = config.get('use_limit_orders', False)
    limit_offset_pct = config.get('limit_offset_pct', 0.035)

    # LONG trades
    if trade_longs:
        for zone in acc_zones:
            entry_idx = zone['entry_idx']

            if session_filter and zone['entry_session'] != session_filter:
                continue

            if entry_idx not in df.index or pd.isna(zone['atr']):
                continue

            entry_price = zone['entry_price']

            # Limit order adjustment
            if use_limit_orders:
                entry_price = entry_price * (1 - limit_offset_pct / 100)

            zone_low = zone['zone_low']
            atr = zone['atr']

            # Calculate stop loss
            if config['sl_type'] == 'atr':
                sl_distance = config['sl_value'] * atr
                stop_loss = entry_price - sl_distance
            elif config['sl_type'] == 'fixed_pct':
                sl_distance = entry_price * (config['sl_value'] / 100)
                stop_loss = entry_price - sl_distance

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
                    fee = 0.0007 if use_limit_orders else 0.001
                    pnl = (stop_loss / entry_price - 1) - fee
                    trades.append({
                        'direction': 'LONG',
                        'pnl': pnl,
                        'bars': i,
                        'exit_reason': 'SL',
                        'zone_bars': zone['zone_bars'],
                        'session': zone['entry_session'],
                        'entry_idx': entry_idx
                    })
                    break

                if candle['high'] >= take_profit:
                    fee = 0.0007 if use_limit_orders else 0.001
                    pnl = (take_profit / entry_price - 1) - fee
                    trades.append({
                        'direction': 'LONG',
                        'pnl': pnl,
                        'bars': i,
                        'exit_reason': 'TP',
                        'zone_bars': zone['zone_bars'],
                        'session': zone['entry_session'],
                        'entry_idx': entry_idx
                    })
                    break
            else:
                exit_price = df.iloc[entry_idx + max_hold]['close'] if entry_idx + max_hold < len(df) else entry_price
                fee = 0.0007 if use_limit_orders else 0.001
                pnl = (exit_price / entry_price - 1) - fee
                trades.append({
                    'direction': 'LONG',
                    'pnl': pnl,
                    'bars': max_hold,
                    'exit_reason': 'TIME',
                    'zone_bars': zone['zone_bars'],
                    'session': zone['entry_session'],
                    'entry_idx': entry_idx
                })

    # SHORT trades
    if trade_shorts:
        for zone in dist_zones:
            entry_idx = zone['entry_idx']

            if session_filter and zone['entry_session'] != session_filter:
                continue

            if entry_idx not in df.index or pd.isna(zone['atr']):
                continue

            entry_price = zone['entry_price']

            # Limit order adjustment
            if use_limit_orders:
                entry_price = entry_price * (1 + limit_offset_pct / 100)

            zone_high = zone['zone_high']
            atr = zone['atr']

            # Calculate stop loss
            if config['sl_type'] == 'atr':
                sl_distance = config['sl_value'] * atr
                stop_loss = entry_price + sl_distance
            elif config['sl_type'] == 'fixed_pct':
                sl_distance = entry_price * (config['sl_value'] / 100)
                stop_loss = entry_price + sl_distance

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
                    fee = 0.0007 if use_limit_orders else 0.001
                    pnl = (entry_price / stop_loss - 1) - fee
                    trades.append({
                        'direction': 'SHORT',
                        'pnl': pnl,
                        'bars': i,
                        'exit_reason': 'SL',
                        'zone_bars': zone['zone_bars'],
                        'session': zone['entry_session'],
                        'entry_idx': entry_idx
                    })
                    break

                if candle['low'] <= take_profit:
                    fee = 0.0007 if use_limit_orders else 0.001
                    pnl = (entry_price / take_profit - 1) - fee
                    trades.append({
                        'direction': 'SHORT',
                        'pnl': pnl,
                        'bars': i,
                        'exit_reason': 'TP',
                        'zone_bars': zone['zone_bars'],
                        'session': zone['entry_session'],
                        'entry_idx': entry_idx
                    })
                    break
            else:
                exit_price = df.iloc[entry_idx + max_hold]['close'] if entry_idx + max_hold < len(df) else entry_price
                fee = 0.0007 if use_limit_orders else 0.001
                pnl = (entry_price / exit_price - 1) - fee
                trades.append({
                    'direction': 'SHORT',
                    'pnl': pnl,
                    'bars': max_hold,
                    'exit_reason': 'TIME',
                    'zone_bars': zone['zone_bars'],
                    'session': zone['entry_session'],
                    'entry_idx': entry_idx
                })

    return trades

def calculate_metrics(trades_df):
    """Calculate performance metrics"""
    if len(trades_df) == 0:
        return None

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

    # Skip impossible configs
    if max_dd >= -0.01:
        return None

    return_dd_ratio = abs(total_return / max_dd)

    # Outlier analysis
    sorted_trades = trades_df.sort_values('pnl', ascending=False)
    top_20_pct = int(len(sorted_trades) * 0.2)
    if top_20_pct == 0:
        top_20_pct = 1
    top_20_contribution = sorted_trades.head(top_20_pct)['pnl'].sum() / sorted_trades['pnl'].sum() * 100

    return {
        'trades': len(trades_df),
        'return': total_return,
        'win_rate': win_rate,
        'avg_winner': avg_winner,
        'avg_loser': avg_loser,
        'profit_factor': profit_factor,
        'max_dd': max_dd,
        'return_dd_ratio': return_dd_ratio,
        'top_20_concentration': top_20_contribution,
        'avg_bars': trades_df['bars'].mean()
    }

def main():
    print("\n" + "="*80)
    print("TRUMP VOLUME ZONES - ADAPTIVE OPTIMIZER (BingX Data)")
    print("="*80)

    # Load BingX data
    print("\nLoading TRUMP BingX data...")
    df = pd.read_csv('trumpsol_30d_bingx.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour

    # Calculate indicators
    df['range'] = df['high'] - df['low']
    df['atr'] = df['range'].rolling(14).mean()
    df['atr_pct'] = (df['atr'] / df['close']) * 100
    df['body'] = df['close'] - df['open']
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    df['session'] = df['hour'].apply(get_session)

    print(f"Loaded {len(df):,} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Test different zone detection parameters
    print("\n" + "="*80)
    print("PHASE 1: ADAPTIVE ZONE DETECTION")
    print("="*80)

    zone_configs = []
    for vol_thresh in [1.2, 1.3, 1.4, 1.5]:
        for min_bars in [3, 4, 5]:
            zones = detect_volume_zones(df, volume_threshold=vol_thresh, min_consecutive=min_bars)
            acc_zones, dist_zones = classify_zones(df, zones)

            print(f"\nThreshold: {vol_thresh}x | Min Bars: {min_bars}")
            print(f"  Total Zones: {len(zones)}")
            print(f"  Accumulation: {len(acc_zones)}")
            print(f"  Distribution: {len(dist_zones)}")

            if len(acc_zones) + len(dist_zones) >= 10:
                zone_configs.append({
                    'vol_threshold': vol_thresh,
                    'min_consecutive': min_bars,
                    'zones': zones,
                    'acc_zones': acc_zones,
                    'dist_zones': dist_zones
                })

    if len(zone_configs) == 0:
        print("\n❌ ERROR: No zone configurations generated enough signals (need 10+ zones)")
        print("   BingX data has very different volume patterns than MEXC")
        return

    print(f"\n✅ {len(zone_configs)} zone configurations passed minimum signal filter")

    # ==================== OPTIMIZATION GRID ====================

    print("\n" + "="*80)
    print("PHASE 2: COMPREHENSIVE OPTIMIZATION")
    print("="*80)

    results = []

    # Simplified test grid
    sl_configs = [
        {'sl_type': 'fixed_pct', 'sl_value': 0.3},
        {'sl_type': 'fixed_pct', 'sl_value': 0.5},  # MEXC baseline
        {'sl_type': 'fixed_pct', 'sl_value': 0.75},
        {'sl_type': 'atr', 'sl_value': 1.0},
        {'sl_type': 'atr', 'sl_value': 1.5},
    ]

    tp_configs = [
        {'tp_type': 'rr_multiple', 'tp_value': 2.0},
        {'tp_type': 'rr_multiple', 'tp_value': 3.0},
        {'tp_type': 'rr_multiple', 'tp_value': 4.0},  # MEXC baseline
        {'tp_type': 'rr_multiple', 'tp_value': 5.0},
    ]

    session_configs = ['overnight', 'us', 'asia_eu', None]
    direction_configs = [
        {'trade_longs': True, 'trade_shorts': True},
        {'trade_longs': True, 'trade_shorts': False},
        {'trade_longs': False, 'trade_shorts': True},
    ]
    max_hold_configs = [60, 90, 120]
    limit_order_configs = [
        {'use_limit_orders': False},
        {'use_limit_orders': True, 'limit_offset_pct': 0.035},
    ]

    total_configs = (len(zone_configs) * len(sl_configs) * len(tp_configs) *
                    len(session_configs) * len(direction_configs) *
                    len(max_hold_configs) * len(limit_order_configs))

    print(f"\nTesting {total_configs:,} configurations...")
    print("This will take a few minutes...\n")

    tested = 0
    for zone_cfg in zone_configs:
        acc_zones = zone_cfg['acc_zones']
        dist_zones = zone_cfg['dist_zones']

        for sl_cfg, tp_cfg, session, dir_cfg, max_hold, limit_cfg in product(
            sl_configs, tp_configs, session_configs, direction_configs,
            max_hold_configs, limit_order_configs
        ):
            config = {
                **sl_cfg,
                **tp_cfg,
                'session_filter': session,
                **dir_cfg,
                'max_hold_bars': max_hold,
                **limit_cfg,
                'zone_vol_threshold': zone_cfg['vol_threshold'],
                'zone_min_bars': zone_cfg['min_consecutive']
            }

            trades = backtest_strategy(df, acc_zones, dist_zones, config)

            if len(trades) < 10:
                continue

            trades_df = pd.DataFrame(trades)
            metrics = calculate_metrics(trades_df)

            if metrics is None:
                continue

            results.append({
                'config': config,
                **metrics,
                'trades_df': trades_df
            })

            tested += 1
            if tested % 200 == 0:
                print(f"  Tested {tested:,}/{total_configs:,} configs ({tested/total_configs*100:.1f}%) | Valid: {len(results)}")

    print(f"\n✅ Generated {len(results):,} valid configurations\n")

    if len(results) == 0:
        print("❌ ERROR: No valid configurations found")
        print("   This suggests TRUMP/BingX data is fundamentally different from MEXC")
        return

    # Sort by Return/DD ratio
    results = sorted(results, key=lambda x: x['return_dd_ratio'], reverse=True)

    # ==================== RESULTS ====================

    print("\n" + "="*80)
    print("TOP 20 CONFIGURATIONS BY RETURN/DD RATIO")
    print("="*80)
    print(f"{'Rank':<5} {'R/DD':<7} {'Ret%':<7} {'DD%':<7} {'SL':<10} {'TP':<10} "
          f"{'Sess':<9} {'Dir':<6} {'Hold':<5} {'Lim':<4} {'Zone':<8} {'#T':<4} {'WR%':<5} {'Top20':<6}")
    print("-" * 125)

    for i, r in enumerate(results[:20], 1):
        cfg = r['config']
        direction = 'BOTH' if cfg['trade_longs'] and cfg['trade_shorts'] else ('LONG' if cfg['trade_longs'] else 'SHORT')
        session_str = cfg['session_filter'] or 'ALL'
        sl_str = f"{cfg['sl_type'][:3]}:{cfg['sl_value']:.1f}"
        tp_str = f"{cfg['tp_type'][:2]}:{cfg['tp_value']:.1f}"
        limit_str = 'YES' if cfg['use_limit_orders'] else 'NO'
        zone_str = f"{cfg['zone_vol_threshold']}x/{cfg['zone_min_bars']}b"

        print(f"{i:<5} {r['return_dd_ratio']:<7.2f} {r['return']:<7.2f} {r['max_dd']:<7.2f} "
              f"{sl_str:<10} {tp_str:<10} {session_str:<9} {direction:<6} "
              f"{cfg['max_hold_bars']:<5} {limit_str:<4} {zone_str:<8} "
              f"{r['trades']:<4} {r['win_rate']:<5.1f} {r['top_20_concentration']:<6.1f}")

    # Best config details
    best = results[0]
    print("\n" + "="*80)
    print("BEST OPTIMIZED CONFIGURATION")
    print("="*80)
    print(f"Return/DD Ratio: {best['return_dd_ratio']:.2f}x")
    print(f"Total Return: {best['return']:+.2f}%")
    print(f"Max Drawdown: {best['max_dd']:.2f}%")
    print()
    print(f"Zone Detection: {best['config']['zone_vol_threshold']}x volume, {best['config']['zone_min_bars']}+ bars")
    print(f"Stop Loss: {best['config']['sl_type']} @ {best['config']['sl_value']}")
    print(f"Take Profit: {best['config']['tp_type']} @ {best['config']['tp_value']}")
    print(f"Session Filter: {best['config']['session_filter'] or 'ALL'}")
    print(f"Direction: {'BOTH' if best['config']['trade_longs'] and best['config']['trade_shorts'] else ('LONG ONLY' if best['config']['trade_longs'] else 'SHORT ONLY')}")
    print(f"Max Hold: {best['config']['max_hold_bars']} bars")
    print(f"Limit Orders: {'YES' if best['config']['use_limit_orders'] else 'NO'}")
    print()
    print(f"Trades: {best['trades']}")
    print(f"Win Rate: {best['win_rate']:.1f}%")
    print(f"Avg Winner: {best['avg_winner']:+.2f}%")
    print(f"Avg Loser: {best['avg_loser']:+.2f}%")
    print(f"Profit Factor: {best['profit_factor']:.2f}")
    print(f"Top 20% Concentration: {best['top_20_concentration']:.1f}%")
    print(f"Avg Hold Time: {best['avg_bars']:.1f} bars")

    # Save results
    best['trades_df'].to_csv('results/TRUMP_bingx_optimized_trades.csv', index=False)

    # Comparison table
    comparison_df = pd.DataFrame([
        {
            'Version': 'MEXC Original',
            'Return': 8.06,
            'Max DD': -0.76,
            'Return/DD': 10.56,
            'Win Rate': 61.9,
            'Trades': 21,
            'Top 20%': 88.6,
            'Zone Config': '1.5x/5b'
        },
        {
            'Version': 'BingX Optimized',
            'Return': best['return'],
            'Max DD': best['max_dd'],
            'Return/DD': best['return_dd_ratio'],
            'Win Rate': best['win_rate'],
            'Trades': best['trades'],
            'Top 20%': best['top_20_concentration'],
            'Zone Config': f"{best['config']['zone_vol_threshold']}x/{best['config']['zone_min_bars']}b"
        }
    ])
    comparison_df.to_csv('results/TRUMP_optimization_comparison.csv', index=False)

    print("\n" + "="*80)
    print("COMPARISON: MEXC vs BingX Optimized")
    print("="*80)
    print(comparison_df.to_string(index=False))

    print("\n" + "="*80)
    print("FILES SAVED")
    print("="*80)
    print("✅ results/TRUMP_bingx_optimized_trades.csv")
    print("✅ results/TRUMP_optimization_comparison.csv")

    # Generate equity curve
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))

    best_equity = (best['trades_df']['pnl'] * 100).cumsum()
    ax.plot(best_equity.values, label=f'BingX Optimized (R/DD: {best["return_dd_ratio"]:.2f}x)',
            color='green', linewidth=2, alpha=0.8)
    ax.fill_between(range(len(best_equity)), 0, best_equity.values, color='green', alpha=0.1)
    ax.set_title('TRUMP Volume Zones - Optimized Strategy on BingX', fontsize=14, fontweight='bold')
    ax.set_xlabel('Trade Number')
    ax.set_ylabel('Cumulative Return (%)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)

    plt.tight_layout()
    plt.savefig('results/TRUMP_optimized_equity.png', dpi=150, bbox_inches='tight')
    print("✅ results/TRUMP_optimized_equity.png")

    return best

if __name__ == '__main__':
    result = main()
