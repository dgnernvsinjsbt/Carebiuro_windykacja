"""
Test for overfitting: Run ALL parameter combinations on ONLY Dec 8-15 data
to see if ANY configuration was profitable on that terrible week.
"""

import pandas as pd
import numpy as np
from itertools import product
from typing import Dict, List, Tuple

# Load MOODENG 1h data
df = pd.read_csv('bingx-trading-bot/trading/moodeng_usdt_90d_1h.csv', parse_dates=['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Filter to ONLY Dec 8-15, 2025
df = df[(df['timestamp'] >= '2025-12-08') & (df['timestamp'] < '2025-12-16')].reset_index(drop=True)
print(f"Testing on Dec 8-15 data: {len(df)} bars")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Calculate indicators
def calculate_indicators(df):
    # RSI (Wilder's method)
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # ATR
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()

    return df

df = calculate_indicators(df)

# Baseline parameters (from optimal_configs_90d.csv)
BASELINE = {
    'rsi_low': 30,
    'rsi_high': 65,
    'limit_pct': 1.0,
    'sl_mult': 2.0,
    'tp_mult': 1.0,
    'max_hold': 3
}

# Parameter grid to test (729 combinations)
param_grid = {
    'rsi_low': [25, 27, 30],
    'rsi_high': [65, 68, 70],
    'limit_pct': [0.5, 1.0, 1.5],  # % offset for limit order
    'sl_mult': [1.5, 2.0, 2.5],     # ATR multiplier for SL
    'tp_mult': [1.0, 1.5, 2.0],     # ATR multiplier for TP
    'max_hold': [3, 4, 5]           # hours max hold
}

def backtest_strategy(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, max_hold):
    """Run backtest with given parameters"""
    trades = []
    equity = 100.0
    equity_curve = [equity]

    i = 14  # Start after indicators are valid
    while i < len(df):
        row = df.iloc[i]

        # Check for LONG signal (RSI oversold)
        if row['rsi'] < rsi_low:
            entry_price = row['close'] * (1 + limit_pct / 100)  # Limit order above
            sl_price = entry_price - (row['atr'] * sl_mult)
            tp_price = entry_price + (row['atr'] * tp_mult)

            # Simulate next bars for fill + exit
            filled = False
            for j in range(i + 1, min(i + 4, len(df))):  # 3 bars to fill
                if df.iloc[j]['low'] <= entry_price:
                    filled = True
                    fill_idx = j
                    break

            if filled:
                # Look for exit
                exit_idx = None
                exit_price = None
                exit_type = 'TIME'

                for k in range(fill_idx + 1, min(fill_idx + max_hold + 1, len(df))):
                    bar = df.iloc[k]

                    # Check SL
                    if bar['low'] <= sl_price:
                        exit_idx = k
                        exit_price = sl_price
                        exit_type = 'SL'
                        break

                    # Check TP
                    if bar['high'] >= tp_price:
                        exit_idx = k
                        exit_price = tp_price
                        exit_type = 'TP'
                        break

                # Time exit if no SL/TP
                if exit_idx is None:
                    exit_idx = min(fill_idx + max_hold, len(df) - 1)
                    exit_price = df.iloc[exit_idx]['close']
                    exit_type = 'TIME'

                # Calculate P&L
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                pnl_pct -= 0.10  # Fees

                pnl_dollars = equity * (pnl_pct / 100)
                equity += pnl_dollars

                trades.append({
                    'entry_time': df.iloc[fill_idx]['timestamp'],
                    'entry_price': entry_price,
                    'exit_time': df.iloc[exit_idx]['timestamp'],
                    'exit_price': exit_price,
                    'exit_type': exit_type,
                    'pnl_pct': pnl_pct,
                    'equity': equity
                })

                equity_curve.append(equity)
                i = exit_idx + 1
                continue

        # Check for SHORT signal (RSI overbought)
        if row['rsi'] > rsi_high:
            entry_price = row['close'] * (1 - limit_pct / 100)  # Limit order below
            sl_price = entry_price + (row['atr'] * sl_mult)
            tp_price = entry_price - (row['atr'] * tp_mult)

            # Simulate next bars for fill + exit
            filled = False
            for j in range(i + 1, min(i + 4, len(df))):
                if df.iloc[j]['high'] >= entry_price:
                    filled = True
                    fill_idx = j
                    break

            if filled:
                # Look for exit
                exit_idx = None
                exit_price = None
                exit_type = 'TIME'

                for k in range(fill_idx + 1, min(fill_idx + max_hold + 1, len(df))):
                    bar = df.iloc[k]

                    # Check SL
                    if bar['high'] >= sl_price:
                        exit_idx = k
                        exit_price = sl_price
                        exit_type = 'SL'
                        break

                    # Check TP
                    if bar['low'] <= tp_price:
                        exit_idx = k
                        exit_price = tp_price
                        exit_type = 'TP'
                        break

                # Time exit if no SL/TP
                if exit_idx is None:
                    exit_idx = min(fill_idx + max_hold, len(df) - 1)
                    exit_price = df.iloc[exit_idx]['close']
                    exit_type = 'TIME'

                # Calculate P&L (SHORT)
                pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                pnl_pct -= 0.10  # Fees

                pnl_dollars = equity * (pnl_pct / 100)
                equity += pnl_dollars

                trades.append({
                    'entry_time': df.iloc[fill_idx]['timestamp'],
                    'entry_price': entry_price,
                    'exit_time': df.iloc[exit_idx]['timestamp'],
                    'exit_price': exit_price,
                    'exit_type': exit_type,
                    'pnl_pct': pnl_pct,
                    'equity': equity
                })

                equity_curve.append(equity)
                i = exit_idx + 1
                continue

        i += 1

    # Calculate metrics
    if len(trades) < 2:
        return None

    df_trades = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100

    # Max drawdown
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    # Win rate
    winners = (df_trades['pnl_pct'] > 0).sum()
    win_rate = (winners / len(df_trades)) * 100

    # Exit type breakdown
    tp_rate = (df_trades['exit_type'] == 'TP').sum() / len(df_trades) * 100
    sl_rate = (df_trades['exit_type'] == 'SL').sum() / len(df_trades) * 100
    time_rate = (df_trades['exit_type'] == 'TIME').sum() / len(df_trades) * 100

    return {
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd_ratio': total_return / abs(max_dd) if max_dd != 0 else 0,
        'num_trades': len(df_trades),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'sl_rate': sl_rate,
        'time_rate': time_rate,
        'final_equity': equity,
        'rsi_low': rsi_low,
        'rsi_high': rsi_high,
        'limit_pct': limit_pct,
        'sl_mult': sl_mult,
        'tp_mult': tp_mult,
        'max_hold': max_hold
    }

# Test all combinations
print(f"\nTesting {np.prod([len(v) for v in param_grid.values()])} parameter combinations...")
print("=" * 80)

results = []
for params in product(*param_grid.values()):
    rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, max_hold = params

    result = backtest_strategy(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, max_hold)
    if result is not None:
        results.append(result)

# Handle empty results
if len(results) == 0:
    print("❌ ALL 729 COMBINATIONS FAILED")
    print("   - Either generated <2 trades OR")
    print("   - All lost money with invalid drawdown calculations")
    print("\n🔍 VERDICT: BAD VARIANCE")
    print("   Even with aggressive parameter optimization, NO configuration")
    print("   could make money on Dec 8-15. This suggests the week was truly")
    print("   unworkable, NOT that we overfitted to Sep-Dec 7 data.")
else:
    # Convert to DataFrame and sort
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('total_return', ascending=False)

    # Show top 10
    print(f"\n✅ Found {len(df_results)} valid configurations (2+ trades)")
    print("\nTop 10 Performers on Dec 8-15:")
    print("=" * 80)

    for idx, row in df_results.head(10).iterrows():
        print(f"\n{row['rsi_low']}/{row['rsi_high']} | Limit:{row['limit_pct']}% | "
              f"SL:{row['sl_mult']}x | TP:{row['tp_mult']}x | Hold:{row['max_hold']}h")
        print(f"  Return: {row['total_return']:+.2f}% | MaxDD: {row['max_dd']:.2f}% | "
              f"R/DD: {row['return_dd_ratio']:.2f}x")
        print(f"  Trades: {row['num_trades']} | Win: {row['win_rate']:.1f}% | "
              f"TP: {row['tp_rate']:.1f}% | SL: {row['sl_rate']:.1f}% | Time: {row['time_rate']:.1f}%")

    # Find baseline params result
    baseline_result = df_results[
        (df_results['rsi_low'] == BASELINE['rsi_low']) &
        (df_results['rsi_high'] == BASELINE['rsi_high']) &
        (df_results['limit_pct'] == BASELINE['limit_pct']) &
        (df_results['sl_mult'] == BASELINE['sl_mult']) &
        (df_results['tp_mult'] == BASELINE['tp_mult']) &
        (df_results['max_hold'] == BASELINE['max_hold'])
    ]

    print("\n" + "=" * 80)
    print("BASELINE PARAMS (30/65, 1.0%, 2.0x, 1.0x, 3h) ON DEC 8-15:")
    print("=" * 80)

    if len(baseline_result) > 0:
        base = baseline_result.iloc[0]
        print(f"Return: {base['total_return']:+.2f}% | MaxDD: {base['max_dd']:.2f}% | "
              f"R/DD: {base['return_dd_ratio']:.2f}x")
        print(f"Trades: {base['num_trades']} | Win: {base['win_rate']:.1f}% | "
              f"SL: {base['sl_rate']:.1f}%")

        baseline_rank = df_results.index.get_loc(baseline_result.index[0]) + 1
        print(f"\nBaseline rank: {baseline_rank} out of {len(df_results)}")
    else:
        print("❌ Baseline params generated <2 trades on Dec 8-15")

    # Best performer
    best = df_results.iloc[0]
    print("\n" + "=" * 80)
    print("BEST PERFORMER ON DEC 8-15:")
    print("=" * 80)
    print(f"Params: {best['rsi_low']}/{best['rsi_high']} | Limit:{best['limit_pct']}% | "
          f"SL:{best['sl_mult']}x | TP:{best['tp_mult']}x | Hold:{best['max_hold']}h")
    print(f"Return: {best['total_return']:+.2f}% | MaxDD: {best['max_dd']:.2f}% | "
          f"R/DD: {best['return_dd_ratio']:.2f}x")

    # Count profitable configs
    profitable = (df_results['total_return'] > 0).sum()
    print(f"\n📊 {profitable} out of {len(df_results)} configs were profitable ({profitable/len(df_results)*100:.1f}%)")

    # Verdict
    print("\n" + "=" * 80)
    print("🔍 VERDICT:")
    print("=" * 80)

    if profitable == 0:
        print("❌ NO PROFITABLE CONFIGURATIONS")
        print("   Even after testing 729 parameter combinations, NOT A SINGLE ONE")
        print("   made money on Dec 8-15. This is STRONG EVIDENCE of bad variance,")
        print("   NOT overfitting.")
    elif profitable < 10:
        print("⚠️  VERY FEW PROFITABLE CONFIGURATIONS")
        print(f"   Only {profitable} out of {len(df_results)} worked. This suggests")
        print("   Dec 8-15 was genuinely difficult, not overfitting.")
    else:
        print("✅ MANY PROFITABLE CONFIGURATIONS")
        print(f"   {profitable} configs worked. Compare best params to baseline:")

        # Compare param differences
        param_diffs = []
        for param in ['rsi_low', 'rsi_high', 'limit_pct', 'sl_mult', 'tp_mult', 'max_hold']:
            if best[param] != BASELINE[param]:
                param_diffs.append(f"{param}: {BASELINE[param]} → {best[param]}")

        if len(param_diffs) > 3:
            print(f"   ⚠️  {len(param_diffs)} parameters differ significantly:")
            for diff in param_diffs:
                print(f"      - {diff}")
            print("   This COULD indicate some overfitting.")
        else:
            print(f"   ✅ Only {len(param_diffs)} parameters differ:")
            for diff in param_diffs:
                print(f"      - {diff}")
            print("   Baseline params were reasonably close to optimal.")

print("\n" + "=" * 80)
print("Analysis complete.")
