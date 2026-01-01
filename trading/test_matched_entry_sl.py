#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
df_dec = df[df['timestamp'].dt.month == 12].copy().reset_index(drop=True)

TP_PCT, INITIAL_EQUITY = 10.0, 100.0

print("Testing MATCHED Entry Offset + SL...")
print("-" * 100)

configs = [
    {'entry': 2.0, 'sl': 2.0},
    {'entry': 2.5, 'sl': 2.5},
    {'entry': 3.0, 'sl': 3.0},
    {'entry': 3.5, 'sl': 3.5},
    {'entry': 4.0, 'sl': 4.0},
]

for config in configs:
    ENTRY_OFFSET_PCT = config['entry']
    SL_PCT = config['sl']
    
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
                entry_price = trigger_price
                sl_price = entry_price * (1 + SL_PCT / 100)
                tp_price = entry_price * (1 - TP_PCT / 100)
                position_size = (equity * 5.0) / SL_PCT
                if position_size > 0:
                    in_position, position = True, {
                        'entry_price': entry_price, 
                        'sl_price': sl_price, 
                        'tp_price': tp_price, 
                        'position_size': position_size
                    }
        
        if in_position:
            hit_sl = row['high'] >= position['sl_price']
            hit_tp = row['low'] <= position['tp_price']
            if hit_sl or hit_tp:
                exit_price = position['sl_price'] if hit_sl else position['tp_price']
                pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
                equity += position['position_size'] * (pnl_pct / 100)
                if equity > peak_equity: 
                    peak_equity = equity
                dd = ((peak_equity - equity) / peak_equity) * 100
                if dd > max_dd: 
                    max_dd = dd
                trades.append({'result': 'TP' if hit_tp else 'SL'})
                in_position, position = False, None
                if hit_tp: 
                    tp_hit_today = True
    
    total_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
    return_dd = total_return / max_dd if max_dd > 0 else 0
    win_rate = (pd.DataFrame(trades)['result'] == 'TP').sum() / len(trades) * 100 if trades else 0
    
    status = "🔥" if return_dd > 1.82 else ("✅" if return_dd > 1.5 else "")
    print(f"Entry {ENTRY_OFFSET_PCT:.1f}% + SL {SL_PCT:.1f}%: Return {total_return:+.2f}%, DD {max_dd:.2f}%, R/DD {return_dd:.2f}x, Trades {len(trades)}, WR {win_rate:.1f}% {status}")

print("-" * 100)
print("Baseline (Entry 2% + SL 3.5%): Return +33.72%, DD 18.55%, R/DD 1.82x")
