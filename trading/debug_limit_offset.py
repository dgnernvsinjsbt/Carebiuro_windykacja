"""Debug why no trades are generated"""
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
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

df['rsi'] = calculate_rsi(df['close'])
df['atr'] = calculate_atr(df)
df['body'] = abs(df['close'] - df['open'])
df['body_pct'] = (df['body'] / df['open']) * 100
df['price_change'] = df['close'].pct_change() * 100
df['is_green'] = (df['close'] > df['open']).astype(int)
df['atr_pct'] = (df['atr'] / df['close']) * 100

# Check pattern triggers
vol_spikes = df[(df['atr_pct'] > 5.0) & (df['rsi'] > 70)]
parabolic = df[(df['body_pct'] > 3.0) & (df['rsi'] > 70) & (df['is_green'] == 1)]
extreme = df[(df['price_change'] > 5.0) & (df['is_green'] == 1)]

print(f"VOL_SPIKE patterns: {len(vol_spikes)}")
print(f"PARABOLIC patterns: {len(parabolic)}")
print(f"EXTREME_GREEN patterns: {len(extreme)}")
print(f"Total pattern triggers: {len(vol_spikes) + len(parabolic) + len(extreme)}")
print()

# Check a few examples
if len(vol_spikes) > 0:
    print("First VOL_SPIKE example:")
    example = vol_spikes.iloc[0]
    print(f"  High: {example['high']:.4f}")
    print(f"  ATR: {example['atr']:.4f}")
    print(f"  Limit at +0.5 ATR: {example['high'] + 0.5*example['atr']:.4f}")
    print(f"  SL at +0.3 ATR: {example['high'] + 0.3*example['atr']:.4f}")
    print()

# Check if limit orders would fill
def check_fills():
    fills = 0
    no_fills = 0

    for idx in vol_spikes.index[:10]:
        pattern_row = df.loc[idx]
        limit_price = pattern_row['high'] + 0.5 * pattern_row['atr']

        # Check next 20 bars
        for j in range(idx+1, min(idx+21, len(df))):
            if df.loc[j, 'high'] >= limit_price:
                fills += 1
                break
        else:
            no_fills += 1

    print(f"Limit fill check (first 10 VOL_SPIKE patterns, 0.5 ATR offset, 20 bar wait):")
    print(f"  Filled: {fills}")
    print(f"  Not filled: {no_fills}")

check_fills()
