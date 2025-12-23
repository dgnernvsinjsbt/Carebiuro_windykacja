"""
Analyze MELANIA 3-month data to find weekly shorting opportunities.
Goal: Identify commonality at weekly tops for a profitable short strategy.
"""
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('trading/melania_3months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Data range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Total candles: {len(df)}")
print(f"Total weeks: {len(df) / (4 * 24 * 7):.1f}")
print()

# Calculate indicators
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
df['wick_top'] = df['high'] - df[['open', 'close']].max(axis=1)
df['wick_bottom'] = df[['open', 'close']].min(axis=1) - df['low']
df['body_size'] = abs(df['close'] - df['open'])
df['wick_ratio'] = df['wick_top'] / (df['high'] - df['low'] + 0.0001)

# Add week number
df['week'] = df['timestamp'].dt.isocalendar().week
df['year'] = df['timestamp'].dt.isocalendar().year
df['year_week'] = df['year'].astype(str) + '_W' + df['week'].astype(str)

# Identify weekly highs
weekly_highs = []
for week in df['year_week'].unique():
    week_data = df[df['year_week'] == week].copy()
    if len(week_data) == 0:
        continue

    # Find the highest point of the week
    max_idx = week_data['high'].idxmax()
    max_row = week_data.loc[max_idx]

    # Calculate week stats
    week_open = week_data.iloc[0]['open']
    week_close = week_data.iloc[-1]['close']
    week_high = week_data['high'].max()
    week_low = week_data['low'].min()
    week_return = ((week_close - week_open) / week_open) * 100

    # Volume surge at top
    avg_vol = week_data['volume'].mean()
    top_vol = max_row['volume']
    vol_ratio = top_vol / avg_vol if avg_vol > 0 else 1.0

    weekly_highs.append({
        'week': week,
        'timestamp': max_row['timestamp'],
        'price': max_row['high'],
        'rsi': max_row['rsi'],
        'atr': max_row['atr'],
        'wick_top': max_row['wick_top'],
        'wick_ratio': max_row['wick_ratio'],
        'body_size': max_row['body_size'],
        'volume': max_row['volume'],
        'vol_ratio': vol_ratio,
        'week_return': week_return,
        'week_high': week_high,
        'week_low': week_low,
        'week_range': week_high - week_low,
    })

weekly_df = pd.DataFrame(weekly_highs)

print("=" * 80)
print("WEEKLY TOPS ANALYSIS")
print("=" * 80)
print(f"Total weeks analyzed: {len(weekly_df)}")
print(f"Negative weeks: {(weekly_df['week_return'] < 0).sum()}")
print(f"Positive weeks: {(weekly_df['week_return'] > 0).sum()}")
print()

print("Weekly returns:")
print(weekly_df[['week', 'week_return']].to_string(index=False))
print()

print("=" * 80)
print("CHARACTERISTICS AT WEEKLY TOPS")
print("=" * 80)
print(f"RSI at tops - Mean: {weekly_df['rsi'].mean():.1f}, Median: {weekly_df['rsi'].median():.1f}")
print(f"RSI range: {weekly_df['rsi'].min():.1f} to {weekly_df['rsi'].max():.1f}")
print()

print(f"Wick ratio at tops - Mean: {weekly_df['wick_ratio'].mean():.2%}, Median: {weekly_df['wick_ratio'].median():.2%}")
print(f"Wick ratio range: {weekly_df['wick_ratio'].min():.2%} to {weekly_df['wick_ratio'].max():.2%}")
print()

print(f"Volume ratio at tops - Mean: {weekly_df['vol_ratio'].mean():.2f}x, Median: {weekly_df['vol_ratio'].median():.2f}x")
print()

# Find weeks where top had extreme characteristics
print("=" * 80)
print("EXTREME TOPS (potential short signals)")
print("=" * 80)

# Define thresholds
high_rsi_weeks = weekly_df[weekly_df['rsi'] > 70]
high_wick_weeks = weekly_df[weekly_df['wick_ratio'] > 0.4]
high_vol_weeks = weekly_df[weekly_df['vol_ratio'] > 1.5]

print(f"\nWeeks with RSI > 70 at top: {len(high_rsi_weeks)}")
if len(high_rsi_weeks) > 0:
    print(high_rsi_weeks[['week', 'rsi', 'week_return']].to_string(index=False))

print(f"\nWeeks with wick ratio > 40% at top: {len(high_wick_weeks)}")
if len(high_wick_weeks) > 0:
    print(high_wick_weeks[['week', 'wick_ratio', 'week_return']].to_string(index=False))

print(f"\nWeeks with volume spike > 1.5x at top: {len(high_vol_weeks)}")
if len(high_vol_weeks) > 0:
    print(high_vol_weeks[['week', 'vol_ratio', 'week_return']].to_string(index=False))

# Combination: RSI > 70 AND big wick
combo = weekly_df[(weekly_df['rsi'] > 70) & (weekly_df['wick_ratio'] > 0.3)]
print(f"\nWeeks with RSI > 70 AND wick > 30%: {len(combo)}")
if len(combo) > 0:
    print(combo[['week', 'rsi', 'wick_ratio', 'week_return']].to_string(index=False))

print("\n" + "=" * 80)
print("CORRELATION ANALYSIS")
print("=" * 80)
print("\nCorrelation with week return:")
correlations = {
    'RSI at top': weekly_df['rsi'].corr(weekly_df['week_return']),
    'Wick ratio': weekly_df['wick_ratio'].corr(weekly_df['week_return']),
    'Volume ratio': weekly_df['vol_ratio'].corr(weekly_df['week_return']),
    'ATR': weekly_df['atr'].corr(weekly_df['week_return']),
}
for key, val in sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True):
    print(f"{key:20s}: {val:+.3f}")

# Save for further analysis
weekly_df.to_csv('trading/melania_weekly_tops_analysis.csv', index=False)
print(f"\nSaved detailed analysis to: trading/melania_weekly_tops_analysis.csv")
