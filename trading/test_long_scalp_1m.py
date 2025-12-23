#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('fartcoin_december_1m_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

ENTRY_OFFSET_PCT = 2.0
TP_PCT = 2.0
SL_PCT = 10.0
INITIAL_EQUITY = 100.0

print("="*100)
print("LONG SCALP STRATEGY - Fresh 1m BingX Data (Dec 1-16)")
print("="*100)
print()

equity, peak_equity, max_dd, trades = INITIAL_EQUITY, INITIAL_EQUITY, 0.0, []
current_day, daily_high, in_position, stopped_out_today, position = None, 0, False, False, None

for i in range(len(df)):
    row = df.iloc[i]
    day = row['timestamp'].date()
    
    if day != current_day:
        current_day, daily_high, stopped_out_today = day, row['high'], False
        if in_position:
            pnl_pct = ((row['open'] - position['entry_price']) / position['entry_price']) * 100
            equity += position['position_size'] * (pnl_pct / 100)
            in_position, position = False, None
    
    if row['high'] > daily_high:
        daily_high = row['high']
    
    if not in_position and not stopped_out_today:
        trigger_price = daily_high * (1 - ENTRY_OFFSET_PCT / 100)
        if row['low'] <= trigger_price:
            entry_price = trigger_price
            sl_price = entry_price * (1 - SL_PCT / 100)
            tp_price = entry_price * (1 + TP_PCT / 100)
            position_size = (equity * 5.0) / SL_PCT
            if position_size > 0:
                in_position, position = True, {
                    'entry_time': row['timestamp'],
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'position_size': position_size,
                    'day': day
                }
    
    if in_position:
        hit_sl = row['low'] <= position['sl_price']
        hit_tp = row['high'] >= position['tp_price']
        
        if hit_sl or hit_tp:
            exit_price = position['sl_price'] if hit_sl else position['tp_price']
            pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
            pnl_dollar = position['position_size'] * (pnl_pct / 100)
            equity += pnl_dollar
            
            if equity > peak_equity:
                peak_equity = equity
            dd = ((peak_equity - equity) / peak_equity) * 100
            if dd > max_dd:
                max_dd = dd
            
            hold_time = (row['timestamp'] - position['entry_time']).total_seconds() / 60
            
            trades.append({
                'day': position['day'],
                'entry_time': position['entry_time'],
                'exit_time': row['timestamp'],
                'hold_minutes': hold_time,
                'result': 'TP' if hit_tp else 'SL',
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar
            })
            
            in_position, position = False, None
            
            if hit_sl:
                stopped_out_today = True

total_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
return_dd = total_return / max_dd if max_dd > 0 else 0
trades_df = pd.DataFrame(trades)
win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100 if len(trades_df) > 0 else 0

print(f"RESULTS (1-minute data):")
print(f"  Return: {total_return:+.2f}%")
print(f"  Max DD: {max_dd:.2f}%")
print(f"  R/DD: {return_dd:.2f}x")
print(f"  Total Trades: {len(trades_df)}")
print(f"  Win Rate: {win_rate:.1f}%")
print(f"  Final Equity: ${equity:.2f}")
print()

if len(trades_df) > 0:
    tp_trades = trades_df[trades_df['result'] == 'TP']
    sl_trades = trades_df[trades_df['result'] == 'SL']
    
    print(f"  Winners: {len(tp_trades)}")
    print(f"  Losers: {len(sl_trades)}")
    
    if len(tp_trades) > 0:
        print(f"  Avg hold time (TP): {tp_trades['hold_minutes'].mean():.1f} minutes")
    if len(sl_trades) > 0:
        print(f"  Avg hold time (SL): {sl_trades['hold_minutes'].mean():.1f} minutes")

print()
print("-"*100)
print()

# Show Dec 8th trades
dec8_trades = trades_df[trades_df['day'] == pd.Timestamp('2025-12-08').date()]
if len(dec8_trades) > 0:
    print(f"DEC 8TH TRADES: {len(dec8_trades)} total")
    print()
    for idx, trade in dec8_trades.head(10).iterrows():
        status = "TP" if trade['result'] == 'TP' else "SL"
        print(f"  {trade['entry_time'].strftime('%H:%M')} → {trade['exit_time'].strftime('%H:%M')} ({trade['hold_minutes']:.0f}m): {status} {trade['pnl_pct']:+.2f}%")

print()
print("="*100)
print()
print("COMPARE TO 15m DATA:")
print("  15m data: +14.45%, 1.82x R/DD, 75 trades, 90.7% WR")
print("="*100)
