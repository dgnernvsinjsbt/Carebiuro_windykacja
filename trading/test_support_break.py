#!/usr/bin/env python3
"""Test support break entry after extreme RSI"""
import pandas as pd
import numpy as np

df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

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

# Filter to Oct-Dec only
df = df[df['timestamp'] >= '2025-10-01'].copy().reset_index(drop=True)

def find_swing_low(df, idx, lookback):
    """Find swing low in last N bars"""
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['low'].min()

def find_swing_high(df, start_idx, end_idx):
    """Find swing high between two indices"""
    return df.iloc[start_idx:end_idx+1]['high'].max()

def test(rsi_trigger, lookback, tp_pct):
    equity = 100.0
    trades = []

    armed = False
    signal_idx = None
    swing_low = None

    for i in range(lookback, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']):
            continue

        # Check if RSI triggered
        if row['rsi'] > rsi_trigger:
            # New signal - replace old setup if exists
            armed = True
            signal_idx = i
            swing_low = find_swing_low(df, i, lookback)

        # If armed, wait for break below swing low
        if armed and swing_low is not None:
            if row['low'] < swing_low:
                # BREAK! Enter SHORT
                entry_price = row['close']

                # SL = swing high between signal and now
                swing_high = find_swing_high(df, signal_idx, i)
                sl_price = swing_high

                tp_price = entry_price * (1 - tp_pct / 100)

                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct <= 0 or sl_dist_pct > 10:  # Skip if SL invalid
                    armed = False
                    continue

                size = (equity * 0.05) / (sl_dist_pct / 100)  # Risk 5%

                # Find exit
                hit_sl = False
                hit_tp = False
                exit_bar = None

                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]

                    if future_row['high'] >= sl_price:
                        hit_sl = True
                        exit_bar = j
                        break
                    elif future_row['low'] <= tp_price:
                        hit_tp = True
                        exit_bar = j
                        break

                if hit_sl:
                    pnl_pct = -sl_dist_pct
                    exit_reason = 'SL'
                elif hit_tp:
                    pnl_pct = tp_pct
                    exit_reason = 'TP'
                else:
                    continue  # Trade still open

                pnl_dollar = size * (pnl_pct / 100) - size * 0.001
                equity += pnl_dollar

                trades.append({
                    'signal_time': df.iloc[signal_idx]['timestamp'],
                    'entry_time': row['timestamp'],
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'exit_reason': exit_reason,
                    'pnl_dollar': pnl_dollar,
                    'pnl_pct': pnl_pct,
                    'sl_dist_pct': sl_dist_pct,
                    'bars_to_entry': i - signal_idx,
                    'bars_held': exit_bar - i if exit_bar else 0
                })

                armed = False  # Reset

    if len(trades) < 3:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df['signal_time'] = pd.to_datetime(trades_df['signal_time'])
    trades_df['month'] = trades_df['signal_time'].dt.to_period('M')

    monthly_pnl = {}
    for month in trades_df['month'].unique():
        monthly_pnl[str(month)] = trades_df[trades_df['month'] == month]['pnl_dollar'].sum()

    oct = monthly_pnl.get('2025-10', 0)
    nov = monthly_pnl.get('2025-11', 0)
    dec = monthly_pnl.get('2025-12', 0)

    total_return = ((equity - 100) / 100) * 100

    equity_curve = [100.0]
    running_equity = 100.0
    for pnl in trades_df['pnl_dollar']:
        running_equity += pnl
        equity_curve.append(running_equity)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = trades_df[trades_df['pnl_dollar'] > 0]
    win_rate = len(winners) / len(trades_df) * 100

    avg_sl = trades_df['sl_dist_pct'].mean()
    tp_rate = len(trades_df[trades_df['exit_reason'] == 'TP']) / len(trades_df) * 100
    avg_bars_to_entry = trades_df['bars_to_entry'].mean()

    return {
        'rsi': rsi_trigger,
        'lookback': lookback,
        'tp': tp_pct,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'avg_sl': avg_sl,
        'avg_bars_to_entry': avg_bars_to_entry,
        'oct': oct,
        'nov': nov,
        'dec': dec,
        'oct_dec_ok': oct > 0 and nov > 0 and dec > 0
    }

print("=" * 80)
print("SUPPORT BREAK STRATEGY (Oct-Dec 2025)")
print("Logic: RSI >X → find swing low → wait for break → SL at swing high")
print("=" * 80)

configs = [
    (70, 10, 5),
    (72, 10, 5),
    (75, 10, 5),
    (72, 5, 5),
    (72, 15, 5),
    (72, 20, 5),
    (72, 10, 4),
    (72, 10, 6),
    (72, 10, 7),
]

results = []
for rsi_t, lb, tp in configs:
    r = test(rsi_t, lb, tp)
    if r:
        results.append(r)
        status = "✅" if r['oct_dec_ok'] else "❌"
        print(f"\nRSI>{rsi_t} Lookback={lb} TP={tp}% {status}")
        print(f"  R/DD: {r['return_dd']:5.2f}x | Ret: {r['return']:+6.1f}% | DD: {r['max_dd']:6.2f}%")
        print(f"  Trades: {r['trades']:2d} | Win: {r['win_rate']:5.1f}% | TP: {r['tp_rate']:5.1f}%")
        print(f"  Avg SL: {r['avg_sl']:.2f}% | Bars to entry: {r['avg_bars_to_entry']:.1f}")
        print(f"  Oct: ${r['oct']:+5.2f} | Nov: ${r['nov']:+5.2f} | Dec: ${r['dec']:+6.2f}")

if results:
    results.sort(key=lambda x: x['return_dd'], reverse=True)

    print("\n" + "=" * 80)
    print("TOP CONFIGS BY R/DD")
    print("=" * 80)

    for i, r in enumerate(results[:5], 1):
        status = "✅" if r['oct_dec_ok'] else "❌"
        print(f"\n#{i} {status} RSI>{r['rsi']} LB={r['lookback']} TP={r['tp']}%")
        print(f"    R/DD: {r['return_dd']:.2f}x | Ret: {r['return']:+.1f}% | Trades: {r['trades']}")
        print(f"    Oct: ${r['oct']:+.2f} | Nov: ${r['nov']:+.2f} | Dec: ${r['dec']:+.2f}")

    valid = [r for r in results if r['oct_dec_ok']]
    if valid:
        best = valid[0]
        print("\n" + "=" * 80)
        print("BEST WITH OCT-DEC ALL PROFITABLE")
        print("=" * 80)
        print(f"RSI > {best['rsi']} | Lookback = {best['lookback']} | TP = {best['tp']}%")
        print(f"R/DD: {best['return_dd']:.2f}x | Return: {best['return']:+.1f}%")
        print(f"Win Rate: {best['win_rate']:.1f}% | TP Rate: {best['tp_rate']:.1f}%")
        print(f"Avg SL: {best['avg_sl']:.2f}% | Avg bars to entry: {best['avg_bars_to_entry']:.1f}")
        print(f"Oct: ${best['oct']:+.2f} | Nov: ${best['nov']:+.2f} | Dec: ${best['dec']:+.2f}")

print("\n" + "=" * 80)
