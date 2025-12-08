"""
ETH Low-Frequency Strategies - Fewer trades, higher quality
"""
import pandas as pd
import numpy as np

print("=" * 70)
print("ETH LOW-FREQUENCY STRATEGIES (Long Only, 0 Fees)")
print("=" * 70)

df = pd.read_csv('./eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
# Full 30 days
print(f"Data: {len(df):,} candles, 30 days")

# Indicators
df['rsi'] = 100 - 100 / (1 + df['close'].diff().clip(lower=0).rolling(14).mean() /
                          df['close'].diff().clip(upper=0).abs().rolling(14).mean())
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
df['bb_lower_3'] = df['bb_mid'] - 3 * df['bb_std']  # 3 std for extreme
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df['vol_ma'] = df['volume'].rolling(50).mean()
df['vol_spike'] = df['volume'] > df['vol_ma'] * 2
df['ema50'] = df['close'].ewm(span=50).mean()
df['ema200'] = df['close'].ewm(span=200).mean()

# Daily high/low for breakout
df['daily_low'] = df['low'].rolling(1440).min()  # 24h low
df['daily_high'] = df['high'].rolling(1440).max()

df = df.dropna()

def backtest(df, long_func, short_func, sl_mult=2.0, tp_mult=4.0, leverage=1, fees=0):
    balance = 10000
    position = None
    trades = []

    for i in range(500, len(df)):
        row = df.iloc[i]

        if position:
            if position['side'] == 'long':
                if row['close'] <= position['stop']:
                    pnl = (position['stop'] - position['entry']) / position['entry'] * leverage * position['margin']
                    pnl -= position['margin'] * leverage * fees * 2
                    balance += pnl
                    trades.append({'pnl': pnl})
                    position = None
                elif row['close'] >= position['target']:
                    pnl = (position['target'] - position['entry']) / position['entry'] * leverage * position['margin']
                    pnl -= position['margin'] * leverage * fees * 2
                    balance += pnl
                    trades.append({'pnl': pnl})
                    position = None
            else:  # short
                if row['close'] >= position['stop']:
                    pnl = (position['entry'] - position['stop']) / position['entry'] * leverage * position['margin']
                    pnl -= position['margin'] * leverage * fees * 2
                    balance += pnl
                    trades.append({'pnl': pnl})
                    position = None
                elif row['close'] <= position['target']:
                    pnl = (position['entry'] - position['target']) / position['entry'] * leverage * position['margin']
                    pnl -= position['margin'] * leverage * fees * 2
                    balance += pnl
                    trades.append({'pnl': pnl})
                    position = None

        if not position:
            if long_func(row):  # Long only
                position = {
                    'side': 'long',
                    'entry': row['close'],
                    'stop': row['close'] - row['atr'] * sl_mult,
                    'target': row['close'] + row['atr'] * tp_mult,
                    'margin': balance * 1.0  # 100% position
                }

    if len(trades) < 5:
        return None

    tdf = pd.DataFrame(trades)
    ret = (balance - 10000) / 100
    dd = min(0, tdf['pnl'].cumsum().min()) / 10000 * 100
    if dd >= 0: dd = -0.1

    return {
        'return': ret,
        'dd': dd,
        'ratio': abs(ret / dd),
        'trades': len(trades),
        'wr': len(tdf[tdf['pnl'] > 0]) / len(tdf) * 100
    }

# Define strategies with long AND short signals
strategies = {
    'rsi_15': (lambda r: r['rsi'] < 15, lambda r: r['rsi'] > 85),
    'rsi_20': (lambda r: r['rsi'] < 20, lambda r: r['rsi'] > 80),
    'bb3_std': (lambda r: r['close'] < r['bb_lower_3'], lambda r: r['close'] > r['bb_mid'] + 3*r['bb_std']),
    'rsi15_vol': (lambda r: r['rsi'] < 15 and r['vol_spike'], lambda r: r['rsi'] > 85 and r['vol_spike']),
    'rsi20_vol': (lambda r: r['rsi'] < 20 and r['vol_spike'], lambda r: r['rsi'] > 80 and r['vol_spike']),
    'bb3_rsi20': (lambda r: r['close'] < r['bb_lower_3'] and r['rsi'] < 20,
                  lambda r: r['close'] > r['bb_mid'] + 3*r['bb_std'] and r['rsi'] > 80),
}

print(f"\nTesting {len(strategies)} strategies...")

results = []
for name, (long_f, short_f) in strategies.items():
    for sl, tp in [(1.5, 3), (2, 4), (2, 5), (2.5, 5)]:
        for lev in [1]:  # Spot = 1x only
            r = backtest(df, long_f, short_f, sl_mult=sl, tp_mult=tp, leverage=lev)
            if r:
                results.append({
                    'strategy': name, 'sl': sl, 'tp': tp, 'lev': lev,
                    **r
                })

rdf = pd.DataFrame(results)
if len(rdf) > 0:
    rdf = rdf.sort_values('ratio', ascending=False)

    print(f"\nTested {len(rdf)} combinations\n")
    print("TOP 15 LOW-FREQUENCY STRATEGIES:")
    print("-" * 70)

    for _, row in rdf.head(15).iterrows():
        status = "4:1 MET" if row['ratio'] >= 4 else ""
        print(f"{row['strategy']:20} {row['lev']}x SL:{row['sl']} TP:{row['tp']} | "
              f"Ret:{row['return']:6.1f}% DD:{row['dd']:5.1f}% "
              f"Ratio:{row['ratio']:4.1f}:1 Trades:{row['trades']:3} WR:{row['wr']:.0f}% {status}")

    # Show trade counts
    print(f"\n{'='*70}")
    print("TRADE FREQUENCY COMPARISON:")
    for name in strategies.keys():
        subset = rdf[rdf['strategy'] == name]
        if len(subset) > 0:
            avg_trades = subset['trades'].mean()
            print(f"  {name:25}: ~{avg_trades:.0f} trades/month")

    winners = rdf[rdf['ratio'] >= 4]
    print(f"\n{'='*70}")
    print(f"Strategies meeting 4:1 target: {len(winners)}")
    if len(winners) > 0:
        best = winners.iloc[0]
        print(f"BEST: {best['strategy']} {best['lev']}x | {best['return']:.1f}% return | {best['ratio']:.1f}:1 ratio | {best['trades']} trades")
