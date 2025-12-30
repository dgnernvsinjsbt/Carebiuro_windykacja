#!/usr/bin/env python3
"""
Optimize EMA Crossover Strategy for NASDAQ100 Futures
"""

import pandas as pd
import numpy as np
from itertools import product

# Load data
df = pd.read_csv('/home/user/Carebiuro_windykacja/trading/nasdaq_nq_futures_1h_2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Pre-calculate indicators
df['tr'] = np.maximum(df['high'] - df['low'],
                      np.maximum(abs(df['high'] - df['close'].shift(1)),
                                abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()

FEE_PCT = 0.01  # Futures fees

def run_backtest(df, ema_fast, ema_slow, tp_atr, sl_atr, offset_atr, max_wait=20):
    # Calculate EMAs
    df = df.copy()
    df['ema_fast'] = df['close'].ewm(span=ema_fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=ema_slow, adjust=False).mean()
    df['ema_fast_prev'] = df['ema_fast'].shift(1)
    df['ema_slow_prev'] = df['ema_slow'].shift(1)
    df['long_signal'] = (df['ema_fast'] > df['ema_slow']) & (df['ema_fast_prev'] <= df['ema_slow_prev'])
    df['short_signal'] = (df['ema_fast'] < df['ema_slow']) & (df['ema_fast_prev'] >= df['ema_slow_prev'])

    equity = 100.0
    max_equity = 100.0
    max_dd = 0.0
    trades = 0
    wins = 0
    position = None
    pending = None

    for i in range(max(ema_slow, 21), len(df)):
        row = df.iloc[i]

        if pending is not None:
            bars = i - pending['bar']
            filled = False
            if pending['side'] == 'LONG' and row['low'] <= pending['limit']:
                filled = True
                entry = pending['limit']
            elif pending['side'] == 'SHORT' and row['high'] >= pending['limit']:
                filled = True
                entry = pending['limit']

            if filled:
                position = {'side': pending['side'], 'entry': entry, 'tp': pending['tp'], 'sl': pending['sl']}
                pending = None
            elif bars >= max_wait:
                pending = None

        if position is not None:
            exit_price = None
            if position['side'] == 'LONG':
                if row['high'] >= position['tp']:
                    exit_price = position['tp']
                    win = True
                elif row['low'] <= position['sl']:
                    exit_price = position['sl']
                    win = False
            else:
                if row['low'] <= position['tp']:
                    exit_price = position['tp']
                    win = True
                elif row['high'] >= position['sl']:
                    exit_price = position['sl']
                    win = False

            if exit_price is not None:
                if position['side'] == 'LONG':
                    pnl = (exit_price - position['entry']) / position['entry'] * 100
                else:
                    pnl = (position['entry'] - exit_price) / position['entry'] * 100
                pnl -= FEE_PCT * 2
                equity *= (1 + pnl/100)
                max_equity = max(max_equity, equity)
                dd = (equity - max_equity) / max_equity * 100
                max_dd = min(max_dd, dd)
                trades += 1
                if win:
                    wins += 1
                position = None

        if position is None and pending is None:
            atr = row['atr']
            price = row['close']
            if row['long_signal']:
                pending = {
                    'side': 'LONG', 'bar': i,
                    'limit': price - offset_atr * atr,
                    'tp': price + tp_atr * atr,
                    'sl': price - sl_atr * atr
                }
            elif row['short_signal']:
                pending = {
                    'side': 'SHORT', 'bar': i,
                    'limit': price + offset_atr * atr,
                    'tp': price - tp_atr * atr,
                    'sl': price + sl_atr * atr
                }

    ret = equity - 100
    rr = ret / abs(max_dd) if max_dd != 0 else 0
    win_rate = wins / trades * 100 if trades > 0 else 0
    return ret, max_dd, rr, trades, win_rate

# Parameter grid
ema_pairs = [(5, 13), (8, 21), (12, 26), (5, 21)]
tp_range = [2, 3, 4, 5]  # Smaller TPs for equities
sl_range = [1, 1.5, 2, 3]  # Tighter SLs
offset_range = [0.3, 0.5, 0.7]

results = []

print("=" * 80)
print("NASDAQ100 FUTURES - EMA CROSSOVER OPTIMIZATION")
print("=" * 80)
print(f"{'EMA':>8} {'Off':>5} {'TP':>5} {'SL':>5} {'Return':>10} {'MaxDD':>10} {'R:R':>8} {'Trades':>8} {'Win%':>8}")
print("-" * 80)

for (ema_f, ema_s), offset, tp, sl in product(ema_pairs, offset_range, tp_range, sl_range):
    ret, dd, rr, trades, win_rate = run_backtest(df, ema_f, ema_s, tp, sl, offset)
    results.append({
        'ema': f"{ema_f}/{ema_s}", 'offset': offset, 'tp': tp, 'sl': sl,
        'return': ret, 'max_dd': dd, 'rr': rr, 'trades': trades, 'win_rate': win_rate
    })

# Sort by R:R
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('rr', ascending=False)

# Show top 15
for _, r in results_df.head(15).iterrows():
    print(f"{r['ema']:>8} {r['offset']:>5.1f} {r['tp']:>5.0f} {r['sl']:>5.1f} {r['return']:>+9.2f}% {r['max_dd']:>9.2f}% {r['rr']:>7.2f}x {r['trades']:>8.0f} {r['win_rate']:>7.1f}%")

print("-" * 80)
best = results_df.iloc[0]
print(f"\n🏆 BEST: EMA {best['ema']}, Offset {best['offset']}, TP {best['tp']}, SL {best['sl']}")
print(f"   → {best['return']:+.2f}%, {best['rr']:.2f}x R:R, {best['trades']:.0f} trades")

# Compare to FARTCOIN
print("\n" + "=" * 80)
print("COMPARISON: NASDAQ vs FARTCOIN")
print("=" * 80)
print(f"{'Metric':<20} {'FARTCOIN':>15} {'NASDAQ (best)':>15}")
print("-" * 80)
print(f"{'Return':<20} {'+2232%':>15} {best['return']:>+14.2f}%")
print(f"{'R:R Ratio':<20} {'124.98x':>15} {best['rr']:>14.2f}x")
print(f"{'Win Rate':<20} {'67.7%':>15} {best['win_rate']:>14.1f}%")
print("=" * 80)
