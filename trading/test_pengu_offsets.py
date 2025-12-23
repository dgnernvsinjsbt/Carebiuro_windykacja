#!/usr/bin/env python3
"""
PENGU - RSI Cross Down - Test different retracement offsets
RSI 72, retracement: 40%, 50%, 60%, 70%, 80% toward highest high
Nov-Dec 2025
"""
import pandas as pd
import numpy as np

print("="*90)
print("PENGU - RSI CROSS DOWN - TESTING RETRACEMENT OFFSETS")
print("="*90)

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Filter to Nov-Dec 2025
df = df[(df['timestamp'] >= '2025-11-01') & (df['timestamp'] < '2026-01-01')].reset_index(drop=True)

print(f"\n📊 Data: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Period: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

# Calculate RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Fixed parameters
rsi_trigger = 72
lookback = 5
tp_pct = 5.0
max_wait_bars = 10
max_sl_pct = 10.0
risk_pct = 5.0

def backtest_offset(df, retracement_pct):
    """Backtest for a specific retracement offset"""
    equity = 100.0
    trades = []

    stats = {
        'crossdowns': 0,
        'signals': 0,
        'skipped_pending': 0,
        'rejected_sl': 0,
        'limits_placed': 0,
        'limits_filled': 0,
        'limits_timeout': 0
    }

    limit_pending = False
    limit_placed_idx = None
    limit_price = None
    sl_price = None
    tp_price = None

    prev_rsi = None

    for i in range(lookback + 14, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']):
            prev_rsi = row['rsi']
            continue

        current_rsi = row['rsi']

        # Check limit order status
        if limit_pending:
            bars_waiting = i - limit_placed_idx

            # Timeout
            if bars_waiting > max_wait_bars:
                stats['limits_timeout'] += 1
                limit_pending = False
                prev_rsi = current_rsi
                continue

            # Check fill
            if row['high'] >= limit_price:
                stats['limits_filled'] += 1

                sl_dist_pct = ((sl_price - limit_price) / limit_price) * 100
                position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)

                # Find exit
                hit_sl = False
                hit_tp = False

                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]

                    if future_row['high'] >= sl_price:
                        hit_sl = True
                        break
                    elif future_row['low'] <= tp_price:
                        hit_tp = True
                        break

                if hit_sl:
                    pnl_pct = -sl_dist_pct
                elif hit_tp:
                    pnl_pct = tp_pct
                else:
                    limit_pending = False
                    prev_rsi = current_rsi
                    continue

                pnl_dollar = position_size * (pnl_pct / 100)
                equity += pnl_dollar
                trades.append(pnl_dollar)

                limit_pending = False

        # Detect RSI cross down
        if prev_rsi is not None:
            crossed_down = (prev_rsi > rsi_trigger and current_rsi <= rsi_trigger)

            if crossed_down:
                stats['crossdowns'] += 1

                if limit_pending:
                    stats['skipped_pending'] += 1
                    prev_rsi = current_rsi
                    continue

                stats['signals'] += 1

                # Calculate signal
                highest_high = df.iloc[i-lookback:i+1]['high'].max()
                current_close = row['close']
                distance = highest_high - current_close
                limit_price = current_close + (distance * (retracement_pct / 100))
                sl_price = highest_high
                tp_price = limit_price * (1 - tp_pct / 100)
                sl_dist_pct = ((sl_price - limit_price) / limit_price) * 100

                # Check SL filter
                if sl_dist_pct > max_sl_pct or sl_dist_pct <= 0:
                    stats['rejected_sl'] += 1
                    prev_rsi = current_rsi
                    continue

                # Valid - place limit
                stats['limits_placed'] += 1
                limit_pending = True
                limit_placed_idx = i

        prev_rsi = current_rsi

    # Calculate metrics
    total_return = ((equity - 100) / 100) * 100

    if len(trades) > 0:
        equity_curve = [100.0]
        for pnl in trades:
            equity_curve.append(equity_curve[-1] + pnl)

        eq_series = pd.Series(equity_curve)
        running_max = eq_series.expanding().max()
        drawdown = (eq_series - running_max) / running_max * 100
        max_dd = drawdown.min()

        return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

        winners = [t for t in trades if t > 0]
        win_rate = (len(winners) / len(trades)) * 100
    else:
        max_dd = 0
        return_dd = 0
        win_rate = 0

    return {
        'offset': retracement_pct,
        'crossdowns': stats['crossdowns'],
        'signals': stats['signals'],
        'rejected_sl': stats['rejected_sl'],
        'limits_placed': stats['limits_placed'],
        'limits_filled': stats['limits_filled'],
        'limits_timeout': stats['limits_timeout'],
        'trades': len(trades),
        'win_rate': win_rate,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'equity': equity
    }

# Test offsets
print(f"\n🔍 Testing retracement offsets 40-80% (RSI 72)...")
print()

offsets = [30, 40, 50, 60, 70, 80]
results = []

for offset in offsets:
    result = backtest_offset(df, offset)
    results.append(result)

# Display
print(f"{'Offset':>7} | {'Cross':>6} | {'Sig':>4} | {'Rej':>4} | {'Lim':>4} | {'Fill':>5} | {'TO':>3} | {'Trades':>6} | {'Win%':>6} | {'Return':>8} | {'MaxDD':>8} | {'R/DD':>7}")
print("-" * 105)

for r in results:
    fill_rate = f"{r['limits_filled']/r['limits_placed']*100:.0f}%" if r['limits_placed'] > 0 else "0%"

    print(f"{r['offset']:>6}% | {r['crossdowns']:>6} | {r['signals']:>4} | {r['rejected_sl']:>4} | {r['limits_placed']:>4} | {fill_rate:>5} | {r['limits_timeout']:>3} | {r['trades']:>6} | {r['win_rate']:>5.1f}% | {r['return']:>7.1f}% | {r['max_dd']:>7.2f}% | {r['return_dd']:>7.2f}x")

# Find best
best_return = max(results, key=lambda x: x['return'])
best_rdd = max(results, key=lambda x: x['return_dd'] if x['trades'] > 0 else -999)

print(f"\n" + "="*90)
print("🏆 BEST RESULTS")
print("="*90)
print()

print(f"Best Return:")
print(f"   {best_return['offset']}% offset: {best_return['trades']} trades, {best_return['win_rate']:.1f}% win rate, {best_return['return']:+.1f}% return")
print()

print(f"Best Return/DD:")
print(f"   {best_rdd['offset']}% offset: {best_rdd['trades']} trades, {best_rdd['win_rate']:.1f}% win rate, {best_rdd['return']:+.1f}% return, {best_rdd['return_dd']:.2f}x R/DD")

print(f"\n💡 Analysis:")
print(f"   Higher offset = entering closer to highest high (tighter SL)")
print(f"   Lower fill rate expected as offset increases")

print("="*90)
