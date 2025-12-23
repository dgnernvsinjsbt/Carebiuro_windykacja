#!/usr/bin/env python3
"""
PENGU SHORT: Momentum Dump Catcher
Enter SHORT when dump is clearly starting (big red momentum)
Ride it down with trailing stop or quick TP
"""
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

# Candle metrics
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['is_red'] = df['close'] < df['open']

# Momentum
df['ret_15m'] = ((df['close'] - df['close'].shift(1)) / df['close'].shift(1)) * 100
df['ret_30m'] = ((df['close'] - df['close'].shift(2)) / df['close'].shift(2)) * 100
df['ret_1h'] = ((df['close'] - df['close'].shift(4)) / df['close'].shift(4)) * 100

# Acceleration
df['accel'] = df['ret_15m'].diff()

print("="*120)
print("PENGU MOMENTUM DUMP CATCHER")
print("="*120)
print()

# Test on full 6 months
df_test = df.copy()

print(f"Testing period: {df_test['timestamp'].min()} to {df_test['timestamp'].max()}")
print(f"Candles: {len(df_test)}")
print()

# Strategy configs
configs = [
    # (body_min, momentum_trigger, tp_pct, max_sl_pct, desc)
    (1.5, None, 5.0, 3.0, "Big red: 1.5% body, 5% TP"),
    (2.0, None, 5.0, 3.0, "Bigger red: 2.0% body, 5% TP"),
    (1.5, None, 3.0, 3.0, "Big red: 1.5% body, 3% TP (quick exit)"),
    (1.0, -1.5, 5.0, 3.0, "Red 1% + 15m momentum <-1.5%"),
    (1.0, -2.0, 5.0, 3.0, "Red 1% + 15m momentum <-2.0%"),
    (1.5, None, 7.0, 3.0, "Big red: 1.5% body, 7% TP (swing)"),
]

results = []

for body_min, momentum_trigger, tp_pct, max_sl_pct, desc in configs:
    equity = 100.0
    trades = []
    risk_pct = 5.0

    for i in range(20, len(df_test)):
        row = df_test.iloc[i]

        if pd.isna(row['atr']):
            continue

        # ENTRY CONDITIONS
        is_red = row['close'] < row['open']
        body_pct = abs(row['close'] - row['open']) / row['open'] * 100

        if not is_red or body_pct < body_min:
            continue

        # Momentum filter if specified
        if momentum_trigger is not None:
            if row['ret_15m'] > momentum_trigger:
                continue

        # ENTRY!
        entry_price = row['close']

        # SL = high of signal candle + 1 ATR
        sl_price = row['high'] * (1 + row['atr_pct'] / 100)
        sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

        if sl_dist_pct <= 0 or sl_dist_pct > max_sl_pct:
            continue

        # TP
        tp_price = entry_price * (1 - tp_pct / 100)

        # Position sizing
        position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)

        # Find exit
        hit_sl = False
        hit_tp = False
        exit_idx = None

        for j in range(i + 1, min(i + 100, len(df_test))):
            future_row = df_test.iloc[j]

            if future_row['high'] >= sl_price:
                hit_sl = True
                exit_idx = j
                break
            elif future_row['low'] <= tp_price:
                hit_tp = True
                exit_idx = j
                break

        if not (hit_sl or hit_tp):
            continue

        if hit_sl:
            pnl_pct = -sl_dist_pct
            exit_reason = 'SL'
        else:
            pnl_pct = tp_pct
            exit_reason = 'TP'

        pnl_dollar = position_size * (pnl_pct / 100)
        equity += pnl_dollar

        trades.append({
            'entry_time': row['timestamp'],
            'pnl_pct': pnl_pct,
            'pnl_dollar': pnl_dollar,
            'exit_reason': exit_reason,
            'sl_dist_pct': sl_dist_pct
        })

    # Calculate metrics
    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        total_return = ((equity - 100) / 100) * 100

        # Max DD
        equity_curve = [100.0]
        for pnl in trades_df['pnl_dollar']:
            equity_curve.append(equity_curve[-1] + pnl)

        eq_series = pd.Series(equity_curve)
        running_max = eq_series.expanding().max()
        drawdown = (eq_series - running_max) / running_max * 100
        max_dd = drawdown.min()

        return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

        winners = trades_df[trades_df['pnl_dollar'] > 0]
        win_rate = (len(winners) / len(trades_df)) * 100

        tp_rate = (len(trades_df[trades_df['exit_reason'] == 'TP']) / len(trades_df)) * 100

        results.append({
            'desc': desc,
            'total_return': total_return,
            'max_dd': max_dd,
            'return_dd': return_dd,
            'trades': len(trades_df),
            'win_rate': win_rate,
            'tp_rate': tp_rate,
            'final_equity': equity,
            'avg_sl': trades_df['sl_dist_pct'].mean()
        })
    else:
        results.append({
            'desc': desc,
            'total_return': 0,
            'max_dd': 0,
            'return_dd': 0,
            'trades': 0,
            'win_rate': 0,
            'tp_rate': 0,
            'final_equity': 100,
            'avg_sl': 0
        })

# Display results
print("="*120)
print("STRATEGY TEST RESULTS")
print("="*120)
print()
print(f"{'Strategy':<45} | {'Return':>8} | {'DD':>8} | {'R/DD':>7} | {'Trades':>7} | {'Win%':>6} | {'TP%':>6} | {'Avg SL':>7}")
print("-"*120)

for r in results:
    print(f"{r['desc']:<45} | {r['total_return']:>7.1f}% | {r['max_dd']:>7.2f}% | {r['return_dd']:>6.2f}x | {r['trades']:>7} | {r['win_rate']:>5.1f}% | {r['tp_rate']:>5.1f}% | {r['avg_sl']:>6.2f}%")

print()

# Find best by R/DD
profitable = [r for r in results if r['return_dd'] > 0]
if profitable:
    best = max(profitable, key=lambda x: x['return_dd'])
    print(f"🏆 Best R/DD: {best['desc']}")
    print(f"   Return/DD: {best['return_dd']:.2f}x")
    print(f"   Return: {best['total_return']:.1f}%")
    print(f"   Max DD: {best['max_dd']:.2f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Trades: {best['trades']}")
    print()

# Find best by absolute return
best_return = max(results, key=lambda x: x['total_return'])
print(f"💰 Best Return: {best_return['desc']}")
print(f"   Return: {best_return['total_return']:.1f}%")
print(f"   Return/DD: {best_return['return_dd']:.2f}x")
print(f"   Win Rate: {best_return['win_rate']:.1f}%")
print(f"   Trades: {best_return['trades']}")

print("="*120)
