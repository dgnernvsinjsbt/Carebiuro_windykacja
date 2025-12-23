#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
df_dec = df[df['timestamp'].dt.month == 12].copy().reset_index(drop=True)

ENTRY_OFFSET_PCT = 2.0
TP_PCT = 2.0
SL_PCT = 10.0
INITIAL_EQUITY = 100.0

print("="*140)
print("ALL TRADES ON DECEMBER 8TH")
print("="*140)
print()

equity = INITIAL_EQUITY
trades = []
current_day, daily_high, in_position, stopped_out_today, position = None, 0, False, False, None
trade_num = 0

for i in range(len(df_dec)):
    row = df_dec.iloc[i]
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
                    'daily_high': daily_high,
                    'day': day
                }
    
    if in_position:
        hit_sl = row['low'] <= position['sl_price']
        hit_tp = row['high'] >= position['tp_price']
        
        if hit_sl or hit_tp:
            trade_num += 1
            exit_price = position['sl_price'] if hit_sl else position['tp_price']
            pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
            pnl_dollar = position['position_size'] * (pnl_pct / 100)
            equity += pnl_dollar
            
            trades.append({
                'trade_num': trade_num,
                'day': position['day'],
                'entry_time': position['entry_time'],
                'exit_time': row['timestamp'],
                'daily_high': position['daily_high'],
                'entry_price': position['entry_price'],
                'sl_price': position['sl_price'],
                'tp_price': position['tp_price'],
                'exit_price': exit_price,
                'result': 'TP' if hit_tp else 'SL',
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'equity_after': equity
            })
            
            in_position, position = False, None
            
            if hit_sl:
                stopped_out_today = True

# Filter to Dec 8th only
trades_df = pd.DataFrame(trades)
dec8_trades = trades_df[trades_df['day'] == pd.Timestamp('2025-12-08').date()].copy()

if len(dec8_trades) == 0:
    print("❌ NO TRADES ON DECEMBER 8TH")
    print()
    print("Checking if Dec 8th has data...")
    dec8_data = df_dec[df_dec['timestamp'].dt.date == pd.Timestamp('2025-12-08').date()]
    if len(dec8_data) == 0:
        print("❌ NO DATA FOR DECEMBER 8TH IN DATASET")
    else:
        print(f"✅ Dataset has {len(dec8_data)} candles for Dec 8th")
        print(f"   First candle: {dec8_data.iloc[0]['timestamp']}")
        print(f"   Last candle: {dec8_data.iloc[-1]['timestamp']}")
        print(f"   High: ${dec8_data['high'].max():.6f}")
        print(f"   Low: ${dec8_data['low'].min():.6f}")
        
        # Check if previous day ended with SL
        dec7_trades = trades_df[trades_df['day'] == pd.Timestamp('2025-12-07').date()]
        if len(dec7_trades) > 0:
            last_dec7 = dec7_trades.iloc[-1]
            print()
            print(f"Last Dec 7th trade:")
            print(f"   Result: {last_dec7['result']}")
            print(f"   Exit time: {last_dec7['exit_time']}")
            if last_dec7['result'] == 'SL':
                print("   ⚠️  Dec 7 ended with SL - stopped trading for that day")
else:
    print(f"DECEMBER 8TH TRADES: {len(dec8_trades)} total")
    print("-"*140)
    
    for _, trade in dec8_trades.iterrows():
        status = "✅ WIN" if trade['result'] == 'TP' else "❌ LOSS"
        print(f"Trade #{trade['trade_num']}:")
        print(f"  Entry Time: {trade['entry_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"  Exit Time: {trade['exit_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"  Daily High: ${trade['daily_high']:.6f}")
        print(f"  Entry: ${trade['entry_price']:.6f}, SL: ${trade['sl_price']:.6f}, TP: ${trade['tp_price']:.6f}")
        print(f"  Exit: ${trade['exit_price']:.6f}")
        print(f"  Result: {trade['result']} - P&L: {trade['pnl_pct']:+.2f}% (${trade['pnl_dollar']:+.2f})")
        print(f"  Equity After: ${trade['equity_after']:.2f}")
        print(f"  {status}")
        print()

print()
print("="*140)
print()

# Show all days with trades
print("TRADES BY DAY:")
for day in sorted(trades_df['day'].unique()):
    day_trades = trades_df[trades_df['day'] == day]
    tp_count = (day_trades['result'] == 'TP').sum()
    sl_count = (day_trades['result'] == 'SL').sum()
    day_pnl = day_trades['pnl_dollar'].sum()
    print(f"  {day}: {len(day_trades)} trades ({tp_count} TP, {sl_count} SL), P&L: ${day_pnl:+.2f}")

print()
print("="*140)
