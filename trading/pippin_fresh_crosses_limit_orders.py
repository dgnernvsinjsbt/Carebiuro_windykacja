"""
PIPPIN Fresh Crosses + LIMIT ORDERS
Apply FARTCOIN's winning limit order approach to PIPPIN:
- Signal: Fresh cross (consecutive = 0)
- Entry: Limit order X% above/below signal price
- Wait: 1-5 bars for fill
- Filter: Only trades that prove continuation

Current baseline: Market orders = 5.35x R/DD, 17.2% TP, 64 trades
Goal: Improve by filtering fake crosses
"""

import pandas as pd
import numpy as np

df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("="*90)
print("PIPPIN FRESH CROSSES - LIMIT ORDER OPTIMIZATION")
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

print(f"Total crossovers: {df['cross_up'].sum() + df['cross_down'].sum()}")
print()

# Test limit order configurations
limit_offsets = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]  # % above/below signal
max_wait_bars = [1, 2, 3, 4, 5]  # bars to wait for fill

SL_MULT = 1.5
TP_MULT = 10.0  # Current best
MAX_HOLD_BARS = 120
FEE_PCT = 0.07  # Limit orders: 0.02% maker + 0.05% taker (if filled)

results = []
print("Testing limit order configurations...")
print()

for limit_pct in limit_offsets:
    for max_wait in max_wait_bars:
        trades = []
        signals = 0
        fills = 0

        in_position = False
        position = None
        waiting_for_fill = False
        limit_order = None

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

            # Check if limit order fills
            if waiting_for_fill:
                bars_waiting = i - limit_order['signal_idx']
                current_price = row['close']

                filled = False

                if limit_order['direction'] == 'LONG':
                    # LONG limit: wait for price to go UP 1% (confirming momentum)
                    if current_price >= limit_order['limit_price']:
                        filled = True
                        entry_price = limit_order['limit_price']
                else:  # SHORT
                    # SHORT limit: wait for price to go DOWN 1% (confirming momentum)
                    if current_price <= limit_order['limit_price']:
                        filled = True
                        entry_price = limit_order['limit_price']

                if filled:
                    fills += 1
                    atr = row['atr']

                    if limit_order['direction'] == 'LONG':
                        position = {
                            'entry_idx': i,
                            'direction': 'LONG',
                            'entry_price': entry_price,
                            'stop_loss': entry_price - (SL_MULT * atr),
                            'take_profit': entry_price + (TP_MULT * atr),
                        }
                    else:
                        position = {
                            'entry_idx': i,
                            'direction': 'SHORT',
                            'entry_price': entry_price,
                            'stop_loss': entry_price + (SL_MULT * atr),
                            'take_profit': entry_price - (TP_MULT * atr),
                        }

                    in_position = True
                    waiting_for_fill = False
                    limit_order = None

                elif bars_waiting >= max_wait:
                    # Order expired
                    waiting_for_fill = False
                    limit_order = None

            # Signal detection - FRESH CROSSES ONLY
            if not in_position and not waiting_for_fill:
                if row['cross_up'] and row['consecutive_ups'] == 0:
                    signals += 1
                    signal_price = row['close']

                    # Place limit order 1% ABOVE signal (wait for continuation)
                    limit_order = {
                        'signal_idx': i,
                        'direction': 'LONG',
                        'signal_price': signal_price,
                        'limit_price': signal_price * (1 + limit_pct / 100),
                    }
                    waiting_for_fill = True

                elif row['cross_down'] and row['consecutive_downs'] == 0:
                    signals += 1
                    signal_price = row['close']

                    # Place limit order 1% BELOW signal (wait for continuation)
                    limit_order = {
                        'signal_idx': i,
                        'direction': 'SHORT',
                        'signal_price': signal_price,
                        'limit_price': signal_price * (1 - limit_pct / 100),
                    }
                    waiting_for_fill = True

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

        fill_rate = (fills / signals * 100) if signals > 0 else 0

        results.append({
            'limit_pct': limit_pct,
            'max_wait': max_wait,
            'signals': signals,
            'fills': fills,
            'fill_rate': fill_rate,
            'trades': num_trades,
            'return': total_return,
            'max_dd': max_dd,
            'return_dd': return_dd,
            'win_rate': win_rate,
            'tp_rate': tp_rate,
            'sl_rate': sl_rate,
        })

