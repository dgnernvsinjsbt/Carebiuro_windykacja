#!/usr/bin/env python3
"""
Find sweetspot: 20-100 trades with positive Return/DD > 2.0x
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

def backtest_symbol(df, symbol, params):
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
        'symbol': symbol,
        'trades': len(trades),
        'signals': len(signals),
        'fill_rate': len(trades) / len(signals) * 100,
        'return': total_return,
        'dd': dd,
        'rdd': rdd,
        'wr': wr,
        'tp_rate': tp_rate,
        **params
    }

print("=" * 80)
print("BTC & ETH SWEETSPOT FINDER (20-100 trades, R/DD > 2.0x)")
print("=" * 80)

# Load data
btc_df = pd.read_csv('btc_usdt_60d_bingx.csv')
btc_df.columns = btc_df.columns.str.lower()
btc_df['timestamp'] = pd.to_datetime(btc_df['timestamp'])
btc_df = btc_df.sort_values('timestamp').reset_index(drop=True)

eth_df = pd.read_csv('eth_usdt_60d_bingx.csv')
eth_df.columns = eth_df.columns.str.lower()
eth_df['timestamp'] = pd.to_datetime(eth_df['timestamp'])
eth_df = eth_df.sort_values('timestamp').reset_index(drop=True)

print(f"\nBTC: {len(btc_df):,} candles")
print(f"ETH: {len(eth_df):,} candles")

# BTC: Test between 0.2x (1098 trades) and 1.5x (4 trades)
print("\n" + "=" * 80)
print("TESTING BTC-USDT (target: 20-100 trades)")
print("=" * 80)

btc_configs = []
for atr_mult in [0.6, 0.8, 1.0, 1.2, 1.4]:
    for ema_dist in [2.0, 4.0]:
        for limit in [0.5, 0.8]:
            btc_configs.append({
                'atr_mult': atr_mult,
                'ema_dist': ema_dist,
                'tp_mult': 8.0,
                'sl_mult': 2.0,
                'limit_offset': limit
            })

print(f"Testing {len(btc_configs)} configs for BTC...")

btc_results = []
for params in btc_configs:
    result = backtest_symbol(btc_df, 'BTC-USDT', params)
    if result and 20 <= result['trades'] <= 100:
        btc_results.append(result)

print(f"Found {len(btc_results)} configs with 20-100 trades")

if btc_results:
    btc_results.sort(key=lambda x: x['rdd'], reverse=True)
    print(f"\n🏆 BEST CONFIGS FOR BTC (20-100 trades):")
    print(f"\n{'Rank':<6} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'TP%':<8} {'Config'}")
    print("-" * 110)
    
    for rank, r in enumerate(btc_results[:5], 1):
        config = f"ATR:{r['atr_mult']} EMA:{r['ema_dist']}% Limit:{r['limit_offset']}%"
        print(f"{rank:<6} {r['trades']:<8} {r['return']:+9.1f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x {r['wr']:7.1f}% {r['tp_rate']:7.1f}% {config}")
else:
    print("\n❌ No BTC configs found with 20-100 trades")

# ETH: Test between 0.3x (345 trades) and 1.5x (~7 trades)
print("\n" + "=" * 80)
print("TESTING ETH-USDT (target: 20-100 trades)")
print("=" * 80)

eth_configs = []
for atr_mult in [0.8, 1.0, 1.2, 1.4, 1.6]:
    for ema_dist in [2.0, 4.0]:
        for limit in [0.5, 0.8]:
            eth_configs.append({
                'atr_mult': atr_mult,
                'ema_dist': ema_dist,
                'tp_mult': 8.0,
                'sl_mult': 2.0,
                'limit_offset': limit
            })

print(f"Testing {len(eth_configs)} configs for ETH...")

eth_results = []
for params in eth_configs:
    result = backtest_symbol(eth_df, 'ETH-USDT', params)
    if result and 20 <= result['trades'] <= 100:
        eth_results.append(result)

print(f"Found {len(eth_results)} configs with 20-100 trades")

if eth_results:
    eth_results.sort(key=lambda x: x['rdd'], reverse=True)
    print(f"\n🏆 BEST CONFIGS FOR ETH (20-100 trades):")
    print(f"\n{'Rank':<6} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'TP%':<8} {'Config'}")
    print("-" * 110)
    
    for rank, r in enumerate(eth_results[:5], 1):
        config = f"ATR:{r['atr_mult']} EMA:{r['ema_dist']}% Limit:{r['limit_offset']}%"
        print(f"{rank:<6} {r['trades']:<8} {r['return']:+9.1f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x {r['wr']:7.1f}% {r['tp_rate']:7.1f}% {config}")
else:
    print("\n❌ No ETH configs found with 20-100 trades")

# Final comparison
print("\n" + "=" * 80)
print("FINAL VERDICT")
print("=" * 80)

viable_configs = []

# FARTCOIN baseline
viable_configs.append({
    'symbol': 'FARTCOIN',
    'trades': 28,
    'return': 98.83,
    'dd': -3.77,
    'rdd': 26.21,
    'wr': 53.6,
    'viable': True
})

# Best BTC
if btc_results:
    best_btc = btc_results[0]
    viable = best_btc['rdd'] >= 2.0 and best_btc['return'] > 0
    viable_configs.append({
        'symbol': 'BTC-USDT',
        'trades': best_btc['trades'],
        'return': best_btc['return'],
        'dd': best_btc['dd'],
        'rdd': best_btc['rdd'],
        'wr': best_btc['wr'],
        'viable': viable
    })

# Best ETH
if eth_results:
    best_eth = eth_results[0]
    viable = best_eth['rdd'] >= 2.0 and best_eth['return'] > 0
    viable_configs.append({
        'symbol': 'ETH-USDT',
        'trades': best_eth['trades'],
        'return': best_eth['return'],
        'dd': best_eth['dd'],
        'rdd': best_eth['rdd'],
        'wr': best_eth['wr'],
        'viable': viable
    })

df_comp = pd.DataFrame(viable_configs)
df_comp = df_comp.sort_values('rdd', ascending=False)

print(f"\n{'Symbol':<12} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'Viable?'}")
print("-" * 90)

for _, row in df_comp.iterrows():
    status = "✅ YES" if row['viable'] else "❌ NO"
    print(f"{row['symbol']:<12} {row['trades']:<8.0f} {row['return']:+9.1f}% {row['dd']:9.2f}% {row['rdd']:7.2f}x {row['wr']:7.1f}% {status}")

print("\n" + "=" * 80)
