#!/usr/bin/env python3
"""
Check how long positions are held
"""
import pandas as pd

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

# December with 0.8% offset - check hold times
df_dec = df[(df['timestamp'] >= '2025-12-17 07:00') & (df['timestamp'] < '2025-12-17 11:00')].copy().reset_index(drop=True)

print("="*120)
print("POSITION HOLD TIMES - Dec 17, 08:00-10:00")
print("="*120)
print()

offset_pct = 0.8
has_pending = False
pending_limit = None
pending_signal_bar = None
pending_sl = None
pending_tp = None

i = 32
while i < len(df_dec):
    row = df_dec.iloc[i]
    
    if pd.isna(row['atr']):
        i += 1
        continue
    
    if has_pending:
        bars_waiting = i - pending_signal_bar
        
        if row['low'] <= pending_limit:
            entry_price = pending_limit
            sl_dist_pct = ((pending_sl - entry_price) / entry_price) * 100
            
            if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                # Find exit
                hit_sl = False
                hit_tp = False
                exit_bar = None
                
                for k in range(i + 1, min(i + 100, len(df_dec))):
                    exit_row = df_dec.iloc[k]
                    
                    if exit_row['high'] >= pending_sl:
                        hit_sl = True
                        exit_bar = k
                        break
                    elif exit_row['low'] <= pending_tp:
                        hit_tp = True
                        exit_bar = k
                        break
                
                if exit_bar:
                    hold_bars = exit_bar - i
                    hold_minutes = hold_bars * 15
                    
                    entry_time = row['timestamp'] + pd.Timedelta(hours=1)
                    exit_time = df_dec.iloc[exit_bar]['timestamp'] + pd.Timedelta(hours=1)
                    
                    print(f"Entry: {entry_time.strftime('%H:%M')} | Exit: {exit_time.strftime('%H:%M')} | Hold: {hold_bars} bars ({hold_minutes} min) | Result: {'TP' if hit_tp else 'SL'}")
            
            has_pending = False
        
        elif row['high'] >= pending_sl:
            has_pending = False
        
        elif bars_waiting >= 16:
            has_pending = False
        
        i += 1
        continue
    
    # Check for signal
    high_8h = df_dec.iloc[max(0, i-32):i]['high'].max()
    dist_pct = ((row['close'] - high_8h) / high_8h) * 100
    
    if dist_pct <= -2.5:
        signal_price = row['close']
        sl_price = high_8h
        tp_price = signal_price * (1 - 0.05)
        limit_price = signal_price * (1 + offset_pct / 100)
        
        if limit_price < sl_price:
            has_pending = True
            pending_limit = limit_price
            pending_signal_bar = i
            pending_sl = sl_price
            pending_tp = tp_price
    
    i += 1

print("="*120)
