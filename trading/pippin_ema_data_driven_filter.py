"""
PIPPIN EMA Cross 10x TP - DATA-DRIVEN FILTERS
Based on winner/loser analysis:
- AVOID: High consecutive bars (momentum chasers = losers)
- AVOID: High ATR/volume (late entries = losers)
- PREFER: Fresh crosses (low consecutive) + strong body
- PREFER: Best hours (17, 12, 23, 9, 1, 11)
"""

import pandas as pd
import numpy as np

df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("="*90)
print("PIPPIN EMA CROSS 10x TP - DATA-DRIVEN FILTERS")
print("="*90)
print()

# Calculate indicators
df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()

df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(window=14).mean()
df['atr_avg'] = df['atr'].rolling(window=20).mean()

df['volume_avg'] = df['volume'].rolling(window=20).mean()

df['ema_9_prev'] = df['ema_9'].shift(1)
df['ema_21_prev'] = df['ema_21'].shift(1)

df['cross_up'] = (df['ema_9'] > df['ema_21']) & (df['ema_9_prev'] <= df['ema_21_prev'])
df['cross_down'] = (df['ema_9'] < df['ema_21']) & (df['ema_9_prev'] >= df['ema_21_prev'])

# Features
df['hour'] = df['timestamp'].dt.hour
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['volume_ratio'] = df['volume'] / df['volume_avg']
df['atr_ratio'] = df['atr'] / df['atr_avg']

# Consecutive bars
df['consecutive_ups'] = 0
df['consecutive_downs'] = 0

for i in range(1, len(df)):
    if df.loc[i, 'close'] > df.loc[i, 'open']:
        df.loc[i, 'consecutive_ups'] = df.loc[i-1, 'consecutive_ups'] + 1
        df.loc[i, 'consecutive_downs'] = 0
    elif df.loc[i, 'close'] < df.loc[i, 'open']:
        df.loc[i, 'consecutive_downs'] = df.loc[i-1, 'consecutive_downs'] + 1
        df.loc[i, 'consecutive_ups'] = 0

print(f"Total EMA crossovers: {df['cross_up'].sum() + df['cross_down'].sum()}")
print()

# Test configurations based on analysis
configs = [
    {
        'name': 'Avoid Momentum Chasers',
        'description': 'Consecutive bars <= 1 (avoid late entries)',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['consecutive_ups'] <= 1,
        'short_filter': lambda row: row['consecutive_downs'] <= 1,
    },
    {
        'name': 'Fresh Crosses Only',
        'description': 'Consecutive = 0 (brand new trend)',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['consecutive_ups'] == 0,
        'short_filter': lambda row: row['consecutive_downs'] == 0,
    },
    {
        'name': 'Avoid High ATR',
        'description': 'ATR < 1.0x avg (calmer entries like winners)',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['atr_ratio'] < 1.0,
        'short_filter': lambda row: row['atr_ratio'] < 1.0,
    },
    {
        'name': 'Strong Body Filter',
        'description': 'Body >= 1.5% (28.6% TP rate)',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['body_pct'] >= 1.5,
        'short_filter': lambda row: row['body_pct'] >= 1.5,
    },
    {
        'name': 'Best Hours Only',
        'description': 'Hours: 17, 12, 23, 9, 1, 11 (>25% TP rate)',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['hour'] in [17, 12, 23, 9, 1, 11],
        'short_filter': lambda row: row['hour'] in [17, 12, 23, 9, 1, 11],
    },
    {
        'name': 'Low Consecutive + Strong Body',
        'description': 'Consec <= 1 + Body >= 0.8%',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['consecutive_ups'] <= 1 and row['body_pct'] >= 0.8,
        'short_filter': lambda row: row['consecutive_downs'] <= 1 and row['body_pct'] >= 0.8,
    },
    {
        'name': 'Calm Entry + Strong Body',
        'description': 'ATR < 1.0x + Body >= 1.0%',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['atr_ratio'] < 1.0 and row['body_pct'] >= 1.0,
        'short_filter': lambda row: row['atr_ratio'] < 1.0 and row['body_pct'] >= 1.0,
    },
    {
        'name': 'Triple Anti-Chase',
        'description': 'Consec <= 1 + ATR < 1.0x + Vol < 1.2x',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['consecutive_ups'] <= 1 and row['atr_ratio'] < 1.0 and row['volume_ratio'] < 1.2,
        'short_filter': lambda row: row['consecutive_downs'] <= 1 and row['atr_ratio'] < 1.0 and row['volume_ratio'] < 1.2,
    },
    {
        'name': 'Best Hour + Low Consec',
        'description': 'Best hours + Consecutive <= 1',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['hour'] in [17, 12, 23, 9, 1, 11] and row['consecutive_ups'] <= 1,
        'short_filter': lambda row: row['hour'] in [17, 12, 23, 9, 1, 11] and row['consecutive_downs'] <= 1,
    },
    {
        'name': 'Mega Winner Profile',
        'description': 'Consec <= 1 + ATR < 0.95x + Body >= 0.8%',
        'sl_mult': 1.5,
        'tp_mult': 10.0,
        'long_filter': lambda row: row['consecutive_ups'] <= 1 and row['atr_ratio'] < 0.95 and row['body_pct'] >= 0.8,
        'short_filter': lambda row: row['consecutive_downs'] <= 1 and row['atr_ratio'] < 0.95 and row['body_pct'] >= 0.8,
    },
]

MAX_HOLD_BARS = 120
FEE_PCT = 0.10

results = []

