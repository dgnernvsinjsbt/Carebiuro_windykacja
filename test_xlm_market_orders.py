#!/usr/bin/env python3
"""
Test XLM with MARKET orders instead of LIMIT
Compare trade frequency for RSI 65-72
"""
import pandas as pd
import numpy as np

print("="*90)
print("XLM - MARKET ORDERS vs LIMIT ORDERS (RSI 65-72)")
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

# DOGE parameters
lookback = 5
tp_pct = 6.0
max_sl_pct = 10.0
risk_pct = 5.0

def backtest_market_orders(df, rsi_trigger):
    """
    Backtest with MARKET orders on swing low break
    No limit orders, no waiting for pullback
    """
    equity = 100.0
    trades = 0

    armed = False
    signal_idx = None
    swing_low = None

    for i in range(lookback + 14, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            continue

        # ARM on RSI > trigger
        if row['rsi'] > rsi_trigger and not armed:
            armed = True
            signal_idx = i
            swing_low = df.iloc[i-lookback:i+1]['low'].min()

        # MARKET ORDER on break (immediate entry at break bar close)
        if armed and swing_low is not None:
            if row['low'] < swing_low:
                # Enter at MARKET on this bar's close
                entry_price = row['close']
                swing_high = df.iloc[signal_idx:i+1]['high'].max()
                sl_price = swing_high
                tp_price = entry_price * (1 - tp_pct / 100)

                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                # Skip if SL invalid
                if sl_dist_pct <= 0 or sl_dist_pct > max_sl_pct:
                    armed = False
                    continue

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
                trades += 1

                armed = False

    total_return = ((equity - 100) / 100) * 100
    return {
        'trades': trades,
        'equity': equity,
        'return': total_return
    }

def count_limit_trades(df, rsi_trigger):
    """Count trades with LIMIT orders (original method)"""
    trades = 0
    armed = False
    signal_idx = None
    swing_low = None
    limit_pending = False
    limit_placed_idx = None
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

        # Break - place LIMIT
        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                atr = row['atr']
                limit_price = swing_low + (atr * 0.6)
                swing_high = df.iloc[signal_idx:i+1]['high'].max()
                sl_dist_pct = ((swing_high - limit_price) / limit_price) * 100

                if sl_dist_pct > 0 and sl_dist_pct <= max_sl_pct:
                    limit_pending = True
                    limit_placed_idx = i
                armed = False

        # Check fill
        if limit_pending:
            if i - limit_placed_idx > 20:  # timeout
                limit_pending = False
                continue

            if row['low'] <= limit_price:
                trades += 1
                limit_pending = False

    return trades

# Test RSI levels
print(f"\n🔍 Testing RSI levels 65-72...")
print()

rsi_levels = [72, 70, 68, 66, 65]

print(f"{'RSI':>4} | {'MARKET Trades':>13} | {'LIMIT Trades':>12} | {'Difference':>11}")
print("-" * 55)

results = []

for rsi in rsi_levels:
    market_result = backtest_market_orders(df, rsi)
    limit_trades = count_limit_trades(df, rsi)

    diff = market_result['trades'] - limit_trades
    pct_more = (diff / limit_trades * 100) if limit_trades > 0 else 0

    results.append({
        'rsi': rsi,
        'market_trades': market_result['trades'],
        'limit_trades': limit_trades,
        'market_return': market_result['return'],
        'market_equity': market_result['equity']
    })

    print(f"{rsi:>4} | {market_result['trades']:>13} | {limit_trades:>12} | +{diff} ({pct_more:+.0f}%)")

print(f"\n" + "="*90)
print("🎯 MARKET ORDERS ANALYSIS")
print("="*90)
print()

# Show full results for market orders
print(f"{'RSI':>4} | {'Trades':>6} | {'Return':>8} | {'Final $':>8} | {'Trades/Day':>11}")
print("-" * 50)

for r in results:
    trades_per_day = r['market_trades'] / 90
    print(f"{r['rsi']:>4} | {r['market_trades']:>6} | {r['market_return']:>7.1f}% | ${r['market_equity']:>7.2f} | {trades_per_day:>11.2f}")

# Target comparison
print(f"\n📊 Target: 27-40 trades (0.30-0.44/day)")
print(f"   MELANIA: 45 trades / 180 days = 0.25/day")
print(f"   DOGE:    79 trades / 180 days = 0.44/day")
print()

# Find best
target_trades = 33  # middle of 27-40
best = min(results, key=lambda x: abs(x['market_trades'] - target_trades))

print("✅ RECOMMENDED:")
print(f"   RSI: {best['rsi']}")
print(f"   Trades: {best['market_trades']} (MARKET orders)")
print(f"   Trades/day: {best['market_trades']/90:.2f}")
print(f"   Return: {best['market_return']:+.1f}%")
print()

if best['market_trades'] >= 27 and best['market_trades'] <= 40:
    print("🎯 Trade frequency in target range!")
else:
    print("⚠️  Trade frequency outside target range")

print(f"\n💡 INSIGHT:")
print(f"   MARKET orders give {results[0]['market_trades'] - results[0]['limit_trades']} MORE trades")
print(f"   vs LIMIT orders at RSI {results[0]['rsi']}")
print(f"   = {((results[0]['market_trades'] - results[0]['limit_trades']) / results[0]['limit_trades'] * 100):.0f}% increase!")

print("="*90)
