#!/usr/bin/env python3
"""
PIPPIN Volume Zones Strategy Research
Test sustained volume (5+ bars) vs single spikes
Based on success with TRUMP (10.56x), DOGE (10.75x), PEPE (6.80x)
"""

import pandas as pd
import numpy as np
from datetime import datetime

print("=" * 80)
print("PIPPIN VOLUME ZONES RESEARCH")
print("=" * 80)

# Load data
df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\nData: {len(df)} candles ({df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]})")
print(f"Duration: {(df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days} days")

# Calculate indicators
print("\nCalculating indicators...")
df['tr'] = df[['high', 'low', 'close']].apply(
    lambda row: max(row['high'] - row['low'],
                    abs(row['high'] - row['close']),
                    abs(row['low'] - row['close'])), axis=1
)
df['atr_14'] = df['tr'].rolling(window=14).mean()

# Volume analysis
df['vol_ma_30'] = df['volume'].rolling(window=30).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma_30']
df['vol_elevated'] = (df['vol_ratio'] >= 1.5).astype(int)  # Binary flag

# Session filters
df['hour'] = df['timestamp'].dt.hour
df['is_us_session'] = ((df['hour'] >= 14) & (df['hour'] < 21)).astype(int)
df['is_overnight'] = (((df['hour'] >= 21) | (df['hour'] < 7))).astype(int)
df['is_asia_eu'] = ((df['hour'] >= 7) & (df['hour'] < 14)).astype(int)

# 20-bar high/low for zone detection
df['high_20'] = df['high'].rolling(window=20).max()
df['low_20'] = df['low'].rolling(window=20).min()

df = df.dropna().reset_index(drop=True)

print(f"After indicators: {len(df)} candles")

# ============================================================================
# VOLUME ZONE DETECTION (Key Difference from Spikes)
# ============================================================================
def detect_volume_zones(df, volume_threshold=1.5, min_zone_bars=5):
    """
    Detect volume zones: 5+ consecutive bars with volume > threshold

    Returns: List of zones with start/end indices and type (accumulation/distribution)
    """
    zones = []
    in_zone = False
    zone_start = None
    consecutive_count = 0

    for i in range(len(df)):
        if df.iloc[i]['vol_ratio'] >= volume_threshold:
            if not in_zone:
                zone_start = i
                consecutive_count = 1
                in_zone = True
            else:
                consecutive_count += 1
        else:
            # Zone ended
            if in_zone and consecutive_count >= min_zone_bars:
                zone_end = i - 1

                # Determine zone type based on price at extremes
                zone_df = df.iloc[zone_start:zone_end+1]
                lookback_df = df.iloc[max(0, zone_start-20):zone_start]

                if len(lookback_df) > 0:
                    lookback_high = lookback_df['high'].max()
                    lookback_low = lookback_df['low'].min()

                    # Accumulation zone: volume at local low
                    if zone_df['low'].min() <= lookback_low * 1.01:  # Within 1% of low
                        zone_type = 'accumulation'
                    # Distribution zone: volume at local high
                    elif zone_df['high'].max() >= lookback_high * 0.99:  # Within 1% of high
                        zone_type = 'distribution'
                    else:
                        zone_type = 'neutral'

                    zones.append({
                        'start': zone_start,
                        'end': zone_end,
                        'bars': consecutive_count,
                        'type': zone_type
                    })

            in_zone = False
            zone_start = None
            consecutive_count = 0

    return zones

