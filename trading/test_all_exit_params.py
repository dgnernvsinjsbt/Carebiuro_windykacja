"""
Test ALL exit parameter combinations on Jul-Aug (worst month)
Find if different SL/TP can fix the problem
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

    return {
        'sl_mult': sl_mult,
        'tp_mult': tp_mult,
        'trades': len(df_t),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'return': ret,
        'max_dd': max_dd,
        'return_dd': ret / abs(max_dd) if max_dd != 0 else 0
    }

print('\n' + '=' * 100)
print('TESTING ALL EXIT COMBINATIONS ON JUL-AUG 2025:')
print('=' * 100)

# Test grid
sl_options = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
tp_options = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]

results = []

for sl in sl_options:
    for tp in tp_options:
        result = backtest_params(df, sl, tp)
        if result:
            results.append(result)
            rr = tp / sl
            print(f'SL {sl:.1f}x / TP {tp:.1f}x (R:R {rr:.2f}): {result["trades"]:3d} trades, {result["win_rate"]:5.1f}% win, {result["tp_rate"]:5.1f}% TP, {result["return"]:+7.1f}%, {result["return_dd"]:5.2f}x R/DD')

df_res = pd.DataFrame(results)

print('\n' + '=' * 100)
print('TOP 10 BY RETURN:')
print('=' * 100)

top_return = df_res.nlargest(10, 'return')
for i, row in top_return.iterrows():
    rr = row['tp_mult'] / row['sl_mult']
    print(f'SL {row["sl_mult"]:.1f}x / TP {row["tp_mult"]:.1f}x (R:R {rr:.2f}): {row["trades"]:3d} trades, {row["win_rate"]:5.1f}% win, {row["return"]:+7.1f}%, {row["return_dd"]:5.2f}x R/DD')

print('\n' + '=' * 100)
print('TOP 10 BY RETURN/DD:')
print('=' * 100)

top_rdd = df_res.nlargest(10, 'return_dd')
for i, row in top_rdd.iterrows():
    rr = row['tp_mult'] / row['sl_mult']
    print(f'SL {row["sl_mult"]:.1f}x / TP {row["tp_mult"]:.1f}x (R:R {rr:.2f}): {row["trades"]:3d} trades, {row["win_rate"]:5.1f}% win, {row["return"]:+7.1f}%, {row["return_dd"]:5.2f}x R/DD')

print('\n' + '=' * 100)
print('TOP 10 BY WIN RATE:')
print('=' * 100)

top_wr = df_res.nlargest(10, 'win_rate')
for i, row in top_wr.iterrows():
    rr = row['tp_mult'] / row['sl_mult']
    print(f'SL {row["sl_mult"]:.1f}x / TP {row["tp_mult"]:.1f}x (R:R {rr:.2f}): {row["trades"]:3d} trades, {row["win_rate"]:5.1f}% win, {row["return"]:+7.1f}%, {row["return_dd"]:5.2f}x R/DD')

df_res.to_csv('jul_aug_exit_param_test.csv', index=False)
print(f'\n💾 Saved: jul_aug_exit_param_test.csv')
