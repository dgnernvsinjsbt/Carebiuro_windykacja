#!/usr/bin/env python3
"""
Analiza wzoru zigzag w downtrendzie
- Wykrywamy swing highs i swing lows
- Mierzymy spadki i odbicia (retraces)
- Znajdujemy średnie proporcje
"""
import pandas as pd
import numpy as np

df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# MA dla potwierdzenia downtrend
df['ma_50'] = df['close'].rolling(window=50).mean()
df['ma_200'] = df['close'].rolling(window=200).mean()

print("="*140)
print("ANALIZA WZORU ZIGZAG W DOWNTRENDZIE")
print("="*140)
print()

# Wykrywamy swing points (lokalne szczyty i dołki)
lookback = 5  # patrzymy 5 candles w każdą stronę

swing_points = []

for i in range(lookback, len(df) - lookback):
    # Swing HIGH (lokalny szczyt)
    is_swing_high = True
    for j in range(1, lookback + 1):
        if df.iloc[i]['high'] <= df.iloc[i-j]['high'] or df.iloc[i]['high'] <= df.iloc[i+j]['high']:
            is_swing_high = False
            break

    if is_swing_high:
        swing_points.append({
            'bar': i,
            'time': df.iloc[i]['timestamp'],
            'price': df.iloc[i]['high'],
            'type': 'HIGH'
        })
        continue

    # Swing LOW (lokalny dołek)
    is_swing_low = True
    for j in range(1, lookback + 1):
        if df.iloc[i]['low'] >= df.iloc[i-j]['low'] or df.iloc[i]['low'] >= df.iloc[i+j]['low']:
            is_swing_low = False
            break

    if is_swing_low:
        swing_points.append({
            'bar': i,
            'time': df.iloc[i]['timestamp'],
            'price': df.iloc[i]['low'],
            'type': 'LOW'
        })

print(f"Znaleziono {len(swing_points)} swing points (HIGHs i LOWs)")
print()

# Analizujemy wzory zigzag w downtrendach
zigzags = []

for i in range(len(swing_points) - 2):
    p1 = swing_points[i]
    p2 = swing_points[i + 1]
    p3 = swing_points[i + 2]

    # Wzór: HIGH → LOW → HIGH (odbicie w downtrendzie)
    if p1['type'] == 'HIGH' and p2['type'] == 'LOW' and p3['type'] == 'HIGH':
        # Sprawdź czy w downtrendzie (p3 < p1 = lower high)
        if p3['price'] < p1['price']:
            drop_pct = ((p1['price'] - p2['price']) / p1['price']) * 100
            retrace_pct = ((p3['price'] - p2['price']) / p2['price']) * 100
            retrace_of_drop = (retrace_pct / drop_pct) * 100

            # Czas trwania
            time_drop = (p2['time'] - p1['time']).total_seconds() / 3600  # godziny
            time_retrace = (p3['time'] - p2['time']).total_seconds() / 3600

            # Sprawdź czy poniżej MA (dodatkowe potwierdzenie downtrend)
            bar_p1 = p1['bar']
            below_ma = df.iloc[bar_p1]['close'] < df.iloc[bar_p1]['ma_50'] if not pd.isna(df.iloc[bar_p1]['ma_50']) else False

            zigzags.append({
                'start_time': p1['time'],
                'start_price': p1['price'],
                'low_price': p2['price'],
                'retrace_price': p3['price'],
                'drop_pct': drop_pct,
                'retrace_pct': retrace_pct,
                'retrace_of_drop': retrace_of_drop,
                'time_drop_hours': time_drop,
                'time_retrace_hours': time_retrace,
                'below_ma': below_ma
            })

zigzags_df = pd.DataFrame(zigzags)

print(f"Znaleziono {len(zigzags_df)} wzorów zigzag (HIGH → LOW → lower HIGH)")
print()

# Filtruj tylko te w downtrendzie (poniżej MA)
zigzags_downtrend = zigzags_df[zigzags_df['below_ma'] == True].copy()

print(f"Z tego w potwierdzonym downtrendzie (poniżej MA50): {len(zigzags_downtrend)}")
print()

