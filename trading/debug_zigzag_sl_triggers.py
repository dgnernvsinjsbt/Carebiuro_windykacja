#!/usr/bin/env python3
"""
DEBUG: Dlaczego SL się triggerują w ZigZag downtrends?
Wizualizuj każdy trade: gdzie był entry, SL, TP
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

# September only
df_sep = df[(df['timestamp'] >= '2025-09-01') & (df['timestamp'] < '2025-10-01')].copy().reset_index(drop=True)

print("="*140)
print("DEBUG: ZIGZAG DOWNTREND SL TRIGGERS - SEPTEMBER")
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
                swings.append({'bar': extreme_low_bar, 'price': extreme_low, 'type': 'LOW', 'time': df.iloc[extreme_low_bar]['timestamp']})
                current_type = 'HIGH'
                current_bar = extreme_high_bar
                current_price = extreme_high
                extreme_low = high
                extreme_low_bar = i
            elif down_move >= min_pct:
                swings.append({'bar': extreme_high_bar, 'price': extreme_high, 'type': 'HIGH', 'time': df.iloc[extreme_high_bar]['timestamp']})
                current_type = 'LOW'
                current_bar = extreme_low_bar
                current_price = extreme_low
                extreme_high = low
                extreme_high_bar = i

        elif current_type == 'HIGH':
            down_move = ((current_price - extreme_low) / current_price) * 100
            if down_move >= min_pct:
                swings.append({'bar': extreme_low_bar, 'price': extreme_low, 'type': 'LOW', 'time': df.iloc[extreme_low_bar]['timestamp']})
                current_type = 'LOW'
                current_bar = extreme_low_bar
                current_price = extreme_low
                extreme_high = high
                extreme_high_bar = i

        elif current_type == 'LOW':
            up_move = ((extreme_high - current_price) / current_price) * 100
            if up_move >= min_pct:
                swings.append({'bar': extreme_high_bar, 'price': extreme_high, 'type': 'HIGH', 'time': df.iloc[extreme_high_bar]['timestamp']})
                current_type = 'HIGH'
                current_bar = extreme_high_bar
                current_price = extreme_high
                extreme_low = low
                extreme_low_bar = i

    return swings

swing_points = zigzag_indicator(df_sep, min_pct=2.0)

tp_pct = 4.0
scale_start = 50
scale_step = 5
max_scales = 10

equity = 100.0
trades = []

i = 0
trade_num = 0
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
        trade_num += 1
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

        for m in range(bar_high + 1, min(bar_high + 100, len(df_sep))):
            row = df_sep.iloc[m]

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

                    trades.append({
                        'num': trade_num,
                        'time': df_sep.iloc[m]['timestamp'],
                        'p1_high': p1['price'],
                        'p1_time': p1['time'],
                        'p2_low': p2['price'],
                        'p2_time': p2['time'],
                        'p3_high': p3['price'],
                        'p3_time': p3['time'],
                        'entries': len(position_entries),
                        'avg_entry': avg_entry,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'result': 'SL',
                        'pnl': pnl_dollar,
                        'exit_time': df_sep.iloc[m]['timestamp']
                    })

                    equity += pnl_dollar
                    break

                elif row['low'] <= tp_price:
                    tp_dist = ((avg_entry - tp_price) / avg_entry) * 100
                    pnl_pct = tp_dist
                    pnl_dollar = total_position_size * (pnl_pct / 100)

                    trades.append({
                        'num': trade_num,
                        'time': df_sep.iloc[m]['timestamp'],
                        'p1_high': p1['price'],
                        'p1_time': p1['time'],
                        'p2_low': p2['price'],
                        'p2_time': p2['time'],
                        'p3_high': p3['price'],
                        'p3_time': p3['time'],
                        'entries': len(position_entries),
                        'avg_entry': avg_entry,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'result': 'TP',
                        'pnl': pnl_dollar,
                        'exit_time': df_sep.iloc[m]['timestamp']
                    })

                    equity += pnl_dollar
                    break

    i = k

# Analiza
trades_df = pd.DataFrame(trades)

print(f"Total Trades: {len(trades_df)}")
print(f"SL hits: {len(trades_df[trades_df['result'] == 'SL'])} ({len(trades_df[trades_df['result'] == 'SL'])/len(trades_df)*100:.1f}%)")
print(f"TP hits: {len(trades_df[trades_df['result'] == 'TP'])} ({len(trades_df[trades_df['result'] == 'TP'])/len(trades_df)*100:.1f}%)")
print()

print("="*140)
print("WSZYSTKIE TRADES:")
print("="*140)
print(f"{'#':<3} | {'Result':<6} | {'P1 High':<10} | {'P2 Low':<10} | {'P3 High (SL)':<14} | {'Avg Entry':<10} | {'TP':<10} | {'Drop%':<7}")
print("-"*140)

for idx, t in trades_df.iterrows():
    drop_pct = ((t['p1_high'] - t['p3_high']) / t['p1_high']) * 100
    status = "✅ TP" if t['result'] == 'TP' else "❌ SL"
    print(f"{t['num']:<3} | {status:<6} | ${t['p1_high']:.6f} | ${t['p2_low']:.6f} | ${t['p3_high']:.6f} | ${t['avg_entry']:.6f} | ${t['tp_price']:.6f} | {drop_pct:>5.2f}%")

print()
print("="*140)
print("ANALIZA SL TRIGGERS:")
print("="*140)

sl_trades = trades_df[trades_df['result'] == 'SL']

print(f"\nPRZYCZYNA: W {len(sl_trades)}/{len(trades_df)} trades cena WRACA powyżej p3 (lower high)")
print()
print("To znaczy że:")
print("  1. ❌ TEORIA NIE DZIAŁA: 'lower high' NIE jest dobrym poziomem SL")
print("  2. ❌ Bounce po spadku często PRZEBIJA poprzedni high")
print("  3. ❌ Scaling na bounce nie działa bo SL za blisko")
print()
print("Możliwe rozwiązania:")
print("  A. SL WYŻEJ: np. p3_high + 1-2 ATR (daj więcej przestrzeni)")
print("  B. ZMIEŃ ENTRY: wchodź PÓŹNIEJ, np. dopiero gdy cena SPADA poniżej 50% bounce")
print("  C. PORZUĆ TĘ STRATEGIĘ: struktura 'lower high' nie daje edge")
print()

# Sprawdź: o ile % cena przebija SL
print("="*140)
print("O ILE % CENA PRZEBIJA SL?")
print("="*140)

for idx, t in sl_trades.iterrows():
    # Znajdź ile wysoko poszła cena po exit
    exit_bar = df_sep[df_sep['timestamp'] == t['exit_time']].index[0]
    max_high_after = df_sep.iloc[exit_bar:min(exit_bar+20, len(df_sep))]['high'].max()

    overshoot_pct = ((max_high_after - t['sl_price']) / t['sl_price']) * 100

    print(f"Trade #{t['num']}: SL ${t['sl_price']:.6f} → Max high ${max_high_after:.6f} (overshoot: +{overshoot_pct:.2f}%)")

print()
print("="*140)
