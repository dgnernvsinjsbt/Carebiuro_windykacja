"""
Backtest the top winner-based filters with proper position sizing
Calculate actual R/DD ratios to find the best

Top candidates:
1. ret_20 > 0%: 35 trades, 65.7% win
2. ret_5 > 0%: 50 trades, 52.0% win
3. ret_5 > 0.5%: 34 trades, 55.9% win
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("BACKTEST WINNER-BASED FILTERS")
print("Test top 3 filters with real position sizing")
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

df['ret_5'] = (df['close'] / df['close'].shift(5) - 1) * 100
df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

print("Indicators calculated")

def backtest_filter(df, filter_name, filter_func):
    """
    Backtest with a specific filter function
    """
    trades = []
    equity = 100.0
    position = None

    i = 300
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_5']) or pd.isna(row['ret_20']):
            i += 1
            continue

        # Manage position
        if position is not None:
            bar = row

            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl = position['size'] * ((position['sl_price'] - position['entry']) / position['entry'])
                    pnl -= position['size'] * 0.001  # fees
                    equity += pnl
                    trades.append({
                        'pnl': pnl,
                        'pnl_pct': ((position['sl_price'] - position['entry']) / position['entry']) * 100,
                        'equity': equity,
                        'exit': 'SL',
                        'direction': 'LONG',
                        'entry_idx': position['entry_idx'],
                        'exit_idx': i
                    })
                    position = None
                    i += 1
                    continue

                if bar['high'] >= position['tp_price']:
                    pnl = position['size'] * ((position['tp_price'] - position['entry']) / position['entry'])
                    pnl -= position['size'] * 0.001  # fees
                    equity += pnl
                    trades.append({
                        'pnl': pnl,
                        'pnl_pct': ((position['tp_price'] - position['entry']) / position['entry']) * 100,
                        'equity': equity,
                        'exit': 'TP',
                        'direction': 'LONG',
                        'entry_idx': position['entry_idx'],
                        'exit_idx': i
                    })
                    position = None
                    i += 1
                    continue

            elif position['direction'] == 'SHORT':
                if bar['high'] >= position['sl_price']:
                    pnl = position['size'] * ((position['entry'] - position['sl_price']) / position['entry'])
                    pnl -= position['size'] * 0.001  # fees
                    equity += pnl
                    trades.append({
                        'pnl': pnl,
                        'pnl_pct': ((position['entry'] - position['sl_price']) / position['entry']) * 100,
                        'equity': equity,
                        'exit': 'SL',
                        'direction': 'SHORT',
                        'entry_idx': position['entry_idx'],
                        'exit_idx': i
                    })
                    position = None
                    i += 1
                    continue

                if bar['low'] <= position['tp_price']:
                    pnl = position['size'] * ((position['entry'] - position['tp_price']) / position['entry'])
                    pnl -= position['size'] * 0.001  # fees
                    equity += pnl
                    trades.append({
                        'pnl': pnl,
                        'pnl_pct': ((position['entry'] - position['tp_price']) / position['entry']) * 100,
                        'equity': equity,
                        'exit': 'TP',
                        'direction': 'SHORT',
                        'entry_idx': position['entry_idx'],
                        'exit_idx': i
                    })
                    position = None
                    i += 1
                    continue

        # New entries - RSI 35/65 + filter
        if position is None and i > 0:
            prev_row = df.iloc[i-1]

            # Apply filter
            if not filter_func(row):
                i += 1
                continue

            if not pd.isna(prev_row['rsi']):
                # LONG signal
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    entry_price = row['close']
                    sl_price = entry_price - (row['atr'] * 2.0)
                    tp_price = entry_price + (row['atr'] * 3.0)

                    sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100
                    risk_dollars = equity * 0.12  # 12% risk
                    size = risk_dollars / (sl_distance_pct / 100)

                    position = {
                        'direction': 'LONG',
                        'entry': entry_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size,
                        'entry_idx': i
                    }

                # SHORT signal
                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    entry_price = row['close']
                    sl_price = entry_price + (row['atr'] * 2.0)
                    tp_price = entry_price - (row['atr'] * 3.0)

                    sl_distance_pct = abs((sl_price - entry_price) / entry_price) * 100
                    risk_dollars = equity * 0.12  # 12% risk
                    size = risk_dollars / (sl_distance_pct / 100)

                    position = {
                        'direction': 'SHORT',
                        'entry': entry_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'size': size,
                        'entry_idx': i
                    }

        i += 1

    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100

    # Calculate max drawdown
    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    max_dd = ((eq - running_max) / running_max * 100).min()

    win_rate = (df_t['pnl'] > 0).sum() / len(df_t) * 100
    tp_rate = (df_t['exit'] == 'TP').sum() / len(df_t) * 100

    return {
        'filter': filter_name,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'final_equity': equity,
        'avg_pnl_pct': df_t['pnl_pct'].mean()
    }

# Test filters
filters = [
    ('ret_20 > 0%', lambda row: row['ret_20'] > 0),
    ('ret_5 > 0%', lambda row: row['ret_5'] > 0),
    ('ret_5 > 0.5%', lambda row: row['ret_5'] > 0.5),
    ('Range96 > 12%', lambda row: row['range_96'] > 12 if 'range_96' in row.index and not pd.isna(row['range_96']) else False),
    ('Range96 > 15%', lambda row: row['range_96'] > 15 if 'range_96' in row.index and not pd.isna(row['range_96']) else False),
]

# Need to add range_96 for last 2 filters
df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100

print("\nTesting filters...\n")

results = []
for filter_name, filter_func in filters:
    res = backtest_filter(df, filter_name, filter_func)
    if res:
        results.append(res)
        print(f"✓ {filter_name}: {res['trades']} trades, {res['return']:+.1f}% return, {res['max_dd']:.1f}% DD, {res['return_dd']:.2f}x R/DD")

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

print("\n" + "=" * 80)
print("RESULTS (sorted by R/DD):")
print("=" * 80)

print(f"\n| # | Filter | Trades | Return | DD    | R/DD  | Win% | TP%  | Avg P | Final $  |")
print("|---|--------|--------|--------|-------|-------|------|------|-------|----------|")

for i, (idx, row) in enumerate(results_df.iterrows(), 1):
    highlight = "🏆" if i == 1 else ("✅" if row['trades'] >= 35 and row['return_dd'] >= 4 else "")
    print(f"| {i:2d} | {row['filter']:<14s} | {row['trades']:3.0f} | "
          f"{row['return']:+6.1f}% | {row['max_dd']:5.1f}% | {row['return_dd']:5.2f}x | "
          f"{row['win_rate']:4.1f}% | {row['tp_rate']:3.0f}% | {row['avg_pnl_pct']:+5.2f}% | "
          f"${row['final_equity']:6.2f} | {highlight}")

# Best
best = results_df.iloc[0]

print("\n" + "=" * 80)
print("🏆 BEST FILTER:")
print("=" * 80)

print(f"\nFilter: {best['filter']}")
print(f"\n📊 PERFORMANCE (3 months):")
print(f"  Return:     {best['return']:+.2f}%")
print(f"  Max DD:     {best['max_dd']:.2f}%")
print(f"  Return/DD:  {best['return_dd']:.2f}x")
print(f"  Final:      ${best['final_equity']:,.2f}")

print(f"\n📈 STATISTICS:")
print(f"  Trades:     {best['trades']:.0f} ({best['trades']/3:.1f}/month)")
print(f"  Win Rate:   {best['win_rate']:.1f}%")
print(f"  TP Rate:    {best['tp_rate']:.1f}%")
print(f"  Avg P&L:    {best['avg_pnl_pct']:+.2f}%")

print(f"\n📋 STRATEGY:")
print(f"  Entry: RSI crosses 35 (LONG) or 65 (SHORT)")
print(f"  Filter: {best['filter']}")
print(f"  SL: 2.0x ATR")
print(f"  TP: 3.0x ATR")
print(f"  Risk: 12% per trade")

if best['trades'] >= 40 and best['return_dd'] >= 5:
    print(f"\n✅ MEETS ALL TARGETS: {best['trades']:.0f} trades AND {best['return_dd']:.2f}x R/DD!")
elif best['trades'] >= 35 and best['return_dd'] >= 4:
    print(f"\n✅ CLOSE: {best['trades']:.0f} trades (35+) with {best['return_dd']:.2f}x R/DD (4+)")
else:
    print(f"\n⚠️  Trades: {best['trades']:.0f} (target: 40+)")
    print(f"   R/DD: {best['return_dd']:.2f}x (target: 5+)")

results_df.to_csv('winner_filter_backtest_results.csv', index=False)
print(f"\n💾 Saved results to: winner_filter_backtest_results.csv")

print("\n" + "=" * 80)
