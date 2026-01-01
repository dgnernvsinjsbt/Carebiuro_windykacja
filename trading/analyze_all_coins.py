#!/usr/bin/env python3
"""
Analyze all 30-day crypto pairs to find FARTCOIN/MOODENG-like candidates
"""

import pandas as pd
import numpy as np
import glob

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

print("=" * 80)
print("COMPREHENSIVE CRYPTO ANALYSIS - Find FARTCOIN/MOODENG Cousins")
print("=" * 80)

# Find all 30-day files
files_30d = glob.glob('/workspaces/Carebiuro_windykacja/trading/*30d_bingx.csv')
print(f"\nFound {len(files_30d)} coins with 30-day data")

# Reference profiles
references = {
    'FARTCOIN': {'atr': 0.3690, 'file': 'fartcoin_60d_bingx.csv'},
    'MOODENG': {'atr': 0.2459, 'file': 'moodeng_usdt_60d_bingx.csv'},
    'ETH': {'atr': 0.1223, 'file': 'eth_usdt_60d_bingx.csv'}
}

results = []

for file_path in files_30d:
    coin_name = file_path.split('/')[-1].replace('_30d_bingx.csv', '').replace('_usdt', '').upper()
    
    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.lower()
        
        # Skip if empty or insufficient data
        if len(df) < 10000:
            continue
        
        df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
        df['atr_pct'] = (df['atr'] / df['close'] * 100)
        
        # Price stats
        price_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100
        price_range = (df['high'].max() - df['low'].min()) / df['close'].iloc[0] * 100
        
        # Volatility stats
        avg_atr_pct = df['atr_pct'].mean()
        std_atr_pct = df['atr_pct'].std()
        max_atr_pct = df['atr_pct'].max()
        
        # Daily moves
        df['daily_return'] = df['close'].pct_change() * 100
        avg_1m_move = df['daily_return'].abs().mean()
        max_1m_move = df['daily_return'].abs().max()
        
        # Similarity to FARTCOIN (our target)
        similarity_fartcoin = abs(avg_atr_pct - references['FARTCOIN']['atr']) / references['FARTCOIN']['atr']
        similarity_moodeng = abs(avg_atr_pct - references['MOODENG']['atr']) / references['MOODENG']['atr']
        
        # Determine similarity category
        if similarity_fartcoin < 0.5:
            category = "FARTCOIN-LIKE"
            score = 10 - (similarity_fartcoin * 10)
        elif similarity_moodeng < 0.5:
            category = "MOODENG-LIKE"
            score = 8 - (similarity_moodeng * 10)
        elif avg_atr_pct > 0.15:
            category = "VOLATILE"
            score = 6
        else:
            category = "LOW-VOL"
            score = 2
        
        results.append({
            'coin': coin_name,
            'avg_atr': avg_atr_pct,
            'std_atr': std_atr_pct,
            'max_atr': max_atr_pct,
            'price_change': price_change,
            'price_range': price_range,
            'avg_1m_move': avg_1m_move,
            'max_1m_move': max_1m_move,
            'sim_fartcoin': similarity_fartcoin,
            'sim_moodeng': similarity_moodeng,
            'category': category,
            'score': score,
            'candles': len(df)
        })
    
    except Exception as e:
        print(f"  ⚠️ Error processing {coin_name}: {e}")
        continue

if not results:
    print("\n❌ No valid results found")
    exit(0)

# Create DataFrame and sort by score
df_results = pd.DataFrame(results)
df_results = df_results.sort_values('score', ascending=False)

print("\n" + "=" * 80)
print("TIER 1: FARTCOIN-LIKE (Most Similar)")
print("=" * 80)

tier1 = df_results[df_results['category'] == 'FARTCOIN-LIKE']
if len(tier1) > 0:
    print(f"\n{'Coin':<12} {'ATR%':<10} {'Sim%':<8} {'30d Ret':<10} {'Max 1m':<10} {'Score'}")
    print("-" * 70)
    for _, row in tier1.iterrows():
        print(f"{row['coin']:<12} {row['avg_atr']:<10.4f} {row['sim_fartcoin']*100:<8.1f} {row['price_change']:+9.1f}% {row['max_1m_move']:<10.2f} {row['score']:<5.1f}")