if len(zigzags_downtrend) > 0:
    print("="*140)
    print("STATYSTYKI ZIGZAG W DOWNTRENDZIE")
    print("="*140)
    print()

    print("SPADKI (HIGH → LOW):")
    print(f"  Średni spadek: {zigzags_downtrend['drop_pct'].mean():.2f}%")
    print(f"  Mediana spadku: {zigzags_downtrend['drop_pct'].median():.2f}%")
    print(f"  Min spadek: {zigzags_downtrend['drop_pct'].min():.2f}%")
    print(f"  Max spadek: {zigzags_downtrend['drop_pct'].max():.2f}%")
    print()

    print("ODBICIA / RETRACES (LOW → lower HIGH):")
    print(f"  Średnie odbicie: {zigzags_downtrend['retrace_pct'].mean():.2f}%")
    print(f"  Mediana odbicia: {zigzags_downtrend['retrace_pct'].median():.2f}%")
    print(f"  Min odbicie: {zigzags_downtrend['retrace_pct'].min():.2f}%")
    print(f"  Max odbicie: {zigzags_downtrend['retrace_pct'].max():.2f}%")
    print()

    print("PROPORCJA ODBICIA DO SPADKU:")
    print(f"  Średnia proporcja: {zigzags_downtrend['retrace_of_drop'].mean():.1f}% (odbicie jako % spadku)")
    print(f"  Mediana proporcji: {zigzags_downtrend['retrace_of_drop'].median():.1f}%")
    print()
    print("  Przykład: jeśli spadek to 10%, to średnie odbicie to {:.1f}% spadku = {:.2f}%".format(
        zigzags_downtrend['retrace_of_drop'].mean(),
        (zigzags_downtrend['retrace_of_drop'].mean() / 100) * zigzags_downtrend['drop_pct'].mean()
    ))
    print()

    print("CZAS TRWANIA:")
    print(f"  Średni czas spadku: {zigzags_downtrend['time_drop_hours'].mean():.1f} godzin")
    print(f"  Średni czas odbicia: {zigzags_downtrend['time_retrace_hours'].mean():.1f} godzin")
    print(f"  Łączny cykl: {(zigzags_downtrend['time_drop_hours'].mean() + zigzags_downtrend['time_retrace_hours'].mean()):.1f} godzin")
    print()

    print("="*140)
    print("ROZKŁAD PROPORCJI ODBICIA")
    print("="*140)
    print()

    # Bins dla rozkładu
    bins = [0, 25, 33, 40, 50, 60, 75, 100, 150]
    labels = ['<25%', '25-33%', '33-40%', '40-50%', '50-60%', '60-75%', '75-100%', '>100%']

    zigzags_downtrend['retrace_bin'] = pd.cut(zigzags_downtrend['retrace_of_drop'], bins=bins, labels=labels)
    dist = zigzags_downtrend['retrace_bin'].value_counts().sort_index()

    print("Proporcja odbicia | Ilość | %")
    print("-" * 50)
    for label, count in dist.items():
        pct = (count / len(zigzags_downtrend)) * 100
        print(f"{label:<17} | {count:>5} | {pct:>5.1f}%")

    print()
    print("="*140)
    print()

    print("PRZYKŁADOWE ZIGZAGI:")
    print("-" * 140)
    print(f"{'Data':<12} | {'Start':<10} | {'Low':<10} | {'Retrace':<10} | {'Spadek':<8} | {'Odbicie':<9} | {'Proporcja':<11}")
    print("-" * 140)

    for idx, row in zigzags_downtrend.head(20).iterrows():
        print(f"{row['start_time'].strftime('%m-%d %H:%M'):<12} | ${row['start_price']:.6f} | ${row['low_price']:.6f} | ${row['retrace_price']:.6f} | {row['drop_pct']:>6.2f}% | {row['retrace_pct']:>7.2f}% | {row['retrace_of_drop']:>9.1f}%")

    print()
    print("="*140)
    print()

    print("💡 REKOMENDACJA DLA STRATEGII:")
    print("-" * 140)

    median_retrace = zigzags_downtrend['retrace_of_drop'].median()
    avg_retrace = zigzags_downtrend['retrace_of_drop'].mean()

    print(f"1. ENTRY POINT: Shortuj gdy odbicie osiągnie {median_retrace:.0f}% poprzedniego spadku (mediana)")
    print(f"   Alternatywnie: {avg_retrace:.0f}% (średnia)")
    print()
    print(f"2. STOP LOSS: Powyżej swing high (szczyt odbicia)")
    print()
    print(f"3. TAKE PROFIT: Oczekuj kolejnego spadku ~{zigzags_downtrend['drop_pct'].median():.1f}% (mediana)")
    print()
    print(f"4. DOWNTREND FILTER: Tylko gdy cena < MA50 LUB lower highs potwierdzone")
    print()
    print("="*140)

else:
    print("Brak wzorów zigzag w downtrendzie do analizy")
