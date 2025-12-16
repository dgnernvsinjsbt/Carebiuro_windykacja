#!/usr/bin/env python3
"""Minimal FARTCOIN test - 10 configs"""
import pandas as pd
import numpy as np
import time

start = time.time()

df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
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

print(f"Data loaded: {len(df)} rows ({time.time()-start:.1f}s)")

def test(rsi_trigger, limit_atr_offset, tp_pct):
    lookback = 5
    max_wait_bars = 20
    equity = 100.0
    trades = []
    armed = False
    signal_idx = None
    swing_low = None
    limit_pending = False
    limit_placed_idx = None
    swing_high_for_sl = None

    for i in range(lookback, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            continue

        if row['rsi'] > rsi_trigger:
            armed = True
            signal_idx = i
            swing_low = df.iloc[max(0, i-lookback):i+1]['low'].min()
            limit_pending = False

        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                atr = row['atr']
                limit_price = swing_low + (atr * limit_atr_offset)
                swing_high_for_sl = df.iloc[signal_idx:i+1]['high'].max()
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
                trades.append({'time': df.iloc[signal_idx]['timestamp'], 'pnl': pnl_dollar})
                limit_pending = False

    if len(trades) < 5:
        return None

    trades_df = pd.DataFrame(trades)
    trades_df['month'] = pd.to_datetime(trades_df['time']).dt.to_period('M')
    monthly_pnl = {}
    for month in trades_df['month'].unique():
        monthly_pnl[str(month)] = trades_df[trades_df['month'] == month]['pnl'].sum()

    total_return = ((equity - 100) / 100) * 100
    equity_curve = [100.0]
    for pnl in trades_df['pnl']:
        equity_curve.append(equity_curve[-1] + pnl)
    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = len(trades_df[trades_df['pnl'] > 0])
    win_rate = winners / len(trades_df) * 100
    profitable_months = sum([1 for v in monthly_pnl.values() if v > 0])

    return {
        'rsi': rsi_trigger, 'offset': limit_atr_offset, 'tp': tp_pct,
        'return': total_return, 'max_dd': max_dd, 'return_dd': return_dd,
        'trades': len(trades_df), 'win_rate': win_rate, 'profitable_months': profitable_months,
        'monthly': monthly_pnl
    }

print("\nTesting 10 configs: RSI 70/72 × offset 0.6/0.8/1.0 × TP 8/9/10%")
results = []
for rsi in [70, 72]:
    for offset in [0.6, 0.8, 1.0]:
        for tp in [8, 9, 10]:
            if len(results) >= 10:
                break
            r = test(rsi, offset, tp)
            if r:
                results.append(r)
                print(f"  RSI{r['rsi']} {r['offset']}ATR {r['tp']}% → {r['return_dd']:.2f}x ({time.time()-start:.0f}s)")

if results:
    results.sort(key=lambda x: x['return_dd'], reverse=True)
    w = results[0]
    print(f"\n{'='*90}")
    print(f"FARTCOIN BEST: RSI>{w['rsi']} | {w['offset']:.1f}ATR | TP{w['tp']}%")
    print(f"{'='*90}")
    print(f"Return/DD: {w['return_dd']:.2f}x")
    print(f"Return: {w['return']:+.2f}%")
    print(f"Max DD: {w['max_dd']:.2f}%")
    print(f"Trades: {w['trades']}")
    print(f"Win Rate: {w['win_rate']:.1f}%")
    print(f"Profitable Months: {w['profitable_months']}/6")
    print("\nMonthly:")
    for m, p in sorted(w['monthly'].items()):
        mark = "✓" if p > 0 else "✗"
        print(f"  {mark} {m}: ${p:+.2f}")

print(f"\nTotal: {time.time()-start:.1f}s")
