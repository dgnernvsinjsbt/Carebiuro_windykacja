import pandas as pd
import numpy as np
import sys

def detect_defended_levels_relaxed(df,
                                    lookback=20,
                                    volume_mult=2.0,
                                    min_defense_hours=12,
                                    max_defense_hours=24,
                                    min_volume_bars=3):
    """
    Detect defended levels with RELAXED conditions to get more trades.
    """

    df['volume_sma'] = df['volume'].rolling(100).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']
    df['local_high'] = df['high'] == df['high'].rolling(lookback*2+1, center=True).max()
    df['local_low'] = df['low'] == df['low'].rolling(lookback*2+1, center=True).min()

    signals = []

    for i in range(lookback, len(df) - max_defense_hours*60):
        # DISTRIBUTION (SHORT)
        if df['local_high'].iloc[i]:
            volume_window = df['volume_ratio'].iloc[i-min_volume_bars+1:i+1]

            if len(volume_window) >= min_volume_bars and (volume_window >= volume_mult).sum() >= min_volume_bars:
                extreme_price = df['high'].iloc[i]
                extreme_time = df['timestamp'].iloc[i]

                for hours_held in range(min_defense_hours, max_defense_hours+1):
                    check_end_idx = i + hours_held * 60
                    if check_end_idx >= len(df):
                        break

                    future_highs = df['high'].iloc[i+1:check_end_idx+1]
                    if (future_highs > extreme_price).any():
                        break

                    if hours_held >= min_defense_hours:
                        entry_idx = i + hours_held * 60
                        if entry_idx >= len(df):
                            break

                        entry_price = df['close'].iloc[entry_idx]
                        entry_time = df['timestamp'].iloc[entry_idx]

                        signals.append({
                            'type': 'DISTRIBUTION',
                            'extreme_time': extreme_time,
                            'extreme_price': extreme_price,
                            'hours_held': hours_held,
                            'entry_time': entry_time,
                            'entry_price': entry_price,
                            'avg_volume_ratio': volume_window.mean(),
                        })
                        break

        # ACCUMULATION (LONG)
        if df['local_low'].iloc[i]:
            volume_window = df['volume_ratio'].iloc[i-min_volume_bars+1:i+1]

            if len(volume_window) >= min_volume_bars and (volume_window >= volume_mult).sum() >= min_volume_bars:
                extreme_price = df['low'].iloc[i]
                extreme_time = df['timestamp'].iloc[i]

                for hours_held in range(min_defense_hours, max_defense_hours+1):
                    check_end_idx = i + hours_held * 60
                    if check_end_idx >= len(df):
                        break

                    future_lows = df['low'].iloc[i+1:check_end_idx+1]
                    if (future_lows < extreme_price).any():
                        break

                    if hours_held >= min_defense_hours:
                        entry_idx = i + hours_held * 60
                        if entry_idx >= len(df):
                            break

                        entry_price = df['close'].iloc[entry_idx]
                        entry_time = df['timestamp'].iloc[entry_idx]

                        signals.append({
                            'type': 'ACCUMULATION',
                            'extreme_time': extreme_time,
                            'extreme_price': extreme_price,
                            'hours_held': hours_held,
                            'entry_time': entry_time,
                            'entry_price': entry_price,
                            'avg_volume_ratio': volume_window.mean(),
                        })
                        break

    return pd.DataFrame(signals)


