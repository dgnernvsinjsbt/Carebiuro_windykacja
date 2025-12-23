"""
Deep pattern analysis for MELANIA shorts.
Goal: Find MORE profitable setups, not just weekly tops.
Look for: intraday patterns, volume spikes, consecutive moves, specific sequences.
"""
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

# Calculate indicators
df['rsi'] = calculate_rsi(df['close'])
df['atr'] = calculate_atr(df)
df['atr_pct'] = (df['atr'] / df['close']) * 100

# Price action features
df['body'] = abs(df['close'] - df['open'])
df['body_pct'] = (df['body'] / df['open']) * 100
df['wick_top'] = df['high'] - df[['open', 'close']].max(axis=1)
df['wick_bot'] = df[['open', 'close']].min(axis=1) - df['low']
df['wick_top_pct'] = (df['wick_top'] / df['open']) * 100
df['range_pct'] = ((df['high'] - df['low']) / df['open']) * 100
df['is_green'] = (df['close'] > df['open']).astype(int)
df['is_red'] = (df['close'] < df['open']).astype(int)

# Volume features
df['vol_ma20'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma20']

# Momentum features
df['price_change'] = df['close'].pct_change() * 100
df['high_change'] = df['high'].pct_change() * 100

# Sequential patterns
df['green_streak'] = 0
df['red_streak'] = 0
streak = 0
for i in range(1, len(df)):
    if df.loc[i, 'is_green']:
        streak = streak + 1 if df.loc[i-1, 'is_green'] else 1
    else:
        streak = 0
    df.loc[i, 'green_streak'] = streak

streak = 0
for i in range(1, len(df)):
    if df.loc[i, 'is_red']:
        streak = streak + 1 if df.loc[i-1, 'is_red'] else 1
    else:
        streak = 0
    df.loc[i, 'red_streak'] = streak

# Look for local highs
df['is_local_high'] = False
lookback = 5
for i in range(lookback, len(df) - lookback):
    if df.loc[i, 'high'] == df.loc[i-lookback:i+lookback+1, 'high'].max():
        df.loc[i, 'is_local_high'] = True

# Analyze what happens after specific patterns
print("=" * 120)
print("PATTERN ANALYSIS - What predicts drops?")
print("=" * 120)

# Pattern 1: RSI spike with volume
print("\n1. RSI SPIKE + VOLUME SURGE (RSI > 70, Vol > 2x avg)")
pattern1 = df[(df['rsi'] > 70) & (df['vol_ratio'] > 2.0)].copy()
pattern1['forward_return_4h'] = -((df['low'].shift(-16) - pattern1['close']) / pattern1['close'] * 100)
pattern1['forward_return_8h'] = -((df['low'].shift(-32) - pattern1['close']) / pattern1['close'] * 100)
pattern1['forward_return_12h'] = -((df['low'].shift(-48) - pattern1['close']) / pattern1['close'] * 100)

print(f"Occurrences: {len(pattern1)}")
print(f"Avg drop after 4h:  {pattern1['forward_return_4h'].mean():.2f}%")
print(f"Avg drop after 8h:  {pattern1['forward_return_8h'].mean():.2f}%")
print(f"Avg drop after 12h: {pattern1['forward_return_12h'].mean():.2f}%")
print(f"Win rate (>2% drop in 12h): {(pattern1['forward_return_12h'] > 2).sum() / len(pattern1) * 100:.1f}%")

# Pattern 2: Green streak exhaustion
print("\n2. GREEN STREAK EXHAUSTION (3+ green candles, RSI > 65)")
pattern2 = df[(df['green_streak'] >= 3) & (df['rsi'] > 65)].copy()
pattern2['forward_return_4h'] = -((df['low'].shift(-16) - pattern2['close']) / pattern2['close'] * 100)
pattern2['forward_return_8h'] = -((df['low'].shift(-32) - pattern2['close']) / pattern2['close'] * 100)

print(f"Occurrences: {len(pattern2)}")
print(f"Avg drop after 4h:  {pattern2['forward_return_4h'].mean():.2f}%")
print(f"Avg drop after 8h:  {pattern2['forward_return_8h'].mean():.2f}%")
print(f"Win rate (>2% drop in 8h): {(pattern2['forward_return_8h'] > 2).sum() / len(pattern2) * 100:.1f}%")

# Pattern 3: Big wick rejection
print("\n3. BIG TOP WICK REJECTION (wick > 50% of range, RSI > 60)")
pattern3 = df[(df['wick_top'] / (df['high'] - df['low'] + 0.0001) > 0.5) & (df['rsi'] > 60)].copy()
pattern3['forward_return_4h'] = -((df['low'].shift(-16) - pattern3['close']) / pattern3['close'] * 100)
pattern3['forward_return_8h'] = -((df['low'].shift(-32) - pattern3['close']) / pattern3['close'] * 100)

print(f"Occurrences: {len(pattern3)}")
print(f"Avg drop after 4h:  {pattern3['forward_return_4h'].mean():.2f}%")
print(f"Avg drop after 8h:  {pattern3['forward_return_8h'].mean():.2f}%")
print(f"Win rate (>2% drop in 8h): {(pattern3['forward_return_8h'] > 2).sum() / len(pattern3) * 100:.1f}%")

# Pattern 4: Parabolic move (large body + high RSI)
print("\n4. PARABOLIC MOVE (body > 3%, RSI > 70)")
pattern4 = df[(df['body_pct'] > 3.0) & (df['rsi'] > 70) & (df['is_green'] == 1)].copy()
pattern4['forward_return_4h'] = -((df['low'].shift(-16) - pattern4['close']) / pattern4['close'] * 100)
pattern4['forward_return_8h'] = -((df['low'].shift(-32) - pattern4['close']) / pattern4['close'] * 100)

print(f"Occurrences: {len(pattern4)}")
print(f"Avg drop after 4h:  {pattern4['forward_return_4h'].mean():.2f}%")
print(f"Avg drop after 8h:  {pattern4['forward_return_8h'].mean():.2f}%")
print(f"Win rate (>2% drop in 8h): {(pattern4['forward_return_8h'] > 2).sum() / len(pattern4) * 100:.1f}%")

# Pattern 5: Failed breakout (new high but closes below open)
print("\n5. FAILED BREAKOUT (local high, closes red)")
pattern5 = df[(df['is_local_high']) & (df['is_red'] == 1) & (df['rsi'] > 60)].copy()
pattern5['forward_return_4h'] = -((df['low'].shift(-16) - pattern5['close']) / pattern5['close'] * 100)
pattern5['forward_return_8h'] = -((df['low'].shift(-32) - pattern5['close']) / pattern5['close'] * 100)

print(f"Occurrences: {len(pattern5)}")
print(f"Avg drop after 4h:  {pattern5['forward_return_4h'].mean():.2f}%")
print(f"Avg drop after 8h:  {pattern5['forward_return_8h'].mean():.2f}%")
print(f"Win rate (>2% drop in 8h): {(pattern5['forward_return_8h'] > 2).sum() / len(pattern5) * 100:.1f}%")

# Pattern 6: Volatility spike
print("\n6. VOLATILITY SPIKE (ATR > 5%, RSI > 70)")
pattern6 = df[(df['atr_pct'] > 5.0) & (df['rsi'] > 70)].copy()
pattern6['forward_return_4h'] = -((df['low'].shift(-16) - pattern6['close']) / pattern6['close'] * 100)
pattern6['forward_return_8h'] = -((df['low'].shift(-32) - pattern6['close']) / pattern6['close'] * 100)

print(f"Occurrences: {len(pattern6)}")
print(f"Avg drop after 4h:  {pattern6['forward_return_4h'].mean():.2f}%")
print(f"Avg drop after 8h:  {pattern6['forward_return_8h'].mean():.2f}%")
print(f"Win rate (>2% drop in 8h): {(pattern6['forward_return_8h'] > 2).sum() / len(pattern6) * 100:.1f}%")

# Pattern 7: Extreme moves (any 5%+ move)
print("\n7. EXTREME GREEN CANDLE (price change > 5%)")
pattern7 = df[(df['price_change'] > 5.0)].copy()
pattern7['forward_return_4h'] = -((df['low'].shift(-16) - pattern7['close']) / pattern7['close'] * 100)
pattern7['forward_return_8h'] = -((df['low'].shift(-32) - pattern7['close']) / pattern7['close'] * 100)

print(f"Occurrences: {len(pattern7)}")
print(f"Avg drop after 4h:  {pattern7['forward_return_4h'].mean():.2f}%")
print(f"Avg drop after 8h:  {pattern7['forward_return_8h'].mean():.2f}%")
print(f"Win rate (>2% drop in 8h): {(pattern7['forward_return_8h'] > 2).sum() / len(pattern7) * 100:.1f}%")

# Pattern 8: Combo - multiple signals
print("\n8. COMBO SIGNAL (RSI > 75, Vol > 1.5x, wick > 30%)")
pattern8 = df[
    (df['rsi'] > 75) &
    (df['vol_ratio'] > 1.5) &
    (df['wick_top'] / (df['high'] - df['low'] + 0.0001) > 0.3)
].copy()
pattern8['forward_return_4h'] = -((df['low'].shift(-16) - pattern8['close']) / pattern8['close'] * 100)
pattern8['forward_return_8h'] = -((df['low'].shift(-32) - pattern8['close']) / pattern8['close'] * 100)
pattern8['forward_return_12h'] = -((df['low'].shift(-48) - pattern8['close']) / pattern8['close'] * 100)

print(f"Occurrences: {len(pattern8)}")
print(f"Avg drop after 4h:  {pattern8['forward_return_4h'].mean():.2f}%")
print(f"Avg drop after 8h:  {pattern8['forward_return_8h'].mean():.2f}%")
print(f"Avg drop after 12h: {pattern8['forward_return_12h'].mean():.2f}%")
print(f"Win rate (>3% drop in 12h): {(pattern8['forward_return_12h'] > 3).sum() / len(pattern8) * 100:.1f}%")

# Find BEST pattern
print("\n" + "=" * 120)
print("SUMMARY - BEST PATTERNS RANKED BY WIN RATE (>2% drop in 8h)")
print("=" * 120)

patterns = [
    ('RSI Spike + Volume', len(pattern1), (pattern1['forward_return_8h'] > 2).sum() / len(pattern1) * 100 if len(pattern1) > 0 else 0, pattern1['forward_return_8h'].mean() if len(pattern1) > 0 else 0),
    ('Green Streak Exhaustion', len(pattern2), (pattern2['forward_return_8h'] > 2).sum() / len(pattern2) * 100 if len(pattern2) > 0 else 0, pattern2['forward_return_8h'].mean() if len(pattern2) > 0 else 0),
    ('Big Wick Rejection', len(pattern3), (pattern3['forward_return_8h'] > 2).sum() / len(pattern3) * 100 if len(pattern3) > 0 else 0, pattern3['forward_return_8h'].mean() if len(pattern3) > 0 else 0),
    ('Parabolic Move', len(pattern4), (pattern4['forward_return_8h'] > 2).sum() / len(pattern4) * 100 if len(pattern4) > 0 else 0, pattern4['forward_return_8h'].mean() if len(pattern4) > 0 else 0),
    ('Failed Breakout', len(pattern5), (pattern5['forward_return_8h'] > 2).sum() / len(pattern5) * 100 if len(pattern5) > 0 else 0, pattern5['forward_return_8h'].mean() if len(pattern5) > 0 else 0),
    ('Volatility Spike', len(pattern6), (pattern6['forward_return_8h'] > 2).sum() / len(pattern6) * 100 if len(pattern6) > 0 else 0, pattern6['forward_return_8h'].mean() if len(pattern6) > 0 else 0),
    ('Extreme Green Candle', len(pattern7), (pattern7['forward_return_8h'] > 2).sum() / len(pattern7) * 100 if len(pattern7) > 0 else 0, pattern7['forward_return_8h'].mean() if len(pattern7) > 0 else 0),
    ('Combo Signal', len(pattern8), (pattern8['forward_return_8h'] > 2).sum() / len(pattern8) * 100 if len(pattern8) > 0 else 0, pattern8['forward_return_8h'].mean() if len(pattern8) > 0 else 0),
]

patterns_df = pd.DataFrame(patterns, columns=['Pattern', 'Occurrences', 'Win_Rate_%', 'Avg_Drop_%'])
patterns_df = patterns_df.sort_values('Win_Rate_%', ascending=False)

print(patterns_df.to_string(index=False))

print("\n" + "=" * 120)
print("INSIGHT: Look for patterns with high occurrences AND high win rate for more trades!")
print("=" * 120)
