#!/usr/bin/env python3
"""
EMA 8/21 Crossover - Detailed Monthly Analysis
"""

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('/home/user/Carebiuro_windykacja/trading/fartcoin_1h_jun_dec_2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Calculate indicators
df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()
df['ema8_prev'] = df['ema8'].shift(1)
df['ema21_prev'] = df['ema21'].shift(1)
df['long_signal'] = (df['ema8'] > df['ema21']) & (df['ema8_prev'] <= df['ema21_prev'])
df['short_signal'] = (df['ema8'] < df['ema21']) & (df['ema8_prev'] >= df['ema21_prev'])

# Params
LIMIT_ATR_OFFSET = 0.7
TP_ATR = 7.0
SL_ATR = 5.0
MAX_WAIT_BARS = 20

# Backtest
trades = []
equity = 100.0
position = None
pending_order = None

for i in range(21, len(df)):
    row = df.iloc[i]

    if pending_order is not None:
        order = pending_order
        bars_waiting = i - order['signal_bar']
        filled = False

        if order['side'] == 'LONG' and row['low'] <= order['limit_price']:
            filled = True
            entry_price = order['limit_price']
        elif order['side'] == 'SHORT' and row['high'] >= order['limit_price']:
            filled = True
            entry_price = order['limit_price']

        if filled:
            position = {
                'side': order['side'], 'entry_price': entry_price,
                'tp': order['tp'], 'sl': order['sl'], 'entry_bar': i,
                'entry_time': row['timestamp']
            }
            pending_order = None
        elif bars_waiting >= MAX_WAIT_BARS:
            pending_order = None

    if position is not None:
        exit_price = None
        exit_reason = None
        if position['side'] == 'LONG':
            if row['high'] >= position['tp']:
                exit_price = position['tp']
                exit_reason = 'TP'
            elif row['low'] <= position['sl']:
                exit_price = position['sl']
                exit_reason = 'SL'
        else:
            if row['low'] <= position['tp']:
                exit_price = position['tp']
                exit_reason = 'TP'
            elif row['high'] >= position['sl']:
                exit_price = position['sl']
                exit_reason = 'SL'

        if exit_price is not None:
            if position['side'] == 'LONG':
                pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * 100
            else:
                pnl_pct = (position['entry_price'] - exit_price) / position['entry_price'] * 100
            equity *= (1 + pnl_pct / 100)
            trades.append({
                'entry_time': position['entry_time'],
                'exit_time': row['timestamp'],
                'side': position['side'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'exit_reason': exit_reason,
                'pnl_pct': pnl_pct,
                'equity': equity
            })
            position = None

    if position is None and pending_order is None:
        atr = row['atr']
        signal_price = row['close']

        if row['long_signal']:
            pending_order = {
                'side': 'LONG', 'signal_price': signal_price,
                'limit_price': signal_price - (LIMIT_ATR_OFFSET * atr),
                'tp': signal_price + (TP_ATR * atr),
                'sl': signal_price - (SL_ATR * atr),
                'signal_bar': i
            }
        elif row['short_signal']:
            pending_order = {
                'side': 'SHORT', 'signal_price': signal_price,
                'limit_price': signal_price + (LIMIT_ATR_OFFSET * atr),
                'tp': signal_price - (TP_ATR * atr),
                'sl': signal_price + (SL_ATR * atr),
                'signal_bar': i
            }

trades_df = pd.DataFrame(trades)
trades_df['month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')

print("=" * 70)
print("EMA 8/21 CROSSOVER - DETAILED MONTHLY ANALYSIS")
print("=" * 70)

# Monthly breakdown
print("\n📅 MONTHLY PERFORMANCE:")
print("-" * 70)
print(f"{'Month':<10} {'P&L':>10} {'Trades':>8} {'Wins':>6} {'Win%':>8} {'Avg W':>10} {'Avg L':>10}")
print("-" * 70)

for month in sorted(trades_df['month'].unique()):
    m_trades = trades_df[trades_df['month'] == month]
    wins = m_trades[m_trades['pnl_pct'] > 0]
    losses = m_trades[m_trades['pnl_pct'] <= 0]

    pnl = m_trades['pnl_pct'].sum()
    win_rate = len(wins) / len(m_trades) * 100 if len(m_trades) > 0 else 0
    avg_win = wins['pnl_pct'].mean() if len(wins) > 0 else 0
    avg_loss = losses['pnl_pct'].mean() if len(losses) > 0 else 0

    status = "✅" if pnl > 0 else "❌"
    print(f"{str(month):<10} {pnl:>+9.2f}% {len(m_trades):>8} {len(wins):>6} {win_rate:>7.1f}% {avg_win:>+9.2f}% {avg_loss:>9.2f}%  {status}")

print("-" * 70)

# Overall stats
wins = trades_df[trades_df['pnl_pct'] > 0]
losses = trades_df[trades_df['pnl_pct'] <= 0]
print(f"{'TOTAL':<10} {trades_df['pnl_pct'].sum():>+9.2f}% {len(trades_df):>8} {len(wins):>6} {len(wins)/len(trades_df)*100:>7.1f}% {wins['pnl_pct'].mean():>+9.2f}% {losses['pnl_pct'].mean():>9.2f}%")

# Top winners
print("\n🏆 TOP 5 WINNERS:")
print("-" * 70)
top_wins = trades_df.nlargest(5, 'pnl_pct')
for _, t in top_wins.iterrows():
    print(f"  {t['exit_time'].strftime('%Y-%m-%d')} | {t['side']:5} | Entry: ${t['entry_price']:.4f} → Exit: ${t['exit_price']:.4f} | {t['pnl_pct']:+.2f}%")

# Top losers
print("\n💀 TOP 5 LOSERS:")
print("-" * 70)
top_losses = trades_df.nsmallest(5, 'pnl_pct')
for _, t in top_losses.iterrows():
    print(f"  {t['exit_time'].strftime('%Y-%m-%d')} | {t['side']:5} | Entry: ${t['entry_price']:.4f} → Exit: ${t['exit_price']:.4f} | {t['pnl_pct']:+.2f}%")

# Stats summary
print("\n📊 TRADE STATISTICS:")
print("-" * 70)
print(f"  Avg Winner:     {wins['pnl_pct'].mean():+.2f}%")
print(f"  Avg Loser:      {losses['pnl_pct'].mean():.2f}%")
print(f"  Best Trade:     {trades_df['pnl_pct'].max():+.2f}%")
print(f"  Worst Trade:    {trades_df['pnl_pct'].min():.2f}%")
print(f"  Median Trade:   {trades_df['pnl_pct'].median():+.2f}%")
print(f"  Std Dev:        {trades_df['pnl_pct'].std():.2f}%")

# Long vs Short
longs = trades_df[trades_df['side'] == 'LONG']
shorts = trades_df[trades_df['side'] == 'SHORT']
print(f"\n  LONG trades:    {len(longs)} ({longs['pnl_pct'].sum():+.2f}% total, {len(longs[longs['pnl_pct']>0])}/{len(longs)} wins)")
print(f"  SHORT trades:   {len(shorts)} ({shorts['pnl_pct'].sum():+.2f}% total, {len(shorts[shorts['pnl_pct']>0])}/{len(shorts)} wins)")

# Consecutive wins/losses
trades_df['is_win'] = trades_df['pnl_pct'] > 0
max_consec_wins = 0
max_consec_losses = 0
curr_wins = 0
curr_losses = 0
for w in trades_df['is_win']:
    if w:
        curr_wins += 1
        curr_losses = 0
        max_consec_wins = max(max_consec_wins, curr_wins)
    else:
        curr_losses += 1
        curr_wins = 0
        max_consec_losses = max(max_consec_losses, curr_losses)

print(f"\n  Max Consecutive Wins:   {max_consec_wins}")
print(f"  Max Consecutive Losses: {max_consec_losses}")

print("\n" + "=" * 70)