def backtest_with_targets(signals_df, df, sl_pct, tp_pct, max_hold_hours=48):
    """Backtest with SL/TP"""
    trades = []

    for idx, signal in signals_df.iterrows():
        entry_idx = df[df['timestamp'] == signal['entry_time']].index[0]
        entry_price = signal['entry_price']
        direction = 1 if signal['type'] == 'ACCUMULATION' else -1

        if direction == 1:
            stop_price = entry_price * (1 - sl_pct/100)
            target_price = entry_price * (1 + tp_pct/100)
        else:
            stop_price = entry_price * (1 + sl_pct/100)
            target_price = entry_price * (1 - tp_pct/100)

        exit_idx = min(entry_idx + max_hold_hours*60, len(df)-1)
        exit_price = None
        exit_reason = 'TIME'

        for i in range(entry_idx+1, exit_idx+1):
            if direction == 1:
                if df['low'].iloc[i] <= stop_price:
                    exit_price = stop_price
                    exit_reason = 'SL'
                    break
                elif df['high'].iloc[i] >= target_price:
                    exit_price = target_price
                    exit_reason = 'TP'
                    break
            else:
                if df['high'].iloc[i] >= stop_price:
                    exit_price = stop_price
                    exit_reason = 'SL'
                    break
                elif df['low'].iloc[i] <= target_price:
                    exit_price = target_price
                    exit_reason = 'TP'
                    break

        if exit_price is None:
            exit_price = df['close'].iloc[exit_idx]

        if direction == 1:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        pnl_pct -= 0.10  # Fees

        trades.append({
            'entry_time': signal['entry_time'],
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct,
        })

    trades_df = pd.DataFrame(trades)

    if len(trades_df) == 0:
        return None

    total_return = trades_df['pnl_pct'].sum()
    win_rate = (trades_df['pnl_pct'] > 0).sum() / len(trades_df)

    trades_df['cumulative'] = trades_df['pnl_pct'].cumsum()
    trades_df['running_max'] = trades_df['cumulative'].cummax()
    trades_df['drawdown'] = trades_df['cumulative'] - trades_df['running_max']
    max_dd = trades_df['drawdown'].min()

    return {
        'trades': len(trades_df),
        'return': total_return,
        'max_dd': max_dd,
        'ratio': abs(total_return/max_dd) if max_dd != 0 else 0,
        'win_rate': win_rate,
        'tp_count': (trades_df['exit_reason'] == 'TP').sum(),
        'sl_count': (trades_df['exit_reason'] == 'SL').sum(),
    }


