#!/usr/bin/env python3
"""
BTC - DOGŁĘBNA ANALIZA CHARAKTERYSTYKI

BTC z batch analysis:
- 43.5% chop (NAJMNIEJ ze wszystkich!)
- Avg ATR: 0.27% (lowest volatility)
- Price range: ?

Czy BTC ma lepszy edge niż MOODENG?
"""
import pandas as pd
import numpy as np
from scipy import stats

df = pd.read_csv('btcusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("="*140)
print("BTC - DOGŁĘBNA ANALIZA CHARAKTERYSTYKI")
print("="*140)
print()

print(f"Data: {df['timestamp'].min()} → {df['timestamp'].max()}")
print(f"Candles: {len(df):,}")
print(f"Price range: ${df['low'].min():,.2f} → ${df['high'].max():,.2f}")
print()

# ============================================
# PART 1: PRICE ACTION DNA
# ============================================
print("="*140)
print("PART 1: PRICE ACTION DNA - Jak BTC się porusza?")
print("="*140)
print()

df['return_1bar'] = df['close'].pct_change() * 100
df['return_1h'] = df['close'].pct_change(4) * 100
df['return_4h'] = df['close'].pct_change(16) * 100
df['return_1d'] = df['close'].pct_change(96) * 100

print("Returns Distribution:")
print(f"  1-bar (15m):")
print(f"    Mean: {df['return_1bar'].mean():.4f}%")
print(f"    Median: {df['return_1bar'].median():.4f}%")
print(f"    Std Dev: {df['return_1bar'].std():.4f}%")
print(f"    Skewness: {df['return_1bar'].skew():.4f} {'(right tail)' if df['return_1bar'].skew() > 0 else '(left tail)'}")
print(f"    Kurtosis: {df['return_1bar'].kurtosis():.4f} {'(fat tails)' if df['return_1bar'].kurtosis() > 3 else '(thin tails)'}")
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

# Asymmetry
dumps = df[df['return_1h'] < 0]['return_1h']
pumps = df[df['return_1h'] > 0]['return_1h']

print("Dumps vs Pumps (1h):")
print(f"  Average dump: {dumps.mean():.3f}%")
print(f"  Average pump: {pumps.mean():.3f}%")
print(f"  Biggest dump: {dumps.min():.2f}%")
print(f"  Biggest pump: {pumps.max():.2f}%")
print(f"  Dump/Pump ratio: {abs(dumps.mean() / pumps.mean()):.2f}x")

if abs(dumps.mean()) > pumps.mean() * 1.1:
    print(f"  💡 INSIGHT: Dumps > pumps - bearish bias")
elif pumps.mean() > abs(dumps.mean()) * 1.1:
    print(f"  💡 INSIGHT: Pumps > dumps - bullish bias")
else:
    print(f"  💡 INSIGHT: Balanced")
print()

# ============================================
# PART 2: VOLATILITY BEHAVIOR
# ============================================
print("="*140)
print("PART 2: VOLATILITY - Czy stabilny czy wybuchowy?")
print("="*140)
print()

high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

print("Volatility Profile:")
print(f"  Average ATR: {df['atr_pct'].mean():.3f}%")
print(f"  Median ATR: {df['atr_pct'].median():.3f}%")
print(f"  Range: {df['atr_pct'].min():.3f}% - {df['atr_pct'].max():.3f}%")
print()

low_vol = df[df['atr_pct'] < 0.25]
med_vol = df[(df['atr_pct'] >= 0.25) & (df['atr_pct'] < 0.35)]
high_vol = df[df['atr_pct'] >= 0.35]

print("Volatility regimes:")
print(f"  LOW (<0.25%):  {len(low_vol)/len(df)*100:5.1f}%")
print(f"  MED (0.25-0.35%): {len(med_vol)/len(df)*100:5.1f}%")
print(f"  HIGH (>0.35%):   {len(high_vol)/len(df)*100:5.1f}%")
print()

# Clustering
df['vol_change'] = df['atr_pct'].pct_change()
high_vol_bars = df[df['atr_pct'] > df['atr_pct'].quantile(0.75)].copy()
high_vol_bars.loc[:, 'next_4h_atr'] = df.loc[high_vol_bars.index, 'atr_pct'].shift(-16)

print("Volatility Clustering:")
print(f"  After high vol, avg ATR 4h later: {high_vol_bars['next_4h_atr'].mean():.3f}%")
print(f"  Overall avg: {df['atr_pct'].mean():.3f}%")
if high_vol_bars['next_4h_atr'].mean() > df['atr_pct'].mean() * 1.15:
    print(f"  💡 INSIGHT: Vol clusters - expansion continues")
else:
    print(f"  💡 INSIGHT: Vol mean-reverts")
print()

# ============================================
# PART 3: MEAN REVERSION vs MOMENTUM
# ============================================
print("="*140)
print("PART 3: MEAN REVERSION vs MOMENTUM")
print("="*140)
print()

df['abs_return_1h'] = df['return_1h'].abs()

big_dumps = df[df['return_1h'] < df['return_1h'].quantile(0.1)].copy()
big_pumps = df[df['return_1h'] > df['return_1h'].quantile(0.9)].copy()

big_dumps.loc[:, 'next_1h'] = df.loc[big_dumps.index, 'return_1h'].shift(-4)
big_dumps.loc[:, 'next_4h'] = df.loc[big_dumps.index, 'return_1h'].shift(-16)

big_pumps.loc[:, 'next_1h'] = df.loc[big_pumps.index, 'return_1h'].shift(-4)
big_pumps.loc[:, 'next_4h'] = df.loc[big_pumps.index, 'return_1h'].shift(-16)

print("After BIG DUMP (bottom 10%):")
print(f"  Avg dump: {big_dumps['return_1h'].mean():.2f}%")
print(f"  Next 1h: {big_dumps['next_1h'].mean():.2f}%")
print(f"  Next 4h: {big_dumps['next_4h'].mean():.2f}%")

if big_dumps['next_1h'].mean() > 0.1:
    print(f"  💡 INSIGHT: Mean reversion - LONG opportunity!")
elif big_dumps['next_1h'].mean() < -0.05:
    print(f"  💡 INSIGHT: Momentum - dumps continue")
else:
    print(f"  💡 INSIGHT: Neutral")
print()

print("After BIG PUMP (top 10%):")
print(f"  Avg pump: {big_pumps['return_1h'].mean():.2f}%")
print(f"  Next 1h: {big_pumps['next_1h'].mean():.2f}%")
print(f"  Next 4h: {big_pumps['next_4h'].mean():.2f}%")

if big_pumps['next_1h'].mean() < -0.1:
    print(f"  💡 INSIGHT: Mean reversion - SHORT opportunity!")
elif big_pumps['next_1h'].mean() > 0.05:
    print(f"  💡 INSIGHT: Momentum - pumps continue")
else:
    print(f"  💡 INSIGHT: Neutral")
print()

# ============================================
# PART 4: TREND vs CHOP
# ============================================
print("="*140)
print("PART 4: TREND vs CHOP - BTC's cleanest feature")
print("="*140)
print()

df['ma_20'] = df['close'].rolling(window=20).mean()
df['ma_50'] = df['close'].rolling(window=50).mean()
df['ma_100'] = df['close'].rolling(window=100).mean()

df['dist_ma20'] = ((df['close'] - df['ma_20']) / df['ma_20']) * 100
df['dist_ma50'] = ((df['close'] - df['ma_50']) / df['ma_50']) * 100

trending_up = df[df['dist_ma20'] > 1.0]
trending_down = df[df['dist_ma20'] < -1.0]
ranging = df[df['dist_ma20'].abs() < 0.5]

print("Market states:")
print(f"  TRENDING UP (>1% above MA20):   {len(trending_up)/len(df)*100:5.1f}%")
print(f"  TRENDING DOWN (<-1% below):      {len(trending_down)/len(df)*100:5.1f}%")
print(f"  RANGING (<0.5% from MA20):       {len(ranging)/len(df)*100:5.1f}%")
print()

# Performance
if len(trending_up) > 100:
    trending_up.loc[:, 'next_4h'] = df.loc[trending_up.index, 'return_4h'].shift(-16)
    print(f"During uptrends, next 4h: {trending_up['next_4h'].mean():.2f}%")

if len(trending_down) > 100:
    trending_down.loc[:, 'next_4h'] = df.loc[trending_down.index, 'return_4h'].shift(-16)
    print(f"During downtrends, next 4h: {trending_down['next_4h'].mean():.2f}%")

if len(ranging) > 100:
    ranging.loc[:, 'next_4h'] = df.loc[ranging.index, 'return_4h'].shift(-16)
    print(f"During ranging, next 4h: {ranging['next_4h'].mean():.2f}%")
print()

# ============================================
# PART 5: TIME PATTERNS
# ============================================
print("="*140)
print("PART 5: TIME-OF-DAY PATTERNS")
print("="*140)
print()

df['hour'] = df['timestamp'].dt.hour

hourly_stats = df.groupby('hour').agg({
    'return_1h': ['mean', lambda x: x.abs().mean()],
    'atr_pct': 'mean'
}).round(4)

print("Top 5 volatile hours:")
hourly_vol = df.groupby('hour')['atr_pct'].mean().sort_values(ascending=False).head(5)
for hour, atr in hourly_vol.items():
    avg_ret = df[df['hour'] == hour]['return_1h'].mean()
    print(f"  {hour:02d}:00 - ATR: {atr:.3f}%, Avg return: {avg_ret:+.3f}%")
print()

print("Top 5 calm hours:")
hourly_calm = df.groupby('hour')['atr_pct'].mean().sort_values(ascending=True).head(5)
for hour, atr in hourly_calm.items():
    avg_ret = df[df['hour'] == hour]['return_1h'].mean()
    print(f"  {hour:02d}:00 - ATR: {atr:.3f}%, Avg return: {avg_ret:+.3f}%")
print()

# ============================================
# PART 6: MONTHLY EVOLUTION
# ============================================
print("="*140)
print("PART 6: MONTHLY EVOLUTION")
print("="*140)
print()

df['month'] = df['timestamp'].dt.to_period('M')

monthly_stats = df.groupby('month').agg({
    'close': ['first', 'last'],
    'return_1h': ['mean', 'std'],
    'atr_pct': 'mean'
}).round(4)

print(f"{'Month':<10} | {'Return%':<9} | {'Avg Move':<10} | {'Volatility':<11} | {'Character':<30}")
print("-"*140)

for month in monthly_stats.index:
    start = monthly_stats.loc[month, ('close', 'first')]
    end = monthly_stats.loc[month, ('close', 'last')]
    ret = ((end - start) / start) * 100

    avg_move = monthly_stats.loc[month, ('return_1h', 'std')]
    atr = monthly_stats.loc[month, ('atr_pct', 'mean')]

    if ret > 10:
        char = "🚀 STRONG BULL"
    elif ret > 0:
        char = "📈 Mild bull"
    elif ret > -10:
        char = "📉 Mild bear"
    else:
        char = "💀 STRONG BEAR"

    if atr > 0.3:
        char += " + HIGH VOL"
    elif atr < 0.25:
        char += " + LOW VOL"

    print(f"{str(month):<10} | {ret:>7.1f}% | {avg_move:>8.2f}% | {atr:>9.3f}% | {char:<30}")

print()

# ============================================
# PART 7: BTC SIGNATURE
# ============================================
print("="*140)
print("PART 7: BTC UNIQUE FINGERPRINT")
print("="*140)
print()

print("BTC Signature:")
print(f"  Skewness: {df['return_1h'].skew():.3f}")
print(f"  Kurtosis: {df['return_1h'].kurtosis():.3f} (MOODENG: 387)")
print(f"  Volatility: {df['atr_pct'].mean():.3f}% (MOODENG: 1.02%)")
print(f"  Chop rate: {len(ranging)/len(df)*100:.1f}% (MOODENG: 58.8%)")
print()

# Key edges
edges = {
    'dump_reversion': big_dumps['next_1h'].mean(),
    'pump_reversion': -big_pumps['next_1h'].mean(),
    'uptrend_continuation': trending_up['next_4h'].mean() if len(trending_up) > 100 else 0,
    'downtrend_continuation': trending_down['next_4h'].mean() if len(trending_down) > 100 else 0,
}

print("Potential edges:")
for edge_name, edge_val in sorted(edges.items(), key=lambda x: abs(x[1]), reverse=True):
    print(f"  {edge_name}: {edge_val:.3f}%")

best_edge = max(edges, key=lambda k: abs(edges[k]))
print()
print(f"Strongest edge: {best_edge} ({edges[best_edge]:.3f}%)")
print()

print("="*140)
print("🎯 COMPARISON: BTC vs MOODENG")
print("="*140)
print()

print(f"{'Metric':<30} | {'BTC':<15} | {'MOODENG':<15} | {'Winner':<10}")
print("-"*140)
print(f"{'Kurtosis (fat tails)':<30} | {df['return_1h'].kurtosis():>13.1f} | {387:>13.1f} | {'BTC (cleaner)' if df['return_1h'].kurtosis() < 387 else 'MOODENG':<10}")
print(f"{'Avg ATR%':<30} | {df['atr_pct'].mean():>13.3f} | {1.021:>13.3f} | {'BTC (stable)' if df['atr_pct'].mean() < 1.021 else 'MOODENG':<10}")
print(f"{'% Time ranging':<30} | {len(ranging)/len(df)*100:>13.1f} | {58.8:>13.1f} | {'BTC' if len(ranging)/len(df)*100 < 58.8 else 'MOODENG':<10}")
print(f"{'Mean reversion (dumps)':<30} | {big_dumps['next_1h'].mean():>13.3f} | {-2.49:>13.3f} | {'BTC' if big_dumps['next_1h'].mean() > 0 else 'MOODENG':<10}")

print()
print("="*140)
print("💡 STRATEGY RECOMMENDATION:")
print("="*140)
print()

if abs(edges[best_edge]) > 0.2:
    print(f"✅ BTC ma lepszy edge niż MOODENG!")
    print(f"   Best edge: {best_edge} ({edges[best_edge]:.3f}%)")
    print()
    print(f"   Następny krok: Optimize strategy dla tego edge")
elif abs(edges[best_edge]) > 0.1:
    print(f"⚠️  BTC ma weak edge ale lepszy niż MOODENG")
    print(f"   Best edge: {best_edge} ({edges[best_edge]:.3f}%)")
else:
    print(f"❌ BTC też ma słaby edge mimo cleanest structure")
    print(f"   Best edge: tylko {edges[best_edge]:.3f}%")

print("="*140)
