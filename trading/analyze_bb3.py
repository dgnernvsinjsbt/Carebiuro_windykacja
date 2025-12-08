"""
Analyze bb3_std trades in detail
"""
import pandas as pd
import numpy as np

df = pd.read_csv('./eth_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Indicators
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_lower_3'] = df['bb_mid'] - 3 * df['bb_std']
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df = df.dropna()

# bb3_std strategy: enter when close < bb_lower_3
sl_mult = 2.5
tp_mult = 5.0

balance = 10000
position = None
trades = []

for i in range(500, len(df)):
    row = df.iloc[i]

    if position:
        if row['close'] <= position['stop']:
            pnl_pct = (position['stop'] - position['entry']) / position['entry'] * 100
            pnl = (position['stop'] - position['entry']) / position['entry'] * position['margin']
            balance += pnl
            trades.append({
                'entry_time': position['entry_time'],
                'exit_time': row['timestamp'],
                'entry': position['entry'],
                'exit': position['stop'],
                'stop': position['stop'],
                'target': position['target'],
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'result': 'STOP',
                'balance': balance
            })
            position = None
        elif row['close'] >= position['target']:
            pnl_pct = (position['target'] - position['entry']) / position['entry'] * 100
            pnl = (position['target'] - position['entry']) / position['entry'] * position['margin']
            balance += pnl
            trades.append({
                'entry_time': position['entry_time'],
                'exit_time': row['timestamp'],
                'entry': position['entry'],
                'exit': position['target'],
                'stop': position['stop'],
                'target': position['target'],
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'result': 'TP',
                'balance': balance
            })
            position = None

    if not position:
        if row['close'] < row['bb_lower_3']:
            position = {
                'entry_time': row['timestamp'],
                'entry': row['close'],
                'stop': row['close'] - row['atr'] * sl_mult,
                'target': row['close'] + row['atr'] * tp_mult,
                'margin': balance
            }

trades_df = pd.DataFrame(trades)

print("=" * 80)
print("BB3_STD TRADES ANALYSIS")
print("=" * 80)

print(f"\nTotal trades: {len(trades_df)}")
print(f"Wins (TP): {len(trades_df[trades_df['result'] == 'TP'])}")
print(f"Losses (SL): {len(trades_df[trades_df['result'] == 'STOP'])}")
print(f"Win rate: {len(trades_df[trades_df['result'] == 'TP']) / len(trades_df) * 100:.1f}%")

print(f"\nFinal balance: ${balance:.2f}")
print(f"Total return: {(balance - 10000) / 100:.1f}%")

print("\n" + "=" * 80)
print("PNL % PER TRADE STATS:")
print("=" * 80)
print(f"Average win %: {trades_df[trades_df['pnl'] > 0]['pnl_pct'].mean():.3f}%")
print(f"Average loss %: {trades_df[trades_df['pnl'] < 0]['pnl_pct'].mean():.3f}%")
print(f"Max win %: {trades_df['pnl_pct'].max():.3f}%")
print(f"Max loss %: {trades_df['pnl_pct'].min():.3f}%")

print("\n" + "=" * 80)
print("FIRST 20 TRADES:")
print("=" * 80)
for i, t in trades_df.head(20).iterrows():
    print(f"{t['entry_time']} | Entry: ${t['entry']:.2f} | Exit: ${t['exit']:.2f} | "
          f"PnL: {t['pnl_pct']:+.3f}% | {t['result']} | Bal: ${t['balance']:.0f}")

print("\n" + "=" * 80)
print("LAST 10 TRADES:")
print("=" * 80)
for i, t in trades_df.tail(10).iterrows():
    print(f"{t['entry_time']} | Entry: ${t['entry']:.2f} | Exit: ${t['exit']:.2f} | "
          f"PnL: {t['pnl_pct']:+.3f}% | {t['result']} | Bal: ${t['balance']:.0f}")

# Save all trades
trades_df.to_csv('./results/bb3_std_all_trades.csv', index=False)
print(f"\nAll trades saved to ./results/bb3_std_all_trades.csv")
