#!/usr/bin/env python3
"""Check RSI levels of December signals"""
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
df['avg_move_size'] = (abs(df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100).rolling(96).mean()

# Run backtest with RSI 65
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

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['avg_move_size']):
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
                'prev_rsi': df.iloc[position['signal_bar']-1]['rsi'] if position['signal_bar'] > 0 else None
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

# December only
dec = trades_df[trades_df['month'] == '2025-12'].copy()

print("=" * 80)
print("DECEMBER SIGNAL RSI DISTRIBUTION")
print("=" * 80)

print(f"\nTotal December trades: {len(dec)}")
print(f"Winners: {len(dec[dec['pnl_dollar'] > 0])}")
print(f"Losers: {len(dec[dec['pnl_dollar'] < 0])}")
print(f"Total profit: ${dec['pnl_dollar'].sum():+.2f}")

print("\n" + "=" * 80)
print("PREVIOUS RSI DISTRIBUTION (what level it crossed from)")
print("=" * 80)

rsi_bins = [65, 66, 67, 68, 69, 70, 75, 100]
rsi_labels = ['65-66', '66-67', '67-68', '68-69', '69-70', '70-75', '75+']

dec['prev_rsi_bin'] = pd.cut(dec['prev_rsi'], bins=rsi_bins, labels=rsi_labels, right=False)

for bin_label in rsi_labels:
    bin_trades = dec[dec['prev_rsi_bin'] == bin_label]
    if len(bin_trades) > 0:
        profit = bin_trades['pnl_dollar'].sum()
        winners = len(bin_trades[bin_trades['pnl_dollar'] > 0])
        print(f"\nPrev RSI {bin_label}: {len(bin_trades)} trades | ${profit:+.2f} | {winners}W/{len(bin_trades)-winners}L")

print("\n" + "=" * 80)
print("KEY INSIGHT")
print("=" * 80)

# Show how much profit would be lost with each RSI filter
for threshold in [66, 67, 68, 69, 70]:
    kept = dec[dec['prev_rsi'] >= threshold]
    filtered = dec[dec['prev_rsi'] < threshold]

    print(f"\nRSI {threshold} threshold:")
    print(f"  Keeps: {len(kept)} trades (${kept['pnl_dollar'].sum():+.2f})")
    print(f"  Filters: {len(filtered)} trades (${filtered['pnl_dollar'].sum():+.2f})")

print("\n" + "=" * 80)
