"""
ETH Spot Trading - Long Only, 0 Fees - Quick Test
"""
import pandas as pd
import numpy as np

print("=" * 60)
print("ETH SPOT TRADING (Long Only, 0 Fees)")
print("=" * 60)

df = pd.read_csv('./eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
# Use 7 days first for speed
df = df.head(10080)
print(f"Data: {len(df):,} candles, {(df['timestamp'].max() - df['timestamp'].min()).days} days")

# Indicators
df['rsi'] = df['close'].diff().apply(lambda x: x if x > 0 else 0).rolling(14).mean() / \
            df['close'].diff().abs().rolling(14).mean() * 100
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_lower'] = df['bb_mid'] - 2.5 * df['bb_std']
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df = df.dropna()

def spot_backtest(df, rsi_entry=25, sl_pct=0.02, tp_pct=0.04):
    balance = 10000
    position = None
    trades = []

    for i in range(50, len(df)):
        row = df.iloc[i]

        if position:
            if row['close'] <= position['stop']:
                pnl = position['size'] * (position['stop']/position['entry'] - 1)
                balance += pnl
                trades.append({'pnl': pnl})
                position = None
            elif row['close'] >= position['target']:
                pnl = position['size'] * (position['target']/position['entry'] - 1)
                balance += pnl
                trades.append({'pnl': pnl})
                position = None

        if not position and row['rsi'] < rsi_entry and row['close'] < row['bb_lower']:
            position = {
                'entry': row['close'],
                'stop': row['close'] * (1 - sl_pct),
                'target': row['close'] * (1 + tp_pct),
                'size': balance * 0.5
            }

    if len(trades) < 3:
        return None

    trades_df = pd.DataFrame(trades)
    total_ret = (balance - 10000) / 100
    max_dd = min(0, trades_df['pnl'].cumsum().min()) / 10000 * 100

    return {
        'return': total_ret,
        'max_dd': max_dd if max_dd < 0 else -0.01,
        'trades': len(trades),
        'win_rate': len(trades_df[trades_df['pnl'] > 0]) / len(trades_df) * 100
    }

print("\nTesting...")
results = []
for rsi in [20, 25, 30]:
    for sl in [0.01, 0.015, 0.02, 0.025]:
        for tp in [0.02, 0.03, 0.04, 0.05, 0.06]:
            r = spot_backtest(df, rsi_entry=rsi, sl_pct=sl, tp_pct=tp)
            if r:
                ratio = abs(r['return'] / r['max_dd']) if r['max_dd'] != 0 else 0
                results.append({
                    'rsi': rsi, 'sl': sl*100, 'tp': tp*100,
                    'return': r['return'], 'max_dd': r['max_dd'],
                    'ratio': ratio, 'trades': r['trades'], 'wr': r['win_rate']
                })

results_df = pd.DataFrame(results).sort_values('ratio', ascending=False)

print(f"\nTested {len(results_df)} combinations\n")
print("TOP 10 SPOT STRATEGIES (Long only, 0 fees):")
print("-" * 60)

for _, row in results_df.head(10).iterrows():
    status = "4:1 MET" if row['ratio'] >= 4 else ""
    print(f"RSI<{row['rsi']} SL:{row['sl']:.1f}% TP:{row['tp']:.1f}% | "
          f"Ret:{row['return']:.1f}% DD:{row['max_dd']:.1f}% "
          f"Ratio:{row['ratio']:.1f}:1 WR:{row['wr']:.0f}% Trades:{row['trades']} {status}")

winners = results_df[results_df['ratio'] >= 4]
print(f"\n{'='*60}")
print(f"Strategies meeting 4:1 target: {len(winners)}")
if len(winners) > 0:
    print(f"Best: {winners.iloc[0]['return']:.1f}% return, {winners.iloc[0]['ratio']:.1f}:1 ratio")
