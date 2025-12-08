#!/usr/bin/env python3
"""PEPE/USDT Fast Strategy Test - Core strategies only"""

import pandas as pd
import numpy as np
import sys

print("Loading data...", flush=True)
df = pd.read_csv('pepe_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Loaded {len(df)} candles", flush=True)
print(f"Date range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}", flush=True)

# Fast indicator calculation
print("Calculating indicators...", flush=True)
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

df['ema_9'] = df['close'].ewm(span=9).mean()
df['ema_20'] = df['close'].ewm(span=20).mean()

delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
df['rsi'] = 100 - (100 / (1 + gain / loss))

high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.rolling(14).mean()

df = df.dropna().reset_index(drop=True)
print(f"After indicators: {len(df)} candles\n", flush=True)


def backtest(entry, name, fee=0.1, sl_mult=2.0, tp_mult=4.0):
    """Ultra-fast backtest"""
    trades = []
    pos = None

    for i in range(len(df)):
        r = df.iloc[i]

        if pos is None and entry.iloc[i]:
            pos = {
                'entry': r['close'],
                'sl': r['close'] - r['atr'] * sl_mult,
                'tp': r['close'] + r['atr'] * tp_mult,
                'idx': i
            }
        elif pos is not None:
            if r['low'] <= pos['sl']:
                pnl = ((pos['sl'] / pos['entry']) - 1) * 100 - fee
                trades.append(pnl)
                pos = None
            elif r['high'] >= pos['tp']:
                pnl = ((pos['tp'] / pos['entry']) - 1) * 100 - fee
                trades.append(pnl)
                pos = None

    if len(trades) < 30:
        return None

    total = sum(trades)
    wins = [t for t in trades if t > 0]
    wr = len(wins) / len(trades) * 100

    cum = np.cumsum(trades)
    dd = min(cum - np.maximum.accumulate(cum))
    rr = total / abs(dd) if dd < 0 else 0

    return {
        'name': name,
        'trades': len(trades),
        'wr': wr,
        'pnl': total,
        'dd': abs(dd),
        'rr': rr
    }


results = []

print("Testing strategies...\n", flush=True)

# 1. BB Mean Reversion
print("[1] BB Mean Reversion", flush=True)
entry = df['close'] < df['bb_lower']
for sl, tp in [(1.5, 3), (2, 4), (2.5, 5), (3, 6)]:
    r = backtest(entry, f"BB_MR_ATR{sl}x{tp}", sl_mult=sl, tp_mult=tp)
    if r:
        results.append(r)
        print(f"  {sl}x{tp}: {r['trades']} trades, WR={r['wr']:.1f}%, PnL={r['pnl']:.1f}%, R:R={r['rr']:.2f}", flush=True)

# 2. EMA Crossover
print("\n[2] EMA Crossover", flush=True)
entry = (df['ema_9'] > df['ema_20']) & (df['ema_9'].shift(1) <= df['ema_20'].shift(1))
for sl, tp in [(2, 4), (2.5, 5), (3, 6)]:
    r = backtest(entry, f"EMA9_20_ATR{sl}x{tp}", sl_mult=sl, tp_mult=tp)
    if r:
        results.append(r)
        print(f"  {sl}x{tp}: {r['trades']} trades, WR={r['wr']:.1f}%, PnL={r['pnl']:.1f}%, R:R={r['rr']:.2f}", flush=True)

# 3. RSI Oversold
print("\n[3] RSI Oversold", flush=True)
for thresh in [20, 25, 30]:
    entry = df['rsi'] < thresh
    r = backtest(entry, f"RSI<{thresh}_ATR2x4", sl_mult=2, tp_mult=4)
    if r:
        results.append(r)
        print(f"  RSI<{thresh}: {r['trades']} trades, WR={r['wr']:.1f}%, PnL={r['pnl']:.1f}%, R:R={r['rr']:.2f}", flush=True)

# 4. EMA + RSI Pullback
print("\n[4] EMA + RSI Pullback", flush=True)
entry = (df['close'] > df['ema_20']) & (df['rsi'] < 30)
for sl, tp in [(2, 4), (2.5, 5), (3, 6)]:
    r = backtest(entry, f"EMA_RSI_ATR{sl}x{tp}", sl_mult=sl, tp_mult=tp)
    if r:
        results.append(r)
        print(f"  {sl}x{tp}: {r['trades']} trades, WR={r['wr']:.1f}%, PnL={r['pnl']:.1f}%, R:R={r['rr']:.2f}", flush=True)

# 5. Limit orders (lower fees)
print("\n[5] BB with Limit Orders (0.07% fee)", flush=True)
entry = df['close'] < df['bb_lower']
for sl, tp in [(2, 4), (2.5, 5), (3, 6)]:
    r = backtest(entry, f"BB_Limit_ATR{sl}x{tp}", fee=0.07, sl_mult=sl, tp_mult=tp)
    if r:
        results.append(r)
        print(f"  {sl}x{tp}: {r['trades']} trades, WR={r['wr']:.1f}%, PnL={r['pnl']:.1f}%, R:R={r['rr']:.2f}", flush=True)

# Save and display results
if results:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('rr', ascending=False)
    results_df.to_csv('results/pepe_fast_results.csv', index=False)

    print(f"\n{'=' * 80}", flush=True)
    print(f"TESTED {len(results)} STRATEGIES", flush=True)
    print(f"{'=' * 80}\n", flush=True)

    print("TOP 10 BY R:R RATIO:", flush=True)
    for i, r in results_df.head(10).iterrows():
        print(f"\n{r['name']}", flush=True)
        print(f"  Trades: {r['trades']} | WR: {r['wr']:.1f}%", flush=True)
        print(f"  PnL: {r['pnl']:.1f}% | DD: {r['dd']:.1f}% | R:R: {r['rr']:.2f}", flush=True)

    profitable = results_df[results_df['rr'] >= 2.0]
    if len(profitable) > 0:
        print(f"\n{'=' * 80}", flush=True)
        print(f"STRATEGIES WITH R:R >= 2.0: {len(profitable)}", flush=True)
        print(f"{'=' * 80}", flush=True)
        for i, r in profitable.iterrows():
            print(f"  {r['name']}: R:R={r['rr']:.2f}, PnL={r['pnl']:.1f}%", flush=True)

        best = profitable.iloc[0]
        print(f"\n{'=' * 80}", flush=True)
        print("BEST STRATEGY:", flush=True)
        print(f"{'=' * 80}", flush=True)
        print(f"Name: {best['name']}", flush=True)
        print(f"Trades: {best['trades']}", flush=True)
        print(f"Win Rate: {best['wr']:.1f}%", flush=True)
        print(f"Total PnL: {best['pnl']:.1f}%", flush=True)
        print(f"Max DD: {best['dd']:.1f}%", flush=True)
        print(f"R:R Ratio: {best['rr']:.2f}", flush=True)
    else:
        print(f"\n{'=' * 80}", flush=True)
        print("NO STRATEGIES WITH R:R >= 2.0", flush=True)
        print(f"Best: {results_df.iloc[0]['name']} with R:R={results_df.iloc[0]['rr']:.2f}", flush=True)
        print(f"{'=' * 80}", flush=True)
else:
    print("No strategies produced 30+ trades", flush=True)

print("\nDone!", flush=True)
