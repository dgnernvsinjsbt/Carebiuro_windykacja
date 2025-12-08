"""
DOGE/USDT Quick Test - Top 5 Strategies
"""

import pandas as pd
import numpy as np

INITIAL_CAPITAL = 10000
FEE = 0.001

def calc_indicators(df):
    data = df.copy()
    data['ema_10'] = data['close'].ewm(span=10).mean()
    data['ema_20'] = data['close'].ewm(span=20).mean()
    data['ema_50'] = data['close'].ewm(span=50).mean()

    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    data['rsi'] = 100 - (100 / (1 + gain / loss))

    data['tr'] = np.maximum(data['high'] - data['low'],
                            np.maximum(abs(data['high'] - data['close'].shift()),
                                     abs(data['low'] - data['close'].shift())))
    data['atr'] = data['tr'].rolling(14).mean()

    data['ema_12'] = data['close'].ewm(span=12).mean()
    data['ema_26'] = data['close'].ewm(span=26).mean()
    data['macd'] = data['ema_12'] - data['ema_26']
    data['macd_sig'] = data['macd'].ewm(span=9).mean()

    return data

def test_ema_cross(df, fast, slow, sl, tp):
    capital = INITIAL_CAPITAL
    pos = None
    trades = []

    for i in range(200, len(df)):
        r = df.iloc[i]
        p = df.iloc[i-1]

        if pos:
            if pos['type'] == 'L':
                if r['high'] >= pos['tp']:
                    pnl = (pos['tp'] - pos['e']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None
                elif r['low'] <= pos['sl']:
                    pnl = (pos['sl'] - pos['e']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None
            else:
                if r['low'] <= pos['tp']:
                    pnl = (pos['e'] - pos['tp']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None
                elif r['high'] >= pos['sl']:
                    pnl = (pos['e'] - pos['sl']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None

        if not pos:
            if p[f'ema_{fast}'] <= p[f'ema_{slow}'] and r[f'ema_{fast}'] > r[f'ema_{slow}']:
                pos = {'type': 'L', 'e': r['close'], 'sl': r['close'] - r['atr'] * sl, 'tp': r['close'] + r['atr'] * tp}
            elif p[f'ema_{fast}'] >= p[f'ema_{slow}'] and r[f'ema_{fast}'] < r[f'ema_{slow}']:
                pos = {'type': 'S', 'e': r['close'], 'sl': r['close'] + r['atr'] * sl, 'tp': r['close'] - r['atr'] * tp}

    if len(trades) < 30:
        return None

    arr = np.array(trades)
    wins = arr[arr > 0]
    peak = INITIAL_CAPITAL
    dd = 0

    for t in trades:
        peak = max(peak, capital)
        dd = min(dd, (capital - peak) / peak * 100)

    ret = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    rr = ret / abs(dd) if dd < 0 else 0

    return {
        'name': f'EMA{fast}/{slow}_SL{sl}_TP{tp}',
        'trades': len(trades),
        'wr': len(wins) / len(trades) * 100,
        'return': ret,
        'dd': abs(dd),
        'rr': rr
    }

def test_rsi(df, level, sl, tp):
    capital = INITIAL_CAPITAL
    pos = None
    trades = []

    for i in range(200, len(df)):
        r = df.iloc[i]

        if pos:
            if pos['type'] == 'L':
                if r['high'] >= pos['tp']:
                    pnl = (pos['tp'] - pos['e']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None
                elif r['low'] <= pos['sl']:
                    pnl = (pos['sl'] - pos['e']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None
            else:
                if r['low'] <= pos['tp']:
                    pnl = (pos['e'] - pos['tp']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None
                elif r['high'] >= pos['sl']:
                    pnl = (pos['e'] - pos['sl']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None

        if not pos:
            if r['rsi'] < level:
                pos = {'type': 'L', 'e': r['close'], 'sl': r['close'] - r['atr'] * sl, 'tp': r['close'] + r['atr'] * tp}
            elif r['rsi'] > (100 - level):
                pos = {'type': 'S', 'e': r['close'], 'sl': r['close'] + r['atr'] * sl, 'tp': r['close'] - r['atr'] * tp}

    if len(trades) < 30:
        return None

    arr = np.array(trades)
    wins = arr[arr > 0]
    peak = INITIAL_CAPITAL
    dd = 0

    for t in trades:
        peak = max(peak, capital)
        dd = min(dd, (capital - peak) / peak * 100)

    ret = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    rr = ret / abs(dd) if dd < 0 else 0

    return {
        'name': f'RSI{level}_SL{sl}_TP{tp}',
        'trades': len(trades),
        'wr': len(wins) / len(trades) * 100,
        'return': ret,
        'dd': abs(dd),
        'rr': rr
    }

def test_macd(df, sl, tp):
    capital = INITIAL_CAPITAL
    pos = None
    trades = []

    for i in range(200, len(df)):
        r = df.iloc[i]
        p = df.iloc[i-1]

        if pos:
            if pos['type'] == 'L':
                if r['high'] >= pos['tp']:
                    pnl = (pos['tp'] - pos['e']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None
                elif r['low'] <= pos['sl']:
                    pnl = (pos['sl'] - pos['e']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None
            else:
                if r['low'] <= pos['tp']:
                    pnl = (pos['e'] - pos['tp']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None
                elif r['high'] >= pos['sl']:
                    pnl = (pos['e'] - pos['sl']) / pos['e'] * 100 - FEE * 100
                    capital *= (1 + pnl / 100)
                    trades.append(pnl)
                    pos = None

        if not pos:
            if p['macd'] <= p['macd_sig'] and r['macd'] > r['macd_sig']:
                pos = {'type': 'L', 'e': r['close'], 'sl': r['close'] - r['atr'] * sl, 'tp': r['close'] + r['atr'] * tp}
            elif p['macd'] >= p['macd_sig'] and r['macd'] < r['macd_sig']:
                pos = {'type': 'S', 'e': r['close'], 'sl': r['close'] + r['atr'] * sl, 'tp': r['close'] - r['atr'] * tp}

    if len(trades) < 30:
        return None

    arr = np.array(trades)
    wins = arr[arr > 0]
    peak = INITIAL_CAPITAL
    dd = 0

    for t in trades:
        peak = max(peak, capital)
        dd = min(dd, (capital - peak) / peak * 100)

    ret = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    rr = ret / abs(dd) if dd < 0 else 0

    return {
        'name': f'MACD_SL{sl}_TP{tp}',
        'trades': len(trades),
        'wr': len(wins) / len(trades) * 100,
        'return': ret,
        'dd': abs(dd),
        'rr': rr
    }

print("DOGE/USDT Quick Test")
print("=" * 60)

df = pd.read_csv('doge_usdt_1m_lbank.csv')
print(f"Loaded {len(df):,} candles\n")

df = calc_indicators(df)

results = []

# Test EMA crosses
for fast, slow in [(10, 20), (10, 50), (20, 50)]:
    for sl in [1.5, 2.0, 2.5]:
        for tp in [3.0, 4.0, 5.0]:
            r = test_ema_cross(df, fast, slow, sl, tp)
            if r:
                results.append(r)

# Test RSI
for level in [25, 30]:
    for sl in [1.5, 2.0, 2.5]:
        for tp in [3.0, 4.0, 5.0]:
            r = test_rsi(df, level, sl, tp)
            if r:
                results.append(r)

# Test MACD
for sl in [1.5, 2.0, 2.5, 3.0]:
    for tp in [3.0, 4.0, 5.0, 6.0]:
        r = test_macd(df, sl, tp)
        if r:
            results.append(r)

print(f"Completed {len(results)} tests\n")

if results:
    results.sort(key=lambda x: x['rr'], reverse=True)

    # Save
    df_r = pd.DataFrame(results)
    df_r.to_csv('results/doge_master_results.csv', index=False)
    print("Saved to results/doge_master_results.csv\n")

    # Top 10
    print("TOP 10 STRATEGIES:")
    print("=" * 60)
    for i, r in enumerate(results[:10]):
        print(f"\n{i+1}. {r['name']}")
        print(f"   Trades: {r['trades']}, WR: {r['wr']:.1f}%")
        print(f"   Return: {r['return']:.2f}%, DD: {r['dd']:.2f}%, R:R: {r['rr']:.2f}")

    # Best
    best = results[0]
    print("\n" + "=" * 60)
    print("BEST STRATEGY")
    print("=" * 60)
    print(f"Name: {best['name']}")
    print(f"Trades: {best['trades']}")
    print(f"Win rate: {best['wr']:.1f}%")
    print(f"Return: {best['return']:.2f}%")
    print(f"Max DD: {best['dd']:.2f}%")
    print(f"R:R: {best['rr']:.2f}")

    print("\n" + "=" * 60)
    print("CRITERIA:")
    print(f"R:R >= 2.0: {'✓' if best['rr'] >= 2.0 else '✗'} ({best['rr']:.2f})")
    print(f"WR >= 50%: {'✓' if best['wr'] >= 50 else '✗'} ({best['wr']:.1f}%)")
    print(f"Trades >= 30: {'✓' if best['trades'] >= 30 else '✗'} ({best['trades']})")

else:
    print("No successful strategies found")
