#!/usr/bin/env python3
"""
Aggressive multi-angle optimization for ETH
Target: R/DD > 4.5x, 20-60 trades
"""

import pandas as pd
import numpy as np
from itertools import product

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
    
    # Generate LONG-only signals with configurable RSI filter
    signals = []
    for i in range(len(df)):
        row = df.iloc[i]
        
        rsi_check = True
        if params['rsi_min'] is not None:
            rsi_check = not pd.isna(row['rsi_daily']) and row['rsi_daily'] > params['rsi_min']
        
        if (row['atr_ratio'] > params['atr_mult'] and
            row['distance'] < params['ema_dist'] and
            row['bullish'] and
            rsi_check):
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
print("ETH AGGRESSIVE OPTIMIZATION - ALL ANGLES")
print("=" * 80)
print(f"Data: {len(df):,} candles (60 days)")
print(f"\nTarget: R/DD > 4.5x, 20-60 trades\n")

# STRATEGY 1: Extreme TP/SL ratios
print("=" * 80)
print("ANGLE 1: EXTREME TP/SL RATIOS (maximize winners)")
print("=" * 80)

configs_1 = []
for atr in [1.3, 1.4, 1.5, 1.6]:
    for tp in [12, 15, 20]:
        for sl in [1.0, 1.5]:
            for limit in [0.4, 0.5, 0.6]:
                configs_1.append({
                    'atr_mult': atr,
                    'ema_dist': 2.0,
                    'tp_mult': tp,
                    'sl_mult': sl,
                    'limit_offset': limit,
                    'rsi_min': 50,
                    'angle': 'extreme_tp_sl'
                })

results = []
for params in configs_1:
    result = backtest(df, params)
    if result and 20 <= result['trades'] <= 60:
        results.append(result)

print(f"Tested {len(configs_1)} configs, found {len(results)} with 20-60 trades")

# STRATEGY 2: No RSI filter
print("\n" + "=" * 80)
print("ANGLE 2: REMOVE RSI FILTER (more signals)")
print("=" * 80)

configs_2 = []
for atr in [1.4, 1.5, 1.6]:
    for tp in [8, 10, 12]:
        for sl in [1.5, 2.0]:
            for limit in [0.3, 0.4, 0.5]:
                configs_2.append({
                    'atr_mult': atr,
                    'ema_dist': 2.0,
                    'tp_mult': tp,
                    'sl_mult': sl,
                    'limit_offset': limit,
                    'rsi_min': None,  # No RSI filter!
                    'angle': 'no_rsi'
                })

for params in configs_2:
    result = backtest(df, params)
    if result and 20 <= result['trades'] <= 60:
        results.append(result)

print(f"Tested {len(configs_2)} configs, found {len([r for r in results if r['angle']=='no_rsi'])} with 20-60 trades")

# STRATEGY 3: Lower RSI threshold
print("\n" + "=" * 80)
print("ANGLE 3: LOWER RSI THRESHOLD (45 instead of 50)")
print("=" * 80)

configs_3 = []
for atr in [1.3, 1.4, 1.5]:
    for tp in [10, 12, 15]:
        for sl in [1.0, 1.5]:
            for limit in [0.4, 0.5]:
                configs_3.append({
                    'atr_mult': atr,
                    'ema_dist': 2.0,
                    'tp_mult': tp,
                    'sl_mult': sl,
                    'limit_offset': limit,
                    'rsi_min': 45,  # Lower threshold
                    'angle': 'rsi_45'
                })

for params in configs_3:
    result = backtest(df, params)
    if result and 20 <= result['trades'] <= 60:
        results.append(result)

print(f"Tested {len(configs_3)} configs, found {len([r for r in results if r['angle']=='rsi_45'])} with 20-60 trades")

# STRATEGY 4: Tighter EMA + wider TP
print("\n" + "=" * 80)
print("ANGLE 4: TIGHT EMA + WIDE TP (quality over quantity)")
print("=" * 80)

configs_4 = []
for atr in [1.2, 1.3, 1.4]:
    for ema in [1.0, 1.5]:
        for tp in [15, 20, 25]:
            for sl in [1.0, 1.5]:
                for limit in [0.5, 0.6]:
                    configs_4.append({
                        'atr_mult': atr,
                        'ema_dist': ema,
                        'tp_mult': tp,
                        'sl_mult': sl,
                        'limit_offset': limit,
                        'rsi_min': 50,
                        'angle': 'tight_ema'
                    })

for params in configs_4:
    result = backtest(df, params)
    if result and 20 <= result['trades'] <= 60:
        results.append(result)

print(f"Tested {len(configs_4)} configs, found {len([r for r in results if r['angle']=='tight_ema'])} with 20-60 trades")

# Sort and display top results
print("\n" + "=" * 80)
print("TOP 15 CONFIGS (R/DD > 4.5x highlighted)")
print("=" * 80)

results.sort(key=lambda x: x['rdd'], reverse=True)

print(f"\n{'#':<4} {'Trades':<7} {'Return':<9} {'DD':<9} {'R/DD':<8} {'WR%':<7} {'TP%':<7} {'Angle':<15} {'Config'}")
print("-" * 140)

for i, r in enumerate(results[:15], 1):
    marker = "🎯" if r['rdd'] >= 4.5 else "  "
    config = f"ATR:{r['atr_mult']} TP:{r['tp_mult']}x SL:{r['sl_mult']}x Lim:{r['limit_offset']}% RSI:{r['rsi_min']}"
    print(f"{marker} {i:<2} {r['trades']:<7} {r['return']:+8.1f}% {r['dd']:8.2f}% {r['rdd']:7.2f}x {r['wr']:6.1f}% {r['tp_rate']:6.1f}% {r['angle']:<15} {config}")

# Best config details
if results:
    print("\n" + "=" * 80)
    print("BEST CONFIG DETAILS")
    print("=" * 80)
    
    best = results[0]
    print(f"\nStrategy Angle: {best['angle']}")
    print(f"\nParameters:")
    print(f"  ATR expansion: > {best['atr_mult']}x")
    print(f"  EMA distance: < {best['ema_dist']}%")
    print(f"  Take Profit: {best['tp_mult']}x ATR")
    print(f"  Stop Loss: {best['sl_mult']}x ATR")
    print(f"  Limit offset: {best['limit_offset']}%")
    print(f"  Daily RSI: > {best['rsi_min']}" if best['rsi_min'] else "  Daily RSI: DISABLED")
    
    print(f"\nPerformance:")
    print(f"  Trades: {best['trades']} (from {best['signals']} signals, {best['trades']/best['signals']*100:.1f}% fill)")
    print(f"  Return: {best['return']:+.2f}%")
    print(f"  Max DD: {best['dd']:.2f}%")
    print(f"  R/DD: {best['rdd']:.2f}x {'✅ TARGET MET!' if best['rdd'] >= 4.5 else '❌ Below 4.5x'}")
    print(f"  Win Rate: {best['wr']:.1f}%")
    print(f"  TP Rate: {best['tp_rate']:.1f}%")
    
    print(f"\n{'='*80}")
    print(f"Total configs tested: {len(configs_1) + len(configs_2) + len(configs_3) + len(configs_4)}")
    print(f"Configs with 20-60 trades: {len(results)}")
    print(f"Configs with R/DD > 4.5x: {len([r for r in results if r['rdd'] >= 4.5])}")
    print(f"{'='*80}")
else:
    print("\n❌ No configs found with 20-60 trades")

