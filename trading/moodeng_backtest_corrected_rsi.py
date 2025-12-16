"""
MOODENG RSI Swing Backtest - WITH CORRECTED RSI

Re-run with same parameters but using fixed Wilder's RSI calculation
Compare results to original buggy version
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'bingx-trading-bot'))
from data.indicators import rsi, atr


# Original parameters from optimization
RSI_LOW = 27
RSI_HIGH = 65
LIMIT_OFFSET_PCT = 2.0
STOP_ATR_MULT = 1.5
TP_ATR_MULT = 1.5
MAX_WAIT_BARS = 5
FEES = 0.001  # 0.1% per trade (0.05% taker x2)

print("=" * 100)
print("MOODENG RSI SWING BACKTEST - CORRECTED RSI")
print("=" * 100)
print(f"RSI Thresholds: {RSI_LOW} / {RSI_HIGH}")
print(f"Limit Offset: {LIMIT_OFFSET_PCT}%")
print(f"Stop Loss: {STOP_ATR_MULT}x ATR")
print(f"Take Profit: {TP_ATR_MULT}x ATR")
print(f"Max Wait: {MAX_WAIT_BARS} bars")
print(f"Fees: {FEES*100}% per trade")
print("=" * 100)

# Load data (90-day 1h data)
df_1h = pd.read_csv('bingx-trading-bot/trading/moodeng_usdt_90d_1h.csv')
df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
df_1h = df_1h.sort_values('timestamp').reset_index(drop=True)

print(f"\nData: {len(df_1h)} 1h candles")
print(f"Period: {df_1h['timestamp'].min()} to {df_1h['timestamp'].max()}")

# Calculate indicators using CORRECTED RSI
df_1h['rsi'] = rsi(df_1h['close'], 14)
df_1h['atr'] = atr(df_1h['high'], df_1h['low'], df_1h['close'], 14)

# Backtest
capital = 100.0
position = None
pending_order = None
trades = []
equity_curve = [capital]

for i in range(1, len(df_1h)):
    bar = df_1h.iloc[i]
    prev_bar = df_1h.iloc[i-1]

    # Check if we have valid indicators
    if pd.isna(bar['rsi']) or pd.isna(bar['atr']):
        equity_curve.append(equity_curve[-1])
        continue

    # Check pending limit order
    if pending_order is not None:
        bars_waiting = i - pending_order['signal_bar']

        # Check if limit order filled
        filled = False
        if pending_order['side'] == 'LONG':
            if bar['low'] <= pending_order['limit_price']:
                filled = True
        else:  # SHORT
            if bar['high'] >= pending_order['limit_price']:
                filled = True

        if filled:
            # Limit order filled!
            position = {
                'side': pending_order['side'],
                'entry_bar': i,
                'entry_price': pending_order['limit_price'],
                'stop_loss': pending_order['stop_loss'],
                'take_profit': pending_order['take_profit'],
                'size': capital * 0.10  # 10% of capital per trade
            }
            pending_order = None
        elif bars_waiting >= MAX_WAIT_BARS:
            # Timeout - cancel pending order
            pending_order = None

    # Check existing position
    if position is not None:
        exit_price = None
        exit_reason = None

        # Check stop loss
        if position['side'] == 'LONG':
            if bar['low'] <= position['stop_loss']:
                exit_price = position['stop_loss']
                exit_reason = 'Stop Loss'
        else:  # SHORT
            if bar['high'] >= position['stop_loss']:
                exit_price = position['stop_loss']
                exit_reason = 'Stop Loss'

        # Check take profit
        if exit_price is None:
            if position['side'] == 'LONG':
                if bar['high'] >= position['take_profit']:
                    exit_price = position['take_profit']
                    exit_reason = 'Take Profit'
            else:  # SHORT
                if bar['low'] <= position['take_profit']:
                    exit_price = position['take_profit']
                    exit_reason = 'Take Profit'

        # Check RSI exit
        if exit_price is None:
            if position['side'] == 'LONG':
                if bar['rsi'] < RSI_HIGH and prev_bar['rsi'] >= RSI_HIGH:
                    exit_price = bar['close']
                    exit_reason = 'RSI Exit'
            else:  # SHORT
                if bar['rsi'] > RSI_LOW and prev_bar['rsi'] <= RSI_LOW:
                    exit_price = bar['close']
                    exit_reason = 'RSI Exit'

        # Exit position
        if exit_price is not None:
            if position['side'] == 'LONG':
                pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
            else:  # SHORT
                pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']

            # Apply fees (entry + exit)
            pnl_pct -= (FEES * 2)

            pnl = position['size'] * pnl_pct
            capital += pnl

            trades.append({
                'entry_time': df_1h.iloc[position['entry_bar']]['timestamp'],
                'exit_time': bar['timestamp'],
                'side': position['side'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'pnl': pnl,
                'pnl_pct': pnl_pct * 100,
                'exit_reason': exit_reason,
                'bars_held': i - position['entry_bar']
            })

            position = None

    # Generate new signals (only if no position and no pending order)
    if position is None and pending_order is None:
        # LONG signal: RSI crosses above threshold
        if bar['rsi'] > RSI_LOW and prev_bar['rsi'] <= RSI_LOW:
            signal_price = bar['close']
            limit_price = signal_price * (1 - LIMIT_OFFSET_PCT / 100)
            stop_loss = limit_price - (STOP_ATR_MULT * bar['atr'])
            take_profit = limit_price + (TP_ATR_MULT * bar['atr'])

            pending_order = {
                'side': 'LONG',
                'signal_bar': i,
                'limit_price': limit_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }

        # SHORT signal: RSI crosses below threshold
        elif bar['rsi'] < RSI_HIGH and prev_bar['rsi'] >= RSI_HIGH:
            signal_price = bar['close']
            limit_price = signal_price * (1 + LIMIT_OFFSET_PCT / 100)
            stop_loss = limit_price + (STOP_ATR_MULT * bar['atr'])
            take_profit = limit_price - (TP_ATR_MULT * bar['atr'])

            pending_order = {
                'side': 'SHORT',
                'signal_bar': i,
                'limit_price': limit_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }

    equity_curve.append(capital)

# Calculate statistics
trades_df = pd.DataFrame(trades)

if len(trades_df) > 0:
    total_return = ((capital - 100) / 100) * 100
    winning_trades = trades_df[trades_df['pnl'] > 0]
    losing_trades = trades_df[trades_df['pnl'] < 0]

    win_rate = (len(winning_trades) / len(trades_df)) * 100

    # Calculate drawdown
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = ((equity_series - running_max) / running_max) * 100
    max_drawdown = drawdown.min()

    return_dd_ratio = abs(total_return / max_drawdown) if max_drawdown != 0 else 0

    print("\n" + "=" * 100)
    print("RESULTS - CORRECTED RSI")
    print("=" * 100)
    print(f"Total Trades: {len(trades_df)}")
    print(f"Winning Trades: {len(winning_trades)}")
    print(f"Losing Trades: {len(losing_trades)}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"\nTotal Return: {total_return:+.2f}%")
    print(f"Max Drawdown: {max_drawdown:.2f}%")
    print(f"Return/DD Ratio: {return_dd_ratio:.2f}x")
    print(f"\nFinal Capital: ${capital:.2f}")

    if len(winning_trades) > 0:
        print(f"Avg Win: {winning_trades['pnl_pct'].mean():.2f}%")
    if len(losing_trades) > 0:
        print(f"Avg Loss: {losing_trades['pnl_pct'].mean():.2f}%")

    # Compare to original
    print("\n" + "=" * 100)
    print("COMPARISON TO ORIGINAL (BUGGY RSI)")
    print("=" * 100)
    print(f"Original Trades: 31")
    print(f"Corrected Trades: {len(trades_df)} ({len(trades_df) - 31:+d})")
    print(f"\nOriginal Return: +96.998%")
    print(f"Corrected Return: {total_return:+.2f}% ({total_return - 96.998:+.2f}%)")
    print(f"\nOriginal Max DD: -3.598%")
    print(f"Corrected Max DD: {max_drawdown:.2f}% ({max_drawdown + 3.598:+.2f}%)")
    print(f"\nOriginal R/R: 26.96x")
    print(f"Corrected R/R: {return_dd_ratio:.2f}x ({return_dd_ratio - 26.96:+.2f}x)")
    print(f"\nOriginal Win Rate: 90.32%")
    print(f"Corrected Win Rate: {win_rate:.2f}% ({win_rate - 90.32:+.2f}%)")

    # Save trades
    trades_df.to_csv('moodeng_corrected_rsi_trades.csv', index=False)
    print(f"\n✅ Trades saved to moodeng_corrected_rsi_trades.csv")

    # Show first 10 trades
    print("\n" + "=" * 100)
    print("FIRST 10 TRADES")
    print("=" * 100)
    for idx, trade in trades_df.head(10).iterrows():
        print(f"{trade['entry_time']} {trade['side']:<5} "
              f"Entry: ${trade['entry_price']:.6f} Exit: ${trade['exit_price']:.6f} "
              f"P&L: {trade['pnl_pct']:+.2f}% ({trade['exit_reason']})")

    print("=" * 100)
else:
    print("\n❌ No trades generated!")
