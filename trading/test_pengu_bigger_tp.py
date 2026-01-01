#!/usr/bin/env python3
"""
PENGU - RSI Cross Down - Test bigger take profits
Test 30% and 50% offsets with TP from 5% to 20%
Nov-Dec 2025
"""
import pandas as pd
import numpy as np

print("="*90)
print("PENGU - RSI CROSS DOWN - TESTING BIGGER TAKE PROFITS")
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
max_wait_bars = 10
max_sl_pct = 10.0
risk_pct = 5.0

def backtest_config(df, retracement_pct, tp_pct):
    """Backtest for specific offset and TP"""
    equity = 100.0
    trades = []

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
                limit_pending = False
                prev_rsi = current_rsi
                continue

            # Check fill
            if row['high'] >= limit_price:
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
                trades.append({'pnl': pnl_dollar, 'exit': 'TP' if hit_tp else 'SL'})

                limit_pending = False

        # Detect RSI cross down
        if prev_rsi is not None:
            crossed_down = (prev_rsi > rsi_trigger and current_rsi <= rsi_trigger)

            if crossed_down:
                if limit_pending:
                    prev_rsi = current_rsi
                    continue

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
                    prev_rsi = current_rsi
                    continue

                # Valid - place limit
                limit_pending = True
                limit_placed_idx = i

        prev_rsi = current_rsi

    # Calculate metrics
    total_return = ((equity - 100) / 100) * 100

    if len(trades) > 0:
        equity_curve = [100.0]
        for t in trades:
            equity_curve.append(equity_curve[-1] + t['pnl'])

        eq_series = pd.Series(equity_curve)
        running_max = eq_series.expanding().max()
        drawdown = (eq_series - running_max) / running_max * 100
        max_dd = drawdown.min()

        return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

        winners = [t for t in trades if t['pnl'] > 0]
        win_rate = (len(winners) / len(trades)) * 100

        tp_count = sum(1 for t in trades if t['exit'] == 'TP')
        sl_count = sum(1 for t in trades if t['exit'] == 'SL')
    else:
        max_dd = 0
        return_dd = 0
        win_rate = 0
        tp_count = 0
        sl_count = 0

    return {
        'offset': retracement_pct,
        'tp': tp_pct,
        'trades': len(trades),
        'win_rate': win_rate,
        'tp_count': tp_count,
        'sl_count': sl_count,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'equity': equity
    }

# Test configs
print(f"\n🔍 Testing Take Profit levels 5-20%...")
print()

tp_levels = [5, 7, 10, 12, 15, 20]
offsets_to_test = [30, 50]

results_30 = []
results_50 = []

for tp in tp_levels:
    result_30 = backtest_config(df, 30, tp)
    results_30.append(result_30)

    result_50 = backtest_config(df, 50, tp)
    results_50.append(result_50)

# Display 30% offset results
print("="*90)
print("30% OFFSET")
print("="*90)
print()
print(f"{'TP%':>5} | {'Trades':>6} | {'TP Hits':>8} | {'SL Hits':>8} | {'Win%':>6} | {'Return':>8} | {'MaxDD':>8} | {'R/DD':>7}")
print("-" * 75)

for r in results_30:
    print(f"{r['tp']:>4}% | {r['trades']:>6} | {r['tp_count']:>8} | {r['sl_count']:>8} | {r['win_rate']:>5.1f}% | {r['return']:>7.1f}% | {r['max_dd']:>7.2f}% | {r['return_dd']:>7.2f}x")

best_30_return = max(results_30, key=lambda x: x['return'])
best_30_rdd = max(results_30, key=lambda x: x['return_dd'] if x['trades'] > 0 else -999)

print(f"\n✅ Best Return: TP {best_30_return['tp']}% = {best_30_return['return']:+.1f}%")
print(f"✅ Best R/DD: TP {best_30_rdd['tp']}% = {best_30_rdd['return_dd']:.2f}x")

# Display 50% offset results
print(f"\n" + "="*90)
print("50% OFFSET")
print("="*90)
print()
print(f"{'TP%':>5} | {'Trades':>6} | {'TP Hits':>8} | {'SL Hits':>8} | {'Win%':>6} | {'Return':>8} | {'MaxDD':>8} | {'R/DD':>7}")
print("-" * 75)

for r in results_50:
    print(f"{r['tp']:>4}% | {r['trades']:>6} | {r['tp_count']:>8} | {r['sl_count']:>8} | {r['win_rate']:>5.1f}% | {r['return']:>7.1f}% | {r['max_dd']:>7.2f}% | {r['return_dd']:>7.2f}x")

best_50_return = max(results_50, key=lambda x: x['return'])
best_50_rdd = max(results_50, key=lambda x: x['return_dd'] if x['trades'] > 0 else -999)

print(f"\n✅ Best Return: TP {best_50_return['tp']}% = {best_50_return['return']:+.1f}%")
print(f"✅ Best R/DD: TP {best_50_rdd['tp']}% = {best_50_rdd['return_dd']:.2f}x")

# Overall best
all_results = results_30 + results_50
overall_best = max(all_results, key=lambda x: x['return'])

print(f"\n" + "="*90)
print("🏆 OVERALL BEST CONFIGURATION")
print("="*90)
print()
print(f"Offset: {overall_best['offset']}%")
print(f"Take Profit: {overall_best['tp']}%")
print(f"Trades: {overall_best['trades']}")
print(f"Win Rate: {overall_best['win_rate']:.1f}%")
print(f"TP Hits: {overall_best['tp_count']}")
print(f"SL Hits: {overall_best['sl_count']}")
print(f"Return: {overall_best['return']:+.1f}%")
print(f"Max DD: {overall_best['max_dd']:.2f}%")
print(f"Return/DD: {overall_best['return_dd']:.2f}x")

print("="*90)
