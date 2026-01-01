"""
1. Test best configs on Dec 8-15 (the terrible week)
2. Optimize on FULL July-Dec dataset (all 5 months combined)
"""

import pandas as pd
import numpy as np
from itertools import product

print("=" * 80)
print("PART 1: Testing Best Configs on Dec 8-15")
print("=" * 80)

# Load Dec 8-15 data
df_dec = pd.read_csv('bingx-trading-bot/trading/melania_usdt_90d_1h.csv', parse_dates=['timestamp'])
df_dec = df_dec.sort_values('timestamp').reset_index(drop=True)
df_dec = df_dec[(df_dec['timestamp'] >= '2025-12-08') & (df_dec['timestamp'] < '2025-12-16')].reset_index(drop=True)

print(f"\nDec 8-15 Data: {len(df_dec)} bars")

# Calculate indicators
def calc_indicators(df):
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ))
    df['atr'] = df['tr'].rolling(14).mean()
    return df

df_dec = calc_indicators(df_dec)

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
            trades.append({'exit_type': exit_type, 'pnl_pct': pnl_pct})
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
            trades.append({'exit_type': exit_type, 'pnl_pct': pnl_pct})
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

    return {
        'return': ret,
        'max_dd': dd,
        'return_dd': ret / abs(dd) if dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': wr
    }

# Test top 3 configs on Dec 8-15
top_configs = [
    (25, 65, 0.3, 2.5, 2.5),
    (27, 65, 0.3, 2.5, 2.0),
    (27, 65, 0.3, 3.0, 2.0)
]

for config in top_configs:
    rsi_low, rsi_high, limit_pct, sl_mult, tp_mult = config
    result = backtest(df_dec, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult)

    print(f"\n{int(rsi_low)}/{int(rsi_high)} | {limit_pct}% | SL:{sl_mult}x | TP:{tp_mult}x")
    if result:
        print(f"  Return: {result['return']:+.2f}% | DD: {result['max_dd']:.2f}% | Trades: {result['trades']} | Win: {result['win_rate']:.1f}%")
    else:
        print(f"  ❌ NO TRADES")

# PART 2: Optimize on FULL July-Dec dataset
print("\n" + "=" * 80)
print("PART 2: Optimizing on FULL July-Dec 2025 Dataset")
print("=" * 80)

# Load and combine July-Aug + Sep-Dec data
df_july = pd.read_csv('trading/melania_usdt_july_aug_2025_1h.csv', parse_dates=['timestamp'])
df_sepdec = pd.read_csv('bingx-trading-bot/trading/melania_usdt_90d_1h.csv', parse_dates=['timestamp'])
df_sepdec = df_sepdec[(df_sepdec['timestamp'] >= '2025-09-15') & (df_sepdec['timestamp'] < '2025-12-08')]

# Remove timezone info for concatenation
df_july['timestamp'] = pd.to_datetime(df_july['timestamp']).dt.tz_localize(None)
df_sepdec['timestamp'] = pd.to_datetime(df_sepdec['timestamp']).dt.tz_localize(None)

df_full = pd.concat([df_july, df_sepdec]).sort_values('timestamp').reset_index(drop=True)
df_full = calc_indicators(df_full)

print(f"\nCombined dataset: {len(df_full)} bars ({df_full['timestamp'].min()} to {df_full['timestamp'].max()})")
print("Testing parameter combinations...")

# Focused parameter grid based on what worked
param_grid = {
    'rsi_low': [25, 27, 30],
    'rsi_high': [65, 68, 70],
    'limit_pct': [0.3, 0.5, 0.8],
    'sl_mult': [2.0, 2.5, 3.0],
    'tp_mult': [1.5, 2.0, 2.5, 3.0]
}

results = []
for params in product(*param_grid.values()):
    rsi_low, rsi_high, limit_pct, sl_mult, tp_mult = params
    result = backtest(df_full, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult)
    if result is not None:
        results.append({
            'return': result['return'],
            'max_dd': result['max_dd'],
            'return_dd': result['return_dd'],
            'trades': result['trades'],
            'win_rate': result['win_rate'],
            'rsi_low': rsi_low,
            'rsi_high': rsi_high,
            'limit_pct': limit_pct,
            'sl_mult': sl_mult,
            'tp_mult': tp_mult
        })

df_results = pd.DataFrame(results)
df_results = df_results.sort_values('return_dd', ascending=False)

print(f"\n✅ Found {len(df_results)} valid configurations")
print(f"📊 {(df_results['return'] > 0).sum()} profitable")

print("\n" + "=" * 80)
print("TOP 10 CONFIGS (Full July-Dec Dataset, sorted by R/DD):")
print("=" * 80)

for idx, row in df_results.head(10).iterrows():
    print(f"\n{int(row['rsi_low'])}/{int(row['rsi_high'])} | Limit:{row['limit_pct']}% | "
          f"SL:{row['sl_mult']}x | TP:{row['tp_mult']}x")
    print(f"  Return: {row['return']:+.2f}% | DD: {row['max_dd']:.2f}% | R/DD: {row['return_dd']:.2f}x")
    print(f"  Trades: {int(row['trades'])} | Win: {row['win_rate']:.1f}%")

print("\n" + "=" * 80)
print("FINAL RECOMMENDATION:")
print("=" * 80)

best = df_results.iloc[0]
print(f"\nBest config for MELANIA (July-Dec 2025):")
print(f"  RSI: {int(best['rsi_low'])}/{int(best['rsi_high'])}")
print(f"  Limit: {best['limit_pct']}%")
print(f"  SL: {best['sl_mult']}x ATR")
print(f"  TP: {best['tp_mult']}x ATR")
print(f"\n  Performance:")
print(f"  Return: {best['return']:+.2f}%")
print(f"  Max DD: {best['max_dd']:.2f}%")
print(f"  R/DD: {best['return_dd']:.2f}x")
print(f"  Trades: {int(best['trades'])}")
print(f"  Win Rate: {best['win_rate']:.1f}%")

print("\n" + "=" * 80)
