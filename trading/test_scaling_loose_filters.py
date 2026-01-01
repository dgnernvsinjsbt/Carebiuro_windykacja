"""
Test scaling strategy with MUCH looser filters
Goal: 50-60+ trades with scaling to protect us
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("SCALING STRATEGY WITH LOOSE FILTERS")
print("Let scaling protect us, not strict filters!")
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

def backtest_scaling(df, config):
    """
    Scaling strategy:
    - 40% initial entry
    - +30% at 0.5 ATR against
    - +30% at 1.0 ATR against
    - Take 30% profit at 1.5x ATR
    - Take 30% profit at 2.5x ATR
    - Let 40% run to 3.5x ATR or SL at 2.5x ATR
    """
    long_rsi = config['long_rsi']
    short_rsi = config['short_rsi']
    min_atr_pct = config.get('min_atr_pct', 0)
    min_range_96 = config.get('min_range_96', 0)
    risk_pct = config['risk_pct']

    trades = []
    equity = 100.0
    position = None

    i = 300
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            i += 1
            continue

        # Manage position
        if position is not None:
            bar = row

            if position['direction'] == 'LONG':
                current_price = bar['close']

                # Check scale-ins
                if position['scales'] < 3:
                    if position['scales'] == 1 and bar['low'] <= position['scale_in_prices'][0]:
                        # Scale in #1
                        add_cost = position['scale_in_prices'][0] * position['scale_sizes'][1]
                        total_cost = position['avg_entry'] * position['total_invested'] + add_cost
                        position['total_invested'] += position['scale_sizes'][1]
                        position['avg_entry'] = total_cost / position['total_invested']
                        position['scales'] = 2
                    elif position['scales'] == 2 and bar['low'] <= position['scale_in_prices'][1]:
                        # Scale in #2
                        add_cost = position['scale_in_prices'][1] * position['scale_sizes'][2]
                        total_cost = position['avg_entry'] * position['total_invested'] + add_cost
                        position['total_invested'] += position['scale_sizes'][2]
                        position['avg_entry'] = total_cost / position['total_invested']
                        position['scales'] = 3

                # Check exits
                # SL (based on avg entry after scaling)
                final_sl = position['avg_entry'] - (position['entry_atr'] * 2.5)
                if bar['low'] <= final_sl:
                    pnl_pct = ((final_sl - position['avg_entry']) / position['avg_entry']) * 100
                    pnl = position['total_invested'] * (pnl_pct / 100)
                    pnl -= position['total_invested'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'SL', 'scales': position['scales']})
                    position = None
                    i += 1
                    continue

                # Partial TPs
                tp1 = position['avg_entry'] + (position['entry_atr'] * 1.5)
                tp2 = position['avg_entry'] + (position['entry_atr'] * 2.5)
                tp3 = position['avg_entry'] + (position['entry_atr'] * 3.5)

                if position['remaining_pct'] > 0.4 and bar['high'] >= tp1:
                    # Take 30% profit at TP1
                    exit_size = position['total_invested'] * 0.3
                    pnl_pct = ((tp1 - position['avg_entry']) / position['avg_entry']) * 100
                    pnl = exit_size * (pnl_pct / 100) - exit_size * 0.001
                    equity += pnl
                    position['remaining_pct'] -= 0.3

                if position['remaining_pct'] > 0.4 and bar['high'] >= tp2:
                    # Take 30% profit at TP2
                    exit_size = position['total_invested'] * 0.3
                    pnl_pct = ((tp2 - position['avg_entry']) / position['avg_entry']) * 100
                    pnl = exit_size * (pnl_pct / 100) - exit_size * 0.001
                    equity += pnl
                    position['remaining_pct'] -= 0.3

                if position['remaining_pct'] > 0 and bar['high'] >= tp3:
                    # Final 40% at TP3
                    exit_size = position['total_invested'] * position['remaining_pct']
                    pnl_pct = ((tp3 - position['avg_entry']) / position['avg_entry']) * 100
                    pnl = exit_size * (pnl_pct / 100) - exit_size * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'TP', 'scales': position['scales']})
                    position = None
                    i += 1
                    continue

            elif position['direction'] == 'SHORT':
                current_price = bar['close']

                # Check scale-ins
                if position['scales'] < 3:
                    if position['scales'] == 1 and bar['high'] >= position['scale_in_prices'][0]:
                        add_cost = position['scale_in_prices'][0] * position['scale_sizes'][1]
                        total_cost = position['avg_entry'] * position['total_invested'] + add_cost
                        position['total_invested'] += position['scale_sizes'][1]
                        position['avg_entry'] = total_cost / position['total_invested']
                        position['scales'] = 2
                    elif position['scales'] == 2 and bar['high'] >= position['scale_in_prices'][1]:
                        add_cost = position['scale_in_prices'][1] * position['scale_sizes'][2]
                        total_cost = position['avg_entry'] * position['total_invested'] + add_cost
                        position['total_invested'] += position['scale_sizes'][2]
                        position['avg_entry'] = total_cost / position['total_invested']
                        position['scales'] = 3

                # Check exits
                final_sl = position['avg_entry'] + (position['entry_atr'] * 2.5)
                if bar['high'] >= final_sl:
                    pnl_pct = ((position['avg_entry'] - final_sl) / position['avg_entry']) * 100
                    pnl = position['total_invested'] * (pnl_pct / 100)
                    pnl -= position['total_invested'] * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'SL', 'scales': position['scales']})
                    position = None
                    i += 1
                    continue

                tp1 = position['avg_entry'] - (position['entry_atr'] * 1.5)
                tp2 = position['avg_entry'] - (position['entry_atr'] * 2.5)
                tp3 = position['avg_entry'] - (position['entry_atr'] * 3.5)

                if position['remaining_pct'] > 0.4 and bar['low'] <= tp1:
                    exit_size = position['total_invested'] * 0.3
                    pnl_pct = ((position['avg_entry'] - tp1) / position['avg_entry']) * 100
                    pnl = exit_size * (pnl_pct / 100) - exit_size * 0.001
                    equity += pnl
                    position['remaining_pct'] -= 0.3

                if position['remaining_pct'] > 0.4 and bar['low'] <= tp2:
                    exit_size = position['total_invested'] * 0.3
                    pnl_pct = ((position['avg_entry'] - tp2) / position['avg_entry']) * 100
                    pnl = exit_size * (pnl_pct / 100) - exit_size * 0.001
                    equity += pnl
                    position['remaining_pct'] -= 0.3

                if position['remaining_pct'] > 0 and bar['low'] <= tp3:
                    exit_size = position['total_invested'] * position['remaining_pct']
                    pnl_pct = ((position['avg_entry'] - tp3) / position['avg_entry']) * 100
                    pnl = exit_size * (pnl_pct / 100) - exit_size * 0.001
                    equity += pnl
                    trades.append({'pnl': pnl, 'equity': equity, 'exit': 'TP', 'scales': position['scales']})
                    position = None
                    i += 1
                    continue

        # New entries
        if position is None and i > 0:
            prev_row = df.iloc[i-1]

            # Apply filters if configured
            if min_atr_pct > 0 and (pd.isna(row['atr_pct']) or row['atr_pct'] < min_atr_pct):
                i += 1
                continue

            if min_range_96 > 0 and (pd.isna(row['range_96']) or row['range_96'] < min_range_96):
                i += 1
                continue

            if not pd.isna(prev_row['rsi']) and prev_row['rsi'] < long_rsi and row['rsi'] >= long_rsi:
                # LONG entry
                entry_price = row['close']
                entry_atr = row['atr']

                # Calculate initial position size (40% of total)
                risk_dollars = equity * (risk_pct / 100)
                initial_sl_distance = entry_atr * 2.5
                sl_distance_pct = (initial_sl_distance / entry_price) * 100
                total_position = risk_dollars / (sl_distance_pct / 100)
                initial_size = total_position * 0.4

                # Scale-in prices
                scale1_price = entry_price - (entry_atr * 0.5)
                scale2_price = entry_price - (entry_atr * 1.0)

                position = {
                    'direction': 'LONG',
                    'entry': entry_price,
                    'avg_entry': entry_price,
                    'entry_atr': entry_atr,
                    'total_invested': initial_size,
                    'scale_in_prices': [scale1_price, scale2_price],
                    'scale_sizes': [initial_size, total_position * 0.3, total_position * 0.3],
                    'scales': 1,
                    'remaining_pct': 1.0
                }

            elif not pd.isna(prev_row['rsi']) and prev_row['rsi'] > short_rsi and row['rsi'] <= short_rsi:
                # SHORT entry
                entry_price = row['close']
                entry_atr = row['atr']

                risk_dollars = equity * (risk_pct / 100)
                initial_sl_distance = entry_atr * 2.5
                sl_distance_pct = (initial_sl_distance / entry_price) * 100
                total_position = risk_dollars / (sl_distance_pct / 100)
                initial_size = total_position * 0.4

                scale1_price = entry_price + (entry_atr * 0.5)
                scale2_price = entry_price + (entry_atr * 1.0)

                position = {
                    'direction': 'SHORT',
                    'entry': entry_price,
                    'avg_entry': entry_price,
                    'entry_atr': entry_atr,
                    'total_invested': initial_size,
                    'scale_in_prices': [scale1_price, scale2_price],
                    'scale_sizes': [initial_size, total_position * 0.3, total_position * 0.3],
                    'scales': 1,
                    'remaining_pct': 1.0
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
        'long_rsi': long_rsi,
        'short_rsi': short_rsi,
        'min_atr': min_atr_pct,
        'min_range96': min_range_96,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'avg_scales': df_t['scales'].mean(),
        'final_equity': equity
    }

# Test with different filter levels
print("\nTesting filter combinations...")
results = []

configs = [
    # NO FILTERS - pure RSI
    {'long_rsi': 35, 'short_rsi': 65, 'min_atr_pct': 0, 'min_range_96': 0, 'risk_pct': 12},
    {'long_rsi': 30, 'short_rsi': 70, 'min_atr_pct': 0, 'min_range_96': 0, 'risk_pct': 12},
    {'long_rsi': 40, 'short_rsi': 60, 'min_atr_pct': 0, 'min_range_96': 0, 'risk_pct': 12},

    # MINIMAL FILTERS
    {'long_rsi': 35, 'short_rsi': 65, 'min_atr_pct': 1.0, 'min_range_96': 0, 'risk_pct': 12},
    {'long_rsi': 35, 'short_rsi': 65, 'min_atr_pct': 0, 'min_range_96': 5, 'risk_pct': 12},

    # LIGHT FILTERS
    {'long_rsi': 35, 'short_rsi': 65, 'min_atr_pct': 1.0, 'min_range_96': 5, 'risk_pct': 12},
    {'long_rsi': 30, 'short_rsi': 70, 'min_atr_pct': 1.0, 'min_range_96': 5, 'risk_pct': 12},
]

for config in configs:
    res = backtest_scaling(df, config)
    if res:
        results.append(res)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

print("\n" + "=" * 80)
print("RESULTS (sorted by R/DD):")
print("=" * 80)

print(f"\n| # | RSI L/S | ATR% | R96% | Return  | DD     | R/DD   | Trades | Win%  | Avg Scales | Final $  |")
print("|---|---------|------|------|---------|--------|--------|--------|-------|------------|----------|")

for i, (idx, row) in enumerate(results_df.iterrows(), 1):
    highlight = "🏆" if i == 1 else ("✅" if row['trades'] >= 50 and row['return_dd'] >= 5 else "")
    print(f"| {i} | {row['long_rsi']:2.0f}/{row['short_rsi']:2.0f} | {row['min_atr']:4.1f} | "
          f"{row['min_range96']:4.0f} | {row['return']:+6.0f}% | {row['max_dd']:5.1f}% | "
          f"{row['return_dd']:6.2f}x | {row['trades']:3.0f} | {row['win_rate']:4.1f}% | "
          f"{row['avg_scales']:10.2f} | ${row['final_equity']:7.0f} | {highlight}")

best = results_df.iloc[0]

print("\n" + "=" * 80)
print("🏆 BEST CONFIG:")
print("=" * 80)
print(f"\nRSI: {best['long_rsi']:.0f}/{best['short_rsi']:.0f}")
print(f"Filters: ATR>{best['min_atr']:.1f}%, Range96>{best['min_range96']:.0f}%")
print(f"\nReturn: {best['return']:+.2f}%")
print(f"Max DD: {best['max_dd']:.2f}%")
print(f"R/DD: {best['return_dd']:.2f}x")
print(f"Trades: {best['trades']:.0f} ({best['trades']/3:.1f}/month)")
print(f"Win Rate: {best['win_rate']:.1f}%")
print(f"Avg Scales: {best['avg_scales']:.2f}")

if best['trades'] >= 50 and best['return_dd'] >= 5:
    print("\n✅ SUCCESS: 50+ trades AND 5+ R/DD!")
elif best['trades'] >= 50:
    print(f"\n⚠️  Have 50+ trades but R/DD only {best['return_dd']:.2f}x")
else:
    print(f"\n⚠️  R/DD is {best['return_dd']:.2f}x but only {best['trades']:.0f} trades")

print("\n" + "=" * 80)
