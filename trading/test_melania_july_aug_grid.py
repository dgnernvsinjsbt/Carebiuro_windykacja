"""
Test ALL parameter combinations on MELANIA July-Aug 2025 data
to see if ANY configuration would have been profitable.

If YES → We just picked the wrong params (overfitting)
If NO → July-Aug was genuinely impossible for RSI strategies (variance)
"""

import pandas as pd
import numpy as np
from itertools import product

print("=" * 80)
print("MELANIA-USDT: Parameter Grid Search on July-Aug 2025")
print("Testing 729 combinations to see if ANY worked")
print("=" * 80)

# Load data
df = pd.read_csv('trading/melania_usdt_july_aug_2025_1h.csv', parse_dates=['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\nData: {len(df)} bars ({df['timestamp'].min()} to {df['timestamp'].max()})")

# Calculate indicators
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

# Parameter grid (729 combinations)
param_grid = {
    'rsi_low': [25, 27, 30],
    'rsi_high': [65, 68, 70],
    'limit_pct': [0.5, 1.0, 1.5],
    'sl_mult': [1.0, 1.5, 2.0],
    'tp_mult': [1.0, 1.5, 2.0],
    'max_hold': [3, 4, 5]
}

def backtest(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, max_hold):
    trades = []
    equity = 100.0
    equity_curve = [equity]

    i = 14
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            i += 1
            continue

        direction = None
        if row['rsi'] < rsi_low:
            direction = 'LONG'
        elif row['rsi'] > rsi_high:
            direction = 'SHORT'

        if direction is None:
            i += 1
            continue

        if direction == 'LONG':
            entry_price = row['close'] * (1 + limit_pct / 100)
            sl_price = entry_price - (row['atr'] * sl_mult)
            tp_price = entry_price + (row['atr'] * tp_mult)

            filled = False
            fill_idx = None
            for j in range(i + 1, min(i + 4, len(df))):
                if df.iloc[j]['low'] <= entry_price:
                    filled = True
                    fill_idx = j
                    break

            if not filled:
                i += 1
                continue

            exit_idx = None
            exit_price = None
            exit_type = 'TIME'

            for k in range(fill_idx + 1, min(fill_idx + max_hold + 1, len(df))):
                bar = df.iloc[k]
                if bar['low'] <= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['high'] >= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break

            if exit_idx is None:
                exit_idx = min(fill_idx + max_hold, len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']
                exit_type = 'TIME'

            pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
            equity += equity * (pnl_pct / 100)
            trades.append({'pnl_pct': pnl_pct, 'exit_type': exit_type})
            equity_curve.append(equity)
            i = exit_idx + 1

        elif direction == 'SHORT':
            entry_price = row['close'] * (1 - limit_pct / 100)
            sl_price = entry_price + (row['atr'] * sl_mult)
            tp_price = entry_price - (row['atr'] * tp_mult)

            filled = False
            fill_idx = None
            for j in range(i + 1, min(i + 4, len(df))):
                if df.iloc[j]['high'] >= entry_price:
                    filled = True
                    fill_idx = j
                    break

            if not filled:
                i += 1
                continue

            exit_idx = None
            exit_price = None
            exit_type = 'TIME'

            for k in range(fill_idx + 1, min(fill_idx + max_hold + 1, len(df))):
                bar = df.iloc[k]
                if bar['high'] >= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['low'] <= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break

            if exit_idx is None:
                exit_idx = min(fill_idx + max_hold, len(df) - 1)
                exit_price = df.iloc[exit_idx]['close']
                exit_type = 'TIME'

            pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
            equity += equity * (pnl_pct / 100)
            trades.append({'pnl_pct': pnl_pct, 'exit_type': exit_type})
            equity_curve.append(equity)
            i = exit_idx + 1

        else:
            i += 1

    if len(trades) < 2:
        return None

    df_t = pd.DataFrame(trades)
    ret = ((equity_curve[-1] - 100) / 100) * 100
    eq = pd.Series(equity_curve)
    dd = ((eq - eq.expanding().max()) / eq.expanding().max() * 100).min()
    wr = (df_t['pnl_pct'] > 0).sum() / len(df_t) * 100
    sl_rate = (df_t['exit_type'] == 'SL').sum() / len(df_t) * 100

    return {
        'return': ret,
        'max_dd': dd,
        'return_dd': ret / abs(dd) if dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': wr,
        'sl_rate': sl_rate,
        'rsi_low': rsi_low,
        'rsi_high': rsi_high,
        'limit_pct': limit_pct,
        'sl_mult': sl_mult,
        'tp_mult': tp_mult,
        'max_hold': max_hold
    }

# Test all combinations
print(f"\nTesting {np.prod([len(v) for v in param_grid.values()])} combinations...")

results = []
for params in product(*param_grid.values()):
    rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, max_hold = params
    result = backtest(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, max_hold)
    if result is not None:
        results.append(result)

if len(results) == 0:
    print("\n❌ ALL 729 COMBINATIONS FAILED")
    print("   No configuration generated 2+ trades or all lost money")
    print("\n🔍 VERDICT: July-Aug was genuinely impossible (like Dec 8-15)")
    print("   Not overfitting - just bad market conditions for RSI strategies")
else:
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('return', ascending=False)

    print(f"\n✅ Found {len(df_results)} valid configurations")

    # Count profitable
    profitable = (df_results['return'] > 0).sum()
    print(f"📊 {profitable} out of {len(df_results)} were profitable ({profitable/len(df_results)*100:.1f}%)")

    # Show top 10
    print("\n" + "=" * 80)
    print("TOP 10 PERFORMERS:")
    print("=" * 80)

    for idx, row in df_results.head(10).iterrows():
        print(f"\n{row['rsi_low']}/{row['rsi_high']} | Limit:{row['limit_pct']}% | "
              f"SL:{row['sl_mult']}x | TP:{row['tp_mult']}x | Hold:{row['max_hold']}h")
        print(f"  Return: {row['return']:+.2f}% | DD: {row['max_dd']:.2f}% | R/DD: {row['return_dd']:.2f}x")
        print(f"  Trades: {row['trades']} | Win: {row['win_rate']:.1f}% | SL: {row['sl_rate']:.1f}%")

    # Compare to training params
    TRAINING_PARAMS = {
        'rsi_low': 27,
        'rsi_high': 65,
        'limit_pct': 1.5,
        'sl_mult': 1.5,
        'tp_mult': 2.0,
        'max_hold': 3
    }

    training_result = df_results[
        (df_results['rsi_low'] == TRAINING_PARAMS['rsi_low']) &
        (df_results['rsi_high'] == TRAINING_PARAMS['rsi_high']) &
        (df_results['limit_pct'] == TRAINING_PARAMS['limit_pct']) &
        (df_results['sl_mult'] == TRAINING_PARAMS['sl_mult']) &
        (df_results['tp_mult'] == TRAINING_PARAMS['tp_mult']) &
        (df_results['max_hold'] == TRAINING_PARAMS['max_hold'])
    ]

    print("\n" + "=" * 80)
    print("TRAINING PARAMS (27/65, 1.5%, 1.5x, 2.0x, 3h):")
    print("=" * 80)

    if len(training_result) > 0:
        tr = training_result.iloc[0]
        rank = df_results.index.get_loc(training_result.index[0]) + 1
        print(f"Return: {tr['return']:+.2f}% | DD: {tr['max_dd']:.2f}% | R/DD: {tr['return_dd']:.2f}x")
        print(f"Rank: {rank} out of {len(df_results)}")

        if tr['return'] < 0:
            print(f"\n❌ Training params were UNPROFITABLE on July-Aug")
        else:
            print(f"\n✅ Training params were profitable (but not optimal)")
    else:
        print("❌ Training params generated <2 trades")

    # Verdict
    print("\n" + "=" * 80)
    print("VERDICT:")
    print("=" * 80)

    best = df_results.iloc[0]

    if profitable > 100:
        print(f"\n✅ MANY PROFITABLE CONFIGS ({profitable})")
        print("   July-Aug was WORKABLE with right parameters")
        print(f"\n   Best config: {best['rsi_low']}/{best['rsi_high']}, {best['limit_pct']}%, "
              f"{best['sl_mult']}x, {best['tp_mult']}x, {best['max_hold']}h")
        print(f"   Best return: {best['return']:+.2f}% (vs {TRAINING_PARAMS} params: {tr['return']:+.2f}%)")

        # Compare params
        param_diffs = []
        for p in ['rsi_low', 'rsi_high', 'limit_pct', 'sl_mult', 'tp_mult', 'max_hold']:
            if best[p] != TRAINING_PARAMS[p]:
                param_diffs.append(f"{p}: {TRAINING_PARAMS[p]} → {best[p]}")

        print(f"\n   Parameter differences: {len(param_diffs)}/6")
        for diff in param_diffs:
            print(f"      - {diff}")

        if len(param_diffs) >= 4:
            print("\n   ⚠️  SIGNIFICANTLY DIFFERENT parameters needed")
            print("   → STRONG evidence of overfitting to Sep-Dec period")
        else:
            print("\n   ✅ Similar parameters worked")
            print("   → Training params were reasonable, just not optimal")

    elif profitable > 10:
        print(f"\n⚠️  FEW PROFITABLE CONFIGS ({profitable})")
        print("   July-Aug was DIFFICULT but workable")
        print("   Training params likely overfitted to Sep-Dec")

    elif profitable > 0:
        print(f"\n❌ VERY FEW PROFITABLE CONFIGS ({profitable})")
        print("   July-Aug was VERY DIFFICULT")
        print("   Mix of overfitting + bad market conditions")

    else:
        print("\n❌ NO PROFITABLE CONFIGS")
        print("   July-Aug was genuinely impossible (like Dec 8-15)")
        print("   Not overfitting - just bad variance")

print("\n" + "=" * 80)
