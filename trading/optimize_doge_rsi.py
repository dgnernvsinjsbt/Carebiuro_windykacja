#!/usr/bin/env python3
"""Optimize DOGE RSI thresholds to reach 5x R/DD target"""

import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def backtest_rsi(df, rsi_low, rsi_high, atr_mult=2.0):
    """Backtest RSI strategy with compounding"""

    df = df.copy()
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)

    trades = []
    equity = 100.0

    for i in range(50, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # LONG
        if prev['rsi'] <= rsi_low and row['rsi'] > rsi_low:
            entry_price = row['close']
            entry_time = row['timestamp']
            sl_price = entry_price - (atr_mult * row['atr'])

            exit_found = False
            for j in range(i+1, min(i+168, len(df))):
                exit_row = df.iloc[j]
                if exit_row['low'] <= sl_price:
                    exit_price = sl_price
                    exit_time = exit_row['timestamp']
                    exit_reason = 'SL'
                    exit_found = True
                    break
                if exit_row['rsi'] >= rsi_high:
                    exit_price = exit_row['close']
                    exit_time = exit_row['timestamp']
                    exit_reason = 'TP'
                    exit_found = True
                    break

            if not exit_found:
                j = min(i+167, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_time = df.iloc[j]['timestamp']
                exit_reason = 'TIME'

            pnl_pct = (exit_price - entry_price) / entry_price * 100
            equity *= (1 + pnl_pct / 100)
            trades.append({'pnl_pct': pnl_pct, 'equity': equity, 'exit_reason': exit_reason})

        # SHORT
        elif prev['rsi'] >= rsi_high and row['rsi'] < rsi_high:
            entry_price = row['close']
            sl_price = entry_price + (atr_mult * row['atr'])

            exit_found = False
            for j in range(i+1, min(i+168, len(df))):
                exit_row = df.iloc[j]
                if exit_row['high'] >= sl_price:
                    exit_price = sl_price
                    exit_reason = 'SL'
                    exit_found = True
                    break
                if exit_row['rsi'] <= rsi_low:
                    exit_price = exit_row['close']
                    exit_reason = 'TP'
                    exit_found = True
                    break

            if not exit_found:
                j = min(i+167, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_reason = 'TIME'

            pnl_pct = (entry_price - exit_price) / entry_price * 100
            equity *= (1 + pnl_pct / 100)
            trades.append({'pnl_pct': pnl_pct, 'equity': equity, 'exit_reason': exit_reason})

    if not trades:
        return None

    df_t = pd.DataFrame(trades)
    equity_series = pd.Series([t['equity'] for t in trades])
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max * 100

    total_return = equity - 100
    max_dd = drawdown.min()
    rdd = total_return / abs(max_dd) if max_dd != 0 else 0

    return {
        'rsi_low': rsi_low,
        'rsi_high': rsi_high,
        'trades': len(df_t),
        'return': total_return,
        'dd': max_dd,
        'rdd': rdd,
        'wr': (df_t['pnl_pct'] > 0).mean() * 100,
        'tp_rate': (df_t['exit_reason'] == 'TP').mean() * 100
    }

# Load DOGE data
df = pd.read_csv('doge_1h_90d.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("DOGE RSI THRESHOLD OPTIMIZATION")
print("=" * 80)
print(f"\nData: {len(df):,} candles | {df['timestamp'].min()} to {df['timestamp'].max()}")

# Test RSI threshold combinations
print(f"\n" + "-" * 80)
print("TESTING RSI THRESHOLDS")
print("-" * 80)

results = []

# Test different RSI high thresholds (keep low at 30)
for rsi_high in [62, 63, 64, 65, 66, 67, 68, 70, 72]:
    result = backtest_rsi(df, rsi_low=30, rsi_high=rsi_high, atr_mult=2.0)
    if result:
        results.append(result)

# Test different RSI low thresholds (keep high at 65)
for rsi_low in [25, 27, 28, 32, 33, 35]:
    result = backtest_rsi(df, rsi_low=rsi_low, rsi_high=65, atr_mult=2.0)
    if result:
        results.append(result)

# Sort by R/DD
results = sorted(results, key=lambda x: x['rdd'], reverse=True)

print(f"\n{'Rank':<6} {'RSI Low':<10} {'RSI High':<10} {'Trades':<8} {'Return':<12} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'TP%'}")
print("-" * 95)

for i, r in enumerate(results[:15], 1):
    marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
    status = "✅" if r['rdd'] >= 5 else "⚠️" if r['rdd'] >= 4.5 else ""

    print(f"{marker} {i:<4} {r['rsi_low']:<10} {r['rsi_high']:<10} {r['trades']:<8} {r['return']:+11.2f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x {r['wr']:7.1f}% {r['tp_rate']:6.1f}% {status}")

best = results[0]
baseline = [r for r in results if r['rsi_low'] == 30 and r['rsi_high'] == 65][0]

print(f"\n" + "=" * 80)
print("BEST CONFIGURATION vs BASELINE")
print("=" * 80)

print(f"\nBaseline (RSI 30/65):")
print(f"  {baseline['trades']} trades, {baseline['return']:+.2f}% return, {baseline['dd']:.2f}% DD, {baseline['rdd']:.2f}x R/DD")

print(f"\nBest (RSI {best['rsi_low']}/{best['rsi_high']}):")
print(f"  {best['trades']} trades, {best['return']:+.2f}% return, {best['dd']:.2f}% DD, {best['rdd']:.2f}x R/DD")

improvement = (best['rdd'] - baseline['rdd']) / baseline['rdd'] * 100
print(f"\nImprovement: {improvement:+.1f}% better R/DD")

print(f"\n" + "=" * 80)
if best['rdd'] >= 5:
    print(f"✅ TARGET HIT: {best['rdd']:.2f}x R/DD with RSI {best['rsi_low']}/{best['rsi_high']}")
elif best['rdd'] >= 4.5:
    print(f"⚠️ VERY CLOSE: {best['rdd']:.2f}x R/DD (target: 5x+)")
else:
    print(f"❌ BELOW TARGET: {best['rdd']:.2f}x R/DD (target: 5x+)")
print("=" * 80)
