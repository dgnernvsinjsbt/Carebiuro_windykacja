#!/usr/bin/env python3
"""
Fix TP targets - find optimal TP that actually gets hit
Keep winning params: ATR 1.2x, EMA 1.5%, SL 1.0x, Limit 0.6%
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
    time_rate = (df_t['exit_reason'] == 'TIME').sum() / len(df_t) * 100
    
    return {
        'trades': len(trades),
        'signals': len(signals),
        'return': total_return,
        'dd': dd,
        'rdd': rdd,
        'wr': wr,
        'tp_rate': tp_rate,
        'sl_rate': sl_rate,
        'time_rate': time_rate,
        **params
    }

# Load data
df = pd.read_csv('eth_usdt_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("ETH TP OPTIMIZATION - Fix useless 25x TP")
print("=" * 80)
print(f"Data: {len(df):,} candles (60 days)\n")

# Keep winning params, vary only TP
base_params = {
    'atr_mult': 1.2,
    'ema_dist': 1.5,
    'sl_mult': 1.0,
    'limit_offset': 0.6
}

print("Fixed parameters:")
print(f"  ATR: {base_params['atr_mult']}x")
print(f"  EMA: {base_params['ema_dist']}%")
print(f"  SL: {base_params['sl_mult']}x ATR")
print(f"  Limit: {base_params['limit_offset']}%")
print(f"  RSI: > 50")

print("\n" + "=" * 80)
print("TESTING TP TARGETS (find optimal that actually gets hit)")
print("=" * 80)

tp_values = [4, 5, 6, 7, 8, 10, 12, 15, 18, 20, 25]
results = []

print(f"\n{'TP':<6} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'TP%':<8} {'SL%':<8} {'TIME%'}")
print("-" * 100)

for tp in tp_values:
    params = base_params.copy()
    params['tp_mult'] = tp
    result = backtest(df, params)
    if result:
        results.append(result)
        print(f"{tp:<6.0f} {result['trades']:<8} {result['return']:+9.1f}% {result['dd']:9.2f}% {result['rdd']:7.2f}x {result['wr']:7.1f}% {result['tp_rate']:7.1f}% {result['sl_rate']:7.1f}% {result['time_rate']:6.1f}%")

# Sort by R/DD
results.sort(key=lambda x: x['rdd'], reverse=True)

print("\n" + "=" * 80)
print("BEST TP TARGETS BY R/DD")
print("=" * 80)

print(f"\n{'Rank':<6} {'TP':<6} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'TP%':<8} {'SL%':<8} {'TIME%'}")
print("-" * 100)

for i, r in enumerate(results[:5], 1):
    marker = "🎯" if r['rdd'] >= 5.8 else "  "
    print(f"{marker} {i:<4} {r['tp_mult']:<6.0f} {r['trades']:<8} {r['return']:+9.1f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x {r['tp_rate']:7.1f}% {r['sl_rate']:7.1f}% {r['time_rate']:6.1f}%")

# Detailed analysis
print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

best = results[0]

print(f"\nBest TP: {best['tp_mult']}x ATR")
print(f"\nExit breakdown:")
print(f"  TP exits: {best['tp_rate']:.1f}%")
print(f"  SL exits: {best['sl_rate']:.1f}%")
print(f"  Time exits: {best['time_rate']:.1f}%")

print(f"\nPerformance:")
print(f"  Trades: {best['trades']}")
print(f"  Return: {best['return']:+.2f}%")
print(f"  Max DD: {best['dd']:.2f}%")
print(f"  R/DD: {best['rdd']:.2f}x")
print(f"  Win Rate: {best['wr']:.1f}%")

# Compare with 25x TP
tp25 = [r for r in results if r['tp_mult'] == 25][0]
print(f"\nComparison with 25x TP:")
print(f"  R/DD: {tp25['rdd']:.2f}x → {best['rdd']:.2f}x ({(best['rdd']/tp25['rdd']-1)*100:+.1f}%)")
print(f"  Return: {tp25['return']:+.1f}% → {best['return']:+.1f}% ({best['return']-tp25['return']:+.1f}%)")
print(f"  TP rate: {tp25['tp_rate']:.1f}% → {best['tp_rate']:.1f}% ({best['tp_rate']-tp25['tp_rate']:+.1f}%)")

print("\n" + "=" * 80)
print("FINAL CONFIG")
print("=" * 80)

print(f"\nOptimized ETH-USDT Strategy:")
print(f"  ATR expansion: > {best['atr_mult']}x")
print(f"  EMA distance: < {best['ema_dist']}%")
print(f"  Take Profit: {best['tp_mult']}x ATR")
print(f"  Stop Loss: {best['sl_mult']}x ATR")
print(f"  Limit offset: {best['limit_offset']}%")
print(f"  Daily RSI: > 50")

print(f"\nPerformance: {best['trades']} trades, {best['return']:+.1f}%, {best['rdd']:.2f}x R/DD")
print("=" * 80)

