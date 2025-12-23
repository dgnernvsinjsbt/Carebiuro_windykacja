#!/usr/bin/env python3
"""
Monthly breakdown of dump catcher strategy
Find which months it works and what makes them different
"""
import pandas as pd
import numpy as np

# Load data
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

df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['is_red'] = df['close'] < df['open']
df['month'] = df['timestamp'].dt.to_period('M')

print("="*120)
print("MONTHLY BREAKDOWN: BIG RED 1.5% BODY + 3% TP STRATEGY")
print("="*120)
print()

# Strategy: 1.5% body, 3% TP, 3% max SL
body_min = 1.5
tp_pct = 3.0
max_sl_pct = 3.0
risk_pct = 5.0

# Track by month
monthly_results = {}

for month in df['month'].unique():
    df_month = df[df['month'] == month].copy().reset_index(drop=True)

    if len(df_month) < 50:
        continue

    equity = 100.0
    trades = []

    for i in range(20, len(df_month)):
        row = df_month.iloc[i]

        if pd.isna(row['atr']):
            continue

        # ENTRY
        is_red = row['close'] < row['open']
        body_pct = abs(row['close'] - row['open']) / row['open'] * 100

        if not is_red or body_pct < body_min:
            continue

        entry_price = row['close']
        sl_price = row['high'] * (1 + row['atr_pct'] / 100)
        sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

        if sl_dist_pct <= 0 or sl_dist_pct > max_sl_pct:
            continue

        tp_price = entry_price * (1 - tp_pct / 100)
        position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)

        # Find exit
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

        if hit_sl:
            pnl_pct = -sl_dist_pct
        else:
            pnl_pct = tp_pct

        pnl_dollar = position_size * (pnl_pct / 100)
        equity += pnl_dollar

        trades.append({
            'pnl_pct': pnl_pct,
            'pnl_dollar': pnl_dollar,
            'hit_tp': hit_tp
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

        winners = trades_df[trades_df['pnl_dollar'] > 0]
        win_rate = (len(winners) / len(trades_df)) * 100

        # Market characteristics
        month_start_price = df_month.iloc[0]['close']
        month_end_price = df_month.iloc[-1]['close']
        month_return = ((month_end_price - month_start_price) / month_start_price) * 100
        avg_atr = df_month['atr_pct'].mean()

        monthly_results[str(month)] = {
            'return': total_return,
            'max_dd': max_dd,
            'trades': len(trades_df),
            'win_rate': win_rate,
            'month_return': month_return,
            'avg_atr': avg_atr
        }

# Display
print(f"{'Month':<10} | {'Strategy %':>11} | {'Trades':>7} | {'Win %':>6} | {'Market %':>9} | {'Avg ATR':>8}")
print("-"*120)

for month, data in sorted(monthly_results.items()):
    marker = "✅" if data['return'] > 0 else "❌"
    print(f"{month:<10} | {marker} {data['return']:>8.1f}% | {data['trades']:>7} | {data['win_rate']:>5.1f}% | {data['month_return']:>8.1f}% | {data['avg_atr']:>7.2f}%")

print()
print("="*120)
print("PATTERN ANALYSIS")
print("="*120)
print()

# Find winning vs losing months
winning_months = {k: v for k, v in monthly_results.items() if v['return'] > 0}
losing_months = {k: v for k, v in monthly_results.items() if v['return'] <= 0}

if len(winning_months) > 0:
    print(f"✅ WINNING MONTHS ({len(winning_months)}):")
    avg_win_market = sum([v['month_return'] for v in winning_months.values()]) / len(winning_months)
    avg_win_atr = sum([v['avg_atr'] for v in winning_months.values()]) / len(winning_months)
    avg_win_return = sum([v['return'] for v in winning_months.values()]) / len(winning_months)
    print(f"   Avg strategy return: {avg_win_return:.1f}%")
    print(f"   Avg market return: {avg_win_market:.1f}%")
    print(f"   Avg ATR: {avg_win_atr:.2f}%")
    print()

if len(losing_months) > 0:
    print(f"❌ LOSING MONTHS ({len(losing_months)}):")
    avg_loss_market = sum([v['month_return'] for v in losing_months.values()]) / len(losing_months)
    avg_loss_atr = sum([v['avg_atr'] for v in losing_months.values()]) / len(losing_months)
    avg_loss_return = sum([v['return'] for v in losing_months.values()]) / len(losing_months)
    print(f"   Avg strategy return: {avg_loss_return:.1f}%")
    print(f"   Avg market return: {avg_loss_market:.1f}%")
    print(f"   Avg ATR: {avg_loss_atr:.2f}%")
    print()

print("💡 INSIGHT:")
if len(winning_months) > 0 and len(losing_months) > 0:
    if avg_win_market < 0 and avg_loss_market > 0:
        print("   Strategy works in DOWN/CHOPPY months, fails in UP months!")
        print(f"   Filter: Only trade when monthly return < 0%")
    elif avg_win_atr > avg_loss_atr:
        print("   Strategy works in HIGH volatility months!")
        print(f"   Filter: Only trade when ATR > {(avg_win_atr + avg_loss_atr)/2:.2f}%")
    else:
        print("   No clear pattern found between winning/losing months")

print("="*120)
