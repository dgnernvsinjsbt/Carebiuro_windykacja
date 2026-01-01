"""
Dlaczego December działa a September nie, mimo tego samego Range96?
"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

periods = [
    ('Sep 2025', datetime(2025, 9, 16, tzinfo=timezone.utc), datetime(2025, 9, 30, 23, 59, tzinfo=timezone.utc)),
    ('Dec 2025', datetime(2025, 12, 1, tzinfo=timezone.utc), datetime(2025, 12, 15, tzinfo=timezone.utc)),
]

def analyze_period(df, name):
    """Backtest i szczegółowa analiza tradów"""
    trades = []
    equity = 100.0
    position = None
    
    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']): 
            continue
            
        if position:
            bar = row
            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl_pct = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    trades.append({**position, 'exit': 'SL', 'pnl_pct': pnl_pct, 'exit_idx': i})
                    position = None
                    continue
                if bar['high'] >= position['tp_price']:
                    pnl_pct = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    trades.append({**position, 'exit': 'TP', 'pnl_pct': pnl_pct, 'exit_idx': i})
                    position = None
                    continue
            else:
                if bar['high'] >= position['sl_price']:
                    pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    trades.append({**position, 'exit': 'SL', 'pnl_pct': pnl_pct, 'exit_idx': i})
                    position = None
                    continue
                if bar['low'] <= position['tp_price']:
                    pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    trades.append({**position, 'exit': 'TP', 'pnl_pct': pnl_pct, 'exit_idx': i})
                    position = None
                    continue
        
        if not position and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0: 
                continue
            if not pd.isna(prev_row['rsi']):
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    position = {
                        'direction': 'LONG', 
                        'entry': row['close'],
                        'sl_price': row['close'] - (row['atr'] * 2.0),
                        'tp_price': row['close'] + (row['atr'] * 3.0),
                        'entry_idx': i,
                        'entry_rsi': row['rsi'],
                        'entry_atr_pct': row['atr_pct'],
                        'entry_ret_20': row['ret_20'],
                        'entry_ret_96': row['ret_96'],
                        'entry_range_20': row['range_20'],
                        'entry_ema_dist': row['ema_dist'],
                        'entry_price': row['close']
                    }
                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    position = {
                        'direction': 'SHORT',
                        'entry': row['close'],
                        'sl_price': row['close'] + (row['atr'] * 2.0),
                        'tp_price': row['close'] - (row['atr'] * 3.0),
                        'entry_idx': i,
                        'entry_rsi': row['rsi'],
                        'entry_atr_pct': row['atr_pct'],
                        'entry_ret_20': row['ret_20'],
                        'entry_ret_96': row['ret_96'],
                        'entry_range_20': row['range_20'],
                        'entry_ema_dist': row['ema_dist'],
                        'entry_price': row['close']
                    }
    
    return pd.DataFrame(trades) if trades else None

all_data = {}

for name, start, end in periods:
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
    df['ret_96'] = (df['close'] / df['close'].shift(96) - 1) * 100
    df['ret_288'] = (df['close'] / df['close'].shift(288) - 1) * 100
    
    df['range_20'] = ((df['high'].rolling(20).max() - df['low'].rolling(20).min()) / df['low'].rolling(20).min()) * 100
    df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100
    
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_dist'] = ((df['close'] - df['ema_20']) / df['ema_20']) * 100
    
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['volume_ma']
    
    all_data[name] = {
        'df': df,
        'trades': analyze_period(df, name)
    }
    
    print(f'  {len(df)} bars')

print('\n' + '=' * 80)
print('PORÓWNANIE WARUNKÓW RYNKOWYCH:')
print('=' * 80)

sep_df = all_data['Sep 2025']['df']
dec_df = all_data['Dec 2025']['df']

metrics = [
    ('Avg ATR%', 'atr_pct', 'mean'),
    ('Avg Range20', 'range_20', 'mean'),
    ('Avg Range96', 'range_96', 'mean'),
    ('Avg ret_20', 'ret_20', 'mean'),
    ('Avg ret_96', 'ret_96', 'mean'),
    ('Avg ret_288', 'ret_288', 'mean'),
    ('Avg EMA dist', 'ema_dist', 'mean'),
    ('Avg Vol Ratio', 'vol_ratio', 'mean'),
    ('Price Change', 'close', lambda x: (x.iloc[-1] / x.iloc[0] - 1) * 100),
]

print(f'\n{"Metryka":<20} | {"September":<12} | {"December":<12} | {"Różnica":<10}')
print('-' * 65)

for metric_name, col, func in metrics:
    if callable(func):
        sep_val = func(sep_df[col])
        dec_val = func(dec_df[col])
    else:
        sep_val = getattr(sep_df[col], func)()
        dec_val = getattr(dec_df[col], func)()
    
    diff_pct = ((dec_val - sep_val) / abs(sep_val) * 100) if sep_val != 0 else 0
    marker = ' ⭐⭐⭐' if abs(diff_pct) > 50 else (' ⭐⭐' if abs(diff_pct) > 30 else (' ⭐' if abs(diff_pct) > 15 else ''))
    
    print(f'{metric_name:<20} | {sep_val:>11.2f} | {dec_val:>11.2f} | {diff_pct:>+9.1f}%{marker}')

print('\n' + '=' * 80)
print('PORÓWNANIE TRADÓW:')
print('=' * 80)

sep_trades = all_data['Sep 2025']['trades']
dec_trades = all_data['Dec 2025']['trades']

if sep_trades is not None and dec_trades is not None:
    print(f'\nSeptember: {len(sep_trades)} tradów')
    print(f'  Winners: {len(sep_trades[sep_trades["pnl_pct"] > 0])}/{len(sep_trades)} ({len(sep_trades[sep_trades["pnl_pct"] > 0])/len(sep_trades)*100:.0f}%)')
    print(f'  Avg P&L: {sep_trades["pnl_pct"].mean():+.2f}%')
    
    print(f'\nDecember: {len(dec_trades)} tradów')
    print(f'  Winners: {len(dec_trades[dec_trades["pnl_pct"] > 0])}/{len(dec_trades)} ({len(dec_trades[dec_trades["pnl_pct"] > 0])/len(dec_trades)*100:.0f}%)')
    print(f'  Avg P&L: {dec_trades["pnl_pct"].mean():+.2f}%')
    
    print('\n' + '=' * 80)
    print('CHARAKTERYSTYKA TRADÓW:')
    print('=' * 80)
    
    features = ['entry_atr_pct', 'entry_ret_20', 'entry_ret_96', 'entry_range_20', 'entry_ema_dist']
    
    print(f'\n{"Feature":<18} | {"Sep Avg":<10} | {"Dec Avg":<10} | {"Różnica":<10}')
    print('-' * 60)
    
    for feat in features:
        sep_avg = sep_trades[feat].mean()
        dec_avg = dec_trades[feat].mean()
        diff_pct = ((dec_avg - sep_avg) / abs(sep_avg) * 100) if sep_avg != 0 else 0
        marker = ' ⭐⭐⭐' if abs(diff_pct) > 50 else (' ⭐⭐' if abs(diff_pct) > 30 else (' ⭐' if abs(diff_pct) > 15 else ''))
        
        print(f'{feat:<18} | {sep_avg:>9.2f} | {dec_avg:>9.2f} | {diff_pct:>+9.1f}%{marker}')
    
    print('\n' + '=' * 80)
    print('WSZYSTKIE TRADY DECEMBER:')
    print('=' * 80)
    
    print(f'\n{"#":<3} | {"Dir":<5} | {"P&L%":<7} | {"Exit":<4} | {"ATR%":<6} | {"ret_20":<7} | {"ret_96":<7} | {"Range20":<8}')
    print('-' * 70)
    
    for i, row in dec_trades.iterrows():
        print(f'{i+1:<3} | {row["direction"]:<5} | {row["pnl_pct"]:>+6.2f}% | {row["exit"]:<4} | {row["entry_atr_pct"]:>5.2f} | {row["entry_ret_20"]:>+6.2f}% | {row["entry_ret_96"]:>+6.2f}% | {row["entry_range_20"]:>7.2f}')

print('\n' + '=' * 80)
print('WNIOSKI:')
print('=' * 80)
print('\nCo odróżnia December (działa) od September (nie działa) przy tym samym Range96?')
