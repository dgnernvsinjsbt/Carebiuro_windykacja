#!/usr/bin/env python3
"""
Scan coins for similarity to FARTCOIN volatility profile
Goal: Find coins where our 7.14x/8.88x R:R strategies could work
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def analyze_coin(filepath: str) -> dict:
    """Analyze a coin's volatility and liquidity profile"""
    try:
        df = pd.read_csv(filepath)

        # Standardize column names
        if 'timestamp' not in df.columns and 'time' in df.columns:
            df['timestamp'] = df['time']

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Basic stats
        days = (df['timestamp'].max() - df['timestamp'].min()).days
        candles = len(df)

        # Price change
        start_price = df['close'].iloc[0]
        end_price = df['close'].iloc[-1]
        total_return = ((end_price - start_price) / start_price) * 100

        # Volatility metrics
        df['returns'] = df['close'].pct_change() * 100
        df['range_pct'] = ((df['high'] - df['low']) / df['low']) * 100

        avg_1m_volatility = df['returns'].std()
        avg_candle_range = df['range_pct'].mean()
        max_candle_range = df['range_pct'].max()

        # ATR-like metric
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr_pct'] = (df['tr'] / df['close']) * 100
        avg_atr_pct = df['atr_pct'].mean()

        # Trend strength - how often does price move >1% in a candle?
        big_moves = (abs(df['returns']) > 1).sum() / len(df) * 100

        # Volume analysis
        avg_volume = df['volume'].mean()
        volume_usd = avg_volume * df['close'].mean()  # Rough USD volume

        # Explosive moves (body > 1.2%, our entry condition)
        df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
        explosive_candles = (df['body_pct'] > 1.2).sum() / len(df) * 100

        return {
            'days': days,
            'candles': candles,
            'total_return': total_return,
            'avg_1m_vol': avg_1m_volatility,
            'avg_range': avg_candle_range,
            'max_range': max_candle_range,
            'avg_atr_pct': avg_atr_pct,
            'big_moves_pct': big_moves,
            'explosive_pct': explosive_candles,
            'avg_volume': avg_volume,
            'volume_usd': volume_usd,
            'current_price': end_price
        }
    except Exception as e:
        return {'error': str(e)}

