"""
Comprehensive optimization to find 30+ trades with 5+ R/DD
Test: offsets, wait times, volatility filters
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("COMPREHENSIVE OFFSET OPTIMIZATION")
print("Target: 30+ trades, 5+ R/DD")
print("=" * 80)

# Download data
exchange = ccxt.bingx({'enableRateLimit': True})

end_date = datetime(2025, 12, 15, tzinfo=timezone.utc)
start_date = end_date - timedelta(days=90)

start_ts = int(start_date.timestamp() * 1000)
end_ts = int(end_date.timestamp() * 1000)

print(f"\nDownloading MELANIA 15m data...")

all_candles = []
current_ts = start_ts

while current_ts < end_ts:
    try:
        candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
        if not candles:
            break
        all_candles.extend(candles)
        current_ts = candles[-1][0] + (15 * 60 * 1000)
        time.sleep(0.5)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)
        continue

df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
df = df[(df['timestamp'] >= start_date.replace(tzinfo=None)) & (df['timestamp'] <= end_date.replace(tzinfo=None))]
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Downloaded {len(df)} bars")

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
df['atr_pct'] = (df['atr'] / df['close']) * 100

df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100

print("Indicators calculated")

def backtest_offset(df, config):
    long_rsi = config['long_rsi']
    short_rsi = config['short_rsi']
    min_atr_pct = config['min_atr_pct']
    min_range_96 = config['min_range_96']
    base_sl_mult = config['base_sl_mult']
    base_tp_mult = config['base_tp_mult']
    offset_pct = config['offset_pct']
    risk_pct = config['risk_pct']
    max_wait_bars = config['max_wait_bars']

    # Adjust SL/TP based on offset
    sl_adjustment = offset_pct * 0.1
    tp_adjustment = offset_pct * 0.1

    sl_mult = base_sl_mult - sl_adjustment
    tp_mult = base_tp_mult + tp_adjustment

    trades = []
    equity = 100.0
    position = None

    i = 300
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['atr_pct']) or pd.isna(row['range_96']):
            i += 1
            continue

        # Check for limit order fills
        if position is not None and 'limit_price' in position:
            bar = row
            bars_waited = i - position['signal_idx']

            if bars_waited > max_wait_bars:
                position = None
                i += 1
                continue

            filled = False
            if position['direction'] == 'LONG' and bar['low'] <= position['limit_price']:
                filled = True
            elif position['direction'] == 'SHORT' and bar['high'] >= position['limit_price']:
                filled = True

            if filled:
                position['entry'] = position['limit_price']
                del position['limit_price']
                del position['signal_idx']

        # Manage active position
        if position is not None and 'entry' in position:
            bar = row

            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl = position['size'] * ((position['sl_price'] - position['entry']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'SL', 'direction': 'LONG'})
                    position = None
                    i += 1
                    continue

                if bar['high'] >= position['tp_price']:
                    pnl = position['size'] * ((position['tp_price'] - position['entry']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'TP', 'direction': 'LONG'})
                    position = None
                    i += 1
                    continue

            elif position['direction'] == 'SHORT':
                if bar['high'] >= position['sl_price']:
                    pnl = position['size'] * ((position['entry'] - position['sl_price']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'SL', 'direction': 'SHORT'})
                    position = None
                    i += 1
                    continue

                if bar['low'] <= position['tp_price']:
                    pnl = position['size'] * ((position['entry'] - position['tp_price']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'TP', 'direction': 'SHORT'})
                    position = None
                    i += 1
                    continue

        # New signals
        if position is None and i > 0:
            prev_row = df.iloc[i-1]

            if row['atr_pct'] < min_atr_pct or row['range_96'] < min_range_96:
                i += 1
                continue

            if not pd.isna(prev_row['rsi']) and prev_row['rsi'] < long_rsi and row['rsi'] >= long_rsi:
                signal_price = row['close']
                limit_price = signal_price * (1 - offset_pct / 100)
                sl_price = limit_price - (row['atr'] * sl_mult)
                tp_price = limit_price + (row['atr'] * tp_mult)

                sl_distance_pct = abs((limit_price - sl_price) / limit_price) * 100
                risk_dollars = equity * (risk_pct / 100)
                size = risk_dollars / (sl_distance_pct / 100)

                position = {
                    'direction': 'LONG',
                    'limit_price': limit_price,
                    'signal_idx': i,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size
                }

            elif not pd.isna(prev_row['rsi']) and prev_row['rsi'] > short_rsi and row['rsi'] <= short_rsi:
                signal_price = row['close']
                limit_price = signal_price * (1 + offset_pct / 100)
                sl_price = limit_price + (row['atr'] * sl_mult)
                tp_price = limit_price - (row['atr'] * tp_mult)

                sl_distance_pct = abs((sl_price - limit_price) / limit_price) * 100
                risk_dollars = equity * (risk_pct / 100)
                size = risk_dollars / (sl_distance_pct / 100)

                position = {
                    'direction': 'SHORT',
                    'limit_price': limit_price,
                    'signal_idx': i,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'size': size
                }

        i += 1

    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100
    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    max_dd = ((eq - running_max) / running_max * 100).min()
    win_rate = (df_t['pnl'] > 0).sum() / len(df_t) * 100

    long_trades = df_t[df_t['direction'] == 'LONG']
    short_trades = df_t[df_t['direction'] == 'SHORT']

    return {
        'offset_pct': offset_pct,
        'max_wait': max_wait_bars,
        'min_atr': min_atr_pct,
        'min_range96': min_range_96,
        'sl_mult': sl_mult,
        'tp_mult': tp_mult,
        'trade_rr': tp_mult / sl_mult,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'tp_rate': (df_t['exit'] == 'TP').sum() / len(df_t) * 100,
        'final_equity': equity,
        'long_trades': len(long_trades),
        'short_trades': len(short_trades),
        'long_win': (long_trades['pnl'] > 0).sum() / len(long_trades) * 100 if len(long_trades) > 0 else 0,
        'short_win': (short_trades['pnl'] > 0).sum() / len(short_trades) * 100 if len(short_trades) > 0 else 0
    }

# Test configurations
print("\nTesting configurations...")
results = []

base_config = {
    'long_rsi': 35,
    'short_rsi': 65,
    'base_sl_mult': 2.0,
    'base_tp_mult': 3.0,
    'risk_pct': 12
}

test_count = 0
total_tests = len([0.2, 0.3, 0.5, 0.7, 1.0]) * len([3, 5, 7]) * len([1.5, 2.0, 2.5, 3.0]) * len([10, 15, 20, 25])

for offset in [0.2, 0.3, 0.5, 0.7, 1.0]:
    for wait in [3, 5, 7]:
        for atr in [1.5, 2.0, 2.5, 3.0]:
            for range96 in [10, 15, 20, 25]:
                test_count += 1
                if test_count % 20 == 0:
                    print(f"  Progress: {test_count}/{total_tests}")

                config = base_config.copy()
                config['offset_pct'] = offset
                config['max_wait_bars'] = wait
                config['min_atr_pct'] = atr
                config['min_range_96'] = range96

                res = backtest_offset(df, config)
                if res:
                    results.append(res)

print(f"\nCompleted {len(results)} tests")

# Filter for viable results
results_df = pd.DataFrame(results)

# Primary filter: 30+ trades AND 5+ R/DD
viable = results_df[(results_df['trades'] >= 30) & (results_df['return_dd'] >= 5.0)]

if len(viable) == 0:
    print("\n⚠️  No configs with 30+ trades AND 5+ R/DD")
    print("\nRelaxing to 20+ trades OR 7+ R/DD...")
    viable = results_df[((results_df['trades'] >= 20) & (results_df['return_dd'] >= 5.0)) |
                        ((results_df['trades'] >= 30) & (results_df['return_dd'] >= 3.0))]

if len(viable) == 0:
    print("\n⚠️  Still no viable configs. Showing best by R/DD...")
    viable = results_df.nlargest(20, 'return_dd')

viable = viable.sort_values('return_dd', ascending=False)

print("\n" + "=" * 80)
print("TOP RESULTS:")
print("=" * 80)

print(f"\n| # | Off% | Wait | ATR% | R96% | SL   | TP   | R:R  | Return  | DD    | R/DD   | Trades | Win% | TP% | L/S      |")
print("|---|------|------|------|------|------|------|------|---------|-------|--------|--------|------|-----|----------|")

for i, (idx, row) in enumerate(viable.head(15).iterrows(), 1):
    highlight = "🏆" if i == 1 else ("✅" if row['trades'] >= 30 and row['return_dd'] >= 5 else "")
    print(f"| {i:2d} | {row['offset_pct']:4.1f} | {row['max_wait']:4.0f} | {row['min_atr']:4.1f} | "
          f"{row['min_range96']:4.0f} | {row['sl_mult']:4.2f} | {row['tp_mult']:4.2f} | "
          f"{row['trade_rr']:4.2f} | {row['return']:+6.0f}% | {row['max_dd']:4.1f}% | "
          f"{row['return_dd']:6.2f}x | {row['trades']:3.0f} | {row['win_rate']:3.0f}% | "
          f"{row['tp_rate']:2.0f}% | {row['long_trades']:2.0f}/{row['short_trades']:2.0f} | {highlight}")

# Best
best = viable.iloc[0]

print("\n" + "=" * 80)
print("🏆 BEST CONFIGURATION:")
print("=" * 80)

print("\n📋 ENTRY:")
print(f"  LONG: RSI crosses above 35")
print(f"  SHORT: RSI crosses below 65")
print(f"  Filters:")
print(f"    - ATR% > {best['min_atr']:.1f}%")
print(f"    - 24h Range > {best['min_range96']:.0f}%")
print(f"  Entry: Limit order {best['offset_pct']:.1f}% offset")
print(f"  Wait: Max {best['max_wait']:.0f} bars for fill")

print("\n🎯 EXITS:")
print(f"  SL: {best['sl_mult']:.2f}x ATR")
print(f"  TP: {best['tp_mult']:.2f}x ATR")
print(f"  Trade R:R: {best['trade_rr']:.2f}:1")

print("\n💰 POSITION SIZING:")
print(f"  Risk: 12% per trade")
print(f"  Size = (Equity × 12%) / SL_distance%")

print("\n📊 PERFORMANCE (3 months):")
print(f"  Return:     {best['return']:+.2f}%")
print(f"  Max DD:     {best['max_dd']:.2f}%")
print(f"  Return/DD:  {best['return_dd']:.2f}x ⭐")
print(f"  Final:      ${best['final_equity']:,.2f}")

print("\n📈 STATISTICS:")
print(f"  Trades:     {best['trades']:.0f} ({best['trades']/3:.1f}/month)")
print(f"  Win Rate:   {best['win_rate']:.1f}%")
print(f"  TP Rate:    {best['tp_rate']:.1f}%")
print(f"  LONG:       {best['long_trades']:.0f} trades ({best['long_win']:.1f}% win)")
print(f"  SHORT:      {best['short_trades']:.0f} trades ({best['short_win']:.1f}% win)")

if best['trades'] >= 30 and best['return_dd'] >= 5:
    print("\n✅ MEETS ALL CRITERIA: 30+ trades AND 5+ R/DD!")
else:
    print(f"\n⚠️  Best available: {best['trades']:.0f} trades, {best['return_dd']:.2f}x R/DD")

print("\n" + "=" * 80)
