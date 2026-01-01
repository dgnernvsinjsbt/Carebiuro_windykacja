#!/usr/bin/env python3
"""
Debug: Why do higher offsets get MORE fills?
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

# Test August with 0.0% vs 0.8% offset
df_aug = df[(df['timestamp'] >= '2025-08-01') & (df['timestamp'] < '2025-09-01')].copy().reset_index(drop=True)

print("="*120)
print("DEBUGGING FILL RATES: 0.0% vs 0.8% offset in August")
print("="*120)
print()

for offset_pct in [0.0, 0.8]:
    print(f"\n--- Testing {offset_pct}% offset ---")
    
    breakdown_threshold = -2.5
    lookback_bars = 32
    max_wait_bars = 16
    
    signals_generated = 0
    signals_filled = 0
    signals_timeout = 0
    signals_invalidated = 0
    signals_sl_too_wide = 0
    
    has_pending = False
    pending_limit = None
    pending_signal_bar = None
    pending_sl = None
    
    i = lookback_bars
    while i < len(df_aug):
        row = df_aug.iloc[i]
        
        if pd.isna(row['atr']):
            i += 1
            continue
        
        # Check pending
        if has_pending:
            bars_waiting = i - pending_signal_bar
            
            # Check fill
            if row['low'] <= pending_limit:
                sl_dist_pct = ((pending_sl - pending_limit) / pending_limit) * 100
                
                if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                    signals_filled += 1
                else:
                    signals_sl_too_wide += 1
                    
                has_pending = False
                
            # Check invalidation
            elif row['high'] >= pending_sl:
                signals_invalidated += 1
                has_pending = False
                
            # Check timeout
            elif bars_waiting >= max_wait_bars:
                signals_timeout += 1
                has_pending = False
                
            i += 1
            continue
        
        # Check for new signal
        high_8h = df_aug.iloc[max(0, i-lookback_bars):i]['high'].max()
        dist_pct = ((row['close'] - high_8h) / high_8h) * 100
        
        if dist_pct <= breakdown_threshold:
            signal_price = row['close']
            sl_price = high_8h
            limit_price = signal_price * (1 + offset_pct / 100)
            
            if limit_price < sl_price:
                has_pending = True
                pending_limit = limit_price
                pending_signal_bar = i
                pending_sl = sl_price
                signals_generated += 1
        
        i += 1
    
    print(f"Signals Generated: {signals_generated}")
    print(f"Signals Filled: {signals_filled}")
    print(f"Signals Timeout: {signals_timeout}")
    print(f"Signals Invalidated: {signals_invalidated}")
    print(f"Signals SL Too Wide: {signals_sl_too_wide}")
    print(f"Fill Rate: {signals_filled/signals_generated*100:.1f}%" if signals_generated > 0 else "N/A")

print()
print("="*120)
print("ANALYSIS")
print("="*120)
print()
print("If 0.8% offset has MORE filled trades than 0.0%, there's a bug.")
print("Higher offset should = lower fill rate, not higher!")
print("="*120)
