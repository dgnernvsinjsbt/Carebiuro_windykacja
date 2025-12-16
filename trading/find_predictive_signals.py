"""
Znajdź MIERZALNE sygnały które odróżniają dobre miesiące od złych
Sygnały które możemy trackować w czasie rzeczywistym
"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

months = [
    ('Jun 2025 BAD', datetime(2025, 6, 1, tzinfo=timezone.utc), datetime(2025, 6, 30, 23, 59, tzinfo=timezone.utc)),
    ('Jul-Aug 2025 BAD', datetime(2025, 7, 1, tzinfo=timezone.utc), datetime(2025, 8, 31, 23, 59, tzinfo=timezone.utc)),
    ('Sep 2025 BAD', datetime(2025, 9, 16, tzinfo=timezone.utc), datetime(2025, 9, 30, 23, 59, tzinfo=timezone.utc)),
    ('Oct 2025 GOOD', datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2025, 10, 31, 23, 59, tzinfo=timezone.utc)),
    ('Nov 2025 GOOD', datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2025, 11, 30, 23, 59, tzinfo=timezone.utc)),
    ('Dec 2025 GOOD', datetime(2025, 12, 1, tzinfo=timezone.utc), datetime(2025, 12, 15, tzinfo=timezone.utc)),
]

print('=' * 80)
print('SZUKANIE PREDYKTYWNYCH SYGNAŁÓW')
print('Co możemy mierzyć w czasie rzeczywistym?')
print('=' * 80)

results = []

for name, start, end in months:
    print(f'\nPobieranie {name}...')
    
    start_ts = int(start.timestamp() * 1000)
    end_ts = int(end.timestamp() * 1000)
    
    all_candles = []
    current_ts = start_ts
    
    while current_ts < end_ts:
        try:
            candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
            if not candles: break
            all_candles.extend(candles)
            current_ts = candles[-1][0] + (15 * 60 * 1000)
            time.sleep(0.5)
        except: 
            time.sleep(2)
            continue
    
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= start.replace(tzinfo=None)) & (df['timestamp'] <= end.replace(tzinfo=None))].sort_values('timestamp').reset_index(drop=True)
    
    # Wskaźniki
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = (df['atr'] / df['close']) * 100
    
    # Zmienność
    df['volatility_96'] = df['close'].rolling(96).std() / df['close'].rolling(96).mean() * 100
    df['volatility_288'] = df['close'].rolling(288).std() / df['close'].rolling(288).mean() * 100
    
    # Momentum
    df['ret_96'] = (df['close'] / df['close'].shift(96) - 1) * 100
    df['ret_288'] = (df['close'] / df['close'].shift(288) - 1) * 100
    
    # Range
    df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100
    df['range_288'] = ((df['high'].rolling(288).max() - df['low'].rolling(288).min()) / df['low'].rolling(288).min()) * 100
    
    # Volume
    df['volume_ma_96'] = df['volume'].rolling(96).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma_96']
    df['volume_trend'] = df['volume_ma_96'] / df['volume'].rolling(288).mean()
    
    # Trend strength
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_96'] = df['close'].ewm(span=96, adjust=False).mean()
    df['trend_strength'] = abs((df['ema_20'] - df['ema_96']) / df['ema_96']) * 100
    
    # Price action quality
    df['bullish_bars'] = (df['close'] > df['open']).rolling(96).sum() / 96 * 100
    df['big_moves'] = (abs(df['close'] - df['open']) / df['open'] > 0.01).rolling(96).sum()
    
    # Directional consistency
    df['higher_highs'] = (df['high'] > df['high'].shift(1)).rolling(96).sum()
    df['lower_lows'] = (df['low'] < df['low'].shift(1)).rolling(96).sum()
    
    result = {
        'month': name,
        'status': 'GOOD' if 'GOOD' in name else 'BAD',
        'avg_atr_pct': df['atr_pct'].mean(),
        'avg_volatility_96': df['volatility_96'].mean(),
        'avg_volatility_288': df['volatility_288'].mean(),
        'avg_ret_96': df['ret_96'].mean(),
        'avg_ret_288': df['ret_288'].mean(),
        'avg_range_96': df['range_96'].mean(),
        'avg_range_288': df['range_288'].mean(),
        'avg_volume_ratio': df['volume_ratio'].mean(),
        'avg_volume_trend': df['volume_trend'].mean(),
        'avg_trend_strength': df['trend_strength'].mean(),
        'avg_bullish_bars': df['bullish_bars'].mean(),
        'avg_big_moves': df['big_moves'].mean(),
        'avg_higher_highs': df['higher_highs'].mean(),
        'avg_lower_lows': df['lower_lows'].mean(),
    }
    
    results.append(result)
    print(f'  ✓ {len(df)} bars')

df_results = pd.DataFrame(results)

# Porównaj GOOD vs BAD
good = df_results[df_results['status'] == 'GOOD']
bad = df_results[df_results['status'] == 'BAD']

print('\n' + '=' * 80)
print('GOOD vs BAD MIESIĄCE - PORÓWNANIE:')
print('=' * 80)

metrics = [col for col in df_results.columns if col not in ['month', 'status']]

print(f'\n{"Metryka":<25} | {"BAD avg":<10} | {"GOOD avg":<10} | {"Różnica":<10} | Rating')
print('-' * 80)

predictive = []

for metric in metrics:
    bad_avg = bad[metric].mean()
    good_avg = good[metric].mean()
    diff_pct = ((good_avg - bad_avg) / abs(bad_avg) * 100) if bad_avg != 0 else 0
    
    rating = ''
    if abs(diff_pct) > 50:
        rating = '⭐⭐⭐ SILNY'
        predictive.append((metric, abs(diff_pct), good_avg, bad_avg))
    elif abs(diff_pct) > 30:
        rating = '⭐⭐ DOBRY'
        predictive.append((metric, abs(diff_pct), good_avg, bad_avg))
    elif abs(diff_pct) > 15:
        rating = '⭐ OK'
    else:
        rating = '❌ SŁABY'
    
    print(f'{metric:<25} | {bad_avg:>9.2f} | {good_avg:>9.2f} | {diff_pct:>+9.1f}% | {rating}')

# Top sygnały
predictive.sort(key=lambda x: x[1], reverse=True)

print('\n' + '=' * 80)
print('🎯 TOP PREDYKTYWNE SYGNAŁY (>30% różnicy):')
print('=' * 80)

for metric, diff_pct, good_val, bad_val in predictive[:5]:
    direction = 'wyższe' if good_val > bad_val else 'niższe'
    threshold = (good_val + bad_val) / 2
    
    print(f'\n{metric}:')
    print(f'  BAD miesiące: {bad_val:.2f}')
    print(f'  GOOD miesiące: {good_val:.2f}')
    print(f'  Różnica: {diff_pct:.1f}%')
    print(f'  📊 Sygnał: Traduj gdy {metric} {direction} niż {threshold:.2f}')

print('\n' + '=' * 80)
print('💡 REKOMENDACJA:')
print('=' * 80)

if len(predictive) > 0:
    top_metric, top_diff, good_val, bad_val = predictive[0]
    threshold = (good_val + bad_val) / 2
    operator = '>' if good_val > bad_val else '<'
    
    print(f'\nNajsilniejszy sygnał: {top_metric} ({top_diff:.0f}% różnicy)')
    print(f'')
    print(f'🎯 FILTR REŻIMU:')
    print(f'   Traduj tylko gdy: {top_metric} {operator} {threshold:.2f}')
    print(f'')
    print(f'Ten sygnał możemy mierzyć w CZASIE RZECZYWISTYM i włączać/wyłączać trading.')
else:
    print('\n⚠️  Brak silnych predyktorów - wszystkie miesiące są podobne pod względem metryki')

df_results.to_csv('monthly_regime_signals.csv', index=False)
print(f'\n💾 Zapisano: monthly_regime_signals.csv')
