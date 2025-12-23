#!/usr/bin/env python3
"""
STRUKTURA DOWNTREND + SKALOWANIE POZYCJI:

1. Wykryj downtrend przez strukturę (lower highs, lower lows)
2. Gdy jest lower high i zaczyna spadać, czekaj na bounce
3. Skaluj wejścia: 50%, 55%, 60%, 65%, 70%, 75%, 80%, 85%, 90%, 95% bounce'u
4. SL na sztywno: powyżej ostatniego lower high
5. TP: średni spadek ~4%

KLUCZOWE: W downtrendzie SL nie powinien się triggerować!
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
print("STRATEGIA: DOWNTREND STRUCTURE + POSITION SCALING")
print("="*140)
print()

lookback = 5  # dla wykrywania swing points
tp_pct = 4.0  # średni spadek z analizy
scale_start = 50  # zaczynamy skalować od 50% bounce'u
scale_step = 5  # co 5%
max_scales = 10  # max 10 wejść (50%, 55%, 60%...95%)

test_months = ['2025-09', '2025-10', '2025-11', '2025-12']
results = []

for month_str in test_months:
    df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

    equity = 100.0
    peak_equity = 100.0
    max_dd = 0.0
    trades = []

    # Wykryj swing points
    swing_points = []

    for i in range(lookback, len(df_month) - lookback):
        # Swing HIGH
        is_swing_high = True
        for j in range(1, lookback + 1):
            if df_month.iloc[i]['high'] <= df_month.iloc[i-j]['high'] or df_month.iloc[i]['high'] <= df_month.iloc[i+j]['high']:
                is_swing_high = False
                break

        if is_swing_high:
            swing_points.append({
                'bar': i,
                'price': df_month.iloc[i]['high'],
                'type': 'HIGH'
            })
            continue

        # Swing LOW
        is_swing_low = True
        for j in range(1, lookback + 1):
            if df_month.iloc[i]['low'] >= df_month.iloc[i-j]['low'] or df_month.iloc[i]['low'] >= df_month.iloc[i+j]['low']:
                is_swing_low = False
                break

        if is_swing_low:
            swing_points.append({
                'bar': i,
                'price': df_month.iloc[i]['low'],
                'type': 'LOW'
            })

    # Szukaj downtrend structure: HIGH → LOW → lower HIGH
    i = 0
    while i < len(swing_points) - 2:
        p1 = swing_points[i]

        if p1['type'] != 'HIGH':
            i += 1
            continue

        # Znajdź następny LOW
        j = i + 1
        while j < len(swing_points) and swing_points[j]['type'] != 'LOW':
            j += 1

        if j >= len(swing_points):
            break

        p2 = swing_points[j]  # LOW

        # Znajdź następny HIGH
        k = j + 1
        while k < len(swing_points) and swing_points[k]['type'] != 'HIGH':
            k += 1

        if k >= len(swing_points):
            break

        p3 = swing_points[k]  # Następny HIGH

        # DOWNTREND: p3 (lower high) < p1 (poprzedni high)
        if p3['price'] < p1['price']:
            # Mamy strukturę: HIGH (p1) → LOW (p2) → lower HIGH (p3)
            # p3 to nasz lower high, to poziom SL
            sl_price = p3['price']
            bar_low = p2['bar']
            bar_high = p3['bar']

            # Oblicz wielkość bounce'u (od LOW do lower HIGH)
            bounce_size = p3['price'] - p2['price']

            # Śledź cenę po lower high, czekaj na spadek i bounce
            # Skaluj wejścia od 50% do 95% bounce'u
            position_entries = []
            total_position_size = 0.0

            # Oblicz pozycje do skalowania
            scale_levels = []
            for pct in range(scale_start, 100, scale_step):
                scale_price = p2['price'] + (bounce_size * pct / 100)
                scale_levels.append({'pct': pct, 'price': scale_price, 'filled': False})

            # Śledź cenę po p3 (lower high)
            for m in range(bar_high + 1, min(bar_high + 100, len(df_month))):
                row = df_month.iloc[m]

                # Sprawdź czy cena wraca do któregoś z poziomów skalowania
                for level in scale_levels:
                    if not level['filled'] and row['high'] >= level['price']:
                        # Wejście na tym poziomie
                        entry_price = level['price']

                        # Oblicz wielkość dla tego wejścia (równe części)
                        # Całkowity risk: 5% equity, podzielony na max_scales wejść
                        sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                        if sl_dist_pct > 0 and sl_dist_pct <= 10.0:
                            # Risk per entry = (total_risk / max_scales)
                            risk_per_entry = equity * 5.0 / max_scales / 100
                            entry_size = risk_per_entry / (sl_dist_pct / 100)

                            position_entries.append({
                                'bar': m,
                                'price': entry_price,
                                'size': entry_size
                            })

                            total_position_size += entry_size
                            level['filled'] = True

                # Jeśli mamy jakiekolwiek wejścia, sprawdź SL/TP
                if len(position_entries) > 0:
                    # TP: średni entry - 4%
                    avg_entry = sum([e['price'] * e['size'] for e in position_entries]) / total_position_size
                    tp_price = avg_entry * (1 - tp_pct / 100)

                    # Sprawdź SL
                    if row['high'] >= sl_price:
                        # SL HIT - downtrend złamany!
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
                            'avg_entry': avg_entry,
                            'sl_price': sl_price,
                            'result': 'SL',
                            'pnl': pnl_dollar
                        })

                        break

                    # Sprawdź TP
                    elif row['low'] <= tp_price:
                        # TP HIT
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
                            'avg_entry': avg_entry,
                            'tp_price': tp_price,
                            'result': 'TP',
                            'pnl': pnl_dollar
                        })

                        break

        i = k  # Przeskocz do następnego cycle

    # Stats
    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        total_return = ((equity - 100) / 100) * 100
        winners = trades_df[trades_df['pnl'] > 0]
        losers = trades_df[trades_df['pnl'] < 0]
        win_rate = (len(winners) / len(trades_df)) * 100

        sl_hits = len(trades_df[trades_df['result'] == 'SL'])
        tp_hits = len(trades_df[trades_df['result'] == 'TP'])

        results.append({
            'month': month_str,
            'return': total_return,
            'max_dd': max_dd,
            'return_dd': total_return / max_dd if max_dd > 0 else 0,
            'win_rate': win_rate,
            'trades': len(trades_df),
            'sl_hits': sl_hits,
            'tp_hits': tp_hits
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
            'tp_hits': 0
        })

# Display
results_df = pd.DataFrame(results)

print(f"{'Month':<10} | {'Return':<10} | {'Max DD':<8} | {'R/DD':<7} | {'Win Rate':<9} | {'Trades':<7} | {'TP':<5} | {'SL':<5}")
print("-"*140)

for idx, row in results_df.iterrows():
    status = "✅" if row['return'] > 0 else "❌"
    print(f"{row['month']:<10} | {row['return']:>8.1f}% | {row['max_dd']:>6.1f}% | {row['return_dd']:>5.2f}x | {row['win_rate']:>7.1f}% | {row['trades']:<7} | {row['tp_hits']:<5} | {row['sl_hits']:<5} {status}")

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
print("PODSUMOWANIE (Sep-Dec 2025):")
print(f"  Compounded Return: {total_return:+.1f}%")
print(f"  Max Drawdown: {overall_max_dd:.1f}%")
print(f"  Return/DD Ratio: {overall_return_dd:.2f}x")
print(f"  Winning Months: {wins}/4")
print(f"  Total Trades: {total_trades}")
print(f"  Total TP hits: {total_tp}")
print(f"  Total SL hits: {total_sl}")
print()
print(f"  💡 SL Rate: {total_sl/total_trades*100 if total_trades > 0 else 0:.1f}% (powinno być niskie w prawdziwym downtrendzie!)")
print("="*140)
