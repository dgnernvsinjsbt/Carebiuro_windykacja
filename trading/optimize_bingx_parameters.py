#!/usr/bin/env python3
"""
Optimize MELANIA strategy parameters for BingX
Goal: ~139 trades (like LBank) with max Return/DD ratio
"""
import pandas as pd
import numpy as np
from itertools import product

# Load data
df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# Calculate base indicators
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
    """Run backtest with given parameters"""
    rsi_ob = params['rsi_overbought']
    limit_offset = params['limit_offset_atr']
    sl_atr = params['stop_loss_atr']
    tp_atr = params['take_profit_atr']
    min_move = params['min_move_size']
    min_momentum = params['min_ret_20']

    # Dynamic sizing (keep same)
    current_risk = 0.12
    min_risk = 0.02
    max_risk = 0.30
    win_mult = 1.5
    loss_mult = 0.5

    equity = 100.0
    equity_curve = [equity]
    trades = []
    position = None
    pending_order = None

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']) or pd.isna(row['avg_move_size']):
            continue

        # Check pending
        if pending_order:
            bars_waiting = i - pending_order['signal_bar']
            if bars_waiting > 8:
                pending_order = None
                continue

            if row['high'] >= pending_order['limit_price']:
                position = {
                    'entry': pending_order['limit_price'],
                    'sl_price': pending_order['sl_price'],
                    'tp_price': pending_order['tp_price'],
                    'size': pending_order['size'],
                    'entry_bar': i
                }
                pending_order = None

        # Check exit
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

                trades.append(pnl_dollar)

                won = pnl_pct > 0
                current_risk = min(current_risk * win_mult, max_risk) if won else max(current_risk * loss_mult, min_risk)

                position = None
                continue

        # Generate signals
        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]

            # STRENGTHENED momentum filter
            if row['ret_20'] <= min_momentum or pd.isna(prev_row['rsi']):
                continue

            signal_price = row['close']
            atr = row['atr']

            # SHORT only
            if prev_row['rsi'] > rsi_ob and row['rsi'] <= rsi_ob:
                # STRENGTHENED move size filter
                if row['avg_move_size'] >= min_move:
                    limit_price = signal_price + (atr * limit_offset)
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

    if not trades:
        return None

    # Calculate stats
    total_return = ((equity - 100) / 100) * 100

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    if max_dd == 0:
        return None

    return_dd = total_return / abs(max_dd)

    winners = [t for t in trades if t > 0]
    win_rate = len(winners) / len(trades) * 100

    return {
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': len(trades),
        'win_rate': win_rate,
        'params': params
    }

print("=" * 70)
print("OPTIMIZING PARAMETERS FOR BINGX")
print("Goal: ~139 trades, max Return/DD ratio")
print("=" * 70)

# Parameter grid - focus on reducing trade count and surviving chop
param_grid = {
    'rsi_overbought': [62, 65, 68],  # Tighter = fewer trades
    'limit_offset_atr': [0.1],  # Keep same
    'stop_loss_atr': [1.5, 2.0, 2.5],  # WIDER to survive chop
    'take_profit_atr': [3.0, 4.0, 5.0],  # WIDER to let winners run
    'min_move_size': [0.8, 1.0, 1.2],  # STRICTER filter
    'min_ret_20': [0, 1.0, 2.0]  # STRONGER momentum filter
}

print(f"\nTesting {len(list(product(*param_grid.values())))} combinations...")
print()

results = []

for i, values in enumerate(product(*param_grid.values())):
    params = dict(zip(param_grid.keys(), values))

    result = backtest(params)

    if result and 100 <= result['trades'] <= 180:  # Target trade count range
        results.append(result)

        if i % 20 == 0:
            print(f"Progress: {i}/{len(list(product(*param_grid.values())))} tested, {len(results)} viable configs found")

print(f"\n✅ Found {len(results)} viable configurations")

# Sort by Return/DD ratio
results.sort(key=lambda x: x['return_dd'], reverse=True)

print("\n" + "=" * 70)
print("TOP 10 CONFIGURATIONS (by Return/DD)")
print("=" * 70)

for i, r in enumerate(results[:10], 1):
    print(f"\n#{i}: Return/DD = {r['return_dd']:.2f}x")
    print(f"   Return: {r['return']:+.1f}%")
    print(f"   Max DD: {r['max_dd']:.2f}%")
    print(f"   Trades: {r['trades']}")
    print(f"   Win Rate: {r['win_rate']:.1f}%")
    print(f"   Parameters:")
    print(f"     RSI Overbought: {r['params']['rsi_overbought']}")
    print(f"     Stop Loss: {r['params']['stop_loss_atr']:.1f} ATR")
    print(f"     Take Profit: {r['params']['take_profit_atr']:.1f} ATR")
    print(f"     Min Move Size: {r['params']['min_move_size']:.1f}%")
    print(f"     Min Momentum: {r['params']['min_ret_20']:.1f}%")

if results:
    print("\n" + "=" * 70)
    print("BEST CONFIGURATION")
    print("=" * 70)

    best = results[0]

    print(f"\nReturn: {best['return']:+.1f}%")
    print(f"Max DD: {best['max_dd']:.2f}%")
    print(f"Return/DD: {best['return_dd']:.2f}x")
    print(f"Trades: {best['trades']}")
    print(f"Win Rate: {best['win_rate']:.1f}%")

    print("\nOptimal Parameters:")
    print(f"  rsi_overbought: {best['params']['rsi_overbought']}")
    print(f"  stop_loss_atr: {best['params']['stop_loss_atr']}")
    print(f"  take_profit_atr: {best['params']['take_profit_atr']}")
    print(f"  min_move_size: {best['params']['min_move_size']}")
    print(f"  min_ret_20: {best['params']['min_ret_20']}")

    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print("\nOriginal Config:")
    print("  Return/DD: 9.73x")
    print("  Trades: 218")
    print("  Return: +582.9%")
    print("  Max DD: -59.90%")

    print(f"\nOptimized Config:")
    print(f"  Return/DD: {best['return_dd']:.2f}x ({(best['return_dd']/9.73 - 1)*100:+.1f}%)")
    print(f"  Trades: {best['trades']} ({best['trades'] - 218:+d})")
    print(f"  Return: {best['return']:+.1f}% ({best['return'] - 582.9:+.1f}%)")
    print(f"  Max DD: {best['max_dd']:.2f}% ({best['max_dd'] - (-59.90):+.1f}%)")

    print("\n" + "=" * 70)
else:
    print("\n❌ No viable configurations found in target range")
