#!/usr/bin/env python3
"""
EMA 8/21 Crossover - CORRECTED backtest with proper TP/SL handling
Fixed: Same-bar TP/SL conflict uses conservative assumption (SL wins)
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

# Optimized params
LIMIT_ATR_OFFSET = 0.7
TP_ATR = 7.0
SL_ATR = 5.0
MAX_WAIT_BARS = 20

def check_exit(row, position):
    """
    Check exit with proper same-bar handling.
    If both TP and SL could hit in same bar:
    - Use open price to determine which hits first
    - If still ambiguous, assume SL (conservative)
    """
    tp = position['tp']
    sl = position['sl']

    if position['side'] == 'LONG':
        tp_hit = row['high'] >= tp
        sl_hit = row['low'] <= sl

        if tp_hit and sl_hit:
            # Both could hit - check open direction
            if row['open'] >= tp:
                # Gapped up past TP - TP wins
                return tp, 'TP'
            elif row['open'] <= sl:
                # Gapped down past SL - SL wins
                return sl, 'SL'
            else:
                # Open in between - conservative: SL wins
                return sl, 'SL'
        elif tp_hit:
            return tp, 'TP'
        elif sl_hit:
            return sl, 'SL'
    else:  # SHORT
        tp_hit = row['low'] <= tp
        sl_hit = row['high'] >= sl

        if tp_hit and sl_hit:
            # Both could hit - check open direction
            if row['open'] <= tp:
                # Gapped down past TP - TP wins
                return tp, 'TP'
            elif row['open'] >= sl:
                # Gapped up past SL - SL wins
                return sl, 'SL'
            else:
                # Open in between - conservative: SL wins
                return sl, 'SL'
        elif tp_hit:
            return tp, 'TP'
        elif sl_hit:
            return sl, 'SL'

    return None, None

def backtest():
    trades = []
    equity = 100.0
    position = None
    pending_order = None
    same_bar_conflicts = 0

    for i in range(21, len(df)):
        row = df.iloc[i]

        # Check pending limit order
        if pending_order is not None:
            order = pending_order
            bars_waiting = i - order['signal_bar']
            filled = False

            if order['side'] == 'LONG' and row['low'] <= order['limit_price']:
                filled = True
                entry_price = min(order['limit_price'], row['open'])  # Can't fill better than open
            elif order['side'] == 'SHORT' and row['high'] >= order['limit_price']:
                filled = True
                entry_price = max(order['limit_price'], row['open'])  # Can't fill better than open

            if filled:
                position = {
                    'side': order['side'],
                    'entry_price': entry_price,
                    'signal_price': order['signal_price'],
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
            exit_price, exit_reason = check_exit(row, position)

            # Track same-bar conflicts
            if position['side'] == 'LONG':
                if row['high'] >= position['tp'] and row['low'] <= position['sl']:
                    same_bar_conflicts += 1
            else:
                if row['low'] <= position['tp'] and row['high'] >= position['sl']:
                    same_bar_conflicts += 1

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

        # Generate new signals
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

    return trades, same_bar_conflicts

# Run backtest
trades, conflicts = backtest()

print("=" * 70)
print("EMA 8/21 CROSSOVER - CORRECTED BACKTEST")
print("=" * 70)
print(f"Params: Limit {LIMIT_ATR_OFFSET} ATR | TP {TP_ATR} ATR | SL {SL_ATR} ATR")
print(f"Same-bar TP/SL conflicts: {conflicts} (resolved conservatively → SL)")
print("-" * 70)

if trades:
    trades_df = pd.DataFrame(trades)

    total_return = trades_df['equity'].iloc[-1] - 100
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    losses = len(trades_df[trades_df['pnl_pct'] <= 0])
    win_rate = wins / len(trades_df) * 100

    trades_df['peak'] = trades_df['equity'].cummax()
    trades_df['dd'] = (trades_df['equity'] - trades_df['peak']) / trades_df['peak'] * 100
    max_dd = trades_df['dd'].min()

    rr = abs(total_return / max_dd) if max_dd != 0 else 0

    tp_exits = len(trades_df[trades_df['exit_reason'] == 'TP'])
    sl_exits = len(trades_df[trades_df['exit_reason'] == 'SL'])

    print(f"\nPerformance:")
    print(f"  Total Return: {total_return:+.2f}%")
    print(f"  Max Drawdown: {max_dd:.2f}%")
    print(f"  R:R Ratio: {rr:.2f}x")
    print(f"  Final Equity: ${trades_df['equity'].iloc[-1]:.2f}")

    print(f"\nTrades:")
    print(f"  Total: {len(trades_df)}")
    print(f"  Wins: {wins} | Losses: {losses}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  TP exits: {tp_exits} | SL exits: {sl_exits}")

    print(f"\nAvg P&L:")
    print(f"  Winners: {trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean():+.2f}%")
    print(f"  Losers: {trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean():.2f}%")

    # Monthly breakdown
    trades_df['month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')
    monthly = trades_df.groupby('month')['pnl_pct'].agg(['sum', 'count'])

    print(f"\nMonthly:")
    for month, row in monthly.iterrows():
        status = "✅" if row['sum'] > 0 else "❌"
        print(f"  {month}: {row['sum']:+.2f}% ({int(row['count'])} trades) {status}")

print("=" * 70)
