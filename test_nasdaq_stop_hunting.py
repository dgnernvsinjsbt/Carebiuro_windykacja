#!/usr/bin/env python3
"""
Test stop hunting protection on NASDAQ LONG reversal
Compare exact swing level vs 0.1 ATR buffer vs 0.2 ATR buffer
"""
import pandas as pd
import numpy as np

print("="*90)
print("NASDAQ LONG REVERSAL - STOP HUNTING PROTECTION TEST")
print("="*90)

# Load NASDAQ data
df = pd.read_csv('trading/nasdaq_3months_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n📊 Data Loaded:")
print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Candles: {len(df)}")
print(f"   Avg Price: ${df['close'].mean():,.2f}")

# Calculate RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Calculate ATR
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

def find_swing_high(df, idx, lookback):
    """Find swing high for LONG reversal"""
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['high'].max()

def find_swing_low(df, start_idx, end_idx):
    """Find swing low for stop loss"""
    return df.iloc[start_idx:end_idx+1]['low'].min()

def backtest_with_sl_buffer(df, rsi_trigger, limit_offset, tp_pct, sl_atr_buffer=0.0, lookback=5, max_wait=20, max_sl_pct=5.0):
    """
    Backtest LONG reversal with stop loss buffer

    sl_atr_buffer: ATR multiplier to add BELOW swing low for stop
                   0.0 = exact swing low
                   0.1 = swing_low - 0.1 * ATR
                   0.2 = swing_low - 0.2 * ATR
    """
    equity = 100.0
    trades = []

    armed = False
    signal_idx = None
    swing_high = None
    limit_pending = False
    limit_placed_idx = None
    swing_low_for_sl = None
    signal_atr = None

    for i in range(lookback, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            continue

        # ARM signal - RSI < trigger (OVERSOLD)
        if row['rsi'] < rsi_trigger:
            armed = True
            signal_idx = i
            swing_high = find_swing_high(df, i, lookback)
            signal_atr = row['atr']  # Save ATR at signal time
            limit_pending = False

        # Resistance break (price breaks ABOVE swing high)
        if armed and swing_high is not None and not limit_pending:
            if row['high'] > swing_high:
                atr = row['atr']
                # LIMIT order BELOW the break (buy the pullback)
                limit_price = swing_high - (atr * limit_offset)
                swing_low_for_sl = find_swing_low(df, signal_idx, i)
                limit_pending = True
                limit_placed_idx = i
                armed = False

        # Limit order fill check
        if limit_pending:
            # Timeout
            if i - limit_placed_idx > max_wait:
                limit_pending = False
                continue

            # Check fill (price pulls back to limit)
            if row['low'] <= limit_price:
                entry_price = limit_price
                entry_atr = row['atr']

                # Apply stop loss buffer
                sl_price = swing_low_for_sl - (entry_atr * sl_atr_buffer)
                tp_price = entry_price * (1 + tp_pct / 100)  # LONG: TP above entry

                sl_dist_pct = ((entry_price - sl_price) / entry_price) * 100

                # Skip if SL too wide
                if sl_dist_pct <= 0 or sl_dist_pct > max_sl_pct:
                    limit_pending = False
                    continue

                # Position sizing
                size = (equity * 0.05) / (sl_dist_pct / 100)

                # Find exit
                hit_sl = False
                hit_tp = False
                exit_bar = None

                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]

                    if future_row['low'] <= sl_price:
                        hit_sl = True
                        exit_bar = j
                        break
                    elif future_row['high'] >= tp_price:
                        hit_tp = True
                        exit_bar = j
                        break

                if hit_sl:
                    pnl_pct = -sl_dist_pct  # LONG: SL hit = negative
                    exit_reason = 'SL'
                elif hit_tp:
                    pnl_pct = tp_pct  # LONG: TP hit = positive
                    exit_reason = 'TP'
                else:
                    continue

                pnl_dollar = size * (pnl_pct / 100) - size * 0.001  # 0.1% fees
                equity += pnl_dollar

                trades.append({
                    'entry_time': row['timestamp'],
                    'exit_time': df.iloc[exit_bar]['timestamp'],
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'swing_low': swing_low_for_sl,
                    'sl_buffer_dollars': entry_atr * sl_atr_buffer,
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'exit_reason': exit_reason,
                    'sl_dist_pct': sl_dist_pct
                })

                limit_pending = False

    if len(trades) == 0:
        return None

    # Calculate metrics
    trades_df = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100

    # Max DD
    equity_curve = [100.0]
    for pnl in trades_df['pnl_dollar']:
        equity_curve.append(equity_curve[-1] + pnl)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = trades_df[trades_df['pnl_dollar'] > 0]
    win_rate = (len(winners) / len(trades_df)) * 100

    # Count avoided stop hunts (trades that would have hit exact swing low but didn't hit buffered stop)
    avoided_hunts = 0
    if sl_atr_buffer > 0:
        for _, trade in trades_df.iterrows():
            # If this trade hit SL with buffer, check if it would have hit exact swing low
            if trade['exit_reason'] == 'SL':
                # Both hit - not avoided
                pass
            else:
                # Didn't hit buffered SL - check if exact swing low would have been hit
                # (We can't determine this without re-running, so just count TP trades)
                pass

    return {
        'sl_atr_buffer': sl_atr_buffer,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'final_equity': equity,
        'avg_sl_dist': trades_df['sl_dist_pct'].mean(),
        'tp_count': len(trades_df[trades_df['exit_reason'] == 'TP']),
        'sl_count': len(trades_df[trades_df['exit_reason'] == 'SL']),
        'avg_buffer_dollars': trades_df['sl_buffer_dollars'].mean(),
        'trades_df': trades_df
    }

# Test best config from previous LONG reversal test
# Best was: RSI < 28, offset 0.20, TP 2.0%
rsi_trigger = 28
limit_offset = 0.20
tp_pct = 2.0

print(f"\n🔄 Testing 3 stop loss placement methods...")
print(f"   Base Config: RSI<{rsi_trigger}, Offset:{limit_offset}, TP:{tp_pct}%")
print()

# Test 3 buffer levels
buffers = [
    (0.0, "Exact swing low (baseline)"),
    (0.1, "Swing low - 0.1 ATR"),
    (0.2, "Swing low - 0.2 ATR")
]

results = []

for buffer, description in buffers:
    print(f"Testing: {description}...")
    result = backtest_with_sl_buffer(
        df,
        rsi_trigger=rsi_trigger,
        limit_offset=limit_offset,
        tp_pct=tp_pct,
        sl_atr_buffer=buffer
    )

    if result:
        result['description'] = description
        results.append(result)

print(f"\n✅ Completed {len(results)} tests")

# Display results
print("\n" + "="*90)
print("🏆 STOP HUNTING PROTECTION RESULTS")
print("="*90)
print()

print(f"{'Method':<30} | {'Trades':>7} | {'Win%':>6} | {'Return':>8} | {'Max DD':>8} | {'R/DD':>7}")
print("-" * 90)

for result in results:
    print(f"{result['description']:<30} | {result['trades']:>7} | {result['win_rate']:>5.1f}% | {result['total_return']:>7.1f}% | {result['max_dd']:>7.2f}% | {result['return_dd']:>6.2f}x")

# Detailed comparison
print("\n" + "="*90)
print("📊 DETAILED COMPARISON")
print("="*90)

baseline = results[0]

for i, result in enumerate(results):
    print(f"\n{i+1}. {result['description']}")
    print(f"   Return/DD: {result['return_dd']:.2f}x")
    print(f"   Total Return: {result['total_return']:+.1f}%")
    print(f"   Max Drawdown: {result['max_dd']:.2f}%")
    print(f"   Final Equity: ${result['final_equity']:.2f}")
    print(f"   Win Rate: {result['win_rate']:.1f}% ({result['tp_count']}TP / {result['sl_count']}SL)")
    print(f"   Avg SL Distance: {result['avg_sl_dist']:.2f}%")

    if result['sl_atr_buffer'] > 0:
        print(f"   Avg Buffer: ${result['avg_buffer_dollars']:.2f}")

        # Compare to baseline
        return_diff = result['total_return'] - baseline['total_return']
        dd_diff = result['max_dd'] - baseline['max_dd']
        rdd_diff = result['return_dd'] - baseline['return_dd']
        tp_diff = result['tp_count'] - baseline['tp_count']
        sl_diff = result['sl_count'] - baseline['sl_count']

        print(f"\n   vs Baseline:")
        print(f"   Return: {return_diff:+.1f}pp | DD: {dd_diff:+.2f}pp | R/DD: {rdd_diff:+.2f}x")
        print(f"   TP: {tp_diff:+d} | SL: {sl_diff:+d}")

# Best method
best = max(results, key=lambda x: x['return_dd'])

print("\n" + "="*90)
print("🎯 BEST STOP PLACEMENT METHOD")
print("="*90)
print()
print(f"Method: {best['description']}")
print(f"Buffer: {best['sl_atr_buffer']}x ATR below swing low")
print()
print(f"Performance:")
print(f"  Return/DD: {best['return_dd']:.2f}x")
print(f"  Total Return: {best['total_return']:+.1f}%")
print(f"  Max Drawdown: {best['max_dd']:.2f}%")
print(f"  Win Rate: {best['win_rate']:.1f}%")
print(f"  Total Trades: {best['trades']}")

if best['sl_atr_buffer'] > 0:
    improvement = ((best['return_dd'] - baseline['return_dd']) / baseline['return_dd']) * 100
    print()
    print(f"Improvement vs Baseline:")
    print(f"  Return/DD: {improvement:+.1f}%")
    print(f"  Avoided {baseline['sl_count'] - best['sl_count']} stop losses")
    print()
    print(f"✅ Stop hunting buffer WORKS!" if best['sl_atr_buffer'] > 0 else "❌ Baseline is still best")
else:
    print()
    print("✅ Exact swing low placement is optimal (no buffer needed)")

# Save detailed results
best['trades_df'].to_csv('nasdaq_stop_hunting_best_trades.csv', index=False)

print("\n💾 Best method trades saved to: nasdaq_stop_hunting_best_trades.csv")
print("="*90)
