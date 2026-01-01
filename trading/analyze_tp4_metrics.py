#!/usr/bin/env python3
"""
Comprehensive metrics for TP 4% strategy
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

df['month'] = df['timestamp'].dt.to_period('M')

offset_pct = 1.0
tp_pct = 4.0
test_months = ['2025-09', '2025-10', '2025-11', '2025-12']

monthly_results = []

for month_str in test_months:
    df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

    equity = 100.0
    peak_equity = 100.0
    max_dd = 0.0
    trades = []

    is_busy = False
    pending_limit_price = None
    pending_signal_bar = None
    pending_sl_price = None
    pending_tp_price = None

    i = 32
    while i < len(df_month):
        row = df_month.iloc[i]

        if pd.isna(row['atr']):
            i += 1
            continue

        # If pending limit
        if is_busy and pending_limit_price is not None:
            bars_waiting = i - pending_signal_bar

            if row['high'] >= pending_limit_price:
                entry_price = pending_limit_price
                sl_dist_pct = ((pending_sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                    position_size = (equity * 5.0) / sl_dist_pct
                    entry_bar = i

                    # Find exit
                    hit_sl = False
                    hit_tp = False
                    exit_bar = None

                    for k in range(i + 1, min(i + 100, len(df_month))):
                        exit_row = df_month.iloc[k]

                        if exit_row['high'] >= pending_sl_price:
                            hit_sl = True
                            exit_bar = k
                            break
                        elif exit_row['low'] <= pending_tp_price:
                            hit_tp = True
                            exit_bar = k
                            break

                    if exit_bar:
                        if hit_sl:
                            pnl_pct = -sl_dist_pct
                        else:
                            tp_dist_pct = ((entry_price - pending_tp_price) / entry_price) * 100
                            pnl_pct = tp_dist_pct

                        pnl_dollar = position_size * (pnl_pct / 100)
                        equity += pnl_dollar

                        # Track drawdown
                        if equity > peak_equity:
                            peak_equity = equity
                        dd = ((peak_equity - equity) / peak_equity) * 100
                        if dd > max_dd:
                            max_dd = dd

                        hold_bars = exit_bar - entry_bar
                        hold_minutes = hold_bars * 15

                        trades.append({
                            'pnl_dollar': pnl_dollar,
                            'pnl_pct': pnl_pct,
                            'result': 'TP' if hit_tp else 'SL',
                            'hold_minutes': hold_minutes,
                            'equity_after': equity
                        })

                        i = exit_bar

                is_busy = False
                pending_limit_price = None

            elif row['high'] >= pending_sl_price:
                is_busy = False
                pending_limit_price = None

            elif bars_waiting >= 16:
                is_busy = False
                pending_limit_price = None

            i += 1
            continue

        # Check for new signal
        if not is_busy:
            high_8h = df_month.iloc[max(0, i-32):i]['high'].max()
            dist_pct = ((row['close'] - high_8h) / high_8h) * 100

            if dist_pct <= -2.5:
                signal_price = row['close']
                sl_price = high_8h
                tp_price = signal_price * (1 - tp_pct / 100)
                limit_price = signal_price * (1 + offset_pct / 100)

                if limit_price < sl_price:
                    is_busy = True
                    pending_limit_price = limit_price
                    pending_signal_bar = i
                    pending_sl_price = sl_price
                    pending_tp_price = tp_price

        i += 1

    # Calculate monthly metrics
    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        winners = trades_df[trades_df['pnl_dollar'] > 0]
        losers = trades_df[trades_df['pnl_dollar'] < 0]

        total_return = ((equity - 100) / 100) * 100
        win_rate = (len(winners) / len(trades_df)) * 100

        avg_win = winners['pnl_dollar'].mean() if len(winners) > 0 else 0
        avg_loss = losers['pnl_dollar'].mean() if len(losers) > 0 else 0
        avg_win_time = winners['hold_minutes'].mean() if len(winners) > 0 else 0
        avg_loss_time = losers['hold_minutes'].mean() if len(losers) > 0 else 0
        avg_time_all = trades_df['hold_minutes'].mean()

        return_dd_ratio = total_return / max_dd if max_dd > 0 else 0

        monthly_results.append({
            'month': month_str,
            'total_trades': len(trades_df),
            'wins': len(winners),
            'losses': len(losers),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_profit': equity - 100,
            'total_return': total_return,
            'max_dd': max_dd,
            'return_dd': return_dd_ratio,
            'avg_win_time': avg_win_time,
            'avg_loss_time': avg_loss_time,
            'avg_time_all': avg_time_all
        })

# Display
print("="*160)
print("COMPREHENSIVE TRADING METRICS - TP 4% with 1.0% Offset")
print("="*160)
print()

# Summary table
print(f"{'Month':<10} | {'Trades':<7} | {'Wins':<5} | {'Losses':<7} | {'Win Rate':<9} | {'Total Return':<13} | {'Max DD':<8} | {'R/DD':<7}")
print("-"*160)

for r in monthly_results:
    print(f"{r['month']:<10} | {r['total_trades']:<7} | {r['wins']:<5} | {r['losses']:<7} | {r['win_rate']:>7.1f}% | {r['total_return']:>11.1f}% | {r['max_dd']:>6.1f}% | {r['return_dd']:>5.2f}x")

print()
print("="*160)
print()

# P&L Analysis
print(f"{'Month':<10} | {'Avg Win':<12} | {'Avg Loss':<12} | {'Total Profit':<13}")
print("-"*160)

for r in monthly_results:
    print(f"{r['month']:<10} | ${r['avg_win']:>9.2f} | ${r['avg_loss']:>10.2f} | ${r['total_profit']:>10.2f}")

print()
print("="*160)
print()

# Trade Duration
print(f"{'Month':<10} | {'Avg Win Time':<15} | {'Avg Loss Time':<15} | {'Avg Overall':<15}")
print("-"*160)

for r in monthly_results:
    win_hours = r['avg_win_time'] / 60
    loss_hours = r['avg_loss_time'] / 60
    all_hours = r['avg_time_all'] / 60

    print(f"{r['month']:<10} | {win_hours:>8.1f} hours | {loss_hours:>10.1f} hours | {all_hours:>9.1f} hours")

print()
print("="*160)
print()

# Overall stats
total_trades = sum([r['total_trades'] for r in monthly_results])
total_wins = sum([r['wins'] for r in monthly_results])
total_losses = sum([r['losses'] for r in monthly_results])
overall_wr = (total_wins / total_trades) * 100 if total_trades > 0 else 0

print("OVERALL (Sep-Dec 2025):")
print(f"  Total Trades: {total_trades}")
print(f"  Total Wins: {total_wins}")
print(f"  Total Losses: {total_losses}")
print(f"  Overall Win Rate: {overall_wr:.1f}%")
print()

# Calculate compounded return
compounded_equity = 100.0
for r in monthly_results:
    compounded_equity = compounded_equity * (1 + r['total_return'] / 100)

compounded_return = ((compounded_equity - 100) / 100) * 100
print(f"  Compounded Return (Sep-Dec): {compounded_return:.1f}%")
print(f"  Final Equity: ${compounded_equity:.2f}")

print("="*160)
