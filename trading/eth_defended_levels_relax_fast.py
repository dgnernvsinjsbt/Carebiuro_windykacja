import pandas as pd
import numpy as np

# Reuse the functions from before (copy-paste for speed)
def detect_defended_levels_relaxed(df, lookback=20, volume_mult=2.0,
                                    min_defense_hours=12, max_defense_hours=24, min_volume_bars=3):
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

def backtest_simple(signals_df, df, sl_pct, tp_pct):
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

        exit_idx = min(entry_idx + 48*60, len(df)-1)
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
        pnl_pct -= 0.10
        trades.append({'pnl_pct': pnl_pct, 'exit_reason': exit_reason})

    trades_df = pd.DataFrame(trades)
    if len(trades_df) == 0:
        return None

    total_return = trades_df['pnl_pct'].sum()
    trades_df['cumulative'] = trades_df['pnl_pct'].cumsum()
    trades_df['running_max'] = trades_df['cumulative'].cummax()
    trades_df['drawdown'] = trades_df['cumulative'] - trades_df['running_max']
    max_dd = trades_df['drawdown'].min()

    return {
        'trades': len(trades_df),
        'return': total_return,
        'max_dd': max_dd,
        'ratio': abs(total_return/max_dd) if max_dd != 0 else 0,
        'win_rate': (trades_df['pnl_pct'] > 0).sum() / len(trades_df),
        'tp_count': (trades_df['exit_reason'] == 'TP').sum(),
    }

