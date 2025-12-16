#!/usr/bin/env python3
"""
Test FARTCOIN strategy on BTC & ETH
Adjust parameters for lower volatility
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

def backtest_symbol(df, symbol, params):
    """
    Backtest with specific parameters
    params: dict with atr_mult, ema_dist, tp_mult, sl_mult, limit_offset
    """
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

    # Generate signals
    signals = []
    for i in range(len(df)):
        row = df.iloc[i]

        # Entry conditions
        if (row['atr_ratio'] > params['atr_mult'] and
            row['distance'] < params['ema_dist'] and
            row['bullish'] and
            not pd.isna(row['rsi_daily']) and
            row['rsi_daily'] > 50):  # Daily RSI filter
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
print("BTC & ETH STRATEGY TEST (60 DAYS)")
print("=" * 80)

# Load data
symbols_data = {}

for symbol_file, symbol_name in [
    ('btc_usdt_60d_bingx.csv', 'BTC-USDT'),
    ('eth_usdt_60d_bingx.csv', 'ETH-USDT')
]:
    df = pd.read_csv(f'/workspaces/Carebiuro_windykacja/trading/{symbol_file}')
    df.columns = df.columns.str.lower()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    symbols_data[symbol_name] = df
    print(f"\n{symbol_name}: {len(df):,} candles")

# Parameter grid (adjusted for lower volatility)
print("\n" + "=" * 80)
print("TESTING PARAMETER COMBINATIONS")
print("=" * 80)

param_grid = {
    'atr_mult': [1.2, 1.3, 1.5],      # Lower for BTC/ETH
    'ema_dist': [2.0, 3.0, 4.0],       # Tighter
    'tp_mult': [5.0, 6.0, 8.0],        # Various targets
    'sl_mult': [1.5, 2.0],             # Stops
    'limit_offset': [0.5, 1.0]         # Tighter limit
}

# Generate all combinations
param_combinations = [
    dict(zip(param_grid.keys(), v))
    for v in product(*param_grid.values())
]

print(f"\nTesting {len(param_combinations)} parameter combinations per symbol")
print(f"Total tests: {len(param_combinations) * len(symbols_data)}")

all_results = []

for symbol_name, df in symbols_data.items():
    print(f"\n{'='*80}")
    print(f"Testing {symbol_name}...")
    print(f"{'='*80}")

    symbol_results = []

    for i, params in enumerate(param_combinations, 1):
        result = backtest_symbol(df, symbol_name, params)

        if result:
            symbol_results.append(result)
            all_results.append(result)

        if i % 10 == 0:
            print(f"  Tested {i}/{len(param_combinations)} configs...")

    if symbol_results:
        # Sort by R/DD
        symbol_results.sort(key=lambda x: x['rdd'], reverse=True)

        print(f"\n🏆 TOP 5 CONFIGS FOR {symbol_name}:")
        print(f"\n{'Rank':<6} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'TP%':<8} {'Params'}")
        print("-" * 120)

        for rank, r in enumerate(symbol_results[:5], 1):
            params_str = f"ATR:{r['atr_mult']} EMA:{r['ema_dist']}% TP:{r['tp_mult']}x SL:{r['sl_mult']}x Off:{r['limit_offset']}%"
            print(f"{rank:<6} {r['trades']:<8} {r['return']:+9.1f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x {r['wr']:7.1f}% {r['tp_rate']:7.1f}% {params_str}")

# Final comparison
print("\n" + "=" * 80)
print("BEST CONFIG PER SYMBOL")
print("=" * 80)

df_results = pd.DataFrame(all_results)

for symbol_name in symbols_data.keys():
    symbol_results = df_results[df_results['symbol'] == symbol_name].sort_values('rdd', ascending=False)

    if not symbol_results.empty:
        best = symbol_results.iloc[0]

        print(f"\n{symbol_name}:")
        print(f"  Trades: {best['trades']:.0f} (from {best['signals']:.0f} signals, {best['fill_rate']:.1f}% fill)")
        print(f"  Return: {best['return']:+.2f}%")
        print(f"  Max DD: {best['dd']:.2f}%")
        print(f"  R/DD: {best['rdd']:.2f}x")
        print(f"  Win Rate: {best['wr']:.1f}%")
        print(f"  TP Rate: {best['tp_rate']:.1f}%")
        print(f"\n  Parameters:")
        print(f"    ATR expansion: > {best['atr_mult']}x")
        print(f"    EMA distance: < {best['ema_dist']}%")
        print(f"    Take Profit: {best['tp_mult']}x ATR")
        print(f"    Stop Loss: {best['sl_mult']}x ATR")
        print(f"    Limit offset: {best['limit_offset']}%")

# Compare with FARTCOIN
print("\n" + "=" * 80)
print("COMPARISON WITH FARTCOIN")
print("=" * 80)

fartcoin_stats = {
    'symbol': 'FARTCOIN',
    'trades': 28,
    'return': 98.83,
    'dd': -3.77,
    'rdd': 26.21,
    'wr': 53.6,
    'params': 'ATR:1.5 EMA:3.0% TP:8.0x SL:2.0x Off:1.0%'
}

comparison = []
comparison.append(fartcoin_stats)

for symbol_name in symbols_data.keys():
    symbol_results = df_results[df_results['symbol'] == symbol_name].sort_values('rdd', ascending=False)
    if not symbol_results.empty:
        best = symbol_results.iloc[0]
        comparison.append({
            'symbol': symbol_name,
            'trades': best['trades'],
            'return': best['return'],
            'dd': best['dd'],
            'rdd': best['rdd'],
            'wr': best['wr'],
            'params': f"ATR:{best['atr_mult']} EMA:{best['ema_dist']}% TP:{best['tp_mult']}x SL:{best['sl_mult']}x Off:{best['limit_offset']}%"
        })

df_comp = pd.DataFrame(comparison)
df_comp = df_comp.sort_values('rdd', ascending=False)

print(f"\n{'Symbol':<12} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8}")
print("-" * 70)

for _, row in df_comp.iterrows():
    print(f"{row['symbol']:<12} {row['trades']:<8.0f} {row['return']:+9.1f}% {row['dd']:9.2f}% {row['rdd']:7.2f}x {row['wr']:7.1f}%")

# Verdict
print("\n" + "=" * 80)
print("VERDICT")
print("=" * 80)

best_overall = df_comp.iloc[0]

if best_overall['symbol'] == 'FARTCOIN':
    print(f"\n✅ FARTCOIN remains the best performer ({best_overall['rdd']:.2f}x R/DD)")
    print(f"\nBTC/ETH results:")
    for symbol in ['BTC-USDT', 'ETH-USDT']:
        row = df_comp[df_comp['symbol'] == symbol]
        if not row.empty:
            row = row.iloc[0]
            print(f"  {symbol}: {row['rdd']:.2f}x R/DD ({row['trades']:.0f} trades, {row['return']:+.1f}%)")
else:
    print(f"\n⚠️ {best_overall['symbol']} outperforms FARTCOIN!")
    print(f"  {best_overall['rdd']:.2f}x R/DD vs FARTCOIN's 26.21x")

print("\n" + "=" * 80)

# Save results
df_results.to_csv('/workspaces/Carebiuro_windykacja/trading/results/btc_eth_strategy_results.csv', index=False)
print("\n✅ Results saved to: trading/results/btc_eth_strategy_results.csv")
