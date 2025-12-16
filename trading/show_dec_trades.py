#!/usr/bin/env python3
"""Show exact December trades for TP 10% config"""
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

def find_swing_low(df, idx, lookback):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['low'].min()

def find_swing_high(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['high'].max()

# Fixed config: 0.8 ATR limit offset, 10% TP
limit_atr_offset = 0.8
rsi_trigger = 72
lookback = 5
tp_pct = 10.0
max_wait_bars = 20

equity = 100.0
trades = []

armed = False
signal_idx = None
swing_low = None
limit_pending = False
limit_price = None
limit_placed_idx = None
swing_high_for_sl = None

for i in range(lookback, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        continue

    if row['rsi'] > rsi_trigger:
        armed = True
        signal_idx = i
        swing_low = find_swing_low(df, i, lookback)
        limit_pending = False

    if armed and swing_low is not None and not limit_pending:
        if row['low'] < swing_low:
            atr = row['atr']
            limit_price = swing_low + (atr * limit_atr_offset)
            swing_high_for_sl = find_swing_high(df, signal_idx, i)
            limit_pending = True
            limit_placed_idx = i
            armed = False

    if limit_pending:
        if i - limit_placed_idx > max_wait_bars:
            limit_pending = False
            continue

        if row['high'] >= limit_price:
            entry_price = limit_price
            sl_price = swing_high_for_sl
            tp_price = entry_price * (1 - tp_pct / 100)

            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

            if sl_dist_pct <= 0 or sl_dist_pct > 10:
                limit_pending = False
                continue

            size = (equity * 0.05) / (sl_dist_pct / 100)

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
                continue

            pnl_dollar = size * (pnl_pct / 100) - size * 0.001
            equity += pnl_dollar

            trades.append({
                'signal_time': df.iloc[signal_idx]['timestamp'],
                'entry_time': row['timestamp'],
                'exit_time': df.iloc[exit_bar]['timestamp'] if exit_bar else None,
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'exit_price': df.iloc[exit_bar]['close'] if exit_bar else None,
                'pnl_dollar': pnl_dollar,
                'pnl_pct': pnl_pct,
                'exit_reason': exit_reason,
                'size': size,
                'sl_dist_pct': sl_dist_pct
            })

            limit_pending = False

trades_df = pd.DataFrame(trades)
trades_df['signal_time'] = pd.to_datetime(trades_df['signal_time'])
trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
trades_df['month'] = trades_df['signal_time'].dt.to_period('M')

# Filter December trades
dec_trades = trades_df[trades_df['month'] == '2025-12'].copy()

print("=" * 120)
print("DECEMBER 2025 TRADES - DETAILED BREAKDOWN")
print("=" * 120)
print()

for idx, trade in dec_trades.iterrows():
    result = "🟢 WINNER" if trade['pnl_dollar'] > 0 else "🔴 LOSER"
    print(f"{result} - {trade['exit_reason']}")
    print("-" * 120)
    print(f"Signal Time:  {trade['signal_time']}")
    print(f"Entry Time:   {trade['entry_time']}")
    print(f"Exit Time:    {trade['exit_time']}")
    print()
    print(f"Entry Price:  ${trade['entry_price']:.4f}")
    print(f"SL Price:     ${trade['sl_price']:.4f} ({trade['sl_dist_pct']:.2f}% away)")
    print(f"TP Price:     ${trade['tp_price']:.4f} (10% away)")
    print()
    print(f"Position Size: ${trade['size']:.2f}")
    print(f"P&L:          ${trade['pnl_dollar']:+.2f} ({trade['pnl_pct']:+.2f}%)")

    # Calculate hold time
    if pd.notna(trade['exit_time']) and pd.notna(trade['entry_time']):
        hold_time = trade['exit_time'] - trade['entry_time']
        hours = hold_time.total_seconds() / 3600
        print(f"Hold Time:    {hours:.1f} hours ({hold_time})")

    print("=" * 120)
    print()

# Summary
print("DECEMBER SUMMARY")
print("-" * 120)
print(f"Total Trades: {len(dec_trades)}")
print(f"Winners: {len(dec_trades[dec_trades['pnl_dollar'] > 0])}")
print(f"Losers: {len(dec_trades[dec_trades['pnl_dollar'] < 0])}")
print(f"Total P&L: ${dec_trades['pnl_dollar'].sum():+.2f}")
print(f"Win Rate: {(len(dec_trades[dec_trades['pnl_dollar'] > 0]) / len(dec_trades) * 100):.1f}%")
