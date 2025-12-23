#!/usr/bin/env python3
"""
Show last 5 trades from DECEMBER with 0.8% offset
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

# DECEMBER with 0.8% offset
df_dec = df[(df['timestamp'] >= '2025-12-01') & (df['timestamp'] < '2026-01-01')].copy().reset_index(drop=True)

print("="*140)
print("LAST 5 FILLED TRADES - DECEMBER 0.8% OFFSET")
print("="*140)
print()

offset_pct = 0.8
breakdown_threshold = -2.5
lookback_bars = 32
max_wait_bars = 16

trades = []
has_pending = False
pending_limit = None
pending_signal_bar = None
pending_sl = None
pending_tp = None
pending_signal_price = None
pending_signal_time = None

i = lookback_bars
while i < len(df_dec):
    row = df_dec.iloc[i]
    
    if pd.isna(row['atr']):
        i += 1
        continue
    
    if has_pending:
        bars_waiting = i - pending_signal_bar
        
        if row['low'] <= pending_limit:
            sl_dist_pct = ((pending_sl - pending_limit) / pending_limit) * 100
            
            if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                signal_warsaw = (pending_signal_time + pd.Timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
                fill_warsaw = (row['timestamp'] + pd.Timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
                
                trades.append({
                    'signal_time_warsaw': signal_warsaw,
                    'fill_time_warsaw': fill_warsaw,
                    'signal_price': pending_signal_price,
                    'limit_price': pending_limit,
                    'sl_price': pending_sl,
                    'tp_price': pending_tp,
                    'sl_dist_pct': sl_dist_pct,
                    'bars_waited': bars_waiting
                })
                
            has_pending = False
            
        elif row['high'] >= pending_sl:
            has_pending = False
            
        elif bars_waiting >= max_wait_bars:
            has_pending = False
            
        i += 1
        continue
    
    high_8h = df_dec.iloc[max(0, i-lookback_bars):i]['high'].max()
    dist_pct = ((row['close'] - high_8h) / high_8h) * 100
    
    if dist_pct <= breakdown_threshold:
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
            pending_signal_price = signal_price
            pending_signal_time = row['timestamp']
    
    i += 1

if len(trades) >= 5:
    print("LAST 5 FILLED TRADES FROM DECEMBER:\n")
    
    for idx, t in enumerate(trades[-5:], 1):
        print(f"{'='*140}")
        print(f"TRADE #{len(trades) - 5 + idx} of {len(trades)}")
        print(f"{'='*140}")
        print(f"📍 Signal:  {t['signal_time_warsaw']} | Price ${t['signal_price']:.6f}")
        print(f"📋 Limit:   ${t['limit_price']:.6f} (0.8% above)")
        print(f"🛑 SL:      ${t['sl_price']:.6f} ({t['sl_dist_pct']:.2f}% away)")
        print(f"🎯 TP:      ${t['tp_price']:.6f}")
        print(f"✅ Filled:  {t['fill_time_warsaw']} ({t['bars_waited']} bars = {t['bars_waited'] * 15} min)")
        print()
else:
    print(f"Only {len(trades)} trades found in December")

print("="*140)
