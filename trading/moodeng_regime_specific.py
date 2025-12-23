#!/usr/bin/env python3
"""
MOODENG - REGIME-SPECIFIC EDGES

Sprawdź czy setups działają LEPIEJ w specific monthly regimes.
Może edge jest w "trade tylko w BULL months" albo "avoid BEAR months"
"""
import pandas as pd
import numpy as np

df = pd.read_csv('moodeng_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Indicators
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

df['ma_20'] = df['close'].rolling(window=20).mean()
df['ma_50'] = df['close'].rolling(window=50).mean()

df['forward_4h'] = df['close'].shift(-16).pct_change(fill_method=None) * 100

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("MOODENG - REGIME-SPECIFIC EDGE ANALYSIS")
print("="*140)
print()

# Define regimes per month
regimes = {
    '2025-06': 'BEAR',
    '2025-07': 'BULL',
    '2025-08': 'BEAR',
    '2025-09': 'BULL',
    '2025-10': 'BEAR',
    '2025-11': 'BEAR',
    '2025-12': 'CHOP'
}

df['regime'] = df['month'].astype(str).map(regimes)

# ============================================
# TEST: Czy prosty trend following działa w BULL months?
# ============================================
print("="*140)
print("TEST #1: LONG w BULL months, SHORT w BEAR months")
print("="*140)
print()

bull_months = df[df['regime'] == 'BULL'].copy()
bear_months = df[df['regime'] == 'BEAR'].copy()

# BULL: LONG na strong uptrend
bull_long = bull_months[(bull_months['close'] > bull_months['ma_20'] * 1.02) &
                        (bull_months['ma_20'] > bull_months['ma_50'])].copy()

if len(bull_long) > 30:
    print(f"BULL MONTHS - LONG strong uptrend:")
    print(f"  Count: {len(bull_long)}")
    print(f"  Avg forward 4h: {bull_long['forward_4h'].mean():.2f}%")
    print(f"  Win rate: {(bull_long['forward_4h'] > 0).sum() / len(bull_long) * 100:.1f}%")
    print(f"  Avg win: {bull_long[bull_long['forward_4h'] > 0]['forward_4h'].mean():.2f}%")
    print(f"  Avg loss: {bull_long[bull_long['forward_4h'] < 0]['forward_4h'].mean():.2f}%")

    bull_edge = bull_long['forward_4h'].mean()
    if bull_edge > 0.5:
        print(f"  🔥 STRONG EDGE: {bull_edge:.2f}%")
    elif bull_edge > 0.2:
        print(f"  ✅ DECENT EDGE: {bull_edge:.2f}%")
    else:
        print(f"  ⚠️  WEAK EDGE: {bull_edge:.2f}%")

print()

# BEAR: SHORT na strong downtrend
bear_short = bear_months[(bear_months['close'] < bear_months['ma_20'] * 0.98) &
                         (bear_months['ma_20'] < bear_months['ma_50'])].copy()

if len(bear_short) > 30:
    print(f"BEAR MONTHS - SHORT strong downtrend:")
    print(f"  Count: {len(bear_short)}")
    print(f"  Avg forward 4h: {-bear_short['forward_4h'].mean():.2f}% (for SHORT)")
    print(f"  Win rate: {(bear_short['forward_4h'] < 0).sum() / len(bear_short) * 100:.1f}%")
    print(f"  Avg win: {-bear_short[bear_short['forward_4h'] < 0]['forward_4h'].mean():.2f}%")
    print(f"  Avg loss: {-bear_short[bear_short['forward_4h'] > 0]['forward_4h'].mean():.2f}%")

    bear_edge = -bear_short['forward_4h'].mean()
    if bear_edge > 0.5:
        print(f"  🔥 STRONG EDGE: {bear_edge:.2f}%")
    elif bear_edge > 0.2:
        print(f"  ✅ DECENT EDGE: {bear_edge:.2f}%")
    else:
        print(f"  ⚠️  WEAK EDGE: {bear_edge:.2f}%")

print()

# ============================================
# TEST: Czy pullbacks w BULL months mają edge?
# ============================================
print("="*140)
print("TEST #2: PULLBACK strategy w BULL months")
print("="*140)
print()

bull_pullback = bull_months[(bull_months['close'] > bull_months['ma_20'] * 1.03) &
                            (bull_months['close'] < bull_months['close'].shift(4))].copy()

if len(bull_pullback) > 20:
    print(f"BULL MONTHS - Buy pullbacks in strong uptrend:")
    print(f"  Count: {len(bull_pullback)}")
    print(f"  Avg forward 4h: {bull_pullback['forward_4h'].mean():.2f}%")
    print(f"  Win rate: {(bull_pullback['forward_4h'] > 0).sum() / len(bull_pullback) * 100:.1f}%")
    print(f"  Avg win: {bull_pullback[bull_pullback['forward_4h'] > 0]['forward_4h'].mean():.2f}%")
    print(f"  Avg loss: {bull_pullback[bull_pullback['forward_4h'] < 0]['forward_4h'].mean():.2f}%")

    pullback_edge = bull_pullback['forward_4h'].mean()
    if pullback_edge > 0.5:
        print(f"  🔥 STRONG EDGE: {pullback_edge:.2f}%")
    elif pullback_edge > 0.2:
        print(f"  ✅ DECENT EDGE: {pullback_edge:.2f}%")
    else:
        print(f"  ⚠️  WEAK EDGE: {pullback_edge:.2f}%")

print()

# ============================================
# TEST: Czy избегать BEAR months całkowicie działa?
# ============================================
print("="*140)
print("TEST #3: STRATEGY - Trade TYLKO w BULL months")
print("="*140)
print()

print("Simulate: Trade ONLY w July + September, avoid resztę")
print()

# Count potential trades per month
for month in df['month'].unique():
    df_month = df[df['month'] == month].copy()
    regime = regimes[str(month)]

    # Strong trend condition
    strong_trend = df_month[
        ((df_month['close'] > df_month['ma_20'] * 1.02) & (df_month['ma_20'] > df_month['ma_50'])) |
        ((df_month['close'] < df_month['ma_20'] * 0.98) & (df_month['ma_20'] < df_month['ma_50']))
    ]

    print(f"{str(month):<10} ({regime:<5}): {len(strong_trend):>4} potential setups", end="")

    if regime == 'BULL':
        print(f" ✅ TRADE")
    elif regime == 'BEAR':
        print(f" ❌ SKIP")
    else:
        print(f" ⚠️  MAYBE")

print()

# ============================================
# SUMMARY
# ============================================
print("="*140)
print("🎯 BEST STRATEGY FOR MOODENG:")
print("="*140)
print()

if len(bull_long) > 20 and bull_long['forward_4h'].mean() > 0.3:
    print(f"✅ STRATEGY: Trade ONLY in BULL months")
    print(f"   - LONG strong uptrends (close > MA20 * 1.02)")
    print(f"   - Edge: {bull_long['forward_4h'].mean():.2f}% per trade")
    print(f"   - Win rate: {(bull_long['forward_4h'] > 0).sum() / len(bull_long) * 100:.1f}%")
    print(f"   - Frequency: ~{len(bull_long)/2:.0f} trades per BULL month")
    print()
    print(f"   📅 BULL months to detect:")
    print(f"      - Price making higher highs")
    print(f"      - MA20 > MA50")
    print(f"      - Monthly return > +5%")
    print()
    print(f"   ⚠️  AVOID TRADING:")
    print(f"      - BEAR months (Jun, Aug, Oct, Nov)")
    print(f"      - Wait for regime change")
elif len(bull_pullback) > 15 and bull_pullback['forward_4h'].mean() > 0.4:
    print(f"✅ STRATEGY: Buy pullbacks in BULL months")
    print(f"   - Entry: Pullback in strong uptrend (>3% above MA20)")
    print(f"   - Edge: {bull_pullback['forward_4h'].mean():.2f}% per trade")
    print(f"   - Win rate: {(bull_pullback['forward_4h'] > 0).sum() / len(bull_pullback) * 100:.1f}%")
else:
    print(f"❌ MOODENG NIE MA WYRAŹNEGO EDGE")
    print(f"   Nawet regime-specific strategies mają słaby edge")
    print()
    print(f"   VERDICT: Porzuć MOODENG, znajdź lepszy coin")
    print()
    print(f"   Dlaczego MOODENG nie działa:")
    print(f"   1. Tylko 2/7 months są favorable (29%)")
    print(f"   2. Nawet w BULL months edge jest słaby (<0.5%)")
    print(f"   3. High kurtosis (387) = zbyt dużo random outliers")
    print(f"   4. 58.8% czasu w ranging (no edge)")

print("="*140)