def main():
    print("=" * 90)
    print("COIN VOLATILITY SCAN - Finding FARTCOIN-like opportunities")
    print("=" * 90)
    print()

    # Find all 1-minute USDT pairs
    data_dir = Path('/workspaces/Carebiuro_windykacja/trading')
    files = list(data_dir.glob('*_usdt_1m_*.csv')) + list(data_dir.glob('*_1m_*.csv'))

    # Also check root
    root_files = list(Path('/workspaces/Carebiuro_windykacja').glob('*_usdt_1m_*.csv'))
    files.extend(root_files)

    # Deduplicate
    files = list(set(files))

    results = []

    for f in files:
        coin_name = f.stem.split('_')[0].upper()
        print(f"Analyzing {coin_name}...", end=" ")

        stats = analyze_coin(str(f))
        if 'error' not in stats:
            stats['coin'] = coin_name
            stats['file'] = str(f)
            results.append(stats)
            print(f"✓ ({stats['days']} days, {stats['candles']:,} candles)")
        else:
            print(f"✗ ({stats['error'][:30]})")

    if not results:
        print("No valid data found!")
        return

    df = pd.DataFrame(results)

    # Find FARTCOIN baseline
    fartcoin = df[df['coin'] == 'FARTCOIN'].iloc[0] if 'FARTCOIN' in df['coin'].values else None

    print()
    print("=" * 90)
    print("FARTCOIN BASELINE (our strategy is optimized for this profile)")
    print("=" * 90)

    if fartcoin is not None:
        print(f"  Days of data:        {fartcoin['days']}")
        print(f"  1-min volatility:    {fartcoin['avg_1m_vol']:.3f}%")
        print(f"  Avg candle range:    {fartcoin['avg_range']:.3f}%")
        print(f"  Avg ATR %:           {fartcoin['avg_atr_pct']:.3f}%")
        print(f"  Big moves (>1%):     {fartcoin['big_moves_pct']:.2f}% of candles")
        print(f"  Explosive (>1.2%):   {fartcoin['explosive_pct']:.2f}% of candles")
        print(f"  Total return:        {fartcoin['total_return']:+.1f}%")

    print()
    print("=" * 90)
    print("ALL COINS RANKED BY SIMILARITY TO FARTCOIN")
    print("=" * 90)
    print()

    # Calculate similarity score
    if fartcoin is not None:
        # Score based on volatility similarity (closer = better)
        df['vol_diff'] = abs(df['avg_1m_vol'] - fartcoin['avg_1m_vol'])
        df['range_diff'] = abs(df['avg_range'] - fartcoin['avg_range'])
        df['atr_diff'] = abs(df['avg_atr_pct'] - fartcoin['avg_atr_pct'])
        df['explosive_diff'] = abs(df['explosive_pct'] - fartcoin['explosive_pct'])

        # Normalize and create score (lower = more similar)
        df['similarity_score'] = (
            df['vol_diff'] / df['avg_1m_vol'].max() +
            df['range_diff'] / df['avg_range'].max() +
            df['atr_diff'] / df['avg_atr_pct'].max() +
            df['explosive_diff'] / df['explosive_pct'].max()
        )

        # Sort by similarity
        df = df.sort_values('similarity_score')
    else:
        # Sort by volatility if no FARTCOIN baseline
        df = df.sort_values('avg_1m_vol', ascending=False)

    # Print results
    print(f"{'Coin':<12} {'Days':>6} {'1m Vol%':>8} {'Range%':>8} {'ATR%':>8} {'Expl%':>8} {'BigMv%':>8} {'Return':>10} {'Score':>8}")
    print("-" * 90)

    for _, row in df.iterrows():
        score = row.get('similarity_score', 0)
        marker = "⭐" if row['coin'] == 'FARTCOIN' else ("✓" if score < 0.5 else "")
        print(f"{row['coin']:<12} {row['days']:>6} {row['avg_1m_vol']:>7.3f}% {row['avg_range']:>7.3f}% "
              f"{row['avg_atr_pct']:>7.3f}% {row['explosive_pct']:>7.2f}% {row['big_moves_pct']:>7.2f}% "
              f"{row['total_return']:>+9.1f}% {score:>7.3f} {marker}")

    print()
    print("=" * 90)
    print("RECOMMENDATIONS FOR STRATEGY TESTING")
    print("=" * 90)
    print()

    # Filter good candidates
    # Must have: similar volatility, enough explosive candles, decent liquidity
    good_candidates = df[
        (df['coin'] != 'FARTCOIN') &
        (df['explosive_pct'] > 1.0) &  # At least 1% explosive candles
        (df['avg_1m_vol'] > 0.1) &      # Minimum volatility
        (df['days'] >= 20)              # Enough data
    ].head(5)

    print("TOP CANDIDATES (similar volatility, enough signals):")
    print()

    for i, (_, row) in enumerate(good_candidates.iterrows(), 1):
        print(f"#{i} {row['coin']}")
        print(f"   Volatility: {row['avg_1m_vol']:.3f}% (FARTCOIN: {fartcoin['avg_1m_vol']:.3f}%)" if fartcoin is not None else f"   Volatility: {row['avg_1m_vol']:.3f}%")
        print(f"   Explosive candles: {row['explosive_pct']:.2f}%")
        print(f"   Data: {row['days']} days, {row['candles']:,} candles")
        print(f"   Price: ${row['current_price']:.4f}")
        print()

    # Coins that are TOO different
    print("AVOID (too different from FARTCOIN profile):")
    too_stable = df[df['avg_1m_vol'] < 0.05]['coin'].tolist()
    if too_stable:
        print(f"   Too stable: {', '.join(too_stable)}")

    too_volatile = df[df['avg_1m_vol'] > fartcoin['avg_1m_vol'] * 3]['coin'].tolist() if fartcoin is not None else []
    if too_volatile:
        print(f"   Too volatile: {', '.join(too_volatile)}")

    print()
    print("=" * 90)
    print("LIQUIDITY CHECK (important for real trading)")
    print("=" * 90)
    print()

    # Sort by volume
    df_vol = df.sort_values('volume_usd', ascending=False)
    print(f"{'Coin':<12} {'Avg Volume':>15} {'Est. USD/min':>15} {'Liquidity':>12}")
    print("-" * 60)

    for _, row in df_vol.iterrows():
        liq = "HIGH" if row['volume_usd'] > 100000 else ("MEDIUM" if row['volume_usd'] > 10000 else "LOW ⚠️")
        print(f"{row['coin']:<12} {row['avg_volume']:>15,.0f} ${row['volume_usd']:>14,.0f} {liq:>12}")

    print()
    print("⚠️  LOW liquidity = slippage problems, avoid for live trading")
    print("✓  MEDIUM+ liquidity = OK for testing, monitor slippage")
    print("✓  HIGH liquidity = Good for live trading")

if __name__ == "__main__":
    main()
