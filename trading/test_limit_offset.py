#!/usr/bin/env python3
"""Limit Offset Strategy: Place limit order X ATR above trigger instead of market entry"""
import pandas as pd
import numpy as np

df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
df_dec = df[df['timestamp'].dt.month == 12].copy().reset_index(drop=True)

# Calculate ATR
high_low = df_dec['high'] - df_dec['low']
high_close = abs(df_dec['high'] - df_dec['close'].shift())
low_close = abs(df_dec['low'] - df_dec['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df_dec['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

ENTRY_OFFSET_PCT = 2.0
SL_PCT = 3.5
TP_PCT = 10.0
INITIAL_EQUITY = 100.0
MAX_WAIT_BARS = 20

offset_multipliers = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
results = []

for LIMIT_OFFSET_ATR in offset_multipliers:
    equity = INITIAL_EQUITY
    peak_equity = INITIAL_EQUITY
    max_dd = 0.0
    trades = []
    current_day = None
    daily_high = 0
    in_position = False
    tp_hit_today = False
    position = None
    pending_limit = None

    for i in range(50, len(df_dec)):
        row = df_dec.iloc[i]
        day = row['timestamp'].date()

        if day != current_day:
            current_day = day
            daily_high = row['high']
            tp_hit_today = False
            pending_limit = None
            if in_position:
                pnl_pct = ((position['entry_price'] - row['open']) / position['entry_price']) * 100
                pnl_dollar = position['position_size'] * (pnl_pct / 100)
                equity += pnl_dollar
                trades.append({'result': 'DAY_CLOSE', 'pnl_dollar': pnl_dollar})
                in_position = False
                position = None

        if row['high'] > daily_high:
            daily_high = row['high']

        if pending_limit:
            if i - pending_limit['placed_bar'] > MAX_WAIT_BARS:
                pending_limit = None
            elif row['high'] >= pending_limit['limit_price']:
                entry_price = pending_limit['limit_price']
                sl_price = entry_price * (1 + SL_PCT / 100)
                tp_price = entry_price * (1 - TP_PCT / 100)
                position_size = (equity * 5.0) / SL_PCT
                if position_size > 0:
                    in_position = True
                    position = {'entry_price': entry_price, 'sl_price': sl_price, 'tp_price': tp_price, 'position_size': position_size}
                pending_limit = None

        if not in_position and not tp_hit_today and not pending_limit:
            trigger_price = daily_high * (1 - ENTRY_OFFSET_PCT / 100)
            if row['low'] <= trigger_price:
                limit_price = trigger_price + (LIMIT_OFFSET_ATR * row['atr'])
                if row['high'] >= limit_price:
                    entry_price = limit_price
                    sl_price = entry_price * (1 + SL_PCT / 100)
                    tp_price = entry_price * (1 - TP_PCT / 100)
                    position_size = (equity * 5.0) / SL_PCT
                    if position_size > 0:
                        in_position = True
                        position = {'entry_price': entry_price, 'sl_price': sl_price, 'tp_price': tp_price, 'position_size': position_size}
                else:
                    pending_limit = {'limit_price': limit_price, 'placed_bar': i}

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
                in_position = False
                position = None
                if hit_tp:
                    tp_hit_today = True

    if trades:
        trades_df = pd.DataFrame(trades)
        total_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
        win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100
        return_dd = total_return / max_dd if max_dd > 0 else 0
        results.append({'offset': LIMIT_OFFSET_ATR, 'return': total_return, 'max_dd': max_dd, 'return_dd': return_dd, 'trades': len(trades_df), 'win_rate': win_rate})

print("LIMIT OFFSET RESULTS:")
for r in results:
    print(f"Offset {r['offset']:.1f}x ATR: Return {r['return']:+.2f}%, DD {r['max_dd']:.2f}%, R/DD {r['return_dd']:.2f}x, Trades {r['trades']}, WR {r['win_rate']:.1f}%")
if results:
    best = max(results, key=lambda x: x['return_dd'])
    print(f"BEST: {best['offset']:.1f}x ATR → R/DD {best['return_dd']:.2f}x")
