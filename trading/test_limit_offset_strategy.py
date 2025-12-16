"""
Test LIMIT ORDER OFFSET strategy on Jul-Aug
Enter SHORT ABOVE signal price, LONG BELOW signal price
This gives better entry + filters weak signals
"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

start = datetime(2025, 7, 1, tzinfo=timezone.utc)
end = datetime(2025, 8, 31, 23, 59, tzinfo=timezone.utc)

print('Downloading Jul-Aug data...')

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

print(f'Downloaded {len(df)} bars')

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

def backtest_limit_offset(df, offset_pct, wait_bars, sl_mult=2.0, tp_mult=3.0):
    """
    Backtest with LIMIT ORDER offset
    SHORT: place limit ABOVE signal price (wait for more upside)
    LONG: place limit BELOW signal price (wait for more downside)
    """
    trades, equity, position = [], 100.0, None
    pending_limit = None

    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        # Check pending limit orders
        if pending_limit is not None:
            bars_waited = i - pending_limit['signal_idx']

            # Cancel if waited too long
            if bars_waited > wait_bars:
                pending_limit = None
                continue

            # Check if limit filled
            filled = False
            if pending_limit['direction'] == 'LONG':
                if row['low'] <= pending_limit['limit_price']:
                    filled = True
                    fill_price = pending_limit['limit_price']
            else:  # SHORT
                if row['high'] >= pending_limit['limit_price']:
                    filled = True
                    fill_price = pending_limit['limit_price']

            if filled:
                # Convert pending to active position
                sl_price = fill_price - (pending_limit['atr'] * sl_mult) if pending_limit['direction'] == 'LONG' else fill_price + (pending_limit['atr'] * sl_mult)
                tp_price = fill_price + (pending_limit['atr'] * tp_mult) if pending_limit['direction'] == 'LONG' else fill_price - (pending_limit['atr'] * tp_mult)
                sl_dist = abs((fill_price - sl_price) / fill_price) * 100
                size = (equity * 0.12) / (sl_dist / 100)

                position = {
                    'direction': pending_limit['direction'],
                    'entry': fill_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size,
                    'entry_idx': i
                }
                pending_limit = None

        # Manage active position
        if position:
            bar = row
            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'direction': 'LONG', 'pnl_pct': pnl_pct, 'exit': 'SL', 'offset': offset_pct})
                    position = None
                    continue
                elif bar['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'direction': 'LONG', 'pnl_pct': pnl_pct, 'exit': 'TP', 'offset': offset_pct})
                    position = None
                    continue
            else:  # SHORT
                if bar['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'direction': 'SHORT', 'pnl_pct': pnl_pct, 'exit': 'SL', 'offset': offset_pct})
                    position = None
                    continue
                elif bar['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'direction': 'SHORT', 'pnl_pct': pnl_pct, 'exit': 'TP', 'offset': offset_pct})
                    position = None
                    continue

        # New signals (only if no position and no pending limit)
        if not position and pending_limit is None and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0:
                continue
            if not pd.isna(prev_row['rsi']):
                # RSI 35 cross (LONG) - place limit BELOW
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    signal_price = row['close']
                    limit_price = signal_price * (1 - offset_pct / 100)  # BELOW for LONG
                    pending_limit = {
                        'direction': 'LONG',
                        'signal_price': signal_price,
                        'limit_price': limit_price,
                        'atr': row['atr'],
                        'signal_idx': i
                    }
                # RSI 65 cross (SHORT) - place limit ABOVE
                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    signal_price = row['close']
                    limit_price = signal_price * (1 + offset_pct / 100)  # ABOVE for SHORT
                    pending_limit = {
                        'direction': 'SHORT',
                        'signal_price': signal_price,
                        'limit_price': limit_price,
                        'atr': row['atr'],
                        'signal_idx': i
                    }

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
    fill_rate = len(df_t)  # We don't track unfilled, but filled trades

    return {
        'offset_pct': offset_pct,
        'wait_bars': wait_bars,
        'trades': len(df_t),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'return': ret,
        'max_dd': max_dd,
        'return_dd': ret / abs(max_dd) if max_dd != 0 else 0
    }

print('\n' + '=' * 100)
print('TESTING LIMIT ORDER OFFSET STRATEGY:')
print('=' * 100)
print('SHORT: Place limit ABOVE signal price (wait for more exhaustion)')
print('LONG: Place limit BELOW signal price (wait for more exhaustion)')
print('=' * 100)

# Test different offsets and wait times
offset_options = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
wait_options = [3, 5, 10, 20]

results = []

for offset in offset_options:
    for wait in wait_options:
        result = backtest_limit_offset(df, offset, wait, sl_mult=2.0, tp_mult=3.0)
        if result:
            results.append(result)
            print(f'Offset {offset:4.2f}%, Wait {wait:2d} bars: {result["trades"]:3d} trades, {result["win_rate"]:5.1f}% win, {result["tp_rate"]:5.1f}% TP, {result["return"]:+7.1f}%, {result["return_dd"]:6.2f}x R/DD')

df_res = pd.DataFrame(results)

print('\n' + '=' * 100)
print('TOP 10 BY RETURN:')
print('=' * 100)

top_return = df_res.nlargest(10, 'return')
for idx, row in top_return.iterrows():
    print(f'Offset {row["offset_pct"]:4.2f}%, Wait {int(row["wait_bars"]):2d} bars: {int(row["trades"]):3d} trades, {row["win_rate"]:5.1f}% win, {row["return"]:+7.1f}%, {row["return_dd"]:6.2f}x R/DD')

print('\n' + '=' * 100)
print('TOP 10 BY RETURN/DD:')
print('=' * 100)

top_rdd = df_res.nlargest(10, 'return_dd')
for idx, row in top_rdd.iterrows():
    print(f'Offset {row["offset_pct"]:4.2f}%, Wait {int(row["wait_bars"]):2d} bars: {int(row["trades"]):3d} trades, {row["win_rate"]:5.1f}% win, {row["return"]:+7.1f}%, {row["return_dd"]:6.2f}x R/DD')

print('\n' + '=' * 100)
print('BASELINE (no offset, market order):')
# Baseline = offset 0.0%, no wait
baseline = df_res[df_res['offset_pct'] == 0.0].iloc[0] if len(df_res[df_res['offset_pct'] == 0.0]) > 0 else None
if baseline is not None:
    print(f'Market order: {int(baseline["trades"])} trades, {baseline["win_rate"]:.1f}% win, {baseline["return"]:+.1f}%, {baseline["return_dd"]:.2f}x R/DD')
print('=' * 100)

df_res.to_csv('jul_aug_limit_offset_test.csv', index=False)
print(f'\n💾 Saved: jul_aug_limit_offset_test.csv')
