#!/usr/bin/env python3
"""
Test limit order offsets for breakdown strategy
Signal at 100, SL at 110, but enter at 101-109 with TP staying at original level
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

print("="*140)
print("LIMIT OFFSET STRATEGY TEST")
print("="*140)
print()

# Strategy params
breakdown_threshold = -2.5
lookback_bars = 32
tp_pct_from_signal = 5.0  # TP is 5% below signal price
risk_pct = 5.0
max_wait_bars = 10  # Wait up to 10 bars (2.5 hours) for fill

# Test different limit offsets
offset_pcts = [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0]  # % above signal price

downtrend_months = ['2025-08', '2025-10', '2025-11']

results = []

for offset_pct in offset_pcts:
    monthly_stats = {}

    for month_str in downtrend_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        if len(df_month) == 0:
            continue

        equity = 100.0
        trades = []

        for i in range(lookback_bars, len(df_month)):
            row = df_month.iloc[i]

            if pd.isna(row['atr']):
                continue

            # Check for breakdown signal
            high_8h = df_month.iloc[max(0, i-lookback_bars):i]['high'].max()
            dist_pct = ((row['close'] - high_8h) / high_8h) * 100

            if dist_pct > breakdown_threshold:
                continue

            # SIGNAL TRIGGERED
            signal_price = row['close']
            sl_price = high_8h
            tp_price = signal_price * (1 - tp_pct_from_signal / 100)  # TP stays at this level

            # Calculate limit order price
            limit_price = signal_price * (1 + offset_pct / 100)

            # Check if limit would be above SL (invalid)
            if limit_price >= sl_price:
                continue

            # Wait for fill
            filled = False
            fill_idx = None

            for j in range(i + 1, min(i + 1 + max_wait_bars, len(df_month))):
                future_row = df_month.iloc[j]

                # Check if limit order would fill
                if future_row['low'] <= limit_price:
                    filled = True
                    fill_idx = j
                    break

                # Check if price went above SL before fill (signal invalidated)
                if future_row['high'] >= sl_price:
                    break

            if not filled:
                continue

            # FILLED - now track exit
            entry_price = limit_price
            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100
            tp_dist_pct = ((entry_price - tp_price) / entry_price) * 100

            # Skip if SL too wide
            if sl_dist_pct > 5.0 or sl_dist_pct <= 0:
                continue

            # Position sizing based on actual SL distance
            position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)

            # Find exit
            hit_sl = False
            hit_tp = False

            for k in range(fill_idx + 1, min(fill_idx + 100, len(df_month))):
                exit_row = df_month.iloc[k]

                if exit_row['high'] >= sl_price:
                    hit_sl = True
                    break
                elif exit_row['low'] <= tp_price:
                    hit_tp = True
                    break

            if not (hit_sl or hit_tp):
                continue

            if hit_sl:
                pnl_pct = -sl_dist_pct
            else:
                pnl_pct = tp_dist_pct

            pnl_dollar = position_size * (pnl_pct / 100)
            equity += pnl_dollar

            trades.append({
                'pnl_dollar': pnl_dollar,
                'hit_tp': hit_tp,
                'sl_dist_pct': sl_dist_pct,
                'tp_dist_pct': tp_dist_pct
            })

        # Calculate monthly stats
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            total_return = ((equity - 100) / 100) * 100
            winners = trades_df[trades_df['pnl_dollar'] > 0]
            win_rate = (len(winners) / len(trades_df)) * 100

            monthly_stats[month_str] = {
                'return': total_return,
                'win_rate': win_rate,
                'trades': len(trades_df),
                'avg_sl': trades_df['sl_dist_pct'].mean(),
                'avg_tp': trades_df['tp_dist_pct'].mean()
            }
        else:
            monthly_stats[month_str] = {
                'return': 0,
                'win_rate': 0,
                'trades': 0,
                'avg_sl': 0,
                'avg_tp': 0
            }

    results.append({
        'offset_pct': offset_pct,
        'aug': monthly_stats.get('2025-08', {}),
        'oct': monthly_stats.get('2025-10', {}),
        'nov': monthly_stats.get('2025-11', {})
    })

# Display results
print(f"{'Offset':<8} | {'Aug Ret':<10} | {'Aug WR':<8} | {'Aug Trades':<11} | {'Oct Ret':<10} | {'Oct WR':<8} | {'Oct Trades':<11} | {'Nov Ret':<10} | {'Nov WR':<8} | {'Score'}")
print("-"*140)

for r in results:
    offset = r['offset_pct']
    aug = r['aug']
    oct = r['oct']
    nov = r['nov']

    aug_ret = aug.get('return', 0)
    oct_ret = oct.get('return', 0)
    nov_ret = nov.get('return', 0)

    aug_wr = aug.get('win_rate', 0)
    oct_wr = oct.get('win_rate', 0)
    nov_wr = nov.get('win_rate', 0)

    aug_trades = aug.get('trades', 0)
    oct_trades = oct.get('trades', 0)
    nov_trades = nov.get('trades', 0)

    # Score
    wins = sum([aug_ret > 0, oct_ret > 0, nov_ret > 0])
    if wins == 3:
        score = "✅ 3/3"
    elif wins == 2:
        score = "⚠️ 2/3"
    else:
        score = "❌"

    print(f"{offset:>6.1f}% | {aug_ret:>8.1f}% | {aug_wr:>6.1f}% | {aug_trades:>11} | {oct_ret:>8.1f}% | {oct_wr:>6.1f}% | {oct_trades:>11} | {nov_ret:>8.1f}% | {nov_wr:>6.1f}% | {score}")

print()
print("="*140)
print("ANALYSIS")
print("="*140)
print()

# Find best config
best = None
best_score = -1

for r in results:
    aug_ret = r['aug'].get('return', 0)
    oct_ret = r['oct'].get('return', 0)
    nov_ret = r['nov'].get('return', 0)

    wins = sum([aug_ret > 0, oct_ret > 0, nov_ret > 0])

    if wins > best_score or (wins == best_score and best is not None and
                              aug_ret + oct_ret + nov_ret > best['aug'].get('return', 0) + best['oct'].get('return', 0) + best['nov'].get('return', 0)):
        best = r
        best_score = wins

if best and best_score == 3:
    print(f"🏆 WINNER: {best['offset_pct']:.1f}% offset - WINS ALL 3 MONTHS!")
    print(f"   Aug: +{best['aug']['return']:.1f}% ({best['aug']['trades']} trades, {best['aug']['win_rate']:.1f}% WR)")
    print(f"   Oct: +{best['oct']['return']:.1f}% ({best['oct']['trades']} trades, {best['oct']['win_rate']:.1f}% WR)")
    print(f"   Nov: +{best['nov']['return']:.1f}% ({best['nov']['trades']} trades, {best['nov']['win_rate']:.1f}% WR)")
elif best:
    print(f"⚠️ BEST: {best['offset_pct']:.1f}% offset - Wins {best_score}/3 months")
else:
    print("❌ No winning config found")

print("="*140)
