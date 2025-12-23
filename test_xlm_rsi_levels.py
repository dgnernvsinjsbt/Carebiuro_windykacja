#!/usr/bin/env python3
"""
Test different RSI levels on XLM to find optimal trade frequency
Keep all other parameters same as DOGE
"""
import pandas as pd
import numpy as np

print("="*90)
print("XLM - RSI LEVEL OPTIMIZATION (for trade frequency)")
print("="*90)

# Load XLM data
df = pd.read_csv('trading/xlm_3months_bingx_15m.csv')
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

# Fixed parameters (DOGE)
lookback = 5
limit_atr_offset = 0.6
tp_pct = 6.0
max_wait_bars = 20
max_sl_pct = 10.0
risk_pct = 5.0

def count_trades_for_rsi(df, rsi_trigger):
    """Quick trade counter without full backtest"""
    trades = 0
    armed = False
    signal_idx = None
    swing_low = None
    limit_pending = False
    limit_placed_idx = None

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
                swing_high = df.iloc[signal_idx:i+1]['high'].max()
                sl_dist_pct = ((swing_high - limit_price) / limit_price) * 100

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
                trades += 1
                limit_pending = False

    return trades

# Test RSI levels
print(f"\n🔍 Testing RSI levels...")
print(f"   Target: ~27-40 trades (matching DOGE/MELANIA frequency)")
print(f"   Period: 90 days")
print()

rsi_levels = [72, 70, 68, 66, 65, 64, 62, 60]
results = []

for rsi in rsi_levels:
    trades = count_trades_for_rsi(df, rsi)
    trades_per_day = trades / 90

    results.append({
        'rsi': rsi,
        'trades': trades,
        'trades_per_day': trades_per_day
    })

# Display
print(f"{'RSI Trigger':>12} | {'Total Trades':>12} | {'Trades/Day':>11} | {'vs Target':>15}")
print("-" * 60)

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

    print(f"{r['rsi']:>12} | {r['trades']:>12} | {r['trades_per_day']:>11.2f} | {status:>15}")

# Find best
target_center = (target_min + target_max) / 2
best = min(results, key=lambda x: abs(x['trades'] - target_center))

print(f"\n" + "="*90)
print("🎯 RECOMMENDED RSI TRIGGER")
print("="*90)
print()
print(f"RSI Trigger: {best['rsi']}")
print(f"Expected Trades: {best['trades']} in 90 days")
print(f"Trades per Day: {best['trades_per_day']:.2f}")
print()

# Compare to other coins
print("📊 Comparison to other coins:")
print(f"   MELANIA: 45 trades / 180 days = 0.25/day")
print(f"   DOGE:    79 trades / 180 days = 0.44/day")
print(f"   XLM:     {best['trades']} trades / 90 days = {best['trades_per_day']:.2f}/day")
print()

if best['trades_per_day'] >= 0.25 and best['trades_per_day'] <= 0.45:
    print("✅ XLM trade frequency matches DOGE/MELANIA range!")
else:
    print("⚠️  Trade frequency outside target range")

print(f"\n💡 Next step: Run full backtest with RSI {best['rsi']}")
print("="*90)
