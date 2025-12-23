"""
Analyze what happens AFTER weekly tops form.
Key question: When does the top form within the week, and what's the drawdown?
"""
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('trading/melania_3months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

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
df['body_size'] = abs(df['close'] - df['open'])
df['wick_ratio'] = df['wick_top'] / (df['high'] - df['low'] + 0.0001)

# Add week info
df['week'] = df['timestamp'].dt.isocalendar().week
df['year'] = df['timestamp'].dt.isocalendar().year
df['year_week'] = df['year'].astype(str) + '_W' + df['week'].astype(str)
df['day_of_week'] = df['timestamp'].dt.dayofweek  # Monday=0, Sunday=6

# Analyze each week
print("=" * 100)
print("POST-TOP BEHAVIOR ANALYSIS")
print("=" * 100)

opportunities = []

for week in df['year_week'].unique():
    week_data = df[df['year_week'] == week].copy().reset_index(drop=True)
    if len(week_data) < 10:
        continue

    # Find weekly high
    top_idx = week_data['high'].idxmax()
    top_row = week_data.loc[top_idx]
    top_price = top_row['high']
    top_timestamp = top_row['timestamp']
    top_rsi = top_row['rsi']
    top_wick_ratio = top_row['wick_ratio']

    # When did top occur? (as % through the week)
    top_position_pct = (top_idx / len(week_data)) * 100

    # Data AFTER the top
    after_top = week_data.loc[top_idx:].copy()

    if len(after_top) < 2:
        continue

    # Calculate drawdown from top
    lowest_after = after_top['low'].min()
    max_dd_pct = ((lowest_after - top_price) / top_price) * 100

    # How many candles until lowest point?
    lowest_idx_local = after_top['low'].idxmin()
    candles_to_low = lowest_idx_local - top_idx

    # Week close vs top
    week_close = week_data.iloc[-1]['close']
    close_vs_top_pct = ((week_close - top_price) / top_price) * 100

    # Week stats
    week_open = week_data.iloc[0]['open']
    week_return = ((week_close - week_open) / week_open) * 100

    # Volume at top vs avg
    avg_vol = week_data['volume'].mean()
    top_vol_ratio = top_row['volume'] / avg_vol if avg_vol > 0 else 1.0

    opportunities.append({
        'week': week,
        'top_timestamp': top_timestamp,
        'top_price': top_price,
        'top_rsi': top_rsi,
        'top_wick_ratio': top_wick_ratio,
        'top_vol_ratio': top_vol_ratio,
        'top_position_pct': top_position_pct,
        'candles_after_top': len(after_top) - 1,
        'max_dd_pct': max_dd_pct,
        'candles_to_low': candles_to_low,
        'close_vs_top_pct': close_vs_top_pct,
        'week_return': week_return,
        'top_day_of_week': top_row['day_of_week'],
    })

opp_df = pd.DataFrame(opportunities)

print(f"\nTotal weeks: {len(opp_df)}")
print(f"\nAverage drawdown from weekly top: {opp_df['max_dd_pct'].mean():.2f}%")
print(f"Median drawdown: {opp_df['max_dd_pct'].median():.2f}%")
print(f"Best drawdown: {opp_df['max_dd_pct'].min():.2f}%")
print()

print(f"Average position of top within week: {opp_df['top_position_pct'].mean():.1f}%")
print(f"Average candles after top: {opp_df['candles_after_top'].mean():.1f}")
print()

# Days of week (0=Mon, 6=Sun)
day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
print("Weekly tops by day of week:")
for day in range(7):
    count = (opp_df['top_day_of_week'] == day).sum()
    print(f"  {day_names[day]:10s}: {count} tops")
print()

# Profitable shorts (drawdown > -2%)
good_shorts = opp_df[opp_df['max_dd_pct'] < -2.0]
print(f"Weeks with >2% drawdown from top: {len(good_shorts)}/{len(opp_df)} ({len(good_shorts)/len(opp_df)*100:.1f}%)")
print(f"Average drawdown on these: {good_shorts['max_dd_pct'].mean():.2f}%")
print()

# Best shorts (drawdown > -5%)
best_shorts = opp_df[opp_df['max_dd_pct'] < -5.0]
print(f"Weeks with >5% drawdown from top: {len(best_shorts)}/{len(opp_df)} ({len(best_shorts)/len(opp_df)*100:.1f}%)")
print(f"Average drawdown on these: {best_shorts['max_dd_pct'].mean():.2f}%")
print()

# Analysis: What characteristics lead to big drawdowns?
print("=" * 100)
print("CHARACTERISTICS OF WEEKS WITH >5% DRAWDOWN")
print("=" * 100)
if len(best_shorts) > 0:
    print(f"RSI at top - Mean: {best_shorts['top_rsi'].mean():.1f}, Median: {best_shorts['top_rsi'].median():.1f}")
    print(f"Wick ratio - Mean: {best_shorts['top_wick_ratio'].mean():.2%}, Median: {best_shorts['top_wick_ratio'].median():.2%}")
    print(f"Volume ratio - Mean: {best_shorts['top_vol_ratio'].mean():.2f}x, Median: {best_shorts['top_vol_ratio'].median():.2f}x")
    print(f"Top position - Mean: {best_shorts['top_position_pct'].mean():.1f}%, Median: {best_shorts['top_position_pct'].median():.1f}%")
    print()
    print("Details of best short opportunities:")
    print(best_shorts[['week', 'top_rsi', 'top_wick_ratio', 'top_position_pct', 'max_dd_pct', 'week_return']].to_string(index=False))
print()

# Early top vs late top
early_tops = opp_df[opp_df['top_position_pct'] < 50]
late_tops = opp_df[opp_df['top_position_pct'] >= 50]

print("=" * 100)
print("EARLY TOPS (first half) vs LATE TOPS (second half)")
print("=" * 100)
print(f"Early tops ({len(early_tops)}): Avg drawdown = {early_tops['max_dd_pct'].mean():.2f}%")
print(f"Late tops ({len(late_tops)}): Avg drawdown = {late_tops['max_dd_pct'].mean():.2f}%")
print()

# High RSI tops
high_rsi_tops = opp_df[opp_df['top_rsi'] > 75]
low_rsi_tops = opp_df[opp_df['top_rsi'] <= 75]

print("=" * 100)
print("HIGH RSI TOPS (>75) vs NORMAL RSI TOPS (<=75)")
print("=" * 100)
print(f"High RSI tops ({len(high_rsi_tops)}): Avg drawdown = {high_rsi_tops['max_dd_pct'].mean():.2f}%")
print(f"Normal RSI tops ({len(low_rsi_tops)}): Avg drawdown = {low_rsi_tops['max_dd_pct'].mean():.2f}%")
print()

# Big wick tops
big_wick_tops = opp_df[opp_df['top_wick_ratio'] > 0.4]
small_wick_tops = opp_df[opp_df['top_wick_ratio'] <= 0.4]

print("=" * 100)
print("BIG WICK TOPS (>40%) vs SMALL WICK TOPS (<=40%)")
print("=" * 100)
print(f"Big wick tops ({len(big_wick_tops)}): Avg drawdown = {big_wick_tops['max_dd_pct'].mean():.2f}%")
print(f"Small wick tops ({len(small_wick_tops)}): Avg drawdown = {small_wick_tops['max_dd_pct'].mean():.2f}%")
print()

# Combination: RSI > 75 AND wick > 40%
combo_tops = opp_df[(opp_df['top_rsi'] > 75) & (opp_df['top_wick_ratio'] > 0.4)]
print("=" * 100)
print("COMBO: RSI > 75 AND WICK > 40%")
print("=" * 100)
print(f"Count: {len(combo_tops)}")
if len(combo_tops) > 0:
    print(f"Average drawdown: {combo_tops['max_dd_pct'].mean():.2f}%")
    print(combo_tops[['week', 'top_rsi', 'top_wick_ratio', 'max_dd_pct', 'week_return']].to_string(index=False))
print()

# Correlations
print("=" * 100)
print("CORRELATIONS WITH DRAWDOWN (more negative = better for shorts)")
print("=" * 100)
correlations = {
    'RSI at top': opp_df['top_rsi'].corr(opp_df['max_dd_pct']),
    'Wick ratio': opp_df['top_wick_ratio'].corr(opp_df['max_dd_pct']),
    'Volume ratio': opp_df['top_vol_ratio'].corr(opp_df['max_dd_pct']),
    'Top position in week': opp_df['top_position_pct'].corr(opp_df['max_dd_pct']),
}
for key, val in sorted(correlations.items(), key=lambda x: x[1]):
    print(f"{key:25s}: {val:+.3f}")

opp_df.to_csv('trading/melania_post_top_opportunities.csv', index=False)
print(f"\nSaved analysis to: trading/melania_post_top_opportunities.csv")
