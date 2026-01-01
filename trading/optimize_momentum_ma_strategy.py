#!/usr/bin/env python3
"""
MOMENTUM + MA Strategy Optimization
Goal: 20+ trades/month, maximize Return/DD ratio
"""
import pandas as pd
import numpy as np
from itertools import product

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

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("MOMENTUM + MA STRATEGY OPTIMIZATION")
print("="*140)
print()

# Parameter grid
momentum_thresholds = [-1.0, -1.5, -2.0, -2.5, -3.0]
ma_thresholds = [-0.5, -1.0, -1.5, -2.0]
tp_levels = [3, 4, 5, 6]
swing_lookbacks = [5, 8, 10]

test_months = ['2025-09', '2025-10', '2025-11', '2025-12']

print(f"Testing {len(momentum_thresholds) * len(ma_thresholds) * len(tp_levels) * len(swing_lookbacks)} combinations...")
print()

all_results = []

for mom_thresh, ma_thresh, tp_pct, lookback in product(momentum_thresholds, ma_thresholds, tp_levels, swing_lookbacks):
    monthly_stats = {}

    for month_str in test_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        equity = 100.0
        peak_equity = 100.0
        max_dd = 0.0
        trades = []
        in_position = False

        i = max(20, lookback)
        while i < len(df_month):
            row = df_month.iloc[i]

            if pd.isna(row['momentum_4h']) or pd.isna(row['dist_from_ma']) or pd.isna(row['atr']):
                i += 1
                continue

            if in_position:
                i += 1
                continue

            # SIGNAL: Momentum + MA conditions
            if row['momentum_4h'] < mom_thresh and row['dist_from_ma'] < ma_thresh:
                # Find recent swing high for SL
                swing_high = df_month.iloc[max(0, i-lookback):i]['high'].max()

                entry_price = row['close']
                sl_price = swing_high
                tp_price = entry_price * (1 - tp_pct / 100)

                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct > 0 and sl_dist_pct <= 10.0:
                    position_size = (equity * 5.0) / sl_dist_pct
                    in_position = True

                    # Find exit
                    hit_sl = False
                    hit_tp = False

                    for k in range(i + 1, min(i + 100, len(df_month))):
                        exit_row = df_month.iloc[k]

                        if exit_row['high'] >= sl_price:
                            hit_sl = True
                            break
                        elif exit_row['low'] <= tp_price:
                            hit_tp = True
                            break

                    if hit_sl or hit_tp:
                        if hit_sl:
                            pnl_pct = -sl_dist_pct
                        else:
                            tp_dist_pct = ((entry_price - tp_price) / entry_price) * 100
                            pnl_pct = tp_dist_pct

                        pnl_dollar = position_size * (pnl_pct / 100)
                        equity += pnl_dollar

                        # Track drawdown
                        if equity > peak_equity:
                            peak_equity = equity
                        dd = ((peak_equity - equity) / peak_equity) * 100
                        if dd > max_dd:
                            max_dd = dd

                        trades.append({
                            'result': 'TP' if hit_tp else 'SL',
                            'pnl': pnl_dollar
                        })

                        i = k
                        in_position = False
                        continue

            i += 1

        # Stats
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            total_return = ((equity - 100) / 100) * 100
            winners = trades_df[trades_df['pnl'] > 0]
            win_rate = (len(winners) / len(trades_df)) * 100

            monthly_stats[month_str] = {
                'return': total_return,
                'max_dd': max_dd,
                'trades': len(trades_df),
                'win_rate': win_rate
            }
        else:
            monthly_stats[month_str] = {
                'return': 0,
                'max_dd': 0,
                'trades': 0,
                'win_rate': 0
            }

    # Calculate overall stats
    total_trades = sum([monthly_stats[m]['trades'] for m in test_months])
    avg_trades_per_month = total_trades / len(test_months)

    # Only consider if avg 20+ trades/month
    if avg_trades_per_month >= 20:
        # Compound returns
        compounded_equity = 100.0
        overall_max_dd = 0.0

        for m in test_months:
            compounded_equity = compounded_equity * (1 + monthly_stats[m]['return'] / 100)
            if monthly_stats[m]['max_dd'] > overall_max_dd:
                overall_max_dd = monthly_stats[m]['max_dd']

        total_return = ((compounded_equity - 100) / 100) * 100
        return_dd_ratio = total_return / overall_max_dd if overall_max_dd > 0 else 0

        winning_months = sum([1 for m in test_months if monthly_stats[m]['return'] > 0])

        all_results.append({
            'mom_thresh': mom_thresh,
            'ma_thresh': ma_thresh,
            'tp_pct': tp_pct,
            'lookback': lookback,
            'total_return': total_return,
            'max_dd': overall_max_dd,
            'return_dd': return_dd_ratio,
            'avg_trades': avg_trades_per_month,
            'total_trades': total_trades,
            'winning_months': winning_months,
            'sep_ret': monthly_stats['2025-09']['return'],
            'oct_ret': monthly_stats['2025-10']['return'],
            'nov_ret': monthly_stats['2025-11']['return'],
            'dec_ret': monthly_stats['2025-12']['return']
        })

# Sort by return/DD ratio
results_df = pd.DataFrame(all_results)
results_df = results_df.sort_values('return_dd', ascending=False)

print(f"Found {len(results_df)} combinations with 20+ trades/month")
print()

# Top 10 by return/DD
print("="*140)
print("TOP 10: Best Return/DD Ratio (20+ trades/month)")
print("="*140)
print(f"{'Mom':<6} | {'MA':<6} | {'TP%':<5} | {'Look':<5} | {'Total Ret':<10} | {'Max DD':<8} | {'R/DD':<7} | {'Trades':<7} | {'Wins':<6} | {'Sep':<8} | {'Oct':<8} | {'Nov':<8} | {'Dec':<8}")
print("-"*140)

for idx, row in results_df.head(10).iterrows():
    print(f"{row['mom_thresh']:>5.1f}% | {row['ma_thresh']:>5.1f}% | {row['tp_pct']:>3}% | {row['lookback']:>4} | {row['total_return']:>8.1f}% | {row['max_dd']:>6.1f}% | {row['return_dd']:>5.2f}x | {row['avg_trades']:>5.1f} | {row['winning_months']}/4   | {row['sep_ret']:>6.1f}% | {row['oct_ret']:>6.1f}% | {row['nov_ret']:>6.1f}% | {row['dec_ret']:>6.1f}%")

print()
print("="*140)
print()

# Best overall
best = results_df.iloc[0]
print("🏆 BEST CONFIGURATION:")
print(f"   Momentum threshold: <{best['mom_thresh']:.1f}% (4h)")
print(f"   MA distance: <{best['ma_thresh']:.1f}% (20 MA)")
print(f"   Take Profit: {best['tp_pct']:.0f}%")
print(f"   Swing Lookback: {best['lookback']:.0f} bars")
print()
print(f"   Total Return: {best['total_return']:.1f}%")
print(f"   Max Drawdown: {best['max_dd']:.1f}%")
print(f"   Return/DD: {best['return_dd']:.2f}x")
print(f"   Avg Trades/Month: {best['avg_trades']:.1f}")
print(f"   Winning Months: {best['winning_months']}/4")
print()
print("   Monthly breakdown:")
print(f"     Sep: {best['sep_ret']:+.1f}%")
print(f"     Oct: {best['oct_ret']:+.1f}%")
print(f"     Nov: {best['nov_ret']:+.1f}%")
print(f"     Dec: {best['dec_ret']:+.1f}%")
print()
print("="*140)
