#!/usr/bin/env python3
"""Test SHORT reversal strategy on MOODENG with progress output"""
import pandas as pd
import numpy as np
import sys

df = pd.read_csv('moodeng_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

print(f"Loaded {len(df)} bars", flush=True)

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

print("Indicators computed", flush=True)

def find_swing_low(df, idx, lookback):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['low'].min()

def find_swing_high(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['high'].max()

def test(rsi_trigger, limit_atr_offset, tp_pct):
    lookback = 5
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

        if row['rsi'] > rsi_trigger:
            armed = True
            signal_idx = i
            swing_low = find_swing_low(df, i, lookback)
            limit_pending = False

        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                atr = row['atr']
                limit_price = swing_low + (atr * limit_atr_offset)
                swing_high_for_sl = find_swing_high(df, signal_idx, i)
                limit_pending = True
                limit_placed_idx = i
                armed = False

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
                hit_sl = False
                hit_tp = False

                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]
                    if future_row['high'] >= sl_price:
                        hit_sl = True
                        break
                    elif future_row['low'] <= tp_price:
                        hit_tp = True
                        break

                if hit_sl:
                    pnl_pct = -sl_dist_pct
                elif hit_tp:
                    pnl_pct = tp_pct
                else:
                    continue

                pnl_dollar = size * (pnl_pct / 100) - size * 0.001
                equity += pnl_dollar
                trades.append({'signal_time': df.iloc[signal_idx]['timestamp'], 'pnl_dollar': pnl_dollar})
                limit_pending = False

    if len(trades) < 5:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df['signal_time'] = pd.to_datetime(trades_df['signal_time'])
    trades_df['month'] = trades_df['signal_time'].dt.to_period('M')
    monthly_pnl = {}
    for month in trades_df['month'].unique():
        monthly_pnl[str(month)] = trades_df[trades_df['month'] == month]['pnl_dollar'].sum()

    total_return = ((equity - 100) / 100) * 100
    equity_curve = [100.0]
    for pnl in trades_df['pnl_dollar']:
        equity_curve[-1] += pnl
        equity_curve.append(equity_curve[-1])
    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = trades_df[trades_df['pnl_dollar'] > 0]
    win_rate = len(winners) / len(trades_df) * 100
    profitable_months = sum([1 for v in monthly_pnl.values() if v > 0])

    return {
        'rsi': rsi_trigger, 'offset': limit_atr_offset, 'tp': tp_pct,
        'return': total_return, 'max_dd': max_dd, 'return_dd': return_dd,
        'trades': len(trades_df), 'win_rate': win_rate, 'profitable_months': profitable_months,
        'monthly': monthly_pnl
    }

print("\nMOODENG SHORT REVERSAL TEST", flush=True)
print("Testing 120 configs (5 RSI × 4 offset × 6 TP)...", flush=True)

results = []
config_count = 0
total_configs = 5 * 4 * 6  # 120 total

for rsi in [68, 70, 72, 74, 76]:
    for offset in [0.4, 0.6, 0.8, 1.0]:
        for tp in [5, 6, 7, 8, 9, 10]:
            config_count += 1
            sys.stdout.write(f"\rProcessing config {config_count}/{total_configs}...")
            sys.stdout.flush()

            r = test(rsi, offset, tp)
            if r:
                results.append(r)

print(f"\n\nCompleted {len(results)} profitable configs out of {total_configs}\n", flush=True)

if results:
    results.sort(key=lambda x: x['return_dd'], reverse=True)
    print(f"TOP 5 CONFIGS BY R/DD RATIO:\n")
    for i, r in enumerate(results[:5], 1):
        print(f"#{i} RSI>{r['rsi']} {r['offset']:.1f}ATR {r['tp']}% | R/DD:{r['return_dd']:.2f}x Ret:{r['return']:+.1f}% DD:{r['max_dd']:.2f}% {r['trades']}tr {r['win_rate']:.1f}% {r['profitable_months']}/7mo")

    print(f"\n" + "="*90)
    w = results[0]
    print(f"\nBEST CONFIG: RSI>{w['rsi']} Offset:{w['offset']:.1f}xATR TP:{w['tp']}%")
    print(f"  Return/DD Ratio: {w['return_dd']:.2f}x")
    print(f"  Total Return: {w['return']:+.2f}%")
    print(f"  Max Drawdown: {w['max_dd']:.2f}%")
    print(f"  Trades: {w['trades']}")
    print(f"  Win Rate: {w['win_rate']:.1f}%")
    print(f"  Profitable Months: {w['profitable_months']}/7\n")
    print("MONTHLY BREAKDOWN:")
    for m, p in sorted(w['monthly'].items()):
        print(f"  {m}: ${p:+.2f}")
else:
    print("No profitable configs found")
