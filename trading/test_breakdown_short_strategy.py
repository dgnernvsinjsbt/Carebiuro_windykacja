#!/usr/bin/env python3
"""
PENGU SHORT STRATEGY: Breakdown + Big Red Candle
Entry: Red candle >1% body breaking 20-bar low
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

# Rolling lows (support levels)
df['low_20'] = df['low'].rolling(window=20).min()
df['low_40'] = df['low'].rolling(window=40).min()

# Candle body
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['is_red'] = df['close'] < df['open']

# Momentum
df['ret_1h'] = ((df['close'] - df['close'].shift(4)) / df['close'].shift(4)) * 100
df['ret_2h'] = ((df['close'] - df['close'].shift(8)) / df['close'].shift(8)) * 100

print("="*120)
print("PENGU BREAKDOWN SHORT STRATEGY")
print("="*120)
print()

# Test on October first
df_test = df[(df['timestamp'] >= '2025-10-01') & (df['timestamp'] < '2025-11-01')].copy()

print(f"Testing period: {df_test['timestamp'].min()} to {df_test['timestamp'].max()}")
print(f"Candles: {len(df_test)}")
print()

# Strategy parameters to test
configs = [
    # (body_min, lookback, tp_pct, max_sl_pct, risk_pct, desc)
    (1.0, 20, 5.0, 5.0, 5.0, "Baseline: 1% body, 20-bar, 5% TP"),
    (0.8, 20, 5.0, 5.0, 5.0, "Lower body: 0.8%"),
    (1.2, 20, 5.0, 5.0, 5.0, "Higher body: 1.2%"),
    (1.0, 30, 5.0, 5.0, 5.0, "Longer lookback: 30"),
    (1.0, 20, 7.0, 5.0, 5.0, "Bigger TP: 7%"),
    (1.0, 20, 3.0, 5.0, 5.0, "Smaller TP: 3%"),
    (1.0, 20, 5.0, 3.0, 5.0, "Tighter SL: 3%"),
]

results = []

for body_min, lookback, tp_pct, max_sl_pct, risk_pct, desc in configs:
    equity = 100.0
    trades = []

    for i in range(lookback, len(df_test)):
        row = df_test.iloc[i]

        if pd.isna(row['atr']):
            continue

        # ENTRY CONDITIONS
        is_red = row['close'] < row['open']
        body_pct = abs(row['close'] - row['open']) / row['open'] * 100

        if not is_red or body_pct < body_min:
            continue

        # Check if breaking low
        lookback_start = max(0, i - lookback)
        prev_low = df_test.iloc[lookback_start:i]['low'].min()

        if row['low'] > prev_low:  # Not breaking low
            continue

        # ENTRY!
        entry_price = row['close']

        # SL = recent high
        sl_price = df_test.iloc[lookback_start:i+1]['high'].max()
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

        for j in range(i + 1, min(i + 200, len(df_test))):
            future_row = df_test.iloc[j]

            if future_row['high'] >= sl_price:
                hit_sl = True
                exit_idx = j
                break
            elif future_row['low'] <= tp_price:
                hit_tp = True
                exit_idx = j
                break

        if hit_sl:
            pnl_pct = -sl_dist_pct
            exit_reason = 'SL'
        elif hit_tp:
            pnl_pct = tp_pct
            exit_reason = 'TP'
        else:
            continue

        pnl_dollar = position_size * (pnl_pct / 100)
        equity += pnl_dollar

        trades.append({
            'entry_time': row['timestamp'],
            'entry_price': entry_price,
            'sl_dist_pct': sl_dist_pct,
            'pnl_pct': pnl_pct,
            'pnl_dollar': pnl_dollar,
            'exit_reason': exit_reason,
            'body_pct': body_pct
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

        results.append({
            'desc': desc,
            'total_return': total_return,
            'max_dd': max_dd,
            'return_dd': return_dd,
            'trades': len(trades_df),
            'win_rate': win_rate,
            'final_equity': equity
        })
    else:
        results.append({
            'desc': desc,
            'total_return': 0,
            'max_dd': 0,
            'return_dd': 0,
            'trades': 0,
            'win_rate': 0,
            'final_equity': 100
        })

# Display results
print("="*120)
print("CONFIGURATION TEST RESULTS")
print("="*120)
print()
print(f"{'Config':<40} | {'Return':>8} | {'Max DD':>8} | {'R/DD':>7} | {'Trades':>7} | {'Win%':>6}")
print("-"*120)

for r in results:
    print(f"{r['desc']:<40} | {r['total_return']:>7.1f}% | {r['max_dd']:>7.2f}% | {r['return_dd']:>6.2f}x | {r['trades']:>7} | {r['win_rate']:>5.1f}%")

print()

# Find best
if results:
    best = max(results, key=lambda x: x['return_dd'] if x['return_dd'] > 0 else -999)
    if best['return_dd'] > 0:
        print(f"🏆 Best Config: {best['desc']}")
        print(f"   Return/DD: {best['return_dd']:.2f}x")
        print(f"   Return: {best['total_return']:.1f}%")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Trades: {best['trades']}")
    else:
        print("❌ No profitable configs found")

print("="*120)
