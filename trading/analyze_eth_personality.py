#!/usr/bin/env python3
"""
ETH PERSONALITY ANALYSIS - 6 miesięcy danych

Czy ETH ma lepsze wzorce niż PENGU?
"""
import pandas as pd
import numpy as np

df = pd.read_csv('ethusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("="*140)
print("ETH PERSONALITY ANALYSIS - 6 MIESIĘCY (15m candles)")
print("="*140)
print()

# Basic stats
print(f"Data range: {df['timestamp'].min()} → {df['timestamp'].max()}")
print(f"Total candles: {len(df):,}")
print(f"Price range: ${df['low'].min():.2f} → ${df['high'].max():.2f}")
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
    if regime in vol_counts:
        pct = (vol_counts[regime] / len(df)) * 100
        print(f"  {regime:6} vol: {pct:5.1f}% of time")

print()

# ============================================
# 2. TREND vs RANGE ANALYSIS
# ============================================
print("="*140)
print("2. TREND vs RANGING BEHAVIOR")
print("="*140)

df['ma_20'] = df['close'].rolling(window=20).mean()
df['ma_50'] = df['close'].rolling(window=50).mean()

df['dist_from_ma20'] = ((df['close'] - df['ma_20']) / df['ma_20']) * 100

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
# 3. DUMPS vs PUMPS
# ============================================
print("="*140)
print("3. DUMPS vs PUMPS PATTERNS")
print("="*140)

df['return_1h'] = df['close'].pct_change(4) * 100
df['return_4h'] = df['close'].pct_change(16) * 100

dumps = df[df['return_1h'] < -1.5]
pumps = df[df['return_1h'] > 1.5]

print(f"\n1H DUMPS (<-1.5%): {len(dumps)} occurrences ({len(dumps)/len(df)*100:.2f}% of time)")
if len(dumps) > 0:
    print(f"  Average dump size: {dumps['return_1h'].mean():.2f}%")
    print(f"  Biggest dump: {dumps['return_1h'].min():.2f}%")

print(f"\n1H PUMPS (>+1.5%): {len(pumps)} occurrences ({len(pumps)/len(df)*100:.2f}% of time)")
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

avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

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
rsi_ob = df[df['rsi'] > 70].copy()
if len(rsi_ob) > 0:
    rsi_ob.loc[:, 'forward_1h'] = df.loc[rsi_ob.index, 'close'].shift(-4).pct_change() * 100
    rsi_ob.loc[:, 'forward_4h'] = df.loc[rsi_ob.index, 'close'].shift(-16).pct_change() * 100

    print(f"\nAfter RSI > 70 (overbought):")
    print(f"  1h later: {rsi_ob['forward_1h'].mean():.2f}% avg return")
    print(f"  4h later: {rsi_ob['forward_4h'].mean():.2f}% avg return")

rsi_os = df[df['rsi'] < 30].copy()
if len(rsi_os) > 0:
    rsi_os.loc[:, 'forward_1h'] = df.loc[rsi_os.index, 'close'].shift(-4).pct_change() * 100
    rsi_os.loc[:, 'forward_4h'] = df.loc[rsi_os.index, 'close'].shift(-16).pct_change() * 100

    print(f"\nAfter RSI < 30 (oversold):")
    print(f"  1h later: {rsi_os['forward_1h'].mean():.2f}% avg return")
    print(f"  4h later: {rsi_os['forward_4h'].mean():.2f}% avg return")

print()

# ============================================
# 5. MONTHLY EVOLUTION
# ============================================
print("="*140)
print("5. MONTHLY EVOLUTION")
print("="*140)

df['month'] = df['timestamp'].dt.to_period('M')

monthly_stats = df.groupby('month').agg({
    'close': ['first', 'last', 'min', 'max'],
    'atr_pct': 'mean',
    'return_1h': lambda x: x.abs().mean(),
    'rsi': lambda x: (x > 70).sum() / len(x) * 100
}).round(3)

print("\n")
print(f"{'Month':<10} | {'Start':<10} | {'End':<10} | {'Return%':<9} | {'Avg ATR%':<9} | {'Avg 1h Move':<12} | {'%Time OB':<10}")
print("-"*140)

for month in monthly_stats.index:
    start = monthly_stats.loc[month, ('close', 'first')]
    end = monthly_stats.loc[month, ('close', 'last')]
    ret = ((end - start) / start) * 100

    atr = monthly_stats.loc[month, ('atr_pct', 'mean')]
    avg_move = monthly_stats.loc[month, ('return_1h', '<lambda>')]
    ob_pct = monthly_stats.loc[month, ('rsi', '<lambda>')]

    status = "📈" if ret > 0 else "📉"
    print(f"{str(month):<10} | ${start:>8.2f} | ${end:>8.2f} | {ret:>7.1f}% | {atr:>7.2f}% | {avg_move:>10.2f}% | {ob_pct:>8.1f}% {status}")

print()

# ============================================
# 6. IDENTIFY "HUMORS"
# ============================================
print("="*140)
print("6. ETH's DISTINCT 'HUMORS'")
print("="*140)

def identify_humor(row):
    if pd.isna(row['rsi']) or pd.isna(row['atr_pct']):
        return 'WARMING_UP'

    rsi = row['rsi']
    atr = row['atr_pct']
    dist_ma = row['dist_from_ma20']

    if atr > 0.6 and rsi > 75:
        return 'MANIC_PUMP'
    if atr > 0.6 and rsi < 30:
        return 'PANIC_DUMP'
    if atr < 0.35 and 40 < rsi < 60:
        return 'SLEEPY_CHOP'
    if rsi > 70 and atr < 0.5:
        return 'EXHAUSTED_TOP'
    if dist_ma > 1.0 and 0.4 < atr < 0.7 and rsi > 55:
        return 'HEALTHY_UPTREND'
    if dist_ma < -1.0 and 0.4 < atr < 0.7 and rsi < 45:
        return 'HEALTHY_DOWNTREND'

    return 'NEUTRAL_CHOP'

df['humor'] = df.apply(identify_humor, axis=1)

humor_counts = df['humor'].value_counts()
print("\nETH's Humors (% of time):")
print("-"*140)
for humor in humor_counts.index:
    pct = (humor_counts[humor] / len(df)) * 100
    print(f"  {humor:20}: {pct:5.1f}% of time ({humor_counts[humor]:,} candles)")

print()

# ============================================
# 7. FORWARD RETURNS BY HUMOR
# ============================================
print("="*140)
print("7. HOW TO TRADE EACH HUMOR (Forward Returns)")
print("="*140)

df['forward_1h'] = df['close'].shift(-4).pct_change(fill_method=None) * 100
df['forward_4h'] = df['close'].shift(-16).pct_change(fill_method=None) * 100

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

    tradeable = "✅ YES" if abs(fwd_1h) > 0.15 or abs(fwd_4h) > 0.25 else "❌ NO"

    print(f"{humor:<20} | {fwd_1h:>10.2f}% | {fwd_4h:>10.2f}% | {win_rate_1h:>10.1f}% | {tradeable:<12}")

print()

# ============================================
# COMPARISON WITH PENGU
# ============================================
print("="*140)
print("🔍 ETH vs PENGU COMPARISON")
print("="*140)
print()

print(f"{'Metric':<30} | {'ETH':<15} | {'PENGU':<15} | {'Winner':<10}")
print("-"*140)

eth_chop_pct = (humor_counts.get('NEUTRAL_CHOP', 0) / len(df)) * 100
pengu_chop_pct = 89.6  # from PENGU analysis

print(f"{'% Time in NEUTRAL_CHOP':<30} | {eth_chop_pct:>13.1f}% | {pengu_chop_pct:>13.1f}% | {'ETH' if eth_chop_pct < pengu_chop_pct else 'PENGU':<10}")

eth_high_vol_pct = (df['atr_pct'] > 0.6).sum() / len(df) * 100
pengu_high_vol_pct = 88.5

print(f"{'% Time HIGH volatility':<30} | {eth_high_vol_pct:>13.1f}% | {pengu_high_vol_pct:>13.1f}% | {'ETH' if eth_high_vol_pct < pengu_high_vol_pct else 'PENGU':<10}")

eth_ob_return = df[df['rsi'] > 70]['forward_1h'].mean()
pengu_ob_return = 0.16

print(f"{'Mean reversion (RSI>70)':<30} | {eth_ob_return:>12.2f}% | {pengu_ob_return:>12.2f}% | {'ETH' if abs(eth_ob_return) > abs(pengu_ob_return) else 'PENGU':<10}")

print()
print("="*140)
print("🎯 VERDICT:")
print("="*140)

if eth_chop_pct < 70 and abs(eth_ob_return) > 0.3:
    print("✅ ETH WYGLĄDA LEPIEJ NIŻ PENGU!")
    print(f"   - Mniej czasu w chop ({eth_chop_pct:.1f}% vs {pengu_chop_pct:.1f}%)")
    print(f"   - Silniejszy mean reversion ({eth_ob_return:.2f}% vs {pengu_ob_return:.2f}%)")
    print("\n   NASTĘPNY KROK: Test strategii SHORT reversal na ETH")
else:
    print("❌ ETH ma podobne problemy jak PENGU:")
    print(f"   - Dużo czasu w chop ({eth_chop_pct:.1f}%)")
    print(f"   - Słaby mean reversion ({eth_ob_return:.2f}%)")
    print("\n   MOŻE SZUKAJ INNEGO COINA?")

print("="*140)
