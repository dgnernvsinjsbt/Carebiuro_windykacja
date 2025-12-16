#!/usr/bin/env python3
"""Detailed month-by-month analysis for 0.8 ATR config"""
import pandas as pd
import numpy as np

df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

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

def find_swing_low(df, idx, lookback):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['low'].min()

def find_swing_high(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['high'].max()

# Fixed config: 0.8 ATR
limit_atr_offset = 0.8
rsi_trigger = 72
lookback = 5
tp_pct = 5
max_wait_bars = 20

equity = 100.0
trades = []

armed = False
signal_idx = None
swing_low = None
limit_pending = False
limit_price = None
limit_placed_idx = None
swing_high_for_sl = None

for i in range(lookback, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        continue

    # Check if RSI triggered
    if row['rsi'] > rsi_trigger:
        armed = True
        signal_idx = i
        swing_low = find_swing_low(df, i, lookback)
        limit_pending = False

    # If armed, wait for break below swing low
    if armed and swing_low is not None and not limit_pending:
        if row['low'] < swing_low:
            atr = row['atr']
            limit_price = swing_low + (atr * limit_atr_offset)
            swing_high_for_sl = find_swing_high(df, signal_idx, i)
            limit_pending = True
            limit_placed_idx = i
            armed = False

    # Check if limit order fills
    if limit_pending:
        if i - limit_placed_idx > max_wait_bars:
            limit_pending = False
            continue

        if row['high'] >= limit_price:
            entry_price = limit_price
            sl_price = swing_high_for_sl
            tp_price = entry_price * (1 - tp_pct / 100)

            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

            if sl_dist_pct <= 0 or sl_dist_pct > 10:
                limit_pending = False
                continue

            size = (equity * 0.05) / (sl_dist_pct / 100)

            # Find exit
            hit_sl = False
            hit_tp = False
            exit_bar = None

            for j in range(i + 1, min(i + 500, len(df))):
                future_row = df.iloc[j]

                if future_row['high'] >= sl_price:
                    hit_sl = True
                    exit_bar = j
                    break
                elif future_row['low'] <= tp_price:
                    hit_tp = True
                    exit_bar = j
                    break

            if hit_sl:
                pnl_pct = -sl_dist_pct
                exit_reason = 'SL'
            elif hit_tp:
                pnl_pct = tp_pct
                exit_reason = 'TP'
            else:
                continue

            pnl_dollar = size * (pnl_pct / 100) - size * 0.001
            equity += pnl_dollar

            trades.append({
                'signal_time': df.iloc[signal_idx]['timestamp'],
                'entry_time': row['timestamp'],
                'exit_time': df.iloc[exit_bar]['timestamp'] if exit_bar else None,
                'entry_price': entry_price,
                'pnl_dollar': pnl_dollar,
                'pnl_pct': pnl_pct,
                'exit_reason': exit_reason
            })

            limit_pending = False

trades_df = pd.DataFrame(trades)
trades_df['signal_time'] = pd.to_datetime(trades_df['signal_time'])
trades_df['month'] = trades_df['signal_time'].dt.to_period('M')

print("=" * 90)
print("MONTH-BY-MONTH BREAKDOWN (0.8 ATR CONFIG)")
print("=" * 90)
print()

months = ['2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12']
month_names = ['Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

results = []

for month, name in zip(months, month_names):
    month_trades = trades_df[trades_df['month'] == month]

    if len(month_trades) == 0:
        results.append({
            'month': name,
            'trades': 0,
            'win_rate': 0,
            'pnl': 0,
            'max_dd': 0,
            'return_dd': 0
        })
        continue

    # Calculate monthly metrics
    total_pnl = month_trades['pnl_dollar'].sum()
    winners = month_trades[month_trades['pnl_dollar'] > 0]
    win_rate = (len(winners) / len(month_trades)) * 100

    # Calculate max DD for this month
    equity_curve = [0]
    for pnl in month_trades['pnl_dollar']:
        equity_curve.append(equity_curve[-1] + pnl)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = eq_series - running_max
    max_dd = drawdown.min()

    # Calculate return/DD ratio
    if max_dd < 0:
        return_dd = total_pnl / abs(max_dd)
    else:
        return_dd = 999 if total_pnl > 0 else 0

    results.append({
        'month': name,
        'trades': len(month_trades),
        'win_rate': win_rate,
        'pnl': total_pnl,
        'max_dd': max_dd,
        'return_dd': return_dd
    })

# Print table
print(f"{'Month':<6} {'Trades':>7} {'Win%':>7} {'P&L':>10} {'MaxDD':>10} {'R:DD':>8}")
print("-" * 90)

for r in results:
    status = "✅" if r['pnl'] > 0 else "❌" if r['pnl'] < 0 else "⚪"
    print(f"{r['month']:<6} {r['trades']:>7} {r['win_rate']:>6.1f}% "
          f"${r['pnl']:>+9.2f} ${r['max_dd']:>9.2f} {r['return_dd']:>7.2f}x {status}")

print("-" * 90)

# Overall summary
total_trades = len(trades_df)
total_pnl = trades_df['pnl_dollar'].sum()
overall_win_rate = (len(trades_df[trades_df['pnl_dollar'] > 0]) / total_trades) * 100

# Overall max DD
equity_curve = [100]
for pnl in trades_df['pnl_dollar']:
    equity_curve.append(equity_curve[-1] + pnl)

eq_series = pd.Series(equity_curve)
running_max = eq_series.expanding().max()
drawdown = (eq_series - running_max) / running_max * 100
overall_max_dd = drawdown.min()

total_return = ((equity_curve[-1] - 100) / 100) * 100
overall_rdd = total_return / abs(overall_max_dd) if overall_max_dd != 0 else 0

print(f"{'TOTAL':<6} {total_trades:>7} {overall_win_rate:>6.1f}% "
      f"${total_pnl:>+9.2f} {overall_max_dd:>9.2f}% {overall_rdd:>7.2f}x")
print()

# Monthly insights
print("=" * 90)
print("KEY INSIGHTS")
print("=" * 90)

profitable_months = [r for r in results if r['pnl'] > 0]
losing_months = [r for r in results if r['pnl'] < 0]

print(f"✅ Profitable months: {len(profitable_months)}/7")
print(f"❌ Losing months: {len(losing_months)}/7")
print()

if losing_months:
    print("Worst performing months:")
    for r in sorted(losing_months, key=lambda x: x['pnl']):
        print(f"  {r['month']}: ${r['pnl']:+.2f} ({r['trades']} trades, {r['win_rate']:.1f}% win rate)")
    print()

if profitable_months:
    print("Best performing months:")
    for r in sorted(profitable_months, key=lambda x: x['pnl'], reverse=True)[:3]:
        print(f"  {r['month']}: ${r['pnl']:+.2f} ({r['trades']} trades, {r['win_rate']:.1f}% win rate)")