print(f"Tested {len(results)} limit order configurations")
print()

# Analyze results
results_df = pd.DataFrame(results)
results_df.to_csv('results/pippin_fresh_crosses_limit_orders.csv', index=False)

print("="*90)
print("TOP 10 BY RETURN/DD RATIO")
print("="*90)
top_by_rdd = results_df.nlargest(10, 'return_dd')
print(top_by_rdd[['limit_pct', 'max_wait', 'return', 'return_dd', 'tp_rate', 'fill_rate', 'trades', 'signals']].to_string(index=False))
print()

print("="*90)
print("TOP 10 BY ABSOLUTE RETURN")
print("="*90)
top_by_return = results_df.nlargest(10, 'return')
print(top_by_return[['limit_pct', 'max_wait', 'return', 'return_dd', 'tp_rate', 'fill_rate', 'trades', 'signals']].to_string(index=False))
print()

print("="*90)
print("DEPLOYMENT CANDIDATES (R/DD >= 5.0x)")
print("="*90)
deployment = results_df[results_df['return_dd'] >= 5.0].sort_values('return_dd', ascending=False)
if len(deployment) > 0:
    print(deployment[['limit_pct', 'max_wait', 'return', 'return_dd', 'tp_rate', 'fill_rate', 'trades', 'signals']].to_string(index=False))
    print(f"\n✅ Found {len(deployment)} configs with R/DD >= 5.0x!")
else:
    print("No configs meet 5.0x threshold, showing R/DD >= 4.0x:")
    deployment = results_df[results_df['return_dd'] >= 4.0].sort_values('return_dd', ascending=False)
    if len(deployment) > 0:
        print(deployment[['limit_pct', 'max_wait', 'return', 'return_dd', 'tp_rate', 'fill_rate', 'trades', 'signals']].to_string(index=False))
print()

print("="*90)
print("COMPARISON TO MARKET ORDERS (BASELINE)")
print("="*90)
print("Market Orders: Return=+39.12%, R/DD=5.35x, TP=17.2%, Trades=64")
print()

best = results_df.iloc[results_df['return_dd'].idxmax()]
print(f"🏆 BEST LIMIT ORDER CONFIG:")
print(f"   Limit: {best['limit_pct']}% offset, Max wait: {best['max_wait']} bars")
print(f"   Signals: {int(best['signals'])} | Fills: {int(best['fills'])} ({best['fill_rate']:.1f}%)")
print(f"   Return: {best['return']:+.2f}% | R/DD: {best['return_dd']:.2f}x | TP: {best['tp_rate']:.1f}%")
print()

if best['return_dd'] > 5.35:
    improvement = ((best['return_dd'] / 5.35) - 1) * 100
    print(f"   🎉 IMPROVEMENT: R/DD +{improvement:.1f}% vs market orders!")
    print(f"   Trade reduction: 64 → {int(best['trades'])} ({((1 - best['trades']/64)*100):.1f}% fewer)")
elif best['return_dd'] < 5.35:
    decline = ((5.35 / best['return_dd']) - 1) * 100
    print(f"   ⚠️ R/DD declined by {decline:.1f}% vs market orders")
else:
    print(f"   → No improvement over market orders")

print()

# Find sweet spot (high R/DD + reasonable fill rate)
print("="*90)
print("BALANCED CONFIGS (R/DD > 4.5x AND Fill Rate > 15%)")
print("="*90)
balanced = results_df[(results_df['return_dd'] > 4.5) & (results_df['fill_rate'] > 15)].sort_values('return_dd', ascending=False)
if len(balanced) > 0:
    print(balanced[['limit_pct', 'max_wait', 'return', 'return_dd', 'tp_rate', 'fill_rate', 'trades']].to_string(index=False))
else:
    print("No configs meet both criteria")

print("\n" + "="*90)
