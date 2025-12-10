#!/usr/bin/env python3
"""
Download 30-day 1-minute data from BingX for ATR strategy candidates
using the CHUNKING method (1000 candles per request, working backwards)
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import time

def fetch_bingx_30d(symbol):
    """Download 30 days of 1min data using backward chunking"""
    url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=30)

    all_data = []
    current_end = end_time
    chunk_size = timedelta(minutes=1000)  # 1000 candles per chunk

    print(f"  {symbol}...", end='', flush=True)

    batch_count = 0
    while current_end > start_time:
        current_start = max(start_time, current_end - chunk_size)

        params = {
            'symbol': symbol,
            'interval': '1m',
            'startTime': int(current_start.timestamp() * 1000),
            'endTime': int(current_end.timestamp() * 1000),
            'limit': 1000
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != 0:
                print(f" ❌ {data.get('msg')}")
                return None

            klines = data.get('data', [])
            if klines:
                all_data.extend(klines)
                batch_count += 1
                if batch_count % 10 == 0:
                    print(".", end='', flush=True)

            # Move to next chunk (backwards)
            current_end = current_start - timedelta(minutes=1)
            time.sleep(0.2)  # Rate limit

        except Exception as e:
            print(f" ❌ {e}")
            return None

    if len(all_data) < 20000:
        print(f" ⚠️  Only {len(all_data):,} candles")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp'])

    print(f" ✅ {len(df):,} candles ({(df['timestamp'].max() - df['timestamp'].min()).days} days)")
    return df

def analyze_coin(df, symbol):
    """Calculate ATR strategy suitability metrics"""
    df = df.copy()

    df['returns'] = df['close'].pct_change()
    df['range_pct'] = (df['high'] - df['low']) / df['close'] * 100

    # ATR calculation
    df['prev_close'] = df['close'].shift(1)
    df['tr'] = df[['high', 'low', 'prev_close']].apply(
        lambda x: max(x['high'] - x['low'],
                     abs(x['high'] - x['prev_close']),
                     abs(x['low'] - x['prev_close'])) if pd.notna(x['prev_close']) else x['high'] - x['low'],
        axis=1
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100

    # ATR expansion (key metric)
    df['atr_ma20'] = df['atr'].rolling(20).mean()
    df['atr_expansion'] = df['atr'] / df['atr_ma20']

    return {
        'symbol': symbol,
        'candles': len(df),
        'days': round((df['timestamp'].max() - df['timestamp'].min()).days, 1),
        'avg_price': df['close'].mean(),
        'price_range': f"${df['close'].min():.4f} - ${df['close'].max():.4f}",
        'daily_vol': df['returns'].std() * np.sqrt(1440) * 100,
        'avg_range_pct': df['range_pct'].mean(),
        'range_95th': df['range_pct'].quantile(0.95),
        'explosive_pct': (df['range_pct'] > 1.0).sum() / len(df) * 100,
        'volume_cv': df['volume'].std() / df['volume'].mean(),
        'avg_atr_pct': df['atr_pct'].mean(),
        'atr_expansion_gt_1_5': (df['atr_expansion'] > 1.5).sum() / len(df) * 100,
    }

# Candidate meme coins on BingX
candidates = [
    'WIF-USDT',       # dogwifhat
    'POPCAT-USDT',    # Popcat
    'BRETT-USDT',     # Brett
    'BOME-USDT',      # Book of Meme
    '1000PEPE-USDT',  # Pepe (already have but re-download fresh)
    'FLOKI-USDT',     # Floki
    'SHIB-USDT',      # Shiba
]

print("=" * 100)
print("DOWNLOADING 30-DAY BINGX DATA USING CHUNKING METHOD")
print("=" * 100)
print("Method: Download in 1000-candle chunks, working backwards from now")
print("Target: ~43,200 candles (30 days × 1440 minutes)\n")

results = []
for symbol in candidates:
    df = fetch_bingx_30d(symbol)

    if df is not None and len(df) >= 20000:
        # Save
        filename = f'/workspaces/Carebiuro_windykacja/trading/{symbol.replace("-", "_").lower()}_30d_bingx.csv'
        df.to_csv(filename, index=False)

        # Analyze
        metrics = analyze_coin(df, symbol)
        results.append(metrics)

    time.sleep(0.5)

if not results:
    print("\n❌ No candidates successfully downloaded")
    exit(1)

print(f"\n{'='*100}")
print(f"ANALYSIS: {len(results)} NEW CANDIDATES vs FARTCOIN")
print("=" * 100)

comparison = pd.DataFrame(results)

# FARTCOIN reference
fartcoin = {
    'avg_range_pct': 0.407,
    'explosive_pct': 2.9,
    'volume_cv': 1.50,
    'daily_vol': 11.26,
    'atr_expansion_gt_1_5': 8.5,
}

print(f"\n{'Symbol':<15} {'Days':>5} {'Candles':>8} {'Avg Range':>10} {'Explosive':>10} {'Vol CV':>8} {'ATR>1.5x':>10} {'Score':>7}")
print("-" * 100)

for idx, row in comparison.iterrows():
    # Similarity score
    range_score = min(row['avg_range_pct'] / fartcoin['avg_range_pct'], 2.0) * 20
    explosive_score = min(row['explosive_pct'] / fartcoin['explosive_pct'], 2.0) * 20
    cv_score = min(row['volume_cv'] / fartcoin['volume_cv'], 2.0) * 20
    vol_score = min(row['daily_vol'] / fartcoin['daily_vol'], 2.0) * 20
    atr_score = min(row['atr_expansion_gt_1_5'] / fartcoin['atr_expansion_gt_1_5'], 2.0) * 20
    total_score = range_score + explosive_score + cv_score + vol_score + atr_score

    comparison.loc[idx, 'score'] = total_score

    print(f"{row['symbol']:<15} {row['days']:>5.1f} {row['candles']:>8,} {row['avg_range_pct']:>9.3f}% "
          f"{row['explosive_pct']:>9.1f}% {row['volume_cv']:>8.2f} {row['atr_expansion_gt_1_5']:>9.1f}% {total_score:>7.1f}")

print("-" * 100)
print(f"{'FARTCOIN (REF)':<15} {'30.0':>5} {'46080':>8} {fartcoin['avg_range_pct']:>9.3f}% "
      f"{fartcoin['explosive_pct']:>9.1f}% {fartcoin['volume_cv']:>8.2f} {fartcoin['atr_expansion_gt_1_5']:>9.1f}%  100.0")

# Top 3
top3 = comparison.nlargest(3, 'score')

print("\n" + "=" * 100)
print("🏆 TOP 3 NEW CANDIDATES FOR FARTCOIN ATR STRATEGY")
print("=" * 100)

for i, (_, row) in enumerate(top3.iterrows(), 1):
    verdict = "✅ EXCELLENT" if row['score'] >= 80 else "⚠️ GOOD" if row['score'] >= 60 else "❌ POOR"

    print(f"\n#{i} {row['symbol']} - {row['score']:.1f}/100 {verdict}")
    print(f"   Avg Range:       {row['avg_range_pct']:.3f}% (FARTCOIN: 0.407%)")
    print(f"   Explosive Moves: {row['explosive_pct']:.1f}% (FARTCOIN: 2.9%)")
    print(f"   ATR Expansions:  {row['atr_expansion_gt_1_5']:.1f}% (FARTCOIN: 8.5%) ⭐ KEY")
    print(f"   Volume CV:       {row['volume_cv']:.2f} (FARTCOIN: 1.50)")
    print(f"   Daily Volatility:{row['daily_vol']:.2f}% (FARTCOIN: 11.26%)")
    print(f"   Price Range:     {row['price_range']}")

comparison.to_csv('/workspaces/Carebiuro_windykacja/trading/new_atr_candidates.csv', index=False)
print(f"\n💾 Saved: trading/new_atr_candidates.csv")
