#!/usr/bin/env python3
"""
Optymalizacja parametrów strategii zigzag:
- Różne % odbicia (40%, 50%, 60%, 70%)
- Różne TP (2%, 3%, 4%, 5%)
"""
import pandas as pd
import numpy as np
from itertools import product

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# MA
df['ma_50'] = df['close'].rolling(window=50).mean()

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("OPTYMALIZACJA PARAMETRÓW ZIGZAG")
print("="*140)
print()

# Parameter grid
retrace_targets = [30, 40, 50, 60, 70]  # % odbicia do wejścia
tp_levels = [2.0, 3.0, 4.0, 5.0]  # TP %

lookback = 5
max_sl_pct = 10.0
test_months = ['2025-09', '2025-10', '2025-11', '2025-12']

all_results = []

for retrace_pct, tp_pct in product(retrace_targets, tp_levels):
    monthly_stats = {}

    for month_str in test_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        equity = 100.0
        peak_equity = 100.0
        max_dd = 0.0
        trades = []

        # Wykryj swing points
        swing_points = []

        for i in range(lookback, len(df_month) - lookback):
            is_swing_high = True
            for j in range(1, lookback + 1):
                if df_month.iloc[i]['high'] <= df_month.iloc[i-j]['high'] or df_month.iloc[i]['high'] <= df_month.iloc[i+j]['high']:
                    is_swing_high = False
                    break

            if is_swing_high:
                swing_points.append({'bar': i, 'price': df_month.iloc[i]['high'], 'type': 'HIGH'})
                continue

            is_swing_low = True
            for j in range(1, lookback + 1):
                if df_month.iloc[i]['low'] >= df_month.iloc[i-j]['low'] or df_month.iloc[i]['low'] >= df_month.iloc[i+j]['low']:
                    is_swing_low = False
                    break

            if is_swing_low:
                swing_points.append({'bar': i, 'price': df_month.iloc[i]['low'], 'type': 'LOW'})

        # Strategia
        i = 0
        while i < len(swing_points) - 1:
            p_high = swing_points[i]

            if p_high['type'] != 'HIGH':
                i += 1
                continue

            j = i + 1
            while j < len(swing_points) and swing_points[j]['type'] != 'LOW':
                j += 1

            if j >= len(swing_points):
                break

            p_low = swing_points[j]

            bar_high = p_high['bar']
            if pd.isna(df_month.iloc[bar_high]['ma_50']) or df_month.iloc[bar_high]['close'] >= df_month.iloc[bar_high]['ma_50']:
                i = j
                continue

            drop_pct_val = ((p_high['price'] - p_low['price']) / p_high['price']) * 100

            if drop_pct_val < 1.0:
                i = j
                continue

            drop_size = p_high['price'] - p_low['price']
            target_retrace_price = p_low['price'] + (drop_size * retrace_pct / 100)

            bar_low = p_low['bar']

            for k in range(bar_low + 1, min(bar_low + 50, len(df_month))):
                row = df_month.iloc[k]

                if row['high'] >= target_retrace_price:
                    entry_price = min(target_retrace_price, row['close'])
                    sl_price = df_month.iloc[bar_low:k+1]['high'].max()
                    tp_price = entry_price * (1 - tp_pct / 100)

                    sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                    if sl_dist_pct > 0 and sl_dist_pct <= max_sl_pct:
                        position_size = (equity * 5.0) / sl_dist_pct

                        hit_sl = False
                        hit_tp = False

                        for m in range(k + 1, min(k + 100, len(df_month))):
                            exit_row = df_month.iloc[m]

                            if exit_row['high'] >= sl_price:
                                hit_sl = True
                                break
                            elif exit_row['low'] <= tp_price:
                                hit_tp = True
                                break

                        if hit_sl or hit_tp:
                            pnl_pct = -sl_dist_pct if hit_sl else ((entry_price - tp_price) / entry_price) * 100
                            pnl_dollar = position_size * (pnl_pct / 100)
                            equity += pnl_dollar

                            if equity > peak_equity:
                                peak_equity = equity
                            dd = ((peak_equity - equity) / peak_equity) * 100
                            if dd > max_dd:
                                max_dd = dd

                            trades.append({'result': 'TP' if hit_tp else 'SL', 'pnl': pnl_dollar})

                    break

            i = j

        # Stats
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            total_return = ((equity - 100) / 100) * 100
            winners = trades_df[trades_df['pnl'] > 0]
            win_rate = (len(winners) / len(trades_df)) * 100

            monthly_stats[month_str] = {'return': total_return, 'max_dd': max_dd, 'win_rate': win_rate, 'trades': len(trades_df)}
        else:
            monthly_stats[month_str] = {'return': 0, 'max_dd': 0, 'win_rate': 0, 'trades': 0}

    # Overall
    compounded = 100.0
    for m in test_months:
        compounded *= (1 + monthly_stats[m]['return'] / 100)

    total_return = ((compounded - 100) / 100) * 100
    overall_max_dd = max([monthly_stats[m]['max_dd'] for m in test_months])
    return_dd = total_return / overall_max_dd if overall_max_dd > 0 else 0
    wins = sum([1 for m in test_months if monthly_stats[m]['return'] > 0])
    total_trades = sum([monthly_stats[m]['trades'] for m in test_months])

    all_results.append({
        'retrace_pct': retrace_pct,
        'tp_pct': tp_pct,
        'total_return': total_return,
        'max_dd': overall_max_dd,
        'return_dd': return_dd,
        'wins': wins,
        'total_trades': total_trades
    })

# Sort by return/DD
results_df = pd.DataFrame(all_results)
results_df = results_df.sort_values('return_dd', ascending=False)

print("TOP 10 KONFIGURACJI (sortowane po Return/DD):")
print("-"*140)
print(f"{'Retrace%':<10} | {'TP%':<6} | {'Return':<10} | {'Max DD':<8} | {'R/DD':<7} | {'Wins':<6} | {'Trades':<7}")
print("-"*140)

for idx, row in results_df.head(10).iterrows():
    status = "✅" if row['wins'] >= 3 else "⚠️ "
    print(f"{row['retrace_pct']:>8}% | {row['tp_pct']:>4.1f}% | {row['total_return']:>8.1f}% | {row['max_dd']:>6.1f}% | {row['return_dd']:>5.2f}x | {row['wins']}/4 {status} | {row['total_trades']:<7}")

print()
print("="*140)