# ============================================================================
# STRATEGY FUNCTION
# ============================================================================
def test_volume_zones(df, config):
    """
    Test volume zones strategy with given configuration
    """
    volume_threshold = config['volume_threshold']
    min_zone_bars = config['min_zone_bars']
    session_filter = config['session_filter']
    sl_atr_mult = config['sl_atr_mult']
    tp_atr_mult = config['tp_atr_mult']
    max_hold_bars = config['max_hold_bars']

    # Detect zones
    zones = detect_volume_zones(df, volume_threshold, min_zone_bars)

    if len(zones) == 0:
        return None

    trades = []

    for zone in zones:
        # Enter AFTER zone ends
        entry_idx = zone['end'] + 1
        if entry_idx >= len(df):
            continue

        entry_bar = df.iloc[entry_idx]

        # Session filter
        if session_filter == 'us' and entry_bar['is_us_session'] == 0:
            continue
        elif session_filter == 'overnight' and entry_bar['is_overnight'] == 0:
            continue
        elif session_filter == 'asia_eu' and entry_bar['is_asia_eu'] == 0:
            continue
        # 'all' = no filter

        # Direction based on zone type
        if zone['type'] == 'accumulation':
            direction = 'LONG'  # Buy at low
            entry_price = entry_bar['close']
        elif zone['type'] == 'distribution':
            direction = 'SHORT'  # Sell at high
            entry_price = entry_bar['close']
        else:
            continue  # Skip neutral zones

        # Exits
        atr = entry_bar['atr_14']
        if direction == 'LONG':
            stop_loss = entry_price - (sl_atr_mult * atr)
            take_profit = entry_price + (tp_atr_mult * atr)
        else:  # SHORT
            stop_loss = entry_price + (sl_atr_mult * atr)
            take_profit = entry_price - (tp_atr_mult * atr)

        # Simulate trade
        exit_price = None
        exit_reason = None
        for j in range(1, max_hold_bars + 1):
            if entry_idx + j >= len(df):
                break
            bar = df.iloc[entry_idx + j]

            if direction == 'LONG':
                if bar['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    break
                elif bar['high'] >= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    break
            else:  # SHORT
                if bar['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = 'SL'
                    break
                elif bar['low'] <= take_profit:
                    exit_price = take_profit
                    exit_reason = 'TP'
                    break

        if exit_price is None:
            exit_price = df.iloc[entry_idx + j]['close']
            exit_reason = 'TIME'

        # Calculate P&L
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        pnl_pct -= 0.001  # 0.1% fees

        trades.append({
            'timestamp': entry_bar['timestamp'],
            'direction': direction,
            'zone_type': zone['type'],
            'zone_bars': zone['bars'],
            'entry': entry_price,
            'exit': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct * 100
        })

    if len(trades) == 0:
        return None

    tdf = pd.DataFrame(trades)

    # Calculate metrics
    equity = 10000
    equity_curve = [equity]
    for pnl in tdf['pnl_pct']:
        equity *= (1 + pnl / 100)
        equity_curve.append(equity)

    total_return = (equity - 10000) / 100
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (np.array(equity_curve) - running_max) / running_max * 100
    max_dd = drawdown.min()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    win_rate = (tdf['pnl_pct'] > 0).sum() / len(tdf) * 100
    avg_win = tdf[tdf['pnl_pct'] > 0]['pnl_pct'].mean() if (tdf['pnl_pct'] > 0).any() else 0
    avg_loss = tdf[tdf['pnl_pct'] <= 0]['pnl_pct'].mean() if (tdf['pnl_pct'] <= 0).any() else 0

    # Top 20% concentration
    tdf_sorted = tdf.sort_values('pnl_pct', ascending=False)
    top_20_pct_count = max(1, int(len(tdf) * 0.2))
    top_20_pct_pnl = tdf_sorted.head(top_20_pct_count)['pnl_pct'].sum()
    top_20_concentration = (top_20_pct_pnl / tdf['pnl_pct'].sum() * 100) if tdf['pnl_pct'].sum() != 0 else 0

    return {
        'config': config,
        'zones_detected': len(zones),
        'trades': len(tdf),
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'exit_breakdown': tdf['exit_reason'].value_counts().to_dict(),
        'top20_concentration': top_20_concentration,
        'trades_per_day': len(tdf) / 7
    }

# ============================================================================
# TEST CONFIGURATIONS
# ============================================================================

configs = [
    # Config 1: TRUMP-style (overnight, 4:1 R:R)
    {
        'name': 'TRUMP-style (Overnight)',
        'volume_threshold': 1.5,
        'min_zone_bars': 5,
        'session_filter': 'overnight',
        'sl_atr_mult': 1.5,
        'tp_atr_mult': 4.0,  # 2.67:1 R:R
        'max_hold_bars': 90
    },

    # Config 2: DOGE-style (Asia/EU, tight SL)
    {
        'name': 'DOGE-style (Asia/EU)',
        'volume_threshold': 1.5,
        'min_zone_bars': 5,
        'session_filter': 'asia_eu',
        'sl_atr_mult': 1.5,
        'tp_atr_mult': 4.0,
        'max_hold_bars': 90
    },

    # Config 3: PEPE-style (tighter, 2:1 R:R)
    {
        'name': 'PEPE-style (Overnight, tight)',
        'volume_threshold': 1.5,
        'min_zone_bars': 5,
        'session_filter': 'overnight',
        'sl_atr_mult': 1.0,
        'tp_atr_mult': 2.0,  # 2:1 R:R
        'max_hold_bars': 90
    },

    # Config 4: US session (best for PIPPIN per analysis)
    {
        'name': 'US Session Focus',
        'volume_threshold': 1.5,
        'min_zone_bars': 5,
        'session_filter': 'us',
        'sl_atr_mult': 1.5,
        'tp_atr_mult': 3.0,  # 2:1 R:R
        'max_hold_bars': 60
    },

    # Config 5: Relaxed filters (more trades)
    {
        'name': 'Relaxed (Lower threshold)',
        'volume_threshold': 1.3,  # Lower threshold
        'min_zone_bars': 3,       # Shorter zones
        'session_filter': 'all',
        'sl_atr_mult': 1.5,
        'tp_atr_mult': 3.0,
        'max_hold_bars': 90
    }
]

# ============================================================================
# RUN ALL TESTS
# ============================================================================

print("\n" + "=" * 80)
print("TESTING VOLUME ZONES STRATEGIES")
print("=" * 80)

results = []

for config in configs:
    print(f"\n{'='*80}")
    print(f"Testing: {config['name']}")
    print(f"{'='*80}")
    print(f"  Volume threshold: {config['volume_threshold']}x")
    print(f"  Min zone bars: {config['min_zone_bars']}")
    print(f"  Session: {config['session_filter']}")
    print(f"  SL/TP: {config['sl_atr_mult']}x / {config['tp_atr_mult']}x ATR")

    result = test_volume_zones(df, config)

    if result is None:
        print(f"  ⚠️  No trades generated")
        continue

    print(f"\n  Results:")
    print(f"    Zones detected: {result['zones_detected']}")
    print(f"    Trades: {result['trades']} ({result['trades_per_day']:.1f}/day)")
    print(f"    Return: {result['return']:+.2f}%")
    print(f"    Max DD: {result['max_dd']:.2f}%")
    print(f"    Return/DD: {result['return_dd']:.2f}x")
    print(f"    Win Rate: {result['win_rate']:.1f}%")
    print(f"    Avg Win: {result['avg_win']:+.2f}%")
    print(f"    Avg Loss: {result['avg_loss']:.2f}%")
    print(f"    Top 20% concentration: {result['top20_concentration']:.1f}%")
    print(f"    Exit breakdown: {result['exit_breakdown']}")

    results.append(result)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("SUMMARY - VOLUME ZONES RESEARCH")
print("=" * 80)

if len(results) == 0:
    print("\n⚠️  No strategies generated trades")
else:
    # Sort by Return/DD
    results_sorted = sorted(results, key=lambda x: x['return_dd'], reverse=True)

    print(f"\nTested {len(results)} configurations:\n")
    print("| Rank | Strategy | Trades | Return | Max DD | Return/DD | Win Rate | Top20% |")
    print("|------|----------|--------|--------|--------|-----------|----------|--------|")

    for idx, r in enumerate(results_sorted, 1):
        emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "  "
        print(f"| {emoji} {idx} | {r['config']['name']:<25} | {r['trades']:>6} | {r['return']:>+6.2f}% | {r['max_dd']:>6.2f}% | {r['return_dd']:>9.2f}x | {r['win_rate']:>7.1f}% | {r['top20_concentration']:>6.1f}% |")

    print("\n" + "=" * 80)

    # Best strategy analysis
    best = results_sorted[0]
    print(f"\n🏆 BEST STRATEGY: {best['config']['name']}")
    print(f"   Return/DD: {best['return_dd']:.2f}x")
    print(f"   Return: {best['return']:+.2f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Trades: {best['trades']} ({best['trades_per_day']:.1f}/day)")
    print(f"   Top 20% concentration: {best['top20_concentration']:.1f}%")

    if best['return_dd'] >= 5.0:
        print(f"\n   ✅ EXCELLENT - Return/DD > 5.0x")
        print(f"   Comparable to TRUMP (10.56x) and DOGE (10.75x)")
        print(f"   Recommendation: Deploy to paper trading")
    elif best['return_dd'] >= 3.0:
        print(f"\n   ✅ VIABLE - Return/DD > 3.0x")
        print(f"   Recommendation: Test on 30-day data for validation")
    elif best['return_dd'] >= 2.0:
        print(f"\n   ⚠️  MARGINAL - Return/DD 2-3x")
        print(f"   Recommendation: Optimize filters or abandon")
    else:
        print(f"\n   ❌ NOT VIABLE - Return/DD < 2.0x")
        print(f"   Recommendation: Volume zones don't work on PIPPIN")

    # Outlier dependency check
    if best['top20_concentration'] > 80:
        print(f"\n   ⚠️  OUTLIER DEPENDENT (Top 20% = {best['top20_concentration']:.1f}% of profit)")
        print(f"   Like TRUMP (88.6%) - MUST take ALL signals")

print("\n" + "=" * 80)
print("Volume Zones Research Complete!")
print("=" * 80)
