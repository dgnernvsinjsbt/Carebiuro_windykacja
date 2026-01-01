#!/usr/bin/env python3
"""
ZIGZAG + DOWNTREND FILTER:

Dodaj filtr: p3 (lower high) musi być co najmniej X% niższy od p1
Testuj różne thresholdy: 1%, 2%, 3%
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

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("ZIGZAG + DOWNTREND FILTER OPTIMIZATION")
print("="*140)
print()

def zigzag_indicator(df, min_pct=2.0):
    swings = []
    current_price = df.iloc[0]['close']
    current_type = None
    extreme_high = df.iloc[0]['high']
    extreme_high_bar = 0
    extreme_low = df.iloc[0]['low']
    extreme_low_bar = 0

    for i in range(1, len(df)):
        high = df.iloc[i]['high']
        low = df.iloc[i]['low']

        if high > extreme_high:
            extreme_high = high
            extreme_high_bar = i
        if low < extreme_low:
            extreme_low = low
            extreme_low_bar = i

        if current_type is None:
            up_move = ((extreme_high - extreme_low) / extreme_low) * 100
            down_move = ((extreme_high - extreme_low) / extreme_high) * 100

            if up_move >= min_pct:
                swings.append({'bar': extreme_low_bar, 'price': extreme_low, 'type': 'LOW'})
                current_type = 'HIGH'
                current_bar = extreme_high_bar
                current_price = extreme_high
                extreme_low = high
                extreme_low_bar = i
            elif down_move >= min_pct:
                swings.append({'bar': extreme_high_bar, 'price': extreme_high, 'type': 'HIGH'})
                current_type = 'LOW'
                current_bar = extreme_low_bar
                current_price = extreme_low
                extreme_high = low
                extreme_high_bar = i

        elif current_type == 'HIGH':
            down_move = ((current_price - extreme_low) / current_price) * 100
            if down_move >= min_pct:
                swings.append({'bar': extreme_low_bar, 'price': extreme_low, 'type': 'LOW'})
                current_type = 'LOW'
                current_bar = extreme_low_bar
                current_price = extreme_low
                extreme_high = high
                extreme_high_bar = i

        elif current_type == 'LOW':
            up_move = ((extreme_high - current_price) / current_price) * 100
            if up_move >= min_pct:
                swings.append({'bar': extreme_high_bar, 'price': extreme_high, 'type': 'HIGH'})
                current_type = 'HIGH'
                current_bar = extreme_high_bar
                current_price = extreme_high
                extreme_low = low
                extreme_low_bar = i

    return swings

tp_pct = 4.0
scale_start = 50
scale_step = 5
max_scales = 10

test_months = ['2025-09', '2025-10', '2025-11', '2025-12']

# Test różnych downtrend thresholds
downtrend_filters = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
all_results = []

for dt_filter in downtrend_filters:
    monthly_results = []

    for month_str in test_months:
        df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

        equity = 100.0
        peak_equity = 100.0
        max_dd = 0.0
        trades = []

        swing_points = zigzag_indicator(df_month, min_pct=2.0)

        i = 0
        while i < len(swing_points) - 2:
            p1 = swing_points[i]

            if p1['type'] != 'HIGH':
                i += 1
                continue

            j = i + 1
            while j < len(swing_points) and swing_points[j]['type'] != 'LOW':
                j += 1

            if j >= len(swing_points):
                break

            p2 = swing_points[j]

            k = j + 1
            while k < len(swing_points) and swing_points[k]['type'] != 'HIGH':
                k += 1

            if k >= len(swing_points):
                break

            p3 = swing_points[k]

            # FILTR: p3 musi być co najmniej dt_filter% niższy od p1
            drop_pct = ((p1['price'] - p3['price']) / p1['price']) * 100

            if p3['price'] < p1['price'] and drop_pct >= dt_filter:
                sl_price = p3['price']
                bar_low = p2['bar']
                bar_high = p3['bar']

                bounce_size = p3['price'] - p2['price']

                position_entries = []
                total_position_size = 0.0

                scale_levels = []
                for pct in range(scale_start, 100, scale_step):
                    scale_price = p2['price'] + (bounce_size * pct / 100)
                    scale_levels.append({'pct': pct, 'price': scale_price, 'filled': False})

                for m in range(bar_high + 1, min(bar_high + 100, len(df_month))):
                    row = df_month.iloc[m]

                    for level in scale_levels:
                        if not level['filled'] and row['high'] >= level['price']:
                            entry_price = level['price']
                            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                            if sl_dist_pct > 0 and sl_dist_pct <= 10.0:
                                target_risk = equity * 5.0 / max_scales / 100
                                calculated_size = target_risk / (sl_dist_pct / 100)
                                max_size_per_entry = equity / max_scales
                                entry_size = min(calculated_size, max_size_per_entry)

                                position_entries.append({
                                    'bar': m,
                                    'price': entry_price,
                                    'size': entry_size
                                })

                                total_position_size += entry_size
                                level['filled'] = True

                    if len(position_entries) > 0:
                        avg_entry = sum([e['price'] * e['size'] for e in position_entries]) / total_position_size
                        tp_price = avg_entry * (1 - tp_pct / 100)

                        if row['high'] >= sl_price:
                            sl_dist = ((sl_price - avg_entry) / avg_entry) * 100
                            pnl_pct = -sl_dist
                            pnl_dollar = total_position_size * (pnl_pct / 100)
                            equity += pnl_dollar

                            if equity > peak_equity:
                                peak_equity = equity
                            dd = ((peak_equity - equity) / peak_equity) * 100
                            if dd > max_dd:
                                max_dd = dd

                            trades.append({'result': 'SL', 'pnl': pnl_dollar})
                            break

                        elif row['low'] <= tp_price:
                            tp_dist = ((avg_entry - tp_price) / avg_entry) * 100
                            pnl_pct = tp_dist
                            pnl_dollar = total_position_size * (pnl_pct / 100)
                            equity += pnl_dollar

                            if equity > peak_equity:
                                peak_equity = equity
                            dd = ((peak_equity - equity) / peak_equity) * 100
                            if dd > max_dd:
                                max_dd = dd

                            trades.append({'result': 'TP', 'pnl': pnl_dollar})
                            break

            i = k

        # Stats
        if len(trades) > 0:
            trades_df = pd.DataFrame(trades)
            total_return = ((equity - 100) / 100) * 100
            sl_hits = len(trades_df[trades_df['result'] == 'SL'])
            tp_hits = len(trades_df[trades_df['result'] == 'TP'])
            win_rate = (tp_hits / len(trades_df)) * 100

            monthly_results.append({
                'month': month_str,
                'return': total_return,
                'max_dd': max_dd,
                'trades': len(trades_df),
                'sl_hits': sl_hits,
                'tp_hits': tp_hits,
                'win_rate': win_rate
            })
        else:
            monthly_results.append({
                'month': month_str,
                'return': 0,
                'max_dd': 0,
                'trades': 0,
                'sl_hits': 0,
                'tp_hits': 0,
                'win_rate': 0
            })

    # Overall
    compounded = 100.0
    for m in monthly_results:
        compounded *= (1 + m['return'] / 100)

    total_return = ((compounded - 100) / 100) * 100
    overall_max_dd = max([m['max_dd'] for m in monthly_results])
    return_dd = total_return / overall_max_dd if overall_max_dd > 0 else 0
    total_trades = sum([m['trades'] for m in monthly_results])
    total_sl = sum([m['sl_hits'] for m in monthly_results])
    total_tp = sum([m['tp_hits'] for m in monthly_results])
    sl_rate = (total_sl / total_trades * 100) if total_trades > 0 else 0

    all_results.append({
        'dt_filter': dt_filter,
        'total_return': total_return,
        'max_dd': overall_max_dd,
        'return_dd': return_dd,
        'total_trades': total_trades,
        'sl_rate': sl_rate,
        'tp_rate': (total_tp / total_trades * 100) if total_trades > 0 else 0
    })

# Display
results_df = pd.DataFrame(all_results)

print(f"{'DT Filter%':<11} | {'Return':<10} | {'Max DD':<8} | {'R/DD':<7} | {'Trades':<7} | {'SL%':<6} | {'TP%':<6}")
print("-"*140)

for idx, row in results_df.iterrows():
    status = "✅" if row['total_return'] > 0 and row['sl_rate'] < 50 else "❌"
    print(f"{row['dt_filter']:>9.1f}% | {row['total_return']:>8.1f}% | {row['max_dd']:>6.1f}% | {row['return_dd']:>5.2f}x | {row['total_trades']:<7} | {row['sl_rate']:>4.1f}% | {row['tp_rate']:>4.1f}% {status}")

print()
print("="*140)
print("WNIOSEK:")
print("="*140)

best = results_df[results_df['return_dd'] == results_df['return_dd'].max()].iloc[0]

if best['total_trades'] == 0:
    print("❌ ŻEN FILTR NIE WYKRYWA ŻADNYCH DOWNTRENDS")
    print("   Problem: ZigZag 2% + downtrend filter za restrykcyjny")
    print()
    print("Możliwe rozwiązania:")
    print("  1. Użyj MNIEJSZEGO ZigZag threshold (np. 1.5% zamiast 2%)")
    print("  2. Szukaj downtrends na WIĘKSZYM timeframe (4h struktura, trade na 15m)")
    print("  3. PORZUĆ tę strategię - struktura 'lower high' nie działa na 15m")
else:
    if best['sl_rate'] < 50:
        print(f"✅ NAJLEPSZY: DT Filter = {best['dt_filter']}%")
        print(f"   Return: {best['total_return']:+.1f}%")
        print(f"   R/DD: {best['return_dd']:.2f}x")
        print(f"   SL rate: {best['sl_rate']:.1f}%")
        print(f"   Trades: {best['total_trades']}")
        print()
        print("Teoria użytkownika DZIAŁA z właściwym filtrem!")
    else:
        print(f"❌ NAJLEPSZY: DT Filter = {best['dt_filter']}%")
        print(f"   Ale SL rate wciąż {best['sl_rate']:.1f}% (powinno <50%)")
        print()
        print("Teoria użytkownika NIE działa nawet z filtrem.")

print("="*140)
