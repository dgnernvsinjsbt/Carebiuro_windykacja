"""
PIPPIN Fresh Crosses TP/SL Optimizer
Current: 1.5x ATR SL, 10x ATR TP = 5.35x R/DD, 17.2% TP rate
Goal: Find optimal TP/SL combo to maximize R/DD or TP hit rate
"""

import pandas as pd
import numpy as np

df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("="*90)
print("PIPPIN FRESH CROSSES - TP/SL OPTIMIZATION")
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

df['ema_9_prev'] = df['ema_9'].shift(1)
df['ema_21_prev'] = df['ema_21'].shift(1)

df['cross_up'] = (df['ema_9'] > df['ema_21']) & (df['ema_9_prev'] <= df['ema_21_prev'])
df['cross_down'] = (df['ema_9'] < df['ema_21']) & (df['ema_9_prev'] >= df['ema_21_prev'])

# Consecutive bars (for filter)
df['consecutive_ups'] = 0
df['consecutive_downs'] = 0

for i in range(1, len(df)):
    if df.loc[i, 'close'] > df.loc[i, 'open']:
        df.loc[i, 'consecutive_ups'] = df.loc[i-1, 'consecutive_ups'] + 1
        df.loc[i, 'consecutive_downs'] = 0
    elif df.loc[i, 'close'] < df.loc[i, 'open']:
        df.loc[i, 'consecutive_downs'] = df.loc[i-1, 'consecutive_downs'] + 1
        df.loc[i, 'consecutive_ups'] = 0

print(f"Total crossovers: {df['cross_up'].sum() + df['cross_down'].sum()}")
print()

# Test TP/SL combinations
sl_multiples = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5]
tp_multiples = [4, 5, 6, 7, 8, 10, 12, 15, 20]

MAX_HOLD_BARS = 120
FEE_PCT = 0.10

results = []
print("Testing TP/SL combinations...")
print()

for sl_mult in sl_multiples:
    for tp_mult in tp_multiples:
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

            # Entry logic - FRESH CROSSES ONLY
            if not in_position:
                if row['cross_up'] and row['consecutive_ups'] == 0:
                    entry_price = row['close']
                    atr = row['atr']

                    position = {
                        'entry_idx': i,
                        'direction': 'LONG',
                        'entry_price': entry_price,
                        'stop_loss': entry_price - (sl_mult * atr),
                        'take_profit': entry_price + (tp_mult * atr),
                    }
                    in_position = True

                elif row['cross_down'] and row['consecutive_downs'] == 0:
                    entry_price = row['close']
                    atr = row['atr']

                    position = {
                        'entry_idx': i,
                        'direction': 'SHORT',
                        'entry_price': entry_price,
                        'stop_loss': entry_price + (sl_mult * atr),
                        'take_profit': entry_price - (tp_mult * atr),
                    }
                    in_position = True

        if len(trades) == 0:
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

        results.append({
            'sl_mult': sl_mult,
            'tp_mult': tp_mult,
            'rr_ratio': tp_mult / sl_mult,
            'return': total_return,
            'max_dd': max_dd,
            'return_dd': return_dd,
            'trades': num_trades,
            'win_rate': win_rate,
            'tp_rate': tp_rate,
            'sl_rate': sl_rate,
        })

print(f"Tested {len(results)} combinations")
print()

# Analyze results
results_df = pd.DataFrame(results)
results_df.to_csv('results/pippin_fresh_crosses_tp_sl_grid.csv', index=False)

print("="*90)
print("TOP 10 BY RETURN/DD RATIO")
print("="*90)
top_by_rdd = results_df.nlargest(10, 'return_dd')
print(top_by_rdd[['sl_mult', 'tp_mult', 'rr_ratio', 'return', 'return_dd', 'tp_rate', 'sl_rate', 'trades']].to_string(index=False))
print()

print("="*90)
print("TOP 10 BY ABSOLUTE RETURN")
print("="*90)
top_by_return = results_df.nlargest(10, 'return')
print(top_by_return[['sl_mult', 'tp_mult', 'rr_ratio', 'return', 'return_dd', 'tp_rate', 'sl_rate', 'trades']].to_string(index=False))
print()

