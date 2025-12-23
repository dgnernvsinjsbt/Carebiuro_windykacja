#!/usr/bin/env python3
"""
Momentum + MA Strategy with LIMIT OFFSETS
- Allow multiple pending orders simultaneously
- Each order expires after 4 hours (16 bars)
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

# Momentum
df['momentum_4h'] = ((df['close'] - df['close'].shift(16)) / df['close'].shift(16)) * 100

# MA
df['ma_20'] = df['close'].rolling(window=20).mean()
df['dist_from_ma'] = ((df['close'] - df['ma_20']) / df['ma_20']) * 100

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("MOMENTUM + MA STRATEGY WITH LIMIT OFFSETS")
print("="*140)
print()

# Use best params from previous optimization
mom_thresh = -2.5
ma_thresh = -1.0
tp_pct = 3.0
lookback = 8
max_wait_bars = 16  # 4 hours

# Test offset range
limit_offsets = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]

test_months = ['2025-09', '2025-10', '2025-11', '2025-12']

print(f"Testing {len(limit_offsets)} offset levels...")
print()

all_results = []

for offset_pct in limit_offsets:
    monthly_stats = {}

    for month_str in test_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        equity = 100.0
        peak_equity = 100.0
        max_dd = 0.0
        trades = []

        # Track multiple pending orders
        pending_orders = []  # List of dicts: {signal_bar, limit_price, sl_price, tp_price}
        active_positions = []  # List of dicts: {entry_bar, entry_price, sl_price, tp_price, position_size}

        i = max(20, lookback)
        while i < len(df_month):
            row = df_month.iloc[i]

            if pd.isna(row['momentum_4h']) or pd.isna(row['dist_from_ma']) or pd.isna(row['atr']):
                i += 1
                continue

            # Check active positions for exits
            positions_to_remove = []
            for pos_idx, pos in enumerate(active_positions):
                if row['high'] >= pos['sl_price']:
                    # Hit SL
                    sl_dist_pct = ((pos['sl_price'] - pos['entry_price']) / pos['entry_price']) * 100
                    pnl_pct = -sl_dist_pct
                    pnl_dollar = pos['position_size'] * (pnl_pct / 100)
                    equity += pnl_dollar

                    # Track DD
                    if equity > peak_equity:
                        peak_equity = equity
                    dd = ((peak_equity - equity) / peak_equity) * 100
                    if dd > max_dd:
                        max_dd = dd

                    trades.append({'result': 'SL', 'pnl': pnl_dollar})
                    positions_to_remove.append(pos_idx)

                elif row['low'] <= pos['tp_price']:
                    # Hit TP
                    tp_dist_pct = ((pos['entry_price'] - pos['tp_price']) / pos['entry_price']) * 100
                    pnl_pct = tp_dist_pct
                    pnl_dollar = pos['position_size'] * (pnl_pct / 100)
                    equity += pnl_dollar

                    # Track DD
                    if equity > peak_equity:
                        peak_equity = equity
                    dd = ((peak_equity - equity) / peak_equity) * 100
                    if dd > max_dd:
                        max_dd = dd

                    trades.append({'result': 'TP', 'pnl': pnl_dollar})
                    positions_to_remove.append(pos_idx)

            # Remove closed positions
            for idx in sorted(positions_to_remove, reverse=True):
                active_positions.pop(idx)

            # Check pending orders for fills/timeouts
            orders_to_remove = []
            for order_idx, order in enumerate(pending_orders):
                bars_waiting = i - order['signal_bar']

                # Check if filled (price bounced UP to reach limit)
                if row['high'] >= order['limit_price']:
                    entry_price = order['limit_price']
                    sl_dist_pct = ((order['sl_price'] - entry_price) / entry_price) * 100

                    if sl_dist_pct > 0 and sl_dist_pct <= 10.0:
                        position_size = (equity * 5.0) / sl_dist_pct

                        # Add to active positions
                        active_positions.append({
                            'entry_bar': i,
                            'entry_price': entry_price,
                            'sl_price': order['sl_price'],
                            'tp_price': order['tp_price'],
                            'position_size': position_size
                        })

                    orders_to_remove.append(order_idx)

                # Check if invalidated (SL hit before fill)
                elif row['high'] >= order['sl_price']:
                    orders_to_remove.append(order_idx)

                # Check if timed out
                elif bars_waiting >= max_wait_bars:
                    orders_to_remove.append(order_idx)

            # Remove filled/timed out orders
            for idx in sorted(orders_to_remove, reverse=True):
                pending_orders.pop(idx)

            # Check for NEW signal
            if row['momentum_4h'] < mom_thresh and row['dist_from_ma'] < ma_thresh:
                swing_high = df_month.iloc[max(0, i-lookback):i]['high'].max()

                signal_price = row['close']
                sl_price = swing_high
                tp_price = signal_price * (1 - tp_pct / 100)
                limit_price = signal_price * (1 + offset_pct / 100)

                if limit_price < sl_price:
                    # Add new pending order
                    pending_orders.append({
                        'signal_bar': i,
                        'limit_price': limit_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price
                    })

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

    # Calculate compounded return and overall max DD
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
        'offset': offset_pct,
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

# Display results
results_df = pd.DataFrame(all_results)
results_df = results_df.sort_values('return_dd', ascending=False)

print("="*140)
print("LIMIT OFFSET OPTIMIZATION RESULTS (Sorted by Return/DD)")
print("="*140)
print(f"{'Offset':<8} | {'Total Ret':<10} | {'Max DD':<8} | {'R/DD':<7} | {'Trades/Mo':<10} | {'Wins':<6} | {'Sep':<8} | {'Oct':<8} | {'Nov':<8} | {'Dec':<8}")
print("-"*140)

for idx, row in results_df.iterrows():
    status = "✅" if row['winning_months'] >= 3 else "⚠️ "
    print(f"{row['offset']:>6.1f}% | {row['total_return']:>8.1f}% | {row['max_dd']:>6.1f}% | {row['return_dd']:>5.2f}x | {row['avg_trades']:>8.1f} | {row['winning_months']}/4 {status} | {row['sep_ret']:>6.1f}% | {row['oct_ret']:>6.1f}% | {row['nov_ret']:>6.1f}% | {row['dec_ret']:>6.1f}%")

print()
print("="*140)
print()

# Best overall
best = results_df.iloc[0]
print("🏆 BEST OFFSET:")
print(f"   Offset: {best['offset']:.1f}%")
print(f"   Total Return: {best['total_return']:.1f}%")
print(f"   Max Drawdown: {best['max_dd']:.1f}%")
print(f"   Return/DD: {best['return_dd']:.2f}x")
print(f"   Avg Trades/Month: {best['avg_trades']:.1f}")
print(f"   Total Trades (4 months): {best['total_trades']:.0f}")
print(f"   Winning Months: {best['winning_months']}/4")
print()
print("   Monthly Performance:")
print(f"     Sep: {best['sep_ret']:+.1f}%")
print(f"     Oct: {best['oct_ret']:+.1f}%")
print(f"     Nov: {best['nov_ret']:+.1f}%")
print(f"     Dec: {best['dec_ret']:+.1f}%")
print()
print("="*140)
