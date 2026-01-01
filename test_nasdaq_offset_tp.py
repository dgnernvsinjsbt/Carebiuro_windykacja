#!/usr/bin/env python3
"""
Test different OFFSET and TP combinations for NASDAQ LONG reversal
Maybe limit order too close or TP too small?
"""
import pandas as pd
import numpy as np

print("="*90)
print("NASDAQ LONG REVERSAL - OFFSET & TP OPTIMIZATION")
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

def backtest_config(df, rsi_trigger, limit_offset, tp_pct, lookback=5, max_wait=20, max_sl_pct=5.0):
    """
    Backtest LONG reversal with specific offset and TP
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
        'limit_offset': limit_offset,
        'tp_pct': tp_pct,
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

# Best RSI from previous tests
rsi_trigger = 28

print(f"\n🔄 Testing offset & TP combinations...")
print(f"   RSI<{rsi_trigger}, Lookback=5")
print()

# Test grid
configs = []

# Offsets: 0.10 to 0.40 (wider pullback)
# TPs: 1.5% to 4.0% (larger targets)
for offset in [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]:
    for tp in [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
        configs.append({'offset': offset, 'tp': tp})

print(f"Testing {len(configs)} combinations...")

results = []

for config in configs:
    result = backtest_config(
        df,
        rsi_trigger=rsi_trigger,
        limit_offset=config['offset'],
        tp_pct=config['tp']
    )

    if result:
        results.append(result)

print(f"✅ Completed {len(results)} successful backtests")

# Sort by R/DD
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

# Display top 20
print("\n" + "="*90)
print("🏆 TOP 20 CONFIGS (by Return/DD)")
print("="*90)
print()

print(f"{'Rank':>4} | {'Offset':>6} | {'TP':>5} | {'R/DD':>7} | {'Return':>8} | {'Max DD':>8} | {'Win%':>6} | {'Trades':>6}")
print("-" * 90)

for idx, (i, row) in enumerate(results_df.head(20).iterrows()):
    emoji = "🏆" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx+1:2d}."

    print(f"{emoji:>4} | {row['limit_offset']:>6.2f} | {row['tp_pct']:>4.1f}% | {row['return_dd']:>6.2f}x | {row['total_return']:>7.1f}% | {row['max_dd']:>7.2f}% | {row['win_rate']:>5.1f}% | {row['trades']:>6}")

# Best config
best = results_df.iloc[0]
baseline = results_df[(results_df['limit_offset'] == 0.20) & (results_df['tp_pct'] == 2.0)].iloc[0]

print("\n" + "="*90)
print("🎯 BEST CONFIGURATION")
print("="*90)
print()
print(f"Parameters:")
print(f"  RSI Trigger: <{rsi_trigger} (OVERSOLD)")
print(f"  Limit Offset: {best['limit_offset']:.2f}x ATR below breakout")
print(f"  Take Profit: {best['tp_pct']:.1f}% above entry")
print(f"  Lookback: 5 bars")
print()
print(f"Performance:")
print(f"  Return/DD: {best['return_dd']:.2f}x")
print(f"  Total Return: {best['total_return']:+.1f}%")
print(f"  Max Drawdown: {best['max_dd']:.2f}%")
print(f"  Win Rate: {best['win_rate']:.1f}% ({best['tp_count']}TP / {best['sl_count']}SL)")
print(f"  Avg SL Distance: {best['avg_sl_dist']:.2f}%")
print(f"  Total Trades: {best['trades']}")

print()
print(f"vs Baseline (offset=0.20, TP=2.0%):")
print(f"  Return/DD: {best['return_dd'] - baseline['return_dd']:+.2f}x ({((best['return_dd'] - baseline['return_dd']) / baseline['return_dd'] * 100):+.1f}%)")
print(f"  Return: {best['total_return'] - baseline['total_return']:+.1f}pp")
print(f"  Max DD: {best['max_dd'] - baseline['max_dd']:+.2f}pp")
print(f"  Win Rate: {best['win_rate'] - baseline['win_rate']:+.1f}pp")

# Analyze patterns
print("\n" + "="*90)
print("📊 PATTERN ANALYSIS")
print("="*90)
print()

# Best offset
offset_performance = results_df.groupby('limit_offset').agg({
    'return_dd': 'mean',
    'win_rate': 'mean',
    'total_return': 'mean'
}).sort_values('return_dd', ascending=False)

print("Best Offsets (avg R/DD):")
for offset, row in offset_performance.head(3).iterrows():
    print(f"  {offset:.2f} ATR: R/DD={row['return_dd']:.2f}x, Win%={row['win_rate']:.1f}%, Ret={row['total_return']:+.1f}%")

print()

# Best TP
tp_performance = results_df.groupby('tp_pct').agg({
    'return_dd': 'mean',
    'win_rate': 'mean',
    'total_return': 'mean'
}).sort_values('return_dd', ascending=False)

print("Best TPs (avg R/DD):")
for tp, row in tp_performance.head(3).iterrows():
    print(f"  {tp:.1f}%: R/DD={row['return_dd']:.2f}x, Win%={row['win_rate']:.1f}%, Ret={row['total_return']:+.1f}%")

print("\n" + "="*90)
print("💾 Saving full results...")
results_df.to_csv('nasdaq_offset_tp_results.csv', index=False)
print("Saved to: nasdaq_offset_tp_results.csv")
print("="*90)
