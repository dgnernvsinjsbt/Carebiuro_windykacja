#!/usr/bin/env python3
"""
Find parameters that work across ALL downtrends (Aug, Oct, Nov)
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100

df['month'] = df['timestamp'].dt.to_period('M')

print("="*120)
print("OPTIMIZING PARAMS FOR ALL DOWNTRENDS")
print("="*120)
print()

# Test different combinations
configs = [
    # (breakdown_pct, tp_pct, max_sl_pct, desc)
    (-2.5, 5.0, 3.0, "Baseline: 2.5% breakdown, 5% TP"),
    (-3.0, 5.0, 3.0, "Stricter: 3.0% breakdown, 5% TP"),
    (-3.5, 5.0, 3.0, "Strictest: 3.5% breakdown, 5% TP"),
    (-2.5, 3.0, 3.0, "Tighter TP: 2.5% breakdown, 3% TP"),
    (-3.0, 3.0, 3.0, "Both: 3.0% breakdown, 3% TP"),
    (-2.5, 4.0, 3.0, "Middle: 2.5% breakdown, 4% TP"),
    (-3.0, 4.0, 3.0, "Balanced: 3.0% breakdown, 4% TP"),
]

downtrend_months = ['2025-08', '2025-10', '2025-11']

print(f"{'Config':<40} | {'Aug Return':<12} | {'Aug WR':<8} | {'Oct Return':<12} | {'Oct WR':<8} | {'Nov Return':<12} | {'Nov WR':<8} | {'Score'}")
print("-"*150)

for threshold, tp_pct, max_sl_pct, desc in configs:
    lookback_bars = 32
    risk_pct = 5.0

    monthly_returns = {}

    for month_str in downtrend_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        if len(df_month) == 0:
            monthly_returns[month_str] = 0
            continue

        equity = 100.0
        trades = []

        for i in range(lookback_bars, len(df_month)):
            row = df_month.iloc[i]

            if pd.isna(row['atr']):
                continue

            high_8h = df_month.iloc[max(0, i-lookback_bars):i]['high'].max()
            dist_pct = ((row['close'] - high_8h) / high_8h) * 100

            if dist_pct > threshold:
                continue

            entry_price = row['close']
            sl_price = high_8h
            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

            if sl_dist_pct <= 0 or sl_dist_pct > max_sl_pct:
                continue

            tp_price = entry_price * (1 - tp_pct / 100)
            position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)

            hit_sl = False
            hit_tp = False

            for j in range(i + 1, min(i + 100, len(df_month))):
                future_row = df_month.iloc[j]

                if future_row['high'] >= sl_price:
                    hit_sl = True
                    break
                elif future_row['low'] <= tp_price:
                    hit_tp = True
                    break

            if not (hit_sl or hit_tp):
                continue

            pnl_pct = tp_pct if hit_tp else -sl_dist_pct
            pnl_dollar = position_size * (pnl_pct / 100)
            equity += pnl_dollar

            trades.append({'pnl_dollar': pnl_dollar})

        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            total_return = ((equity - 100) / 100) * 100
            winners = trades_df[trades_df['pnl_dollar'] > 0]
            win_rate = (len(winners) / len(trades_df)) * 100
            monthly_returns[month_str] = {
                'return': total_return,
                'win_rate': win_rate,
                'trades': len(trades_df)
            }
        else:
            monthly_returns[month_str] = {
                'return': 0,
                'win_rate': 0,
                'trades': 0
            }

    # Calculate score: All months must be positive, score = product of returns
    aug_ret = monthly_returns.get('2025-08', {}).get('return', 0)
    oct_ret = monthly_returns.get('2025-10', {}).get('return', 0)
    nov_ret = monthly_returns.get('2025-11', {}).get('return', 0)

    aug_wr = monthly_returns.get('2025-08', {}).get('win_rate', 0)
    oct_wr = monthly_returns.get('2025-10', {}).get('win_rate', 0)
    nov_wr = monthly_returns.get('2025-11', {}).get('win_rate', 0)

    aug_trades = monthly_returns.get('2025-08', {}).get('trades', 0)
    oct_trades = monthly_returns.get('2025-10', {}).get('trades', 0)
    nov_trades = monthly_returns.get('2025-11', {}).get('trades', 0)

    if aug_ret > 0 and oct_ret > 0 and nov_ret > 0:
        score = "✅ ALL WIN"
        wins = 3
    elif (aug_ret > 0 and oct_ret > 0) or (aug_ret > 0 and nov_ret > 0) or (oct_ret > 0 and nov_ret > 0):
        score = "⚠️ 2/3"
        wins = 2
    else:
        score = "❌"
        wins = 0 if aug_ret <= 0 and oct_ret <= 0 and nov_ret <= 0 else 1

    print(f"{desc:<40} | {aug_ret:>9.1f}% | {aug_wr:>6.1f}% | {oct_ret:>9.1f}% | {oct_wr:>6.1f}% | {nov_ret:>9.1f}% | {nov_wr:>6.1f}% | {score}")

print()
print("="*120)
print("Finding best config that wins in ALL 3 downtrends...")
print("="*120)
