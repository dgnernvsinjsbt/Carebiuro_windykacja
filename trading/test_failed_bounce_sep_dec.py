#!/usr/bin/env python3
"""
Failed Bounce Strategy - Sep-Dec 2025
"""
import pandas as pd

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

df['month'] = df['timestamp'].dt.to_period('M')

print("="*120)
print("FAILED BOUNCE STRATEGY - SEP-DEC 2025")
print("="*120)
print()

lookback = 5
rejection_distance = 0.5  # Max % distance from swing high
tp_pct = 5.0
max_sl_pct = 5.0

test_months = ['2025-09', '2025-10', '2025-11', '2025-12']
results = []

for month_str in test_months:
    df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

    equity = 100.0
    trades = []
    in_position = False

    i = lookback
    while i < len(df_month):
        row = df_month.iloc[i]

        if pd.isna(row['atr']):
            i += 1
            continue

        if in_position:
            i += 1
            continue

        # Find recent swing high
        recent_high = df_month.iloc[max(0, i-lookback):i]['high'].max()

        # Check for bounce attempt (green candle near swing high)
        if row['close'] > row['open']:
            distance_to_high = ((recent_high - row['high']) / recent_high) * 100

            if 0 < distance_to_high <= rejection_distance:
                if i + 1 < len(df_month):
                    next_candle = df_month.iloc[i + 1]

                    # REJECTION confirmed
                    if next_candle['close'] < next_candle['open'] and next_candle['close'] < row['low']:
                        entry_price = next_candle['close']
                        sl_price = recent_high
                        tp_price = entry_price * (1 - tp_pct / 100)

                        sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                        if sl_dist_pct > 0 and sl_dist_pct <= max_sl_pct:
                            position_size = (equity * 5.0) / sl_dist_pct
                            in_position = True

                            # Find exit
                            hit_sl = False
                            hit_tp = False

                            for k in range(i + 2, min(i + 100, len(df_month))):
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

                                trades.append({
                                    'result': 'TP' if hit_tp else 'SL',
                                    'pnl': pnl_dollar
                                })

                                # Jump to exit
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

        results.append({
            'month': month_str,
            'return': total_return,
            'win_rate': win_rate,
            'trades': len(trades_df)
        })
    else:
        results.append({
            'month': month_str,
            'return': 0,
            'win_rate': 0,
            'trades': 0
        })

# Display
print(f"{'Month':<10} | {'Return':<10} | {'Win Rate':<9} | {'Trades':<7}")
print("-"*120)

for r in results:
    status = "✅" if r['return'] > 0 else "❌"
    print(f"{r['month']:<10} | {r['return']:>8.1f}% | {r['win_rate']:>7.1f}% | {r['trades']:<7} {status}")

wins = sum([1 for r in results if r['return'] > 0])
print()
print(f"Winning months: {wins}/4")
print("="*120)
