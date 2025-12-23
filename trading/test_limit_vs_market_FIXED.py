#!/usr/bin/env python3
import pandas as pd
import numpy as np

df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
df_dec = df[df['timestamp'].dt.month == 12].copy().reset_index(drop=True)

# ATR
high_low = df_dec['high'] - df_dec['low']
high_close = abs(df_dec['high'] - df_dec['close'].shift())
low_close = abs(df_dec['low'] - df_dec['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df_dec['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

ENTRY_OFFSET_PCT, SL_PCT, TP_PCT, INITIAL_EQUITY = 2.0, 3.5, 10.0, 100.0
MAX_WAIT = 20

print("Testing MARKET vs LIMIT strategies...")

# TEST 1: MARKET ENTRY (baseline)
equity, peak_equity, max_dd, trades = INITIAL_EQUITY, INITIAL_EQUITY, 0.0, []
current_day, daily_high, in_position, tp_hit_today, position = None, 0, False, False, None

for i in range(len(df_dec)):
    row = df_dec.iloc[i]
    day = row['timestamp'].date()
    
    if day != current_day:
        current_day, daily_high, tp_hit_today = day, row['high'], False
        if in_position:
            pnl_pct = ((position['entry_price'] - row['open']) / position['entry_price']) * 100
            equity += position['position_size'] * (pnl_pct / 100)
            in_position, position = False, None
    
    if row['high'] > daily_high:
        daily_high = row['high']
    
    if not in_position and not tp_hit_today:
        trigger_price = daily_high * (1 - ENTRY_OFFSET_PCT / 100)
        if row['low'] <= trigger_price:
            entry_price, sl_price, tp_price = trigger_price, trigger_price * (1 + SL_PCT / 100), trigger_price * (1 - TP_PCT / 100)
            position_size = (equity * 5.0) / SL_PCT
            if position_size > 0:
                in_position, position = True, {'entry_price': entry_price, 'sl_price': sl_price, 'tp_price': tp_price, 'position_size': position_size}
    
    if in_position:
        hit_sl, hit_tp = row['high'] >= position['sl_price'], row['low'] <= position['tp_price']
        if hit_sl or hit_tp:
            exit_price = position['sl_price'] if hit_sl else position['tp_price']
            pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
            equity += position['position_size'] * (pnl_pct / 100)
            if equity > peak_equity: peak_equity = equity
            dd = ((peak_equity - equity) / peak_equity) * 100
            if dd > max_dd: max_dd = dd
            trades.append({'result': 'TP' if hit_tp else 'SL'})
            in_position, position = False, None
            if hit_tp: tp_hit_today = True

market_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
market_rdd = market_return / max_dd if max_dd > 0 else 0
market_wr = (pd.DataFrame(trades)['result'] == 'TP').sum() / len(trades) * 100 if trades else 0
print(f"MARKET: Return {market_return:+.2f}%, DD {max_dd:.2f}%, R/DD {market_rdd:.2f}x, Trades {len(trades)}, WR {market_wr:.1f}%")

# TEST 2-8: LIMIT OFFSET
for OFFSET in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
    equity, peak_equity, max_dd, trades = INITIAL_EQUITY, INITIAL_EQUITY, 0.0, []
    current_day, daily_high, in_position, tp_hit_today, position, pending = None, 0, False, False, None, None
    
    for i in range(len(df_dec)):
        row = df_dec.iloc[i]
        day = row['timestamp'].date()
        
        if day != current_day:
            current_day, daily_high, tp_hit_today, pending = day, row['high'], False, None
            if in_position:
                pnl_pct = ((position['entry_price'] - row['open']) / position['entry_price']) * 100
                equity += position['position_size'] * (pnl_pct / 100)
                in_position, position = False, None
        
        if row['high'] > daily_high:
            daily_high = row['high']
        
        if pending:
            if i - pending['bar'] > MAX_WAIT:
                pending = None
            elif row['high'] >= pending['limit']:
                entry_price, sl_price, tp_price = pending['limit'], pending['limit'] * (1 + SL_PCT / 100), pending['limit'] * (1 - TP_PCT / 100)
                position_size = (equity * 5.0) / SL_PCT
                in_position, position, pending = True, {'entry_price': entry_price, 'sl_price': sl_price, 'tp_price': tp_price, 'position_size': position_size}, None
        
        if not in_position and not tp_hit_today and not pending:
            trigger_price = daily_high * (1 - ENTRY_OFFSET_PCT / 100)
            if row['low'] <= trigger_price:
                limit_price = trigger_price + (OFFSET * row['atr'])
                if row['high'] >= limit_price:
                    entry_price, sl_price, tp_price = limit_price, limit_price * (1 + SL_PCT / 100), limit_price * (1 - TP_PCT / 100)
                    position_size = (equity * 5.0) / SL_PCT
                    in_position, position = True, {'entry_price': entry_price, 'sl_price': sl_price, 'tp_price': tp_price, 'position_size': position_size}
                else:
                    pending = {'limit': limit_price, 'bar': i}
        
        if in_position:
            hit_sl, hit_tp = row['high'] >= position['sl_price'], row['low'] <= position['tp_price']
            if hit_sl or hit_tp:
                exit_price = position['sl_price'] if hit_sl else position['tp_price']
                pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
                equity += position['position_size'] * (pnl_pct / 100)
                if equity > peak_equity: peak_equity = equity
                dd = ((peak_equity - equity) / peak_equity) * 100
                if dd > max_dd: max_dd = dd
                trades.append({'result': 'TP' if hit_tp else 'SL'})
                in_position, position = False, None
                if hit_tp: tp_hit_today = True
    
    limit_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
    limit_rdd = limit_return / max_dd if max_dd > 0 else 0
    limit_wr = (pd.DataFrame(trades)['result'] == 'TP').sum() / len(trades) * 100 if trades else 0
    status = "🔥" if limit_rdd > market_rdd else ""
    print(f"LIMIT {OFFSET:.1f}x: Return {limit_return:+.2f}%, DD {max_dd:.2f}%, R/DD {limit_rdd:.2f}x, Trades {len(trades)}, WR {limit_wr:.1f}% {status}")
