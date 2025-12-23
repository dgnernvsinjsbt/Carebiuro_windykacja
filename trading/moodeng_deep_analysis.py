#!/usr/bin/env python3
"""
MOODENG - DOGŁĘBNA ANALIZA CHARAKTERYSTYKI

Cel: Zrozumieć DOKŁADNIE jak MOODENG się zachowuje, żeby stworzyć
strategię szytą na miarę dla tego coina.

Nie używamy żadnych preconceived notions o mean reversion czy RSI.
Patrzymy NA DANE i szukamy wzorców.
"""
import pandas as pd
import numpy as np
from scipy import stats

df = pd.read_csv('moodeng_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("="*140)
print("MOODENG - DOGŁĘBNA ANALIZA CHARAKTERYSTYKI")
print("="*140)
print()

print(f"Data: {df['timestamp'].min()} → {df['timestamp'].max()}")
print(f"Candles: {len(df):,}")
print(f"Price range: ${df['low'].min():.6f} → ${df['high'].max():.6f}")
print()

# ============================================
# PART 1: PRICE ACTION DNA
# ============================================
print("="*140)
print("PART 1: PRICE ACTION DNA - Jak MOODENG się porusza?")
print("="*140)
print()

# Returns distribution
df['return_1bar'] = df['close'].pct_change() * 100
df['return_1h'] = df['close'].pct_change(4) * 100
df['return_4h'] = df['close'].pct_change(16) * 100
df['return_1d'] = df['close'].pct_change(96) * 100

print("Returns Distribution:")
print(f"  1-bar (15m):")
print(f"    Mean: {df['return_1bar'].mean():.4f}%")
print(f"    Median: {df['return_1bar'].median():.4f}%")
print(f"    Std Dev: {df['return_1bar'].std():.4f}%")
print(f"    Skewness: {df['return_1bar'].skew():.4f} {'(right tail heavy)' if df['return_1bar'].skew() > 0 else '(left tail heavy)'}")
print(f"    Kurtosis: {df['return_1bar'].kurtosis():.4f} {'(fat tails)' if df['return_1bar'].kurtosis() > 3 else '(normal tails)'}")
print()

print(f"  1-hour:")
print(f"    Mean: {df['return_1h'].mean():.4f}%")
print(f"    Std Dev: {df['return_1h'].std():.4f}%")
print(f"    Skewness: {df['return_1h'].skew():.4f}")
print()

# Move sizes
print("Typical Move Sizes:")
for pct in [50, 75, 90, 95, 99]:
    val = df['return_1h'].abs().quantile(pct/100)
    print(f"  {pct}th percentile: {val:.2f}%")
print()

# Asymmetry: dumps vs pumps
dumps = df[df['return_1h'] < 0]['return_1h']
pumps = df[df['return_1h'] > 0]['return_1h']

print("Dumps vs Pumps (1h):")
print(f"  Average dump: {dumps.mean():.3f}%")
print(f"  Average pump: {pumps.mean():.3f}%")
print(f"  Biggest dump: {dumps.min():.2f}%")
print(f"  Biggest pump: {pumps.max():.2f}%")
print(f"  Dump/Pump ratio: {abs(dumps.mean() / pumps.mean()):.2f}x")

if abs(dumps.mean()) > pumps.mean() * 1.1:
    print(f"  💡 INSIGHT: Dumps są większe niż pumps - asymmetry!")
elif pumps.mean() > abs(dumps.mean()) * 1.1:
    print(f"  💡 INSIGHT: Pumps są większe niż dumps - bullish bias!")
else:
    print(f"  💡 INSIGHT: Dumps i pumps są balanced")
print()

# ============================================
# PART 2: VOLATILITY BEHAVIOR
# ============================================
print("="*140)
print("PART 2: VOLATILITY BEHAVIOR - Czy wybuchowy czy stabilny?")
print("="*140)
print()

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

print("Volatility Profile:")
print(f"  Average ATR: {df['atr_pct'].mean():.3f}%")
print(f"  Median ATR: {df['atr_pct'].median():.3f}%")
print(f"  Min ATR: {df['atr_pct'].min():.3f}%")
print(f"  Max ATR: {df['atr_pct'].max():.3f}%")
print()

# Volatility regimes
low_vol = df[df['atr_pct'] < 0.5]
med_vol = df[(df['atr_pct'] >= 0.5) & (df['atr_pct'] < 1.0)]
high_vol = df[df['atr_pct'] >= 1.0]

print("Time in different volatility regimes:")
print(f"  LOW vol (<0.5%):  {len(low_vol)/len(df)*100:5.1f}% of time")
print(f"  MED vol (0.5-1%): {len(med_vol)/len(df)*100:5.1f}% of time")
print(f"  HIGH vol (>1%):   {len(high_vol)/len(df)*100:5.1f}% of time")
print()

# Volatility clustering
df['vol_change'] = df['atr_pct'].pct_change()
high_vol_bars = df[df['atr_pct'] > df['atr_pct'].quantile(0.75)]
high_vol_bars['next_4h_atr'] = df['atr_pct'].shift(-16)

print("Volatility Clustering:")
print(f"  After high vol bar, avg ATR 4h later: {high_vol_bars['next_4h_atr'].mean():.3f}%")
print(f"  Overall avg ATR: {df['atr_pct'].mean():.3f}%")
if high_vol_bars['next_4h_atr'].mean() > df['atr_pct'].mean() * 1.2:
    print(f"  💡 INSIGHT: High volatility CLUSTERS - używaj vol expansion as signal!")
else:
    print(f"  💡 INSIGHT: Volatility mean-reverts - fade spikes")
print()

# ============================================
# PART 3: MEAN REVERSION vs MOMENTUM
# ============================================
print("="*140)
print("PART 3: MEAN REVERSION vs MOMENTUM - Continuation czy reversal?")
print("="*140)
print()

# After big moves, what happens?
df['abs_return_1h'] = df['return_1h'].abs()

big_dumps = df[df['return_1h'] < df['return_1h'].quantile(0.1)].copy()
big_pumps = df[df['return_1h'] > df['return_1h'].quantile(0.9)].copy()

big_dumps['next_1h'] = df.loc[big_dumps.index, 'return_1h'].shift(-4)
big_dumps['next_4h'] = df.loc[big_dumps.index, 'return_1h'].shift(-16)

big_pumps['next_1h'] = df.loc[big_pumps.index, 'return_1h'].shift(-4)
big_pumps['next_4h'] = df.loc[big_pumps.index, 'return_1h'].shift(-16)

print("After BIG DUMP (bottom 10%):")
print(f"  Avg dump size: {big_dumps['return_1h'].mean():.2f}%")
print(f"  Next 1h: {big_dumps['next_1h'].mean():.2f}%")
print(f"  Next 4h: {big_dumps['next_4h'].mean():.2f}%")

if big_dumps['next_1h'].mean() > 0.1:
    print(f"  💡 INSIGHT: STRONG mean reversion po dumpach - LONG opportunity!")
elif big_dumps['next_1h'].mean() < -0.1:
    print(f"  💡 INSIGHT: Dumps KONTYNUUJĄ - momentum strategy!")
else:
    print(f"  💡 INSIGHT: Neutral - brak edge po dumpach")
print()

print("After BIG PUMP (top 10%):")
print(f"  Avg pump size: {big_pumps['return_1h'].mean():.2f}%")
print(f"  Next 1h: {big_pumps['next_1h'].mean():.2f}%")
print(f"  Next 4h: {big_pumps['next_4h'].mean():.2f}%")

if big_pumps['next_1h'].mean() < -0.1:
    print(f"  💡 INSIGHT: STRONG mean reversion po pumpach - SHORT opportunity!")
elif big_pumps['next_1h'].mean() > 0.1:
    print(f"  💡 INSIGHT: Pumps KONTYNUUJĄ - momentum long!")
else:
    print(f"  💡 INSIGHT: Neutral - brak edge po pumpach")
print()

# ============================================
# PART 4: TREND vs CHOP CHARACTERISTICS
# ============================================
print("="*140)
print("PART 4: TREND vs CHOP - Kiedy trenduje, kiedy chopi?")
print("="*140)
print()

# Moving averages
df['ma_20'] = df['close'].rolling(window=20).mean()
df['ma_50'] = df['close'].rolling(window=50).mean()
df['ma_100'] = df['close'].rolling(window=100).mean()

df['dist_ma20'] = ((df['close'] - df['ma_20']) / df['ma_20']) * 100
df['dist_ma50'] = ((df['close'] - df['ma_50']) / df['ma_50']) * 100

# Trending periods
trending_up = df[df['dist_ma20'] > 1.5]
trending_down = df[df['dist_ma20'] < -1.5]
ranging = df[df['dist_ma20'].abs() < 1.0]

print("Time in different market states:")
print(f"  TRENDING UP (>1.5% above MA20):   {len(trending_up)/len(df)*100:5.1f}%")
print(f"  TRENDING DOWN (<-1.5% below MA20): {len(trending_down)/len(df)*100:5.1f}%")
print(f"  RANGING (within 1% of MA20):      {len(ranging)/len(df)*100:5.1f}%")
print()

# Performance in different states
if len(trending_up) > 100:
    trending_up['next_4h'] = df.loc[trending_up.index, 'return_4h'].shift(-16)
    print(f"During uptrends, next 4h avg: {trending_up['next_4h'].mean():.2f}%")

if len(trending_down) > 100:
    trending_down['next_4h'] = df.loc[trending_down.index, 'return_4h'].shift(-16)
    print(f"During downtrends, next 4h avg: {trending_down['next_4h'].mean():.2f}%")

if len(ranging) > 100:
    ranging['next_4h'] = df.loc[ranging.index, 'return_4h'].shift(-16)
    print(f"During ranging, next 4h avg: {ranging['next_4h'].mean():.2f}%")
print()

# ============================================
# PART 5: TIME-BASED PATTERNS
# ============================================
print("="*140)
print("PART 5: TIME-BASED PATTERNS - Kiedy jest najbardziej aktywny?")
print("="*140)
print()

df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek

hourly_stats = df.groupby('hour').agg({
    'return_1h': ['mean', 'std'],
    'atr_pct': 'mean',
    'volume': 'mean'
}).round(4)

print("Top 5 najbardziej volatile hours (UTC):")
hourly_vol = df.groupby('hour')['atr_pct'].mean().sort_values(ascending=False).head(5)
for hour, atr in hourly_vol.items():
    avg_return = df[df['hour'] == hour]['return_1h'].mean()
    print(f"  {hour:02d}:00 - ATR: {atr:.3f}%, Avg return: {avg_return:+.3f}%")
print()

print("Top 5 najspokojniejsze hours (UTC):")
hourly_calm = df.groupby('hour')['atr_pct'].mean().sort_values(ascending=True).head(5)
for hour, atr in hourly_calm.items():
    avg_return = df[df['hour'] == hour]['return_1h'].mean()
    print(f"  {hour:02d}:00 - ATR: {atr:.3f}%, Avg return: {avg_return:+.3f}%")
print()

# ============================================
# PART 6: MONTHLY EVOLUTION
# ============================================
print("="*140)
print("PART 6: MONTHLY EVOLUTION - Jak się zmieniał przez czas?")
print("="*140)
print()

df['month'] = df['timestamp'].dt.to_period('M')

monthly_stats = df.groupby('month').agg({
    'close': ['first', 'last'],
    'return_1h': ['mean', 'std'],
    'atr_pct': 'mean',
    'volume': 'mean'
}).round(4)

print(f"{'Month':<10} | {'Return%':<9} | {'Avg Move':<10} | {'Volatility':<11} | {'Character':<30}")
print("-"*140)

for month in monthly_stats.index:
    start = monthly_stats.loc[month, ('close', 'first')]
    end = monthly_stats.loc[month, ('close', 'last')]
    ret = ((end - start) / start) * 100

    avg_move = monthly_stats.loc[month, ('return_1h', 'std')]
    atr = monthly_stats.loc[month, ('atr_pct', 'mean')]

    # Characterize month
    if ret > 10:
        char = "🚀 STRONG BULL"
    elif ret > 0:
        char = "📈 Mild bull"
    elif ret > -10:
        char = "📉 Mild bear"
    else:
        char = "💀 STRONG BEAR"

    if atr > 1.2:
        char += " + HIGH VOL"
    elif atr < 0.8:
        char += " + LOW VOL"

    print(f"{str(month):<10} | {ret:>7.1f}% | {avg_move:>8.2f}% | {atr:>9.3f}% | {char:<30}")

print()

# ============================================
# PART 7: SUPPORT/RESISTANCE BEHAVIOR
# ============================================
print("="*140)
print("PART 7: BREAKOUT BEHAVIOR - Czy breakouty są real czy fake?")
print("="*140)
print()

# Find local highs (resistance)
lookback = 20
df['local_high'] = df['high'].rolling(window=lookback, center=True).max()
df['is_at_resistance'] = (df['high'] >= df['local_high'] * 0.999) & (df['high'] == df['local_high'])

# When price breaks above resistance
resistances = df[df['is_at_resistance'] == True].copy()
resistances['next_4h'] = df.loc[resistances.index, 'return_4h'].shift(-16)
resistances['breakout'] = resistances['next_4h'] > 1.0  # Continuation
resistances['fakeout'] = resistances['next_4h'] < -1.0  # Reversal

if len(resistances) > 20:
    print(f"Resistance breakout analysis ({len(resistances)} instances):")
    print(f"  Real breakouts (>1% continuation): {resistances['breakout'].sum()} ({resistances['breakout'].sum()/len(resistances)*100:.1f}%)")
    print(f"  Fakeouts (<-1% reversal): {resistances['fakeout'].sum()} ({resistances['fakeout'].sum()/len(resistances)*100:.1f}%)")
    print(f"  Avg next 4h: {resistances['next_4h'].mean():.2f}%")

    if resistances['fakeout'].sum() > resistances['breakout'].sum():
        print(f"  💡 INSIGHT: FADE breakouts - większość to fakeouty!")
    elif resistances['breakout'].sum() > resistances['fakeout'].sum() * 1.5:
        print(f"  💡 INSIGHT: FOLLOW breakouts - momentum strategy!")
    else:
        print(f"  💡 INSIGHT: Mixed - neutral na breakoutach")

print()

# ============================================
# PART 8: UNIQUE MOODENG FINGERPRINT
# ============================================
print("="*140)
print("PART 8: UNIQUE FINGERPRINT - Co wyróżnia MOODENG?")
print("="*140)
print()

# Compare key metrics
print("MOODENG Signature:")
print(f"  Skewness: {df['return_1h'].skew():.3f} (negative = dumps większe)")
print(f"  Kurtosis: {df['return_1h'].kurtosis():.3f} (>3 = fat tails, ekstremalne moves)")
print(f"  Volatility regime: {len(high_vol)/len(df)*100:.1f}% HIGH vol")
print(f"  Market state: {len(ranging)/len(df)*100:.1f}% ranging")
print()

# Identify key edge
edges = {
    'dump_reversion': big_dumps['next_1h'].mean(),
    'pump_reversion': -big_pumps['next_1h'].mean(),
    'vol_clustering': high_vol_bars['next_4h_atr'].mean() - df['atr_pct'].mean(),
}

best_edge = max(edges, key=lambda k: abs(edges[k]))
print("Strongest edge:")
print(f"  {best_edge}: {edges[best_edge]:.3f}%")
print()

print("="*140)
print("🎯 SUMMARY & STRATEGY RECOMMENDATIONS")
print("="*140)
print()

# Build strategy based on findings
print("Based on deep analysis:")
print()

if abs(big_dumps['next_1h'].mean()) > 0.15:
    print("✅ STRATEGY #1: LONG after big dumps")
    print(f"   Edge: {big_dumps['next_1h'].mean():.2f}% 1h forward return")
    print(f"   Entry: After dump >-{abs(big_dumps['return_1h'].mean()):.1f}%")
    print(f"   TP: {big_dumps['next_1h'].mean() * 0.7:.2f}%")
    print()

if abs(big_pumps['next_1h'].mean()) > 0.15:
    print("✅ STRATEGY #2: SHORT after big pumps")
    print(f"   Edge: {-big_pumps['next_1h'].mean():.2f}% 1h forward return")
    print(f"   Entry: After pump >{big_pumps['return_1h'].mean():.1f}%")
    print(f"   TP: {abs(big_pumps['next_1h'].mean()) * 0.7:.2f}%")
    print()

if high_vol_bars['next_4h_atr'].mean() > df['atr_pct'].mean() * 1.2:
    print("✅ STRATEGY #3: Ride volatility expansion")
    print(f"   Edge: Vol clusters - after spike, more vol coming")
    print(f"   Entry: When ATR spikes >{df['atr_pct'].quantile(0.75):.2f}%")
    print(f"   Trade direction: Based on trend")
    print()

if resistances['fakeout'].sum() > resistances['breakout'].sum():
    print("✅ STRATEGY #4: Fade resistance breakouts")
    print(f"   Edge: {resistances['fakeout'].sum()/len(resistances)*100:.0f}% fakeout rate")
    print(f"   Entry: SHORT when breaks {lookback}-bar high")
    print(f"   TP: {abs(resistances[resistances['fakeout']]['next_4h'].mean()):.1f}%")
    print()

if len([e for e in edges.values() if abs(e) > 0.15]) == 0:
    print("❌ WARNING: No strong edge found")
    print("   MOODENG może być zbyt random/choppy do tradowania")
    print("   Rozważ inny coin")

print("="*140)
