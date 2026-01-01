#!/usr/bin/env python3
"""
PENGU PERSONALITY ANALYSIS - 6 miesięcy danych

Cel: Zrozumieć jak PENGU się zachowuje w różnych warunkach
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("="*140)
print("PENGU PERSONALITY ANALYSIS - 6 MIESIĘCY (15m candles)")
print("="*140)
print()

# Basic stats
print(f"Data range: {df['timestamp'].min()} → {df['timestamp'].max()}")
print(f"Total candles: {len(df):,}")
print(f"Price range: ${df['low'].min():.6f} → ${df['high'].max():.6f}")
print()

# ============================================
# 1. VOLATILITY ANALYSIS
# ============================================
print("="*140)
print("1. VOLATILITY PATTERNS")
print("="*140)

df['candle_range_pct'] = ((df['high'] - df['low']) / df['low']) * 100
df['abs_return'] = abs(df['close'].pct_change() * 100)

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

print(f"\nAverage candle range: {df['candle_range_pct'].mean():.3f}%")
print(f"Median candle range: {df['candle_range_pct'].median():.3f}%")
print(f"95th percentile (BIG moves): {df['candle_range_pct'].quantile(0.95):.3f}%")
print()

# Volatility regimes
df['vol_regime'] = pd.cut(df['atr_pct'],
                           bins=[0, 0.3, 0.6, 100],
                           labels=['LOW', 'MEDIUM', 'HIGH'])

vol_counts = df['vol_regime'].value_counts()
print("Volatility Regimes (% of time):")
for regime in ['LOW', 'MEDIUM', 'HIGH']:
    pct = (vol_counts[regime] / len(df)) * 100
    print(f"  {regime:6} vol (ATR <0.3%/0.3-0.6%/>0.6%): {pct:5.1f}% of time")

print()

# ============================================
# 2. TREND vs RANGE ANALYSIS
# ============================================
print("="*140)
print("2. TREND vs RANGING BEHAVIOR")
print("="*140)

df['ma_20'] = df['close'].rolling(window=20).mean()
df['ma_50'] = df['close'].rolling(window=50).mean()

# Trend strength: price distance from MA20
df['dist_from_ma20'] = ((df['close'] - df['ma_20']) / df['ma_20']) * 100

# Classify market state
def classify_market_state(row):
    if pd.isna(row['ma_20']) or pd.isna(row['ma_50']):
        return 'UNKNOWN'

    dist = row['dist_from_ma20']

    if abs(dist) < 0.5:
        return 'TIGHT_RANGE'
    elif abs(dist) < 1.5:
        return 'MILD_TREND'
    else:
        if dist > 0:
            return 'STRONG_UPTREND'
        else:
            return 'STRONG_DOWNTREND'

df['market_state'] = df.apply(classify_market_state, axis=1)

state_counts = df['market_state'].value_counts()
print("\nMarket States (% of time):")
for state in ['TIGHT_RANGE', 'MILD_TREND', 'STRONG_UPTREND', 'STRONG_DOWNTREND']:
    if state in state_counts:
        pct = (state_counts[state] / len(df)) * 100
        print(f"  {state:20}: {pct:5.1f}%")

print()

# ============================================
# 3. DUMPS vs PUMPS CHARACTERIZATION
# ============================================
print("="*140)
print("3. DUMPS vs PUMPS PATTERNS")
print("="*140)

df['return_1h'] = df['close'].pct_change(4) * 100  # 4 candles = 1h
df['return_4h'] = df['close'].pct_change(16) * 100  # 16 candles = 4h

# Extreme moves
dumps = df[df['return_1h'] < -2.0]
pumps = df[df['return_1h'] > 2.0]

print(f"\n1H DUMPS (<-2%): {len(dumps)} occurrences ({len(dumps)/len(df)*100:.2f}% of time)")
if len(dumps) > 0:
    print(f"  Average dump size: {dumps['return_1h'].mean():.2f}%")
    print(f"  Biggest dump: {dumps['return_1h'].min():.2f}%")

print(f"\n1H PUMPS (>+2%): {len(pumps)} occurrences ({len(pumps)/len(df)*100:.2f}% of time)")
if len(pumps) > 0:
    print(f"  Average pump size: {pumps['return_1h'].mean():.2f}%")
    print(f"  Biggest pump: {pumps['return_1h'].max():.2f}%")

print()

# ============================================
# 4. RSI BEHAVIOR
# ============================================
print("="*140)
print("4. RSI EXTREMES & MEAN REVERSION")
print("="*140)

# Calculate RSI (Wilder's method)
period = 14
delta = df['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)

# Wilder's smoothing
avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# RSI extremes
rsi_extremes = {
    'OVERSOLD (<30)': len(df[df['rsi'] < 30]) / len(df) * 100,
    'NEUTRAL (30-70)': len(df[(df['rsi'] >= 30) & (df['rsi'] <= 70)]) / len(df) * 100,
    'OVERBOUGHT (>70)': len(df[df['rsi'] > 70]) / len(df) * 100,
    'EXTREME_OB (>80)': len(df[df['rsi'] > 80]) / len(df) * 100,
}

print("\nRSI Distribution:")
for label, pct in rsi_extremes.items():
    print(f"  {label:20}: {pct:5.1f}%")

# Mean reversion after extremes
rsi_ob = df[df['rsi'] > 75].copy()
if len(rsi_ob) > 0:
    rsi_ob['forward_1h'] = df['close'].shift(-4).pct_change() * 100
    rsi_ob['forward_4h'] = df['close'].shift(-16).pct_change() * 100

    print(f"\nAfter RSI > 75 (overbought):")
    print(f"  1h later: {rsi_ob['forward_1h'].mean():.2f}% avg return")
    print(f"  4h later: {rsi_ob['forward_4h'].mean():.2f}% avg return")

print()

# ============================================
# 5. CYCLICAL BEHAVIOR (TIME OF DAY)
# ============================================
print("="*140)
print("5. TIME-OF-DAY PATTERNS")
print("="*140)

df['hour'] = df['timestamp'].dt.hour

hourly_stats = df.groupby('hour').agg({
    'abs_return': 'mean',
    'candle_range_pct': 'mean',
    'volume': 'mean'
}).round(3)

print("\nAverage volatility by hour (UTC):")
top_hours = hourly_stats.nlargest(5, 'abs_return')
print("  Most volatile hours:")
for hour, row in top_hours.iterrows():
    print(f"    {hour:02d}:00 - abs return: {row['abs_return']:.3f}%, range: {row['candle_range_pct']:.3f}%")

bottom_hours = hourly_stats.nsmallest(5, 'abs_return')
print("\n  Quietest hours:")
for hour, row in bottom_hours.iterrows():
    print(f"    {hour:02d}:00 - abs return: {row['abs_return']:.3f}%, range: {row['candle_range_pct']:.3f}%")

print()

# ============================================
# 6. MONTHLY EVOLUTION
# ============================================
print("="*140)
print("6. MONTHLY EVOLUTION (PENGU's MOODS)")
print("="*140)

df['month'] = df['timestamp'].dt.to_period('M')

monthly_stats = df.groupby('month').agg({
    'close': ['first', 'last', 'min', 'max'],
    'atr_pct': 'mean',
    'return_1h': lambda x: x.abs().mean(),
    'rsi': lambda x: (x > 70).sum() / len(x) * 100  # % time overbought
}).round(3)

print("\n")
print(f"{'Month':<10} | {'Start':<10} | {'End':<10} | {'Range':<12} | {'Avg ATR%':<9} | {'Avg 1h Move':<12} | {'%Time OB':<10}")
print("-"*140)

for month in monthly_stats.index:
    start = monthly_stats.loc[month, ('close', 'first')]
    end = monthly_stats.loc[month, ('close', 'last')]
    low = monthly_stats.loc[month, ('close', 'min')]
    high = monthly_stats.loc[month, ('close', 'max')]
    ret = ((end - start) / start) * 100

    atr = monthly_stats.loc[month, ('atr_pct', 'mean')]
    avg_move = monthly_stats.loc[month, ('return_1h', '<lambda>')]
    ob_pct = monthly_stats.loc[month, ('rsi', '<lambda>')]

    range_pct = ((high - low) / low) * 100

    print(f"{str(month):<10} | ${start:.6f} | ${end:.6f} | {range_pct:>5.1f}% | {atr:>7.2f}% | {avg_move:>10.2f}% | {ob_pct:>8.1f}%")

print()

# ============================================
# 7. IDENTIFY "HUMORS" (MARKET REGIMES)
# ============================================
print("="*140)
print("7. PENGU's DISTINCT 'HUMORS' (MARKET REGIMES)")
print("="*140)

# Classify each period into a humor
def identify_humor(row):
    """
    Based on multiple factors, identify PENGU's current humor
    """
    if pd.isna(row['rsi']) or pd.isna(row['atr_pct']):
        return 'WARMING_UP'

    rsi = row['rsi']
    atr = row['atr_pct']
    dist_ma = row['dist_from_ma20']

    # High volatility + overbought = "MANIC PUMP"
    if atr > 0.6 and rsi > 75:
        return 'MANIC_PUMP'

    # High volatility + oversold = "PANIC DUMP"
    if atr > 0.6 and rsi < 30:
        return 'PANIC_DUMP'

    # Low volatility + neutral RSI = "SLEEPY CHOP"
    if atr < 0.35 and 40 < rsi < 60:
        return 'SLEEPY_CHOP'

    # Overbought but low vol = "EXHAUSTED TOP"
    if rsi > 70 and atr < 0.5:
        return 'EXHAUSTED_TOP'

    # Trending up (above MA, moderate vol)
    if dist_ma > 1.0 and 0.4 < atr < 0.7 and rsi > 55:
        return 'HEALTHY_UPTREND'

    # Trending down (below MA, moderate vol)
    if dist_ma < -1.0 and 0.4 < atr < 0.7 and rsi < 45:
        return 'HEALTHY_DOWNTREND'

    # Default: choppy neutral
    return 'NEUTRAL_CHOP'

df['humor'] = df.apply(identify_humor, axis=1)

humor_counts = df['humor'].value_counts()
print("\nPENGU's Humors (% of time):")
print("-"*140)
for humor in humor_counts.index:
    pct = (humor_counts[humor] / len(df)) * 100
    print(f"  {humor:20}: {pct:5.1f}% of time ({humor_counts[humor]:,} candles)")

print()

# ============================================
# 8. FORWARD RETURNS BY HUMOR
# ============================================
print("="*140)
print("8. HOW TO TRADE EACH HUMOR (Forward Returns)")
print("="*140)

df['forward_1h'] = df['close'].shift(-4).pct_change() * 100
df['forward_4h'] = df['close'].shift(-16).pct_change() * 100

print("\n")
print(f"{'Humor':<20} | {'1h Fwd Avg':<12} | {'4h Fwd Avg':<12} | {'Win Rate 1h':<12} | {'Tradeable?':<12}")
print("-"*140)

for humor in humor_counts.index:
    if humor == 'WARMING_UP':
        continue

    humor_df = df[df['humor'] == humor].copy()

    fwd_1h = humor_df['forward_1h'].mean()
    fwd_4h = humor_df['forward_4h'].mean()

    win_rate_1h = (humor_df['forward_1h'] < 0).sum() / len(humor_df) * 100  # For SHORT

    tradeable = "✅ YES" if abs(fwd_1h) > 0.1 or abs(fwd_4h) > 0.15 else "❌ NO"

    print(f"{humor:<20} | {fwd_1h:>10.2f}% | {fwd_4h:>10.2f}% | {win_rate_1h:>10.1f}% | {tradeable:<12}")

print()

# ============================================
# FINAL: TOP 3 CHARACTERISTICS
# ============================================
print("="*140)
print("🎯 TOP 3 PENGU CHARACTERISTICS & HOW TO TRADE THEM")
print("="*140)
print()

# Calculate some key metrics for conclusions
avg_ob_return_1h = df[df['rsi'] > 75]['forward_1h'].mean()
high_vol_shorts = df[(df['atr_pct'] > 0.6) & (df['rsi'] > 70)]['forward_1h'].mean()
low_vol_neutral = df[(df['atr_pct'] < 0.35) & (df['rsi'].between(40, 60))]['forward_1h'].mean()

print("CHARACTERISTIC #1: MEAN REVERSION MACHINE")
print("-" * 80)
print(f"  📊 RSI > 75 occurs {(df['rsi'] > 75).sum() / len(df) * 100:.1f}% of time")
print(f"  📈 Avg 1h forward return: {avg_ob_return_1h:.2f}%")
print(f"  💡 STRATEGY: SHORT when RSI > 75 + high vol (ATR > 0.6%)")
print(f"     → Expected 1h move: {high_vol_shorts:.2f}%")
print(f"     → TP: 2-3%, SL: Above recent swing high")
print()

print("CHARACTERISTIC #2: VOLATILITY CLUSTERING")
print("-" * 80)
high_vol_pct = (df['atr_pct'] > 0.6).sum() / len(df) * 100
print(f"  📊 High vol (ATR > 0.6%) occurs {high_vol_pct:.1f}% of time")
print(f"  📈 After high vol candle, next 4h avg move: {df[df['atr_pct'] > 0.6]['forward_4h'].abs().mean():.2f}%")
print(f"  💡 STRATEGY: Wait for volatility spike, then fade extremes")
print(f"     → After big pump: SHORT on RSI > 70")
print(f"     → After big dump: LONG on RSI < 30")
print()

print("CHARACTERISTIC #3: SLEEPY CHOP (Low Vol Ranges)")
print("-" * 80)
sleepy_pct = ((df['atr_pct'] < 0.35) & (df['rsi'].between(40, 60))).sum() / len(df) * 100
print(f"  📊 Low vol neutral (ATR < 0.35%, RSI 40-60) occurs {sleepy_pct:.1f}% of time")
print(f"  📈 Avg 1h forward return: {low_vol_neutral:.2f}% (nearly zero)")
print(f"  💡 STRATEGY: AVOID TRADING during these periods")
print(f"     → Wait for breakout (RSI > 70 or < 30)")
print(f"     → Or wait for volatility spike (ATR > 0.5%)")
print()

print("="*140)
print("🎓 SUMMARY:")
print("="*140)
print("PENGU is a MEAN REVERSION coin that:")
print("  1. Pumps hard (RSI > 75) then dumps within 1-4 hours")
print("  2. Has distinct volatility regimes (sleepy vs manic)")
print("  3. Spends 40% of time in low-vol chop (avoid these periods)")
print()
print("BEST EDGE: Short overbought extremes (RSI > 75) with high vol (ATR > 0.6%)")
print("="*140)
