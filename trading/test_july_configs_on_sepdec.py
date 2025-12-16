"""
Test the top July-Aug configs on Sep-Dec data
to see if they work consistently across both periods
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("Testing Top July-Aug Configs on Sep-Dec 2025")
print("=" * 80)

# Load Sep-Dec data
df = pd.read_csv('bingx-trading-bot/trading/melania_usdt_90d_1h.csv', parse_dates=['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
df = df[(df['timestamp'] >= '2025-09-15') & (df['timestamp'] < '2025-12-08')].reset_index(drop=True)

print(f"\nSep-Dec Data: {len(df)} bars ({df['timestamp'].min()} to {df['timestamp'].max()})")

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

def backtest(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult):
    trades = []
    equity = 100.0
    equity_curve = [equity]

    i = 14
    while i < len(df):
        row = df.iloc[i]
        prev_row = df.iloc[i-1] if i > 0 else None

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or prev_row is None or pd.isna(prev_row['rsi']):
            i += 1
            continue

        # LONG: RSI crosses UP through rsi_low
        if prev_row['rsi'] < rsi_low and row['rsi'] >= rsi_low:
            signal_price = row['close']
            entry_price = signal_price * (1 + limit_pct / 100)
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
            exit_type = None

            for k in range(fill_idx + 1, len(df)):
                bar = df.iloc[k]
                prev_bar = df.iloc[k-1]

                if bar['low'] <= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['high'] >= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break
                if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                    if prev_bar['rsi'] > rsi_high and bar['rsi'] <= rsi_high:
                        exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                        break

            if exit_idx is None:
                i += 1
                continue

            pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
            equity += equity * (pnl_pct / 100)
            trades.append({'exit_type': exit_type, 'pnl_pct': pnl_pct, 'duration': exit_idx - fill_idx})
            equity_curve.append(equity)
            i = exit_idx + 1
            continue

        # SHORT: RSI crosses DOWN through rsi_high
        if prev_row['rsi'] > rsi_high and row['rsi'] <= rsi_high:
            signal_price = row['close']
            entry_price = signal_price * (1 - limit_pct / 100)
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
            exit_type = None

            for k in range(fill_idx + 1, len(df)):
                bar = df.iloc[k]
                prev_bar = df.iloc[k-1]

                if bar['high'] >= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['low'] <= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break
                if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                    if prev_bar['rsi'] < rsi_low and bar['rsi'] >= rsi_low:
                        exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                        break

            if exit_idx is None:
                i += 1
                continue

            pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
            equity += equity * (pnl_pct / 100)
            trades.append({'exit_type': exit_type, 'pnl_pct': pnl_pct, 'duration': exit_idx - fill_idx})
            equity_curve.append(equity)
            i = exit_idx + 1
            continue

        i += 1

    if len(trades) < 2:
        return None

    df_t = pd.DataFrame(trades)
    ret = ((equity_curve[-1] - 100) / 100) * 100
    eq = pd.Series(equity_curve)
    dd = ((eq - eq.expanding().max()) / eq.expanding().max() * 100).min()
    wr = (df_t['pnl_pct'] > 0).sum() / len(df_t) * 100
    exit_breakdown = df_t['exit_type'].value_counts()

    return {
        'return': ret,
        'max_dd': dd,
        'return_dd': ret / abs(dd) if dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': wr,
        'avg_duration': df_t['duration'].mean(),
        'tp_rate': (exit_breakdown.get('TP', 0) / len(df_t)) * 100,
        'sl_rate': (exit_breakdown.get('SL', 0) / len(df_t)) * 100,
        'opposite_rate': (exit_breakdown.get('OPPOSITE', 0) / len(df_t)) * 100
    }

# Top 10 configs from July-Aug
top_configs = [
    (25, 65, 0.3, 2.5, 5.0, 38.72),
    (25, 65, 0.3, 3.0, 5.0, 36.26),
    (27, 65, 0.3, 2.5, 2.0, 35.32),
    (27, 65, 0.3, 3.0, 2.0, 34.12),
    (25, 65, 0.3, 2.5, 4.0, 33.16),
    (25, 65, 0.5, 2.5, 5.0, 32.87),
    (25, 65, 0.5, 2.5, 4.0, 32.39),
    (25, 65, 0.3, 3.0, 4.0, 30.71),
    (25, 65, 0.3, 2.5, 2.5, 30.39),
    (30, 65, 0.3, 2.5, 5.0, 30.17),
]

print("\n" + "=" * 80)
print("TOP JULY-AUG CONFIGS TESTED ON SEP-DEC:")
print("=" * 80)

results = []
for config in top_configs:
    rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, july_aug_return = config

    result = backtest(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult)

    print(f"\n{int(rsi_low)}/{int(rsi_high)} | Limit:{limit_pct}% | SL:{sl_mult}x | TP:{tp_mult}x")
    print(f"  July-Aug: +{july_aug_return:.2f}%")

    if result:
        print(f"  Sep-Dec:  {result['return']:+.2f}% | DD: {result['max_dd']:.2f}% | R/DD: {result['return_dd']:.2f}x")
        print(f"  Trades: {result['trades']} | Win: {result['win_rate']:.1f}% | Avg Hold: {result['avg_duration']:.1f}h")
        print(f"  Exits: TP {result['tp_rate']:.1f}% | SL {result['sl_rate']:.1f}% | OPP {result['opposite_rate']:.1f}%")

        results.append({
            'config': f"{int(rsi_low)}/{int(rsi_high)}, {limit_pct}%, {sl_mult}x, {tp_mult}x",
            'july_aug_return': july_aug_return,
            'sepdec_return': result['return'],
            'sepdec_rdd': result['return_dd'],
            'sepdec_trades': result['trades'],
            'sepdec_wr': result['win_rate']
        })
    else:
        print(f"  Sep-Dec:  ❌ NO TRADES")

# Summary
print("\n" + "=" * 80)
print("CONSISTENCY CHECK:")
print("=" * 80)

if len(results) > 0:
    df_res = pd.DataFrame(results)

    # Count how many are profitable on both periods
    both_profitable = ((df_res['july_aug_return'] > 0) & (df_res['sepdec_return'] > 0)).sum()

    print(f"\n✅ Configs profitable on BOTH periods: {both_profitable} out of {len(results)}")

    if both_profitable > 0:
        print("\nConfigs that work on BOTH periods:")
        for idx, row in df_res[df_res['sepdec_return'] > 0].iterrows():
            print(f"\n  {row['config']}")
            print(f"    July-Aug: +{row['july_aug_return']:.2f}%")
            print(f"    Sep-Dec:  {row['sepdec_return']:+.2f}% (R/DD: {row['sepdec_rdd']:.2f}x)")
            print(f"    Avg return: {(row['july_aug_return'] + row['sepdec_return']) / 2:+.2f}%")

    if both_profitable == 0:
        print("\n❌ NO CONFIGS WORK ON BOTH PERIODS")
        print("   Still overfitting - just to July-Aug instead of Sep-Dec")
    elif both_profitable < 3:
        print("\n⚠️  ONLY A FEW CONFIGS WORK ON BOTH")
        print("   Limited robustness - market-dependent")
    else:
        print("\n✅ MULTIPLE CONFIGS WORK ON BOTH PERIODS")
        print("   This suggests some robustness")

print("\n" + "=" * 80)
