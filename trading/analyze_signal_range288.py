"""
Check: Is range_288 AT SIGNAL TIME different from monthly average?
Maybe December had low average but HIGH range when signals occurred
"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

months = [
    ('Jun 2025', datetime(2025, 6, 1, tzinfo=timezone.utc), datetime(2025, 6, 30, 23, 59, tzinfo=timezone.utc)),
    ('Jul-Aug 2025', datetime(2025, 7, 1, tzinfo=timezone.utc), datetime(2025, 8, 31, 23, 59, tzinfo=timezone.utc)),
    ('Sep 2025', datetime(2025, 9, 16, tzinfo=timezone.utc), datetime(2025, 9, 30, 23, 59, tzinfo=timezone.utc)),
    ('Oct 2025', datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2025, 10, 31, 23, 59, tzinfo=timezone.utc)),
    ('Nov 2025', datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2025, 11, 30, 23, 59, tzinfo=timezone.utc)),
    ('Dec 2025', datetime(2025, 12, 1, tzinfo=timezone.utc), datetime(2025, 12, 15, tzinfo=timezone.utc)),
]

all_results = []

for name, start, end in months:
    print(f'\nProcessing {name}...')

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

    # Calculate indicators
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
    df['atr'] = df['tr'].rolling(14).mean()
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100
    df['range_288'] = ((df['high'].rolling(288).max() - df['low'].rolling(288).min()) / df['low'].rolling(288).min()) * 100

    # Find all RSI signals
    signals = []
    for i in range(300, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]

        if pd.isna(row['rsi']) or pd.isna(prev_row['rsi']):
            continue
        if pd.isna(row['ret_20']) or row['ret_20'] <= 0:
            continue

        # RSI 35 cross (LONG)
        if prev_row['rsi'] < 35 and row['rsi'] >= 35:
            signals.append({
                'month': name,
                'direction': 'LONG',
                'range_288': row['range_288'],
                'ret_20': row['ret_20']
            })
        # RSI 65 cross (SHORT)
        elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
            signals.append({
                'month': name,
                'direction': 'SHORT',
                'range_288': row['range_288'],
                'ret_20': row['ret_20']
            })

    if signals:
        df_sig = pd.DataFrame(signals)
        avg_range_at_signal = df_sig['range_288'].mean()
        avg_range_overall = df['range_288'].mean()

        print(f'  Signals: {len(df_sig)}')
        print(f'  Avg range_288 (overall): {avg_range_overall:.2f}%')
        print(f'  Avg range_288 (at signals): {avg_range_at_signal:.2f}%')
        print(f'  Difference: {avg_range_at_signal - avg_range_overall:+.2f}% ({((avg_range_at_signal / avg_range_overall) - 1) * 100:+.0f}%)')

        all_results.append({
            'month': name,
            'signals': len(df_sig),
            'range_overall': avg_range_overall,
            'range_at_signals': avg_range_at_signal,
            'diff_pct': ((avg_range_at_signal / avg_range_overall) - 1) * 100
        })
    else:
        print(f'  No signals found')

print('\n' + '=' * 80)
print('SUMMARY: Range288 at Signal Time vs Overall')
print('=' * 80)

df_res = pd.DataFrame(all_results)
print(df_res.to_string(index=False))

print('\n' + '=' * 80)
print('KEY INSIGHT:')
print('=' * 80)

good_months = df_res[df_res['month'].isin(['Oct 2025', 'Nov 2025', 'Dec 2025'])]
bad_months = df_res[df_res['month'].isin(['Jun 2025', 'Jul-Aug 2025', 'Sep 2025'])]

if len(good_months) > 0 and len(bad_months) > 0:
    print(f'\nBAD months - avg range_288 at signals: {bad_months["range_at_signals"].mean():.2f}%')
    print(f'GOOD months - avg range_288 at signals: {good_months["range_at_signals"].mean():.2f}%')
    print(f'Difference: {((good_months["range_at_signals"].mean() / bad_months["range_at_signals"].mean()) - 1) * 100:+.0f}%')

    threshold = (bad_months['range_at_signals'].mean() + good_months['range_at_signals'].mean()) / 2
    print(f'\nSuggested threshold: {threshold:.2f}%')

    print('\nMonth classification with signal-time range:')
    for _, row in df_res.iterrows():
        status = '✅ TRADE' if row['range_at_signals'] > threshold else '❌ SKIP'
        print(f"  {row['month']:15s}: {row['range_at_signals']:6.2f}% {status}")

df_res.to_csv('signal_range_288_analysis.csv', index=False)
print(f'\n💾 Saved: signal_range_288_analysis.csv')