else:
    print("\n  None found")

print("\n" + "=" * 80)
print("TIER 2: MOODENG-LIKE (Moderate Volatility)")
print("=" * 80)

tier2 = df_results[df_results['category'] == 'MOODENG-LIKE']
if len(tier2) > 0:
    print(f"\n{'Coin':<12} {'ATR%':<10} {'Sim%':<8} {'30d Ret':<10} {'Max 1m':<10} {'Score'}")
    print("-" * 70)
    for _, row in tier2.iterrows():
        print(f"{row['coin']:<12} {row['avg_atr']:<10.4f} {row['sim_moodeng']*100:<8.1f} {row['price_change']:+9.1f}% {row['max_1m_move']:<10.2f} {row['score']:<5.1f}")
else:
    print("\n  None found")

print("\n" + "=" * 80)
print("TIER 3: VOLATILE (Could work)")
print("=" * 80)

tier3 = df_results[df_results['category'] == 'VOLATILE']
if len(tier3) > 0:
    print(f"\n{'Coin':<12} {'ATR%':<10} {'30d Ret':<10} {'Max 1m':<10} {'Score'}")
    print("-" * 60)
    for _, row in tier3.iterrows():
        print(f"{row['coin']:<12} {row['avg_atr']:<10.4f} {row['price_change']:+9.1f}% {row['max_1m_move']:<10.2f} {row['score']:<5.1f}")
else:
    print("\n  None found")

print("\n" + "=" * 80)
print("TIER 4: LOW VOLATILITY (Skip)")
print("=" * 80)

tier4 = df_results[df_results['category'] == 'LOW-VOL']
if len(tier4) > 0:
    print(f"\n  {len(tier4)} coins too low-volatility for this strategy")
    print(f"  Examples: {', '.join(tier4['coin'].head(3).tolist())}")

# Final recommendations
print("\n" + "=" * 80)
print("RECOMMENDATIONS FOR TESTING")
print("=" * 80)

candidates = df_results[df_results['score'] >= 6].sort_values('score', ascending=False)

if len(candidates) > 0:
    print(f"\n✅ {len(candidates)} candidates worth testing:")
    print(f"\n{'Rank':<6} {'Coin':<12} {'Category':<18} {'ATR%':<10} {'30d Ret':<10} {'Score'}")
    print("-" * 75)
    
    for i, (_, row) in enumerate(candidates.iterrows(), 1):
        marker = "🎯" if row['score'] >= 9 else "✅" if row['score'] >= 7 else "⚠️"
        print(f"{marker} {i:<4} {row['coin']:<12} {row['category']:<18} {row['avg_atr']:<10.4f} {row['price_change']:+9.1f}% {row['score']:<5.1f}")
    
    print(f"\n{'='*80}")
    print("NEXT STEPS")
    print(f"{'='*80}")
    
    top3 = candidates.head(3)
    print(f"\n📊 Download 60-day data for top candidates:")
    for _, row in top3.iterrows():
        print(f"  - {row['coin']}")
    
    print(f"\n🔬 Test strategy on each with MOODENG-like parameters:")
    print(f"  - Start ATR: ~{top3.iloc[0]['avg_atr'] / 0.2459 * 1.4:.1f}x (scaled from MOODENG)")
    print(f"  - Start EMA: ~{top3.iloc[0]['avg_atr'] / 0.2459 * 2.0:.1f}%")
    print(f"  - Target: R/DD > 5.0x, 20-60 trades")

else:
    print("\n❌ No strong candidates found")
    print("   All coins either too stable or don't match FARTCOIN/MOODENG profile")

print("\n" + "=" * 80)

# Save results
df_results.to_csv('results/crypto_volatility_analysis.csv', index=False)
print("\n✅ Full analysis saved to: results/crypto_volatility_analysis.csv")
