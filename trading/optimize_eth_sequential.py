#!/usr/bin/env python3
"""
Sequential parameter optimization for ETH-USDT
Start: ATR 1.2x, EMA 2.0%, TP 8x, SL 2x, Limit 0.5%
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
df = pd.read_csv('eth_usdt_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("ETH-USDT SEQUENTIAL OPTIMIZATION")
print("=" * 80)
print(f"\nData: {len(df):,} candles (60 days)")

# Baseline
best_params = {
    'atr_mult': 1.2,
    'ema_dist': 2.0,
    'tp_mult': 8.0,
    'sl_mult': 2.0,
    'limit_offset': 0.5
}

baseline = backtest(df, best_params)
print(f"\nBaseline: {baseline['trades']} trades, {baseline['return']:+.1f}%, {baseline['rdd']:.2f}x R/DD")

# STEP 1: Optimize ATR expansion
print("\n" + "=" * 80)
print("STEP 1: Optimize ATR Expansion")
print("=" * 80)

atr_values = [0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
results = []

for atr in atr_values:
    params = best_params.copy()
    params['atr_mult'] = atr
    result = backtest(df, params)
    if result:
        results.append(result)
        print(f"ATR {atr:4.1f}x: {result['trades']:3} trades, {result['return']:+6.1f}%, {result['rdd']:5.2f}x R/DD, {result['wr']:4.1f}% WR")

if results:
    best = max(results, key=lambda x: x['rdd'])
    best_params['atr_mult'] = best['atr_mult']
    print(f"\n✅ Best ATR: {best['atr_mult']}x → {best['rdd']:.2f}x R/DD")

# STEP 2: Optimize EMA distance
print("\n" + "=" * 80)
print("STEP 2: Optimize EMA Distance")
print("=" * 80)

ema_values = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
results = []

for ema in ema_values:
    params = best_params.copy()
    params['ema_dist'] = ema
    result = backtest(df, params)
    if result:
        results.append(result)
        print(f"EMA {ema:4.1f}%: {result['trades']:3} trades, {result['return']:+6.1f}%, {result['rdd']:5.2f}x R/DD, {result['wr']:4.1f}% WR")

if results:
    best = max(results, key=lambda x: x['rdd'])
    best_params['ema_dist'] = best['ema_dist']
    print(f"\n✅ Best EMA: {best['ema_dist']}% → {best['rdd']:.2f}x R/DD")

# STEP 3: Optimize Take Profit
print("\n" + "=" * 80)
print("STEP 3: Optimize Take Profit")
print("=" * 80)

tp_values = [4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0]
results = []

for tp in tp_values:
    params = best_params.copy()
    params['tp_mult'] = tp
    result = backtest(df, params)
    if result:
        results.append(result)
        print(f"TP  {tp:4.1f}x: {result['trades']:3} trades, {result['return']:+6.1f}%, {result['rdd']:5.2f}x R/DD, TP rate: {result['tp_rate']:4.1f}%")

if results:
    best = max(results, key=lambda x: x['rdd'])
    best_params['tp_mult'] = best['tp_mult']
    print(f"\n✅ Best TP: {best['tp_mult']}x ATR → {best['rdd']:.2f}x R/DD")

# STEP 4: Optimize Stop Loss
print("\n" + "=" * 80)
print("STEP 4: Optimize Stop Loss")
print("=" * 80)

sl_values = [1.0, 1.5, 2.0, 2.5, 3.0]
results = []

for sl in sl_values:
    params = best_params.copy()
    params['sl_mult'] = sl
    result = backtest(df, params)
    if result:
        results.append(result)
        print(f"SL  {sl:4.1f}x: {result['trades']:3} trades, {result['return']:+6.1f}%, {result['rdd']:5.2f}x R/DD, {result['wr']:4.1f}% WR")

if results:
    best = max(results, key=lambda x: x['rdd'])
    best_params['sl_mult'] = best['sl_mult']
    print(f"\n✅ Best SL: {best['sl_mult']}x ATR → {best['rdd']:.2f}x R/DD")

# STEP 5: Optimize Limit Offset
print("\n" + "=" * 80)
print("STEP 5: Optimize Limit Offset")
print("=" * 80)

limit_values = [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]
results = []

for limit in limit_values:
    params = best_params.copy()
    params['limit_offset'] = limit
    result = backtest(df, params)
    if result:
        results.append(result)
        print(f"Limit {limit:4.1f}%: {result['trades']:3} trades, {result['return']:+6.1f}%, {result['rdd']:5.2f}x R/DD, Fill: {result['trades']/result['signals']*100:4.1f}%")

if results:
    best = max(results, key=lambda x: x['rdd'])
    best_params['limit_offset'] = best['limit_offset']
    print(f"\n✅ Best Limit: {best['limit_offset']}% → {best['rdd']:.2f}x R/DD")

# Final result
print("\n" + "=" * 80)
print("FINAL OPTIMIZED CONFIG")
print("=" * 80)

final = backtest(df, best_params)

print(f"\nOptimized Parameters:")
print(f"  ATR expansion: > {best_params['atr_mult']}x")
print(f"  EMA distance: < {best_params['ema_dist']}%")
print(f"  Take Profit: {best_params['tp_mult']}x ATR")
print(f"  Stop Loss: {best_params['sl_mult']}x ATR")
print(f"  Limit offset: {best_params['limit_offset']}%")

print(f"\nPerformance:")
print(f"  Trades: {final['trades']} (from {final['signals']} signals, {final['trades']/final['signals']*100:.1f}% fill)")
print(f"  Return: {final['return']:+.2f}%")
print(f"  Max DD: {final['dd']:.2f}%")
print(f"  R/DD: {final['rdd']:.2f}x")
print(f"  Win Rate: {final['wr']:.1f}%")
print(f"  TP Rate: {final['tp_rate']:.1f}%")

print(f"\nComparison with baseline:")
print(f"  R/DD: {baseline['rdd']:.2f}x → {final['rdd']:.2f}x ({(final['rdd']/baseline['rdd']-1)*100:+.1f}%)")
print(f"  Return: {baseline['return']:+.1f}% → {final['return']:+.1f}% ({final['return']-baseline['return']:+.1f}%)")

print("\n" + "=" * 80)
