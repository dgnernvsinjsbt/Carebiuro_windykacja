#!/usr/bin/env python3
"""
Test logical filters for TRUMPSOL
Focus: Volume confirmation + ATR strength + other real edges
Target: 20+ trades, 5+ R/DD
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
    df['above_ema'] = df['close'] > df['ema20']

    # Volume
    df['volume_ma'] = df['volume'].rolling(30).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']

    # Consecutive ATR expansion bars
    df['atr_expanded'] = df['atr_ratio'] > params['atr_mult']
    df['consecutive_expansion'] = 0
    count = 0
    for i in range(len(df)):
        if df['atr_expanded'].iloc[i]:
            count += 1
        else:
            count = 0
        df.loc[df.index[i], 'consecutive_expansion'] = count

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
                row['distance'] < params['ema_dist'] and
                row['bullish'] and
                not pd.isna(row['rsi_daily']) and
                row['rsi_daily'] > 50):
            continue

        # Volume filter
        if params.get('volume_min') and row['volume_ratio'] < params['volume_min']:
            continue

        # Trend filter - only LONG when above EMA
        if params.get('trend_filter') and not row['above_ema']:
            continue

        # Consecutive expansion filter
        if params.get('consecutive_min') and row['consecutive_expansion'] < params['consecutive_min']:
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
print("TRUMPSOL LOGICAL FILTER OPTIMIZATION")
print("=" * 80)
print("Target: 20+ trades, 5+ R/DD")
print("Focus: Volume confirmation + ATR strength + trend alignment")

base_params = {
    'ema_dist': 2.0,
    'tp_mult': 8.0,
    'sl_mult': 1.5,
    'limit_offset': 0.5
}

results = []

# Test 1: ATR threshold (stronger = higher quality signals)
print(f"\n" + "-" * 80)
print("TEST 1: ATR Expansion Threshold (higher = stronger breakouts)")
print("-" * 80)

for atr in [1.5, 1.6, 1.7, 1.8, 2.0]:
    params = base_params.copy()
    params['atr_mult'] = atr
    result = backtest(df, params)
    if result and result['trades'] >= 15:
        results.append(result)
        print(f"  ATR > {atr}x → {result['trades']} trades, {result['return']:+.1f}%, DD {result['dd']:.2f}%, R/DD {result['rdd']:.2f}x, WR {result['wr']:.1f}%")

# Test 2: Volume confirmation (higher volume = stronger conviction)
print(f"\n" + "-" * 80)
print("TEST 2: Volume Confirmation (volume > average)")
print("-" * 80)

for vol in [1.0, 1.1, 1.2, 1.3, 1.4, 1.5]:
    params = base_params.copy()
    params['atr_mult'] = 1.5
    params['volume_min'] = vol
    result = backtest(df, params)
    if result and result['trades'] >= 15:
        results.append(result)
        print(f"  ATR 1.5x + Vol >= {vol}x → {result['trades']} trades, {result['return']:+.1f}%, DD {result['dd']:.2f}%, R/DD {result['rdd']:.2f}x, WR {result['wr']:.1f}%")

# Test 3: Trend filter (only LONG when above EMA = trend alignment)
print(f"\n" + "-" * 80)
print("TEST 3: Trend Alignment (only LONG above EMA20)")
print("-" * 80)

params = base_params.copy()
params['atr_mult'] = 1.5
params['trend_filter'] = True
result = backtest(df, params)
if result:
    results.append(result)
    print(f"  ATR 1.5x + Trend Filter → {result['trades']} trades, {result['return']:+.1f}%, DD {result['dd']:.2f}%, R/DD {result['rdd']:.2f}x, WR {result['wr']:.1f}%")

# Test 4: Consecutive expansion (2+ bars = confirmed move)
print(f"\n" + "-" * 80)
print("TEST 4: Consecutive ATR Expansion (confirmed breakout)")
print("-" * 80)

for consec in [2, 3]:
    params = base_params.copy()
    params['atr_mult'] = 1.5
    params['consecutive_min'] = consec
    result = backtest(df, params)
    if result and result['trades'] >= 15:
        results.append(result)
        print(f"  ATR 1.5x + {consec}+ consecutive bars → {result['trades']} trades, {result['return']:+.1f}%, DD {result['dd']:.2f}%, R/DD {result['rdd']:.2f}x, WR {result['wr']:.1f}%")

# Test 5: Combinations
print(f"\n" + "-" * 80)
print("TEST 5: COMBINATIONS (ATR + Volume)")
print("-" * 80)

for atr in [1.5, 1.6, 1.7, 1.8]:
    for vol in [1.1, 1.2, 1.3]:
        params = base_params.copy()
        params['atr_mult'] = atr
        params['volume_min'] = vol
        result = backtest(df, params)
        if result and result['trades'] >= 20:
            results.append(result)
            print(f"  ATR > {atr}x + Vol >= {vol}x → {result['trades']} trades, {result['rdd']:.2f}x R/DD, WR {result['wr']:.1f}%")

# Test 6: Triple combo (ATR + Volume + Trend)
print(f"\n" + "-" * 80)
print("TEST 6: TRIPLE COMBO (ATR + Volume + Trend)")
print("-" * 80)

for atr in [1.5, 1.6]:
    for vol in [1.1, 1.2]:
        params = base_params.copy()
        params['atr_mult'] = atr
        params['volume_min'] = vol
        params['trend_filter'] = True
        result = backtest(df, params)
        if result and result['trades'] >= 15:
            results.append(result)
            print(f"  ATR > {atr}x + Vol >= {vol}x + Trend → {result['trades']} trades, {result['rdd']:.2f}x R/DD, WR {result['wr']:.1f}%")

# Sort results by R/DD
results = sorted([r for r in results if r['trades'] >= 20], key=lambda x: x['rdd'], reverse=True)

print(f"\n" + "=" * 80)
print(f"TOP CONFIGURATIONS (20+ trades)")
print("=" * 80)

if results:
    print(f"\n{'Rank':<6} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'TP%':<8} {'Configuration'}")
    print("-" * 100)

    for i, result in enumerate(results[:15], 1):
        filters = []
        filters.append(f"ATR>{result['atr_mult']}x")
        if result.get('volume_min'):
            filters.append(f"Vol>={result['volume_min']}x")
        if result.get('trend_filter'):
            filters.append("Trend")
        if result.get('consecutive_min'):
            filters.append(f"Consec>={result['consecutive_min']}")

        config_str = ", ".join(filters)
        marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        status = "✅" if result['rdd'] >= 5 else ""

        print(f"{marker} {i:<4} {result['trades']:<8} {result['return']:+9.1f}% {result['dd']:9.2f}% {result['rdd']:7.2f}x {result['wr']:7.1f}% {result['tp_rate']:7.1f}% {config_str} {status}")

    # Show best config
    best = results[0]

    print(f"\n" + "=" * 80)
    print("BEST CONFIGURATION")
    print("=" * 80)

    print(f"\nFilters:")
    print(f"  ✓ ATR expansion: > {best['atr_mult']}x")
    if best.get('volume_min'):
        print(f"  ✓ Volume: >= {best['volume_min']}x average")
    if best.get('trend_filter'):
        print(f"  ✓ Trend: Price > EMA20 (LONG only)")
    if best.get('consecutive_min'):
        print(f"  ✓ Consecutive: {best['consecutive_min']}+ bars ATR expansion")
    print(f"  ✓ Daily RSI: > 50 (baseline)")

    print(f"\nPerformance:")
    print(f"  Trades: {best['trades']} (from {best['signals']} signals, {best['trades']/best['signals']*100:.1f}% fill)")
    print(f"  Return: {best['return']:+.2f}%")
    print(f"  Max DD: {best['dd']:.2f}%")
    print(f"  R/DD: {best['rdd']:.2f}x")
    print(f"  Win Rate: {best['wr']:.1f}%")
    print(f"  TP Rate: {best['tp_rate']:.1f}%")

    print(f"\n" + "=" * 80)
    print("FINAL RANKING vs OTHER COINS")
    print("=" * 80)

    comparison = [
        {'coin': 'FARTCOIN', 'rdd': 26.21, 'return': 98.8, 'dd': -3.77, 'trades': 28},
        {'coin': 'MOODENG', 'rdd': 13.34, 'return': 73.8, 'dd': -5.53, 'trades': 26},
        {'coin': 'TRUMPSOL (optimized)', 'rdd': best['rdd'], 'return': best['return'], 'dd': best['dd'], 'trades': best['trades']}
    ]

    df_comp = pd.DataFrame(comparison).sort_values('rdd', ascending=False)

    print(f"\n{'Rank':<6} {'Coin':<22} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'Status'}")
    print("-" * 75)

    for i, (_, row) in enumerate(df_comp.iterrows(), 1):
        marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        status = "✅" if row['rdd'] >= 10 else "⚠️" if row['rdd'] >= 5 else "❌"
        print(f"{marker} {i:<4} {row['coin']:<22} {row['trades']:<8.0f} {row['return']:+9.1f}% {row['dd']:9.2f}% {row['rdd']:7.2f}x {status}")

    if best['rdd'] >= 10:
        print(f"\n✅ TRUMPSOL VIABLE - Add to bot!")
    elif best['rdd'] >= 5:
        print(f"\n⚠️ TRUMPSOL MARGINAL - {best['rdd']:.2f}x R/DD (target: 10x+ preferred, 5x+ acceptable)")
        print(f"   Logical filters applied, replicable edge expected")
    else:
        print(f"\n❌ TRUMPSOL still below 5x threshold")

    print("=" * 80)

else:
    print("\n❌ No configurations with 20+ trades found")
    print("   Showing configs with 15+ trades:")

    results_15 = sorted([r for r in results if r['trades'] >= 15], key=lambda x: x['rdd'], reverse=True)

    if results_15:
        for i, result in enumerate(results_15[:5], 1):
            filters = []
            filters.append(f"ATR>{result['atr_mult']}x")
            if result.get('volume_min'):
                filters.append(f"Vol>={result['volume_min']}x")
            config_str = ", ".join(filters)
            print(f"  {i}. {result['trades']} trades, {result['rdd']:.2f}x R/DD - {config_str}")
