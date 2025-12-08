#!/usr/bin/env python3
"""
Market Archaeology: Find the overarching conditions that separate
profitable periods from catastrophic losing periods

Goal: Discover simple macro indicators that say "DON'T TRADE NOW"
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def calculate_ema(prices, period):
    return prices.ewm(span=period, adjust=False).mean()


def analyze_market_structure():
    """Analyze market conditions during different time periods"""

    # Load data
    df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Calculate indicators
    df['ema20'] = calculate_ema(df['close'], 20)
    df['ema50'] = calculate_ema(df['close'], 50)
    df['ema100'] = calculate_ema(df['close'], 100)
    df['ema200'] = calculate_ema(df['close'], 200)

    # Price momentum over different timeframes
    df['momentum_1d'] = df['close'].pct_change(96) * 100    # 1 day = 96 bars
    df['momentum_3d'] = df['close'].pct_change(288) * 100   # 3 days
    df['momentum_7d'] = df['close'].pct_change(672) * 100   # 7 days
    df['momentum_14d'] = df['close'].pct_change(1344) * 100 # 14 days
    df['momentum_30d'] = df['close'].pct_change(2880) * 100 # 30 days

    # EMA alignment (are EMAs stacked correctly for downtrend?)
    df['ema_bearish'] = (df['ema20'] < df['ema50']) & (df['ema50'] < df['ema100']) & (df['ema100'] < df['ema200'])
    df['ema_bullish'] = (df['ema20'] > df['ema50']) & (df['ema50'] > df['ema100']) & (df['ema100'] > df['ema200'])

    # Price vs EMAs
    df['price_vs_ema50'] = (df['close'] - df['ema50']) / df['ema50'] * 100
    df['price_vs_ema100'] = (df['close'] - df['ema100']) / df['ema100'] * 100
    df['price_vs_ema200'] = (df['close'] - df['ema200']) / df['ema200'] * 100

    # Volatility
    df['returns'] = df['close'].pct_change()
    df['volatility_7d'] = df['returns'].rolling(672).std() * 100   # 7 days
    df['volatility_14d'] = df['returns'].rolling(1344).std() * 100 # 14 days
    df['volatility_30d'] = df['returns'].rolling(2880).std() * 100 # 30 days

    # Higher highs / lower lows (trend structure)
    df['high_20'] = df['high'].rolling(20).max()
    df['low_20'] = df['low'].rolling(20).min()
    df['high_100'] = df['high'].rolling(100).max()
    df['low_100'] = df['low'].rolling(100).min()

    # Distance from recent extremes
    df['dist_from_high_20'] = (df['close'] - df['high_20']) / df['high_20'] * 100
    df['dist_from_high_100'] = (df['close'] - df['high_100']) / df['high_100'] * 100

    # Define key periods
    periods = {
        'Current (Nov-Dec 2025)': ('2025-11-01', '2025-12-03'),
        'March Catastrophe': ('2025-03-10', '2025-03-30'),
        'May Losses': ('2025-05-12', '2025-05-25'),
        'Good Period (Oct)': ('2025-10-06', '2025-10-26'),
        'Good Period (Aug)': ('2025-08-11', '2025-08-24'),
        'Early Losses (Jan-Feb)': ('2025-01-27', '2025-02-16'),
    }

    print("=" * 100)
    print("MARKET ARCHAEOLOGY: COMPARING PROFITABLE VS CATASTROPHIC PERIODS")
    print("=" * 100)

    results = {}

    for period_name, (start, end) in periods.items():
        period_df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)]

        if len(period_df) == 0:
            continue

        # Calculate average conditions
        avg_conditions = {
            'period': period_name,
            'bars': len(period_df),
            'price_start': period_df['close'].iloc[0],
            'price_end': period_df['close'].iloc[-1],
            'price_change': (period_df['close'].iloc[-1] / period_df['close'].iloc[0] - 1) * 100,

            # Momentum
            'momentum_7d': period_df['momentum_7d'].mean(),
            'momentum_14d': period_df['momentum_14d'].mean(),
            'momentum_30d': period_df['momentum_30d'].mean(),

            # EMA alignment
            'pct_ema_bearish': period_df['ema_bearish'].mean() * 100,
            'pct_ema_bullish': period_df['ema_bullish'].mean() * 100,

            # Price vs EMAs
            'price_vs_ema50': period_df['price_vs_ema50'].mean(),
            'price_vs_ema100': period_df['price_vs_ema100'].mean(),
            'price_vs_ema200': period_df['price_vs_ema200'].mean(),

            # Volatility
            'volatility_14d': period_df['volatility_14d'].mean(),

            # Distance from highs
            'dist_from_high_100': period_df['dist_from_high_100'].mean(),
        }

        results[period_name] = avg_conditions

    # Display results
    print("\n" + "=" * 100)
    print("PERIOD ANALYSIS")
    print("=" * 100)

    for period_name, stats in results.items():
        is_catastrophic = 'Catastrophe' in period_name or 'Losses' in period_name
        marker = "❌ BAD" if is_catastrophic else "✅ GOOD"

        print(f"\n{marker} {period_name}")
        print(f"  Price change: {stats['price_change']:+.1f}%")
        print(f"  7d momentum: {stats['momentum_7d']:+.1f}%")
        print(f"  14d momentum: {stats['momentum_14d']:+.1f}%")
        print(f"  30d momentum: {stats['momentum_30d']:+.1f}%")
        print(f"  EMA bearish alignment: {stats['pct_ema_bearish']:.0f}%")
        print(f"  EMA bullish alignment: {stats['pct_ema_bullish']:.0f}%")
        print(f"  Price vs EMA100: {stats['price_vs_ema100']:+.1f}%")
        print(f"  Price vs EMA200: {stats['price_vs_ema200']:+.1f}%")
        print(f"  Distance from 100-bar high: {stats['dist_from_high_100']:+.1f}%")
        print(f"  14d volatility: {stats['volatility_14d']:.2f}%")

    # Compare catastrophic vs good periods
    print("\n" + "=" * 100)
    print("KEY DIFFERENCES: CATASTROPHIC VS PROFITABLE PERIODS")
    print("=" * 100)

    catastrophic_periods = [k for k in results.keys() if 'Catastrophe' in k or 'Losses' in k]
    good_periods = [k for k in results.keys() if 'Good' in k or 'Current' in k]

    # Calculate averages
    cat_avg = {
        'momentum_7d': np.mean([results[p]['momentum_7d'] for p in catastrophic_periods]),
        'momentum_14d': np.mean([results[p]['momentum_14d'] for p in catastrophic_periods]),
        'momentum_30d': np.mean([results[p]['momentum_30d'] for p in catastrophic_periods]),
        'pct_ema_bullish': np.mean([results[p]['pct_ema_bullish'] for p in catastrophic_periods]),
        'price_vs_ema100': np.mean([results[p]['price_vs_ema100'] for p in catastrophic_periods]),
        'price_vs_ema200': np.mean([results[p]['price_vs_ema200'] for p in catastrophic_periods]),
        'dist_from_high_100': np.mean([results[p]['dist_from_high_100'] for p in catastrophic_periods]),
    }

    good_avg = {
        'momentum_7d': np.mean([results[p]['momentum_7d'] for p in good_periods]),
        'momentum_14d': np.mean([results[p]['momentum_14d'] for p in good_periods]),
        'momentum_30d': np.mean([results[p]['momentum_30d'] for p in good_periods]),
        'pct_ema_bullish': np.mean([results[p]['pct_ema_bullish'] for p in good_periods]),
        'price_vs_ema100': np.mean([results[p]['price_vs_ema100'] for p in good_periods]),
        'price_vs_ema200': np.mean([results[p]['price_vs_ema200'] for p in good_periods]),
        'dist_from_high_100': np.mean([results[p]['dist_from_high_100'] for p in good_periods]),
    }

    print("\nCATASTROPHIC PERIODS (average conditions):")
    for key, val in cat_avg.items():
        print(f"  {key}: {val:+.2f}")

    print("\nPROFITABLE PERIODS (average conditions):")
    for key, val in good_avg.items():
        print(f"  {key}: {val:+.2f}")

    print("\nDIFFERENCES:")
    for key in cat_avg.keys():
        diff = good_avg[key] - cat_avg[key]
        print(f"  {key}: {diff:+.2f}")

    # Propose filters
    print("\n" + "=" * 100)
    print("🎯 PROPOSED MACRO FILTERS (DON'T TRADE WHEN...)")
    print("=" * 100)

    print("\n1️⃣  MOMENTUM FILTER:")
    print(f"   Catastrophic: 7d momentum = {cat_avg['momentum_7d']:+.1f}%")
    print(f"   Profitable: 7d momentum = {good_avg['momentum_7d']:+.1f}%")
    print(f"   ✅ DON'T TRADE when 7-day momentum > +5%")

    print("\n2️⃣  EMA ALIGNMENT FILTER:")
    print(f"   Catastrophic: {cat_avg['pct_ema_bullish']:.0f}% bullish EMA alignment")
    print(f"   Profitable: {good_avg['pct_ema_bullish']:.0f}% bullish EMA alignment")
    print(f"   ✅ DON'T TRADE when EMAs are bullish aligned (EMA20 > EMA50 > EMA100)")

    print("\n3️⃣  DISTANCE FROM HIGHS FILTER:")
    print(f"   Catastrophic: {cat_avg['dist_from_high_100']:+.1f}% from 100-bar high")
    print(f"   Profitable: {good_avg['dist_from_high_100']:+.1f}% from 100-bar high")
    print(f"   ✅ DON'T TRADE when price is within -5% of 100-bar high")

    print("\n4️⃣  PRICE VS EMA200 FILTER:")
    print(f"   Catastrophic: {cat_avg['price_vs_ema200']:+.1f}% vs EMA200")
    print(f"   Profitable: {good_avg['price_vs_ema200']:+.1f}% vs EMA200")
    print(f"   ✅ DON'T TRADE when price > EMA200")

    print("\n5️⃣  30-DAY MOMENTUM FILTER:")
    print(f"   Catastrophic: {cat_avg['momentum_30d']:+.1f}% 30-day momentum")
    print(f"   Profitable: {good_avg['momentum_30d']:+.1f}% 30-day momentum")
    print(f"   ✅ DON'T TRADE when 30-day momentum > 0%")

    # Test proposed filters on full dataset
    print("\n" + "=" * 100)
    print("TESTING PROPOSED FILTERS ON FULL DATASET")
    print("=" * 100)

    # Create combined filter signal
    df['macro_filter'] = (
        (df['momentum_7d'] < 5) &           # Not in strong rally
        (df['momentum_30d'] < 0) &          # Longer term downtrend
        (~df['ema_bullish']) &               # EMAs not bullish aligned
        (df['dist_from_high_100'] < -5) &   # Not near recent highs
        (df['price_vs_ema200'] < 0)         # Below EMA200
    )

    print(f"\nBars passing macro filter: {df['macro_filter'].sum()} of {len(df)} ({df['macro_filter'].mean()*100:.1f}%)")

    # Check which periods would be filtered
    print("\nPeriod filtering results:")
    for period_name, (start, end) in periods.items():
        period_df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)]
        if len(period_df) > 0:
            pct_allowed = period_df['macro_filter'].mean() * 100
            status = "✅ ALLOWED" if pct_allowed > 50 else "❌ BLOCKED"
            print(f"  {status} {period_name}: {pct_allowed:.0f}% of time allowed to trade")

    return df, results


if __name__ == '__main__':
    df, results = analyze_market_structure()
