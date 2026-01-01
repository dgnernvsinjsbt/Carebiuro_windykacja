#!/usr/bin/env python3
"""
EMA 8/21 Crossover Strategy - NASDAQ100 Futures (NQ)
Same parameters as profitable FARTCOIN strategy
"""

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('/home/user/Carebiuro_windykacja/trading/nasdaq_nq_futures_1h_2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"Loaded {len(df)} candles")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Calculate indicators
df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
df['tr'] = np.maximum(df['high'] - df['low'],
                      np.maximum(abs(df['high'] - df['close'].shift(1)),
                                abs(df['low'] - df['close'].shift(1))))
df['atr'] = df['tr'].rolling(14).mean()

# Signal detection
df['ema8_prev'] = df['ema8'].shift(1)
df['ema21_prev'] = df['ema21'].shift(1)
df['long_signal'] = (df['ema8'] > df['ema21']) & (df['ema8_prev'] <= df['ema21_prev'])
df['short_signal'] = (df['ema8'] < df['ema21']) & (df['ema8_prev'] >= df['ema21_prev'])

# Strategy parameters (same as FARTCOIN)
LIMIT_ATR_OFFSET = 0.7
TP_ATR = 7.0
SL_ATR = 5.0
MAX_WAIT_BARS = 20
FEE_PCT = 0.01  # Lower fees for futures (0.01% vs 0.07% crypto)

# Backtest
trades = []
equity = 100.0
max_equity = 100.0
max_dd = 0.0
position = None
pending_order = None

for i in range(21, len(df)):
    row = df.iloc[i]

    # Check pending order
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
                'side': order['side'],
                'entry_price': entry_price,
                'tp': order['tp'],
                'sl': order['sl'],
                'entry_bar': i,
                'entry_time': row['timestamp']
            }
            pending_order = None
        elif bars_waiting >= MAX_WAIT_BARS:
            pending_order = None

    # Check position exit
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
        else:  # SHORT
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

            # Deduct fees
            pnl_pct -= FEE_PCT * 2  # Entry + exit

            equity *= (1 + pnl_pct / 100)
            max_equity = max(max_equity, equity)
            dd = (equity - max_equity) / max_equity * 100
            max_dd = min(max_dd, dd)

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

    # Check for new signals
    if position is None and pending_order is None:
        atr = row['atr']
        signal_price = row['close']

        if row['long_signal']:
            pending_order = {
                'side': 'LONG',
                'signal_price': signal_price,
                'limit_price': signal_price - (LIMIT_ATR_OFFSET * atr),
                'tp': signal_price + (TP_ATR * atr),
                'sl': signal_price - (SL_ATR * atr),
                'signal_bar': i
            }
        elif row['short_signal']:
            pending_order = {
                'side': 'SHORT',
                'signal_price': signal_price,
                'limit_price': signal_price + (LIMIT_ATR_OFFSET * atr),
                'tp': signal_price - (TP_ATR * atr),
                'sl': signal_price + (SL_ATR * atr),
                'signal_bar': i
            }

# Results
trades_df = pd.DataFrame(trades)
total_return = (equity - 100)
wins = len(trades_df[trades_df['pnl_pct'] > 0])
losses = len(trades_df[trades_df['pnl_pct'] <= 0])
win_rate = wins / len(trades_df) * 100 if len(trades_df) > 0 else 0

print("\n" + "=" * 70)
print("NASDAQ100 FUTURES (NQ) - EMA 8/21 CROSSOVER")
print("=" * 70)
print(f"Parameters: TP {TP_ATR} ATR, SL {SL_ATR} ATR, Offset {LIMIT_ATR_OFFSET} ATR")
print(f"Fees: {FEE_PCT}% per side (futures)")
print("-" * 70)
print(f"Total Return:  {total_return:+.2f}%")
print(f"Max Drawdown:  {max_dd:.2f}%")
print(f"R:R Ratio:     {total_return / abs(max_dd):.2f}x" if max_dd != 0 else "R:R Ratio:     N/A")
print(f"Total Trades:  {len(trades_df)}")
print(f"Win Rate:      {win_rate:.1f}% ({wins}W / {losses}L)")
print("-" * 70)

if len(trades_df) > 0:
    winners = trades_df[trades_df['pnl_pct'] > 0]
    losers = trades_df[trades_df['pnl_pct'] <= 0]
    print(f"Avg Winner:    {winners['pnl_pct'].mean():+.2f}%" if len(winners) > 0 else "Avg Winner:    N/A")
    print(f"Avg Loser:     {losers['pnl_pct'].mean():.2f}%" if len(losers) > 0 else "Avg Loser:     N/A")
    print(f"Best Trade:    {trades_df['pnl_pct'].max():+.2f}%")
    print(f"Worst Trade:   {trades_df['pnl_pct'].min():.2f}%")

    # Monthly breakdown
    trades_df['month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')
    print("\n📅 MONTHLY PERFORMANCE:")
    print("-" * 70)
    for month in sorted(trades_df['month'].unique()):
        m_trades = trades_df[trades_df['month'] == month]
        m_pnl = m_trades['pnl_pct'].sum()
        m_wins = len(m_trades[m_trades['pnl_pct'] > 0])
        status = "✅" if m_pnl > 0 else "❌"
        print(f"  {month}: {m_pnl:+.2f}% ({len(m_trades)} trades, {m_wins}W) {status}")

    # Long vs Short
    longs = trades_df[trades_df['side'] == 'LONG']
    shorts = trades_df[trades_df['side'] == 'SHORT']
    print(f"\n  LONG:  {longs['pnl_pct'].sum():+.2f}% ({len(longs)} trades)")
    print(f"  SHORT: {shorts['pnl_pct'].sum():+.2f}% ({len(shorts)} trades)")

print("=" * 70)
