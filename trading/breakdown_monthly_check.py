#!/usr/bin/env python3
"""
Check if breakdown strategy wins in ALL downtrends or just October
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
print("BREAKDOWN STRATEGY: MONTHLY PERFORMANCE")
print("="*120)
print()

# Strategy: 2.5% breakdown from 8h high, 5% TP
threshold = -2.5
lookback_bars = 32  # 8 hours
tp_pct = 5.0
max_sl_pct = 3.0
risk_pct = 5.0

monthly_results = []

for month in df['month'].unique():
    df_month = df[df['month'] == month].copy().reset_index(drop=True)

    if len(df_month) < 100:
        continue

    # Calculate market return for month
    month_start = df_month.iloc[0]['close']
    month_end = df_month.iloc[-1]['close']
    market_return = ((month_end - month_start) / month_start) * 100

    equity = 100.0
    trades = []

    for i in range(lookback_bars, len(df_month)):
        row = df_month.iloc[i]

        if pd.isna(row['atr']):
            continue

        # Distance from 8h high
        high_8h = df_month.iloc[max(0, i-lookback_bars):i]['high'].max()
        dist_pct = ((row['close'] - high_8h) / high_8h) * 100

        if dist_pct > threshold:
            continue

        # ENTRY
        entry_price = row['close']
        sl_price = high_8h
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

        pnl_pct = tp_pct if hit_tp else -sl_dist_pct
        pnl_dollar = position_size * (pnl_pct / 100)
        equity += pnl_dollar

        trades.append({'pnl_dollar': pnl_dollar})

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

        monthly_results.append({
            'month': str(month),
            'strategy_return': total_return,
            'market_return': market_return,
            'max_dd': max_dd,
            'trades': len(trades_df),
            'win_rate': win_rate
        })
    else:
        monthly_results.append({
            'month': str(month),
            'strategy_return': 0,
            'market_return': market_return,
            'max_dd': 0,
            'trades': 0,
            'win_rate': 0
        })

# Display results
print(f"{'Month':<10} | {'Strategy':<12} | {'Market':<10} | {'Trades':<7} | {'Win%':<6} | {'Status'}")
print("-"*120)

for r in monthly_results:
    market_trend = "DOWN ⬇️" if r['market_return'] < -5 else ("UP ⬆️" if r['market_return'] > 5 else "FLAT ➡️")
    strategy_status = "✅ WIN" if r['strategy_return'] > 10 else ("❌ LOSE" if r['strategy_return'] < -10 else "⚪ FLAT")

    print(f"{r['month']:<10} | {r['strategy_return']:>9.1f}% | {r['market_return']:>8.1f}% | {r['trades']:>7} | {r['win_rate']:>5.1f}% | {strategy_status:<10} (Market: {market_trend})")

print()
print("="*120)
print("ANALYSIS")
print("="*120)
print()

# Categorize by market
downtrends = [r for r in monthly_results if r['market_return'] < -5]
uptrends = [r for r in monthly_results if r['market_return'] > 5]
flat = [r for r in monthly_results if -5 <= r['market_return'] <= 5]

if downtrends:
    print(f"📉 DOWNTREND MONTHS ({len(downtrends)}):")
    for r in downtrends:
        status = "✅" if r['strategy_return'] > 0 else "❌"
        print(f"   {status} {r['month']}: Strategy {r['strategy_return']:+.1f}%, Market {r['market_return']:+.1f}%")

    winners = [r for r in downtrends if r['strategy_return'] > 0]
    print(f"   Win Rate: {len(winners)}/{len(downtrends)} months ({len(winners)/len(downtrends)*100:.0f}%)")
    print()

if uptrends:
    print(f"📈 UPTREND MONTHS ({len(uptrends)}):")
    for r in uptrends:
        status = "✅" if r['strategy_return'] > 0 else "❌"
        print(f"   {status} {r['month']}: Strategy {r['strategy_return']:+.1f}%, Market {r['market_return']:+.1f}%")

    winners = [r for r in uptrends if r['strategy_return'] > 0]
    print(f"   Win Rate: {len(winners)}/{len(uptrends)} months ({len(winners)/len(uptrends)*100:.0f}%)")
    print()

if flat:
    print(f"➡️ FLAT MONTHS ({len(flat)}):")
    for r in flat:
        status = "✅" if r['strategy_return'] > 0 else "❌"
        print(f"   {status} {r['month']}: Strategy {r['strategy_return']:+.1f}%, Market {r['market_return']:+.1f}%")
    print()

# Verdict
downtrend_wins = [r for r in downtrends if r['strategy_return'] > 0]
if len(downtrends) > 1 and len(downtrend_wins) <= 1:
    print("🗑️ VERDICT: TRASH - Only works in ONE downtrend, fails in others!")
elif len(downtrends) > 0 and len(downtrend_wins) == len(downtrends):
    print("✅ VERDICT: GOOD - Works in ALL downtrends!")
elif len(downtrends) > 0 and len(downtrend_wins) >= len(downtrends) * 0.75:
    print("⚠️ VERDICT: DECENT - Works in MOST downtrends")
else:
    print("❓ VERDICT: UNCLEAR - Mixed results")

print("="*120)
