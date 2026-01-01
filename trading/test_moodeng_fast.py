#!/usr/bin/env python3
"""Test SHORT reversal strategy on MOODENG - FAST (50 configs)"""
import pandas as pd
import numpy as np

df = pd.read_csv('moodeng_6months_bingx_15m.csv')
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
        equity_curve.append(equity_curve[-1] + pnl)
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

print("MOODENG SHORT REVERSAL - FAST TEST (50 configs)")
print("=" * 80)
results = []
config_num = 0

# Test 50 most logical configs: 5 RSI × 2 offset × 5 TP
for rsi in [68, 70, 72, 74, 76]:
    for offset in [0.6, 0.8]:  # Skip 0.4 and 1.0
        for tp in [6, 7, 8, 9, 10]:  # Skip 5%
            config_num += 1
            if config_num % 10 == 0:
                print(f"  Tested {config_num}/50 configs...")
            r = test(rsi, offset, tp)
            if r:
                results.append(r)

print(f"\nVALID RESULTS: {len(results)}/50")

if results:
    results.sort(key=lambda x: x['return_dd'], reverse=True)
    print(f"\nTOP 5 BY R/DD:")
    print("-" * 80)
    for i, r in enumerate(results[:5], 1):
        print(f"#{i} RSI>{r['rsi']} {r['offset']:.1f}ATR TP{r['tp']}% | R/DD:{r['return_dd']:.2f}x Ret:{r['return']:+.1f}% {r['trades']}tr {r['win_rate']:.1f}%W {r['profitable_months']}/6mo")

    w = results[0]
    print(f"\nBEST: RSI>{w['rsi']} {w['offset']:.1f}ATR TP{w['tp']}% | {w['return_dd']:.2f}x {w['return']:+.1f}% {w['max_dd']:.2f}%DD {w['trades']}tr")
    print("\nMONTHLY:")
    for m, p in sorted(w['monthly'].items()):
        mark = "✓" if p > 0 else "✗"
        print(f"  {mark} {m}: ${p:+.2f}")
else:
    print("No valid results")
