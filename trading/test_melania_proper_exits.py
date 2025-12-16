"""
Test MELANIA with PROPER exit logic:
- SL: Stop loss hit
- TP: Take profit hit
- REVERSION: Opposite RSI signal appears (mean reversion complete)

NO arbitrary time exits!
"""

import pandas as pd
import numpy as np
from itertools import product

print("=" * 80)
print("MELANIA-USDT: Proper Exit Logic Test (July-Aug 2025)")
print("Exits: SL, TP, or Opposite Signal ONLY (no time exits)")
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

# Parameter grid
param_grid = {
    'rsi_low': [25, 27, 30],
    'rsi_high': [65, 68, 70],
    'limit_pct': [0.5, 1.0, 1.5],
    'sl_mult': [1.0, 1.5, 2.0],
    'tp_mult': [1.0, 1.5, 2.0],
    'exit_rsi': [50, 55, 60]  # RSI level for reversion exit
}

def backtest_proper_exits(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, exit_rsi):
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

            # Look for exit: SL, TP, or RSI crosses back above exit_rsi
            exit_idx = None
            exit_price = None
            exit_type = None

            for k in range(fill_idx + 1, len(df)):  # No max hold!
                bar = df.iloc[k]

                # Check SL first (highest priority)
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

                # Check reversion (RSI crosses back above exit level)
                if not pd.isna(bar['rsi']) and bar['rsi'] > exit_rsi:
                    exit_idx = k
                    exit_price = bar['close']
                    exit_type = 'REVERSION'
                    break

                # Also exit on opposite signal (RSI > rsi_high = overbought)
                if not pd.isna(bar['rsi']) and bar['rsi'] > rsi_high:
                    exit_idx = k
                    exit_price = bar['close']
                    exit_type = 'OPPOSITE'
                    break

            if exit_idx is None:
                # Reached end of data without exit
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

        elif direction == 'SHORT':
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

            # Look for exit: SL, TP, or RSI crosses back below exit_rsi
            exit_idx = None
            exit_price = None
            exit_type = None

            for k in range(fill_idx + 1, len(df)):  # No max hold!
                bar = df.iloc[k]

                # Check SL first
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

                # Check reversion (RSI crosses back below exit level)
                if not pd.isna(bar['rsi']) and bar['rsi'] < exit_rsi:
                    exit_idx = k
                    exit_price = bar['close']
                    exit_type = 'REVERSION'
                    break

                # Also exit on opposite signal (RSI < rsi_low = oversold)
                if not pd.isna(bar['rsi']) and bar['rsi'] < rsi_low:
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

        else:
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
        'reversion_rate': (exit_breakdown.get('REVERSION', 0) / len(df_t)) * 100,
        'opposite_rate': (exit_breakdown.get('OPPOSITE', 0) / len(df_t)) * 100,
        'rsi_low': rsi_low,
        'rsi_high': rsi_high,
        'limit_pct': limit_pct,
        'sl_mult': sl_mult,
        'tp_mult': tp_mult,
        'exit_rsi': exit_rsi
    }

# Test all combinations
print(f"\nTesting {np.prod([len(v) for v in param_grid.values()])} combinations...")

results = []
for params in product(*param_grid.values()):
    rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, exit_rsi = params
    result = backtest_proper_exits(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, exit_rsi)
    if result is not None:
        results.append(result)

if len(results) == 0:
    print("\n❌ ALL COMBINATIONS FAILED")
