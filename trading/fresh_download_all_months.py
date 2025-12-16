"""
FRESH DOWNLOAD - każdy miesiąc osobno, lipiec-grudzień 2025
Czyste dane, czyste backtesty, zero assumptions
"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

# Lipiec do dzisiaj (15 grudnia 2025)
months = [
    ('Jul 2025', datetime(2025, 7, 1, tzinfo=timezone.utc), datetime(2025, 7, 31, 23, 59, tzinfo=timezone.utc)),
    ('Aug 2025', datetime(2025, 8, 1, tzinfo=timezone.utc), datetime(2025, 8, 31, 23, 59, tzinfo=timezone.utc)),
    ('Sep 2025', datetime(2025, 9, 1, tzinfo=timezone.utc), datetime(2025, 9, 30, 23, 59, tzinfo=timezone.utc)),
    ('Oct 2025', datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2025, 10, 31, 23, 59, tzinfo=timezone.utc)),
    ('Nov 2025', datetime(2025, 11, 1, tzinfo=timezone.utc), datetime(2025, 11, 30, 23, 59, tzinfo=timezone.utc)),
    ('Dec 2025', datetime(2025, 12, 1, tzinfo=timezone.utc), datetime(2025, 12, 15, 23, 59, tzinfo=timezone.utc)),
]

def backtest_clean(df, sl_mult, tp_mult):
    """Clean backtest - RSI 35/65 + ret_20 > 0"""
    trades, equity, position = [], 100.0, None

    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        # Manage position
        if position:
            if position['direction'] == 'LONG':
                if row['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'SL', 'direction': 'LONG'})
                    position = None
                    continue
                elif row['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'TP', 'direction': 'LONG'})
                    position = None
                    continue
            else:  # SHORT
                if row['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'SL', 'direction': 'SHORT'})
                    position = None
                    continue
                elif row['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': pnl_pct, 'exit': 'TP', 'direction': 'SHORT'})
                    position = None
                    continue

        # New signals
        if not position and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0:
                continue
            if not pd.isna(prev_row['rsi']):
                # LONG: RSI crosses above 35
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    entry = row['close']
                    sl = entry - (row['atr'] * sl_mult)
                    tp = entry + (row['atr'] * tp_mult)
                    sl_dist = abs((entry - sl) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {'direction': 'LONG', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}
                # SHORT: RSI crosses below 65
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

    # Calculate proper equity curve
    eq = [100.0]
    cum_eq = 100.0
    for pnl in df_t['pnl_pct']:
        cum_eq += (cum_eq * 0.12) * (pnl / 100) - (cum_eq * 0.12) * 0.001
        eq.append(cum_eq)

    eq_s = pd.Series(eq)
    max_dd = ((eq_s - eq_s.expanding().max()) / eq_s.expanding().max() * 100).min()
    win_rate = (df_t['pnl_pct'] > 0).sum() / len(df_t) * 100
    tp_rate = (df_t['exit'] == 'TP').sum() / len(df_t) * 100

    longs = df_t[df_t['direction'] == 'LONG']
    shorts = df_t[df_t['direction'] == 'SHORT']

    return {
        'trades': len(df_t),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'return': ret,
        'max_dd': max_dd,
        'return_dd': ret / abs(max_dd) if max_dd != 0 else 0,
        'final_equity': equity,
        'longs': len(longs),
        'shorts': len(shorts),
        'long_wins': (longs['pnl_pct'] > 0).sum() if len(longs) > 0 else 0,
        'short_wins': (shorts['pnl_pct'] > 0).sum() if len(shorts) > 0 else 0
    }

print('=' * 100)
print('FRESH DOWNLOAD - MELANIA-USDT 15M - LIPIEC DO GRUDNIA 2025')
print('=' * 100)

all_results = []

for name, start, end in months:
    print(f'\n{"="*100}')
    print(f'Downloading {name}...')
    print(f'{"="*100}')

    start_ts = int(start.timestamp() * 1000)
    end_ts = int(end.timestamp() * 1000)

    all_candles = []
    current_ts = start_ts

    while current_ts < end_ts:
        try:
            candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            current_ts = candles[-1][0] + (15 * 60 * 1000)
            print(f'  Downloaded {len(all_candles)} candles...', end='\r')
            time.sleep(0.5)
        except Exception as e:
            print(f'  Error: {e}')
            time.sleep(2)
            continue

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= start.replace(tzinfo=None)) & (df['timestamp'] <= end.replace(tzinfo=None))].sort_values('timestamp').reset_index(drop=True)

    print(f'\n  Total bars: {len(df)} (from {df["timestamp"].min()} to {df["timestamp"].max()})')

    # Calculate indicators (Wilder's RSI)
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

    # Backtest both configs
    current = backtest_clean(df, sl_mult=2.0, tp_mult=3.0)
    wide_sl = backtest_clean(df, sl_mult=3.0, tp_mult=1.0)

    print(f'\n  CURRENT (SL 2.0x / TP 3.0x):')
    if current:
        print(f'    Trades: {current["trades"]} ({current["longs"]}L/{current["shorts"]}S)')
        print(f'    Win rate: {current["win_rate"]:.1f}%')
        print(f'    Return: {current["return"]:+.1f}%')
        print(f'    Max DD: {current["max_dd"]:.2f}%')
        print(f'    R/DD: {current["return_dd"]:.2f}x')
    else:
        print(f'    No trades')

    print(f'\n  WIDE SL (SL 3.0x / TP 1.0x):')
    if wide_sl:
        print(f'    Trades: {wide_sl["trades"]} ({wide_sl["longs"]}L/{wide_sl["shorts"]}S)')
        print(f'    Win rate: {wide_sl["win_rate"]:.1f}%')
        print(f'    Return: {wide_sl["return"]:+.1f}%')
        print(f'    Max DD: {wide_sl["max_dd"]:.2f}%')
        print(f'    R/DD: {wide_sl["return_dd"]:.2f}x')
    else:
        print(f'    No trades')

    all_results.append({
        'month': name,
        'bars': len(df),
        'current_trades': current['trades'] if current else 0,
        'current_win': current['win_rate'] if current else 0,
        'current_return': current['return'] if current else 0,
        'current_dd': current['max_dd'] if current else 0,
        'current_rdd': current['return_dd'] if current else 0,
        'wide_trades': wide_sl['trades'] if wide_sl else 0,
        'wide_win': wide_sl['win_rate'] if wide_sl else 0,
        'wide_return': wide_sl['return'] if wide_sl else 0,
        'wide_dd': wide_sl['max_dd'] if wide_sl else 0,
        'wide_rdd': wide_sl['return_dd'] if wide_sl else 0,
    })

print('\n' + '=' * 100)
print('SUMMARY - ALL MONTHS')
print('=' * 100)

df_res = pd.DataFrame(all_results)

print(f'\n{"Month":<12} {"Bars":<6} │ Current (2.0/3.0)                          │ Wide SL (3.0/1.0)')
print(f'{"":12} {"":6} │ {"Trades":<7} {"Win%":<7} {"Return":<10} {"R/DD":<8} │ {"Trades":<7} {"Win%":<7} {"Return":<10} {"R/DD":<8}')
print('-' * 100)

for idx, row in df_res.iterrows():
    print(f'{row["month"]:<12} {row["bars"]:<6} │ {row["current_trades"]:<7} {row["current_win"]:<6.1f}% {row["current_return"]:<+9.1f}% {row["current_rdd"]:<7.2f}x │ {row["wide_trades"]:<7} {row["wide_win"]:<6.1f}% {row["wide_return"]:<+9.1f}% {row["wide_rdd"]:<7.2f}x')

print('\n' + '=' * 100)
print('TOTALS:')
print('=' * 100)

total_current_ret = df_res['current_return'].sum()
total_wide_ret = df_res['wide_return'].sum()

print(f'\nCURRENT (SL 2.0x / TP 3.0x):')
print(f'  Total trades: {df_res["current_trades"].sum()}')
print(f'  Avg win rate: {df_res["current_win"].mean():.1f}%')
print(f'  Total return: {total_current_ret:+.1f}%')
print(f'  Avg R/DD: {df_res["current_rdd"].mean():.2f}x')

print(f'\nWIDE SL (SL 3.0x / TP 1.0x):')
print(f'  Total trades: {df_res["wide_trades"].sum()}')
print(f'  Avg win rate: {df_res["wide_win"].mean():.1f}%')
print(f'  Total return: {total_wide_ret:+.1f}%')
print(f'  Avg R/DD: {df_res["wide_rdd"].mean():.2f}x')

print(f'\nDIFFERENCE:')
print(f'  Return: {total_current_ret:+.1f}% vs {total_wide_ret:+.1f}% ({total_current_ret - total_wide_ret:+.1f}% difference)')

df_res.to_csv('fresh_monthly_results.csv', index=False)
print(f'\n💾 Saved: fresh_monthly_results.csv')
