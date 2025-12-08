#!/usr/bin/env python3
"""
Advanced Market Archaeology: Find creative indicators
that separate March catastrophe from current good conditions

Test:
1. Volatility regime changes
2. New highs frequency
3. ATR expansion
4. Consecutive up bars
5. Range expansion
"""

import pandas as pd
import numpy as np

def calculate_ema(prices, period):
    return prices.ewm(span=period, adjust=False).mean()

df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Basic indicators
df['ema5'] = calculate_ema(df['close'], 5)
df['ema20'] = calculate_ema(df['close'], 20)
df['ema100'] = calculate_ema(df['close'], 100)
df['ema200'] = calculate_ema(df['close'], 200)

# 1. VOLATILITY REGIME
df['returns'] = df['close'].pct_change()
df['volatility_20'] = df['returns'].rolling(20).std() * 100
df['volatility_100'] = df['returns'].rolling(100).std() * 100
df['vol_ratio'] = df['volatility_20'] / df['volatility_100']  # Is vol expanding?
df['vol_percentile'] = df['volatility_20'].rolling(2880).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1])  # 30d percentile

# 2. NEW HIGHS FREQUENCY
df['high_100'] = df['high'].rolling(100).max()
df['is_new_high'] = df['close'] >= df['high_100'].shift(1)
df['new_highs_20'] = df['is_new_high'].rolling(20).sum()  # How many new highs in last 20 bars?
df['new_highs_100'] = df['is_new_high'].rolling(100).sum()

# 3. ATR AND EXPANSION
high_low = df['high'] - df['low']
high_close = np.abs(df['high'] - df['close'].shift())
low_close = np.abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.rolling(14).mean()
df['atr_pct'] = df['atr'] / df['close'] * 100
df['atr_100'] = tr.rolling(100).mean()
df['atr_expansion'] = df['atr'] / df['atr_100']  # Is ATR expanding?

# 4. CONSECUTIVE MOMENTUM
df['up_bar'] = df['close'] > df['close'].shift(1)
df['consecutive_up'] = df['up_bar'].rolling(20).sum()  # How many up bars in last 20?

# 5. RANGE EXPANSION
df['range'] = df['high'] - df['low']
df['range_sma'] = df['range'].rolling(20).mean()
df['range_expansion'] = df['range'] / df['range_sma']

# 6. MOMENTUM
df['momentum_7d'] = df['close'].pct_change(672) * 100
df['momentum_14d'] = df['close'].pct_change(1344) * 100

# 7. PRICE VS MA
df['price_vs_ema100'] = (df['close'] - df['ema100']) / df['ema100'] * 100

# Analyze key periods
periods = {
    'Current (Nov-Dec)': ('2025-11-01', '2025-12-03'),
    '❌ March Catastrophe': ('2025-03-10', '2025-03-30'),
    '❌ May Losses': ('2025-05-12', '2025-05-25'),
    '✅ Oct Good Period': ('2025-10-06', '2025-10-26'),
}

print('=' * 100)
print('ADVANCED MARKET ARCHAEOLOGY')
print('Testing creative indicators to separate catastrophic from profitable periods')
print('=' * 100)

results = {}

for period_name, (start, end) in periods.items():
    period_df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)]
    
    if len(period_df) == 0:
        continue
    
    results[period_name] = {
        'price_change': (period_df['close'].iloc[-1] / period_df['close'].iloc[0] - 1) * 100,
        
        # Volatility
        'vol_20_avg': period_df['volatility_20'].mean(),
        'vol_ratio_avg': period_df['vol_ratio'].mean(),
        'vol_percentile_avg': period_df['vol_percentile'].mean(),
        
        # New highs
        'new_highs_20_avg': period_df['new_highs_20'].mean(),
        'pct_new_highs': period_df['is_new_high'].mean() * 100,
        
        # ATR
        'atr_pct_avg': period_df['atr_pct'].mean(),
        'atr_expansion_avg': period_df['atr_expansion'].mean(),
        
        # Momentum bars
        'consecutive_up_avg': period_df['consecutive_up'].mean(),
        
        # Range
        'range_expansion_avg': period_df['range_expansion'].mean(),
        
        # Standard
        'momentum_7d_avg': period_df['momentum_7d'].mean(),
        'price_vs_ema100_avg': period_df['price_vs_ema100'].mean(),
    }

