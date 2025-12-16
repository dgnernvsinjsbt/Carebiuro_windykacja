#!/usr/bin/env python3
"""
Test ATR expansion strategy on TRUMPSOL
Sequential optimization like MOODENG
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

    # Calculate daily RSI
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

    # Generate LONG-only signals
    signals = []
    for i in range(len(df)):
        row = df.iloc[i]

        if (row['atr_ratio'] > params['atr_mult'] and
            row['distance'] < params['ema_dist'] and
            row['bullish'] and
            not pd.isna(row['rsi_daily']) and
            row['rsi_daily'] > 50):
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
    sl_rate = (df_t['exit_reason'] == 'SL').sum() / len(df_t) * 100

    return {
        'trades': len(trades),
        'signals': len(signals),
        'return': total_return,
        'dd': dd,
        'rdd': rdd,
        'wr': wr,
        'tp_rate': tp_rate,
        'sl_rate': sl_rate,
        **params
    }

# Load data
df = pd.read_csv('trumpsol_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("TRUMPSOL VOLATILITY ANALYSIS")
print("=" * 80)
print(f"\nData: {len(df):,} candles (60 days)")
print(f"Price Range: ${df['close'].min():.6f} - ${df['close'].max():.6f}")

# Calculate volatility profile
df_temp = df.copy()
df_temp['atr'] = calculate_atr(df_temp['high'], df_temp['low'], df_temp['close'])
df_temp['atr_pct'] = (df_temp['atr'] / df_temp['close'] * 100)

avg_atr_pct = df_temp['atr_pct'].mean()
print(f"\nAverage ATR%: {avg_atr_pct:.4f}")

# Compare to FARTCOIN/MOODENG
fartcoin_atr = 0.3690
moodeng_atr = 0.2459

fartcoin_ratio = fartcoin_atr / avg_atr_pct
moodeng_ratio = moodeng_atr / avg_atr_pct

print(f"\nVolatility vs FARTCOIN: {fartcoin_ratio:.2f}x {'MORE' if fartcoin_ratio > 1 else 'LESS'} volatile")
print(f"Volatility vs MOODENG: {moodeng_ratio:.2f}x {'MORE' if moodeng_ratio > 1 else 'LESS'} volatile")

# Start with MOODENG-like params (since it's moderate volatility)
base_params = {
    'ema_dist': 2.0,
    'tp_mult': 6.0,
    'sl_mult': 1.5,
    'limit_offset': 0.7
}

print("\n" + "=" * 80)
print("SEQUENTIAL OPTIMIZATION")
print("=" * 80)

# Step 1: ATR
print("\n" + "-" * 80)
print("STEP 1: ATR Threshold")
print("-" * 80)

atr_results = []
for atr in [1.2, 1.4, 1.5, 1.6, 1.8]:
    params = base_params.copy()
    params['atr_mult'] = atr
    result = backtest(df, params)
    if result and 20 <= result['trades'] <= 100:
        atr_results.append(result)
        print(f"  ATR {atr}x → {result['trades']} trades, {result['rdd']:.2f}x R/DD, {result['return']:+.1f}%")

if atr_results:
    best_atr = max(atr_results, key=lambda x: x['rdd'])
    base_params['atr_mult'] = best_atr['atr_mult']
    print(f"\n✅ Best ATR: {best_atr['atr_mult']}x → {best_atr['rdd']:.2f}x R/DD")
else:
    base_params['atr_mult'] = 1.4
    print(f"\n⚠️ No configs with 20-100 trades, using 1.4x")

# Step 2: TP/SL
print("\n" + "-" * 80)
print("STEP 2: TP/SL Optimization")
print("-" * 80)

tp_sl_results = []
for tp in [4, 6, 8]:
    for sl in [1.5, 2.0]:
        params = base_params.copy()
        params['tp_mult'] = tp
        params['sl_mult'] = sl
        result = backtest(df, params)
        if result and 20 <= result['trades'] <= 100:
            tp_sl_results.append(result)
            print(f"  TP {tp}x / SL {sl}x → {result['rdd']:.2f}x R/DD, {result['tp_rate']:.1f}% TP rate")

if tp_sl_results:
    best_tp_sl = max(tp_sl_results, key=lambda x: x['rdd'])
    base_params['tp_mult'] = best_tp_sl['tp_mult']
    base_params['sl_mult'] = best_tp_sl['sl_mult']
    print(f"\n✅ Best TP/SL: {best_tp_sl['tp_mult']}x/{best_tp_sl['sl_mult']}x → {best_tp_sl['rdd']:.2f}x R/DD")

# Step 3: Limit
print("\n" + "-" * 80)
print("STEP 3: Limit Offset")
print("-" * 80)

limit_results = []
for limit in [0.5, 0.7, 1.0]:
    params = base_params.copy()
    params['limit_offset'] = limit
    result = backtest(df, params)
    if result and 20 <= result['trades'] <= 100:
        limit_results.append(result)
        print(f"  Limit {limit}% → {result['rdd']:.2f}x R/DD, {result['trades']} trades")

if limit_results:
    best_limit = max(limit_results, key=lambda x: x['rdd'])
    base_params['limit_offset'] = best_limit['limit_offset']
    print(f"\n✅ Best Limit: {best_limit['limit_offset']}% → {best_limit['rdd']:.2f}x R/DD")

# Final result
final = backtest(df, base_params)

print("\n" + "=" * 80)
print("FINAL TRUMPSOL CONFIGURATION")
print("=" * 80)

if final:
    print(f"\nParameters:")
    print(f"  ATR expansion: > {final['atr_mult']}x")
    print(f"  EMA distance: < {final['ema_dist']}%")
    print(f"  Take Profit: {final['tp_mult']}x ATR")
    print(f"  Stop Loss: {final['sl_mult']}x ATR")
    print(f"  Limit offset: {final['limit_offset']}%")
    print(f"  Daily RSI: > 50")

    print(f"\nPerformance:")
    print(f"  Trades: {final['trades']} (from {final['signals']} signals, {final['trades']/final['signals']*100:.1f}% fill)")
    print(f"  Return: {final['return']:+.2f}%")
    print(f"  Max DD: {final['dd']:.2f}%")
    print(f"  R/DD: {final['rdd']:.2f}x")
    print(f"  Win Rate: {final['wr']:.1f}%")
    print(f"  TP Rate: {final['tp_rate']:.1f}%")
    print(f"  SL Rate: {final['sl_rate']:.1f}%")

    # Compare to FARTCOIN/MOODENG
    print(f"\n" + "=" * 80)
    print("COMPARISON TO OTHER COINS")
    print("=" * 80)

    comparison = [
        {'coin': 'FARTCOIN', 'rdd': 26.21, 'return': 98.8, 'dd': -3.77, 'trades': 28},
        {'coin': 'MOODENG', 'rdd': 13.34, 'return': 73.8, 'dd': -5.53, 'trades': 26},
        {'coin': 'TRUMPSOL', 'rdd': final['rdd'], 'return': final['return'], 'dd': final['dd'], 'trades': final['trades']}
    ]

    df_comp = pd.DataFrame(comparison).sort_values('rdd', ascending=False)

    print(f"\n{'Rank':<6} {'Coin':<12} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'Status'}")
    print("-" * 70)

    for i, (_, row) in enumerate(df_comp.iterrows(), 1):
        marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        status = "✅" if row['rdd'] >= 10 else "⚠️" if row['rdd'] >= 5 else "❌"
        print(f"{marker} {i:<4} {row['coin']:<12} {row['trades']:<8.0f} {row['return']:+9.1f}% {row['dd']:9.2f}% {row['rdd']:7.2f}x {status}")

    print(f"\n" + "=" * 80)
    if final['rdd'] >= 10:
        print("✅ TRUMPSOL VIABLE - Add to bot!")
        print(f"   R/DD {final['rdd']:.2f}x exceeds 10x threshold")
    elif final['rdd'] >= 5:
        print("⚠️ TRUMPSOL MARGINAL - Consider adding")
        print(f"   R/DD {final['rdd']:.2f}x is decent but below 10x target")
    else:
        print("❌ TRUMPSOL NOT VIABLE")
        print(f"   R/DD {final['rdd']:.2f}x too low (target: 10x+)")
    print("=" * 80)

else:
    print("\n❌ No viable configuration found")
