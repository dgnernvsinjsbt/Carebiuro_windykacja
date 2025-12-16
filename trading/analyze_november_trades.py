#!/usr/bin/env python3
"""Analyze November trades to find filter opportunities"""
import pandas as pd
import numpy as np

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

# Original config
rsi_ob = 65
limit_offset_atr = 0.1
sl_atr = 1.2
tp_atr = 3.0
min_move = 0.8
min_momentum = 0

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

            signal_row = df.iloc[position['signal_bar']]

            trades.append({
                'signal_time': signal_row['timestamp'],
                'pnl_dollar': pnl_dollar,
                'exit_reason': exit_reason,
                'signal_rsi': signal_row['rsi'],
                'signal_ret20': signal_row['ret_20'],
                'signal_atr_pct': (signal_row['atr'] / signal_row['close']) * 100,
                'signal_move_size': signal_row['avg_move_size']
            })

            won = pnl_pct > 0
            current_risk = min(current_risk * 1.5, 0.30) if won else max(current_risk * 0.5, 0.02)
            position = None

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
trades_df['signal_time'] = pd.to_datetime(trades_df['signal_time'])
trades_df['month'] = trades_df['signal_time'].dt.to_period('M')
trades_df['winner'] = trades_df['pnl_dollar'] > 0

# November only
nov = trades_df[trades_df['month'] == '2025-11'].copy()

print("=" * 70)
print("NOVEMBER TRADE ANALYSIS")
print("=" * 70)

winners = nov[nov['winner']]
losers = nov[~nov['winner']]

print(f"\nTotal: {len(nov)} trades")
print(f"Winners: {len(winners)} (${winners['pnl_dollar'].sum():+.2f})")
print(f"Losers: {len(losers)} (${losers['pnl_dollar'].sum():+.2f})")
print(f"Net: ${nov['pnl_dollar'].sum():+.2f}")

print("\n" + "=" * 70)
print("WINNER vs LOSER CHARACTERISTICS")
print("=" * 70)

print(f"\nSignal RSI:")
print(f"  Winners: {winners['signal_rsi'].mean():.1f} (±{winners['signal_rsi'].std():.1f})")
print(f"  Losers:  {losers['signal_rsi'].mean():.1f} (±{losers['signal_rsi'].std():.1f})")

print(f"\nRet20 (momentum):")
print(f"  Winners: {winners['signal_ret20'].mean():+.2f}% (±{winners['signal_ret20'].std():.2f})")
print(f"  Losers:  {losers['signal_ret20'].mean():+.2f}% (±{losers['signal_ret20'].std():.2f})")

print(f"\nATR % (volatility):")
print(f"  Winners: {winners['signal_atr_pct'].mean():.3f}% (±{winners['signal_atr_pct'].std():.3f})")
print(f"  Losers:  {losers['signal_atr_pct'].mean():.3f}% (±{losers['signal_atr_pct'].std():.3f})")

print(f"\nMove Size:")
print(f"  Winners: {winners['signal_move_size'].mean():.3f}% (±{winners['signal_move_size'].std():.3f})")
print(f"  Losers:  {losers['signal_move_size'].mean():.3f}% (±{losers['signal_move_size'].std():.3f})")

print("\n" + "=" * 70)
print("FILTER SUGGESTIONS")
print("=" * 70)

# Test potential filters
if winners['signal_ret20'].mean() > losers['signal_ret20'].mean():
    diff = winners['signal_ret20'].mean() - losers['signal_ret20'].mean()
    print(f"\n✅ Momentum filter: Winners have {diff:+.1f}% higher ret_20")
    print(f"   Try min_ret_20 >= {losers['signal_ret20'].quantile(0.75):.1f}%")

if winners['signal_rsi'].mean() != losers['signal_rsi'].mean():
    diff = abs(winners['signal_rsi'].mean() - losers['signal_rsi'].mean())
    if winners['signal_rsi'].mean() < losers['signal_rsi'].mean():
        print(f"\n✅ RSI filter: Winners have {diff:.1f} LOWER RSI")
        print(f"   Try RSI <= {losers['signal_rsi'].quantile(0.25):.0f}")
    else:
        print(f"\n✅ RSI filter: Winners have {diff:.1f} HIGHER RSI")
        print(f"   Try RSI >= {winners['signal_rsi'].quantile(0.25):.0f}")

if winners['signal_atr_pct'].mean() > losers['signal_atr_pct'].mean():
    diff = winners['signal_atr_pct'].mean() - losers['signal_atr_pct'].mean()
    print(f"\n✅ Volatility filter: Winners have {diff:.3f}% higher ATR")
    print(f"   Try ATR >= {losers['signal_atr_pct'].quantile(0.75):.3f}%")

print("\n" + "=" * 70)
