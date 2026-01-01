"""
CORRECT mean reversion logic:

ENTRY:
- LONG: RSI crosses UP through rsi_low (e.g., crosses from <30 to >30)
- SHORT: RSI crosses DOWN through rsi_high (e.g., crosses from >65 to <65)

EXIT:
- SL hit, OR
- TP hit, OR
- Opposite signal (LONG exits on SHORT signal, SHORT exits on LONG signal)

Test different SL/TP/limit offset levels
"""

import pandas as pd
import numpy as np
from itertools import product

print("=" * 80)
print("MELANIA-USDT: CORRECT Mean Reversion Logic")
print("Entry: RSI cross through threshold | Exit: SL/TP/Opposite signal")
print("=" * 80)

# Load July-Aug data
df = pd.read_csv('trading/melania_usdt_july_aug_2025_1h.csv', parse_dates=['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\nJuly-Aug Data: {len(df)} bars ({df['timestamp'].min()} to {df['timestamp'].max()})")

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

# Wider parameter grid
param_grid = {
    'rsi_low': [25, 27, 30],
    'rsi_high': [65, 68, 70],
    'limit_pct': [0.3, 0.5, 0.8, 1.0, 1.5],
    'sl_mult': [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
    'tp_mult': [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
}

def backtest_correct_logic(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult):
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

        # LONG signal: RSI crosses UP through rsi_low
        if prev_row['rsi'] < rsi_low and row['rsi'] >= rsi_low:
            signal_price = row['close']
            entry_price = signal_price * (1 + limit_pct / 100)
            sl_price = entry_price - (row['atr'] * sl_mult)
            tp_price = entry_price + (row['atr'] * tp_mult)

            # Wait for fill (max 3 bars)
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

            # Look for exit
            exit_idx = None
            exit_price = None
            exit_type = None

            for k in range(fill_idx + 1, len(df)):
                bar = df.iloc[k]
                prev_bar = df.iloc[k-1]

                # Check SL first
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

                # Check opposite signal: RSI crosses DOWN through rsi_high
                if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                    if prev_bar['rsi'] > rsi_high and bar['rsi'] <= rsi_high:
                        exit_idx = k
                        exit_price = bar['close']
                        exit_type = 'OPPOSITE'
                        break

            if exit_idx is None:
                i += 1
                continue

            pnl_pct = ((exit_price - entry_price) / entry_price) * 100 - 0.10
            equity += equity * (pnl_pct / 100)

            trades.append({
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'duration': exit_idx - fill_idx
            })

            equity_curve.append(equity)
            i = exit_idx + 1
            continue

        # SHORT signal: RSI crosses DOWN through rsi_high
        if prev_row['rsi'] > rsi_high and row['rsi'] <= rsi_high:
            signal_price = row['close']
            entry_price = signal_price * (1 - limit_pct / 100)
            sl_price = entry_price + (row['atr'] * sl_mult)
            tp_price = entry_price - (row['atr'] * tp_mult)

            # Wait for fill
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

            # Look for exit
            exit_idx = None
            exit_price = None
            exit_type = None

            for k in range(fill_idx + 1, len(df)):
                bar = df.iloc[k]
                prev_bar = df.iloc[k-1]

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

                # Check opposite signal: RSI crosses UP through rsi_low
                if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                    if prev_bar['rsi'] < rsi_low and bar['rsi'] >= rsi_low:
                        exit_idx = k
                        exit_price = bar['close']
                        exit_type = 'OPPOSITE'
                        break

            if exit_idx is None:
                i += 1
                continue

            pnl_pct = ((entry_price - exit_price) / entry_price) * 100 - 0.10
            equity += equity * (pnl_pct / 100)

            trades.append({
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'duration': exit_idx - fill_idx
            })

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
        'opposite_rate': (exit_breakdown.get('OPPOSITE', 0) / len(df_t)) * 100,
        'rsi_low': rsi_low,
        'rsi_high': rsi_high,
        'limit_pct': limit_pct,
        'sl_mult': sl_mult,
        'tp_mult': tp_mult
    }

# Test all combinations
total_combos = np.prod([len(v) for v in param_grid.values()])
print(f"\nTesting {total_combos} combinations...")

results = []
for params in product(*param_grid.values()):
    rsi_low, rsi_high, limit_pct, sl_mult, tp_mult = params
    result = backtest_correct_logic(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult)
    if result is not None:
        results.append(result)

if len(results) == 0:
    print("\n❌ ALL COMBINATIONS FAILED")
else:
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('return', ascending=False)

    profitable = (df_results['return'] > 0).sum()
    print(f"\n✅ Found {len(df_results)} valid configurations")
    print(f"📊 {profitable} profitable ({profitable/len(df_results)*100:.1f}%)")

    # Top 20
    print("\n" + "=" * 80)
    print("TOP 20 PERFORMERS (July-Aug 2025):")
    print("=" * 80)

    for idx, row in df_results.head(20).iterrows():
        print(f"\n{int(row['rsi_low'])}/{int(row['rsi_high'])} | Limit:{row['limit_pct']}% | "
              f"SL:{row['sl_mult']}x | TP:{row['tp_mult']}x")
        print(f"  Return: {row['return']:+.2f}% | DD: {row['max_dd']:.2f}% | R/DD: {row['return_dd']:.2f}x")
        print(f"  Trades: {int(row['trades'])} | Win: {row['win_rate']:.1f}% | Avg Hold: {row['avg_duration']:.1f}h")
        print(f"  Exits: TP {row['tp_rate']:.1f}% | SL {row['sl_rate']:.1f}% | OPP {row['opposite_rate']:.1f}%")

    # Save results
    df_results.to_csv('melania_correct_logic_results.csv', index=False)
    print(f"\n📁 Full results saved to melania_correct_logic_results.csv")

print("\n" + "=" * 80)
