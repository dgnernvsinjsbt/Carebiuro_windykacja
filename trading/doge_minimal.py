"""Ultra-minimal DOGE test - fastest possible"""
import pandas as pd
import numpy as np

df = pd.read_csv('doge_usdt_1m_lbank.csv')
print(f"Testing DOGE: {len(df)} candles\n")

# EMA
df['e10'] = df['close'].ewm(10).mean()
df['e20'] = df['close'].ewm(20).mean()
df['e50'] = df['close'].ewm(50).mean()

# RSI
d = df['close'].diff()
g = (d.where(d > 0, 0)).rolling(14).mean()
l = (-d.where(d < 0, 0)).rolling(14).mean()
df['rsi'] = 100 - (100 / (1 + g / l))

# ATR
df['atr'] = np.maximum(df['high'] - df['low'],
                       np.maximum(abs(df['high'] - df['close'].shift()),
                                abs(df['low'] - df['close'].shift()))).rolling(14).mean()

def test(name, cond_long, cond_short, sl, tp):
    cap = 10000
    pos = None
    t = []

    for i in range(200, len(df)):
        r, p = df.iloc[i], df.iloc[i-1]

        # Exit
        if pos:
            if pos[0] == 'L':
                if r['high'] >= pos[2]: pnl = (pos[2]-pos[1])/pos[1]*100-0.1; cap *= (1+pnl/100); t.append(pnl); pos = None
                elif r['low'] <= pos[3]: pnl = (pos[3]-pos[1])/pos[1]*100-0.1; cap *= (1+pnl/100); t.append(pnl); pos = None
            else:
                if r['low'] <= pos[2]: pnl = (pos[1]-pos[2])/pos[1]*100-0.1; cap *= (1+pnl/100); t.append(pnl); pos = None
                elif r['high'] >= pos[3]: pnl = (pos[1]-pos[3])/pos[1]*100-0.1; cap *= (1+pnl/100); t.append(pnl); pos = None

        # Entry
        if not pos:
            if cond_long(r, p):
                pos = ('L', r['close'], r['close'] + r['atr']*tp, r['close'] - r['atr']*sl)
            elif cond_short(r, p):
                pos = ('S', r['close'], r['close'] - r['atr']*tp, r['close'] + r['atr']*sl)

    if len(t) < 30:
        return None

    arr = np.array(t)
    pk, dd = 10000, 0
    for x in t:
        pk = max(pk, cap)
        dd = min(dd, (cap-pk)/pk*100)

    ret = (cap-10000)/10000*100
    rr = ret/abs(dd) if dd < 0 else 0
    wr = len(arr[arr>0])/len(arr)*100

    return {'name': name, 'trades': len(t), 'wr': wr, 'ret': ret, 'dd': abs(dd), 'rr': rr}

# Test configs
configs = [
    ('EMA10/20_2x4', lambda r,p: p['e10']<=p['e20'] and r['e10']>r['e20'],
                     lambda r,p: p['e10']>=p['e20'] and r['e10']<r['e20'], 2, 4),
    ('EMA10/50_2x4', lambda r,p: p['e10']<=p['e50'] and r['e10']>r['e50'],
                     lambda r,p: p['e10']>=p['e50'] and r['e10']<r['e50'], 2, 4),
    ('EMA20/50_2x4', lambda r,p: p['e20']<=p['e50'] and r['e20']>r['e50'],
                     lambda r,p: p['e20']>=p['e50'] and r['e20']<r['e50'], 2, 4),
    ('RSI30_2x4', lambda r,p: r['rsi']<30, lambda r,p: r['rsi']>70, 2, 4),
    ('RSI25_2x4', lambda r,p: r['rsi']<25, lambda r,p: r['rsi']>75, 2, 4),
    ('EMA10/20_2.5x5', lambda r,p: p['e10']<=p['e20'] and r['e10']>r['e20'],
                       lambda r,p: p['e10']>=p['e20'] and r['e10']<r['e20'], 2.5, 5),
    ('EMA10/50_2.5x5', lambda r,p: p['e10']<=p['e50'] and r['e10']>r['e50'],
                       lambda r,p: p['e10']>=p['e50'] and r['e10']<r['e50'], 2.5, 5),
]

results = []
for cfg in configs:
    r = test(*cfg)
    if r:
        results.append(r)
        print(f"{r['name']}: {r['trades']} trades, {r['wr']:.1f}% WR, {r['ret']:.1f}% ret, {r['dd']:.1f}% DD, RR={r['rr']:.2f}")

if results:
    results.sort(key=lambda x: x['rr'], reverse=True)
    best = results[0]
    print(f"\nBEST: {best['name']}")
    print(f"  R:R {best['rr']:.2f} {'✓' if best['rr']>=2 else '✗'}")
    print(f"  WR {best['wr']:.1f}% {'✓' if best['wr']>=50 else '✗'}")
    print(f"  Return: {best['ret']:.2f}%, DD: {best['dd']:.2f}%")

    # Save
    pd.DataFrame(results).to_csv('results/doge_master_results.csv', index=False)
    print("\nSaved to results/doge_master_results.csv")
else:
    print("\nNo strategies with 30+ trades found")
