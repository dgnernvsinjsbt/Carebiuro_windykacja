#!/usr/bin/env python3
"""
Strategia ZIGZAG w downtrendzie:
1. Wykryj downtrend (lower highs, poniżej MA)
2. Wykryj spadek (HIGH → LOW)
3. Czekaj na odbicie do ~70% spadku
4. SHORT z SL powyżej odbicia, TP na kolejny spadek
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# MA
df['ma_50'] = df['close'].rolling(window=50).mean()

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

df['month'] = df['timestamp'].dt.to_period('M')

print("="*140)
print("STRATEGIA ZIGZAG - TEST NA SEP-DEC 2025")
print("="*140)
print()

# Parametry (z analizy)
lookback = 5  # wykrywanie swing points
retrace_target_pct = 70  # shortuj gdy odbicie osiągnie 70% spadku
tp_pct = 3.7  # oczekiwany kolejny spadek (mediana)
max_sl_pct = 10.0  # max stop loss

test_months = ['2025-09', '2025-10', '2025-11', '2025-12']
results = []

for month_str in test_months:
    df_month = df[df['month'] == month_str].copy().reset_index(drop=True)

    equity = 100.0
    peak_equity = 100.0
    max_dd = 0.0
    trades = []

    # Wykryj swing points dla tego miesiąca
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

    # Szukaj wzorów zigzag: HIGH → LOW → teraz śledzimy odbicie
    i = 0
    while i < len(swing_points) - 1:
        p_high = swing_points[i]

        if p_high['type'] != 'HIGH':
            i += 1
            continue

        # Szukaj następnego LOW
        j = i + 1
        while j < len(swing_points) and swing_points[j]['type'] != 'LOW':
            j += 1

        if j >= len(swing_points):
            break

        p_low = swing_points[j]

        # Sprawdź czy w downtrendzie (cena poniżej MA50 w momencie HIGH)
        bar_high = p_high['bar']
        if pd.isna(df_month.iloc[bar_high]['ma_50']) or df_month.iloc[bar_high]['close'] >= df_month.iloc[bar_high]['ma_50']:
            i = j
            continue

        # Mamy HIGH → LOW w downtrendzie
        drop_pct = ((p_high['price'] - p_low['price']) / p_high['price']) * 100

        if drop_pct < 1.0:  # Pomiń małe spadki
            i = j
            continue

        # Oblicz target retrace price (70% spadku z powrotem)
        drop_size = p_high['price'] - p_low['price']
        target_retrace_price = p_low['price'] + (drop_size * retrace_target_pct / 100)

        # Śledź cenę od LOW, czekaj aż odbije do target
        bar_low = p_low['bar']

        for k in range(bar_low + 1, min(bar_low + 50, len(df_month))):
            row = df_month.iloc[k]

            # Czy cena osiągnęła target retrace?
            if row['high'] >= target_retrace_price:
                # ENTRY SHORT na close tego candla (lub limit na target)
                entry_price = min(target_retrace_price, row['close'])

                # SL: znajdź local high po low (swing high odbicia)
                sl_price = df_month.iloc[bar_low:k+1]['high'].max()

                # TP: oczekuj spadku o tp_pct
                tp_price = entry_price * (1 - tp_pct / 100)

                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                if sl_dist_pct > 0 and sl_dist_pct <= max_sl_pct:
                    position_size = (equity * 5.0) / sl_dist_pct

                    # Znajdź exit
                    hit_sl = False
                    hit_tp = False

                    for m in range(k + 1, min(k + 100, len(df_month))):
                        exit_row = df_month.iloc[m]

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

                        # Track DD
                        if equity > peak_equity:
                            peak_equity = equity
                        dd = ((peak_equity - equity) / peak_equity) * 100
                        if dd > max_dd:
                            max_dd = dd

                        trades.append({
                            'result': 'TP' if hit_tp else 'SL',
                            'pnl': pnl_dollar
                        })

                # Po wejściu w trade, przeskocz dalej
                break

        i = j

    # Stats
    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        total_return = ((equity - 100) / 100) * 100
        winners = trades_df[trades_df['pnl'] > 0]
        win_rate = (len(winners) / len(trades_df)) * 100

        results.append({
            'month': month_str,
            'return': total_return,
            'max_dd': max_dd,
            'return_dd': total_return / max_dd if max_dd > 0 else 0,
            'win_rate': win_rate,
            'trades': len(trades_df)
        })
    else:
        results.append({
            'month': month_str,
            'return': 0,
            'max_dd': 0,
            'return_dd': 0,
            'win_rate': 0,
            'trades': 0
        })

# Display
results_df = pd.DataFrame(results)

print(f"{'Month':<10} | {'Return':<10} | {'Max DD':<8} | {'R/DD':<7} | {'Win Rate':<9} | {'Trades':<7}")
print("-"*140)

for idx, row in results_df.iterrows():
    status = "✅" if row['return'] > 0 else "❌"
    print(f"{row['month']:<10} | {row['return']:>8.1f}% | {row['max_dd']:>6.1f}% | {row['return_dd']:>5.2f}x | {row['win_rate']:>7.1f}% | {row['trades']:<7} {status}")

print()

# Overall stats
compounded = 100.0
for idx, row in results_df.iterrows():
    compounded *= (1 + row['return'] / 100)

total_return = ((compounded - 100) / 100) * 100
overall_max_dd = results_df['max_dd'].max()
overall_return_dd = total_return / overall_max_dd if overall_max_dd > 0 else 0
wins = len(results_df[results_df['return'] > 0])
total_trades = results_df['trades'].sum()

print("="*140)
print("PODSUMOWANIE (Sep-Dec 2025):")
print(f"  Compounded Return: {total_return:+.1f}%")
print(f"  Max Drawdown: {overall_max_dd:.1f}%")
print(f"  Return/DD Ratio: {overall_return_dd:.2f}x")
print(f"  Winning Months: {wins}/4")
print(f"  Total Trades: {total_trades}")
print(f"  Avg Trades/Month: {total_trades/4:.1f}")
print("="*140)
