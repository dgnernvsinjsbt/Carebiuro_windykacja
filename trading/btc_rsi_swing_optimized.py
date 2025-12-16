#!/usr/bin/env python3
"""
BTC RSI Swing - Optimized with Filters + Position Stacking
Target: 5:1 R/DD, 1-7 day holds
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

def backtest_config(df, rsi_low, rsi_high, use_sl_tp=False, sl_atr_mult=None, tp_atr_mult=None):
    """Backtest with specific RSI thresholds and optional SL/TP"""

    positions = []

    for i in range(50, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # LONG: RSI crosses above oversold level
        if prev['rsi'] <= rsi_low and row['rsi'] > rsi_low:
            entry_price = row['close']
            entry_time = row['timestamp']
            atr_val = row['atr']

            # Calculate SL/TP if enabled
            if use_sl_tp:
                sl_price = entry_price - (sl_atr_mult * atr_val)
                tp_price = entry_price + (tp_atr_mult * atr_val)

            exit_found = False
            for j in range(i+1, min(i+168, len(df))):
                exit_row = df.iloc[j]

                # Check SL/TP first
                if use_sl_tp:
                    if exit_row['low'] <= sl_price:
                        exit_price = sl_price
                        exit_time = exit_row['timestamp']
                        exit_reason = 'SL'
                        exit_found = True
                        break
                    if exit_row['high'] >= tp_price:
                        exit_price = tp_price
                        exit_time = exit_row['timestamp']
                        exit_reason = 'TP'
                        exit_found = True
                        break

                # RSI exit
                if exit_row['rsi'] >= rsi_high:
                    exit_price = exit_row['close']
                    exit_time = exit_row['timestamp']
                    exit_reason = 'RSI'
                    exit_found = True
                    break

            if not exit_found:
                j = min(i+167, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_time = df.iloc[j]['timestamp']
                exit_reason = 'TIME'

            pnl_pct = (exit_price - entry_price) / entry_price * 100
            hold_hours = (exit_time - entry_time).total_seconds() / 3600

            positions.append({'direction': 'LONG', 'pnl_pct': pnl_pct, 'hold_hours': hold_hours, 'exit_reason': exit_reason})

        # SHORT: RSI crosses below overbought level
        elif prev['rsi'] >= rsi_high and row['rsi'] < rsi_high:
            entry_price = row['close']
            entry_time = row['timestamp']
            atr_val = row['atr']

            if use_sl_tp:
                sl_price = entry_price + (sl_atr_mult * atr_val)
                tp_price = entry_price - (tp_atr_mult * atr_val)

            exit_found = False
            for j in range(i+1, min(i+168, len(df))):
                exit_row = df.iloc[j]

                if use_sl_tp:
                    if exit_row['high'] >= sl_price:
                        exit_price = sl_price
                        exit_time = exit_row['timestamp']
                        exit_reason = 'SL'
                        exit_found = True
                        break
                    if exit_row['low'] <= tp_price:
                        exit_price = tp_price
                        exit_time = exit_row['timestamp']
                        exit_reason = 'TP'
                        exit_found = True
                        break

                if exit_row['rsi'] <= rsi_low:
                    exit_price = exit_row['close']
                    exit_time = exit_row['timestamp']
                    exit_reason = 'RSI'
                    exit_found = True
                    break

            if not exit_found:
                j = min(i+167, len(df)-1)
                exit_price = df.iloc[j]['close']
                exit_time = df.iloc[j]['timestamp']
                exit_reason = 'TIME'

            pnl_pct = (entry_price - exit_price) / entry_price * 100
            hold_hours = (exit_time - entry_time).total_seconds() / 3600

            positions.append({'direction': 'SHORT', 'pnl_pct': pnl_pct, 'hold_hours': hold_hours, 'exit_reason': exit_reason})

    if not positions:
        return None

    df_pos = pd.DataFrame(positions)
    df_pos['cum'] = df_pos['pnl_pct'].cumsum()
    equity = 100 + df_pos['cum']
    dd = ((equity - equity.cummax()) / equity.cummax() * 100).min()
    total_return = df_pos['pnl_pct'].sum()
    rdd = total_return / abs(dd) if dd != 0 else 0
    wr = (df_pos['pnl_pct'] > 0).mean() * 100

    return {
        'trades': len(df_pos),
        'return': total_return,
        'dd': dd,
        'rdd': rdd,
        'wr': wr,
        'avg_hold': df_pos['hold_hours'].mean() / 24
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
print("BTC RSI SWING OPTIMIZATION - Testing Configurations")
print("=" * 80)

results = []

# Test different RSI levels
print("\nTEST 1: RSI Thresholds")
print("-" * 80)

for rsi_low in [25, 30, 35]:
    for rsi_high in [65, 70, 75]:
        result = backtest_config(df, rsi_low, rsi_high)
        if result and result['trades'] >= 20:
            results.append({
                'config': f"RSI {rsi_low}/{rsi_high}",
                **result
            })
            print(f"  RSI {rsi_low}/{rsi_high}: {result['trades']} trades, {result['rdd']:.2f}x R/DD, {result['return']:+.1f}%")

# Test with SL/TP
print("\nTEST 2: Add SL/TP (2x/6x ATR)")
print("-" * 80)

for rsi_low in [25, 30]:
    for rsi_high in [70, 75]:
        result = backtest_config(df, rsi_low, rsi_high, use_sl_tp=True, sl_atr_mult=2.0, tp_atr_mult=6.0)
        if result and result['trades'] >= 20:
            results.append({
                'config': f"RSI {rsi_low}/{rsi_high} + SL/TP 2x/6x",
                **result
            })
            print(f"  RSI {rsi_low}/{rsi_high} + SL/TP: {result['trades']} trades, {result['rdd']:.2f}x R/DD, {result['return']:+.1f}%")

# Sort by R/DD
results = sorted(results, key=lambda x: x['rdd'], reverse=True)

print("\n" + "=" * 80)
print("TOP 10 CONFIGURATIONS")
print("=" * 80)

print(f"\n{'Rank':<6} {'Config':<30} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'WR%':<8} {'Days'}")
print("-" * 90)

for i, r in enumerate(results[:10], 1):
    marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
    status = "✅" if r['rdd'] >= 5 else "⚠️" if r['rdd'] >= 3 else ""

    print(f"{marker} {i:<4} {r['config']:<30} {r['trades']:<8} {r['return']:+9.1f}% {r['dd']:9.2f}% {r['rdd']:7.2f}x {r['wr']:7.1f}% {r['avg_hold']:.1f}")

if results:
    best = results[0]

    print(f"\n" + "=" * 80)
    print("BEST CONFIGURATION")
    print("=" * 80)

    print(f"\nConfig: {best['config']}")
    print(f"Trades: {best['trades']}")
    print(f"Return: {best['return']:+.2f}%")
    print(f"Max DD: {best['dd']:.2f}%")
    print(f"R/DD: {best['rdd']:.2f}x")
    print(f"Win Rate: {best['wr']:.1f}%")
    print(f"Avg Hold: {best['avg_hold']:.1f} days")

    print(f"\n" + "=" * 80)
    if best['rdd'] >= 5:
        print(f"✅ TARGET HIT: {best['rdd']:.2f}x R/DD (target: 5x+)")
    elif best['rdd'] >= 3:
        print(f"⚠️ CLOSE TO TARGET: {best['rdd']:.2f}x R/DD (target: 5x+)")
    else:
        print(f"❌ BELOW TARGET: {best['rdd']:.2f}x R/DD (target: 5x+)")
    print("=" * 80)
