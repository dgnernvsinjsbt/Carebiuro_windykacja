"""
Test 1% LIMIT OFFSET on ALL months
Check if it fixes bad months without breaking good ones
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

def backtest_strategy(df, use_offset=False, offset_pct=1.0, wait_bars=20, sl_mult=2.0, tp_mult=3.0):
    """Backtest with optional LIMIT offset"""
    trades, equity, position = [], 100.0, None
    pending_limit = None

    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        # Check pending limit orders (if using offset)
        if use_offset and pending_limit is not None:
            bars_waited = i - pending_limit['signal_idx']
            if bars_waited > wait_bars:
                pending_limit = None
                continue

            filled = False
            if pending_limit['direction'] == 'LONG':
                if row['low'] <= pending_limit['limit_price']:
                    filled = True
                    fill_price = pending_limit['limit_price']
            else:
                if row['high'] >= pending_limit['limit_price']:
                    filled = True
                    fill_price = pending_limit['limit_price']

            if filled:
                sl_price = fill_price - (pending_limit['atr'] * sl_mult) if pending_limit['direction'] == 'LONG' else fill_price + (pending_limit['atr'] * sl_mult)
                tp_price = fill_price + (pending_limit['atr'] * tp_mult) if pending_limit['direction'] == 'LONG' else fill_price - (pending_limit['atr'] * tp_mult)
                sl_dist = abs((fill_price - sl_price) / fill_price) * 100
                size = (equity * 0.12) / (sl_dist / 100)
                position = {'direction': pending_limit['direction'], 'entry': fill_price, 'sl_price': sl_price, 'tp_price': tp_price, 'size': size}
                pending_limit = None

        # Manage position
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

        # New signals
        if not position and (not use_offset or pending_limit is None) and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0:
                continue
            if not pd.isna(prev_row['rsi']):
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    if use_offset:
                        signal_price = row['close']
                        limit_price = signal_price * (1 - offset_pct / 100)
                        pending_limit = {'direction': 'LONG', 'signal_price': signal_price, 'limit_price': limit_price, 'atr': row['atr'], 'signal_idx': i}
                    else:
                        entry = row['close']
                        sl = entry - (row['atr'] * sl_mult)
                        tp = entry + (row['atr'] * tp_mult)
                        sl_dist = abs((entry - sl) / entry) * 100
                        size = (equity * 0.12) / (sl_dist / 100)
                        position = {'direction': 'LONG', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}
                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    if use_offset:
                        signal_price = row['close']
                        limit_price = signal_price * (1 + offset_pct / 100)
                        pending_limit = {'direction': 'SHORT', 'signal_price': signal_price, 'limit_price': limit_price, 'atr': row['atr'], 'signal_idx': i}
                    else:
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

print('=' * 120)
print('TESTING 1% LIMIT OFFSET ON ALL MONTHS')
print('=' * 120)

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

    # Test both strategies
    market = backtest_strategy(df, use_offset=False)
    limit = backtest_strategy(df, use_offset=True, offset_pct=1.0, wait_bars=20)

    if market:
        print(f'  MARKET ORDER:  {market["trades"]:3d} trades, {market["win_rate"]:5.1f}% win, {market["return"]:+8.1f}%, {market["return_dd"]:6.2f}x R/DD')
    else:
        print(f'  MARKET ORDER:  No trades')

    if limit:
        print(f'  LIMIT 1% OFF:  {limit["trades"]:3d} trades, {limit["win_rate"]:5.1f}% win, {limit["return"]:+8.1f}%, {limit["return_dd"]:6.2f}x R/DD')
        improvement = ((limit['return'] - market['return']) / abs(market['return']) * 100) if market and market['return'] != 0 else 0
        print(f'  IMPROVEMENT:   {improvement:+.0f}% return change')
    else:
        print(f'  LIMIT 1% OFF:  No trades')

    results.append({'month': name, 'quality': quality, 'market_return': market['return'] if market else 0, 'limit_return': limit['return'] if limit else 0, 'market_rdd': market['return_dd'] if market else 0, 'limit_rdd': limit['return_dd'] if limit else 0})

print('\n' + '=' * 120)
print('SUMMARY:')
print('=' * 120)

df_res = pd.DataFrame(results)
print(f'\n{"Month":<15} {"Quality":<6} {"Market Return":<14} {"Limit Return":<14} {"Change":<10}')
print('-' * 120)
for idx, row in df_res.iterrows():
    change = row['limit_return'] - row['market_return']
    status = '✅ BETTER' if change > 10 else ('⚠️  WORSE' if change < -10 else '➡️  SIMILAR')
    print(f'{row["month"]:<15} {row["quality"]:<6} {row["market_return"]:>+13.1f}% {row["limit_return"]:>+13.1f}% {change:>+9.1f}%  {status}')

bad_market = df_res[df_res['quality'] == 'BAD']['market_return'].sum()
bad_limit = df_res[df_res['quality'] == 'BAD']['limit_return'].sum()
good_market = df_res[df_res['quality'] == 'GOOD']['market_return'].sum()
good_limit = df_res[df_res['quality'] == 'GOOD']['limit_return'].sum()

print('\n' + '=' * 120)
print('AGGREGATE:')
print('=' * 120)
print(f'\nBAD MONTHS (Jun + Jul-Aug + Sep):')
print(f'  Market order: {bad_market:+.1f}%')
print(f'  Limit 1% offset: {bad_limit:+.1f}%')
print(f'  Change: {bad_limit - bad_market:+.1f}%')

print(f'\nGOOD MONTHS (Oct + Nov + Dec):')
print(f'  Market order: {good_market:+.1f}%')
print(f'  Limit 1% offset: {good_limit:+.1f}%')
print(f'  Change: {good_limit - good_market:+.1f}%')

df_res.to_csv('all_months_offset_comparison.csv', index=False)
print(f'\n💾 Saved: all_months_offset_comparison.csv')
