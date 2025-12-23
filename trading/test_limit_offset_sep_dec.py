#!/usr/bin/env python3
"""
Test CORRECTED limit offset on Sep-Dec 2025
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
print("CORRECTED LIMIT OFFSET - SEP-DEC 2025")
print("="*120)
print()

offset_pcts = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
test_months = ['2025-09', '2025-10', '2025-11', '2025-12']

results = []

for offset_pct in offset_pcts:
    monthly_stats = {}

    for month_str in test_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        equity = 100.0
        trades = []

        # STATE: Only one thing at a time
        is_busy = False
        pending_limit_price = None
        pending_signal_bar = None
        pending_sl_price = None
        pending_tp_price = None

        i = 32
        while i < len(df_month):
            row = df_month.iloc[i]

            if pd.isna(row['atr']):
                i += 1
                continue

            # If pending limit
            if is_busy and pending_limit_price is not None:
                bars_waiting = i - pending_signal_bar

                # CORRECT: Check HIGH for SHORT limit fills
                if row['high'] >= pending_limit_price:
                    entry_price = pending_limit_price
                    sl_dist_pct = ((pending_sl_price - entry_price) / entry_price) * 100

                    if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                        position_size = (equity * 5.0) / sl_dist_pct

                        # Find exit
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
                            if hit_sl:
                                pnl_pct = -sl_dist_pct
                            else:
                                tp_dist_pct = ((entry_price - pending_tp_price) / entry_price) * 100
                                pnl_pct = tp_dist_pct

                            pnl_dollar = position_size * (pnl_pct / 100)
                            equity += pnl_dollar

                            trades.append({
                                'pnl_dollar': pnl_dollar,
                                'result': 'TP' if hit_tp else 'SL'
                            })

                            # JUMP to exit bar
                            i = k

                    is_busy = False
                    pending_limit_price = None

                elif row['high'] >= pending_sl_price:
                    is_busy = False
                    pending_limit_price = None

                elif bars_waiting >= 16:
                    is_busy = False
                    pending_limit_price = None

                i += 1
                continue

            # Check for new signal (only if NOT busy)
            if not is_busy:
                high_8h = df_month.iloc[max(0, i-32):i]['high'].max()
                dist_pct = ((row['close'] - high_8h) / high_8h) * 100

                if dist_pct <= -2.5:
                    signal_price = row['close']
                    sl_price = high_8h
                    tp_price = signal_price * (1 - 0.05)
                    limit_price = signal_price * (1 + offset_pct / 100)

                    if limit_price < sl_price:
                        is_busy = True
                        pending_limit_price = limit_price
                        pending_signal_bar = i
                        pending_sl_price = sl_price
                        pending_tp_price = tp_price

            i += 1

        # Calculate stats
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            total_return = ((equity - 100) / 100) * 100
            winners = trades_df[trades_df['pnl_dollar'] > 0]
            win_rate = (len(winners) / len(trades_df)) * 100

            monthly_stats[month_str] = {
                'return': total_return,
                'win_rate': win_rate,
                'trades': len(trades_df)
            }
        else:
            monthly_stats[month_str] = {'return': 0, 'win_rate': 0, 'trades': 0}

    results.append({
        'offset': offset_pct,
        'sep': monthly_stats.get('2025-09', {}),
        'oct': monthly_stats.get('2025-10', {}),
        'nov': monthly_stats.get('2025-11', {}),
        'dec': monthly_stats.get('2025-12', {})
    })

# Display
print(f"{'Offset':<8} | {'Sep Ret':<10} | {'Sep T':<6} | {'Oct Ret':<10} | {'Oct T':<6} | {'Nov Ret':<10} | {'Nov T':<6} | {'Dec Ret':<10} | {'Dec T':<6}")
print("-"*120)

for r in results:
    sep_ret = r['sep'].get('return', 0)
    oct_ret = r['oct'].get('return', 0)
    nov_ret = r['nov'].get('return', 0)
    dec_ret = r['dec'].get('return', 0)

    sep_t = r['sep'].get('trades', 0)
    oct_t = r['oct'].get('trades', 0)
    nov_t = r['nov'].get('trades', 0)
    dec_t = r['dec'].get('trades', 0)

    print(f"{r['offset']:>6.1f}% | {sep_ret:>8.1f}% | {sep_t:>6} | {oct_ret:>8.1f}% | {oct_t:>6} | {nov_ret:>8.1f}% | {nov_t:>6} | {dec_ret:>8.1f}% | {dec_t:>6}")

print("="*120)
