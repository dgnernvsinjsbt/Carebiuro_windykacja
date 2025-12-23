#!/usr/bin/env python3
"""Filter Test: ATR > 1.0% (avoid low vol chop)"""
import pandas as pd
import numpy as np

df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
df_dec = df[df['timestamp'].dt.month == 12].copy().reset_index(drop=True)

# Indicators
high_low = df_dec['high'] - df_dec['low']
high_close = abs(df_dec['high'] - df_dec['close'].shift())
low_close = abs(df_dec['low'] - df_dec['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df_dec['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df_dec['atr_pct'] = (df_dec['atr'] / df_dec['close']) * 100

ENTRY_OFFSET_PCT, SL_PCT, TP_PCT, INITIAL_EQUITY = 2.0, 3.5, 10.0, 100.0
equity, peak_equity, max_dd, trades = INITIAL_EQUITY, INITIAL_EQUITY, 0.0, []
current_day, daily_high, in_position, tp_hit_today, position, skipped = None, 0, False, False, None, 0

for i in range(50, len(df_dec)):
    row = df_dec.iloc[i]
    day = row['timestamp'].date()

    if day != current_day:
        current_day, daily_high, tp_hit_today = day, row['high'], False
        if in_position:
            pnl_pct = ((position['entry_price'] - row['open']) / position['entry_price']) * 100
            pnl_dollar = position['position_size'] * (pnl_pct / 100)
            equity += pnl_dollar
            trades.append({'result': 'DAY_CLOSE', 'pnl_dollar': pnl_dollar})
            in_position, position = False, None

    if row['high'] > daily_high:
        daily_high = row['high']

    if not in_position and not tp_hit_today:
        trigger_price = daily_high * (1 - ENTRY_OFFSET_PCT / 100)
        if row['low'] <= trigger_price:
            # FILTER: ATR > 1.0%
            if row['atr_pct'] <= 1.0:
                skipped += 1
                continue

            entry_price = trigger_price
            sl_price = entry_price * (1 + SL_PCT / 100)
            tp_price = entry_price * (1 - TP_PCT / 100)
            position_size = (equity * 5.0) / SL_PCT

            if position_size > 0:
                in_position, position = True, {
                    'entry_price': entry_price, 'sl_price': sl_price,
                    'tp_price': tp_price, 'position_size': position_size
                }

    if in_position:
        hit_sl = row['high'] >= position['sl_price']
        hit_tp = row['low'] <= position['tp_price']

        if hit_sl or hit_tp:
            exit_price = position['sl_price'] if hit_sl else position['tp_price']
            pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
            pnl_dollar = position['position_size'] * (pnl_pct / 100)
            equity += pnl_dollar

            if equity > peak_equity:
                peak_equity = equity
            dd = ((peak_equity - equity) / peak_equity) * 100
            if dd > max_dd:
                max_dd = dd

            trades.append({'result': 'TP' if hit_tp else 'SL', 'pnl_dollar': pnl_dollar})
            in_position, position = False, None
            if hit_tp:
                tp_hit_today = True

if trades:
    trades_df = pd.DataFrame(trades)
    total_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
    win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100
    print(f"ATR > 1.0%: Return {total_return:+.2f}%, DD {max_dd:.2f}%, R/DD {total_return/max_dd if max_dd > 0 else 0:.2f}x, Trades {len(trades_df)}, WR {win_rate:.1f}%, Skipped {skipped}")
