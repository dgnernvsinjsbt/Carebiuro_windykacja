#!/usr/bin/env python3
"""
Test MELANIA RSI Optimized - SHORT ONLY on 6 months BingX data
"""
import pandas as pd
import numpy as np

# Load BingX data
df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

print("=" * 70)
print("MELANIA RSI OPTIMIZED - SHORT ONLY (6 MONTHS BINGX)")
print("=" * 70)
print(f"Data: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Candles: {len(df)}")
print(f"Period: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
print()

# Calculate indicators
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()

df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

df['ret_4h'] = (df['close'] - df['close'].shift(16)) / df['close'].shift(16) * 100
df['ret_4h_abs'] = abs(df['ret_4h'])
df['avg_move_size'] = df['ret_4h_abs'].rolling(96).mean()

# Strategy parameters
rsi_overbought = 65
limit_offset_atr = 0.1
stop_loss_atr = 1.2
take_profit_atr = 3.0
max_wait_bars = 8
min_move_size = 0.8

# Dynamic sizing
initial_risk = 0.12
current_risk = 0.12
min_risk = 0.02
max_risk = 0.30
win_multiplier = 1.5
loss_multiplier = 0.5

# Backtest
equity = 100.0
equity_curve = [equity]
trades = []
position = None
pending_order = None

for i in range(300, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']) or pd.isna(row['avg_move_size']):
        continue

    # Check pending order
    if pending_order:
        bars_waiting = i - pending_order['signal_bar']
        if bars_waiting > max_wait_bars:
            pending_order = None
            continue

        if row['high'] >= pending_order['limit_price']:
            position = {
                'entry': pending_order['limit_price'],
                'sl_price': pending_order['sl_price'],
                'tp_price': pending_order['tp_price'],
                'size': pending_order['size'],
                'entry_bar': i
            }
            pending_order = None

    # Check exit
    if position:
        pnl_pct = None
        exit_reason = None

        if row['high'] >= position['sl_price']:
            pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
            exit_reason = 'SL'
        elif row['low'] <= position['tp_price']:
            pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
            exit_reason = 'TP'

        if pnl_pct is not None:
            pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
            equity += pnl_dollar
            equity_curve.append(equity)

            trades.append({
                'entry_time': df.iloc[position['entry_bar']]['timestamp'],
                'exit_time': row['timestamp'],
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'risk_pct': current_risk * 100,
                'exit_reason': exit_reason
            })

            won = pnl_pct > 0
            if won:
                current_risk = min(current_risk * win_multiplier, max_risk)
            else:
                current_risk = max(current_risk * loss_multiplier, min_risk)

            position = None
            continue

    # Generate SHORT signals only
    if not position and not pending_order and i > 0:
        prev_row = df.iloc[i-1]

        if row['ret_20'] <= 0 or pd.isna(prev_row['rsi']):
            continue

        signal_price = row['close']
        atr = row['atr']

        # SHORT signal: RSI crosses below 65
        if prev_row['rsi'] > rsi_overbought and row['rsi'] <= rsi_overbought:
            if row['avg_move_size'] >= min_move_size:
                limit_price = signal_price + (atr * limit_offset_atr)
                sl_price = limit_price + (atr * stop_loss_atr)
                tp_price = limit_price - (atr * take_profit_atr)
                sl_dist = abs((sl_price - limit_price) / limit_price) * 100
                size = (equity * current_risk) / (sl_dist / 100)

                pending_order = {
                    'limit_price': limit_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'signal_bar': i
                }

# Results
if trades:
    trades_df = pd.DataFrame(trades)

    total_return = ((equity - 100) / 100) * 100

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = trades_df[trades_df['pnl_dollar'] > 0]
    losers = trades_df[trades_df['pnl_dollar'] <= 0]

    win_rate = len(winners) / len(trades_df) * 100

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total Return: {total_return:+.1f}%")
    print(f"Final Equity: ${equity:.2f}")
    print(f"Max Drawdown: {max_dd:.2f}%")
    print(f"Return/DD Ratio: {return_dd:.2f}x")
    print()
    print(f"Total Trades: {len(trades_df)}")
    print(f"Win Rate: {win_rate:.1f}% ({len(winners)}W / {len(losers)}L)")
    print(f"  TP: {len(trades_df[trades_df['exit_reason'] == 'TP'])} ({len(trades_df[trades_df['exit_reason'] == 'TP'])/len(trades_df)*100:.1f}%)")
    print(f"  SL: {len(trades_df[trades_df['exit_reason'] == 'SL'])} ({len(trades_df[trades_df['exit_reason'] == 'SL'])/len(trades_df)*100:.1f}%)")
    print()
    print(f"Avg Win: +${winners['pnl_dollar'].mean():.2f}" if len(winners) > 0 else "Avg Win: N/A")
    print(f"Avg Loss: ${losers['pnl_dollar'].mean():.2f}" if len(losers) > 0 else "Avg Loss: N/A")

    if len(winners) > 0 and len(losers) > 0:
        print(f"Win/Loss Ratio: {winners['pnl_dollar'].mean() / abs(losers['pnl_dollar'].mean()):.2f}:1")

    print()
    print("=" * 70)
    print("MONTHLY BREAKDOWN")
    print("=" * 70)

    trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.to_period('M')

    for month in trades_df['month'].unique():
        month_trades = trades_df[trades_df['month'] == month]
        month_winners = month_trades[month_trades['pnl_dollar'] > 0]
        month_profit = month_trades['pnl_dollar'].sum()

        print(f"{month}: {len(month_trades)} trades, {len(month_winners)}/{len(month_trades)-len(month_winners)} W/L, P&L: ${month_profit:+.2f}")

    print("=" * 70)

    trades_df.to_csv('melania_6months_short_only.csv', index=False)
    print(f"\n💾 Trades saved to melania_6months_short_only.csv")
else:
    print("\n❌ No trades")
