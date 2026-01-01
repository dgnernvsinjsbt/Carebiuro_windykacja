#!/usr/bin/env python3
"""
Test ATR expansion strategy on POPCAT and BRETT
Sequential optimization for each
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

def optimize_coin(coin_name, file_path):
    """Sequential optimization for a coin"""
    
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.lower()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print("=" * 80)
    print(f"{coin_name} OPTIMIZATION")
    print("=" * 80)
    print(f"Data: {len(df):,} candles (60 days)")
    print(f"Price: ${df['close'].min():.6f} - ${df['close'].max():.6f}")
    
    # Start with FARTCOIN-like params (since these coins are FARTCOIN-like)
    base_params = {
        'ema_dist': 2.5,
        'tp_mult': 8.0,
        'sl_mult': 2.0,
        'limit_offset': 1.0
    }
    
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
    
    if atr_results:
        best_atr = max(atr_results, key=lambda x: x['rdd'])
        base_params['atr_mult'] = best_atr['atr_mult']
        print(f"✅ Best ATR: {best_atr['atr_mult']}x → {best_atr['trades']} trades, {best_atr['rdd']:.2f}x R/DD")
    else:
        base_params['atr_mult'] = 1.5
        print(f"⚠️ No configs with 20-100 trades, using 1.5x")
    
    # Step 2: TP/SL
    print("\n" + "-" * 80)
    print("STEP 2: TP/SL Optimization")
    print("-" * 80)
    
    tp_sl_results = []
    for tp in [6, 8, 10]:
        for sl in [1.5, 2.0]:
            params = base_params.copy()
            params['tp_mult'] = tp
            params['sl_mult'] = sl
            result = backtest(df, params)
            if result and 20 <= result['trades'] <= 100:
                tp_sl_results.append(result)
    
    if tp_sl_results:
        best_tp_sl = max(tp_sl_results, key=lambda x: x['rdd'])
        base_params['tp_mult'] = best_tp_sl['tp_mult']
        base_params['sl_mult'] = best_tp_sl['sl_mult']
        print(f"✅ Best TP/SL: {best_tp_sl['tp_mult']}x/{best_tp_sl['sl_mult']}x → {best_tp_sl['rdd']:.2f}x R/DD")
    
    # Step 3: Limit
    print("\n" + "-" * 80)
    print("STEP 3: Limit Offset")
    print("-" * 80)
    
    limit_results = []
    for limit in [0.7, 1.0, 1.2]:
        params = base_params.copy()
        params['limit_offset'] = limit
        result = backtest(df, params)
        if result and 20 <= result['trades'] <= 100:
            limit_results.append(result)
    
    if limit_results:
        best_limit = max(limit_results, key=lambda x: x['rdd'])
        base_params['limit_offset'] = best_limit['limit_offset']
        print(f"✅ Best Limit: {best_limit['limit_offset']}% → {best_limit['rdd']:.2f}x R/DD")
    
    # Final result
    final = backtest(df, base_params)
    
    return final, base_params

# Test both coins
print("=" * 80)
print("TESTING POPCAT & BRETT WITH FARTCOIN-LIKE STRATEGY")
print("=" * 80)

results = {}

# POPCAT
popcat_result, popcat_params = optimize_coin('POPCAT', 'popcat_usdt_60d_bingx.csv')
results['POPCAT'] = popcat_result

print("\n")

# BRETT
brett_result, brett_params = optimize_coin('BRETT', 'brett_usdt_60d_bingx.csv')
results['BRETT'] = brett_result

# Final comparison
print("\n" + "=" * 80)
print("FINAL RESULTS - ALL COINS")
print("=" * 80)

comparison = [
    {'coin': 'FARTCOIN', 'trades': 28, 'return': 98.8, 'dd': -3.77, 'rdd': 26.21, 'wr': 53.6, 'tp': 28.6},
    {'coin': 'MOODENG', 'trades': 26, 'return': 73.8, 'dd': -5.53, 'rdd': 13.34, 'wr': 46.2, 'tp': 42.3},
]

if popcat_result:
    comparison.append({
        'coin': 'POPCAT',
        'trades': popcat_result['trades'],
        'return': popcat_result['return'],
        'dd': popcat_result['dd'],
        'rdd': popcat_result['rdd'],
        'wr': popcat_result['wr'],
        'tp': popcat_result['tp_rate']
    })

if brett_result:
    comparison.append({
        'coin': 'BRETT',
        'trades': brett_result['trades'],
        'return': brett_result['return'],
        'dd': brett_result['dd'],
        'rdd': brett_result['rdd'],
        'wr': brett_result['wr'],
        'tp': brett_result['tp_rate']
    })

df_comp = pd.DataFrame(comparison)
df_comp = df_comp.sort_values('rdd', ascending=False)

print(f"\n{'Rank':<6} {'Coin':<12} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'TP%':<8} {'Status'}")
print("-" * 100)

for i, (_, row) in enumerate(df_comp.iterrows(), 1):
    marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
    status = "✅" if row['rdd'] >= 10 else "⚠️" if row['rdd'] >= 5 else "❌"
    print(f"{marker} {i:<4} {row['coin']:<12} {row['trades']:<8.0f} {row['return']:+9.1f}% {row['dd']:9.2f}% {row['rdd']:7.2f}x {row['wr']:7.1f}% {row['tp']:7.1f}% {status}")

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

viable = df_comp[df_comp['rdd'] >= 10]
if len(viable) > 1:
    print(f"\n✅ {len(viable)} coins with R/DD >= 10x - All viable for bot!")
    for _, row in viable.iterrows():
        print(f"  - {row['coin']}: {row['rdd']:.2f}x R/DD, {row['trades']:.0f} trades, {row['return']:+.1f}%")
elif len(viable) == 1:
    print(f"\n⚠️ Only {viable.iloc[0]['coin']} hits R/DD >= 10x target")
else:
    print(f"\n❌ None of the new coins hit R/DD >= 10x target")
    print(f"   Best performer: {df_comp.iloc[0]['coin']} with {df_comp.iloc[0]['rdd']:.2f}x R/DD")

print("\n" + "=" * 80)