print("="*90)
print("TOP 10 BY TP HIT RATE")
print("="*90)
top_by_tp = results_df.nlargest(10, 'tp_rate')
print(top_by_tp[['sl_mult', 'tp_mult', 'rr_ratio', 'return', 'return_dd', 'tp_rate', 'sl_rate', 'trades']].to_string(index=False))
print()

# Find sweet spots
print("="*90)
print("DEPLOYMENT CANDIDATES (R/DD >= 3.0x)")
print("="*90)
deployment = results_df[results_df['return_dd'] >= 3.0].sort_values('return_dd', ascending=False)
if len(deployment) > 0:
    print(deployment[['sl_mult', 'tp_mult', 'rr_ratio', 'return', 'return_dd', 'tp_rate', 'sl_rate', 'trades']].to_string(index=False))
    print(f"\n✅ Found {len(deployment)} deployment-ready configs!")
else:
    print("❌ No configs meet 3.0x R/DD threshold")
print()

# Current baseline comparison
print("="*90)
print("COMPARISON TO CURRENT (1.5x SL, 10x TP)")
print("="*90)
baseline = results_df[(results_df['sl_mult'] == 1.5) & (results_df['tp_mult'] == 10)]
if len(baseline) > 0:
    baseline_row = baseline.iloc[0]
    print(f"Current: Return={baseline_row['return']:+.2f}%, R/DD={baseline_row['return_dd']:.2f}x, TP={baseline_row['tp_rate']:.1f}%")

    best = results_df.iloc[results_df['return_dd'].idxmax()]
    print(f"Best R/DD: SL={best['sl_mult']}x, TP={best['tp_mult']}x")
    print(f"  Return={best['return']:+.2f}%, R/DD={best['return_dd']:.2f}x, TP={best['tp_rate']:.1f}%")
    print(f"  Improvement: R/DD {best['return_dd'] - baseline_row['return_dd']:+.2f}x ({((best['return_dd']/baseline_row['return_dd'])-1)*100:+.1f}%)")
print()

# Optimal balance (high R/DD + reasonable TP rate)
print("="*90)
print("BALANCED CONFIGS (R/DD > 4.0x AND TP Rate > 15%)")
print("="*90)
balanced = results_df[(results_df['return_dd'] > 4.0) & (results_df['tp_rate'] > 15)].sort_values('return_dd', ascending=False)
if len(balanced) > 0:
    print(balanced[['sl_mult', 'tp_mult', 'rr_ratio', 'return', 'return_dd', 'tp_rate', 'sl_rate', 'trades']].to_string(index=False))
else:
    print("No configs meet both criteria")
print()

print("="*90)
print("RECOMMENDATIONS")
print("="*90)

best_rdd = results_df.iloc[results_df['return_dd'].idxmax()]
best_return = results_df.iloc[results_df['return'].idxmax()]
best_tp_rate = results_df.iloc[results_df['tp_rate'].idxmax()]

print(f"\n🏆 BEST R/DD: SL={best_rdd['sl_mult']}x, TP={best_rdd['tp_mult']}x")
print(f"   Return: {best_rdd['return']:+.2f}% | R/DD: {best_rdd['return_dd']:.2f}x | TP: {best_rdd['tp_rate']:.1f}%")

print(f"\n💰 BEST RETURN: SL={best_return['sl_mult']}x, TP={best_return['tp_mult']}x")
print(f"   Return: {best_return['return']:+.2f}% | R/DD: {best_return['return_dd']:.2f}x | TP: {best_return['tp_rate']:.1f}%")

print(f"\n🎯 BEST TP RATE: SL={best_tp_rate['sl_mult']}x, TP={best_tp_rate['tp_mult']}x")
print(f"   Return: {best_tp_rate['return']:+.2f}% | R/DD: {best_tp_rate['return_dd']:.2f}x | TP: {best_tp_rate['tp_rate']:.1f}%")

print("\n" + "="*90)