if __name__ == '__main__':
    print("Loading ETH 1m data...")
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"Loaded {len(df)} candles\n")

    print("="*80)
    print("RELAXED CONDITIONS OPTIMIZATION")
    print("Goal: Find configs with 10+ trades AND Return/DD >= 5.0x")
    print("="*80)

    results = []

    # Test relaxed parameters
    volume_thresholds = [1.5, 1.8, 2.0, 2.2, 2.5]
    min_bars_options = [3, 4, 5]
    defense_periods = [
        (8, 18),   # Shorter
        (10, 20),  # Shorter
        (12, 24),  # Original
        (6, 16),   # Much shorter
    ]
    lookbacks = [15, 20, 30]

    configs_tested = 0
    configs_meeting_criteria = []

    for vol_thresh in volume_thresholds:
        for min_bars in min_bars_options:
            for (min_def, max_def) in defense_periods:
                for lookback in lookbacks:
                    configs_tested += 1

                    # Detect signals
                    signals_df = detect_defended_levels_relaxed(
                        df,
                        lookback=lookback,
                        volume_mult=vol_thresh,
                        min_defense_hours=min_def,
                        max_defense_hours=max_def,
                        min_volume_bars=min_bars
                    )

                    if len(signals_df) < 10:
                        continue  # Need at least 10 trades

                    # Backtest with best SL/TP from optimization (1% / 10%)
                    result = backtest_with_targets(signals_df, df, sl_pct=1.0, tp_pct=10.0)

                    if result is None:
                        continue

                    # Check if meets criteria
                    if result['ratio'] >= 5.0 and result['trades'] >= 10:
                        config = {
                            'volume_mult': vol_thresh,
                            'min_bars': min_bars,
                            'min_defense_h': min_def,
                            'max_defense_h': max_def,
                            'lookback': lookback,
                            'trades': result['trades'],
                            'return': result['return'],
                            'max_dd': result['max_dd'],
                            'ratio': result['ratio'],
                            'win_rate': result['win_rate'],
                            'tp_count': result['tp_count'],
                            'sl_count': result['sl_count'],
                        }
                        configs_meeting_criteria.append(config)
                        results.append(config)

                        print(f"✓ Vol:{vol_thresh}x Bars:{min_bars} Def:{min_def}-{max_def}h LB:{lookback} → "
                              f"Trades:{result['trades']} | Ret:{result['return']:+.2f}% | "
                              f"DD:{result['max_dd']:.2f}% | R/DD:{result['ratio']:.2f}x | "
                              f"WR:{result['win_rate']*100:.0f}% | TP:{result['tp_count']}/{result['trades']}")

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Configs tested: {configs_tested}")
    print(f"Configs meeting criteria (10+ trades, R/DD >= 5.0x): {len(configs_meeting_criteria)}")

    if len(configs_meeting_criteria) == 0:
        print("\n❌ No configurations found meeting criteria (10+ trades AND R/DD >= 5.0x)")
        print("\nLet's try with lower R/DD threshold (>= 3.0x)...")

        # Try again with lower threshold
        results_lower = []
        for vol_thresh in volume_thresholds:
            for min_bars in min_bars_options:
                for (min_def, max_def) in defense_periods:
                    for lookback in lookbacks:
                        signals_df = detect_defended_levels_relaxed(
                            df,
                            lookback=lookback,
                            volume_mult=vol_thresh,
                            min_defense_hours=min_def,
                            max_defense_hours=max_def,
                            min_volume_bars=min_bars
                        )

                        if len(signals_df) < 10:
                            continue

                        result = backtest_with_targets(signals_df, df, sl_pct=1.0, tp_pct=10.0)

                        if result is None:
                            continue

                        if result['ratio'] >= 3.0 and result['trades'] >= 10:
                            config = {
                                'volume_mult': vol_thresh,
                                'min_bars': min_bars,
                                'min_defense_h': min_def,
                                'max_defense_h': max_def,
                                'lookback': lookback,
                                'trades': result['trades'],
                                'return': result['return'],
                                'max_dd': result['max_dd'],
                                'ratio': result['ratio'],
                                'win_rate': result['win_rate'],
                                'tp_count': result['tp_count'],
                                'sl_count': result['sl_count'],
                            }
                            results_lower.append(config)

        if len(results_lower) > 0:
            print(f"\n✓ Found {len(results_lower)} configs with R/DD >= 3.0x")
            results_df = pd.DataFrame(results_lower)
            results_df = results_df.sort_values('ratio', ascending=False)
            print("\nTOP 10 BY RETURN/DD:")
            print(results_df.head(10).to_string(index=False))

            # Save
            results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_relaxed_configs.csv', index=False)
            print(f"\n✓ Saved all configs to trading/results/eth_defended_levels_relaxed_configs.csv")

            # Show best config details
            best = results_df.iloc[0]
            print(f"\n{'='*80}")
            print("BEST RELAXED CONFIG")
            print(f"{'='*80}")
            print(f"Volume threshold: {best['volume_mult']}x average")
            print(f"Min volume bars: {best['min_bars']} consecutive")
            print(f"Defense period: {best['min_defense_h']}-{best['max_defense_h']} hours")
            print(f"Lookback: {best['lookback']} bars")
            print(f"\nRESULTS:")
            print(f"  Trades: {int(best['trades'])} (vs 3 original)")
            print(f"  Return: {best['return']:+.2f}%")
            print(f"  Max DD: {best['max_dd']:.2f}%")
            print(f"  Return/DD: {best['ratio']:.2f}x")
            print(f"  Win Rate: {best['win_rate']*100:.1f}%")
            print(f"  TP hits: {int(best['tp_count'])}/{int(best['trades'])}")
            print(f"  SL hits: {int(best['sl_count'])}/{int(best['trades'])}")
        else:
            print("\n❌ No configurations found even with R/DD >= 3.0x")
            print("The pattern may be too rare on this timeframe/token.")
    else:
        results_df = pd.DataFrame(configs_meeting_criteria)
        results_df = results_df.sort_values('ratio', ascending=False)

        print("\nTOP 10 CONFIGS BY RETURN/DD:")
        print(results_df.head(10).to_string(index=False))

        print("\nTOP 10 CONFIGS BY TOTAL RETURN:")
        print(results_df.nlargest(10, 'return').to_string(index=False))

        print("\nTOP 10 CONFIGS BY TRADE COUNT:")
        print(results_df.nlargest(10, 'trades').to_string(index=False))

        # Save
        results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_relaxed_configs.csv', index=False)
        print(f"\n✓ Saved all {len(results_df)} configs to trading/results/eth_defended_levels_relaxed_configs.csv")

        # Show best config
        best = results_df.iloc[0]
        print(f"\n{'='*80}")
        print("BEST RELAXED CONFIG")
        print(f"{'='*80}")
        print(f"Volume threshold: {best['volume_mult']}x average")
        print(f"Min volume bars: {best['min_bars']} consecutive")
        print(f"Defense period: {best['min_defense_h']}-{best['max_defense_h']} hours")
        print(f"Lookback: {best['lookback']} bars")
        print(f"\nRESULTS:")
        print(f"  Trades: {int(best['trades'])} (vs 3 original)")
        print(f"  Return: {best['return']:+.2f}%")
        print(f"  Max DD: {best['max_dd']:.2f}%")
        print(f"  Return/DD: {best['ratio']:.2f}x")
        print(f"  Win Rate: {best['win_rate']*100:.1f}%")
        print(f"  TP hits: {int(best['tp_count'])}/{int(best['trades'])}")
        print(f"  SL hits: {int(best['sl_count'])}/{int(best['trades'])}")

        print(f"\n{'='*80}")
        print("RECOMMENDATION")
        print(f"{'='*80}")
        print("Use this relaxed config to get more trades while maintaining good R/DD.")
        print("With 10+ trades, statistical confidence is much higher than 3 trades.")
