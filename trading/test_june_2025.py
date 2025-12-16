import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

exchange = ccxt.bingx({'enableRateLimit': True})

start = datetime(2025, 6, 1, tzinfo=timezone.utc)
end = datetime(2025, 6, 30, 23, 59, 59, tzinfo=timezone.utc)

print("Downloading MELANIA June 2025 15m data...")

all_candles = []
current_ts = int(start.timestamp() * 1000)
end_ts = int(end.timestamp() * 1000)

while current_ts < end_ts:
    try:
        candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
        if not candles:
            break
        all_candles.extend(candles)
        current_ts = candles[-1][0] + (15 * 60 * 1000)
        time.sleep(0.5)
    except:
        time.sleep(2)
        continue

df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
df = df[(df['timestamp'] >= start.replace(tzinfo=None)) & (df['timestamp'] <= end.replace(tzinfo=None))]
df = df.sort_values('timestamp').reset_index(drop=True)

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
df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100
df['ret_288'] = (df['close'] / df['close'].shift(288) - 1) * 100

print(f"Loaded {len(df)} bars")

trades = []
equity = 100.0
position = None

i = 300
while i < len(df):
    row = df.iloc[i]
    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
        i += 1
        continue

    if position is not None:
        bar = row
        if position['direction'] == 'LONG':
            if bar['low'] <= position['sl_price']:
                pnl = position['size'] * ((position['sl_price'] - position['entry']) / position['entry']) - position['size'] * 0.001
                equity += pnl
                trades.append({'pnl_pct': ((position['sl_price'] - position['entry']) / position['entry']) * 100, 'equity': equity})
                position = None
                i += 1
                continue
            if bar['high'] >= position['tp_price']:
                pnl = position['size'] * ((position['tp_price'] - position['entry']) / position['entry']) - position['size'] * 0.001
                equity += pnl
                trades.append({'pnl_pct': ((position['tp_price'] - position['entry']) / position['entry']) * 100, 'equity': equity})
                position = None
                i += 1
                continue
        elif position['direction'] == 'SHORT':
            if bar['high'] >= position['sl_price']:
                pnl = position['size'] * ((position['entry'] - position['sl_price']) / position['entry']) - position['size'] * 0.001
                equity += pnl
                trades.append({'pnl_pct': ((position['entry'] - position['sl_price']) / position['entry']) * 100, 'equity': equity})
                position = None
                i += 1
                continue
            if bar['low'] <= position['tp_price']:
                pnl = position['size'] * ((position['entry'] - position['tp_price']) / position['entry']) - position['size'] * 0.001
                equity += pnl
                trades.append({'pnl_pct': ((position['entry'] - position['tp_price']) / position['entry']) * 100, 'equity': equity})
                position = None
                i += 1
                continue

    if position is None and i > 0:
        prev_row = df.iloc[i-1]
        if row['ret_20'] <= 0:
            i += 1
            continue
        if not pd.isna(prev_row['rsi']):
            if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                entry = row['close']
                sl = entry - (row['atr'] * 2.0)
                tp = entry + (row['atr'] * 3.0)
                sl_dist = abs((entry - sl) / entry) * 100
                size = (equity * 0.12) / (sl_dist / 100)
                position = {'direction': 'LONG', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}
            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                entry = row['close']
                sl = entry + (row['atr'] * 2.0)
                tp = entry - (row['atr'] * 3.0)
                sl_dist = abs((sl - entry) / entry) * 100
                size = (equity * 0.12) / (sl_dist / 100)
                position = {'direction': 'SHORT', 'entry': entry, 'sl_price': sl, 'tp_price': tp, 'size': size}
    i += 1

if len(trades) > 0:
    df_t = pd.DataFrame(trades)
    ret = ((equity - 100) / 100) * 100
    eq = [100.0] + df_t['equity'].tolist()
    eq_s = pd.Series(eq)
    max_dd = ((eq_s - eq_s.expanding().max()) / eq_s.expanding().max() * 100).min()
    win_rate = (df_t['pnl_pct'] > 0).sum() / len(df_t) * 100
    
    print(f"\n📊 JUNE 2025 RESULTS:")
    print(f"  Trades: {len(df_t)}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Return: {ret:+.1f}%")
    print(f"  Max DD: {max_dd:.1f}%")
    print(f"  R/DD: {ret/abs(max_dd):.2f}x")
    print(f"  Final: ${equity:.2f}")
    
    print(f"\n📊 MARKET CONDITIONS:")
    print(f"  Avg Range96: {df['range_96'].mean():.2f}%")
    print(f"  Avg ret_288: {df['ret_288'].mean():+.2f}%")
    print(f"  Price Change: {(df['close'].iloc[-1]/df['close'].iloc[0]-1)*100:+.1f}%")
    
    if ret/abs(max_dd) >= 5:
        print(f"\n✅ GOOD MONTH (R/DD >= 5)")
    elif ret/abs(max_dd) >= 1:
        print(f"\n⚠️  OK MONTH (1 <= R/DD < 5)")
    else:
        print(f"\n❌ BAD MONTH (R/DD < 1)")
else:
    print("No trades")
