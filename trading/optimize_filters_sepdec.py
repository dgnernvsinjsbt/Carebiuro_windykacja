#!/usr/bin/env python3
"""Find optimal filters by analyzing Sept-Dec winners vs losers"""
import pandas as pd
import numpy as np
from itertools import product

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
df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100
df['ret_4h'] = (df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100
df['ret_4h_abs'] = abs(df['ret_4h'])
df['avg_move_size'] = df['ret_4h_abs'].rolling(96).mean()

# Baseline run to get all trades
rsi_ob = 65
limit_offset_atr = 0.1
sl_atr = 1.2
tp_atr = 3.0
min_move = 0.8

current_risk = 0.12
equity = 100.0
trades = []
position = None
pending_order = None

for i in range(300, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']) or pd.isna(row['avg_move_size']):
        continue

    if pending_order:
        if i - pending_order['signal_bar'] > 8:
            pending_order = None
        elif row['high'] >= pending_order['limit_price']:
            position = {
                'entry': pending_order['limit_price'],
                'sl_price': pending_order['sl_price'],
                'tp_price': pending_order['tp_price'],
                'size': pending_order['size'],
                'entry_bar': i,
                'signal_bar': pending_order['signal_bar']
            }
            pending_order = None

    if position:
        pnl_pct = None

        if row['high'] >= position['sl_price']:
            pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
        elif row['low'] <= position['tp_price']:
            pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100

        if pnl_pct is not None:
            pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
            equity += pnl_dollar

            signal_row = df.iloc[position['signal_bar']]
            trades.append({
                'signal_time': signal_row['timestamp'],
                'pnl_dollar': pnl_dollar,
                'signal_rsi': signal_row['rsi'],
                'signal_ret20': signal_row['ret_20'],
                'signal_move_size': signal_row['avg_move_size'],
                'signal_atr_pct': (signal_row['atr'] / signal_row['close']) * 100
            })

            won = pnl_pct > 0
            current_risk = min(current_risk * 1.5, 0.30) if won else max(current_risk * 0.5, 0.02)
            position = None

    if not position and not pending_order and i > 0:
        prev_row = df.iloc[i-1]

        if pd.isna(prev_row['rsi']):
            continue

        if prev_row['rsi'] > rsi_ob and row['rsi'] <= rsi_ob:
            if row['avg_move_size'] >= min_move:
                signal_price = row['close']
                atr = row['atr']

                limit_price = signal_price + (atr * limit_offset_atr)
                sl_price = limit_price + (atr * sl_atr)
                tp_price = limit_price - (atr * tp_atr)

                sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                size = (equity * current_risk) / (sl_dist / 100)

                pending_order = {
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'signal_bar': i
                }

trades_df = pd.DataFrame(trades)
trades_df['signal_time'] = pd.to_datetime(trades_df['signal_time'])
trades_df['month'] = trades_df['signal_time'].dt.to_period('M')
trades_df['winner'] = trades_df['pnl_dollar'] > 0

# Sept-Dec only
sepdec = trades_df[trades_df['month'].isin(['2025-09', '2025-10', '2025-11', '2025-12'])].copy()

winners = sepdec[sepdec['winner']]
losers = sepdec[~sepdec['winner']]

print("=" * 80)
print("SEPT-DEC WINNERS vs LOSERS ANALYSIS")
print("=" * 80)
print(f"\nTotal Sept-Dec: {len(sepdec)} trades")
print(f"Winners: {len(winners)} (${winners['pnl_dollar'].sum():+.2f})")
print(f"Losers: {len(losers)} (${losers['pnl_dollar'].sum():+.2f})")

print("\n" + "=" * 80)
print("CHARACTERISTICS")
print("=" * 80)

print(f"\nRSI: Winners {winners['signal_rsi'].mean():.1f} vs Losers {losers['signal_rsi'].mean():.1f}")
print(f"Ret20: Winners {winners['signal_ret20'].mean():+.1f}% vs Losers {losers['signal_ret20'].mean():+.1f}%")
print(f"Move: Winners {winners['signal_move_size'].mean():.2f}% vs Losers {losers['signal_move_size'].mean():.2f}%")
print(f"ATR%: Winners {winners['signal_atr_pct'].mean():.3f}% vs Losers {losers['signal_atr_pct'].mean():.3f}%")

# Grid search for optimal filters
print("\n" + "=" * 80)
print("TESTING FILTER COMBINATIONS")
print("=" * 80)

param_grid = {
    'min_ret20': [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
    'min_rsi': [55, 58, 60, 62, 65],
    'max_rsi': [65, 68, 70],
    'min_move': [0.8, 1.0, 1.2, 1.5]
}

def test_filters(min_ret20, min_rsi, max_rsi, min_move_filter):
    current_risk = 0.12
    equity = 100.0
    trades = []
    position = None
    pending_order = None

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']) or pd.isna(row['avg_move_size']):
            continue

        if pending_order:
            if i - pending_order['signal_bar'] > 8:
                pending_order = None
            elif row['high'] >= pending_order['limit_price']:
                position = {
                    'entry': pending_order['limit_price'],
                    'sl_price': pending_order['sl_price'],
                    'tp_price': pending_order['tp_price'],
                    'size': pending_order['size'],
                    'entry_bar': i,
                    'signal_bar': pending_order['signal_bar']
                }
                pending_order = None

        if position:
            pnl_pct = None

            if row['high'] >= position['sl_price']:
                pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
            elif row['low'] <= position['tp_price']:
                pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100

            if pnl_pct is not None:
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl_dollar

                signal_row = df.iloc[position['signal_bar']]
                trades.append({
                    'signal_time': signal_row['timestamp'],
                    'pnl_dollar': pnl_dollar
                })

                won = pnl_pct > 0
                current_risk = min(current_risk * 1.5, 0.30) if won else max(current_risk * 0.5, 0.02)
                position = None

        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]

            # FILTERS
            if row['ret_20'] < min_ret20:
                continue
            if pd.isna(prev_row['rsi']):
                continue
            if row['avg_move_size'] < min_move_filter:
                continue

            if prev_row['rsi'] > max_rsi and row['rsi'] <= max_rsi:
                if prev_row['rsi'] >= min_rsi:  # RSI range filter
                    signal_price = row['close']
                    atr = row['atr']

                    limit_price = signal_price + (atr * limit_offset_atr)
                    sl_price = limit_price + (atr * sl_atr)
                    tp_price = limit_price - (atr * tp_atr)

                    sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                    size = (equity * current_risk) / (sl_dist / 100)

                    pending_order = {
                        'limit_price': limit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size,
                        'signal_bar': i
                    }

    if len(trades) < 20:  # Need minimum sample
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

    if not (oct > 0 and nov > 0 and dec > 0):
        return None

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

    return {
        'min_ret20': min_ret20,
        'min_rsi': min_rsi,
        'max_rsi': max_rsi,
        'min_move': min_move_filter,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': len(trades_df),
        'oct': oct,
        'nov': nov,
        'dec': dec
    }

results = []
total = len(list(product(*param_grid.values())))
print(f"\nTesting {total} combinations...")

for i, (ret20, min_rsi, max_rsi, move) in enumerate(product(*param_grid.values())):
    if min_rsi >= max_rsi:
        continue

    result = test_filters(ret20, min_rsi, max_rsi, move)
    if result:
        results.append(result)

    if i % 50 == 0:
        print(f"Progress: {i}/{total} | Found {len(results)} valid configs")

results.sort(key=lambda x: x['return_dd'], reverse=True)

print(f"\n✅ Found {len(results)} configs with Oct-Dec all profitable\n")

print("=" * 80)
print("TOP 10 CONFIGS")
print("=" * 80)

for i, r in enumerate(results[:10], 1):
    print(f"\n#{i}: R/DD = {r['return_dd']:.2f}x | Ret = {r['return']:+.1f}% | DD = {r['max_dd']:.2f}%")
    print(f"    Trades: {r['trades']} | Ret20≥{r['min_ret20']}% | RSI {r['min_rsi']}-{r['max_rsi']} | Move≥{r['min_move']}%")
    print(f"    Oct: ${r['oct']:+.2f} | Nov: ${r['nov']:+.2f} | Dec: ${r['dec']:+.2f}")

if results:
    best = results[0]
    print("\n" + "=" * 80)
    print("🏆 BEST CONFIG")
    print("=" * 80)
    print(f"\nFilters:")
    print(f"  Min Momentum (ret_20): {best['min_ret20']}%")
    print(f"  RSI Range: {best['min_rsi']}-{best['max_rsi']}")
    print(f"  Min Move Size: {best['min_move']}%")
    print(f"\nPerformance:")
    print(f"  Return/DD: {best['return_dd']:.2f}x")
    print(f"  Return: {best['return']:+.1f}%")
    print(f"  Max DD: {best['max_dd']:.2f}%")
    print(f"  Trades: {best['trades']}")
    print(f"\nMonthly:")
    print(f"  Oct: ${best['oct']:+.2f} ✅")
    print(f"  Nov: ${best['nov']:+.2f} ✅")
    print(f"  Dec: ${best['dec']:+.2f} ✅")

print("\n" + "=" * 80)
