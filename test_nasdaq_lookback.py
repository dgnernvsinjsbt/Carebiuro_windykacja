#!/usr/bin/env python3
"""
Test different lookback periods for NASDAQ LONG reversal
Larger lookback = stronger swing levels, less noise
"""
import pandas as pd
import numpy as np

print("="*90)
print("NASDAQ LONG REVERSAL - LOOKBACK OPTIMIZATION")
print("="*90)

# Load NASDAQ data
df = pd.read_csv('trading/nasdaq_3months_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n📊 Data: {len(df)} candles")

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
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['high'].max()

def find_swing_low(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['low'].min()

def backtest_config(df, rsi_trigger, limit_offset, tp_pct, lookback, max_wait=20, max_sl_pct=5.0):
    """
    Backtest LONG reversal with specific lookback
    """
    equity = 100.0
    trades = []

    armed = False
    signal_idx = None
    swing_high = None
    limit_pending = False
    limit_placed_idx = None
    swing_low_for_sl = None

    for i in range(lookback, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            continue

        # ARM - RSI < trigger
        if row['rsi'] < rsi_trigger:
            armed = True
            signal_idx = i
            swing_high = find_swing_high(df, i, lookback)
            limit_pending = False

        # Break ABOVE swing high
        if armed and swing_high is not None and not limit_pending:
            if row['high'] > swing_high:
                atr = row['atr']
                limit_price = swing_high - (atr * limit_offset)
                swing_low_for_sl = find_swing_low(df, signal_idx, i)
                limit_pending = True
                limit_placed_idx = i
                armed = False

        # Fill check
        if limit_pending:
            if i - limit_placed_idx > max_wait:
                limit_pending = False
                continue

            if row['low'] <= limit_price:
                entry_price = limit_price
                sl_price = swing_low_for_sl
                tp_price = entry_price * (1 + tp_pct / 100)

                sl_dist_pct = ((entry_price - sl_price) / entry_price) * 100

                if sl_dist_pct <= 0 or sl_dist_pct > max_sl_pct:
                    limit_pending = False
                    continue

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
                    pnl_pct = -sl_dist_pct
                    exit_reason = 'SL'
                elif hit_tp:
                    pnl_pct = tp_pct
                    exit_reason = 'TP'
                else:
                    continue

                pnl_dollar = size * (pnl_pct / 100) - size * 0.001
                equity += pnl_dollar

                trades.append({
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'exit_reason': exit_reason,
                    'sl_dist_pct': sl_dist_pct
                })

                limit_pending = False

    if len(trades) == 0:
        return None

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

    return {
        'lookback': lookback,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'final_equity': equity,
        'avg_sl_dist': trades_df['sl_dist_pct'].mean(),
        'tp_count': len(trades_df[trades_df['exit_reason'] == 'TP']),
        'sl_count': len(trades_df[trades_df['exit_reason'] == 'SL'])
    }

# Best config from previous test
rsi_trigger = 28
limit_offset = 0.20
tp_pct = 2.0

print(f"\n🔄 Testing lookback periods...")
print(f"   Base: RSI<{rsi_trigger}, Offset:{limit_offset}, TP:{tp_pct}%")
print()

# Test lookback from 5 to 30
lookbacks = [5, 10, 15, 20, 25, 30]

results = []

for lookback in lookbacks:
    result = backtest_config(
        df,
        rsi_trigger=rsi_trigger,
        limit_offset=limit_offset,
        tp_pct=tp_pct,
        lookback=lookback
    )

    if result:
        results.append(result)

print(f"✅ Completed {len(results)} tests")

# Display
print("\n" + "="*90)
print("🏆 LOOKBACK OPTIMIZATION RESULTS")
print("="*90)
print()

print(f"{'Lookback':>8} | {'Trades':>6} | {'Win%':>6} | {'Return':>8} | {'Max DD':>8} | {'R/DD':>7} | {'TP/SL':>8}")
print("-" * 90)

for r in results:
    print(f"{r['lookback']:>8} | {r['trades']:>6} | {r['win_rate']:>5.1f}% | {r['total_return']:>7.1f}% | {r['max_dd']:>7.2f}% | {r['return_dd']:>6.2f}x | {r['tp_count']:>2}/{r['sl_count']:<2}")

# Best
best = max(results, key=lambda x: x['return_dd'])
baseline = results[0]  # lookback=5

print("\n" + "="*90)
print("🎯 BEST LOOKBACK")
print("="*90)
print()
print(f"Lookback: {best['lookback']} bars")
print()
print(f"Performance:")
print(f"  Return/DD: {best['return_dd']:.2f}x")
print(f"  Total Return: {best['total_return']:+.1f}%")
print(f"  Max Drawdown: {best['max_dd']:.2f}%")
print(f"  Win Rate: {best['win_rate']:.1f}% ({best['tp_count']}TP / {best['sl_count']}SL)")
print(f"  Avg SL Distance: {best['avg_sl_dist']:.2f}%")
print(f"  Total Trades: {best['trades']}")

if best['lookback'] != baseline['lookback']:
    print()
    print(f"vs Baseline (lookback={baseline['lookback']}):")
    print(f"  Return/DD: {best['return_dd'] - baseline['return_dd']:+.2f}x ({((best['return_dd'] - baseline['return_dd']) / baseline['return_dd'] * 100):+.1f}%)")
    print(f"  Return: {best['total_return'] - baseline['total_return']:+.1f}pp")
    print(f"  Max DD: {best['max_dd'] - baseline['max_dd']:+.2f}pp")
    print(f"  Trades: {best['trades'] - baseline['trades']:+d}")
    print(f"  TP: {best['tp_count'] - baseline['tp_count']:+d} | SL: {best['sl_count'] - baseline['sl_count']:+d}")
else:
    print()
    print("✅ Baseline lookback=5 is already optimal")

print("\n" + "="*90)
print("📊 INSIGHTS")
print("="*90)
print()

# Analyze trend
if len(results) >= 3:
    early = results[:2]  # 5, 10
    late = results[-2:]  # 25, 30

    early_avg_rdd = sum(r['return_dd'] for r in early) / len(early)
    late_avg_rdd = sum(r['return_dd'] for r in late) / len(late)

    early_avg_win = sum(r['win_rate'] for r in early) / len(early)
    late_avg_win = sum(r['win_rate'] for r in late) / len(late)

    print(f"Short lookback (5-10): Avg R/DD={early_avg_rdd:.2f}x, Win%={early_avg_win:.1f}%")
    print(f"Long lookback (25-30): Avg R/DD={late_avg_rdd:.2f}x, Win%={late_avg_win:.1f}%")
    print()

    if late_avg_rdd > early_avg_rdd:
        print("✅ Longer lookback = stronger swing levels = better performance")
    else:
        print("❌ Shorter lookback works better (more responsive to recent price action)")

print("="*90)
