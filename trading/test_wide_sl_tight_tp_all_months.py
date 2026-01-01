"""
Test SL 3.0x / TP 1.0x on ALL months
This worked amazingly on Jul-Aug - check if it's universal
"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

months = [
    ('Jun 2025', datetime(2025, 6, 1, tzinfo=timezone.utc), datetime(2025, 6, 30, 23, 59, tzinfo=timezone.utc), 'BAD'),
    ('Jul-Aug 2025', datetime(2025, 7, 1, tzinfo=timezone.utc), datetime(2025, 8, 31, 23, 59, tzinfo=timezone.utc), 'BAD'),
    ('Sep 2025', datetime(2025, 9, 16, tzinfo=timezone.utc), datetime(2025, 9, 30, 23, 59, tzinfo=timezone.utc), 'BAD'),
    ('Oct 2025', datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2025, 10, 31, 23, 59, tzinfo=timezone.utc), 'GOOD'),
    ('Nov 2025', datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2025, 11, 30, 23, 59, tzinfo=timezone.utc), 'GOOD'),
    ('Dec 2025', datetime(2025, 12, 1, tzinfo=timezone.utc), datetime(2025, 12, 15, tzinfo=timezone.utc), 'GOOD'),
]

def backtest_params(df, sl_mult, tp_mult):
    """Backtest with specific SL/TP params"""
    trades, equity, position = [], 100.0, None

    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        if position:
            bar = row
            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'SL'})
                    position = None
                    continue
                elif bar['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'TP'})
                    position = None
                    continue
            else:
                if bar['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'SL'})
                    position = None
                    continue
                elif bar['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'TP'})
                    position = None
                    continue

        if not position and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0:
                continue
            if not pd.isna(prev_row['rsi']):
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    entry = row['close']
                    sl = entry - (row['atr'] * sl_mult)
                    tp = entry + (row['atr'] * tp_mult)
                    sl_dist = abs((entry - sl) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {'direction': 'LONG', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}
                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    entry = row['close']
                    sl = entry + (row['atr'] * sl_mult)
                    tp = entry - (row['atr'] * tp_mult)
                    sl_dist = abs((sl - entry) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {'direction': 'SHORT', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}

    if not trades:
        return None

    df_t = pd.DataFrame(trades)
    ret = ((equity - 100) / 100) * 100
    eq = [100.0]
    cum_eq = 100.0
    for pnl in df_t['pnl_pct']:
        cum_eq += (cum_eq * 0.12) * (pnl / 100) - (cum_eq * 0.12) * 0.001
        eq.append(cum_eq)
    eq_s = pd.Series(eq)
    max_dd = ((eq_s - eq_s.expanding().max()) / eq_s.expanding().max() * 100).min()
    win_rate = (df_t['pnl_pct'] > 0).sum() / len(df_t) * 100
    tp_rate = (df_t['exit'] == 'TP').sum() / len(df_t) * 100

    return {'trades': len(df_t), 'win_rate': win_rate, 'tp_rate': tp_rate, 'return': ret, 'max_dd': max_dd, 'return_dd': ret / abs(max_dd) if max_dd != 0 else 0}

print('=' * 100)
print('TESTING SL 3.0x / TP 1.0x ON ALL MONTHS')
print('vs CURRENT SL 2.0x / TP 3.0x')
print('=' * 100)

results = []

for name, start, end, quality in months:
    print(f'\n{name} ({quality}):')

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

    # Test both configs
    current = backtest_params(df, sl_mult=2.0, tp_mult=3.0)
    wide_sl = backtest_params(df, sl_mult=3.0, tp_mult=1.0)

    if current:
        print(f'  CURRENT (2.0/3.0):  {current["trades"]:3d} trades, {current["win_rate"]:5.1f}% win, {current["tp_rate"]:5.1f}% TP, {current["return"]:+8.1f}%, {current["return_dd"]:6.2f}x R/DD')
    else:
        print(f'  CURRENT (2.0/3.0):  No trades')

    if wide_sl:
        print(f'  WIDE SL (3.0/1.0):  {wide_sl["trades"]:3d} trades, {wide_sl["win_rate"]:5.1f}% win, {wide_sl["tp_rate"]:5.1f}% TP, {wide_sl["return"]:+8.1f}%, {wide_sl["return_dd"]:6.2f}x R/DD')
        if current:
            improvement = wide_sl['return'] - current['return']
            print(f'  CHANGE:             {improvement:+.1f}% return')
    else:
        print(f'  WIDE SL (3.0/1.0):  No trades')

    results.append({
        'month': name,
        'quality': quality,
        'current_return': current['return'] if current else 0,
        'wide_sl_return': wide_sl['return'] if wide_sl else 0,
        'current_rdd': current['return_dd'] if current else 0,
        'wide_sl_rdd': wide_sl['return_dd'] if wide_sl else 0,
        'current_wr': current['win_rate'] if current else 0,
        'wide_sl_wr': wide_sl['win_rate'] if wide_sl else 0
    })

print('\n' + '=' * 100)
print('SUMMARY:')
print('=' * 100)

df_res = pd.DataFrame(results)
print(f'\n{"Month":<15} {"Quality":<6} {"Current (2/3)":<14} {"Wide SL (3/1)":<14} {"Change":<12} {"Status":<15}')
print('-' * 100)
for idx, row in df_res.iterrows():
    change = row['wide_sl_return'] - row['current_return']
    if change > 20:
        status = '✅ LEPSZE'
    elif change < -20:
        status = '❌ GORSZE'
    else:
        status = '➡️  PODOBNE'

    print(f'{row["month"]:<15} {row["quality"]:<6} {row["current_return"]:>+13.1f}% {row["wide_sl_return"]:>+13.1f}% {change:>+11.1f}% {status:<15}')

bad = df_res[df_res['quality'] == 'BAD']
good = df_res[df_res['quality'] == 'GOOD']

bad_current = bad['current_return'].sum()
bad_wide = bad['wide_sl_return'].sum()
good_current = good['current_return'].sum()
good_wide = good['wide_sl_return'].sum()

print('\n' + '=' * 100)
print('AGGREGATE:')
print('=' * 100)
print(f'\n📊 ZŁE MIESIĄCE (Jun + Jul-Aug + Sep):')
print(f'   Current (2/3):  {bad_current:>+8.1f}%')
print(f'   Wide SL (3/1):  {bad_wide:>+8.1f}%')
print(f'   Change:         {bad_wide - bad_current:>+8.1f}%')

print(f'\n📊 DOBRE MIESIĄCE (Oct + Nov + Dec):')
print(f'   Current (2/3):  {good_current:>+8.1f}%')
print(f'   Wide SL (3/1):  {good_wide:>+8.1f}%')
print(f'   Change:         {good_wide - good_current:>+8.1f}%')

total_current = bad_current + good_current
total_wide = bad_wide + good_wide

print(f'\n📊 TOTAL (wszystkie 6 miesięcy):')
print(f'   Current (2/3):  {total_current:>+8.1f}%')
print(f'   Wide SL (3/1):  {total_wide:>+8.1f}%')
print(f'   Change:         {total_wide - total_current:>+8.1f}%')

if total_wide > total_current:
    print(f'\n✅ WIDE SL WINS! (+{total_wide - total_current:.1f}% better)')
else:
    print(f'\n❌ CURRENT WINS! ({total_current - total_wide:.1f}% better)')

df_res.to_csv('wide_sl_tight_tp_comparison.csv', index=False)
print(f'\n💾 Saved: wide_sl_tight_tp_comparison.csv')
