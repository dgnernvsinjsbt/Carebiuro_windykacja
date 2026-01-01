#!/usr/bin/env python3
"""
STRUKTURA DOWNTREND + SCALING - Z ZIGZAG INDICATOR

ZMIANA: Używamy ZigZag (min 2% move) zamiast lookback=5
OCZEKIWANIE: SL rate spadnie z 69% do <30% (bo prawdziwe downtrends)
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
print("STRATEGIA: DOWNTREND STRUCTURE + SCALING - ZIGZAG INDICATOR")
print("="*140)
print()

# ============================================
# ZIGZAG INDICATOR FUNCTION
# ============================================
def zigzag_indicator(df, min_pct=2.0):
    """ZigZag indicator - wykrywa tylko major swings (>= min_pct% move)"""
    swings = []
    current_price = df.iloc[0]['close']
    current_type = None
    current_bar = 0

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
                swings.append({
                    'bar': extreme_low_bar,
                    'price': extreme_low,
                    'type': 'LOW',
                    'time': df.iloc[extreme_low_bar]['timestamp']
                })
                current_type = 'HIGH'
                current_bar = extreme_high_bar
                current_price = extreme_high
                extreme_low = high
                extreme_low_bar = i
            elif down_move >= min_pct:
                swings.append({
                    'bar': extreme_high_bar,
                    'price': extreme_high,
                    'type': 'HIGH',
                    'time': df.iloc[extreme_high_bar]['timestamp']
                })
                current_type = 'LOW'
                current_bar = extreme_low_bar
                current_price = extreme_low
                extreme_high = low
                extreme_high_bar = i

        elif current_type == 'HIGH':
            down_move = ((current_price - extreme_low) / current_price) * 100
            if down_move >= min_pct:
                swings.append({
                    'bar': extreme_low_bar,
                    'price': extreme_low,
                    'type': 'LOW',
                    'time': df.iloc[extreme_low_bar]['timestamp']
                })
                current_type = 'LOW'
                current_bar = extreme_low_bar
                current_price = extreme_low
                extreme_high = high
                extreme_high_bar = i

        elif current_type == 'LOW':
            up_move = ((extreme_high - current_price) / current_price) * 100
            if up_move >= min_pct:
                swings.append({
                    'bar': extreme_high_bar,
                    'price': extreme_high,
                    'type': 'HIGH',
                    'time': df.iloc[extreme_high_bar]['timestamp']
                })
                current_type = 'HIGH'
                current_bar = extreme_high_bar
                current_price = extreme_high
                extreme_low = low
                extreme_low_bar = i

    return swings

# ============================================
# STRATEGIA Z ZIGZAG
# ============================================
tp_pct = 4.0
scale_start = 50
scale_step = 5
max_scales = 10

test_months = ['2025-09', '2025-10', '2025-11', '2025-12']
results = []

for month_str in test_months:
    df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

    equity = 100.0
    peak_equity = 100.0
    max_dd = 0.0
    trades = []

    # Wykryj swing points ZIGZAG
    swing_points = zigzag_indicator(df_month, min_pct=2.0)

    # Strategia
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

        if p3['price'] < p1['price']:
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
                            # POPRAWIONY POSITION SIZING
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

                    equity_before = equity

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

                        trades.append({
                            'entries': len(position_entries),
                            'total_size': total_position_size,
                            'result': 'SL',
                            'pnl': pnl_dollar
                        })

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

                        trades.append({
                            'entries': len(position_entries),
                            'total_size': total_position_size,
                            'result': 'TP',
                            'pnl': pnl_dollar
                        })

                        break

        i = k

    # Stats
    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        total_return = ((equity - 100) / 100) * 100
        winners = trades_df[trades_df['pnl'] > 0]
        losers = trades_df[trades_df['pnl'] < 0]
        win_rate = (len(winners) / len(trades_df)) * 100

        sl_hits = len(trades_df[trades_df['result'] == 'SL'])
        tp_hits = len(trades_df[trades_df['result'] == 'TP'])

        max_pos_size = trades_df['total_size'].max()
        avg_pos_size = trades_df['total_size'].mean()

        results.append({
            'month': month_str,
            'return': total_return,
            'max_dd': max_dd,
            'return_dd': total_return / max_dd if max_dd > 0 else 0,
            'win_rate': win_rate,
            'trades': len(trades_df),
            'sl_hits': sl_hits,
            'tp_hits': tp_hits,
            'final_equity': equity,
            'max_pos_size': max_pos_size,
            'avg_pos_size': avg_pos_size
        })
    else:
        results.append({
            'month': month_str,
            'return': 0,
            'max_dd': 0,
            'return_dd': 0,
            'win_rate': 0,
            'trades': 0,
            'sl_hits': 0,
            'tp_hits': 0,
            'final_equity': equity,
            'max_pos_size': 0,
            'avg_pos_size': 0
        })

# Display
results_df = pd.DataFrame(results)

print(f"{'Month':<10} | {'Return':<10} | {'Max DD':<8} | {'R/DD':<7} | {'WR%':<6} | {'Trades':<7} | {'TP':<4} | {'SL':<4} | {'SL%':<6} | {'Final $':<12}")
print("-"*140)

for idx, row in results_df.iterrows():
    sl_rate = (row['sl_hits'] / row['trades'] * 100) if row['trades'] > 0 else 0
    status = "✅" if row['return'] > 0 else "❌"
    print(f"{row['month']:<10} | {row['return']:>8.1f}% | {row['max_dd']:>6.1f}% | {row['return_dd']:>5.2f}x | {row['win_rate']:>4.1f}% | {row['trades']:<7} | {row['tp_hits']:<4} | {row['sl_hits']:<4} | {sl_rate:>4.1f}% | ${row['final_equity']:>10,.2f} {status}")

print()

# Position sizing check
print("="*140)
print("POSITION SIZING CHECK")
print("="*140)
for idx, row in results_df.iterrows():
    if row['trades'] > 0:
        leverage = row['max_pos_size'] / row['final_equity'] if row['final_equity'] > 0 else 0
        print(f"{row['month']}: Max pos ${row['max_pos_size']:,.2f} / Equity ${row['final_equity']:,.2f} = {leverage:.2f}x leverage {'✅' if leverage <= 1.2 else '❌ TOO HIGH'}")

print()

# Overall
compounded = 100.0
for idx, row in results_df.iterrows():
    compounded *= (1 + row['return'] / 100)

total_return = ((compounded - 100) / 100) * 100
overall_max_dd = results_df['max_dd'].max()
overall_return_dd = total_return / overall_max_dd if overall_max_dd > 0 else 0
wins = len(results_df[results_df['return'] > 0])
total_trades = results_df['trades'].sum()
total_sl = results_df['sl_hits'].sum()
total_tp = results_df['tp_hits'].sum()

print("="*140)
print("PODSUMOWANIE (Sep-Dec 2025) - ZIGZAG INDICATOR:")
print(f"  Compounded Return: {total_return:+.1f}%")
print(f"  Max Drawdown: {overall_max_dd:.1f}%")
print(f"  Return/DD Ratio: {overall_return_dd:.2f}x")
print(f"  Winning Months: {wins}/4")
print(f"  Total Trades: {total_trades}")
print(f"  Total TP hits: {total_tp} ({total_tp/total_trades*100 if total_trades > 0 else 0:.1f}%)")
print(f"  Total SL hits: {total_sl} ({total_sl/total_trades*100 if total_trades > 0 else 0:.1f}%)")
print()

# PORÓWNANIE
print("="*140)
print("PORÓWNANIE: Lookback=5 vs ZigZag")
print("="*140)
print("LOOKBACK=5 (stara wersja):")
print("  - Return: +296.3%")
print("  - R/DD: 29.76x")
print("  - SL rate: 69% ❌ (zbyt wysoki - teoria nie działa)")
print()
print("ZIGZAG (nowa wersja):")
print(f"  - Return: {total_return:+.1f}%")
print(f"  - R/DD: {overall_return_dd:.2f}x")
print(f"  - SL rate: {total_sl/total_trades*100 if total_trades > 0 else 0:.1f}% {'✅ (teoria działa!)' if (total_sl/total_trades*100 if total_trades > 0 else 0) < 40 else '❌ (teoria wciąż nie działa)'}")
print()
print("="*140)
