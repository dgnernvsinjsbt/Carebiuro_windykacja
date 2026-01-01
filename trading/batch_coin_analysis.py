#!/usr/bin/env python3
"""
BATCH COIN ANALYSIS - Wszystkie coiny 15m

Ranking po:
1. Mean reversion edge (RSI > 70)
2. % czasu w chop
3. Forward returns
"""
import pandas as pd
import numpy as np
import glob
import os

print("="*140)
print("BATCH COIN ANALYSIS - WSZYSTKIE COINY 15m")
print("="*140)
print()

# Find all coin files
coin_files = glob.glob('*_6months_bingx_15m.csv')

results = []

for coin_file in sorted(coin_files):
    coin_name = coin_file.replace('_6months_bingx_15m.csv', '').upper()

    print(f"Analyzing {coin_name}...")

    try:
        df = pd.read_csv(coin_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Basic stats
        price_range_pct = ((df['high'].max() - df['low'].min()) / df['low'].min()) * 100

        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        df['atr_pct'] = (df['atr'] / df['close']) * 100

        # RSI (Wilder's method)
        period = 14
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MA
        df['ma_20'] = df['close'].rolling(window=20).mean()
        df['dist_from_ma20'] = ((df['close'] - df['ma_20']) / df['ma_20']) * 100

        # Market states
        def classify_market_state(row):
            if pd.isna(row['ma_20']):
                return 'UNKNOWN'
            dist = row['dist_from_ma20']
            if abs(dist) < 0.5:
                return 'TIGHT_RANGE'
            elif abs(dist) < 1.5:
                return 'MILD_TREND'
            else:
                return 'STRONG_TREND'

        df['market_state'] = df.apply(classify_market_state, axis=1)

        # Humors
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

            return 'NEUTRAL_CHOP'

        df['humor'] = df.apply(identify_humor, axis=1)

        # Forward returns
        df['forward_1h'] = df['close'].shift(-4).pct_change(fill_method=None) * 100
        df['forward_4h'] = df['close'].shift(-16).pct_change(fill_method=None) * 100

        # Key metrics
        pct_chop = (df['humor'] == 'NEUTRAL_CHOP').sum() / len(df) * 100
        pct_high_vol = (df['atr_pct'] > 0.6).sum() / len(df) * 100

        # Mean reversion RSI > 70
        rsi_ob = df[df['rsi'] > 70].copy()
        if len(rsi_ob) > 10:
            mr_1h = rsi_ob['forward_1h'].mean()
            mr_4h = rsi_ob['forward_4h'].mean()
            rsi_ob_pct = len(rsi_ob) / len(df) * 100
        else:
            mr_1h = 0.0
            mr_4h = 0.0
            rsi_ob_pct = 0.0

        # Mean reversion RSI < 30
        rsi_os = df[df['rsi'] < 30].copy()
        if len(rsi_os) > 10:
            mr_os_1h = rsi_os['forward_1h'].mean()
            mr_os_4h = rsi_os['forward_4h'].mean()
        else:
            mr_os_1h = 0.0
            mr_os_4h = 0.0

        # MANIC_PUMP edge
        manic = df[df['humor'] == 'MANIC_PUMP'].copy()
        if len(manic) > 5:
            manic_edge = manic['forward_1h'].mean()
            manic_pct = len(manic) / len(df) * 100
        else:
            manic_edge = 0.0
            manic_pct = 0.0

        # EXHAUSTED_TOP edge
        exhausted = df[df['humor'] == 'EXHAUSTED_TOP'].copy()
        if len(exhausted) > 5:
            exhausted_edge = exhausted['forward_1h'].mean()
            exhausted_pct = len(exhausted) / len(df) * 100
        else:
            exhausted_edge = 0.0
            exhausted_pct = 0.0

        # Avg candle range
        avg_range = df['atr_pct'].mean()

        # Overall return
        overall_return = ((df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close']) * 100

        results.append({
            'coin': coin_name,
            'price_range': price_range_pct,
            'overall_return': overall_return,
            'pct_chop': pct_chop,
            'pct_high_vol': pct_high_vol,
            'avg_atr_pct': avg_range,
            'mr_ob_1h': mr_1h,
            'mr_ob_4h': mr_4h,
            'mr_ob_pct': rsi_ob_pct,
            'mr_os_1h': mr_os_1h,
            'mr_os_4h': mr_os_4h,
            'manic_edge': manic_edge,
            'manic_pct': manic_pct,
            'exhausted_edge': exhausted_edge,
            'exhausted_pct': exhausted_pct
        })

    except Exception as e:
        print(f"  ERROR: {e}")
        continue

# Convert to DataFrame
results_df = pd.DataFrame(results)

print()
print("="*140)
print("📊 OVERVIEW - WSZYSTKIE COINY")
print("="*140)
print()

print(f"{'Coin':<15} | {'6M Return':<10} | {'Avg ATR%':<9} | {'% Chop':<8} | {'% High Vol':<11}")
print("-"*140)

for idx, row in results_df.iterrows():
    status = "📈" if row['overall_return'] > 0 else "📉"
    print(f"{row['coin']:<15} | {row['overall_return']:>8.1f}% | {row['avg_atr_pct']:>7.2f}% | {row['pct_chop']:>6.1f}% | {row['pct_high_vol']:>9.1f}% {status}")

print()

# ============================================
# RANKING #1: MEAN REVERSION (SHORT OB)
# ============================================
print("="*140)
print("🎯 RANKING #1: MEAN REVERSION - SHORT OVERBOUGHT (RSI > 70)")
print("="*140)
print()

# Sort by mean reversion edge (most negative = best for SHORT)
mr_ranked = results_df.sort_values('mr_ob_1h', ascending=True)

print(f"{'Rank':<6} | {'Coin':<15} | {'1h Return':<11} | {'4h Return':<11} | {'% Time OB':<10} | {'Edge Quality':<15}")
print("-"*140)

for rank, (idx, row) in enumerate(mr_ranked.head(10).iterrows(), 1):
    edge_quality = "✅ STRONG" if row['mr_ob_1h'] < -0.2 else ("⚠️  WEAK" if row['mr_ob_1h'] < -0.05 else "❌ NONE")
    print(f"{rank:<6} | {row['coin']:<15} | {row['mr_ob_1h']:>9.2f}% | {row['mr_ob_4h']:>9.2f}% | {row['mr_ob_pct']:>8.1f}% | {edge_quality:<15}")

print()

# ============================================
# RANKING #2: LEAST CHOPPY
# ============================================
print("="*140)
print("🎯 RANKING #2: LEAST CHOPPY (More Tradeable)")
print("="*140)
print()

chop_ranked = results_df.sort_values('pct_chop', ascending=True)

print(f"{'Rank':<6} | {'Coin':<15} | {'% Chop':<10} | {'Avg ATR%':<10} | {'Tradeability':<15}")
print("-"*140)

for rank, (idx, row) in enumerate(chop_ranked.head(10).iterrows(), 1):
    tradeable = "✅ GOOD" if row['pct_chop'] < 60 else ("⚠️  MEDIUM" if row['pct_chop'] < 75 else "❌ BAD")
    print(f"{rank:<6} | {row['coin']:<15} | {row['pct_chop']:>8.1f}% | {row['avg_atr_pct']:>8.2f}% | {tradeable:<15}")

print()

# ============================================
# RANKING #3: MANIC PUMP FADE
# ============================================
print("="*140)
print("🎯 RANKING #3: MANIC PUMP FADE (RSI > 75 + High Vol)")
print("="*140)
print()

manic_ranked = results_df.sort_values('manic_edge', ascending=True)

print(f"{'Rank':<6} | {'Coin':<15} | {'1h Edge':<11} | {'% Time Manic':<13} | {'Tradeable?':<15}")
print("-"*140)

for rank, (idx, row) in enumerate(manic_ranked.head(10).iterrows(), 1):
    tradeable = "✅ YES" if row['manic_edge'] < -0.15 and row['manic_pct'] > 0.5 else "❌ NO"
    print(f"{rank:<6} | {row['coin']:<15} | {row['manic_edge']:>9.2f}% | {row['manic_pct']:>11.1f}% | {tradeable:<15}")

print()

# ============================================
# RANKING #4: EXHAUSTED TOP
# ============================================
print("="*140)
print("🎯 RANKING #4: EXHAUSTED TOP (RSI > 70 + Low Vol)")
print("="*140)
print()

exhausted_ranked = results_df.sort_values('exhausted_edge', ascending=True)

print(f"{'Rank':<6} | {'Coin':<15} | {'1h Edge':<11} | {'% Time':<10} | {'Tradeable?':<15}")
print("-"*140)

for rank, (idx, row) in enumerate(exhausted_ranked.head(10).iterrows(), 1):
    tradeable = "✅ YES" if row['exhausted_edge'] < -0.2 and row['exhausted_pct'] > 1.0 else "❌ NO"
    print(f"{rank:<6} | {row['coin']:<15} | {row['exhausted_edge']:>9.2f}% | {row['exhausted_pct']:>8.1f}% | {tradeable:<15}")

print()

# ============================================
# TOP 5 RECOMMENDATIONS
# ============================================
print("="*140)
print("🏆 TOP 5 COINS DO TRADOWANIA (Overall Score)")
print("="*140)
print()

# Calculate composite score
results_df['score'] = (
    -results_df['pct_chop'] * 0.3 +  # Lower chop = better
    results_df['mr_ob_1h'].fillna(0) * 100 * 0.4 +  # More negative = better
    -results_df['pct_high_vol'] * 0.1 +  # Lower chaos = better
    results_df['manic_edge'].fillna(0) * 50 * 0.2  # More negative = better
)

top_ranked = results_df.sort_values('score', ascending=True)

print(f"{'Rank':<6} | {'Coin':<15} | {'Score':<10} | {'Best Edge':<30} | {'Why?':<50}")
print("-"*140)

for rank, (idx, row) in enumerate(top_ranked.head(5).iterrows(), 1):
    # Determine best edge
    edges = {
        'MR_OB': row['mr_ob_1h'],
        'MANIC': row['manic_edge'],
        'EXHAUSTED': row['exhausted_edge']
    }

    best_edge_name = min(edges, key=edges.get)
    best_edge_val = edges[best_edge_name]

    if best_edge_name == 'MR_OB':
        best_edge_str = f"SHORT RSI>70 ({best_edge_val:.2f}%)"
        why = f"Mean reversion, {row['pct_chop']:.0f}% chop"
    elif best_edge_name == 'MANIC':
        best_edge_str = f"Fade manic pump ({best_edge_val:.2f}%)"
        why = f"High vol reversals, {row['manic_pct']:.1f}% occurrence"
    else:
        best_edge_str = f"Exhausted top ({best_edge_val:.2f}%)"
        why = f"Low vol reversals, {row['exhausted_pct']:.1f}% occurrence"

    print(f"{rank:<6} | {row['coin']:<15} | {row['score']:>8.1f} | {best_edge_str:<30} | {why:<50}")

print()
print("="*140)
print("🎓 VERDICT:")
print("="*140)

winner = top_ranked.iloc[0]
print(f"\n✅ BEST COIN: {winner['coin']}")
print(f"   Score: {winner['score']:.1f}")
print(f"   % Chop: {winner['pct_chop']:.1f}% (lower is better)")
print(f"   Mean Reversion: {winner['mr_ob_1h']:.2f}% after RSI > 70")
print(f"   Avg ATR: {winner['avg_atr_pct']:.2f}%")
print()

if winner['mr_ob_1h'] < -0.2:
    print("   💡 STRATEGY: SHORT reversal on RSI > 70-75 with limit offset")
elif winner['manic_edge'] < -0.15:
    print("   💡 STRATEGY: Fade MANIC_PUMP (RSI > 75 + ATR > 0.6%)")
elif winner['pct_chop'] < 50:
    print("   💡 STRATEGY: Trend following (low chop = cleaner trends)")
else:
    print("   ⚠️  STRATEGY: Needs further investigation")

print()
print("="*140)
