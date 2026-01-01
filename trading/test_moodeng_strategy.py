#!/usr/bin/env python3
"""
Test ATR expansion strategy on MOODENG
Starting point: FARTCOIN-like params but scaled for 1.5x less volatility
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
    
    # Generate LONG-only signals with Daily RSI > 50 filter
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
    
    # Backtest with limit orders
    trades = []
    
    for signal_idx in signals:
        if signal_idx >= len(df) - 1:
            continue
        
        signal_price = df['close'].iloc[signal_idx]
        signal_atr = df['atr'].iloc[signal_idx]
        
        if pd.isna(signal_atr) or signal_atr == 0:
            continue
        
        # Limit order
        limit_price = signal_price * (1 + params['limit_offset'] / 100)
        
        # Try to fill
        filled = False
        fill_idx = None
        
        for i in range(signal_idx + 1, min(signal_idx + 4, len(df))):
            if df['high'].iloc[i] >= limit_price:
                filled = True
                fill_idx = i
                break
        
        if not filled:
            continue
        
        # Trade filled
        entry_price = limit_price
        entry_atr = df['atr'].iloc[fill_idx]
        
        sl_price = entry_price - (params['sl_mult'] * entry_atr)
        tp_price = entry_price + (params['tp_mult'] * entry_atr)
        
        # Find exit
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

# Load MOODENG data
df = pd.read_csv('moodeng_usdt_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("MOODENG STRATEGY TEST (FARTCOIN-like, scaled for 1.5x less volatility)")
print("=" * 80)
print(f"Data: {len(df):,} candles (60 days)")
print(f"Price range: ${df['close'].min():.6f} - ${df['close'].max():.6f}")

# Test grid around scaled FARTCOIN params
print("\n" + "=" * 80)
print("SEQUENTIAL OPTIMIZATION")
print("=" * 80)

# Step 1: Find best ATR
print("\nSTEP 1: Optimize ATR expansion")
print("-" * 80)

base_params = {
    'ema_dist': 2.0,
    'tp_mult': 8.0,
    'sl_mult': 2.0,
    'limit_offset': 0.7
}

atr_values = [0.8, 1.0, 1.2, 1.4, 1.6, 1.8]
atr_results = []

print(f"{'ATR':<6} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8}")
print("-" * 70)

for atr in atr_values:
    params = base_params.copy()
    params['atr_mult'] = atr
    result = backtest(df, params)
    if result and 20 <= result['trades'] <= 100:
        atr_results.append(result)
        print(f"{atr:<6.1f} {result['trades']:<8} {result['return']:+9.1f}% {result['dd']:9.2f}% {result['rdd']:7.2f}x {result['wr']:7.1f}%")

if atr_results:
    best_atr = max(atr_results, key=lambda x: x['rdd'])
    base_params['atr_mult'] = best_atr['atr_mult']
    print(f"\n✅ Best ATR: {best_atr['atr_mult']}x → {best_atr['rdd']:.2f}x R/DD")
else:
    print("\n❌ No ATR configs with 20-100 trades, using 1.0x")
    base_params['atr_mult'] = 1.0

# Step 2: Optimize TP/SL
print("\n" + "=" * 80)
print("STEP 2: Optimize TP/SL")
print("-" * 80)

tp_values = [6, 8, 10, 12, 15]
sl_values = [1.5, 2.0, 2.5]
tp_sl_results = []

print(f"{'TP':<6} {'SL':<6} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'TP%':<8}")
print("-" * 80)

for tp in tp_values:
    for sl in sl_values:
        params = base_params.copy()
        params['tp_mult'] = tp
        params['sl_mult'] = sl
        result = backtest(df, params)
        if result and 20 <= result['trades'] <= 100:
            tp_sl_results.append(result)
            print(f"{tp:<6.0f} {sl:<6.1f} {result['trades']:<8} {result['return']:+9.1f}% {result['dd']:9.2f}% {result['rdd']:7.2f}x {result['tp_rate']:7.1f}%")

if tp_sl_results:
    best_tp_sl = max(tp_sl_results, key=lambda x: x['rdd'])
    base_params['tp_mult'] = best_tp_sl['tp_mult']
    base_params['sl_mult'] = best_tp_sl['sl_mult']
    print(f"\n✅ Best TP/SL: {best_tp_sl['tp_mult']}x / {best_tp_sl['sl_mult']}x → {best_tp_sl['rdd']:.2f}x R/DD")

# Step 3: Optimize Limit offset
print("\n" + "=" * 80)
print("STEP 3: Optimize Limit offset")
print("-" * 80)

limit_values = [0.5, 0.7, 1.0, 1.2]
limit_results = []

print(f"{'Limit':<8} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'Fill%':<8}")
print("-" * 80)

for limit in limit_values:
    params = base_params.copy()
    params['limit_offset'] = limit
    result = backtest(df, params)
    if result and 20 <= result['trades'] <= 100:
        limit_results.append(result)
        fill_rate = result['trades'] / result['signals'] * 100
        print(f"{limit:<8.1f} {result['trades']:<8} {result['return']:+9.1f}% {result['dd']:9.2f}% {result['rdd']:7.2f}x {fill_rate:7.1f}%")

if limit_results:
    best_limit = max(limit_results, key=lambda x: x['rdd'])
    base_params['limit_offset'] = best_limit['limit_offset']
    print(f"\n✅ Best Limit: {best_limit['limit_offset']}% → {best_limit['rdd']:.2f}x R/DD")

# Final result
print("\n" + "=" * 80)
print("FINAL OPTIMIZED CONFIG")
print("=" * 80)

final = backtest(df, base_params)

if final:
    print(f"\nParameters:")
    print(f"  ATR expansion: > {base_params['atr_mult']}x")
    print(f"  EMA distance: < {base_params['ema_dist']}%")
    print(f"  Take Profit: {base_params['tp_mult']}x ATR")
    print(f"  Stop Loss: {base_params['sl_mult']}x ATR")
    print(f"  Limit offset: {base_params['limit_offset']}%")
    print(f"  Daily RSI: > 50")
    
    print(f"\nPerformance:")
    print(f"  Trades: {final['trades']} (from {final['signals']} signals, {final['trades']/final['signals']*100:.1f}% fill)")
    print(f"  Return: {final['return']:+.2f}%")
    print(f"  Max DD: {final['dd']:.2f}%")
    print(f"  R/DD: {final['rdd']:.2f}x {'✅' if final['rdd'] >= 4.5 else '⚠️'}")
    print(f"  Win Rate: {final['wr']:.1f}%")
    print(f"  TP Rate: {final['tp_rate']:.1f}%")
    print(f"  SL Rate: {final['sl_rate']:.1f}%")
    
    # Compare with FARTCOIN
    print(f"\n{'=' * 80}")
    print("COMPARISON")
    print(f"{'=' * 80}")
    
    print(f"\n{'Coin':<12} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'Status'}")
    print("-" * 70)
    print(f"{'FARTCOIN':<12} {28:<8} {+98.8:+9.1f}% {-3.77:9.2f}% {26.21:7.2f}x ✅ LIVE")
    print(f"{'MOODENG':<12} {final['trades']:<8} {final['return']:+9.1f}% {final['dd']:9.2f}% {final['rdd']:7.2f}x {'✅ GOOD' if final['rdd'] >= 4.5 else '⚠️ MEH'}")
    
print("\n" + "=" * 80)
