#!/usr/bin/env python3
"""
Scan untested tokens for volume zones strategy potential
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Tokens already tested with volume zones
ALREADY_TESTED = ['DOGE', 'ETH', 'PEPE', 'PENGU', 'TRUMP']

# Find all LBank data files
data_dir = Path('/workspaces/Carebiuro_windykacja/trading')
files = list(data_dir.glob('*_usdt_1m_lbank.csv'))

print("=" * 80)
print("VOLUME ZONES CANDIDATE ANALYSIS")
print("=" * 80)
print()

results = []

for f in files:
    token = f.stem.replace('_usdt_1m_lbank', '').upper()

    if token in ALREADY_TESTED:
        continue

    try:
        df = pd.read_csv(f)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Basic stats
        rows = len(df)
        days = (df['timestamp'].max() - df['timestamp'].min()).days

        # Price stats
        avg_price = df['close'].mean()
        price_range = (df['high'].max() - df['low'].min()) / avg_price * 100

        # Volume stats (in USD)
        df['volume_usd'] = df['volume'] * df['close']
        avg_volume_usd = df['volume_usd'].mean()

        # Volatility (ATR-like)
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        avg_atr_pct = (df['tr'].mean() / avg_price) * 100

        # Volume spike frequency (how often volume > 1.5x average)
        avg_vol = df['volume'].rolling(20).mean()
        spikes = (df['volume'] > avg_vol * 1.5).sum()
        spike_pct = spikes / len(df) * 100

        # Consecutive volume bars (key for volume zones)
        df['high_vol'] = df['volume'] > avg_vol * 1.5
        consecutive_counts = []
        count = 0
        for hv in df['high_vol']:
            if hv:
                count += 1
            else:
                if count >= 5:
                    consecutive_counts.append(count)
                count = 0
        zones_per_day = len(consecutive_counts) / max(days, 1)

        # Mean reversion tendency
        df['returns'] = df['close'].pct_change()
        autocorr = df['returns'].autocorr(lag=1)

        results.append({
            'token': token,
            'days': days,
            'avg_price': avg_price,
            'avg_vol_usd': avg_volume_usd,
            'volatility_pct': avg_atr_pct,
            'spike_pct': spike_pct,
            'zones_per_day': zones_per_day,
            'autocorr': autocorr,
            'score': 0  # Will calculate
        })

    except Exception as e:
        print(f"Error processing {token}: {e}")

# Convert to DataFrame and score
df_results = pd.DataFrame(results)

# Score based on:
# 1. Higher USD volume = better liquidity (weight: 30%)
# 2. Higher volatility = better profit potential (weight: 20%)
# 3. More volume zones per day = more opportunities (weight: 25%)
# 4. Negative autocorrelation = mean reversion tendency (weight: 25%)

df_results['vol_score'] = df_results['avg_vol_usd'].rank(pct=True) * 30
df_results['volatility_score'] = df_results['volatility_pct'].rank(pct=True) * 20
df_results['zones_score'] = df_results['zones_per_day'].rank(pct=True) * 25
df_results['mr_score'] = (-df_results['autocorr']).rank(pct=True) * 25  # Negative = mean reverting

df_results['total_score'] = (
    df_results['vol_score'] +
    df_results['volatility_score'] +
    df_results['zones_score'] +
    df_results['mr_score']
)

df_results = df_results.sort_values('total_score', ascending=False)

print("UNTESTED TOKENS - RANKED BY VOLUME ZONES POTENTIAL")
print("-" * 80)
print()

for _, row in df_results.iterrows():
    print(f"🪙 {row['token']}")
    print(f"   Avg Volume: ${row['avg_vol_usd']:,.0f}/min")
    print(f"   Volatility: {row['volatility_pct']:.3f}%/candle")
    print(f"   Volume Zones: {row['zones_per_day']:.1f}/day")
    print(f"   Autocorrelation: {row['autocorr']:.3f} ({'mean-reverting' if row['autocorr'] < 0 else 'trending'})")
    print(f"   📊 SCORE: {row['total_score']:.1f}/100")
    print()

print("=" * 80)
print("TOP 3 RECOMMENDATIONS FOR VOLUME ZONES STRATEGY:")
print("=" * 80)
top3 = df_results.head(3)
for i, (_, row) in enumerate(top3.iterrows(), 1):
    liquidity = "🟢 HIGH" if row['avg_vol_usd'] > 10000 else "🟡 MEDIUM" if row['avg_vol_usd'] > 1000 else "🔴 LOW"
    print(f"\n{i}. {row['token']}")
    print(f"   Liquidity: {liquidity} (${row['avg_vol_usd']:,.0f}/min)")
    print(f"   Zones/day: {row['zones_per_day']:.1f}")
    print(f"   Why: ", end="")
    reasons = []
    if row['autocorr'] < -0.02:
        reasons.append("strong mean-reversion")
    if row['zones_per_day'] > 2:
        reasons.append("frequent volume zones")
    if row['volatility_pct'] > 0.3:
        reasons.append("good volatility")
    if row['avg_vol_usd'] > 5000:
        reasons.append("decent liquidity")
    print(", ".join(reasons) if reasons else "balanced profile")

print("\n" + "=" * 80)
print("⚠️  LOW LIQUIDITY WARNING - These may have slippage issues:")
print("=" * 80)
low_liq = df_results[df_results['avg_vol_usd'] < 1000]
for _, row in low_liq.iterrows():
    print(f"   {row['token']}: ${row['avg_vol_usd']:,.0f}/min avg volume")
