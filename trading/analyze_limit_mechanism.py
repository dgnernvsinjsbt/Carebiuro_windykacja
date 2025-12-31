"""
Szczegółowa analiza mechanizmu limit order
Odpowiadamy na pytanie: JAK to filtruje loserów?
"""
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('trading/doge_1h_jun_dec_2025.csv', parse_dates=['timestamp'])

# Parameters
PERIOD = 15
TP_ATR = 4.0
SL_ATR = 4.0
LIMIT_OFFSET_PCT = 0.5
WAIT_BARS = 1

# Calculate indicators
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df['donchian_upper'] = df['high'].rolling(PERIOD).max().shift(1)
df['donchian_lower'] = df['low'].rolling(PERIOD).min().shift(1)

# Find all signals
signals = []
for i in range(PERIOD + 14, len(df) - 50):
    row = df.iloc[i]
    atr = row['atr']
    
    if row['close'] > row['donchian_upper']:
        signals.append({
            'bar': i,
            'direction': 'LONG',
            'signal_price': row['close'],
            'atr': atr,
            'tp_price': row['close'] + TP_ATR * atr,
            'sl_price': row['close'] - SL_ATR * atr
        })
    elif row['close'] < row['donchian_lower']:
        signals.append({
            'bar': i,
            'direction': 'SHORT', 
            'signal_price': row['close'],
            'atr': atr,
            'tp_price': row['close'] - TP_ATR * atr,
            'sl_price': row['close'] + SL_ATR * atr
        })

print(f"Wszystkich sygnałów: {len(signals)}")

# Analizuj każdy sygnał szczegółowo
results = []
for sig in signals:
    i = sig['bar']
    direction = sig['direction']
    signal_price = sig['signal_price']
    atr = sig['atr']
    
    # Cena limitu
    if direction == 'LONG':
        limit_price = signal_price * (1 - LIMIT_OFFSET_PCT / 100)
    else:
        limit_price = signal_price * (1 + LIMIT_OFFSET_PCT / 100)
    
    # Sprawdź czy limit wypełniony w ciągu WAIT_BARS
    filled = False
    fill_bar = None
    for j in range(1, WAIT_BARS + 1):
        if i + j >= len(df):
            break
        candle = df.iloc[i + j]
        if direction == 'LONG' and candle['low'] <= limit_price:
            filled = True
            fill_bar = i + j
            break
        elif direction == 'SHORT' and candle['high'] >= limit_price:
            filled = True
            fill_bar = i + j
            break
    
    # Teraz sprawdź outcome gdybyśmy weszli Z MARKET ORDER na signal_price
    # (żeby porównać z limitem)
    tp_price = sig['tp_price']
    sl_price = sig['sl_price']
    
    market_outcome = None
    for j in range(1, 50):
        if i + j >= len(df):
            break
        candle = df.iloc[i + j]
        
        if direction == 'LONG':
            if candle['low'] <= sl_price:
                market_outcome = 'SL'
                break
            if candle['high'] >= tp_price:
                market_outcome = 'TP'
                break
        else:
            if candle['high'] >= sl_price:
                market_outcome = 'SL'
                break
            if candle['low'] <= tp_price:
                market_outcome = 'TP'
                break
    
    if market_outcome is None:
        market_outcome = 'TIMEOUT'
    
    # Co się dzieje w barze 1 (cena idzie w naszą stronę czy przeciw?)
    bar1 = df.iloc[i + 1] if i + 1 < len(df) else None
    if bar1 is not None:
        if direction == 'LONG':
            # Dla LONG: czy cena spadła (w naszą stronę do limitu)?
            bar1_move = (bar1['low'] - signal_price) / signal_price * 100
            bar1_favorable = bar1['low'] < signal_price  # spadek = korzystny dla limitu LONG
        else:
            bar1_move = (bar1['high'] - signal_price) / signal_price * 100
            bar1_favorable = bar1['high'] > signal_price  # wzrost = korzystny dla limitu SHORT
    else:
        bar1_move = 0
        bar1_favorable = False
    
    results.append({
        'bar': i,
        'direction': direction,
        'signal_price': signal_price,
        'limit_price': limit_price,
        'filled': filled,
        'market_outcome': market_outcome,
        'bar1_move_pct': bar1_move,
        'bar1_favorable': bar1_favorable
    })

df_results = pd.DataFrame(results)

# Podsumowanie
print("\n" + "="*70)
print("PODSUMOWANIE MECHANIZMU LIMIT ORDER")
print("="*70)

# Ile wypełniono vs pominięto
filled = df_results[df_results['filled'] == True]
missed = df_results[df_results['filled'] == False]

print(f"\nWypełnione (weszliśmy): {len(filled)} sygnałów")
print(f"Pominięte (anulowane): {len(missed)} sygnałów")

# Rozkład outcomes w każdej grupie
print("\n--- WYPEŁNIONE (weszliśmy) ---")
filled_outcomes = filled['market_outcome'].value_counts()
print(f"  TP: {filled_outcomes.get('TP', 0)}")
print(f"  SL: {filled_outcomes.get('SL', 0)}")
print(f"  TIMEOUT: {filled_outcomes.get('TIMEOUT', 0)}")
filled_tp = filled_outcomes.get('TP', 0)
filled_sl = filled_outcomes.get('SL', 0)
if filled_tp + filled_sl > 0:
    print(f"  Win Rate: {filled_tp / (filled_tp + filled_sl) * 100:.1f}%")

