"""Simplest possible test"""
import pandas as pd
import numpy as np

df = pd.read_csv('trading/melania_3months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

df['rsi'] = calculate_rsi(df['close'])
df['atr'] = calculate_atr(df)
df['atr_pct'] = (df['atr'] / df['close']) * 100

# Find first VOL_SPIKE
vol_spikes = df[(df['atr_pct'] > 5.0) & (df['rsi'] > 70)]
print(f"Found {len(vol_spikes)} VOL_SPIKE patterns")

if len(vol_spikes) > 0:
    first = vol_spikes.iloc[0]
    idx = vol_spikes.index[0]
    
    print(f"\nFirst VOL_SPIKE at index {idx}:")
    print(f"  Price: {first['close']:.4f}")
    print(f"  High: {first['high']:.4f}")
    print(f"  RSI: {first['rsi']:.1f}")
    print(f"  ATR: {first['atr']:.4f} ({first['atr_pct']:.2f}%)")
    
    # Place limit order
    limit_price = first['high'] + 0.5 * first['atr']
    sl_price = first['high'] + 0.3 * first['atr']
    
    print(f"\nLimit order:")
    print(f"  Limit: {limit_price:.4f} (entry)")
    print(f"  SL: {sl_price:.4f}")
    print(f"  TP (10%): {limit_price * 0.90:.4f}")
    
    # Check if it fills in next 20 bars
    print(f"\nChecking next 20 bars for fill...")
    for j in range(idx+1, min(idx+21, len(df))):
        bar = df.iloc[j]
        if bar['high'] >= limit_price:
            print(f"  FILLED at bar {j} (bar {j-idx} after signal)")
            print(f"    High: {bar['high']:.4f}")
            
            # Check TP/SL
            tp_price = limit_price * 0.90
            for k in range(j+1, min(j+51, len(df))):
                check = df.iloc[k]
                if check['low'] <= tp_price:
                    print(f"  TP HIT at bar {k} (bar {k-j} after fill)")
                    print(f"    Profit: {((tp_price - limit_price) / limit_price * 100):.2f}%")
                    break
                elif check['high'] >= sl_price:
                    print(f"  SL HIT at bar {k} (bar {k-j} after fill)")
                    print(f"    Loss: {((sl_price - limit_price) / limit_price * 100):.2f}%")
                    break
            break
    else:
        print(f"  NOT FILLED in 20 bars")
