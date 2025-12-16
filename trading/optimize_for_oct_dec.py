#!/usr/bin/env python3
"""
Optimize for Oct-Dec profitability (like LBank)
Target: All 3 months profitable, max Return/DD
"""
import pandas as pd
import numpy as np
from itertools import product

df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# Indicators
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

def backtest(params):
    rsi_ob = params['rsi_overbought']
    sl_atr = params['stop_loss_atr']
    tp_atr = params['take_profit_atr']
    min_move = params['min_move_size']
    min_momentum = params['min_ret_20']

    current_risk = 0.12
    min_risk = 0.02
    max_risk = 0.30

    equity = 100.0
    equity_curve = [equity]
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
                position = {'entry': pending_order['limit_price'], 'sl_price': pending_order['sl_price'],
                           'tp_price': pending_order['tp_price'], 'size': pending_order['size'],
                           'entry_bar': i}
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
                equity_curve.append(equity)

                trades.append({
                    'pnl_dollar': pnl_dollar,
                    'entry_time': df.iloc[position['entry_bar']]['timestamp']
                })

                won = pnl_pct > 0
                current_risk = min(current_risk * 1.5, max_risk) if won else max(current_risk * 0.5, min_risk)
                position = None

        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]

            if row['ret_20'] <= min_momentum or pd.isna(prev_row['rsi']):
                continue

            if prev_row['rsi'] > rsi_ob and row['rsi'] <= rsi_ob:
                if row['avg_move_size'] >= min_move:
                    signal_price = row['close']
                    atr = row['atr']
                    limit_price = signal_price + (atr * 0.1)
                    sl_price = limit_price + (atr * sl_atr)
                    tp_price = limit_price - (atr * tp_atr)
                    sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                    size = (equity * current_risk) / (sl_dist / 100)

                    pending_order = {'limit_price': limit_price, 'sl_price': sl_price,
                                   'tp_price': tp_price, 'size': size, 'signal_bar': i}

    if len(trades) < 50:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')

    # Calculate monthly P&L
    monthly_pnl = {}
    for month in trades_df['month'].unique():
        month_pnl = trades_df[trades_df['month'] == month]['pnl_dollar'].sum()
        monthly_pnl[str(month)] = month_pnl

    # Check if Oct, Nov, Dec are ALL profitable
    oct_profit = monthly_pnl.get('2025-10', 0) > 0
    nov_profit = monthly_pnl.get('2025-11', 0) > 0
    dec_profit = monthly_pnl.get('2025-12', 0) > 0

    if not (oct_profit and nov_profit and dec_profit):
        return None  # Reject if any of Oct-Dec is not profitable

    total_return = ((equity - 100) / 100) * 100
    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    if max_dd == 0:
        return None

    return_dd = total_return / abs(max_dd)

    return {
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': len(trades),
        'monthly_pnl': monthly_pnl,
        'params': params
    }

print("=" * 70)
print("OPTIMIZING FOR OCT-DEC PROFITABILITY")
print("Requirement: ALL of Oct, Nov, Dec must be profitable")
print("=" * 70)

# Expand parameter grid
param_grid = {
    'rsi_overbought': [62, 65, 68],
    'stop_loss_atr': [1.5, 2.0, 2.5, 3.0],  # Even wider
    'take_profit_atr': [3.0, 4.0, 5.0, 6.0],  # Let winners run more
    'min_move_size': [0.8, 1.0, 1.2, 1.5],  # Stricter
    'min_ret_20': [0.5, 1.0, 1.5, 2.0]  # Range of momentum
}

total_combos = len(list(product(*param_grid.values())))
print(f"\nTesting {total_combos} combinations...")
print()

results = []

for i, values in enumerate(product(*param_grid.values())):
    params = dict(zip(param_grid.keys(), values))
    result = backtest(params)

    if result:
        results.append(result)

    if i % 100 == 0:
        print(f"Progress: {i}/{total_combos} | Found {len(results)} configs with Oct-Dec all profitable")

print(f"\n✅ Found {len(results)} configurations where Oct-Dec are ALL profitable")

if not results:
    print("\n❌ No configurations found! Oct-Dec profitability is very hard constraint.")
else:
    results.sort(key=lambda x: x['return_dd'], reverse=True)

    print("\n" + "=" * 70)
    print("TOP 10 CONFIGURATIONS (Oct-Dec all profitable)")
    print("=" * 70)

    for i, r in enumerate(results[:10], 1):
        print(f"\n#{i}: Return/DD = {r['return_dd']:.2f}x")
        print(f"   Return: {r['return']:+.1f}%")
        print(f"   Max DD: {r['max_dd']:.2f}%")
        print(f"   Trades: {r['trades']}")
        print(f"   Parameters:")
        print(f"     RSI: {r['params']['rsi_overbought']}")
        print(f"     SL: {r['params']['stop_loss_atr']:.1f} ATR")
        print(f"     TP: {r['params']['take_profit_atr']:.1f} ATR")
        print(f"     Move: {r['params']['min_move_size']:.1f}%")
        print(f"     Momentum: {r['params']['min_ret_20']:.1f}%")
        print(f"   Monthly P&L:")
        for month in ['2025-10', '2025-11', '2025-12']:
            pnl = r['monthly_pnl'].get(month, 0)
            print(f"     {month}: ${pnl:+8.2f}")

    print("\n" + "=" * 70)
    print("BEST CONFIGURATION")
    print("=" * 70)

    best = results[0]
    print(f"\nReturn: {best['return']:+.1f}%")
    print(f"Max DD: {best['max_dd']:.2f}%")
    print(f"Return/DD: {best['return_dd']:.2f}x")
    print(f"Trades: {best['trades']}")

    print("\nOptimal Parameters:")
    print(f"  rsi_overbought: {best['params']['rsi_overbought']}")
    print(f"  stop_loss_atr: {best['params']['stop_loss_atr']}")
    print(f"  take_profit_atr: {best['params']['take_profit_atr']}")
    print(f"  min_move_size: {best['params']['min_move_size']}")
    print(f"  min_ret_20: {best['params']['min_ret_20']}")

    print("\nAll Monthly P&L:")
    for month, pnl in sorted(best['monthly_pnl'].items()):
        print(f"  {month}: ${pnl:+8.2f}")

    print("\n" + "=" * 70)
