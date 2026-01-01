"""Download and test each month Jan-Jun 2025"""
import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

months = [
    ('Jan 2025', datetime(2025, 1, 1, tzinfo=timezone.utc), datetime(2025, 1, 31, 23, 59, tzinfo=timezone.utc)),
    ('Feb 2025', datetime(2025, 2, 1, tzinfo=timezone.utc), datetime(2025, 2, 28, 23, 59, tzinfo=timezone.utc)),
    ('Mar 2025', datetime(2025, 3, 1, tzinfo=timezone.utc), datetime(2025, 3, 31, 23, 59, tzinfo=timezone.utc)),
    ('Apr 2025', datetime(2025, 4, 1, tzinfo=timezone.utc), datetime(2025, 4, 30, 23, 59, tzinfo=timezone.utc)),
    ('May 2025', datetime(2025, 5, 1, tzinfo=timezone.utc), datetime(2025, 5, 31, 23, 59, tzinfo=timezone.utc)),
    ('Jun 2025', datetime(2025, 6, 1, tzinfo=timezone.utc), datetime(2025, 6, 30, 23, 59, tzinfo=timezone.utc)),
]

def backtest_month(df):
    """Backtest with RSI 35/65 + ret_20 > 0%"""
    trades, equity, position = [], 100.0, None
    
    for i in range(300, len(df)):
        row = df.iloc[i]
        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']): 
            continue
            
        if position:
            bar = row
            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl = position['size'] * ((position['sl_price'] - position['entry']) / position['entry']) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': ((position['sl_price'] - position['entry']) / position['entry']) * 100, 'equity': equity})
                    position = None
                    continue
                if bar['high'] >= position['tp_price']:
                    pnl = position['size'] * ((position['tp_price'] - position['entry']) / position['entry']) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': ((position['tp_price'] - position['entry']) / position['entry']) * 100, 'equity': equity})
                    position = None
                    continue
            else:
                if bar['high'] >= position['sl_price']:
                    pnl = position['size'] * ((position['entry'] - position['sl_price']) / position['entry']) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': ((position['entry'] - position['sl_price']) / position['entry']) * 100, 'equity': equity})
                    position = None
                    continue
                if bar['low'] <= position['tp_price']:
                    pnl = position['size'] * ((position['entry'] - position['tp_price']) / position['entry']) - position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl_pct': ((position['entry'] - position['tp_price']) / position['entry']) * 100, 'equity': equity})
                    position = None
                    continue
        
        if not position and i > 0:
            prev_row = df.iloc[i-1]
            if row['ret_20'] <= 0: 
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
    
    if not trades:
        return None
        
    df_t = pd.DataFrame(trades)
    ret = ((equity - 100) / 100) * 100
    eq = [100.0] + df_t['equity'].tolist()
    eq_s = pd.Series(eq)
    max_dd = ((eq_s - eq_s.expanding().max()) / eq_s.expanding().max() * 100).min()
    win_rate = (df_t['pnl_pct'] > 0).sum() / len(df_t) * 100
    
    return {
        'trades': len(df_t),
        'win_rate': win_rate,
        'return': ret,
        'max_dd': max_dd,
        'return_dd': ret / abs(max_dd) if max_dd != 0 else 0,
        'equity': equity
    }

results = []

for name, start, end in months:
    print(f"\nDownloading {name}...")
    
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
            print(f"  Downloaded {len(all_candles)} candles...", end='\r')
            time.sleep(0.5)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(2)
            continue
    
    if not all_candles:
        print(f"  ❌ No data for {name}")
        continue
        
    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= start.replace(tzinfo=None)) & (df['timestamp'] <= end.replace(tzinfo=None))]
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"  Loaded {len(df)} bars                    ")
    
    # Calculate indicators
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
    df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100
    df['ret_288'] = (df['close'] / df['close'].shift(288) - 1) * 100
    
    # Backtest
    result = backtest_month(df)
    
    if result:
        result['month'] = name
        result['avg_range_96'] = df['range_96'].mean()
        result['avg_ret_288'] = df['ret_288'].mean()
        result['price_change'] = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
        results.append(result)
        
        print(f"  ✓ {result['trades']} trades, {result['win_rate']:.1f}% win, {result['return']:+.0f}%, {result['return_dd']:.2f}x R/DD")
    else:
        print(f"  ❌ No trades")

# Add previous results
results.extend([
    {'month': 'Jul-Aug 2025', 'trades': 57, 'win_rate': 45.6, 'return': 4.18, 'max_dd': -79.70, 'return_dd': 0.05, 'equity': 104.18, 'avg_range_96': 9.46, 'avg_ret_288': 0.28, 'price_change': -5.0},
    {'month': 'Sep-Dec 2025', 'trades': 53, 'win_rate': 64.2, 'return': 1685.86, 'max_dd': -41.32, 'return_dd': 40.80, 'equity': 1785.86, 'avg_range_96': 15.52, 'avg_ret_288': -1.13, 'price_change': -44.62}
])

df_results = pd.DataFrame(results).sort_values('return_dd', ascending=False)

print("\n" + "=" * 80)
print("ALL MONTHS RANKED:")
print("=" * 80)

print(f"\n| # | Month | Trades | Win% | Return | DD | R/DD | Range96 | ret288 | Price% | Status |")
print("|---|-------|--------|------|--------|--------|------|---------|--------|--------|--------|")

for i, (idx, row) in enumerate(df_results.iterrows(), 1):
    status = "✅ GOOD" if row['return_dd'] >= 5 else ("⚠️  OK" if row['return_dd'] >= 1 else "❌ BAD")
    print(f"| {i:2d} | {row['month']:<14s} | {row['trades']:3.0f} | {row['win_rate']:4.1f}% | {row['return']:+6.0f}% | {row['max_dd']:6.1f}% | {row['return_dd']:5.2f} | {row['avg_range_96']:7.2f} | {row['avg_ret_288']:+6.2f}% | {row['price_change']:+6.1f}% | {status} |")

good = df_results[df_results['return_dd'] >= 3]
bad = df_results[df_results['return_dd'] < 1]

if len(good) > 0 and len(bad) > 0:
    print("\n" + "=" * 80)
    print("GOOD vs BAD COMPARISON:")
    print("=" * 80)
    
    print(f"\nGOOD months (R/DD >= 3): avg_range_96 = {good['avg_range_96'].mean():.2f}%")
    print(f"BAD months (R/DD < 1):   avg_range_96 = {bad['avg_range_96'].mean():.2f}%")
    print(f"\nDifference: {((good['avg_range_96'].mean() - bad['avg_range_96'].mean()) / bad['avg_range_96'].mean() * 100):+.1f}%")
    
    threshold = (good['avg_range_96'].mean() + bad['avg_range_96'].mean()) / 2
    print(f"\n🎯 REGIME FILTER: Range96 > {threshold:.1f}%")

df_results.to_csv('all_months_results.csv', index=False)
print(f"\n💾 Saved: all_months_results.csv")