if __name__ == '__main__':
    print("Loading ETH data...")
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/eth_usdt_1m_lbank.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    print(f"✓ Loaded {len(df)} candles\n")

    print("="*80)
    print("FAST RELAXATION: Testing most promising configs only")
    print("Goal: 10+ trades with Return/DD >= 5.0x (or at least >= 3.0x)")
    print("="*80)

    # Focus on most promising relaxations
    configs_to_test = [
        # Relax volume threshold (most impactful)
        {'volume_mult': 2.0, 'min_bars': 5, 'min_def': 12, 'max_def': 24, 'lookback': 20, 'name': 'Lower volume 2.0x'},
        {'volume_mult': 1.8, 'min_bars': 5, 'min_def': 12, 'max_def': 24, 'lookback': 20, 'name': 'Lower volume 1.8x'},
        {'volume_mult': 1.5, 'min_bars': 5, 'min_def': 12, 'max_def': 24, 'lookback': 20, 'name': 'Lower volume 1.5x'},

        # Fewer bars required
        {'volume_mult': 2.0, 'min_bars': 3, 'min_def': 12, 'max_def': 24, 'lookback': 20, 'name': 'Fewer bars (3)'},
        {'volume_mult': 2.0, 'min_bars': 4, 'min_def': 12, 'max_def': 24, 'lookback': 20, 'name': 'Fewer bars (4)'},

        # Shorter defense period
        {'volume_mult': 2.0, 'min_bars': 5, 'min_def': 8, 'max_def': 18, 'lookback': 20, 'name': 'Shorter defense 8-18h'},
        {'volume_mult': 2.0, 'min_bars': 5, 'min_def': 6, 'max_def': 16, 'lookback': 20, 'name': 'Shorter defense 6-16h'},

        # Combinations
        {'volume_mult': 1.8, 'min_bars': 3, 'min_def': 10, 'max_def': 20, 'lookback': 20, 'name': 'Combo: 1.8x vol + 3 bars + 10-20h'},
        {'volume_mult': 2.0, 'min_bars': 4, 'min_def': 8, 'max_def': 18, 'lookback': 20, 'name': 'Combo: 2.0x vol + 4 bars + 8-18h'},

        # Original for comparison
        {'volume_mult': 2.5, 'min_bars': 5, 'min_def': 12, 'max_def': 24, 'lookback': 20, 'name': 'ORIGINAL'},
    ]

    results = []

    for i, config in enumerate(configs_to_test, 1):
        print(f"\n[{i}/{len(configs_to_test)}] Testing: {config['name']}...")

        signals_df = detect_defended_levels_relaxed(
            df,
            lookback=config['lookback'],
            volume_mult=config['volume_mult'],
            min_defense_hours=config['min_def'],
            max_defense_hours=config['max_def'],
            min_volume_bars=config['min_bars']
        )

        print(f"     Signals detected: {len(signals_df)}")

        if len(signals_df) < 5:
            print(f"     ⚠️ Too few signals (<5), skipping...")
            continue

        result = backtest_simple(signals_df, df, sl_pct=1.0, tp_pct=10.0)

        if result:
            print(f"     Return: {result['return']:+.2f}% | DD: {result['max_dd']:.2f}% | "
                  f"R/DD: {result['ratio']:.2f}x | WR: {result['win_rate']*100:.0f}% | "
                  f"TP: {result['tp_count']}/{result['trades']}")

            results.append({
                **config,
                **result
            })

    print(f"\n{'='*80}")
    print("RESULTS")
    print(f"{'='*80}")

    if len(results) == 0:
        print("❌ No configs produced results")
    else:
        results_df = pd.DataFrame(results)

        # Filter by criteria
        good_configs = results_df[(results_df['trades'] >= 10) & (results_df['ratio'] >= 5.0)]

        if len(good_configs) > 0:
            print(f"\n✅ Found {len(good_configs)} configs with 10+ trades AND R/DD >= 5.0x\n")
            good_configs = good_configs.sort_values('ratio', ascending=False)
            print(good_configs[['name', 'trades', 'return', 'max_dd', 'ratio', 'win_rate']].to_string(index=False))

            best = good_configs.iloc[0]
            print(f"\n{'='*80}")
            print(f"🏆 BEST CONFIG: {best['name']}")
            print(f"{'='*80}")
            print(f"Volume: {best['volume_mult']}x | Bars: {int(best['min_bars'])} | "
                  f"Defense: {int(best['min_def'])}-{int(best['max_def'])}h | Lookback: {int(best['lookback'])}")
            print(f"\nTrades: {int(best['trades'])} (vs 3 original)")
            print(f"Return: {best['return']:+.2f}%")
            print(f"Max DD: {best['max_dd']:.2f}%")
            print(f"Return/DD: {best['ratio']:.2f}x")
            print(f"Win Rate: {best['win_rate']*100:.1f}%")

        else:
            print("⚠️ No configs met both criteria (10+ trades AND R/DD >= 5.0x)")
            print("\nTrying lower threshold (R/DD >= 3.0x)...\n")

            decent_configs = results_df[(results_df['trades'] >= 10) & (results_df['ratio'] >= 3.0)]

            if len(decent_configs) > 0:
                print(f"✅ Found {len(decent_configs)} configs with 10+ trades AND R/DD >= 3.0x\n")
                decent_configs = decent_configs.sort_values('ratio', ascending=False)
                print(decent_configs[['name', 'trades', 'return', 'max_dd', 'ratio', 'win_rate']].to_string(index=False))

                best = decent_configs.iloc[0]
                print(f"\n{'='*80}")
                print(f"🏆 BEST CONFIG (R/DD >= 3.0x): {best['name']}")
                print(f"{'='*80}")
                print(f"Volume: {best['volume_mult']}x | Bars: {int(best['min_bars'])} | "
                      f"Defense: {int(best['min_def'])}-{int(best['max_def'])}h | Lookback: {int(best['lookback'])}")
                print(f"\nTrades: {int(best['trades'])} (vs 3 original)")
                print(f"Return: {best['return']:+.2f}%")
                print(f"Max DD: {best['max_dd']:.2f}%")
                print(f"Return/DD: {best['ratio']:.2f}x")
                print(f"Win Rate: {best['win_rate']*100:.1f}%")
            else:
                print("❌ No configs with 10+ trades even at R/DD >= 3.0x")
                print("\nShowing all configs with 5+ trades:\n")
                all_configs = results_df[results_df['trades'] >= 5].sort_values('ratio', ascending=False)
                print(all_configs[['name', 'trades', 'return', 'max_dd', 'ratio', 'win_rate']].to_string(index=False))

        # Save all results
        results_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/eth_defended_levels_relaxed_comparison.csv', index=False)
        print(f"\n✓ Saved all results to trading/results/eth_defended_levels_relaxed_comparison.csv")
