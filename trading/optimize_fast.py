#!/usr/bin/env python3
"""
FAST optimization - key parameters only
"""
import pandas as pd
import numpy as np
import pickle
from numba import jit
import warnings
warnings.filterwarnings('ignore')

print('Loading cached data...')
with open('trading/cache/listings_2025_data.pkl', 'rb') as f:
    data = pickle.load(f)
print(f'Loaded {len(data)} coins')

# Pre-convert to numpy for speed
print('Converting to numpy arrays...')
coin_arrays = {}
for symbol, cd in data.items():
    df = cd['df']
    if len(df) >= 60:
        coin_arrays[symbol] = {
            'close': df['close'].values,
            'high': df['high'].values,
            'low': df['low'].values,
            'lp': cd['listing_price']
        }
print(f'Converted {len(coin_arrays)} coins')

def backtest_fast(coin_arrays, wait, pump, max_e, step, sl, tp, risk):
    """Fast backtest using numpy"""
    all_pnl = []
    all_n = []

    for symbol, arr in coin_arrays.items():
        close = arr['close']
        high = arr['high']
        low = arr['low']
        lp = arr['lp']

        if len(close) < wait + 10:
            continue

        pos_avg = 0
        pos_sl = 0
        entries = []

        for i in range(wait, len(close)):
            p = close[i]
            h = high[i]
            lo = low[i]

            if pos_avg > 0:
                # Check SL
                if h >= pos_sl:
                    all_pnl.append(-sl)
                    all_n.append(len(entries))
                    pos_avg = 0
                    entries = []
                    continue

                # Check TP
                tgt = pos_avg * (1 - tp / 100)
                if lo <= tgt or lo <= lp:
                    ep = max(tgt, lp * 0.99)
                    pnl = (pos_avg - ep) / pos_avg * 100
                    all_pnl.append(pnl)
                    all_n.append(len(entries))
                    pos_avg = 0
                    entries = []
                    continue

            # Check entry
            pmp = (p / lp - 1) * 100

            if pmp >= pump:
                if pos_avg == 0:
                    entries = [p]
                    pos_avg = p
                    pos_sl = p * (1 + sl / 100)
                elif len(entries) < max_e:
                    if p >= entries[-1] * (1 + step / 100):
                        entries.append(p)
                        pos_avg = np.mean(entries)
                        pos_sl = p * (1 + sl / 100)

        # Close open
        if pos_avg > 0:
            ep = close[-1]
            pnl = (pos_avg - ep) / pos_avg * 100
            all_pnl.append(pnl)
            all_n.append(len(entries))

    if len(all_pnl) < 30:
        return None

    # Equity simulation
    eq = 100.0
    mxeq = 100.0
    mxdd = 0

    for pnl, n in zip(all_pnl, all_n):
        pv = eq * (risk * n / sl)
        eq += pv * pnl / 100
        mxeq = max(mxeq, eq)
        dd = (mxeq - eq) / mxeq * 100
        mxdd = max(mxdd, dd)

    ret = (eq / 100 - 1) * 100
    wr = sum(1 for p in all_pnl if p > 0) / len(all_pnl) * 100
    rr = ret / mxdd if mxdd > 0 else 0

    return {
        'wait': wait, 'pump': pump, 'max_e': max_e, 'step': step,
        'sl': sl, 'tp': tp, 'risk': risk,
        'trades': len(all_pnl), 'wr': round(wr, 1),
        'ret': round(ret, 1), 'dd': round(mxdd, 1), 'rr': round(rr, 2)
    }

print('\nGrid search...')
results = []
cnt = 0

# Focused grid - key params only
for wait in [12, 24, 48]:
    for pump in [10, 15, 20, 25, 30, 40]:
        for max_e in [1, 2, 3]:
            for step in [5, 10]:
                for sl in [15, 20, 25, 30]:
                    for tp in [25, 35, 50]:
                        for risk in [0.25, 0.5, 0.75, 1.0]:
                            r = backtest_fast(coin_arrays, wait, pump, max_e, step, sl, tp, risk)
                            if r:
                                results.append(r)
                            cnt += 1

    print(f'  Wait={wait}h done ({cnt} tested)')

df = pd.DataFrame(results)
print(f'\nTotal valid combinations: {len(df)}')

# Filter DD < 40%
v40 = df[df['dd'] < 40].sort_values('rr', ascending=False)
print(f"\n{'='*100}")
print(f"TOP 15 (DD < 40%)")
print(f"{'='*100}")
if len(v40) > 0:
    print(v40.head(15).to_string(index=False))
else:
    print("No results with DD < 40%")

# DD < 30%
v30 = df[df['dd'] < 30].sort_values('rr', ascending=False)
print(f"\n{'='*100}")
print(f"TOP 10 (DD < 30%)")
print(f"{'='*100}")
if len(v30) > 0:
    print(v30.head(10).to_string(index=False))
else:
    print("No results with DD < 30%")

# Best overall
if len(v40) > 0:
    best = v40.iloc[0]
    print(f"\n{'='*100}")
    print("BEST PARAMETERS:")
    print(f"{'='*100}")
    print(f"Wait: {best['wait']}h | Pump threshold: {best['pump']}%")
    print(f"Max entries: {best['max_e']} | Entry step: {best['step']}%")
    print(f"SL: {best['sl']}% | TP: {best['tp']}% | Risk/entry: {best['risk']}%")
    print(f"\nTrades: {best['trades']} | Win Rate: {best['wr']}%")
    print(f"Return: {best['ret']:+.1f}% | Max DD: {best['dd']:.1f}% | R:R: {best['rr']:.2f}x")

df.to_csv('trading/results/new_listings_grid.csv', index=False)
print(f"\n✅ Saved {len(df)} results")
