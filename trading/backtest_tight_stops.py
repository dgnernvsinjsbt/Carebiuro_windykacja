#!/usr/bin/env python3
"""
Test tighter stop losses to achieve <30% drawdown
Try multiple SL/TP combinations with enhanced filters
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from regime_filter_v2 import prepare_dataframe_v2, should_trade_v2


def backtest_with_tight_stops(df: pd.DataFrame, filter_level: str, sl_pct: float, tp_multiplier: float = 1.5):
    """Backtest with configurable stops"""

    df = df.copy()
    df = prepare_dataframe_v2(df)

    # Signal
    df['signal'] = 0
    df.loc[(df['ema5'] < df['ema20']) & (df['ema5'].shift(1) >= df['ema20'].shift(1)), 'signal'] = -1

    trades = []
    equity = 1.0
    max_equity = 1.0

    in_position = False
    entry_idx = 0
    fee = 0.00005

    tp_pct = sl_pct * tp_multiplier

    for i in range(200, len(df)):
        row = df.iloc[i]

        if not in_position:
            if row['signal'] == -1:
                if filter_level != 'none' and not should_trade_v2(df, i, filter_level):
                    continue

                in_position = True
                entry_idx = i
                entry_price = row['close']
                entry_time = row['timestamp'] if 'timestamp' in row else None
                stop_loss = entry_price * (1 + sl_pct)
                take_profit = entry_price * (1 - tp_pct)

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
                net_pnl = pnl_pct - (fee * 2)

                equity *= (1 + net_pnl)
                max_equity = max(max_equity, equity)
                dd = (max_equity - equity) / max_equity * 100

                trades.append({
                    'entry_time': entry_time,
                    'pnl_pct': net_pnl * 100,
                    'winner': net_pnl > 0,
                    'exit_reason': exit_reason,
                    'equity': equity,
                    'drawdown': dd,
                })

                in_position = False

    return pd.DataFrame(trades), equity


def test_configurations():
    """Test multiple SL/TP and filter combinations"""

    print("=" * 90)
    print("FARTCOIN: TESTING TIGHTER STOPS FOR <30% DRAWDOWN")
    print("=" * 90)

    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv')

    print(f"\nData: {len(df)} bars, {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")

    # Test configurations
    configs = []

    # SL levels to test: 2%, 2.5%, 3%, 3.5%, 4%, 5%
    sl_levels = [0.02, 0.025, 0.03, 0.035, 0.04, 0.05]

    # Filter levels
    filters = ['balanced', 'conservative']

    print("\n" + "=" * 90)
    print("TESTING CONFIGURATIONS")
    print("=" * 90)

    for filter_level in filters:
        for sl in sl_levels:
            tp = sl * 1.5  # Maintain 1.5:1 R:R

            trades_df, equity = backtest_with_tight_stops(df, filter_level, sl)

            if len(trades_df) > 0:
                total_return = (equity - 1) * 100
                max_dd = trades_df['drawdown'].max()
                win_rate = trades_df['winner'].mean() * 100
                risk_reward = total_return / max_dd if max_dd > 0 else 0

                configs.append({
                    'filter': filter_level,
                    'sl_pct': sl * 100,
                    'tp_pct': tp * 100,
                    'rr_ratio': tp / sl,
                    'trades': len(trades_df),
                    'win_rate': win_rate,
                    'return': total_return,
                    'max_dd': max_dd,
                    'risk_reward': risk_reward,
                    'dd_target_met': max_dd <= 30,
                })

    # Sort by risk:reward for configs that meet DD target
    configs_df = pd.DataFrame(configs)

    # Display all configs
    print(f"\n{'Filter':<14} {'SL%':<6} {'TP%':<6} {'R:R':<6} {'Trades':<8} {'Win%':<7} {'Return':<11} {'MaxDD':<9} {'Risk:Rew':<9} {'<30% DD?'}")
    print("=" * 90)

    for _, row in configs_df.iterrows():
        dd_status = "✅" if row['dd_target_met'] else "❌"
        print(f"{row['filter']:<14} {row['sl_pct']:<6.1f} {row['tp_pct']:<6.1f} {row['rr_ratio']:<6.1f} "
              f"{row['trades']:<8} {row['win_rate']:<6.1f}% {row['return']:<+10.2f}% {row['max_dd']:<8.1f}% "
              f"{row['risk_reward']:<8.2f}x {dd_status}")

    # Find best configs that meet DD target
    print("\n" + "=" * 90)
    print("CONFIGS MEETING <30% DD TARGET")
    print("=" * 90)

    target_met = configs_df[configs_df['dd_target_met'] == True].sort_values('risk_reward', ascending=False)

    if len(target_met) > 0:
        print(f"\n✅ Found {len(target_met)} configurations with <30% DD:")
        print()
        print(f"{'Filter':<14} {'SL%':<6} {'TP%':<6} {'Trades':<8} {'Return':<11} {'MaxDD':<9} {'R:R':<9}")
        print("-" * 70)

        for _, row in target_met.iterrows():
            print(f"{row['filter']:<14} {row['sl_pct']:<6.1f} {row['tp_pct']:<6.1f} {row['trades']:<8} "
                  f"{row['return']:<+10.2f}% {row['max_dd']:<8.1f}% {row['risk_reward']:<8.2f}x")

        # Best config
        best = target_met.iloc[0]

        print("\n" + "=" * 90)
        print("🎯 BEST CONFIGURATION (Highest R:R with <30% DD)")
        print("=" * 90)

        print(f"\nFilter: {best['filter'].upper()}")
        print(f"Stop Loss: {best['sl_pct']:.1f}%")
        print(f"Take Profit: {best['tp_pct']:.1f}%")
        print(f"Risk:Reward Ratio: {best['rr_ratio']:.1f}:1")
        print(f"\nResults:")
        print(f"  Total Return: {best['return']:+.2f}%")
        print(f"  Max Drawdown: {best['max_dd']:.2f}% ✅")
        print(f"  Risk:Reward: {best['risk_reward']:.2f}x")
        print(f"  Total Trades: {best['trades']}")
        print(f"  Win Rate: {best['win_rate']:.1f}%")

        print(f"\n💡 Leverage Recommendations:")
        safe_lev = 100 / (best['max_dd'] * 2)
        agg_lev = 100 / (best['max_dd'] * 1.5)

        print(f"  Safe (2x buffer): {safe_lev:.1f}x")
        print(f"  Aggressive (1.5x buffer): {agg_lev:.1f}x")

        print(f"\n  With leverage:")
        for lev in [2, 3, 5]:
            lev_return = best['return'] * lev
            lev_dd = best['max_dd'] * lev
            status = "✅" if lev_dd < 50 else "⚠️" if lev_dd < 80 else "❌"
            print(f"    {status} {lev}x: {lev_return:+.0f}% return, {lev_dd:.1f}% DD")

    else:
        print("\n❌ No configuration achieved <30% DD target")
        print("\nClosest result:")
        best_attempt = configs_df.sort_values('max_dd').iloc[0]
        print(f"  Filter: {best_attempt['filter']}")
        print(f"  SL: {best_attempt['sl_pct']:.1f}%, TP: {best_attempt['tp_pct']:.1f}%")
        print(f"  Max DD: {best_attempt['max_dd']:.1f}%")
        print(f"  Return: {best_attempt['return']:+.1f}%")

    return configs_df


if __name__ == '__main__':
    results = test_configurations()
