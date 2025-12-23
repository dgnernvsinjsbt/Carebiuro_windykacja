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
print("DECEMBER LOSING TRADES - LONG SCALP STRATEGY")
print("="*140)
print()

equity = INITIAL_EQUITY
peak_equity = INITIAL_EQUITY
trades = []

current_day, daily_high, in_position, stopped_out_today, position = None, 0, False, False, None

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
                    'daily_high': daily_high
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
            
            trades.append({
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

# Filter to losing trades only
trades_df = pd.DataFrame(trades)
losing_trades = trades_df[trades_df['result'] == 'SL'].copy()

print(f"Total Trades: {len(trades_df)}")
print(f"Winning Trades: {(trades_df['result'] == 'TP').sum()}")
print(f"Losing Trades: {len(losing_trades)}")
print(f"Win Rate: {(trades_df['result'] == 'TP').sum() / len(trades_df) * 100:.1f}%")
print()
print("="*140)
print()
print("ALL LOSING TRADES (SL HIT):")
print("-"*140)

for idx, trade in losing_trades.iterrows():
    print(f"Trade #{idx + 1}:")
    print(f"  Date: {trade['entry_time'].strftime('%Y-%m-%d')}")
    print(f"  Entry Time: {trade['entry_time'].strftime('%H:%M')}")
    print(f"  Exit Time: {trade['exit_time'].strftime('%H:%M')}")
    print(f"  Daily High: ${trade['daily_high']:.6f}")
    print(f"  Entry Price: ${trade['entry_price']:.6f} (2% below high)")
    print(f"  SL Price: ${trade['sl_price']:.6f} (10% below entry)")
    print(f"  TP Price: ${trade['tp_price']:.6f} (2% above entry)")
    print(f"  Exit Price: ${trade['exit_price']:.6f}")
    print(f"  P&L: {trade['pnl_pct']:+.2f}% (${trade['pnl_dollar']:+.2f})")
    print(f"  Equity After: ${trade['equity_after']:.2f}")
    
    # Calculate how far price dropped from entry
    drop_from_entry = ((trade['entry_price'] - trade['exit_price']) / trade['entry_price']) * 100
    print(f"  Drop from Entry: {drop_from_entry:.2f}%")
    print()

print("-"*140)
print()
print(f"Summary:")
print(f"  Total Loss from SL trades: ${losing_trades['pnl_dollar'].sum():+.2f}")
print(f"  Avg Loss per SL trade: {losing_trades['pnl_pct'].mean():+.2f}%")
print(f"  Largest Loss: {losing_trades['pnl_pct'].min():+.2f}% (${losing_trades['pnl_dollar'].min():+.2f})")

print()
print("="*140)
