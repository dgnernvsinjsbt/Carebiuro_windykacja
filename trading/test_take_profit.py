#!/usr/bin/env python3
"""Test different take profit ATR values"""
import pandas as pd
import numpy as np

df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

# Calculate indicators
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

def backtest_tp(tp_atr):
    """Test with specific take profit"""
    # Fixed params (OPTIMAL from previous tests)
    rsi_ob = 65
    limit_offset_atr = 0.1  # OPTIMAL
    sl_atr = 2.0  # OPTIMAL
    min_move = 0.8
    min_momentum = 0

    current_risk = 0.12
    equity = 100.0
    equity_curve = [equity]
    trades = []
    position = None
    pending_order = None

    for i in range(300, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']) or pd.isna(row['avg_move_size']):
            continue

        # Check pending order
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
            exit_reason = None

            if row['high'] >= position['sl_price']:
                pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                exit_reason = 'SL'
            elif row['low'] <= position['tp_price']:
                pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                exit_reason = 'TP'

            if pnl_pct is not None:
                pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl_dollar
                equity_curve.append(equity)

                trades.append({
                    'pnl_dollar': pnl_dollar,
                    'entry_time': df.iloc[position['entry_bar']]['timestamp'],
                    'exit_reason': exit_reason
                })

                won = pnl_pct > 0
                current_risk = min(current_risk * 1.5, 0.30) if won else max(current_risk * 0.5, 0.02)
                position = None
                continue

        # Generate signals (SHORT only)
        if not position and not pending_order and i > 0:
            prev_row = df.iloc[i-1]

            if row['ret_20'] <= min_momentum or pd.isna(prev_row['rsi']):
                continue

            if prev_row['rsi'] > rsi_ob and row['rsi'] <= rsi_ob:
                if row['avg_move_size'] >= min_move:
                    signal_price = row['close']
                    atr = row['atr']

                    limit_price = signal_price + (atr * limit_offset_atr)
                    sl_price = limit_price + (atr * sl_atr)
                    tp_price = limit_price - (atr * tp_atr)  # VARIABLE

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

    trades_df = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = trades_df[trades_df['pnl_dollar'] > 0]
    win_rate = len(winners) / len(trades_df) * 100

    tp_rate = len(trades_df[trades_df['exit_reason'] == 'TP']) / len(trades_df) * 100

    return {
        'tp_atr': tp_atr,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'tp_rate': tp_rate
    }

print("=" * 70)
print("TESTING TAKE PROFIT (2.0 to 6.0 ATR)")
print("Fixed: Offset=0.1 ATR, SL=2.0 ATR, RSI=65, Move=0.8%, Momentum=0%")
print("=" * 70)

tp_values = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]

results = []
for tp in tp_values:
    result = backtest_tp(tp)
    if result:
        results.append(result)
        print(f"\nTP {tp:.1f} ATR:")
        print(f"  Return: {result['return']:+7.1f}% | DD: {result['max_dd']:6.2f}% | R/DD: {result['return_dd']:5.2f}x")
        print(f"  Trades: {result['trades']:3d} | Win Rate: {result['win_rate']:5.1f}% | TP Rate: {result['tp_rate']:5.1f}%")

if results:
    print("\n" + "=" * 70)
    print("SUMMARY (sorted by Return/DD)")
    print("=" * 70)

    results.sort(key=lambda x: x['return_dd'], reverse=True)

    print(f"\n{'TP ATR':<8} {'Return':<10} {'Max DD':<10} {'R/DD':<8} {'Trades':<8} {'Win%':<8} {'TP%':<8}")
    print("-" * 70)

    for r in results:
        print(f"{r['tp_atr']:<8.1f} {r['return']:>+9.1f}% {r['max_dd']:>9.2f}% {r['return_dd']:>7.2f}x {r['trades']:>7d} {r['win_rate']:>7.1f}% {r['tp_rate']:>7.1f}%")

    print("\n" + "=" * 70)
    print("BEST BY RETURN/DD")
    print("=" * 70)

    best = results[0]
    print(f"\nTake Profit: {best['tp_atr']:.1f} ATR")
    print(f"Return: {best['return']:+.1f}%")
    print(f"Max DD: {best['max_dd']:.2f}%")
    print(f"Return/DD: {best['return_dd']:.2f}x")
    print(f"Trades: {best['trades']}")
    print(f"Win Rate: {best['win_rate']:.1f}%")
    print(f"TP Hit Rate: {best['tp_rate']:.1f}%")

    print("\n" + "=" * 70)