for config in configs:
    print(f"🧪 Testing: {config['name']}")
    print(f"   {config['description']}")

    trades = []
    in_position = False
    position = None

    for i in range(50, len(df)):
        row = df.iloc[i]

        if in_position:
            bars_held = i - position['entry_idx']
            current_price = row['close']

            hit_sl = False
            hit_tp = False
            time_exit = False

            if position['direction'] == 'LONG':
                if current_price <= position['stop_loss']:
                    hit_sl = True
                    exit_price = position['stop_loss']
                elif current_price >= position['take_profit']:
                    hit_tp = True
                    exit_price = position['take_profit']
                elif bars_held >= MAX_HOLD_BARS:
                    time_exit = True
                    exit_price = current_price
            else:
                if current_price >= position['stop_loss']:
                    hit_sl = True
                    exit_price = position['stop_loss']
                elif current_price <= position['take_profit']:
                    hit_tp = True
                    exit_price = position['take_profit']
                elif bars_held >= MAX_HOLD_BARS:
                    time_exit = True
                    exit_price = current_price

            if hit_sl or hit_tp or time_exit:
                if position['direction'] == 'LONG':
                    pnl_pct = ((exit_price / position['entry_price']) - 1) * 100
                else:
                    pnl_pct = ((position['entry_price'] / exit_price) - 1) * 100

                pnl_pct -= FEE_PCT

                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': row['timestamp'],
                    'direction': position['direction'],
                    'pnl_pct': pnl_pct,
                    'exit_reason': 'SL' if hit_sl else ('TP' if hit_tp else 'Time'),
                })

                in_position = False
                position = None

        if not in_position:
            if row['cross_up'] and config['long_filter'](row):
                entry_price = row['close']
                atr = row['atr']

                position = {
                    'entry_idx': i,
                    'entry_time': row['timestamp'],
                    'direction': 'LONG',
                    'entry_price': entry_price,
                    'stop_loss': entry_price - (config['sl_mult'] * atr),
                    'take_profit': entry_price + (config['tp_mult'] * atr),
                }
                in_position = True

            elif row['cross_down'] and config['short_filter'](row):
                entry_price = row['close']
                atr = row['atr']

                position = {
                    'entry_idx': i,
                    'entry_time': row['timestamp'],
                    'direction': 'SHORT',
                    'entry_price': entry_price,
                    'stop_loss': entry_price + (config['sl_mult'] * atr),
                    'take_profit': entry_price - (config['tp_mult'] * atr),
                }
                in_position = True

    if len(trades) == 0:
        print(f"   ❌ No trades\n")
        continue

    trades_df = pd.DataFrame(trades)

    total_return = trades_df['pnl_pct'].sum()
    num_trades = len(trades_df)
    winners = trades_df[trades_df['pnl_pct'] > 0]
    losers = trades_df[trades_df['pnl_pct'] <= 0]
    win_rate = (len(winners) / num_trades * 100)

    trades_df['cumulative_pnl'] = trades_df['pnl_pct'].cumsum()
    trades_df['running_max'] = trades_df['cumulative_pnl'].expanding().max()
    trades_df['drawdown'] = trades_df['cumulative_pnl'] - trades_df['running_max']
    max_dd = trades_df['drawdown'].min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    tp_count = len(trades_df[trades_df['exit_reason'] == 'TP'])
    sl_count = len(trades_df[trades_df['exit_reason'] == 'SL'])

    tp_rate = (tp_count / num_trades * 100)
    sl_rate = (sl_count / num_trades * 100)

    print(f"   Return: {total_return:+.2f}% | R/DD: {return_dd:.2f}x | Trades: {num_trades}")
    print(f"   Win Rate: {win_rate:.1f}% | TP: {tp_rate:.1f}% | SL: {sl_rate:.1f}%")
    print()

    results.append({
        'config': config['name'],
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'trades': num_trades,
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'sl_rate': sl_rate,
    })

print("\n" + "="*90)
print("SUMMARY - DATA-DRIVEN FILTERS")
print("="*90)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)
results_df.to_csv('results/pippin_ema_data_driven_summary.csv', index=False)

print("\nRanked by R/DD:")
print(results_df[['config', 'return', 'return_dd', 'tp_rate', 'sl_rate', 'trades']].to_string(index=False))

print("\n" + "="*90)
if len(results_df) > 0:
    best = results_df.iloc[0]
    print("🎯 BEST DATA-DRIVEN CONFIG:")
    print(f"   {best['config']}")
    print(f"   Return: {best['return']:+.2f}% | R/DD: {best['return_dd']:.2f}x")
    print(f"   Trades: {int(best['trades'])} (vs 184 unfiltered)")
    print(f"   TP Rate: {best['tp_rate']:.1f}% (vs 13.0% unfiltered)")
    print(f"   SL Rate: {best['sl_rate']:.1f}% (vs 73.9% unfiltered)")

    print("\n📊 vs UNFILTERED:")
    print(f"   Trades: 184 → {int(best['trades'])} ({((1-best['trades']/184)*100):.1f}% fewer)")
    print(f"   R/DD: 2.18x → {best['return_dd']:.2f}x ({best['return_dd']-2.18:+.2f}x)")
    print(f"   SL Rate: 73.9% → {best['sl_rate']:.1f}% ({best['sl_rate']-73.9:+.1f}pp)")

    if best['return_dd'] > 2.18:
        print(f"\n   🎉 IMPROVED R/DD by {((best['return_dd']/2.18)-1)*100:+.1f}%!")

    if best['return_dd'] >= 3.0:
        print(f"\n   ✅ DEPLOYMENT READY! R/DD {best['return_dd']:.2f}x >= 3.0x threshold")

print("="*90)
