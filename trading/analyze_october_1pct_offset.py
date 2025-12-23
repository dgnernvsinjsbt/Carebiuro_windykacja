#!/usr/bin/env python3
"""
Analyze October +1032% return in detail
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

# Momentum
df['momentum_4h'] = ((df['close'] - df['close'].shift(16)) / df['close'].shift(16)) * 100

# MA
df['ma_20'] = df['close'].rolling(window=20).mean()
df['dist_from_ma'] = ((df['close'] - df['ma_20']) / df['ma_20']) * 100

# October only
df_oct = df[(df['timestamp'] >= '2025-10-01') & (df['timestamp'] < '2025-11-01')].copy().reset_index(drop=True)

print("="*140)
print("OCTOBER +1032% ANALYSIS - 1.0% Limit Offset")
print("="*140)
print()

# Strategy params
mom_thresh = -2.5
ma_thresh = -1.0
tp_pct = 3.0
lookback = 8
max_wait_bars = 16
offset_pct = 1.0

equity = 100.0
trades = []

is_busy = False
pending_limit = None
pending_signal_bar = None
pending_sl = None
pending_tp = None

i = max(20, lookback)
while i < len(df_oct):
    row = df_oct.iloc[i]

    if pd.isna(row['momentum_4h']) or pd.isna(row['dist_from_ma']) or pd.isna(row['atr']):
        i += 1
        continue

    # If pending limit
    if is_busy and pending_limit is not None:
        bars_waiting = i - pending_signal_bar

        # Check if filled (HIGH >= limit for SHORT)
        if row['high'] >= pending_limit:
            entry_price = pending_limit
            sl_dist_pct = ((pending_sl - entry_price) / entry_price) * 100

            if sl_dist_pct > 0 and sl_dist_pct <= 10.0:
                position_size = (equity * 5.0) / sl_dist_pct
                equity_before = equity

                # Find exit
                hit_sl = False
                hit_tp = False
                exit_bar = None

                for k in range(i + 1, min(i + 100, len(df_oct))):
                    exit_row = df_oct.iloc[k]

                    if exit_row['high'] >= pending_sl:
                        hit_sl = True
                        exit_bar = k
                        break
                    elif exit_row['low'] <= pending_tp:
                        hit_tp = True
                        exit_bar = k
                        break

                if exit_bar:
                    hold_bars = exit_bar - i

                    if hit_sl:
                        pnl_pct = -sl_dist_pct
                    else:
                        tp_dist_pct = ((entry_price - pending_tp) / entry_price) * 100
                        pnl_pct = tp_dist_pct

                    pnl_dollar = position_size * (pnl_pct / 100)
                    equity += pnl_dollar

                    trades.append({
                        'entry_time': row['timestamp'],
                        'entry_price': entry_price,
                        'exit_time': df_oct.iloc[exit_bar]['timestamp'],
                        'sl_price': pending_sl,
                        'tp_price': pending_tp,
                        'sl_dist_pct': sl_dist_pct,
                        'result': 'TP' if hit_tp else 'SL',
                        'hold_bars': hold_bars,
                        'position_size': position_size,
                        'pnl_pct': pnl_pct,
                        'pnl_dollar': pnl_dollar,
                        'equity_before': equity_before,
                        'equity_after': equity
                    })

                    i = exit_bar

            is_busy = False
            pending_limit = None

        elif row['high'] >= pending_sl:
            is_busy = False
            pending_limit = None

        elif bars_waiting >= max_wait_bars:
            is_busy = False
            pending_limit = None

        i += 1
        continue

    # Check for new signal
    if not is_busy:
        if row['momentum_4h'] < mom_thresh and row['dist_from_ma'] < ma_thresh:
            swing_high = df_oct.iloc[max(0, i-lookback):i]['high'].max()

            signal_price = row['close']
            sl_price = swing_high
            tp_price = signal_price * (1 - tp_pct / 100)
            limit_price = signal_price * (1 + offset_pct / 100)

            if limit_price < sl_price:
                is_busy = True
                pending_limit = limit_price
                pending_signal_bar = i
                pending_sl = sl_price
                pending_tp = tp_price

    i += 1

# Analysis
trades_df = pd.DataFrame(trades)

print(f"Total Trades: {len(trades_df)}")
print(f"Starting Equity: $100.00")
print(f"Ending Equity: ${equity:.2f}")
print(f"Total Return: {((equity - 100) / 100) * 100:.1f}%")
print()

winners = trades_df[trades_df['pnl_dollar'] > 0]
losers = trades_df[trades_df['pnl_dollar'] < 0]

print(f"Winners: {len(winners)} ({len(winners)/len(trades_df)*100:.1f}%)")
print(f"Losers: {len(losers)} ({len(losers)/len(trades_df)*100:.1f}%)")
print()

print("="*140)
print("TRADE-BY-TRADE BREAKDOWN")
print("="*140)
print(f"{'#':<4} | {'Date':<12} | {'Entry':<10} | {'Exit':<10} | {'Result':<6} | {'Hold':<6} | {'Pos Size':<12} | {'P&L $':<12} | {'Equity After':<15}")
print("-"*140)

for idx, t in trades_df.iterrows():
    entry_date = t['entry_time'].strftime('%m-%d %H:%M')
    exit_date = t['exit_time'].strftime('%m-%d %H:%M')

    print(f"{idx+1:<4} | {entry_date:<12} | ${t['entry_price']:.6f} | ${t['exit_time']:<10} | {t['result']:<6} | {t['hold_bars']:>4}b | ${t['position_size']:>10.2f} | ${t['pnl_dollar']:>+10.2f} | ${t['equity_after']:>13.2f}")

print()
print("="*140)
print("KEY INSIGHTS")
print("="*140)
print()

# Find biggest winners
top_5_winners = trades_df.nlargest(5, 'pnl_dollar')
print("TOP 5 WINNING TRADES:")
for idx, t in top_5_winners.iterrows():
    contribution = (t['pnl_dollar'] / (equity - 100)) * 100
    print(f"  #{idx+1}: {t['entry_time'].strftime('%m-%d %H:%M')} | ${t['pnl_dollar']:+.2f} | {contribution:.1f}% of total profit | Equity: ${t['equity_before']:.2f} → ${t['equity_after']:.2f}")

print()

# Analyze compounding effect
print("COMPOUNDING ANALYSIS:")
print(f"  Avg position size: ${trades_df['position_size'].mean():.2f}")
print(f"  First trade position: ${trades_df.iloc[0]['position_size']:.2f}")
print(f"  Last trade position: ${trades_df.iloc[-1]['position_size']:.2f}")
print(f"  Position size growth: {(trades_df.iloc[-1]['position_size'] / trades_df.iloc[0]['position_size'] - 1) * 100:.0f}%")
print()

# Cumulative equity curve
print("EQUITY MILESTONES:")
milestones = [200, 300, 500, 1000]
for milestone in milestones:
    crossed = trades_df[trades_df['equity_after'] >= milestone]
    if len(crossed) > 0:
        first_cross = crossed.iloc[0]
        print(f"  Crossed ${milestone}: Trade #{crossed.index[0]+1} on {first_cross['entry_time'].strftime('%m-%d %H:%M')}")

print()
print("="*140)
print()

# Win rate by week
trades_df['week'] = trades_df['entry_time'].dt.isocalendar().week
print("WEEKLY PERFORMANCE:")
for week, group in trades_df.groupby('week'):
    week_winners = group[group['pnl_dollar'] > 0]
    week_return = ((group.iloc[-1]['equity_after'] / group.iloc[0]['equity_before']) - 1) * 100
    print(f"  Week {week}: {len(group)} trades | {len(week_winners)} wins ({len(week_winners)/len(group)*100:.0f}% WR) | Return: {week_return:+.1f}%")

print("="*140)
