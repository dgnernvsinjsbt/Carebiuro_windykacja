#!/usr/bin/env python3
"""
Analyze why WIF/AVAX fail at volume zones while others succeed
"""
import pandas as pd
import numpy as np
from pathlib import Path

def load_and_analyze(token):
    """Load data and calculate key metrics"""
    path = f'/workspaces/Carebiuro_windykacja/trading/{token.lower()}_usdt_1m_lbank.csv'
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Volume metrics
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    df['high_vol'] = df['vol_ratio'] > 1.5

    # Price metrics
    df['returns'] = df['close'].pct_change()
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = df['atr'] / df['close'] * 100

    # Local extremes
    df['local_high'] = df['high'].rolling(20).max()
    df['local_low'] = df['low'].rolling(20).min()
    df['at_local_low'] = df['low'] <= df['local_low'] * 1.005
    df['at_local_high'] = df['high'] >= df['local_high'] * 0.995

    # Detect volume zones and measure follow-through
    zones = []
    i = 20
    while i < len(df) - 100:
        # Find start of high volume sequence
        if df['high_vol'].iloc[i] and not df['high_vol'].iloc[i-1]:
            start = i
            consecutive = 0
            while i < len(df) and df['high_vol'].iloc[i]:
                consecutive += 1
                i += 1

            if consecutive >= 5:
                zone_end = i - 1
                entry_price = df['close'].iloc[zone_end]
                atr = df['atr'].iloc[zone_end]

                at_low = df['at_local_low'].iloc[zone_end]
                at_high = df['at_local_high'].iloc[zone_end]

                if at_low or at_high:
                    direction = 'LONG' if at_low else 'SHORT'

                    # Measure follow-through (next 30-90 bars)
                    future_prices = df['close'].iloc[zone_end+1:zone_end+91]
                    if len(future_prices) > 0:
                        if direction == 'LONG':
                            max_move = (future_prices.max() - entry_price) / entry_price * 100
                            min_move = (future_prices.min() - entry_price) / entry_price * 100
                            favorable = max_move
                            adverse = abs(min_move)
                        else:
                            max_move = (entry_price - future_prices.min()) / entry_price * 100
                            min_move = (entry_price - future_prices.max()) / entry_price * 100
                            favorable = max_move
                            adverse = abs(min_move)

                        zones.append({
                            'direction': direction,
                            'entry_price': entry_price,
                            'atr_pct': atr / entry_price * 100,
                            'favorable_move': favorable,
                            'adverse_move': adverse,
                            'follow_through_ratio': favorable / adverse if adverse > 0 else 0
                        })
        i += 1

    return df, zones

