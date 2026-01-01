#!/usr/bin/env python3
"""
FIXED: Limit offset strategy with proper pending order management
Only ONE pending limit at a time, no new signals while waiting
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
print("LIMIT OFFSET STRATEGY - FIXED (One pending order at a time)")
print("="*140)
print()

# Strategy params
breakdown_threshold = -2.5
lookback_bars = 32
tp_pct_from_signal = 5.0
risk_pct = 5.0
max_wait_bars = 16  # 4 hours = 16 bars on 15m

# Test different limit offsets
offset_pcts = [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0]

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
        
        # STATE TRACKING
        has_pending_limit = False
        pending_limit_price = None
        pending_signal_bar = None
        pending_sl_price = None
        pending_tp_price = None
        in_position = False

        i = lookback_bars
        while i < len(df_month):
            row = df_month.iloc[i]

            if pd.isna(row['atr']):
                i += 1
                continue

            # If we have a pending limit, check for fill or timeout
            if has_pending_limit:
                bars_waiting = i - pending_signal_bar

                # Check if filled
                if row['low'] <= pending_limit_price:
                    # FILLED!
                    entry_price = pending_limit_price
                    sl_dist_pct = ((pending_sl_price - entry_price) / entry_price) * 100
                    tp_dist_pct = ((entry_price - pending_tp_price) / entry_price) * 100

                    if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                        position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)
                        in_position = True
                        
                        # Track exit
                        hit_sl = False
                        hit_tp = False

                        for k in range(i + 1, min(i + 100, len(df_month))):
                            exit_row = df_month.iloc[k]

                            if exit_row['high'] >= pending_sl_price:
                                hit_sl = True
                                break
                            elif exit_row['low'] <= pending_tp_price:
                                hit_tp = True
                                break

                        if hit_sl or hit_tp:
                            pnl_pct = tp_dist_pct if hit_tp else -sl_dist_pct
                            pnl_dollar = position_size * (pnl_pct / 100)
                            equity += pnl_dollar

                            trades.append({
                                'pnl_dollar': pnl_dollar,
                                'hit_tp': hit_tp,
                                'sl_dist_pct': sl_dist_pct,
                                'tp_dist_pct': tp_dist_pct
                            })

                    # Clear pending limit
                    has_pending_limit = False
                    in_position = False

                # Check if invalidated (price went above SL)
                elif row['high'] >= pending_sl_price:
                    has_pending_limit = False

                # Check if timed out
                elif bars_waiting >= max_wait_bars:
                    has_pending_limit = False

                i += 1
                continue

            # No pending limit - check for new signal
            high_8h = df_month.iloc[max(0, i-lookback_bars):i]['high'].max()
            dist_pct = ((row['close'] - high_8h) / high_8h) * 100

            if dist_pct <= breakdown_threshold:
                # SIGNAL!
                signal_price = row['close']
                sl_price = high_8h
                tp_price = signal_price * (1 - tp_pct_from_signal / 100)

                limit_price = signal_price * (1 + offset_pct / 100)

                if limit_price < sl_price:
                    # Place pending limit
                    has_pending_limit = True
                    pending_limit_price = limit_price
                    pending_signal_bar = i
                    pending_sl_price = sl_price
                    pending_tp_price = tp_price

            i += 1

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
print(f"{'Offset':<8} | {'Aug Ret':<10} | {'Aug WR':<8} | {'Aug T':<6} | {'Oct Ret':<10} | {'Oct WR':<8} | {'Oct T':<6} | {'Nov Ret':<10} | {'Nov WR':<8} | {'Nov T':<6} | {'Score'}")
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

    aug_t = aug.get('trades', 0)
    oct_t = oct.get('trades', 0)
    nov_t = nov.get('trades', 0)

    wins = sum([aug_ret > 0, oct_ret > 0, nov_ret > 0])
    if wins == 3:
        score = "✅ 3/3"
    elif wins == 2:
        score = "⚠️ 2/3"
    else:
        score = "❌"

    print(f"{offset:>6.1f}% | {aug_ret:>8.1f}% | {aug_wr:>6.1f}% | {aug_t:>6} | {oct_ret:>8.1f}% | {oct_wr:>6.1f}% | {oct_t:>6} | {nov_ret:>8.1f}% | {nov_wr:>6.1f}% | {nov_t:>6} | {score}")

print()
print("="*140)
print("ANALYSIS")
print("="*140)
print()

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
