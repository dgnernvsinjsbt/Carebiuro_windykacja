#!/usr/bin/env python3
"""FARTCOIN SHORT reversal - Ultra-fast NumPy version"""
import pandas as pd
import numpy as np
import time

print("Loading data...")
df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

print(f"Data: {len(df)} rows")

# Pre-compute RSI
delta = df['close'].diff().values
gain = np.maximum(delta, 0)
loss = -np.minimum(delta, 0)
avg_gain = pd.Series(gain).ewm(alpha=1/14, min_periods=14, adjust=False).mean().values
avg_loss = pd.Series(loss).ewm(alpha=1/14, min_periods=14, adjust=False).mean().values
rs = avg_gain / np.where(avg_loss > 0, avg_loss, np.nan)
rsi_vals = 100 - (100 / (1 + rs))

# Pre-compute ATR
high_vals = df['high'].values
low_vals = df['low'].values
close_vals = df['close'].values
tr = np.maximum(high_vals - low_vals,
                np.maximum(np.abs(high_vals - np.roll(close_vals, 1)),
                          np.abs(low_vals - np.roll(close_vals, 1))))
atr_vals = pd.Series(tr).rolling(14).mean().values
timestamps = df['timestamp'].values

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

    for i in range(lookback, len(high_vals)):
        if np.isnan(rsi_vals[i]) or np.isnan(atr_vals[i]):
            continue

        # Check for RSI trigger
        if rsi_vals[i] > rsi_trigger:
            armed = True
            signal_idx = i
            swing_low = np.min(low_vals[max(0, i-lookback):i+1])
            limit_pending = False

        # Check for limit order setup
        if armed and swing_low is not None and not limit_pending:
            if low_vals[i] < swing_low:
                atr_val = atr_vals[i]
                limit_price = swing_low + (atr_val * limit_atr_offset)
                swing_high_for_sl = np.max(high_vals[signal_idx:i+1])
                limit_pending = True
                limit_placed_idx = i
                armed = False

        # Check for limit fill
        if limit_pending:
            if i - limit_placed_idx > max_wait_bars:
                limit_pending = False
                continue

            if high_vals[i] >= limit_price:
                entry_price = limit_price
                sl_price = swing_high_for_sl
                tp_price = entry_price * (1 - tp_pct / 100)
                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct <= 0 or sl_dist_pct > 10:
                    limit_pending = False
                    continue

                size = (equity * 0.05) / (sl_dist_pct / 100)

                # Search for exit
                hit_sl = False
                hit_tp = False
                search_end = min(i + 500, len(high_vals))

                for j in range(i + 1, search_end):
                    if high_vals[j] >= sl_price:
                        hit_sl = True
                        break
                    elif low_vals[j] <= tp_price:
                        hit_tp = True
                        break

                if hit_sl:
                    pnl_pct = -sl_dist_pct
                elif hit_tp:
                    pnl_pct = tp_pct
                else:
                    limit_pending = False
                    continue

                pnl_dollar = size * (pnl_pct / 100) - size * 0.001
                equity += pnl_dollar
                trades.append({
                    'signal_time': timestamps[signal_idx],
                    'pnl_dollar': pnl_dollar
                })
                limit_pending = False

    if len(trades) < 5:
        return None

    # Post-process results
    trades_df = pd.DataFrame(trades)
    trades_df['month'] = pd.to_datetime(trades_df['signal_time']).dt.to_period('M')

    # Monthly P&L
    monthly_pnl = {}
    for month in trades_df['month'].unique():
        pnl = float(trades_df[trades_df['month'] == month]['pnl_dollar'].sum())
        monthly_pnl[str(month)] = pnl

    # Performance metrics
    total_return = ((equity - 100) / 100) * 100
    pnl_array = trades_df['pnl_dollar'].values
    equity_curve = np.zeros(len(pnl_array) + 1)
    equity_curve[0] = 100.0
    np.cumsum(pnl_array, out=equity_curve[1:])
    equity_curve[1:] += 100

    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - running_max) / running_max * 100
    max_dd = np.min(drawdown)
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    win_rate = (trades_df['pnl_dollar'] > 0).sum() / len(trades_df) * 100
    profitable_months = sum(1 for v in monthly_pnl.values() if v > 0)

    return {
        'rsi': rsi_trigger, 'offset': limit_atr_offset, 'tp': tp_pct,
        'return': total_return, 'max_dd': max_dd, 'return_dd': return_dd,
        'trades': len(trades_df), 'win_rate': win_rate, 'profitable_months': profitable_months,
        'monthly': monthly_pnl
    }

print("\nTesting 120 configs...")
test_start = time.time()
results = []

for rsi in [68, 70, 72, 74, 76]:
    for offset in [0.4, 0.6, 0.8, 1.0]:
        for tp in [5, 6, 7, 8, 9, 10]:
            r = test(rsi, offset, tp)
            if r:
                results.append(r)

elapsed = time.time() - test_start
print(f"Completed in {elapsed:.1f}s ({len(results)}/120 valid configs)")

if results:
    results.sort(key=lambda x: x['return_dd'], reverse=True)

    print("\n" + "="*100)
    print("FARTCOIN SHORT REVERSAL - TOP 5 BY R/DD RATIO")
    print("="*100)

    for i, r in enumerate(results[:5], 1):
        print(f"\n#{i} RSI>{r['rsi']} | {r['offset']:.1f}x ATR | {r['tp']}% TP")
        print(f"    R/DD: {r['return_dd']:.2f}x | Return: {r['return']:+.2f}% | Max DD: {r['max_dd']:.2f}% | Trades: {r['trades']} | Win%: {r['win_rate']:.1f}% | {r['profitable_months']}/7 mo")

    w = results[0]
    print("\n" + "="*100)
    print("BEST CONFIG FULL DETAILS")
    print("="*100)
    print(f"\nParameters:")
    print(f"  RSI Trigger: > {w['rsi']}")
    print(f"  Limit Offset: {w['offset']:.1f}x ATR")
    print(f"  Take Profit: {w['tp']}%")

    print(f"\nPerformance:")
    print(f"  Return/DD Ratio: {w['return_dd']:.2f}x")
    print(f"  Total Return: {w['return']:+.2f}%")
    print(f"  Max Drawdown: {w['max_dd']:.2f}%")
    print(f"  Total Trades: {w['trades']}")
    print(f"  Win Rate: {w['win_rate']:.1f}%")
    print(f"  Profitable Months: {w['profitable_months']}/7")

    print(f"\nMonthly Breakdown:")
    for m in sorted(w['monthly'].keys()):
        p = w['monthly'][m]
        indicator = "✓" if p > 0 else "✗" if p < 0 else "="
        print(f"  {indicator} {m}: ${p:+.2f}")
else:
    print("No valid results found")
