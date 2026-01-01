"""
1. Analyze losing trades - what makes them fail?
2. Test entry offset strategy with adjusted SL/TP
   Logic: For each X% offset, reduce SL by X% and increase TP by X%
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("PART 1: ANALYZE LOSING TRADES")
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

df['sma_20'] = df['close'].rolling(20).mean()
df['price_vs_sma20'] = ((df['close'] - df['sma_20']) / df['sma_20']) * 100

df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100

print("Indicators calculated")

# Collect trade data with detailed info
def collect_trades(df, long_rsi, short_rsi, min_atr_pct, min_range_96, sl_mult, tp_mult):
    trades = []
    position = None

    i = 300
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['atr_pct']) or pd.isna(row['range_96']):
            i += 1
            continue

        # Manage position
        if position is not None:
            bar = row

            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    position['exit_type'] = 'SL'
                    position['exit_price'] = position['sl_price']
                    position['exit_idx'] = i
                    position['pnl_pct'] = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    trades.append(position)
                    position = None
                    i += 1
                    continue

                if bar['high'] >= position['tp_price']:
                    position['exit_type'] = 'TP'
                    position['exit_price'] = position['tp_price']
                    position['exit_idx'] = i
                    position['pnl_pct'] = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    trades.append(position)
                    position = None
                    i += 1
                    continue

            elif position['direction'] == 'SHORT':
                if bar['high'] >= position['sl_price']:
                    position['exit_type'] = 'SL'
                    position['exit_price'] = position['sl_price']
                    position['exit_idx'] = i
                    position['pnl_pct'] = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    trades.append(position)
                    position = None
                    i += 1
                    continue

                if bar['low'] <= position['tp_price']:
                    position['exit_type'] = 'TP'
                    position['exit_price'] = position['tp_price']
                    position['exit_idx'] = i
                    position['pnl_pct'] = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    trades.append(position)
                    position = None
                    i += 1
                    continue

        # New entries
        if position is None and i > 0:
            prev_row = df.iloc[i-1]

            if row['atr_pct'] < min_atr_pct or row['range_96'] < min_range_96:
                i += 1
                continue

            if not pd.isna(prev_row['rsi']) and prev_row['rsi'] < long_rsi and row['rsi'] >= long_rsi:
                entry_price = row['close']
                sl_price = entry_price - (row['atr'] * sl_mult)
                tp_price = entry_price + (row['atr'] * tp_mult)

                position = {
                    'direction': 'LONG',
                    'entry': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'entry_rsi': row['rsi'],
                    'entry_atr_pct': row['atr_pct'],
                    'entry_price_vs_sma20': row['price_vs_sma20'],
                    'entry_range_96': row['range_96'],
                    'entry_idx': i
                }

            elif not pd.isna(prev_row['rsi']) and prev_row['rsi'] > short_rsi and row['rsi'] <= short_rsi:
                entry_price = row['close']
                sl_price = entry_price + (row['atr'] * sl_mult)
                tp_price = entry_price - (row['atr'] * tp_mult)

                position = {
                    'direction': 'SHORT',
                    'entry': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'entry_rsi': row['rsi'],
                    'entry_atr_pct': row['atr_pct'],
                    'entry_price_vs_sma20': row['price_vs_sma20'],
                    'entry_range_96': row['range_96'],
                    'entry_idx': i
                }

        i += 1

    return pd.DataFrame(trades)

# Collect trades
print("\nCollecting trades...")
trades_df = collect_trades(df, 35, 65, 1.5, 10.0, 2.0, 3.0)

print(f"Total trades: {len(trades_df)}")

winners = trades_df[trades_df['pnl_pct'] > 0]
losers = trades_df[trades_df['pnl_pct'] < 0]

print(f"Winners: {len(winners)} ({len(winners)/len(trades_df)*100:.1f}%)")
print(f"Losers: {len(losers)} ({len(losers)/len(trades_df)*100:.1f}%)")

# Analyze losers
print("\n" + "=" * 80)
print("WINNER vs LOSER COMPARISON:")
print("=" * 80)

metrics = ['entry_rsi', 'entry_atr_pct', 'entry_price_vs_sma20', 'entry_range_96']

print(f"\n{'Metric':<25} | {'Winners':<12} | {'Losers':<12} | {'Difference':<12}")
print("-" * 80)

for metric in metrics:
    w_avg = winners[metric].mean()
    l_avg = losers[metric].mean()
    diff = ((w_avg - l_avg) / abs(l_avg) * 100) if l_avg != 0 else 0
    print(f"{metric:<25} | {w_avg:>11.2f} | {l_avg:>11.2f} | {diff:>10.1f}%")

# By direction
print("\n" + "=" * 80)
print("BY DIRECTION:")
print("=" * 80)

for direction in ['LONG', 'SHORT']:
    dir_trades = trades_df[trades_df['direction'] == direction]
    dir_winners = dir_trades[dir_trades['pnl_pct'] > 0]
    dir_losers = dir_trades[dir_trades['pnl_pct'] < 0]

    print(f"\n{direction}:")
    print(f"  Total: {len(dir_trades)}")
    print(f"  Winners: {len(dir_winners)} ({len(dir_winners)/len(dir_trades)*100:.1f}%)")
    print(f"  Losers: {len(dir_losers)} ({len(dir_losers)/len(dir_trades)*100:.1f}%)")
    print(f"  Avg Win: {dir_winners['pnl_pct'].mean():.2f}%")
    print(f"  Avg Loss: {dir_losers['pnl_pct'].mean():.2f}%")

# Now test OFFSET strategy
print("\n" + "=" * 80)
print("PART 2: OFFSET ENTRY STRATEGY")
print("=" * 80)
print("\nLogic: For each X% offset, reduce SL by X*0.1 ATR and increase TP by X*0.1 ATR")
print("Example: 1% offset → SL becomes 1.9x ATR, TP becomes 3.1x ATR")

def backtest_offset(df, config):
    """
    Test offset entry with adjusted SL/TP
    """
    long_rsi = config['long_rsi']
    short_rsi = config['short_rsi']
    min_atr_pct = config['min_atr_pct']
    min_range_96 = config['min_range_96']
    base_sl_mult = config['base_sl_mult']
    base_tp_mult = config['base_tp_mult']
    offset_pct = config['offset_pct']
    risk_pct = config['risk_pct']
    max_wait_bars = config.get('max_wait_bars', 3)

    # Adjust SL/TP based on offset
    sl_adjustment = offset_pct * 0.1  # For each 1% offset, reduce SL by 0.1x ATR
    tp_adjustment = offset_pct * 0.1  # For each 1% offset, increase TP by 0.1x ATR

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

        # Check for limit order fills first
        if position is not None and 'limit_price' in position:
            bar = row
            bars_waited = i - position['signal_idx']

            if bars_waited > max_wait_bars:
                # Cancel unfilled order
                position = None
                i += 1
                continue

            # Check if limit filled
            filled = False
            if position['direction'] == 'LONG' and bar['low'] <= position['limit_price']:
                filled = True
            elif position['direction'] == 'SHORT' and bar['high'] >= position['limit_price']:
                filled = True

            if filled:
                # Convert to active position
                position['entry'] = position['limit_price']
                del position['limit_price']
                del position['signal_idx']

        # Manage active position (after fill)
        if position is not None and 'entry' in position:
            bar = row

            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    pnl = position['size'] * ((position['sl_price'] - position['entry']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'SL'})
                    position = None
                    i += 1
                    continue

                if bar['high'] >= position['tp_price']:
                    pnl = position['size'] * ((position['tp_price'] - position['entry']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'TP'})
                    position = None
                    i += 1
                    continue

            elif position['direction'] == 'SHORT':
                if bar['high'] >= position['sl_price']:
                    pnl = position['size'] * ((position['entry'] - position['sl_price']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'SL'})
                    position = None
                    i += 1
                    continue

                if bar['low'] <= position['tp_price']:
                    pnl = position['size'] * ((position['entry'] - position['tp_price']) / position['entry'])
                    pnl -= position['size'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'TP'})
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
                limit_price = signal_price * (1 - offset_pct / 100)  # Buy LOWER
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
                limit_price = signal_price * (1 + offset_pct / 100)  # Sell HIGHER
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

    return {
        'offset_pct': offset_pct,
        'sl_mult': sl_mult,
        'tp_mult': tp_mult,
        'trade_rr': tp_mult / sl_mult,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'tp_rate': (df_t['exit'] == 'TP').sum() / len(df_t) * 100,
        'final_equity': equity
    }

# Test offset strategies
print("\nTesting offset strategies...")
results = []

base_config = {
    'long_rsi': 35,
    'short_rsi': 65,
    'min_atr_pct': 1.5,
    'min_range_96': 10.0,
    'base_sl_mult': 2.0,
    'base_tp_mult': 3.0,
    'risk_pct': 12,
    'max_wait_bars': 3
}

# Test offsets from 0% to 3%
for offset in [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
    config = base_config.copy()
    config['offset_pct'] = offset

    res = backtest_offset(df, config)
    if res:
        results.append(res)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

print("\n" + "=" * 80)
print("OFFSET STRATEGY RESULTS:")
print("=" * 80)

print(f"\n| # | Offset | SL    | TP    | Trade R:R | Return  | DD     | R/DD    | Trades | Win%  | TP%  | Final $ |")
print("|---|--------|-------|-------|-----------|---------|--------|---------|--------|-------|------|---------|")

for i, (idx, row) in enumerate(results_df.iterrows(), 1):
    highlight = "🏆" if i == 1 else ""
    print(f"| {i} | {row['offset_pct']:5.1f}% | {row['sl_mult']:4.2f}x | {row['tp_mult']:4.2f}x | "
          f"{row['trade_rr']:8.2f}:1 | {row['return']:+6.0f}% | {row['max_dd']:5.1f}% | "
          f"{row['return_dd']:7.2f}x | {row['trades']:3.0f} | {row['win_rate']:4.1f}% | "
          f"{row['tp_rate']:3.0f}% | ${row['final_equity']:6.0f} | {highlight}")

best = results_df.iloc[0]

print("\n" + "=" * 80)
print("🏆 BEST OFFSET STRATEGY:")
print("=" * 80)
print(f"\nOffset: {best['offset_pct']:.1f}%")
print(f"Adjusted SL: {best['sl_mult']:.2f}x ATR")
print(f"Adjusted TP: {best['tp_mult']:.2f}x ATR")
print(f"Trade R:R: {best['trade_rr']:.2f}:1")
print(f"\nReturn: {best['return']:+.2f}%")
print(f"Max DD: {best['max_dd']:.2f}%")
print(f"Return/DD: {best['return_dd']:.2f}x ⭐")
print(f"Trades: {best['trades']:.0f}")
print(f"Win Rate: {best['win_rate']:.1f}%")
print(f"TP Rate: {best['tp_rate']:.1f}%")

print("\n" + "=" * 80)
