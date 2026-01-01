#!/usr/bin/env python3
"""
Validate TRUMPSOL filters - test if body % filter is a fluke
- Test on first 30 days vs last 30 days (walk-forward validation)
- Test volume ratio filter more thoroughly
- Test RSI filters
- Test combinations
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
    df['rsi'] = calculate_rsi(df['close'], 14)

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
                row['distance'] < params['ema_dist'] and
                row['bullish'] and
                not pd.isna(row['rsi_daily']) and
                row['rsi_daily'] > 50):
            continue

        # Optional filters
        if params.get('volume_min') and row['volume_ratio'] < params['volume_min']:
            continue

        if params.get('body_max') and row['body_pct'] > params['body_max']:
            continue

        if params.get('rsi_min') and row['rsi'] < params['rsi_min']:
            continue

        if params.get('rsi_max') and row['rsi'] > params['rsi_max']:
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

        trades.append({'pnl_pct': pnl_pct})

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

    return {
        'trades': len(trades),
        'return': total_return,
        'dd': dd,
        'rdd': rdd,
        'wr': wr
    }

# Load data
df_full = pd.read_csv('trumpsol_60d_bingx.csv')
df_full.columns = df_full.columns.str.lower()
df_full['timestamp'] = pd.to_datetime(df_full['timestamp'])
df_full = df_full.sort_values('timestamp').reset_index(drop=True)

# Split into first 30 days and last 30 days
midpoint = len(df_full) // 2
df_first = df_full.iloc[:midpoint].copy()
df_last = df_full.iloc[midpoint:].copy()

print("=" * 80)
print("WALK-FORWARD VALIDATION - Body % Filter")
print("=" * 80)

base_params = {
    'atr_mult': 1.5,
    'ema_dist': 2.0,
    'tp_mult': 8.0,
    'sl_mult': 1.5,
    'limit_offset': 0.5
}

print(f"\nData split:")
print(f"  First 30 days: {df_first['timestamp'].min()} to {df_first['timestamp'].max()}")
print(f"  Last 30 days:  {df_last['timestamp'].min()} to {df_last['timestamp'].max()}")

# Test body filter on both periods
body_thresholds = [None, 0.5, 0.4, 0.35, 0.3, 0.25]

print(f"\n{'Body Filter':<15} {'Period':<12} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%'}")
print("-" * 80)

for body in body_thresholds:
    params = base_params.copy()
    if body:
        params['body_max'] = body

    filter_name = f"< {body}%" if body else "None"

    # Test on first 30 days
    result_first = backtest(df_first, params)
    if result_first and result_first['trades'] >= 5:
        print(f"{filter_name:<15} {'First 30d':<12} {result_first['trades']:<8} {result_first['return']:+9.1f}% {result_first['dd']:9.2f}% {result_first['rdd']:7.2f}x {result_first['wr']:6.1f}%")

    # Test on last 30 days
    result_last = backtest(df_last, params)
    if result_last and result_last['trades'] >= 5:
        print(f"{filter_name:<15} {'Last 30d':<12} {result_last['trades']:<8} {result_last['return']:+9.1f}% {result_last['dd']:9.2f}% {result_last['rdd']:7.2f}x {result_last['wr']:6.1f}%")

# Test volume filter thoroughly
print(f"\n" + "=" * 80)
print("VOLUME RATIO FILTER VALIDATION")
print("=" * 80)

volume_thresholds = [None, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]

print(f"\n{'Vol Filter':<15} {'Period':<12} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%'}")
print("-" * 80)

for vol in volume_thresholds:
    params = base_params.copy()
    if vol:
        params['volume_min'] = vol

    filter_name = f">= {vol}x" if vol else "None"

    result_first = backtest(df_first, params)
    if result_first and result_first['trades'] >= 5:
        print(f"{filter_name:<15} {'First 30d':<12} {result_first['trades']:<8} {result_first['return']:+9.1f}% {result_first['dd']:9.2f}% {result_first['rdd']:7.2f}x {result_first['wr']:6.1f}%")

    result_last = backtest(df_last, params)
    if result_last and result_last['trades'] >= 5:
        print(f"{filter_name:<15} {'Last 30d':<12} {result_last['trades']:<8} {result_last['return']:+9.1f}% {result_last['dd']:9.2f}% {result_last['rdd']:7.2f}x {result_last['wr']:6.1f}%")

# Test RSI filter
print(f"\n" + "=" * 80)
print("RSI (1-MIN) FILTER VALIDATION")
print("=" * 80)

rsi_configs = [
    (None, None, "None"),
    (55, None, ">= 55"),
    (60, None, ">= 60"),
    (None, 60, "<= 60"),
    (50, 70, "50-70"),
]

print(f"\n{'RSI Filter':<15} {'Period':<12} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%'}")
print("-" * 80)

for rsi_min, rsi_max, label in rsi_configs:
    params = base_params.copy()
    if rsi_min:
        params['rsi_min'] = rsi_min
    if rsi_max:
        params['rsi_max'] = rsi_max

    result_first = backtest(df_first, params)
    if result_first and result_first['trades'] >= 5:
        print(f"{label:<15} {'First 30d':<12} {result_first['trades']:<8} {result_first['return']:+9.1f}% {result_first['dd']:9.2f}% {result_first['rdd']:7.2f}x {result_first['wr']:6.1f}%")

    result_last = backtest(df_last, params)
    if result_last and result_last['trades'] >= 5:
        print(f"{label:<15} {'Last 30d':<12} {result_last['trades']:<8} {result_last['return']:+9.1f}% {result_last['dd']:9.2f}% {result_last['rdd']:7.2f}x {result_last['wr']:6.1f}%")

# Summary
print(f"\n" + "=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)

print(f"\nTesting on 60-day full dataset for comparison:")

configs_to_test = [
    ({'body_max': 0.3}, "Body < 0.3%"),
    ({'volume_min': 1.4}, "Volume >= 1.4x"),
    ({'rsi_min': 55}, "RSI >= 55"),
    ({'body_max': 0.35, 'volume_min': 1.2}, "Body < 0.35% + Vol >= 1.2x"),
]

results_full = []

for extra_params, label in configs_to_test:
    params = base_params.copy()
    params.update(extra_params)

    result = backtest(df_full, params)
    if result and result['trades'] >= 15:
        results_full.append({
            'label': label,
            **result
        })

if results_full:
    print(f"\n{'Filter Config':<40} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%'}")
    print("-" * 85)

    for r in sorted(results_full, key=lambda x: x['rdd'], reverse=True):
        print(f"{r['label']:<40} {r['trades']:<8} {r['return']:+9.1f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x {r['wr']:6.1f}%")

print(f"\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\nIf Body < 0.3% performs well on BOTH first 30d and last 30d:")
print("  ✅ Likely a real edge (not a fluke)")
print("\nIf Body < 0.3% only works on one period:")
print("  ❌ Likely overfitting (fluke)")
print("\nIf Volume or RSI filters work better consistently:")
print("  ✅ Use those instead")
print("=" * 80)
