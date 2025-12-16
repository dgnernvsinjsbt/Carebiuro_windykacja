#!/usr/bin/env python3
"""
Optimize TRUMPSOL filters based on winner/loser analysis
Focus: EMA distance, Volume ratio, Body %
"""

import pandas as pd
import numpy as np

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest(df, params):
    df = df.copy()

    # Calculate indicators
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
    df['atr_ma'] = df['atr'].rolling(20).mean()
    df['atr_ratio'] = df['atr'] / df['atr_ma']
    df['ema20'] = calculate_ema(df['close'], 20)
    df['distance'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)
    df['bullish'] = df['close'] > df['open']
    df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

    # Volume
    df['volume_ma'] = df['volume'].rolling(30).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']

    # Daily RSI
    df_daily = df.set_index('timestamp').resample('1D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    df_daily['rsi_daily'] = calculate_rsi(df_daily['close'], 14)

    df = df.set_index('timestamp')
    df = df.join(df_daily[['rsi_daily']], how='left')
    df = df.ffill()
    df = df.reset_index()

    # Generate signals with filters
    signals = []
    for i in range(len(df)):
        row = df.iloc[i]

        # Base conditions
        if not (row['atr_ratio'] > params['atr_mult'] and
                row['bullish'] and
                not pd.isna(row['rsi_daily']) and
                row['rsi_daily'] > 50):
            continue

        # NEW FILTERS
        if row['distance'] >= params['ema_dist']:
            continue

        if params.get('volume_min') and row['volume_ratio'] < params['volume_min']:
            continue

        if params.get('body_max') and row['body_pct'] > params['body_max']:
            continue

        signals.append(i)

    if len(signals) == 0:
        return None

    # Backtest
    trades = []

    for signal_idx in signals:
        if signal_idx >= len(df) - 1:
            continue

        signal_price = df['close'].iloc[signal_idx]
        signal_atr = df['atr'].iloc[signal_idx]

        if pd.isna(signal_atr) or signal_atr == 0:
            continue

        limit_price = signal_price * (1 + params['limit_offset'] / 100)

        filled = False
        fill_idx = None

        for i in range(signal_idx + 1, min(signal_idx + 4, len(df))):
            if df['high'].iloc[i] >= limit_price:
                filled = True
                fill_idx = i
                break

        if not filled:
            continue

        entry_price = limit_price
        entry_atr = df['atr'].iloc[fill_idx]

        sl_price = entry_price - (params['sl_mult'] * entry_atr)
        tp_price = entry_price + (params['tp_mult'] * entry_atr)

        exit_idx = None
        exit_price = None
        exit_reason = None

        for i in range(fill_idx + 1, min(fill_idx + 200, len(df))):
            if df['low'].iloc[i] <= sl_price:
                exit_idx = i
                exit_price = sl_price
                exit_reason = 'SL'
                break
            if df['high'].iloc[i] >= tp_price:
                exit_idx = i
                exit_price = tp_price
                exit_reason = 'TP'
                break

        if exit_idx is None:
            exit_idx = min(fill_idx + 199, len(df) - 1)
            exit_price = df['close'].iloc[exit_idx]
            exit_reason = 'TIME'

        pnl_pct = (exit_price - entry_price) / entry_price * 100 - 0.10

        trades.append({
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

    if len(trades) == 0:
        return None

    # Calculate metrics
    df_t = pd.DataFrame(trades)
    df_t['cum'] = df_t['pnl_pct'].cumsum()
    equity = 100 + df_t['cum']
    dd = ((equity - equity.cummax()) / equity.cummax() * 100).min()
    total_return = df_t['pnl_pct'].sum()
    rdd = total_return / abs(dd) if dd != 0 else 0
    wr = (df_t['pnl_pct'] > 0).mean() * 100
    tp_rate = (df_t['exit_reason'] == 'TP').sum() / len(df_t) * 100

    return {
        'trades': len(trades),
        'signals': len(signals),
        'return': total_return,
        'dd': dd,
        'rdd': rdd,
        'wr': wr,
        'tp_rate': tp_rate,
        **params
    }

# Load data
df = pd.read_csv('trumpsol_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("TRUMPSOL FILTER OPTIMIZATION")
print("=" * 80)

# Baseline config
base_params = {
    'atr_mult': 1.5,
    'ema_dist': 2.0,  # Baseline
    'tp_mult': 8.0,
    'sl_mult': 1.5,
    'limit_offset': 0.5
}

baseline = backtest(df, base_params)

print(f"\nBASELINE (no additional filters):")
print(f"  Trades: {baseline['trades']}, Return: {baseline['return']:+.2f}%, DD: {baseline['dd']:.2f}%, R/DD: {baseline['rdd']:.2f}x")

results = []

# Test EMA distance (winners at 0.73%, losers at 1.15%)
print(f"\n" + "-" * 80)
print("FILTER 1: EMA Distance (tighter)")
print("-" * 80)

for ema_dist in [1.5, 1.2, 1.0, 0.8]:
    params = base_params.copy()
    params['ema_dist'] = ema_dist
    result = backtest(df, params)
    if result and result['trades'] >= 15:
        results.append(result)
        improvement = (result['rdd'] - baseline['rdd']) / baseline['rdd'] * 100
        print(f"  EMA < {ema_dist}% → {result['trades']} trades, {result['rdd']:.2f}x R/DD ({improvement:+.1f}%)")

# Test Volume ratio (winners at 1.80x, losers at 1.19x)
print(f"\n" + "-" * 80)
print("FILTER 2: Volume Ratio (higher)")
print("-" * 80)

for vol_min in [1.0, 1.2, 1.4, 1.6]:
    params = base_params.copy()
    params['volume_min'] = vol_min
    result = backtest(df, params)
    if result and result['trades'] >= 15:
        results.append(result)
        improvement = (result['rdd'] - baseline['rdd']) / baseline['rdd'] * 100
        print(f"  Vol >= {vol_min}x → {result['trades']} trades, {result['rdd']:.2f}x R/DD ({improvement:+.1f}%)")

# Test Body % (winners at 0.28%, losers at 0.49%)
print(f"\n" + "-" * 80)
print("FILTER 3: Body % (smaller candles)")
print("-" * 80)

for body_max in [0.5, 0.4, 0.35, 0.3]:
    params = base_params.copy()
    params['body_max'] = body_max
    result = backtest(df, params)
    if result and result['trades'] >= 15:
        results.append(result)
        improvement = (result['rdd'] - baseline['rdd']) / baseline['rdd'] * 100
        print(f"  Body < {body_max}% → {result['trades']} trades, {result['rdd']:.2f}x R/DD ({improvement:+.1f}%)")

# Test combinations
print(f"\n" + "-" * 80)
print("FILTER COMBINATIONS (Best Single Filters)")
print("-" * 80)

best_results = sorted([r for r in results if r['trades'] >= 15], key=lambda x: x['rdd'], reverse=True)[:3]

combo_results = []

# Test top 3 single filters combined
for i, r1 in enumerate(best_results):
    for r2 in best_results[i+1:]:
        params = base_params.copy()

        # Combine filters
        if r1.get('ema_dist') and r1['ema_dist'] < base_params['ema_dist']:
            params['ema_dist'] = r1['ema_dist']
        if r2.get('ema_dist') and r2['ema_dist'] < base_params['ema_dist']:
            params['ema_dist'] = r2['ema_dist']

        if r1.get('volume_min'):
            params['volume_min'] = r1['volume_min']
        if r2.get('volume_min'):
            params['volume_min'] = r2['volume_min']

        if r1.get('body_max'):
            params['body_max'] = r1['body_max']
        if r2.get('body_max'):
            params['body_max'] = r2['body_max']

        result = backtest(df, params)
        if result and result['trades'] >= 15:
            combo_results.append(result)

# Also test all 3 together
print("\nTesting combinations of best individual filters...")

# Try EMA + Volume
for ema in [1.5, 1.2, 1.0]:
    for vol in [1.2, 1.4]:
        params = base_params.copy()
        params['ema_dist'] = ema
        params['volume_min'] = vol
        result = backtest(df, params)
        if result and result['trades'] >= 15:
            combo_results.append(result)
            print(f"  EMA<{ema}% + Vol>={vol}x → {result['trades']} trades, {result['rdd']:.2f}x R/DD")

# Try EMA + Body
for ema in [1.5, 1.2, 1.0]:
    for body in [0.4, 0.35]:
        params = base_params.copy()
        params['ema_dist'] = ema
        params['body_max'] = body
        result = backtest(df, params)
        if result and result['trades'] >= 15:
            combo_results.append(result)
            print(f"  EMA<{ema}% + Body<{body}% → {result['trades']} trades, {result['rdd']:.2f}x R/DD")

# Try Volume + Body
for vol in [1.2, 1.4]:
    for body in [0.4, 0.35]:
        params = base_params.copy()
        params['volume_min'] = vol
        params['body_max'] = body
        result = backtest(df, params)
        if result and result['trades'] >= 15:
            combo_results.append(result)
            print(f"  Vol>={vol}x + Body<{body}% → {result['trades']} trades, {result['rdd']:.2f}x R/DD")

# Try all 3
for ema in [1.5, 1.2, 1.0]:
    for vol in [1.2, 1.4]:
        for body in [0.4, 0.35]:
            params = base_params.copy()
            params['ema_dist'] = ema
            params['volume_min'] = vol
            params['body_max'] = body
            result = backtest(df, params)
            if result and result['trades'] >= 15:
                combo_results.append(result)

# Final results
all_results = results + combo_results
all_results = sorted([r for r in all_results if r['trades'] >= 15], key=lambda x: x['rdd'], reverse=True)

print(f"\n" + "=" * 80)
print("TOP 10 CONFIGURATIONS")
print("=" * 80)

print(f"\n{'Rank':<6} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'TP%':<8} {'Filters'}")
print("-" * 100)

for i, result in enumerate(all_results[:10], 1):
    filters = []
    if result['ema_dist'] < base_params['ema_dist']:
        filters.append(f"EMA<{result['ema_dist']}%")
    if result.get('volume_min'):
        filters.append(f"Vol>={result['volume_min']}x")
    if result.get('body_max'):
        filters.append(f"Body<{result['body_max']}%")

    filter_str = ", ".join(filters) if filters else "None"
    improvement = (result['rdd'] - baseline['rdd']) / baseline['rdd'] * 100

    marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "

    print(f"{marker} {i:<4} {result['trades']:<8} {result['return']:+9.1f}% {result['dd']:9.2f}% {result['rdd']:7.2f}x {result['wr']:7.1f}% {result['tp_rate']:7.1f}% {filter_str}")

# Show best config
best = all_results[0]

print(f"\n" + "=" * 80)
print("BEST CONFIGURATION")
print("=" * 80)

improvement = (best['rdd'] - baseline['rdd']) / baseline['rdd'] * 100

print(f"\nFilters Applied:")
if best['ema_dist'] < base_params['ema_dist']:
    print(f"  ✓ EMA Distance: < {best['ema_dist']}% (was < {base_params['ema_dist']}%)")
if best.get('volume_min'):
    print(f"  ✓ Volume Ratio: >= {best['volume_min']}x (was no filter)")
if best.get('body_max'):
    print(f"  ✓ Body %: < {best['body_max']}% (was no filter)")

print(f"\nPerformance:")
print(f"  Trades: {best['trades']} (from {best['signals']} signals, {best['trades']/best['signals']*100:.1f}% fill)")
print(f"  Return: {best['return']:+.2f}%")
print(f"  Max DD: {best['dd']:.2f}%")
print(f"  R/DD: {best['rdd']:.2f}x (was {baseline['rdd']:.2f}x, {improvement:+.1f}% improvement)")
print(f"  Win Rate: {best['wr']:.1f}%")
print(f"  TP Rate: {best['tp_rate']:.1f}%")

print(f"\n" + "=" * 80)
print("FINAL RANKING vs OTHER COINS")
print("=" * 80)

comparison = [
    {'coin': 'FARTCOIN', 'rdd': 26.21, 'return': 98.8, 'dd': -3.77, 'trades': 28},
    {'coin': 'MOODENG', 'rdd': 13.34, 'return': 73.8, 'dd': -5.53, 'trades': 26},
    {'coin': 'TRUMPSOL (filtered)', 'rdd': best['rdd'], 'return': best['return'], 'dd': best['dd'], 'trades': best['trades']}
]

df_comp = pd.DataFrame(comparison).sort_values('rdd', ascending=False)

print(f"\n{'Rank':<6} {'Coin':<22} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'Status'}")
print("-" * 75)

for i, (_, row) in enumerate(df_comp.iterrows(), 1):
    marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
    status = "✅" if row['rdd'] >= 10 else "⚠️" if row['rdd'] >= 5 else "❌"
    print(f"{marker} {i:<4} {row['coin']:<22} {row['trades']:<8.0f} {row['return']:+9.1f}% {row['dd']:9.2f}% {row['rdd']:7.2f}x {status}")

if best['rdd'] >= 10:
    print(f"\n✅ TRUMPSOL NOW VIABLE - Add to bot!")
elif best['rdd'] >= 5:
    print(f"\n⚠️ TRUMPSOL IMPROVED but still marginal (target: 10x+)")
else:
    print(f"\n❌ TRUMPSOL still below 5x threshold")

print("=" * 80)
