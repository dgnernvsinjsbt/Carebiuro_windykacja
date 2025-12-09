"""
PIPPIN Fresh Crosses - FULL SPECTRUM Limit Order Test
Test from almost-market (0.1%) to ultra-selective (5.0%)
Find the sweet spot between trade frequency and quality
"""

import pandas as pd
import numpy as np

df = pd.read_csv('pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("="*90)
print("PIPPIN FRESH CROSSES - FULL SPECTRUM LIMIT ORDERS")
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

# FULL SPECTRUM of limit offsets
limit_offsets = [
    # Almost market
    0.1, 0.2, 0.3,
    # Close to market
    0.5, 0.75,
    # Medium distance (original test range)
    1.0, 1.25, 1.5, 2.0,
    # Far from market (very selective)
    2.5, 3.0, 3.5, 4.0, 5.0
]

max_wait_bars = [3, 5]  # Test both 3 and 5 bar waits

SL_MULT = 1.5
TP_MULT = 10.0
MAX_HOLD_BARS = 120
FEE_PCT = 0.07  # Limit orders

results = []
print(f"Testing {len(limit_offsets) * len(max_wait_bars)} limit configurations...")
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

            # Check limit fill
            if waiting_for_fill:
                bars_waiting = i - limit_order['signal_idx']
                current_price = row['close']

                filled = False

                if limit_order['direction'] == 'LONG':
                    if current_price >= limit_order['limit_price']:
                        filled = True
                        entry_price = limit_order['limit_price']
                else:
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
                    waiting_for_fill = False
                    limit_order = None

            # Signal detection - FRESH CROSSES ONLY
            if not in_position and not waiting_for_fill:
                if row['cross_up'] and row['consecutive_ups'] == 0:
                    signals += 1
                    signal_price = row['close']

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

                    limit_order = {
                        'signal_idx': i,
                        'direction': 'SHORT',
                        'signal_price': signal_price,
                        'limit_price': signal_price * (1 - limit_pct / 100),
                    }
                    waiting_for_fill = True

        if len(trades) == 0:
            # Store zero-trade results too
            results.append({
                'limit_pct': limit_pct,
                'max_wait': max_wait,
                'signals': signals,
                'fills': fills,
                'fill_rate': 0,
                'trades': 0,
                'return': 0,
                'max_dd': 0,
                'return_dd': 0,
                'win_rate': 0,
                'tp_rate': 0,
                'sl_rate': 0,
            })
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

results_df = pd.DataFrame(results)
results_df.to_csv('results/pippin_limit_full_spectrum.csv', index=False)

print("="*90)
print("FULL SPECTRUM RESULTS - ALL CONFIGS")
print("="*90)
print()

# Group by limit % for overview
print("OVERVIEW BY LIMIT OFFSET %:")
print("Limit% | Wait | Signals | Fills | Fill% | Trades | Return | R/DD | TP%")
print("-------|------|---------|-------|-------|--------|--------|------|-----")
for _, row in results_df.iterrows():
    if row['trades'] > 0:
        print(f"{row['limit_pct']:6.2f} | {int(row['max_wait']):4d} | {int(row['signals']):7d} | {int(row['fills']):5d} | {row['fill_rate']:5.1f} | {int(row['trades']):6d} | {row['return']:6.2f} | {row['return_dd']:4.2f} | {row['tp_rate']:3.0f}")
    else:
        print(f"{row['limit_pct']:6.2f} | {int(row['max_wait']):4d} | {int(row['signals']):7d} | {int(row['fills']):5d} | {row['fill_rate']:5.1f} |      0 | NO TRADES")
print()

print("="*90)
print("TOP 10 BY R/DD (with minimum 5 trades)")
print("="*90)
min_trades = results_df[results_df['trades'] >= 5]
if len(min_trades) > 0:
    top = min_trades.nlargest(10, 'return_dd')
    print(top[['limit_pct', 'max_wait', 'return', 'return_dd', 'tp_rate', 'fill_rate', 'trades']].to_string(index=False))
else:
    print("No configs with >= 5 trades")
print()

print("="*90)
print("SWEET SPOT ANALYSIS (10-30 trades for good sample)")
print("="*90)
sweet_spot = results_df[(results_df['trades'] >= 10) & (results_df['trades'] <= 30)].sort_values('return_dd', ascending=False)
if len(sweet_spot) > 0:
    print(sweet_spot[['limit_pct', 'max_wait', 'return', 'return_dd', 'tp_rate', 'fill_rate', 'trades']].to_string(index=False))
else:
    print("No configs in 10-30 trade range, showing 5-15 trades:")
    sweet_spot = results_df[(results_df['trades'] >= 5) & (results_df['trades'] <= 15)].sort_values('return_dd', ascending=False)
    if len(sweet_spot) > 0:
        print(sweet_spot[['limit_pct', 'max_wait', 'return', 'return_dd', 'tp_rate', 'fill_rate', 'trades']].to_string(index=False))
print()

print("="*90)
print("COMPARISON TO MARKET ORDERS")
print("="*90)
print("Market Orders: Return=+39.12%, R/DD=5.35x, TP=17.2%, Trades=64")
print()

# Best by different metrics
best_rdd = results_df.iloc[results_df['return_dd'].idxmax()]
best_return = results_df.iloc[results_df['return'].idxmax()]

# Best with reasonable trade count (10+)
reasonable = results_df[results_df['trades'] >= 10]
if len(reasonable) > 0:
    best_reasonable = reasonable.iloc[reasonable['return_dd'].idxmax()]
    print("🏆 BEST R/DD (10+ trades):")
    print(f"   Limit: {best_reasonable['limit_pct']}%, Wait: {int(best_reasonable['max_wait'])} bars")
    print(f"   Trades: {int(best_reasonable['trades'])} | Fill Rate: {best_reasonable['fill_rate']:.1f}%")
    print(f"   Return: {best_reasonable['return']:+.2f}% | R/DD: {best_reasonable['return_dd']:.2f}x | TP: {best_reasonable['tp_rate']:.1f}%")
    print()

print("🥇 BEST R/DD (any trade count):")
print(f"   Limit: {best_rdd['limit_pct']}%, Wait: {int(best_rdd['max_wait'])} bars")
print(f"   Trades: {int(best_rdd['trades'])} | Fill Rate: {best_rdd['fill_rate']:.1f}%")
print(f"   Return: {best_rdd['return']:+.2f}% | R/DD: {best_rdd['return_dd']:.2f}x | TP: {best_rdd['tp_rate']:.1f}%")
print()

print("💰 BEST RETURN:")
print(f"   Limit: {best_return['limit_pct']}%, Wait: {int(best_return['max_wait'])} bars")
print(f"   Trades: {int(best_return['trades'])} | Fill Rate: {best_return['fill_rate']:.1f}%")
print(f"   Return: {best_return['return']:+.2f}% | R/DD: {best_return['return_dd']:.2f}x | TP: {best_return['tp_rate']:.1f}%")

print("\n" + "="*90)
print("RECOMMENDATION")
print("="*90)

if best_rdd['return_dd'] > 5.35:
    print(f"✅ Limit orders IMPROVE R/DD: {best_rdd['return_dd']:.2f}x vs 5.35x market orders")
    print(f"   Trade-off: {int(best_rdd['trades'])} trades vs 64 market orders")

    if best_rdd['trades'] >= 10:
        print(f"   ✅ Good sample size ({int(best_rdd['trades'])} trades) - RECOMMEND DEPLOYMENT")
    elif best_rdd['trades'] >= 5:
        print(f"   ⚠️ Low sample size ({int(best_rdd['trades'])} trades) - consider 30 day test")
    else:
        print(f"   ❌ Too few trades ({int(best_rdd['trades'])}) - need 30 day data for validation")
else:
    print(f"⚠️ Limit orders don't improve R/DD: {best_rdd['return_dd']:.2f}x vs 5.35x market")
    print("   Recommend sticking with market orders")

print("="*90)
