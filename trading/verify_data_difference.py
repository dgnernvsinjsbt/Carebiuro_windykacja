"""
Verify if BingX API data differs from CSV data
Compare October 2025 data as a test case
"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

print('=' * 100)
print('COMPARING BINGX API DATA vs CSV FILE DATA')
print('Test Case: October 2025 (where results differed massively)')
print('=' * 100)

# Load CSV data
print('\n1. Loading CSV data...')
df_csv = pd.read_csv('trading/melania_15m_jan2025.csv')
df_csv['timestamp'] = pd.to_datetime(df_csv['timestamp'])
df_oct_csv = df_csv[(df_csv['timestamp'].dt.month == 10) & (df_csv['timestamp'].dt.year == 2025)].copy()
df_oct_csv = df_oct_csv.sort_values('timestamp').reset_index(drop=True)
print(f'   CSV October bars: {len(df_oct_csv)}')
print(f'   Date range: {df_oct_csv["timestamp"].min()} to {df_oct_csv["timestamp"].max()}')
print(f'   First close: ${df_oct_csv.iloc[0]["close"]:.6f}')
print(f'   Last close: ${df_oct_csv.iloc[-1]["close"]:.6f}')

# Download from BingX API
print('\n2. Downloading from BingX API...')
exchange = ccxt.bingx({'enableRateLimit': True})
start = datetime(2025, 10, 1, tzinfo=timezone.utc)
end = datetime(2025, 10, 31, 23, 59, tzinfo=timezone.utc)
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
        print(f'   Downloaded {len(all_candles)} candles...', end='\r')
        time.sleep(0.5)
    except Exception as e:
        print(f'\n   Error: {e}')
        time.sleep(2)
        continue

df_api = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df_api['timestamp'] = pd.to_datetime(df_api['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
df_api = df_api[(df_api['timestamp'] >= start.replace(tzinfo=None)) &
                 (df_api['timestamp'] <= end.replace(tzinfo=None))].sort_values('timestamp').reset_index(drop=True)

print(f'\n   API October bars: {len(df_api)}')
print(f'   Date range: {df_api["timestamp"].min()} to {df_api["timestamp"].max()}')
print(f'   First close: ${df_api.iloc[0]["close"]:.6f}')
print(f'   Last close: ${df_api.iloc[-1]["close"]:.6f}')

# Compare
print('\n3. Comparison:')
print('   ' + '-' * 80)

if len(df_api) != len(df_oct_csv):
    print(f'   ❌ BAR COUNT MISMATCH: API has {len(df_api)} bars, CSV has {len(df_oct_csv)} bars')
else:
    print(f'   ✅ Bar count matches: {len(df_api)} bars')

# Merge on timestamp and compare values
df_merged = pd.merge(df_oct_csv, df_api, on='timestamp', how='outer', suffixes=('_csv', '_api'), indicator=True)

# Check for missing data
only_csv = df_merged[df_merged['_merge'] == 'left_only']
only_api = df_merged[df_merged['_merge'] == 'right_only']
both = df_merged[df_merged['_merge'] == 'both']

print(f'\n   Bars only in CSV: {len(only_csv)}')
print(f'   Bars only in API: {len(only_api)}')
print(f'   Bars in both: {len(both)}')

if len(only_csv) > 0:
    print(f'\n   Example timestamps only in CSV (first 5):')
    for ts in only_csv['timestamp'].head():
        print(f'      {ts}')

if len(only_api) > 0:
    print(f'\n   Example timestamps only in API (first 5):')
    for ts in only_api['timestamp'].head():
        print(f'      {ts}')

# For matching bars, compare OHLCV values
if len(both) > 0:
    both['close_diff'] = abs(both['close_csv'] - both['close_api'])
    both['close_diff_pct'] = (both['close_diff'] / both['close_csv']) * 100

    max_diff = both['close_diff_pct'].max()
    avg_diff = both['close_diff_pct'].mean()
    num_different = (both['close_diff_pct'] > 0.01).sum()  # More than 0.01% difference

    print(f'\n   Close price comparison (for {len(both)} matching bars):')
    print(f'      Max difference: {max_diff:.4f}%')
    print(f'      Avg difference: {avg_diff:.6f}%')
    print(f'      Bars with >0.01% diff: {num_different}')

    if max_diff > 0.1:
        print(f'\n   ⚠️  SIGNIFICANT PRICE DIFFERENCES FOUND!')
        worst = both.nlargest(5, 'close_diff_pct')[['timestamp', 'close_csv', 'close_api', 'close_diff_pct']]
        print(f'\n   Top 5 worst differences:')
        for idx, row in worst.iterrows():
            print(f'      {row["timestamp"]}: CSV=${row["close_csv"]:.6f}, API=${row["close_api"]:.6f}, Diff={row["close_diff_pct"]:.4f}%')
    else:
        print(f'\n   ✅ Price data matches closely (all diffs < 0.1%)')

# Now backtest both datasets with SAME logic
print('\n' + '=' * 100)
print('4. BACKTEST COMPARISON (SAME LOGIC, DIFFERENT DATA):')
print('=' * 100)

def quick_backtest(df):
    """Simple backtest - RSI 35/65 + ret_20 > 0"""
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ))
    df['atr'] = df['tr'].rolling(14).mean()
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

    trades, equity, position = [], 100.0, None

    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            continue

        # Manage position (same logic as before)
        if position:
            if position['direction'] == 'LONG':
                if row['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append(pnl_pct)
                    position = None
                    continue
                elif row['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append(pnl_pct)
                    position = None
                    continue
            else:  # SHORT
                if row['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append(pnl_pct)
                    position = None
                    continue
                elif row['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                    equity += pnl
                    trades.append(pnl_pct)
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
                    sl = entry - (row['atr'] * 2.0)
                    tp = entry + (row['atr'] * 3.0)
                    sl_dist = abs((entry - sl) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {'direction': 'LONG', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}
                # SHORT: RSI crosses below 65
                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    entry = row['close']
                    sl = entry + (row['atr'] * 2.0)
                    tp = entry - (row['atr'] * 3.0)
                    sl_dist = abs((sl - entry) / entry) * 100
                    size = (equity * 0.12) / (sl_dist / 100)
                    position = {'direction': 'SHORT', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}

    if not trades:
        return None

    ret = ((equity - 100) / 100) * 100
    return {'trades': len(trades), 'return': ret, 'equity': equity}

csv_result = quick_backtest(df_oct_csv.copy())
api_result = quick_backtest(df_api.copy())

print(f'\nCSV Data Backtest:')
if csv_result:
    print(f'   Trades: {csv_result["trades"]}')
    print(f'   Return: {csv_result["return"]:+.2f}%')
    print(f'   Final equity: ${csv_result["equity"]:.2f}')
else:
    print(f'   No trades')

print(f'\nAPI Data Backtest:')
if api_result:
    print(f'   Trades: {api_result["trades"]}')
    print(f'   Return: {api_result["return"]:+.2f}%')
    print(f'   Final equity: ${api_result["equity"]:.2f}')
else:
    print(f'   No trades')

if csv_result and api_result:
    trade_diff = csv_result['trades'] - api_result['trades']
    return_diff = csv_result['return'] - api_result['return']

    print(f'\nDifference:')
    print(f'   Trades: {trade_diff:+d} ({abs(trade_diff / api_result["trades"] * 100):.1f}% difference)')
    print(f'   Return: {return_diff:+.2f}% difference')

    if abs(return_diff) > 10:
        print(f'\n   ❌ SIGNIFICANT BACKTEST DIFFERENCE! Data sources are NOT equivalent.')
    else:
        print(f'\n   ✅ Backtest results similar despite minor data differences.')

print('\n' + '=' * 100)
print('CONCLUSION')
print('=' * 100)
print('\nIf data differs significantly, this explains the 510% vs -250% discrepancy.')
print('The old script used fresh BingX API data, the new script uses cached CSV data.')
