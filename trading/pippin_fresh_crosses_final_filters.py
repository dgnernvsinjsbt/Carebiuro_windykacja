"""
PIPPIN Fresh Crosses - Apply Data-Driven Filters
Test filters discovered from 64-trade analysis:
1. RSI >= 55 (highest TP rate)
2. EMA50 Distance <= 0.12% (calm entries)
3. Body <= 0.06% (tiny bodies like doji)
4. Combinations
"""

import pandas as pd
import numpy as np

df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("="*90)
print("PIPPIN FRESH CROSSES - FINAL FILTERS (Data-Driven)")
print("="*90)
print()

# Calculate indicators
df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(window=14).mean()

delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

df['ema_9_prev'] = df['ema_9'].shift(1)
df['ema_21_prev'] = df['ema_21'].shift(1)

df['cross_up'] = (df['ema_9'] > df['ema_21']) & (df['ema_9_prev'] <= df['ema_21_prev'])
df['cross_down'] = (df['ema_9'] < df['ema_21']) & (df['ema_9_prev'] >= df['ema_21_prev'])

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

# Additional features
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['ema50_dist_pct'] = ((df['close'] - df['ema_50']) / df['ema_50'] * 100).abs()

# Test configurations
configs = [
    {
        'name': 'Baseline (Fresh Crosses)',
        'description': 'No additional filters',
        'filter': lambda row: True,
    },
    {
        'name': 'RSI >= 55',
        'description': '33.3% TP rate (vs 17.2% baseline)',
        'filter': lambda row: row['rsi'] >= 55,
    },
    {
        'name': 'EMA50 Dist <= 0.12%',
        'description': '28.6% TP rate (calm entries)',
        'filter': lambda row: row['ema50_dist_pct'] <= 0.12,
    },
    {
        'name': 'Body <= 0.06%',
        'description': '27.3% TP rate (tiny body doji-like)',
        'filter': lambda row: row['body_pct'] <= 0.06,
    },
    {
        'name': 'RSI >= 55 + EMA50 Dist <= 0.12%',
        'description': 'Combo: High RSI + Calm entry',
        'filter': lambda row: row['rsi'] >= 55 and row['ema50_dist_pct'] <= 0.12,
    },
    {
        'name': 'RSI >= 55 + Body <= 0.06%',
        'description': 'Combo: High RSI + Tiny body',
        'filter': lambda row: row['rsi'] >= 55 and row['body_pct'] <= 0.06,
    },
    {
        'name': 'EMA50 Dist <= 0.12% + Body <= 0.06%',
        'description': 'Combo: Calm + Tiny body',
        'filter': lambda row: row['ema50_dist_pct'] <= 0.12 and row['body_pct'] <= 0.06,
    },
    {
        'name': 'Triple Filter',
        'description': 'RSI >= 55 + EMA50 <= 0.12% + Body <= 0.06%',
        'filter': lambda row: row['rsi'] >= 55 and row['ema50_dist_pct'] <= 0.12 and row['body_pct'] <= 0.06,
    },
    {
        'name': 'RSI >= 50 (Looser)',
        'description': 'More trades than RSI >= 55',
        'filter': lambda row: row['rsi'] >= 50,
    },
    {
        'name': 'EMA50 Dist <= 0.2% (Looser)',
        'description': 'More trades than 0.12%',
        'filter': lambda row: row['ema50_dist_pct'] <= 0.2,
    },
]

SL_MULT = 1.5
TP_MULT = 10.0
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

        # Exit logic
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
                    'pnl_pct': pnl_pct,
                    'exit_reason': 'SL' if hit_sl else ('TP' if hit_tp else 'Time'),
                })

                in_position = False
                position = None

        # Entry logic - FRESH CROSSES + FILTER
        if not in_position:
            if row['cross_up'] and row['consecutive_ups'] == 0 and config['filter'](row):
                entry_price = row['close']
                atr = row['atr']

                position = {
                    'entry_idx': i,
                    'direction': 'LONG',
                    'entry_price': entry_price,
                    'stop_loss': entry_price - (SL_MULT * atr),
                    'take_profit': entry_price + (TP_MULT * atr),
                }
                in_position = True

            elif row['cross_down'] and row['consecutive_downs'] == 0 and config['filter'](row):
                entry_price = row['close']
                atr = row['atr']

                position = {
                    'entry_idx': i,
                    'direction': 'SHORT',
                    'entry_price': entry_price,
                    'stop_loss': entry_price + (SL_MULT * atr),
                    'take_profit': entry_price - (TP_MULT * atr),
                }
                in_position = True

    if len(trades) == 0:
        print(f"   ❌ No trades\n")
        continue

    trades_df = pd.DataFrame(trades)

    total_return = trades_df['pnl_pct'].sum()
    num_trades = len(trades_df)
    winners = trades_df[trades_df['pnl_pct'] > 0]
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

    print(f"   Return: {total_return:+.2f}% | R/DD: {return_dd:.2f}x")
    print(f"   Trades: {num_trades} | TP: {tp_rate:.1f}% | SL: {sl_rate:.1f}%")
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
print("SUMMARY - FILTERED RESULTS")
print("="*90)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)
results_df.to_csv('results/pippin_fresh_crosses_filtered.csv', index=False)

print("\nRanked by R/DD:")
print(results_df[['config', 'return', 'return_dd', 'tp_rate', 'trades']].to_string(index=False))

print("\n" + "="*90)
print("BASELINE COMPARISON")
print("="*90)
baseline = results_df[results_df['config'] == 'Baseline (Fresh Crosses)'].iloc[0]
print(f"Baseline: Return={baseline['return']:+.2f}%, R/DD={baseline['return_dd']:.2f}x, TP={baseline['tp_rate']:.1f}%, Trades={int(baseline['trades'])}")
print()

best = results_df.iloc[0]
if best['config'] != 'Baseline (Fresh Crosses)':
    print(f"🏆 BEST: {best['config']}")
    print(f"   Return: {best['return']:+.2f}% | R/DD: {best['return_dd']:.2f}x | TP: {best['tp_rate']:.1f}%")
    print(f"   Trades: {int(best['trades'])} (vs {int(baseline['trades'])} baseline)")
    print()
    print(f"   R/DD improvement: {best['return_dd'] - baseline['return_dd']:+.2f}x ({((best['return_dd']/baseline['return_dd'])-1)*100:+.1f}%)")
    print(f"   TP rate improvement: {best['tp_rate'] - baseline['tp_rate']:+.1f}pp")

    if best['return_dd'] >= 6.0:
        print(f"\n   ✅ DEPLOYMENT READY! R/DD {best['return_dd']:.2f}x >> 3.0x threshold")
else:
    print("⚠️ No filter improved R/DD over baseline")

print("="*90)
