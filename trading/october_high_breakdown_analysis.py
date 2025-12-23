#!/usr/bin/env python3
"""
New approach: Catch dumps by detecting breakdown from recent highs
Enter when price drops X% from recent peak
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

# Rolling highs (different lookbacks)
df['high_4h'] = df['high'].rolling(window=16).max()
df['high_8h'] = df['high'].rolling(window=32).max()
df['high_12h'] = df['high'].rolling(window=48).max()

# Distance from highs
df['dist_4h'] = ((df['close'] - df['high_4h']) / df['high_4h']) * 100
df['dist_8h'] = ((df['close'] - df['high_8h']) / df['high_8h']) * 100
df['dist_12h'] = ((df['close'] - df['high_12h']) / df['high_12h']) * 100

# Future returns
df['fwd_2h'] = ((df['close'].shift(-8) - df['close']) / df['close']) * 100
df['fwd_4h'] = ((df['close'].shift(-16) - df['close']) / df['close']) * 100

print("="*120)
print("OCTOBER: HIGH BREAKDOWN ANALYSIS")
print("="*120)
print()

df_oct = df.copy()  # Test on full 6 months

print(f"Period: {df_oct['timestamp'].min()} to {df_oct['timestamp'].max()}")
print(f"Testing different breakdown thresholds...")
print()

# Test different breakdown levels
thresholds_4h = [-1.5, -2.0, -2.5, -3.0, -3.5, -4.0]
thresholds_8h = [-2.0, -3.0, -4.0, -5.0]

print("="*120)
print("4-HOUR HIGH BREAKDOWN")
print("="*120)
print()

for threshold in thresholds_4h:
    signals = df_oct[df_oct['dist_4h'] <= threshold].copy()

    if len(signals) == 0:
        continue

    # Check how many led to dumps
    dumps = signals[signals['fwd_4h'] < -3.0]
    avg_fwd = signals['fwd_4h'].mean()

    print(f"Breakdown {threshold:.1f}% from 4h high:")
    print(f"  Signals: {len(signals)}")
    print(f"  Led to >3% dump: {len(dumps)} ({len(dumps)/len(signals)*100:.1f}%)")
    print(f"  Avg fwd 4h return: {avg_fwd:.2f}%")
    print()

print("="*120)
print("8-HOUR HIGH BREAKDOWN")
print("="*120)
print()

for threshold in thresholds_8h:
    signals = df_oct[df_oct['dist_8h'] <= threshold].copy()

    if len(signals) == 0:
        continue

    dumps = signals[signals['fwd_4h'] < -3.0]
    avg_fwd = signals['fwd_4h'].mean()

    print(f"Breakdown {threshold:.1f}% from 8h high:")
    print(f"  Signals: {len(signals)}")
    print(f"  Led to >3% dump: {len(dumps)} ({len(dumps)/len(signals)*100:.1f}%)")
    print(f"  Avg fwd 4h return: {avg_fwd:.2f}%")
    print()

# Now backtest the best threshold
print("="*120)
print("BACKTESTING: 3% BREAKDOWN FROM 8H HIGH")
print("="*120)
print()

configs = [
    (-3.0, 8, 5.0, 3.0, "3% breakdown, 8h high, 5% TP"),
    (-3.0, 8, 3.0, 3.0, "3% breakdown, 8h high, 3% TP"),
    (-3.0, 8, 7.0, 3.0, "3% breakdown, 8h high, 7% TP"),
    (-4.0, 8, 5.0, 3.0, "4% breakdown, 8h high, 5% TP"),
    (-2.5, 8, 5.0, 3.0, "2.5% breakdown, 8h high, 5% TP"),
]

results = []

for threshold, lookback_hours, tp_pct, max_sl_pct, desc in configs:
    lookback_bars = lookback_hours * 4  # 4 bars per hour on 15m

    equity = 100.0
    trades = []
    risk_pct = 5.0

    for i in range(lookback_bars, len(df_oct)):
        row = df_oct.iloc[i]

        if pd.isna(row['atr']):
            continue

        # Calculate distance from high
        high_lookback = df_oct.iloc[max(0, i-lookback_bars):i]['high'].max()
        dist_pct = ((row['close'] - high_lookback) / high_lookback) * 100

        if dist_pct > threshold:  # Not broken down enough
            continue

        # ENTRY
        entry_price = row['close']

        # SL = recent high
        sl_price = high_lookback
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

        for j in range(i + 1, min(i + 100, len(df_oct))):
            future_row = df_oct.iloc[j]

            if future_row['high'] >= sl_price:
                hit_sl = True
                break
            elif future_row['low'] <= tp_price:
                hit_tp = True
                break

        if not (hit_sl or hit_tp):
            continue

        if hit_sl:
            pnl_pct = -sl_dist_pct
        else:
            pnl_pct = tp_pct

        pnl_dollar = position_size * (pnl_pct / 100)
        equity += pnl_dollar

        trades.append({
            'entry_time': row['timestamp'],
            'pnl_pct': pnl_pct,
            'pnl_dollar': pnl_dollar,
            'hit_tp': hit_tp,
            'sl_dist_pct': sl_dist_pct
        })

    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
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
        win_rate = (len(winners) / len(trades_df)) * 100

        results.append({
            'desc': desc,
            'return': total_return,
            'max_dd': max_dd,
            'return_dd': return_dd,
            'trades': len(trades_df),
            'win_rate': win_rate,
            'avg_sl': trades_df['sl_dist_pct'].mean()
        })

print(f"{'Strategy':<40} | {'Return':>8} | {'DD':>8} | {'R/DD':>7} | {'Trades':>7} | {'Win%':>6} | {'Avg SL':>7}")
print("-"*120)

for r in results:
    print(f"{r['desc']:<40} | {r['return']:>7.1f}% | {r['max_dd']:>7.2f}% | {r['return_dd']:>6.2f}x | {r['trades']:>7} | {r['win_rate']:>5.1f}% | {r['avg_sl']:>6.2f}%")

print()

if results:
    best = max(results, key=lambda x: x['return_dd'] if x['return_dd'] > 0 else -999)
    if best['return_dd'] > 0:
        print(f"🏆 Best: {best['desc']}")
        print(f"   Return: {best['return']:.1f}%")
        print(f"   Return/DD: {best['return_dd']:.2f}x")
        print(f"   Trades: {best['trades']}, Win Rate: {best['win_rate']:.1f}%")

print("="*120)
