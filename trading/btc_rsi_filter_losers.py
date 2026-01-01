#!/usr/bin/env python3
"""
BTC RSI 30/65 - Filter out losers based on analysis
Key insight: Losers hold 3x longer (45h vs 15h)
"""

import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def backtest_with_filters(df, max_hold_hours=None, trend_filter=False, use_atr_stop=False):
    """Backtest RSI 30/65 with filters"""

    trades = []

    for i in range(200, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # LONG signal
        if prev['rsi'] <= 30 and row['rsi'] > 30:
            # Trend filter
            if trend_filter and row['close'] < row['ema50']:
                continue

            entry_price = row['close']
            entry_time = row['timestamp']
            atr_val = row['atr']

            # Calculate ATR stop if enabled
            if use_atr_stop:
                sl_price = entry_price - (2.0 * atr_val)

            # Find exit
            max_bars = int((max_hold_hours or 168) / 1)  # 1h bars
            exit_found = False

            for j in range(i+1, min(i+max_bars, len(df))):
                exit_row = df.iloc[j]

                # ATR stop check
                if use_atr_stop and exit_row['low'] <= sl_price:
                    exit_price = sl_price
                    exit_time = exit_row['timestamp']
                    exit_reason = 'SL'
                    exit_found = True
                    break

                # RSI exit
                if exit_row['rsi'] >= 65:
                    exit_price = exit_row['close']
                    exit_time = exit_row['timestamp']
                    exit_reason = 'RSI'
                    exit_found = True
                    break

            if not exit_found:
                j = min(i+max_bars-1, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_time = df.iloc[j]['timestamp']
                exit_reason = 'TIME'

            pnl_pct = (exit_price - entry_price) / entry_price * 100
            hold_hours = (exit_time - entry_time).total_seconds() / 3600

            trades.append({
                'direction': 'LONG',
                'pnl_pct': pnl_pct,
                'hold_hours': hold_hours,
                'exit_reason': exit_reason
            })

        # SHORT signal
        elif prev['rsi'] >= 65 and row['rsi'] < 65:
            if trend_filter and row['close'] > row['ema50']:
                continue

            entry_price = row['close']
            entry_time = row['timestamp']
            atr_val = row['atr']

            if use_atr_stop:
                sl_price = entry_price + (2.0 * atr_val)

            max_bars = int((max_hold_hours or 168) / 1)
            exit_found = False

            for j in range(i+1, min(i+max_bars, len(df))):
                exit_row = df.iloc[j]

                if use_atr_stop and exit_row['high'] >= sl_price:
                    exit_price = sl_price
                    exit_time = exit_row['timestamp']
                    exit_reason = 'SL'
                    exit_found = True
                    break

                if exit_row['rsi'] <= 30:
                    exit_price = exit_row['close']
                    exit_time = exit_row['timestamp']
                    exit_reason = 'RSI'
                    exit_found = True
                    break

            if not exit_found:
                j = min(i+max_bars-1, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_time = df.iloc[j]['timestamp']
                exit_reason = 'TIME'

            pnl_pct = (entry_price - exit_price) / entry_price * 100
            hold_hours = (exit_time - entry_time).total_seconds() / 3600

            trades.append({
                'direction': 'SHORT',
                'pnl_pct': pnl_pct,
                'hold_hours': hold_hours,
                'exit_reason': exit_reason
            })

    if not trades:
        return None

    df_t = pd.DataFrame(trades)
    df_t['cum'] = df_t['pnl_pct'].cumsum()
    equity = 100 + df_t['cum']
    dd = ((equity - equity.cummax()) / equity.cummax() * 100).min()
    total_return = df_t['pnl_pct'].sum()
    rdd = total_return / abs(dd) if dd != 0 else 0

    return {
        'trades': len(df_t),
        'return': total_return,
        'dd': dd,
        'rdd': rdd,
        'wr': (df_t['pnl_pct'] > 0).mean() * 100,
        'avg_hold': df_t['hold_hours'].mean()
    }

# Load data
df = pd.read_csv('btc_1h_90d.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
df['rsi'] = calculate_rsi(df['close'], 14)
df['ema50'] = calculate_ema(df['close'], 50)
df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)

print("=" * 80)
print("BTC RSI 30/65 - FILTER OPTIMIZATION")
print("=" * 80)

results = []

# Baseline
baseline = backtest_with_filters(df)
print(f"\nBASELINE (no filters):")
print(f"  {baseline['trades']} trades, {baseline['rdd']:.2f}x R/DD, {baseline['return']:+.1f}%, {baseline['avg_hold']:.1f}h hold")
results.append(('Baseline', baseline))

# Test 1: Max hold time (since losers hold 3x longer)
print(f"\n" + "-" * 80)
print("FILTER 1: Max Hold Time (cut losers early)")
print("-" * 80)

for max_hold in [24, 30, 36, 48]:
    result = backtest_with_filters(df, max_hold_hours=max_hold)
    if result:
        improvement = (result['rdd'] - baseline['rdd']) / baseline['rdd'] * 100
        results.append((f'MaxHold {max_hold}h', result))
        print(f"  Max {max_hold}h: {result['trades']} trades, {result['rdd']:.2f}x R/DD ({improvement:+.1f}%), {result['avg_hold']:.1f}h")

# Test 2: Trend filter (only trade with EMA50)
print(f"\n" + "-" * 80)
print("FILTER 2: Trend Alignment (LONG above EMA50, SHORT below)")
print("-" * 80)

result = backtest_with_filters(df, trend_filter=True)
if result:
    improvement = (result['rdd'] - baseline['rdd']) / baseline['rdd'] * 100
    results.append(('Trend Filter', result))
    print(f"  Trend Filter: {result['trades']} trades, {result['rdd']:.2f}x R/DD ({improvement:+.1f}%)")

# Test 3: ATR stop (2x ATR)
print(f"\n" + "-" * 80)
print("FILTER 3: ATR Stop Loss (2x ATR)")
print("-" * 80)

result = backtest_with_filters(df, use_atr_stop=True)
if result:
    improvement = (result['rdd'] - baseline['rdd']) / baseline['rdd'] * 100
    results.append(('ATR Stop', result))
    print(f"  ATR Stop: {result['trades']} trades, {result['rdd']:.2f}x R/DD ({improvement:+.1f}%)")

# Test 4: Combinations
print(f"\n" + "-" * 80)
print("FILTER 4: COMBINATIONS")
print("-" * 80)

# Max hold + Trend
result = backtest_with_filters(df, max_hold_hours=30, trend_filter=True)
if result:
    results.append(('MaxHold 30h + Trend', result))
    print(f"  MaxHold 30h + Trend: {result['trades']} trades, {result['rdd']:.2f}x R/DD")

# Max hold + ATR stop
result = backtest_with_filters(df, max_hold_hours=30, use_atr_stop=True)
if result:
    results.append(('MaxHold 30h + ATR Stop', result))
    print(f"  MaxHold 30h + ATR Stop: {result['trades']} trades, {result['rdd']:.2f}x R/DD")

# All 3
result = backtest_with_filters(df, max_hold_hours=30, trend_filter=True, use_atr_stop=True)
if result:
    results.append(('All 3 Filters', result))
    print(f"  All 3 Filters: {result['trades']} trades, {result['rdd']:.2f}x R/DD")

# Sort by R/DD
results = sorted(results, key=lambda x: x[1]['rdd'], reverse=True)

print(f"\n" + "=" * 80)
print("TOP RESULTS")
print("=" * 80)

print(f"\n{'Rank':<6} {'Config':<30} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'Hold(h)'}")
print("-" * 95)

for i, (name, r) in enumerate(results[:10], 1):
    marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
    status = "✅" if r['rdd'] >= 5 else "⚠️" if r['rdd'] >= 4 else ""

    print(f"{marker} {i:<4} {name:<30} {r['trades']:<8} {r['return']:+9.1f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x {r['wr']:7.1f}% {r['avg_hold']:7.1f} {status}")

best = results[0]

print(f"\n" + "=" * 80)
print("BEST CONFIGURATION")
print("=" * 80)

print(f"\nConfig: {results[0][0]}")
print(f"Trades: {best['trades']}")
print(f"Return: {best['return']:+.2f}%")
print(f"Max DD: {best['dd']:.2f}%")
print(f"R/DD: {best['rdd']:.2f}x")
print(f"Win Rate: {best['wr']:.1f}%")
print(f"Avg Hold: {best['avg_hold']:.1f}h ({best['avg_hold']/24:.1f} days)")

improvement = (best['rdd'] - baseline['rdd']) / baseline['rdd'] * 100

print(f"\nImprovement vs baseline: {improvement:+.1f}%")
print(f"Baseline R/DD: {baseline['rdd']:.2f}x → Best R/DD: {best['rdd']:.2f}x")

print(f"\n" + "=" * 80)
if best['rdd'] >= 5:
    print(f"✅ TARGET HIT: {best['rdd']:.2f}x R/DD (target: 5x+)")
elif best['rdd'] >= 4.5:
    print(f"⚠️ VERY CLOSE: {best['rdd']:.2f}x R/DD (target: 5x+)")
else:
    print(f"❌ BELOW TARGET: {best['rdd']:.2f}x R/DD (target: 5x+)")
print("=" * 80)
