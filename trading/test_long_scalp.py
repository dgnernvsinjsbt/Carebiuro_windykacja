#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
df_dec = df[df['timestamp'].dt.month == 12].copy().reset_index(drop=True)

print("="*100)
print("LONG SCALP STRATEGY - December Test")
print("Entry: LONG when price dips 2% below daily high")
print("TP: 2% (quick scalp), SL: 10% (wide stop)")
print("Rule: TP = can trade again, SL = done for the day")
print("="*100)
print()

ENTRY_OFFSET_PCT = 2.0
TP_PCT = 2.0
SL_PCT = 10.0
INITIAL_EQUITY = 100.0

equity, peak_equity, max_dd, trades = INITIAL_EQUITY, INITIAL_EQUITY, 0.0, []
current_day, daily_high, in_position, stopped_out_today, position = None, 0, False, False, None

for i in range(len(df_dec)):
    row = df_dec.iloc[i]
    day = row['timestamp'].date()
    
    if day != current_day:
        current_day, daily_high, stopped_out_today = day, row['high'], False
        if in_position:
            # Close at market on day end
            pnl_pct = ((row['open'] - position['entry_price']) / position['entry_price']) * 100
            equity += position['position_size'] * (pnl_pct / 100)
            trades.append({'result': 'DAY_CLOSE', 'pnl_pct': pnl_pct})
            in_position, position = False, None
    
    if row['high'] > daily_high:
        daily_high = row['high']
    
    # Only enter if not in position AND not stopped out today
    if not in_position and not stopped_out_today:
        trigger_price = daily_high * (1 - ENTRY_OFFSET_PCT / 100)
        if row['low'] <= trigger_price:
            # LONG ENTRY
            entry_price = trigger_price
            sl_price = entry_price * (1 - SL_PCT / 100)  # 10% below
            tp_price = entry_price * (1 + TP_PCT / 100)  # 2% above
            position_size = (equity * 5.0) / SL_PCT
            if position_size > 0:
                in_position, position = True, {
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'position_size': position_size
                }
    
    if in_position:
        hit_sl = row['low'] <= position['sl_price']
        hit_tp = row['high'] >= position['tp_price']
        
        if hit_sl or hit_tp:
            exit_price = position['sl_price'] if hit_sl else position['tp_price']
            pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
            equity += position['position_size'] * (pnl_pct / 100)
            
            if equity > peak_equity:
                peak_equity = equity
            dd = ((peak_equity - equity) / peak_equity) * 100
            if dd > max_dd:
                max_dd = dd
            
            trades.append({'result': 'TP' if hit_tp else 'SL', 'pnl_pct': pnl_pct})
            in_position, position = False, None
            
            # If SL hit, stop trading for the day
            if hit_sl:
                stopped_out_today = True

total_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
return_dd = total_return / max_dd if max_dd > 0 else 0
trades_df = pd.DataFrame(trades)
win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100 if len(trades_df) > 0 else 0
tp_trades = (trades_df['result'] == 'TP').sum()
sl_trades = (trades_df['result'] == 'SL').sum()

print(f"RESULTS:")
print(f"  Return: {total_return:+.2f}%")
print(f"  Max DD: {max_dd:.2f}%")
print(f"  R/DD: {return_dd:.2f}x")
print(f"  Total Trades: {len(trades_df)}")
print(f"  TP Trades: {tp_trades} ({win_rate:.1f}%)")
print(f"  SL Trades: {sl_trades}")
print(f"  Final Equity: ${equity:.2f}")
print()

if win_rate > 0:
    avg_win = trades_df[trades_df['result'] == 'TP']['pnl_pct'].mean()
    avg_loss = trades_df[trades_df['result'] == 'SL']['pnl_pct'].mean()
    print(f"  Avg Win: {avg_win:+.2f}%")
    print(f"  Avg Loss: {avg_loss:+.2f}%")
    expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)
    print(f"  Expectancy: {expectancy:+.3f}%")

print()
print("="*100)
print("Compare to SHORT (Entry 2%, SL 3.5%, TP 10%): +33.72%, 1.82x R/DD")
print("="*100)
