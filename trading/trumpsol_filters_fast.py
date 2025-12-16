#!/usr/bin/env python3
"""
Fast TRUMPSOL filter test - Volume + ATR strength
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

def backtest(df, atr_mult, volume_min=None, trend_filter=False):
    df = df.copy()

    # Indicators
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
    df['atr_ma'] = df['atr'].rolling(20).mean()
    df['atr_ratio'] = df['atr'] / df['atr_ma']
    df['ema20'] = calculate_ema(df['close'], 20)
    df['distance'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)
    df['bullish'] = df['close'] > df['open']
    df['above_ema'] = df['close'] > df['ema20']
    df['volume_ma'] = df['volume'].rolling(30).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']

    # Daily RSI
    df_daily = df.set_index('timestamp').resample('1D').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    df_daily['rsi_daily'] = calculate_rsi(df_daily['close'], 14)

    df = df.set_index('timestamp').join(df_daily[['rsi_daily']], how='left').ffill().reset_index()

    # Generate signals
    signals = []
    for i in range(len(df)):
        row = df.iloc[i]

        if (row['atr_ratio'] > atr_mult and
            row['distance'] < 2.0 and
            row['bullish'] and
            not pd.isna(row['rsi_daily']) and
            row['rsi_daily'] > 50):

            if volume_min and row['volume_ratio'] < volume_min:
                continue
            if trend_filter and not row['above_ema']:
                continue

            signals.append(i)

    if not signals:
        return None

    # Backtest trades
    trades = []
    for signal_idx in signals:
        if signal_idx >= len(df) - 1:
            continue

        signal_price = df['close'].iloc[signal_idx]
        signal_atr = df['atr'].iloc[signal_idx]
        if pd.isna(signal_atr) or signal_atr == 0:
            continue

        limit_price = signal_price * 1.005
        filled = False
        fill_idx = None

        for i in range(signal_idx + 1, min(signal_idx + 4, len(df))):
            if df['high'].iloc[i] >= limit_price:
                filled = True
                fill_idx = i
                break

        if not filled:
            continue

        entry_atr = df['atr'].iloc[fill_idx]
        sl_price = limit_price - (1.5 * entry_atr)
        tp_price = limit_price + (8.0 * entry_atr)

        for i in range(fill_idx + 1, min(fill_idx + 200, len(df))):
            if df['low'].iloc[i] <= sl_price:
                pnl_pct = (sl_price - limit_price) / limit_price * 100 - 0.10
                trades.append(pnl_pct)
                break
            if df['high'].iloc[i] >= tp_price:
                pnl_pct = (tp_price - limit_price) / limit_price * 100 - 0.10
                trades.append(pnl_pct)
                break
        else:
            exit_price = df['close'].iloc[min(fill_idx + 199, len(df) - 1)]
            pnl_pct = (exit_price - limit_price) / limit_price * 100 - 0.10
            trades.append(pnl_pct)

    if not trades:
        return None

    cum = pd.Series(trades).cumsum()
    equity = 100 + cum
    dd = ((equity - equity.cummax()) / equity.cummax() * 100).min()
    total_return = sum(trades)
    rdd = total_return / abs(dd) if dd != 0 else 0

    return {
        'trades': len(trades),
        'return': total_return,
        'dd': dd,
        'rdd': rdd,
        'wr': sum(1 for t in trades if t > 0) / len(trades) * 100
    }

# Load data
df = pd.read_csv('trumpsol_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("TRUMPSOL LOGICAL FILTERS - Volume + ATR Strength")
print("=" * 80)

results = []

# Baseline
print("\nBASELINE:")
baseline = backtest(df, 1.5)
if baseline:
    print(f"  ATR 1.5x → {baseline['trades']} trades, {baseline['rdd']:.2f}x R/DD, {baseline['return']:+.1f}%, DD {baseline['dd']:.2f}%")

# Test ATR thresholds
print("\nATR THRESHOLD:")
for atr in [1.6, 1.7, 1.8, 2.0]:
    r = backtest(df, atr)
    if r and r['trades'] >= 20:
        results.append(('ATR', atr, None, False, r))
        print(f"  ATR {atr}x → {r['trades']} trades, {r['rdd']:.2f}x R/DD, WR {r['wr']:.1f}%")

# Test Volume filters
print("\nVOLUME FILTER:")
for vol in [1.1, 1.2, 1.3, 1.4]:
    r = backtest(df, 1.5, volume_min=vol)
    if r and r['trades'] >= 20:
        results.append(('VOL', 1.5, vol, False, r))
        print(f"  ATR 1.5x + Vol>={vol}x → {r['trades']} trades, {r['rdd']:.2f}x R/DD, WR {r['wr']:.1f}%")

# Test Trend filter
print("\nTREND FILTER:")
r = backtest(df, 1.5, trend_filter=True)
if r and r['trades'] >= 20:
    results.append(('TREND', 1.5, None, True, r))
    print(f"  ATR 1.5x + Trend → {r['trades']} trades, {r['rdd']:.2f}x R/DD, WR {r['wr']:.1f}%")

# Test combos
print("\nCOMBINATIONS:")
for atr in [1.5, 1.6, 1.7]:
    for vol in [1.1, 1.2, 1.3]:
        r = backtest(df, atr, volume_min=vol)
        if r and r['trades'] >= 20:
            results.append(('COMBO', atr, vol, False, r))
            print(f"  ATR {atr}x + Vol>={vol}x → {r['trades']} trades, {r['rdd']:.2f}x R/DD")

# Triple combo
for atr in [1.5, 1.6]:
    for vol in [1.1, 1.2]:
        r = backtest(df, atr, volume_min=vol, trend_filter=True)
        if r and r['trades'] >= 15:
            results.append(('TRIPLE', atr, vol, True, r))
            print(f"  ATR {atr}x + Vol>={vol}x + Trend → {r['trades']} trades, {r['rdd']:.2f}x R/DD")

# Sort and show top results
if results:
    results = sorted(results, key=lambda x: x[4]['rdd'], reverse=True)

    print(f"\n" + "=" * 80)
    print("TOP RESULTS (20+ trades)")
    print("=" * 80)

    print(f"\n{'Rank':<6} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'Config'}")
    print("-" * 80)

    for i, (ftype, atr, vol, trend, r) in enumerate([x for x in results if x[4]['trades'] >= 20][:10], 1):
        config = f"ATR {atr}x"
        if vol:
            config += f" + Vol>={vol}x"
        if trend:
            config += " + Trend"

        marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        status = "✅" if r['rdd'] >= 5 else ""

        print(f"{marker} {i:<4} {r['trades']:<8} {r['return']:+9.1f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x {r['wr']:7.1f}% {config} {status}")

    best = results[0]
    print(f"\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    if best[4]['rdd'] >= 10:
        print(f"\n✅ TRUMPSOL VIABLE at {best[4]['rdd']:.2f}x R/DD (10x+ threshold)")
    elif best[4]['rdd'] >= 5:
        print(f"\n⚠️ TRUMPSOL ACCEPTABLE at {best[4]['rdd']:.2f}x R/DD (5x+ threshold)")
        print(f"   Logical filters (Volume/ATR strength) = replicable edge")
    else:
        print(f"\n❌ TRUMPSOL below 5x threshold at {best[4]['rdd']:.2f}x R/DD")

    print("=" * 80)

else:
    print("\n❌ No configs with 20+ trades found")
