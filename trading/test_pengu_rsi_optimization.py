#!/usr/bin/env python3
"""
Test different RSI levels on PENGU to find optimal trade frequency
Target: 27-40 trades in 6 months (matching MELANIA/DOGE frequency)
"""
import pandas as pd
import numpy as np

print("="*90)
print("PENGU-USDT - RSI LEVEL OPTIMIZATION")
print("="*90)

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

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

# Fixed parameters (MELANIA)
lookback = 5
limit_atr_offset = 0.8
tp_pct = 10.0
max_wait_bars = 20
max_sl_pct = 10.0
risk_pct = 5.0

def backtest_rsi_level(df, rsi_trigger):
    """Full backtest for a given RSI level"""
    equity = 100.0
    trades = []

    armed = False
    signal_idx = None
    swing_low = None
    limit_pending = False
    limit_placed_idx = None
    swing_high_for_sl = None
    limit_price = None

    for i in range(lookback + 14, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            continue

        # ARM
        if row['rsi'] > rsi_trigger and not armed and not limit_pending:
            armed = True
            signal_idx = i
            swing_low = df.iloc[i-lookback:i+1]['low'].min()

        # Break
        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                atr = row['atr']
                limit_price = swing_low + (atr * limit_atr_offset)
                swing_high_for_sl = df.iloc[signal_idx:i+1]['high'].max()
                sl_dist_pct = ((swing_high_for_sl - limit_price) / limit_price) * 100

                if sl_dist_pct > 0 and sl_dist_pct <= max_sl_pct:
                    limit_pending = True
                    limit_placed_idx = i
                armed = False

        # Fill check
        if limit_pending:
            bars_waiting = i - limit_placed_idx

            if bars_waiting > max_wait_bars:
                limit_pending = False
                continue

            if row['low'] <= limit_price:
                # FILLED
                entry_price = limit_price
                sl_price = swing_high_for_sl
                tp_price = entry_price * (1 - tp_pct / 100)
                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100
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
                    continue

                pnl_dollar = position_size * (pnl_pct / 100)
                equity += pnl_dollar
                trades.append(pnl_dollar)

                limit_pending = False

    total_return = ((equity - 100) / 100) * 100

    # Max DD
    if len(trades) > 0:
        equity_curve = [100.0]
        for pnl in trades:
            equity_curve.append(equity_curve[-1] + pnl)

        eq_series = pd.Series(equity_curve)
        running_max = eq_series.expanding().max()
        drawdown = (eq_series - running_max) / running_max * 100
        max_dd = drawdown.min()
    else:
        max_dd = 0

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    return {
        'trades': len(trades),
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'equity': equity
    }

# Test RSI levels
print(f"\n🔍 Testing RSI levels 65-72...")
print(f"   Target: 27-40 trades in 6 months (matching MELANIA/DOGE)")
print(f"   Period: 199 days")
print()

rsi_levels = [72, 70, 68, 66, 65]
results = []

for rsi in rsi_levels:
    result = backtest_rsi_level(df, rsi)
    result['rsi'] = rsi
    result['trades_per_day'] = result['trades'] / 199
    results.append(result)

# Display
print(f"{'RSI':>4} | {'Trades':>6} | {'Trades/Day':>11} | {'Return':>8} | {'Max DD':>8} | {'R/DD':>8} | {'Status':>15}")
print("-" * 85)

target_min = 27
target_max = 40

for r in results:
    status = ""
    if r['trades'] < target_min:
        status = "❌ TOO FEW"
    elif r['trades'] > target_max:
        status = "⚠️  TOO MANY"
    else:
        status = "✅ GOOD"

    print(f"{r['rsi']:>4} | {r['trades']:>6} | {r['trades_per_day']:>11.2f} | {r['return']:>7.1f}% | {r['max_dd']:>7.2f}% | {r['return_dd']:>7.2f}x | {status:>15}")

# Find best
target_center = (target_min + target_max) / 2
best = min(results, key=lambda x: abs(x['trades'] - target_center))

print(f"\n" + "="*90)
print("🎯 RECOMMENDED RSI TRIGGER")
print("="*90)
print()
print(f"RSI Trigger: {best['rsi']}")
print(f"Expected Trades: {best['trades']} in 199 days")
print(f"Trades per Day: {best['trades_per_day']:.2f}")
print(f"Total Return: {best['return']:+.1f}%")
print(f"Max Drawdown: {best['max_dd']:.2f}%")
print(f"Return/DD: {best['return_dd']:.2f}x")
print()

# Compare to other coins
print("📊 Comparison to 4-coin portfolio:")
print(f"   MELANIA: 45 trades / 180 days = 0.25/day (RSI 72)")
print(f"   DOGE:    79 trades / 180 days = 0.44/day (RSI 72)")
print(f"   PENGU:   {best['trades']} trades / 199 days = {best['trades_per_day']:.2f}/day (RSI {best['rsi']})")
print()

if best['trades_per_day'] >= 0.15 and best['trades_per_day'] <= 0.45:
    print("✅ PENGU trade frequency in acceptable range!")
else:
    print("⚠️  Trade frequency outside target range")

print(f"\n💡 Next step: Full backtest analysis with RSI {best['rsi']}")
print("="*90)