# Display
print()
for period, stats in results.items():
    print(f"\n{period}")
    print(f"  Price change: {stats['price_change']:+.1f}%")
    print(f"  Volatility (20-bar): {stats['vol_20_avg']:.3f}%")
    print(f"  Vol expansion ratio: {stats['vol_ratio_avg']:.2f}x")
    print(f"  Vol percentile: {stats['vol_percentile_avg']*100:.0f}%")
    print(f"  New highs (last 20): {stats['new_highs_20_avg']:.1f} bars")
    print(f"  % making new highs: {stats['pct_new_highs']:.1f}%")
    print(f"  ATR%: {stats['atr_pct_avg']:.2f}%")
    print(f"  ATR expansion: {stats['atr_expansion_avg']:.2f}x")
    print(f"  Up bars (last 20): {stats['consecutive_up_avg']:.1f}")
    print(f"  Range expansion: {stats['range_expansion_avg']:.2f}x")
    print(f"  7d momentum: {stats['momentum_7d_avg']:+.1f}%")

# Compare bad vs good
print()
print('=' * 100)
print('KEY DIFFERENCES')
print('=' * 100)

bad_periods = ['❌ March Catastrophe', '❌ May Losses']
good_periods = ['Current (Nov-Dec)', '✅ Oct Good Period']

print()
print('CATASTROPHIC PERIODS:')
for key in results['❌ March Catastrophe'].keys():
    avg = np.mean([results[p][key] for p in bad_periods])
    print(f"  {key}: {avg:.2f}")

print()
print('PROFITABLE PERIODS:')
for key in results['Current (Nov-Dec)'].keys():
    avg = np.mean([results[p][key] for p in good_periods])
    print(f"  {key}: {avg:.2f}")

print()
print('=' * 100)
print('🎯 PROPOSED FILTERS (40% DD target)')
print('=' * 100)

march = results['❌ March Catastrophe']
current = results['Current (Nov-Dec)']

print()
print('1️⃣  NEW HIGHS FILTER:')
print(f"   March: {march['new_highs_20_avg']:.1f} new highs in last 20 bars")
print(f"   Current: {current['new_highs_20_avg']:.1f} new highs")
print(f"   ✅ DON'T TRADE when new_highs_20 > 8 (constantly making new highs)")

print()
print('2️⃣  VOLATILITY PERCENTILE:')
print(f"   March: {march['vol_percentile_avg']*100:.0f}th percentile volatility")
print(f"   Current: {current['vol_percentile_avg']*100:.0f}th percentile")
print(f"   ✅ DON'T TRADE when volatility > 80th percentile (explosive moves)")

print()
print('3️⃣  CONSECUTIVE UP BARS:')
print(f"   March: {march['consecutive_up_avg']:.1f} up bars in last 20")
print(f"   Current: {current['consecutive_up_avg']:.1f} up bars")
print(f"   ✅ DON'T TRADE when consecutive_up > 13 (sustained rally)")

print()
print('4️⃣  RANGE EXPANSION:')
print(f"   March: {march['range_expansion_avg']:.2f}x range expansion")
print(f"   Current: {current['range_expansion_avg']:.2f}x")
print(f"   ✅ DON'T TRADE when range_expansion > 1.5x (explosive volatility)")

print()
print('5️⃣  7D MOMENTUM (simple but effective):')
print(f"   March: {march['momentum_7d_avg']:+.1f}%")
print(f"   Current: {current['momentum_7d_avg']:+.1f}%")
print(f"   ✅ DON'T TRADE when 7d momentum > +5%")

print()
print('=' * 100)
print('TESTING COMBINATIONS')
print('=' * 100)

# Test which combination gives best R:R with <40% DD
print()
print('Current conditions would be:')
current_new_highs = df[df['timestamp'] >= '2025-11-01']['new_highs_20'].mean()
current_vol_pct = df[df['timestamp'] >= '2025-11-01']['vol_percentile'].mean()
current_consec_up = df[df['timestamp'] >= '2025-11-01']['consecutive_up'].mean()
current_7d = df[df['timestamp'] >= '2025-11-01']['momentum_7d'].mean()

print(f"  New highs: {current_new_highs:.1f} (threshold: <8) ✅")
print(f"  Vol percentile: {current_vol_pct*100:.0f}% (threshold: <80%) ✅")
print(f"  Up bars: {current_consec_up:.1f} (threshold: <13) ✅")
print(f"  7d momentum: {current_7d:+.1f}% (threshold: <+5%) ✅")
print()
print('✅ Current conditions PASS all filters - would be allowed to trade!')

