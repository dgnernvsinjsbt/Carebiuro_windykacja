#!/usr/bin/env python3
"""
Backtest with Enhanced Filters V2
Goal: Achieve <30% max drawdown with best risk:reward
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from regime_filter_v2 import (
    prepare_dataframe_v2,
    should_trade_v2,
    classify_regime_v2,
    FILTER_CONFIGS_V2,
)


def backtest_with_enhanced_filter(df: pd.DataFrame, filter_level: str = 'balanced',
                                   sl_pct: float = 0.05, tp_pct: float = 0.075,
                                   fee_per_side: float = 0.00005) -> tuple:
    """
    Backtest with enhanced regime filters

    Args:
        df: OHLC DataFrame
        filter_level: 'none', 'aggressive', 'balanced', 'conservative'
        sl_pct: Stop loss (5% = 0.05)
        tp_pct: Take profit (7.5% = 0.075)
        fee_per_side: Fee per side (0.005% = 0.00005)

    Returns:
        (trades_df, final_equity, filter_stats)
    """
    df = df.copy()

    # Prepare all indicators
    df = prepare_dataframe_v2(df)

    # Generate signals
    df['signal'] = 0
    df.loc[(df['ema5'] < df['ema20']) & (df['ema5'].shift(1) >= df['ema20'].shift(1)), 'signal'] = -1

    # Backtest
    trades = []
    equity = 1.0
    max_equity = 1.0

    in_position = False
    entry_idx = 0

    # Filter tracking
    signals_generated = 0
    signals_filtered = 0
    filter_reasons = {}

    for i in range(200, len(df)):
        row = df.iloc[i]

        if not in_position:
            if row['signal'] == -1:
                signals_generated += 1

                # Apply enhanced filter
                if filter_level != 'none':
                    if not should_trade_v2(df, i, filter_level):
                        signals_filtered += 1

                        # Track filter reason
                        regime = classify_regime_v2(df, i)
                        reason = regime['reason']
                        filter_reasons[reason] = filter_reasons.get(reason, 0) + 1

                        continue

                # Enter short
                regime = classify_regime_v2(df, i)

                in_position = True
                entry_idx = i
                entry_price = row['close']
                entry_time = row['timestamp'] if 'timestamp' in row else None
                stop_loss = entry_price * (1 + sl_pct)
                take_profit = entry_price * (1 - tp_pct)

                entry_regime = regime

        else:
            exit_price = None
            exit_reason = None

            if row['high'] >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
            elif row['low'] <= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'

            if exit_price:
                pnl_pct = (entry_price - exit_price) / entry_price
                net_pnl = pnl_pct - (fee_per_side * 2)

                equity *= (1 + net_pnl)
                max_equity = max(max_equity, equity)
                dd = (max_equity - equity) / max_equity * 100

                trades.append({
                    'entry_time': entry_time,
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': net_pnl * 100,
                    'winner': net_pnl > 0,
                    'exit_reason': exit_reason,
                    'equity': equity,
                    'drawdown': dd,
                    'bars_held': i - entry_idx,
                    'regime': entry_regime['regime'],
                    'regime_confidence': entry_regime['confidence'],
                })

                in_position = False

    filter_stats = {
        'signals_generated': signals_generated,
        'signals_filtered': signals_filtered,
        'filter_rate': signals_filtered / signals_generated * 100 if signals_generated > 0 else 0,
        'filter_reasons': filter_reasons,
    }

    return pd.DataFrame(trades), equity, filter_stats


def compare_enhanced_filters():
    """Compare all enhanced filter levels"""

    print("=" * 80)
    print("FARTCOIN ENHANCED FILTER BACKTEST")
    print("Strategy: EMA 5/20 Cross Down Short")
    print("Config: SL 5%, TP 7.5% (1.5:1 R:R), 0.01% fees")
    print("Goal: <30% Max Drawdown with Best Risk:Reward")
    print("=" * 80)

    # Load data
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv')

    print(f"\nData Range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    print(f"Total Bars: {len(df)}")
    print(f"Price Change: {(df['close'].iloc[-1] / df['close'].iloc[200] - 1) * 100:+.1f}%")

    # Test all filter levels
    results = []

    print("\n" + "=" * 80)
    print("FILTER COMPARISON")
    print("=" * 80)

    for filter_level in ['none', 'aggressive', 'balanced', 'conservative']:
        print(f"\nTesting {filter_level.upper()} filter...")

        trades_df, equity, filter_stats = backtest_with_enhanced_filter(df, filter_level)

        if len(trades_df) > 0:
            total_return = (equity - 1) * 100
            win_rate = trades_df['winner'].mean() * 100
            max_dd = trades_df['drawdown'].max()
            risk_reward = total_return / max_dd if max_dd > 0 else 0

            results.append({
                'filter': filter_level,
                'name': FILTER_CONFIGS_V2[filter_level]['name'],
                'trades': len(trades_df),
                'signals_filtered': filter_stats['signals_filtered'],
                'filter_rate': filter_stats['filter_rate'],
                'win_rate': win_rate,
                'return': total_return,
                'max_dd': max_dd,
                'risk_reward': risk_reward,
                'avg_trade': trades_df['pnl_pct'].mean(),
                'target_dd': FILTER_CONFIGS_V2[filter_level]['target_dd'],
                'filter_reasons': filter_stats['filter_reasons'],
            })

    # Display results
    print("\n" + "=" * 80)
    print(f"{'Filter':<20} {'Trades':<8} {'Filtered':<12} {'Win%':<8} {'Return':<12} {'MaxDD':<10} {'R:R':<8} {'Target':<10}")
    print("=" * 80)

    for r in results:
        filtered_str = f"{r['signals_filtered']} ({r['filter_rate']:.0f}%)" if r['filter_rate'] > 0 else "0"
        dd_status = "✅" if r['max_dd'] <= 30 else "⚠️" if r['max_dd'] <= 40 else "❌"

        print(f"{r['name']:<20} {r['trades']:<8} {filtered_str:<12} {r['win_rate']:<7.1f}% "
              f"{r['return']:<+11.2f}% {dd_status} {r['max_dd']:<8.1f}% {r['risk_reward']:<7.2f}x {r['target_dd']:<10}")

    # Detailed analysis of best filter
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS")
    print("=" * 80)

    # Find filter closest to <30% DD target
    target_filter = None
    for r in results:
        if r['filter'] == 'balanced':
            target_filter = r
            break

    if target_filter:
        print(f"\n{target_filter['name']} (TARGET: <30% DD):")
        print(f"  Total Return: {target_filter['return']:+.2f}%")
        print(f"  Max Drawdown: {target_filter['max_dd']:.2f}%")
        print(f"  Risk:Reward: {target_filter['risk_reward']:.2f}x")
        print(f"  Total Trades: {target_filter['trades']}")
        print(f"  Win Rate: {target_filter['win_rate']:.1f}%")
        print(f"  Signals Filtered: {target_filter['signals_filtered']} ({target_filter['filter_rate']:.0f}%)")

        print(f"\n  Filter Reasons (why trades were skipped):")
        for reason, count in sorted(target_filter['filter_reasons'].items(), key=lambda x: x[1], reverse=True):
            print(f"    • {reason}: {count} times")

        # Compare to baseline
        baseline = next((r for r in results if r['filter'] == 'none'), None)
        if baseline:
            print(f"\n  vs Baseline (No Filter):")
            print(f"    Return: {target_filter['return']:+.2f}% vs {baseline['return']:+.2f}% ({target_filter['return']-baseline['return']:+.2f}%)")
            print(f"    Max DD: {target_filter['max_dd']:.1f}% vs {baseline['max_dd']:.1f}% ({target_filter['max_dd']-baseline['max_dd']:+.1f}%)")
            print(f"    R:R: {target_filter['risk_reward']:.2f}x vs {baseline['risk_reward']:.2f}x ({target_filter['risk_reward']-baseline['risk_reward']:+.2f}x)")
            print(f"    Trades: {target_filter['trades']} vs {baseline['trades']} ({target_filter['trades']-baseline['trades']})")

    # Leverage recommendations
    print("\n" + "=" * 80)
    print("LEVERAGE RECOMMENDATIONS")
    print("=" * 80)

    for r in results:
        if r['filter'] in ['balanced', 'conservative']:
            print(f"\n{r['name']} (DD: {r['max_dd']:.1f}%):")

            if r['max_dd'] <= 30:
                safe_lev = 100 / (r['max_dd'] * 2)
                agg_lev = 100 / (r['max_dd'] * 1.5)
                print(f"  ✅ Safe leverage (2x buffer): {safe_lev:.1f}x")
                print(f"  ⚡ Aggressive leverage (1.5x buffer): {agg_lev:.1f}x")

                for lev in [2, 3, 5]:
                    lev_return = r['return'] * lev
                    lev_dd = r['max_dd'] * lev
                    status = "✅" if lev_dd < 50 else "⚠️" if lev_dd < 80 else "❌"
                    print(f"    {status} {lev}x: {lev_return:+.0f}% return, {lev_dd:.1f}% DD")
            else:
                print(f"  ❌ DD too high for safe leverage")

    # Save results
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)

    for r in results:
        filter_level = r['filter']
        trades_df, _, _ = backtest_with_enhanced_filter(df, filter_level)

        output_path = Path(f'/workspaces/Carebiuro_windykacja/trading/results/fartcoin_enhanced_{filter_level}.csv')
        trades_df.to_csv(output_path, index=False)
        print(f"✅ {r['name']}: {output_path}")

    # Summary recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    best = None
    for r in results:
        if r['max_dd'] <= 30:
            if best is None or r['risk_reward'] > best['risk_reward']:
                best = r

    if best:
        print(f"\n🎯 RECOMMENDED: {best['name']}")
        print(f"   Return: {best['return']:+.1f}%")
        print(f"   Max DD: {best['max_dd']:.1f}% ✅")
        print(f"   Risk:Reward: {best['risk_reward']:.2f}x")
        print(f"   Safe leverage: {100/(best['max_dd']*2):.1f}x")
    else:
        print("\n⚠️  No filter achieved <30% DD target")
        print("   Consider using Conservative filter for maximum safety")

    return pd.DataFrame(results)


if __name__ == '__main__':
    results_df = compare_enhanced_filters()