print("\n--- POMINIĘTE (anulowane) ---")
missed_outcomes = missed['market_outcome'].value_counts()
print(f"  TP (stracone okazje): {missed_outcomes.get('TP', 0)}")
print(f"  SL (uniknięte straty): {missed_outcomes.get('SL', 0)}")
print(f"  TIMEOUT: {missed_outcomes.get('TIMEOUT', 0)}")
missed_tp = missed_outcomes.get('TP', 0)
missed_sl = missed_outcomes.get('SL', 0)
if missed_tp + missed_sl > 0:
    print(f"  'Win Rate' (gdybyśmy weszli): {missed_tp / (missed_tp + missed_sl) * 100:.1f}%")

# KLUCZOWA ANALIZA: dlaczego pominięte mają inny rozkład?
print("\n" + "="*70)
print("KLUCZOWA ANALIZA: CO CHARAKTERYZUJE POMINIĘTE SYGNAŁY?")
print("="*70)

# Pominięte TP vs pominięte SL - czy jest różnica w bar1 move?
missed_tp_df = missed[missed['market_outcome'] == 'TP']
missed_sl_df = missed[missed['market_outcome'] == 'SL']

print(f"\nPominięte TP ({len(missed_tp_df)} szt.):")
print(f"  Średni ruch bar1: {missed_tp_df['bar1_move_pct'].mean():.2f}%")
print(f"  Ile miało korzystny ruch (w stronę limitu): {missed_tp_df['bar1_favorable'].sum()}")

print(f"\nPominięte SL ({len(missed_sl_df)} szt.):")
print(f"  Średni ruch bar1: {missed_sl_df['bar1_move_pct'].mean():.2f}%")
print(f"  Ile miało korzystny ruch (w stronę limitu): {missed_sl_df['bar1_favorable'].sum()}")

# Wypełnione TP vs SL
filled_tp_df = filled[filled['market_outcome'] == 'TP']
filled_sl_df = filled[filled['market_outcome'] == 'SL']

print(f"\nWypełnione TP ({len(filled_tp_df)} szt.):")
print(f"  Średni ruch bar1: {filled_tp_df['bar1_move_pct'].mean():.2f}%")

print(f"\nWypełnione SL ({len(filled_sl_df)} szt.):")
print(f"  Średni ruch bar1: {filled_sl_df['bar1_move_pct'].mean():.2f}%")

# NET EFFECT
print("\n" + "="*70)
print("NET EFFECT: CZY WARTO UŻYWAĆ LIMIT?")
print("="*70)

# Zakładając 3% risk, 4:4 TP:SL ratio
# Każdy TP = +TP_ATR/SL_ATR * risk = 3%
# Każdy SL = -3%
TP_VALUE = TP_ATR / SL_ATR * 3  # +3%
SL_VALUE = -3  # -3%

# Z market order (wszystkie sygnały)
all_tp = df_results['market_outcome'].value_counts().get('TP', 0)
all_sl = df_results['market_outcome'].value_counts().get('SL', 0)
market_pnl = all_tp * TP_VALUE + all_sl * SL_VALUE

# Z limit order (tylko filled, ale z lepszą ceną!)
# Tu trzeba by liczyć faktyczny PnL z lepszą ceną, ale dla prostoty:
# Pomijamy missed, liczymy PnL z filled
limit_pnl = filled_tp * TP_VALUE + filled_sl * SL_VALUE

# Uniknięte straty
avoided_losses = missed_sl * abs(SL_VALUE)
lost_gains = missed_tp * TP_VALUE

print(f"\nMarket order (wszystkie {all_tp + all_sl} trejdy):")
print(f"  {all_tp} TP × {TP_VALUE:.1f}% = +{all_tp * TP_VALUE:.1f}%")
print(f"  {all_sl} SL × {SL_VALUE:.1f}% = {all_sl * SL_VALUE:.1f}%")
print(f"  NET: {market_pnl:.1f}%")

print(f"\nLimit order ({filled_tp + filled_sl} trejdów):")
print(f"  {filled_tp} TP × {TP_VALUE:.1f}% = +{filled_tp * TP_VALUE:.1f}%")
print(f"  {filled_sl} SL × {SL_VALUE:.1f}% = {filled_sl * SL_VALUE:.1f}%")
print(f"  NET: {limit_pnl:.1f}%")

print(f"\n  Uniknięte straty ({missed_sl} SL): +{avoided_losses:.1f}%")
print(f"  Stracone okazje ({missed_tp} TP): -{lost_gains:.1f}%")
print(f"  Różnica: {avoided_losses - lost_gains:.1f}%")

# WNIOSEK
print("\n" + "="*70)
print("WNIOSEK")
print("="*70)
if avoided_losses > lost_gains:
    print("✅ Limit order OPŁACA SIĘ: unikamy więcej strat niż tracimy okazji")
else:
    print("❌ Limit order NIE opłaca się: tracimy więcej okazji niż unikamy strat")
    
print(f"\nKluczowy insight: Pominięte sygnały mają win rate {missed_tp/(missed_tp+missed_sl)*100:.1f}%")
print(f"Wypełnione sygnały mają win rate {filled_tp/(filled_tp+filled_sl)*100:.1f}%")
print("\n→ Limit order filtruje sygnały o NIŻSZYM win rate!")

