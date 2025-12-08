#!/usr/bin/env python3
"""
PENGU Chart Pattern Analysis - Reversal Trading

Hypothesis: Since PENGU is 91.76% choppy and mean-reverting, generic indicators fail.
But specific chart patterns (double bottoms/tops, V-reversals, failed breakouts)
might capture the reversals more reliably.

Patterns to test:
1. Double Bottom (W pattern) - bullish reversal
2. Double Top (M pattern) - bearish reversal
3. V-Bottom - sharp exhaustion reversal up
4. V-Top - sharp exhaustion reversal down
5. Failed Breakout - fakeout above resistance, then dump
6. Failed Breakdown - fakeout below support, then pump
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load PENGU data
print("Loading PENGU data...")
df = pd.read_csv('pengu_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Calculate indicators
df['range'] = df['high'] - df['low']
df['atr'] = df['range'].rolling(14).mean()
df['body'] = df['close'] - df['open']
df['body_pct'] = (df['close'] - df['open']) / df['open'] * 100

# Support/Resistance levels (local highs/lows)
df['local_high'] = df['high'].rolling(20, center=True).max() == df['high']
df['local_low'] = df['low'].rolling(20, center=True).min() == df['low']

# Forward returns
for i in [1, 5, 10, 20]:
    df[f'fwd_{i}'] = df['close'].shift(-i) / df['close'] - 1

print(f"Total candles: {len(df)}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print()

# ============================================================================
# PATTERN 1: DOUBLE BOTTOM (W pattern)
# ============================================================================
print("=" * 80)
print("PATTERN 1: DOUBLE BOTTOM (Bullish Reversal)")
print("=" * 80)

double_bottoms = []

# Look for two local lows within 20-50 bars, similar price, then bounce
for i in range(50, len(df) - 20):
    # Find two local lows in past 50 bars
    recent_lows = df.iloc[i-50:i][df['local_low'] == True]

    if len(recent_lows) >= 2:
        # Get last two lows
        low1_idx = recent_lows.index[-2]
        low2_idx = recent_lows.index[-1]

        low1_price = df.loc[low1_idx, 'low']
        low2_price = df.loc[low2_idx, 'low']

        # Check if lows are within 0.3% of each other (similar price)
        price_diff_pct = abs(low2_price - low1_price) / low1_price * 100

        if price_diff_pct < 0.3:
            # Check if there was a bounce between the two lows (middle peak)
            between_bars = df.loc[low1_idx:low2_idx]
            middle_high = between_bars['high'].max()
            avg_low = (low1_price + low2_price) / 2

            bounce_pct = (middle_high - avg_low) / avg_low * 100

            # Valid W pattern if middle bounce > 0.5%
            if bounce_pct > 0.5:
                # Entry: breakout above middle high
                entry_price = middle_high
                current_price = df.loc[i, 'close']

                # Only enter if we're breaking above middle high
                if current_price > entry_price:
                    double_bottoms.append({
                        'idx': i,
                        'entry': entry_price,
                        'low1': low1_price,
                        'low2': low2_price,
                        'middle_high': middle_high,
                        'bounce_pct': bounce_pct
                    })

print(f"Double bottom patterns found: {len(double_bottoms)}")

if len(double_bottoms) > 0:
    # Analyze forward returns
    db_df = pd.DataFrame(double_bottoms)
    for col in ['fwd_1', 'fwd_5', 'fwd_10', 'fwd_20']:
        db_df[col] = db_df['idx'].apply(lambda idx: df.loc[idx, col] if idx in df.index else np.nan)

    print(f"Avg bounce size: {db_df['bounce_pct'].mean():.2f}%")
    print()
    print("Forward returns after double bottom breakout:")
    for i in [1, 5, 10, 20]:
        fwd_ret = db_df[f'fwd_{i}'].mean() * 100
        win_rate = (db_df[f'fwd_{i}'] > 0).mean() * 100
        print(f"  +{i} bars: {fwd_ret:+.3f}% (WR: {win_rate:.1f}%)")
    print()

# ============================================================================
# PATTERN 2: DOUBLE TOP (M pattern)
# ============================================================================
print("=" * 80)
print("PATTERN 2: DOUBLE TOP (Bearish Reversal)")
print("=" * 80)

double_tops = []

for i in range(50, len(df) - 20):
    # Find two local highs in past 50 bars
    recent_highs = df.iloc[i-50:i][df['local_high'] == True]

    if len(recent_highs) >= 2:
        high1_idx = recent_highs.index[-2]
        high2_idx = recent_highs.index[-1]

        high1_price = df.loc[high1_idx, 'high']
        high2_price = df.loc[high2_idx, 'high']

        # Check if highs are within 0.3% of each other
        price_diff_pct = abs(high2_price - high1_price) / high1_price * 100

        if price_diff_pct < 0.3:
            # Check for middle dip
            between_bars = df.loc[high1_idx:high2_idx]
            middle_low = between_bars['low'].min()
            avg_high = (high1_price + high2_price) / 2

            dip_pct = (avg_high - middle_low) / avg_high * 100

            # Valid M pattern if middle dip > 0.5%
            if dip_pct > 0.5:
                # Entry: breakdown below middle low
                entry_price = middle_low
                current_price = df.loc[i, 'close']

                if current_price < entry_price:
                    double_tops.append({
                        'idx': i,
                        'entry': entry_price,
                        'high1': high1_price,
                        'high2': high2_price,
                        'middle_low': middle_low,
                        'dip_pct': dip_pct
                    })

print(f"Double top patterns found: {len(double_tops)}")

if len(double_tops) > 0:
    dt_df = pd.DataFrame(double_tops)
    for col in ['fwd_1', 'fwd_5', 'fwd_10', 'fwd_20']:
        dt_df[col] = dt_df['idx'].apply(lambda idx: df.loc[idx, col] if idx in df.index else np.nan)

    print(f"Avg dip size: {dt_df['dip_pct'].mean():.2f}%")
    print()
    print("Forward returns after double top breakdown (negative = short profit):")
    for i in [1, 5, 10, 20]:
        fwd_ret = dt_df[f'fwd_{i}'].mean() * 100
        win_rate = (dt_df[f'fwd_{i}'] < 0).mean() * 100  # Negative = short profit
        print(f"  +{i} bars: {fwd_ret:+.3f}% (Short WR: {win_rate:.1f}%)")
    print()

# ============================================================================
# PATTERN 3: V-BOTTOM (Sharp Exhaustion Reversal Up)
# ============================================================================
print("=" * 80)
print("PATTERN 3: V-BOTTOM (Sharp Down + Sharp Up)")
print("=" * 80)

# V-bottom: 3+ consecutive down bars (>0.3% each), then 2+ up bars (>0.3% each)
v_bottoms = []

for i in range(10, len(df) - 5):
    # Check for 3+ down bars
    down_bars = 0
    for j in range(1, 6):  # Look back up to 5 bars
        if df.loc[i-j, 'body_pct'] < -0.3:
            down_bars += 1
        else:
            break

    if down_bars >= 3:
        # Now check for reversal (2+ up bars)
        up_bars = 0
        for j in range(0, 3):
            if i+j < len(df) and df.loc[i+j, 'body_pct'] > 0.3:
                up_bars += 1
            else:
                break

        if up_bars >= 2:
            v_bottoms.append({
                'idx': i,
                'down_bars': down_bars,
                'up_bars': up_bars,
                'entry': df.loc[i, 'close']
            })

print(f"V-bottom patterns found: {len(v_bottoms)}")

if len(v_bottoms) > 0:
    vb_df = pd.DataFrame(v_bottoms)
    for col in ['fwd_1', 'fwd_5', 'fwd_10', 'fwd_20']:
        vb_df[col] = vb_df['idx'].apply(lambda idx: df.loc[idx, col] if idx in df.index else np.nan)

    print(f"Avg down bars: {vb_df['down_bars'].mean():.1f}")
    print(f"Avg up bars: {vb_df['up_bars'].mean():.1f}")
    print()
    print("Forward returns after V-bottom:")
    for i in [1, 5, 10, 20]:
        fwd_ret = vb_df[f'fwd_{i}'].mean() * 100
        win_rate = (vb_df[f'fwd_{i}'] > 0).mean() * 100
        print(f"  +{i} bars: {fwd_ret:+.3f}% (WR: {win_rate:.1f}%)")
    print()

# ============================================================================
# PATTERN 4: V-TOP (Sharp Up + Sharp Down)
# ============================================================================
print("=" * 80)
print("PATTERN 4: V-TOP (Sharp Up + Sharp Down)")
print("=" * 80)

v_tops = []

for i in range(10, len(df) - 5):
    # Check for 3+ up bars
    up_bars = 0
    for j in range(1, 6):
        if df.loc[i-j, 'body_pct'] > 0.3:
            up_bars += 1
        else:
            break

    if up_bars >= 3:
        # Check for reversal (2+ down bars)
        down_bars = 0
        for j in range(0, 3):
            if i+j < len(df) and df.loc[i+j, 'body_pct'] < -0.3:
                down_bars += 1
            else:
                break

        if down_bars >= 2:
            v_tops.append({
                'idx': i,
                'up_bars': up_bars,
                'down_bars': down_bars,
                'entry': df.loc[i, 'close']
            })

print(f"V-top patterns found: {len(v_tops)}")

if len(v_tops) > 0:
    vt_df = pd.DataFrame(v_tops)
    for col in ['fwd_1', 'fwd_5', 'fwd_10', 'fwd_20']:
        vt_df[col] = vt_df['idx'].apply(lambda idx: df.loc[idx, col] if idx in df.index else np.nan)

    print(f"Avg up bars: {vt_df['up_bars'].mean():.1f}")
    print(f"Avg down bars: {vt_df['down_bars'].mean():.1f}")
    print()
    print("Forward returns after V-top (negative = short profit):")
    for i in [1, 5, 10, 20]:
        fwd_ret = vt_df[f'fwd_{i}'].mean() * 100
        win_rate = (vt_df[f'fwd_{i}'] < 0).mean() * 100
        print(f"  +{i} bars: {fwd_ret:+.3f}% (Short WR: {win_rate:.1f}%)")
    print()

# ============================================================================
# COMPARISON AND BEST PATTERN
# ============================================================================
print("=" * 80)
print("PATTERN COMPARISON")
print("=" * 80)

results = []

if len(double_bottoms) > 0:
    results.append({
        'pattern': 'Double Bottom (Long)',
        'count': len(double_bottoms),
        'avg_fwd_10': db_df['fwd_10'].mean() * 100,
        'win_rate_10': (db_df['fwd_10'] > 0).mean() * 100
    })

if len(double_tops) > 0:
    results.append({
        'pattern': 'Double Top (Short)',
        'count': len(double_tops),
        'avg_fwd_10': -dt_df['fwd_10'].mean() * 100,  # Invert for short
        'win_rate_10': (dt_df['fwd_10'] < 0).mean() * 100
    })

if len(v_bottoms) > 0:
    results.append({
        'pattern': 'V-Bottom (Long)',
        'count': len(v_bottoms),
        'avg_fwd_10': vb_df['fwd_10'].mean() * 100,
        'win_rate_10': (vb_df['fwd_10'] > 0).mean() * 100
    })

if len(v_tops) > 0:
    results.append({
        'pattern': 'V-Top (Short)',
        'count': len(v_tops),
        'avg_fwd_10': -vt_df['fwd_10'].mean() * 100,  # Invert for short
        'win_rate_10': (vt_df['fwd_10'] < 0).mean() * 100
    })

if results:
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    print()

    best = results_df.loc[results_df['avg_fwd_10'].idxmax()]
    print(f"✅ BEST PATTERN: {best['pattern']}")
    print(f"   Occurrences: {int(best['count'])}")
    print(f"   Avg 10-bar return: {best['avg_fwd_10']:.3f}%")
    print(f"   Win rate: {best['win_rate_10']:.1f}%")
    print()

    # Backtest the best pattern
    print("=" * 80)
    print(f"BACKTESTING: {best['pattern']}")
    print("=" * 80)

    # Determine which pattern to backtest
    if 'Double Bottom' in best['pattern']:
        pattern_data = db_df
        direction = 'LONG'
    elif 'Double Top' in best['pattern']:
        pattern_data = dt_df
        direction = 'SHORT'
    elif 'V-Bottom' in best['pattern']:
        pattern_data = vb_df
        direction = 'LONG'
    else:  # V-Top
        pattern_data = vt_df
        direction = 'SHORT'

    # Backtest with stops/targets
    trades = []
    for idx, row in pattern_data.iterrows():
        i = row['idx']
        if i not in df.index or pd.isna(df.loc[i, 'atr']):
            continue

        entry_price = row['entry']
        atr = df.loc[i, 'atr']

        if direction == 'LONG':
            stop_loss = entry_price - (1.5 * atr)
            take_profit = entry_price + (3.0 * atr)

            # Check next 20 bars for SL/TP
            for j in range(1, 21):
                if i + j >= len(df):
                    break
                candle = df.iloc[i + j]

                if candle['low'] <= stop_loss:
                    pnl = (stop_loss / entry_price - 1) - 0.001
                    trades.append({'direction': direction, 'pnl': pnl, 'bars': j, 'exit': 'SL'})
                    break
                elif candle['high'] >= take_profit:
                    pnl = (take_profit / entry_price - 1) - 0.001
                    trades.append({'direction': direction, 'pnl': pnl, 'bars': j, 'exit': 'TP'})
                    break
            else:
                exit_price = df.iloc[i + 20]['close'] if i + 20 < len(df) else entry_price
                pnl = (exit_price / entry_price - 1) - 0.001
                trades.append({'direction': direction, 'pnl': pnl, 'bars': 20, 'exit': 'TIME'})

        else:  # SHORT
            stop_loss = entry_price + (1.5 * atr)
            take_profit = entry_price - (3.0 * atr)

            for j in range(1, 21):
                if i + j >= len(df):
                    break
                candle = df.iloc[i + j]

                if candle['high'] >= stop_loss:
                    pnl = (entry_price / stop_loss - 1) - 0.001
                    trades.append({'direction': direction, 'pnl': pnl, 'bars': j, 'exit': 'SL'})
                    break
                elif candle['low'] <= take_profit:
                    pnl = (entry_price / take_profit - 1) - 0.001
                    trades.append({'direction': direction, 'pnl': pnl, 'bars': j, 'exit': 'TP'})
                    break
            else:
                exit_price = df.iloc[i + 20]['close'] if i + 20 < len(df) else entry_price
                pnl = (entry_price / exit_price - 1) - 0.001
                trades.append({'direction': direction, 'pnl': pnl, 'bars': 20, 'exit': 'TIME'})

    trades_df = pd.DataFrame(trades)

    if len(trades_df) > 0:
        total_return = trades_df['pnl'].sum() * 100
        avg_trade = trades_df['pnl'].mean() * 100
        win_rate = (trades_df['pnl'] > 0).mean() * 100
        avg_winner = trades_df[trades_df['pnl'] > 0]['pnl'].mean() * 100 if (trades_df['pnl'] > 0).any() else 0
        avg_loser = trades_df[trades_df['pnl'] < 0]['pnl'].mean() * 100 if (trades_df['pnl'] < 0).any() else 0

        print(f"Total trades: {len(trades_df)}")
        print(f"Total return: {total_return:+.2f}%")
        print(f"Avg trade: {avg_trade:+.3f}%")
        print(f"Win rate: {win_rate:.1f}%")
        print(f"Avg winner: {avg_winner:+.3f}%")
        print(f"Avg loser: {avg_loser:+.3f}%")
        print()

        print("Exit reasons:")
        print(trades_df['exit'].value_counts())
        print()

        # Save results
        trades_df.to_csv('results/PENGU_chart_pattern_trades.csv', index=False)
        print("✅ Trades saved to: results/PENGU_chart_pattern_trades.csv")
    else:
        print("❌ No trades generated")
else:
    print("❌ No patterns found")

print()
print("=" * 80)
print("CONCLUSION")
print("=" * 80)
print("Chart patterns test if PENGU's chop can be exploited through:")
print("  - W/M patterns (double bottoms/tops)")
print("  - V-reversals (exhaustion moves)")
print("If these show positive returns, it validates that PENGU needs")
print("specific pattern recognition, not generic indicators.")