else:
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('return', ascending=False)

    profitable = (df_results['return'] > 0).sum()
    print(f"\n✅ Found {len(df_results)} valid configurations")
    print(f"📊 {profitable} out of {len(df_results)} were profitable ({profitable/len(df_results)*100:.1f}%)")

    # Show top 10
    print("\n" + "=" * 80)
    print("TOP 10 PERFORMERS (PROPER EXITS):")
    print("=" * 80)

    for idx, row in df_results.head(10).iterrows():
        print(f"\n{int(row['rsi_low'])}/{int(row['rsi_high'])} | Limit:{row['limit_pct']}% | "
              f"SL:{row['sl_mult']}x | TP:{row['tp_mult']}x | Exit RSI:{int(row['exit_rsi'])}")
        print(f"  Return: {row['return']:+.2f}% | DD: {row['max_dd']:.2f}% | R/DD: {row['return_dd']:.2f}x")
        print(f"  Trades: {int(row['trades'])} | Win: {row['win_rate']:.1f}% | Avg Duration: {row['avg_duration']:.1f}h")
        print(f"  Exits: TP {row['tp_rate']:.1f}% | SL {row['sl_rate']:.1f}% | "
              f"REV {row['reversion_rate']:.1f}% | OPP {row['opposite_rate']:.1f}%")

    # Compare to old time-based exits
    print("\n" + "=" * 80)
    print("COMPARISON: Proper Exits vs Time-Based Exits")
    print("=" * 80)

    best = df_results.iloc[0]
    print(f"\nBest config with PROPER exits:")
    print(f"  Params: {int(best['rsi_low'])}/{int(best['rsi_high'])}, {best['limit_pct']}%, "
          f"{best['sl_mult']}x, {best['tp_mult']}x, exit RSI {int(best['exit_rsi'])}")
    print(f"  Return: {best['return']:+.2f}% | Win: {best['win_rate']:.1f}% | Trades: {int(best['trades'])}")
    print(f"  Avg hold: {best['avg_duration']:.1f}h")

    print(f"\nBest config with TIME exits (old method):")
    print(f"  Params: 30/65, 0.5%, 2.0x, 1.0x, 5h max")
    print(f"  Return: +10.56% | Win: 58.9% | Trades: 56")
    print(f"  Avg hold: 3.6h")

    print(f"\n📊 Improvement: {best['return'] - 10.56:+.2f}% return")

    # Test Sep-Dec training params with proper exits
    print("\n" + "=" * 80)
    print("Sep-Dec Training Params with PROPER exits:")
    print("=" * 80)

    # Load Sep-Dec data
    df_sepdec = pd.read_csv('bingx-trading-bot/trading/melania_usdt_90d_1h.csv', parse_dates=['timestamp'])
    df_sepdec = df_sepdec.sort_values('timestamp').reset_index(drop=True)
    df_sepdec = df_sepdec[(df_sepdec['timestamp'] >= '2025-09-15') & (df_sepdec['timestamp'] < '2025-12-08')].reset_index(drop=True)

    # Calculate indicators
    delta = df_sepdec['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df_sepdec['rsi'] = 100 - (100 / (1 + rs))

    df_sepdec['tr'] = np.maximum(
        df_sepdec['high'] - df_sepdec['low'],
        np.maximum(
            abs(df_sepdec['high'] - df_sepdec['close'].shift(1)),
            abs(df_sepdec['low'] - df_sepdec['close'].shift(1))
        )
    )
    df_sepdec['atr'] = df_sepdec['tr'].rolling(14).mean()

    # Test training params: 27/65, 1.5%, 1.5x, 2.0x, exit_rsi=55
    result_sepdec = backtest_proper_exits(df_sepdec, 27, 65, 1.5, 1.5, 2.0, 55)

    if result_sepdec:
        print(f"Params: 27/65, 1.5%, 1.5x SL, 2.0x TP, exit RSI 55")
        print(f"Return: {result_sepdec['return']:+.2f}% | Win: {result_sepdec['win_rate']:.1f}% | "
              f"Trades: {result_sepdec['trades']}")
        print(f"R/DD: {result_sepdec['return_dd']:.2f}x | Max DD: {result_sepdec['max_dd']:.2f}%")
        print(f"Exits: TP {result_sepdec['tp_rate']:.1f}% | SL {result_sepdec['sl_rate']:.1f}% | "
              f"REV {result_sepdec['reversion_rate']:.1f}% | OPP {result_sepdec['opposite_rate']:.1f}%")

        print(f"\nOriginal optimization result (with time exits): +71.60%, 75% win")
        print(f"Proper exits: {result_sepdec['return']:+.2f}%, {result_sepdec['win_rate']:.1f}% win")
        print(f"Difference: {result_sepdec['return'] - 71.60:+.2f}%")

print("\n" + "=" * 80)
