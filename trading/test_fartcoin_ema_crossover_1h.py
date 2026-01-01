#!/usr/bin/env python3
"""
EMA 8/21 Crossover Trend Following Strategy - FARTCOIN 1h BingX

Signal: EMA 8 crosses EMA 21
Entry: Limit order 0.7 ATR from signal price
TP: 8 ATR from signal price
SL: 2 ATR from signal price
"""

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('/home/user/Carebiuro_windykacja/trading/fartcoin_1h_jun_dec_2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f"Loaded {len(df):,} candles: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Calculate indicators
df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

# ATR(14)
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

# EMA crossover signals
df['ema8_prev'] = df['ema8'].shift(1)
df['ema21_prev'] = df['ema21'].shift(1)

df['long_signal'] = (df['ema8'] > df['ema21']) & (df['ema8_prev'] <= df['ema21_prev'])
df['short_signal'] = (df['ema8'] < df['ema21']) & (df['ema8_prev'] >= df['ema21_prev'])

# Strategy parameters
LIMIT_ATR_OFFSET = 0.7
TP_ATR = 8.0
SL_ATR = 2.0
MAX_WAIT_BARS = 20  # Cancel limit if not filled in 20 bars

# Backtest
trades = []
equity = 100.0
position = None
pending_order = None

for i in range(21, len(df)):
    row = df.iloc[i]

    # Check pending limit order
    if pending_order is not None:
        order = pending_order
        bars_waiting = i - order['signal_bar']

        # Check if limit hit
        filled = False
        if order['side'] == 'LONG':
            if row['low'] <= order['limit_price']:
                filled = True
                entry_price = order['limit_price']
        else:  # SHORT
            if row['high'] >= order['limit_price']:
                filled = True
                entry_price = order['limit_price']

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
            # Cancel stale order
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
            # Calculate P&L
            if position['side'] == 'LONG':
                pnl_pct = (exit_price - position['entry_price']) / position['entry_price'] * 100
            else:
                pnl_pct = (position['entry_price'] - exit_price) / position['entry_price'] * 100

            equity *= (1 + pnl_pct / 100)

            trades.append({
                'entry_time': position['entry_time'],
                'exit_time': row['timestamp'],
                'side': position['side'],
                'signal_price': position['signal_price'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'exit_reason': exit_reason,
                'pnl_pct': pnl_pct,
                'equity': equity
            })
            position = None

    # Generate new signals (only if no position and no pending order)
    if position is None and pending_order is None:
        atr = row['atr']
        signal_price = row['close']

        if row['long_signal']:
            limit_price = signal_price - (LIMIT_ATR_OFFSET * atr)
            tp = signal_price + (TP_ATR * atr)
            sl = signal_price - (SL_ATR * atr)

            pending_order = {
                'side': 'LONG',
                'signal_price': signal_price,
                'limit_price': limit_price,
                'tp': tp,
                'sl': sl,
                'signal_bar': i
            }

        elif row['short_signal']:
            limit_price = signal_price + (LIMIT_ATR_OFFSET * atr)
            tp = signal_price - (TP_ATR * atr)
            sl = signal_price + (SL_ATR * atr)

            pending_order = {
                'side': 'SHORT',
                'signal_price': signal_price,
                'limit_price': limit_price,
                'tp': tp,
                'sl': sl,
                'signal_bar': i
            }

# Results
print("\n" + "=" * 60)
print("EMA 8/21 CROSSOVER - FARTCOIN 1H BINGX")
print("=" * 60)

if not trades:
    print("No trades executed!")
else:
    trades_df = pd.DataFrame(trades)

    total_trades = len(trades_df)
    wins = len(trades_df[trades_df['pnl_pct'] > 0])
    losses = len(trades_df[trades_df['pnl_pct'] <= 0])
    win_rate = wins / total_trades * 100

    total_return = (equity - 100)

    # Max drawdown
    trades_df['peak'] = trades_df['equity'].cummax()
    trades_df['dd'] = (trades_df['equity'] - trades_df['peak']) / trades_df['peak'] * 100
    max_dd = trades_df['dd'].min()

    # R:R ratio (return / max drawdown)
    rr_ratio = abs(total_return / max_dd) if max_dd != 0 else 0

    longs = trades_df[trades_df['side'] == 'LONG']
    shorts = trades_df[trades_df['side'] == 'SHORT']

    print(f"\nParameters:")
    print(f"  Entry: Limit {LIMIT_ATR_OFFSET} ATR from signal")
    print(f"  TP: {TP_ATR} ATR | SL: {SL_ATR} ATR")
    print(f"  Max wait: {MAX_WAIT_BARS} bars")

    print(f"\nPerformance:")
    print(f"  Total Return: {total_return:+.2f}%")
    print(f"  Max Drawdown: {max_dd:.2f}%")
    print(f"  R:R Ratio: {rr_ratio:.2f}x")
    print(f"  Final Equity: ${equity:.2f}")

    print(f"\nTrades:")
    print(f"  Total: {total_trades}")
    print(f"  Wins: {wins} | Losses: {losses}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Longs: {len(longs)} | Shorts: {len(shorts)}")

    print(f"\nAvg P&L:")
    print(f"  All: {trades_df['pnl_pct'].mean():+.2f}%")
    print(f"  Winners: {trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean():+.2f}%")
    print(f"  Losers: {trades_df[trades_df['pnl_pct'] <= 0]['pnl_pct'].mean():.2f}%")

    # Monthly breakdown
    trades_df['month'] = pd.to_datetime(trades_df['exit_time']).dt.to_period('M')
    monthly = trades_df.groupby('month')['pnl_pct'].agg(['sum', 'count'])

    print(f"\nMonthly Breakdown:")
    for month, row in monthly.iterrows():
        status = "✅" if row['sum'] > 0 else "❌"
        print(f"  {month}: {row['sum']:+.2f}% ({int(row['count'])} trades) {status}")

    # Trade log
    print(f"\nTrade Log:")
    print("-" * 80)
    for _, t in trades_df.iterrows():
        print(f"  {t['entry_time']} | {t['side']:5} | Entry: ${t['entry_price']:.6f} | "
              f"Exit: ${t['exit_price']:.6f} | {t['exit_reason']} | {t['pnl_pct']:+.2f}%")

print("\n" + "=" * 60)
