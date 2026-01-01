#!/usr/bin/env python3
"""Verify if optimal config makes Oct-Dec all profitable"""
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

# OPTIMAL PARAMETERS
rsi_ob = 65
limit_offset_atr = 0.1
sl_atr = 2.0
tp_atr = 3.0
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
trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')

# Calculate monthly P&L
monthly_pnl = {}
for month in trades_df['month'].unique():
    month_pnl = trades_df[trades_df['month'] == month]['pnl_dollar'].sum()
    monthly_pnl[str(month)] = month_pnl

total_return = ((equity - 100) / 100) * 100
eq_series = pd.Series(equity_curve)
running_max = eq_series.expanding().max()
drawdown = (eq_series - running_max) / running_max * 100
max_dd = drawdown.min()
return_dd = total_return / abs(max_dd)

print("=" * 70)
print("OPTIMAL CONFIG VERIFICATION")
print("=" * 70)
print(f"\nParameters:")
print(f"  RSI: {rsi_ob}")
print(f"  Offset: {limit_offset_atr} ATR")
print(f"  Stop Loss: {sl_atr} ATR")
print(f"  Take Profit: {tp_atr} ATR")
print(f"  Min Move: {min_move}%")
print(f"  Min Momentum: {min_momentum}%")

print(f"\nOverall Performance:")
print(f"  Return: {total_return:+.1f}%")
print(f"  Max DD: {max_dd:.2f}%")
print(f"  Return/DD: {return_dd:.2f}x")
print(f"  Trades: {len(trades_df)}")

print("\n" + "=" * 70)
print("MONTHLY BREAKDOWN")
print("=" * 70)

for month in sorted(monthly_pnl.keys()):
    pnl = monthly_pnl[month]
    profit_status = "✅" if pnl > 0 else "❌"
    print(f"{month}: ${pnl:+8.2f} {profit_status}")

oct_pnl = monthly_pnl.get('2025-10', 0)
nov_pnl = monthly_pnl.get('2025-11', 0)
dec_pnl = monthly_pnl.get('2025-12', 0)

oct_dec_all_positive = (oct_pnl > 0) and (nov_pnl > 0) and (dec_pnl > 0)

print("\n" + "=" * 70)
print("OCT-DEC STATUS")
print("=" * 70)
print(f"\nOct 2025: ${oct_pnl:+.2f} {'✅' if oct_pnl > 0 else '❌'}")
print(f"Nov 2025: ${nov_pnl:+.2f} {'✅' if nov_pnl > 0 else '❌'}")
print(f"Dec 2025: ${dec_pnl:+.2f} {'✅' if dec_pnl > 0 else '❌'}")

if oct_dec_all_positive:
    print("\n🎉 SUCCESS! Oct-Dec are ALL profitable!")
else:
    print("\n❌ FAIL: Not all of Oct-Dec are profitable")
    print("\nNeed to test different filters (momentum, RSI levels)")

print("\n" + "=" * 70)
