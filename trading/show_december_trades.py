"""
Show ALL December 2025 trades in detail
"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

print('=' * 100)
print('DECEMBER 2025 - ALL TRADES DETAILED')
print('=' * 100)

start = datetime(2025, 12, 1, tzinfo=timezone.utc)
end = datetime(2025, 12, 15, 23, 59, tzinfo=timezone.utc)

start_ts = int(start.timestamp() * 1000)
end_ts = int(end.timestamp() * 1000)

print(f'\nDownloading data...')

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
df['atr_pct'] = (df['atr'] / df['close']) * 100
df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100
df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100
df['range_288'] = ((df['high'].rolling(288).max() - df['low'].rolling(288).min()) / df['low'].rolling(288).min()) * 100

# Backtest
trades = []
equity = 100.0
position = None

for i in range(300, len(df)):
    row = df.iloc[i]
    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
        continue

    if position:
        bars_held = i - position['entry_idx']
        bar = row

        if position['direction'] == 'LONG':
            if bar['low'] <= position['sl_price']:
                pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': df.iloc[i]['timestamp'],
                    'direction': 'LONG',
                    'entry': position['entry'],
                    'exit': position['sl_price'],
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'exit_type': 'SL',
                    'bars_held': bars_held,
                    'entry_rsi': position['entry_rsi'],
                    'entry_atr_pct': position['entry_atr_pct'],
                    'entry_ret_20': position['entry_ret_20'],
                    'entry_range_96': position['entry_range_96'],
                    'entry_range_288': position['entry_range_288']
                })
                position = None
                continue
            elif bar['high'] >= position['tp_price']:
                pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': df.iloc[i]['timestamp'],
                    'direction': 'LONG',
                    'entry': position['entry'],
                    'exit': position['tp_price'],
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'exit_type': 'TP',
                    'bars_held': bars_held,
                    'entry_rsi': position['entry_rsi'],
                    'entry_atr_pct': position['entry_atr_pct'],
                    'entry_ret_20': position['entry_ret_20'],
                    'entry_range_96': position['entry_range_96'],
                    'entry_range_288': position['entry_range_288']
                })
                position = None
                continue
        else:  # SHORT
            if bar['high'] >= position['sl_price']:
                pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': df.iloc[i]['timestamp'],
                    'direction': 'SHORT',
                    'entry': position['entry'],
                    'exit': position['sl_price'],
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'exit_type': 'SL',
                    'bars_held': bars_held,
                    'entry_rsi': position['entry_rsi'],
                    'entry_atr_pct': position['entry_atr_pct'],
                    'entry_ret_20': position['entry_ret_20'],
                    'entry_range_96': position['entry_range_96'],
                    'entry_range_288': position['entry_range_288']
                })
                position = None
                continue
            elif bar['low'] <= position['tp_price']:
                pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                pnl = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
                equity += pnl
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': df.iloc[i]['timestamp'],
                    'direction': 'SHORT',
                    'entry': position['entry'],
                    'exit': position['tp_price'],
                    'pnl_pct': pnl_pct,
                    'pnl_usd': pnl,
                    'equity': equity,
                    'exit_type': 'TP',
                    'bars_held': bars_held,
                    'entry_rsi': position['entry_rsi'],
                    'entry_atr_pct': position['entry_atr_pct'],
                    'entry_ret_20': position['entry_ret_20'],
                    'entry_range_96': position['entry_range_96'],
                    'entry_range_288': position['entry_range_288']
                })
                position = None
                continue

    if not position and i > 0:
        prev_row = df.iloc[i-1]
        if row['ret_20'] <= 0:
            continue
        if not pd.isna(prev_row['rsi']):
            # RSI 35 cross (LONG)
            if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                entry = row['close']
                sl = entry - (row['atr'] * 2.0)
                tp = entry + (row['atr'] * 3.0)
                sl_dist = abs((entry - sl) / entry) * 100
                size = (equity * 0.12) / (sl_dist / 100)
                position = {
                    'direction': 'LONG',
                    'entry': entry,
                    'sl_price': sl,
                    'tp_price': tp,
                    'size': size,
                    'entry_idx': i,
                    'entry_date': row['timestamp'],
                    'entry_rsi': row['rsi'],
                    'entry_atr_pct': row['atr_pct'],
                    'entry_ret_20': row['ret_20'],
                    'entry_range_96': row['range_96'],
                    'entry_range_288': row['range_288']
                }
            # RSI 65 cross (SHORT)
            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                entry = row['close']
                sl = entry + (row['atr'] * 2.0)
                tp = entry - (row['atr'] * 3.0)
                sl_dist = abs((sl - entry) / entry) * 100
                size = (equity * 0.12) / (sl_dist / 100)
                position = {
                    'direction': 'SHORT',
                    'entry': entry,
                    'sl_price': sl,
                    'tp_price': tp,
                    'size': size,
                    'entry_idx': i,
                    'entry_date': row['timestamp'],
                    'entry_rsi': row['rsi'],
                    'entry_atr_pct': row['atr_pct'],
                    'entry_ret_20': row['ret_20'],
                    'entry_range_96': row['range_96'],
                    'entry_range_288': row['range_288']
                }

df_trades = pd.DataFrame(trades)

print('\n' + '=' * 100)
print('ALL DECEMBER TRADES:')
print('=' * 100)

for i, trade in df_trades.iterrows():
    print(f"\nTrade #{i+1}: {trade['direction']} {'✅ WIN' if trade['pnl_pct'] > 0 else '❌ LOSS'}")
    print(f"  Entry: {trade['entry_date'].strftime('%Y-%m-%d %H:%M')} @ ${trade['entry']:.4f}")
    print(f"  Exit:  {trade['exit_date'].strftime('%Y-%m-%d %H:%M')} @ ${trade['exit']:.4f} ({trade['exit_type']})")
    print(f"  P&L: {trade['pnl_pct']:+.2f}% (${trade['pnl_usd']:+.2f}) | Equity: ${trade['equity']:.2f}")
    print(f"  Held: {trade['bars_held']} bars ({trade['bars_held']*15/60:.1f}h)")
    print(f"  Entry conditions:")
    print(f"    - RSI: {trade['entry_rsi']:.1f}")
    print(f"    - ret_20: {trade['entry_ret_20']:+.2f}%")
    print(f"    - ATR%: {trade['entry_atr_pct']:.2f}%")
    print(f"    - Range96: {trade['entry_range_96']:.2f}%")
    print(f"    - Range288: {trade['entry_range_288']:.2f}%")

print('\n' + '=' * 100)
print('SUMMARY:')
print('=' * 100)

winners = df_trades[df_trades['pnl_pct'] > 0]
losers = df_trades[df_trades['pnl_pct'] < 0]

print(f'\nTotal trades: {len(df_trades)}')
print(f'Winners: {len(winners)} ({len(winners)/len(df_trades)*100:.1f}%)')
print(f'Losers: {len(losers)} ({len(losers)/len(df_trades)*100:.1f}%)')
print(f'Total return: {((df_trades["equity"].iloc[-1] - 100) / 100 * 100):+.2f}%')
print(f'Avg winner: {winners["pnl_pct"].mean():+.2f}%')
if len(losers) > 0:
    print(f'Avg loser: {losers["pnl_pct"].mean():+.2f}%')

print('\nDirection breakdown:')
print(f'LONG: {len(df_trades[df_trades["direction"] == "LONG"])} trades, {(df_trades[df_trades["direction"] == "LONG"]["pnl_pct"] > 0).sum()} wins')
print(f'SHORT: {len(df_trades[df_trades["direction"] == "SHORT"])} trades, {(df_trades[df_trades["direction"] == "SHORT"]["pnl_pct"] > 0).sum()} wins')

print('\nEntry conditions (avg):')
print(f'RSI: {df_trades["entry_rsi"].mean():.1f}')
print(f'ret_20: {df_trades["entry_ret_20"].mean():+.2f}%')
print(f'ATR%: {df_trades["entry_atr_pct"].mean():.2f}%')
print(f'Range96: {df_trades["entry_range_96"].mean():.2f}%')
print(f'Range288: {df_trades["entry_range_288"].mean():.2f}%')

df_trades.to_csv('december_all_trades.csv', index=False)
print(f'\n💾 Saved: december_all_trades.csv')
