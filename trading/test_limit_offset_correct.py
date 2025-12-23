#!/usr/bin/env python3
"""
CORRECT: Only ONE position at a time (pending OR active)
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
print("CORRECTED: ONLY ONE POSITION AT A TIME")
print("="*120)
print()

offset_pcts = [0.0, 0.2, 0.4, 0.6, 0.8]
downtrend_months = ['2025-08', '2025-10', '2025-11']

results = []

for offset_pct in offset_pcts:
    monthly_stats = {}

    for month_str in downtrend_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        equity = 100.0
        trades = []
        
        # STATE: Only one of these can be true at a time
        has_pending_limit = False
        in_active_position = False
        
        pending_limit_price = None
        pending_signal_bar = None
        pending_sl_price = None
        pending_tp_price = None
        
        active_entry_bar = None
        active_sl_price = None
        active_tp_price = None

        i = 32
        while i < len(df_month):
            row = df_month.iloc[i]

            if pd.isna(row['atr']):
                i += 1
                continue

            # If in active position, check for exit
            if in_active_position:
                if row['high'] >= active_sl_price:
                    # Hit SL
                    in_active_position = False
                elif row['low'] <= active_tp_price:
                    # Hit TP
                    in_active_position = False
                
                i += 1
                continue

            # If pending limit, check for fill/timeout/invalidation
            if has_pending_limit:
                bars_waiting = i - pending_signal_bar

                if row['low'] <= pending_limit_price:
                    # FILLED
                    entry_price = pending_limit_price
                    sl_dist_pct = ((pending_sl_price - entry_price) / entry_price) * 100

                    if sl_dist_pct > 0 and sl_dist_pct <= 5.0:
                        position_size = (equity * 5.0) / sl_dist_pct
                        
                        # Enter active position
                        in_active_position = True
                        active_entry_bar = i
                        active_sl_price = pending_sl_price
                        active_tp_price = pending_tp_price
                        
                        # Find exit
                        hit_sl = False
                        hit_tp = False

                        for k in range(i + 1, min(i + 100, len(df_month))):
                            exit_row = df_month.iloc[k]

                            if exit_row['high'] >= active_sl_price:
                                hit_sl = True
                                break
                            elif exit_row['low'] <= active_tp_price:
                                hit_tp = True
                                break

                        if hit_sl or hit_tp:
                            tp_dist_pct = ((entry_price - active_tp_price) / entry_price) * 100
                            pnl_pct = tp_dist_pct if hit_tp else -sl_dist_pct
                            pnl_dollar = position_size * (pnl_pct / 100)
                            equity += pnl_dollar

                            trades.append({'pnl_dollar': pnl_dollar})
                            
                        in_active_position = False

                    has_pending_limit = False

                elif row['high'] >= pending_sl_price:
                    has_pending_limit = False

                elif bars_waiting >= 16:
                    has_pending_limit = False

                i += 1
                continue

            # No pending, no position - check for new signal
            high_8h = df_month.iloc[max(0, i-32):i]['high'].max()
            dist_pct = ((row['close'] - high_8h) / high_8h) * 100

            if dist_pct <= -2.5:
                signal_price = row['close']
                sl_price = high_8h
                tp_price = signal_price * (1 - 0.05)
                limit_price = signal_price * (1 + offset_pct / 100)

                if limit_price < sl_price:
                    has_pending_limit = True
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
        'aug': monthly_stats.get('2025-08', {}),
        'oct': monthly_stats.get('2025-10', {}),
        'nov': monthly_stats.get('2025-11', {})
    })

# Display
print(f"{'Offset':<8} | {'Aug Ret':<10} | {'Aug T':<6} | {'Oct Ret':<10} | {'Oct T':<6} | {'Nov Ret':<10} | {'Nov T':<6} | {'Score'}")
print("-"*120)

for r in results:
    aug_ret = r['aug'].get('return', 0)
    oct_ret = r['oct'].get('return', 0)
    nov_ret = r['nov'].get('return', 0)
    
    aug_t = r['aug'].get('trades', 0)
    oct_t = r['oct'].get('trades', 0)
    nov_t = r['nov'].get('trades', 0)

    wins = sum([aug_ret > 0, oct_ret > 0, nov_ret > 0])
    score = "✅ 3/3" if wins == 3 else ("⚠️ 2/3" if wins == 2 else "❌")

    print(f"{r['offset']:>6.1f}% | {aug_ret:>8.1f}% | {aug_t:>6} | {oct_ret:>8.1f}% | {oct_t:>6} | {nov_ret:>8.1f}% | {nov_t:>6} | {score}")

print("="*120)