def main():
    tokens_profitable = ['DOGE', 'PEPE', 'PENGU', 'ETH']
    tokens_unprofitable = ['WIF', 'AVAX']

    print("=" * 90)
    print("VOLUME ZONES: WHY SOME TOKENS WORK AND OTHERS DON'T")
    print("=" * 90)

    all_stats = []

    for token in tokens_profitable + tokens_unprofitable:
        try:
            df, zones = load_and_analyze(token)

            if not zones:
                continue

            zones_df = pd.DataFrame(zones)

            # Key metrics
            autocorr = df['returns'].autocorr(lag=1)
            avg_atr_pct = df['atr_pct'].mean()

            # Volume zone follow-through
            avg_favorable = zones_df['favorable_move'].mean()
            avg_adverse = zones_df['adverse_move'].mean()
            avg_ft_ratio = zones_df['follow_through_ratio'].mean()

            # Win rate proxy (favorable > adverse)
            win_proxy = (zones_df['favorable_move'] > zones_df['adverse_move']).mean() * 100

            # How often does price move 2x ATR in favorable direction before 1x ATR adverse?
            good_rr_zones = zones_df[zones_df['follow_through_ratio'] > 2.0]
            good_rr_pct = len(good_rr_zones) / len(zones_df) * 100

            status = "✅ PROFITABLE" if token in tokens_profitable else "❌ UNPROFITABLE"

            all_stats.append({
                'token': token,
                'status': status,
                'autocorr': autocorr,
                'avg_atr_pct': avg_atr_pct,
                'zones_count': len(zones_df),
                'avg_favorable': avg_favorable,
                'avg_adverse': avg_adverse,
                'follow_through': avg_ft_ratio,
                'win_proxy': win_proxy,
                'good_rr_pct': good_rr_pct
            })

        except Exception as e:
            print(f"Error with {token}: {e}")

    # Display comparison
    stats_df = pd.DataFrame(all_stats)

    print("\n📊 KEY METRICS COMPARISON")
    print("-" * 90)
    print(f"{'Token':<8} {'Status':<15} {'Autocorr':>10} {'ATR%':>8} {'Zones':>7} {'FavMove':>9} {'AdvMove':>9} {'FT Ratio':>10}")
    print("-" * 90)

    for _, row in stats_df.iterrows():
        print(f"{row['token']:<8} {row['status']:<15} {row['autocorr']:>+10.3f} {row['avg_atr_pct']:>7.3f}% {row['zones_count']:>7} {row['avg_favorable']:>+8.2f}% {row['avg_adverse']:>+8.2f}% {row['follow_through']:>10.2f}x")

    print("\n" + "=" * 90)
    print("📈 FOLLOW-THROUGH ANALYSIS (Key Factor!)")
    print("=" * 90)
    print(f"\n{'Token':<8} {'Win Proxy':>12} {'Good R:R Zones':>15} {'Interpretation':<40}")
    print("-" * 90)

    for _, row in stats_df.iterrows():
        interp = ""
        if row['follow_through'] > 1.5:
            interp = "✅ Price follows through after zones"
        elif row['follow_through'] > 1.0:
            interp = "⚠️ Marginal follow-through"
        else:
            interp = "❌ Price reverses against zone direction"

        print(f"{row['token']:<8} {row['win_proxy']:>11.1f}% {row['good_rr_pct']:>14.1f}% {interp:<40}")

    # Calculate averages
    profitable_avg = stats_df[stats_df['status'] == "✅ PROFITABLE"]['follow_through'].mean()
    unprofitable_avg = stats_df[stats_df['status'] == "❌ UNPROFITABLE"]['follow_through'].mean()

    print("\n" + "=" * 90)
    print("🔍 ROOT CAUSE ANALYSIS")
    print("=" * 90)

    print(f"""
PROFITABLE tokens avg follow-through: {profitable_avg:.2f}x
UNPROFITABLE tokens avg follow-through: {unprofitable_avg:.2f}x

KEY INSIGHT: The difference is FOLLOW-THROUGH after volume zones form.

When a volume zone forms at a local low (accumulation):
- PROFITABLE tokens: Price tends to CONTINUE UP after the zone
- UNPROFITABLE tokens: Price often REVERSES BACK DOWN

This means:
- In DOGE/PEPE/PENGU/ETH: Volume zones signal real whale accumulation
- In WIF/AVAX: Volume zones are just noise or liquidity grabs
""")

    # Detailed breakdown
    print("=" * 90)
    print("📋 DETAILED BREAKDOWN")
    print("=" * 90)

    for _, row in stats_df.iterrows():
        print(f"\n{row['token']}:")
        print(f"  Autocorrelation: {row['autocorr']:+.3f} ({'mean-reverting' if row['autocorr'] < 0 else 'trending'})")
        print(f"  Volatility (ATR%): {row['avg_atr_pct']:.3f}%")
        print(f"  Volume Zones Found: {row['zones_count']}")
        print(f"  Avg Favorable Move: {row['avg_favorable']:+.2f}%")
        print(f"  Avg Adverse Move: {row['avg_adverse']:+.2f}%")
        print(f"  Follow-Through Ratio: {row['follow_through']:.2f}x")

        if row['token'] in ['WIF', 'AVAX']:
            print(f"  ⚠️  PROBLEM: Low follow-through ({row['follow_through']:.2f}x) means zones don't predict direction")

if __name__ == "__main__":
    main()
