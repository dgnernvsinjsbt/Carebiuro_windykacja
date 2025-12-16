"""
Test 3 position sizing improvements (no gimmicks, no hindsight):
1. Position size cap (max 3x leverage)
2. Signal quality tiers (24h range based)
3. Optimize risk % (12%, 15%, 18%, 20%)
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

print("=" * 80)
print("POSITION SIZING IMPROVEMENTS TEST")
print("=" * 80)

# Download data
exchange = ccxt.bingx({'enableRateLimit': True})

start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
end_date = datetime(2025, 12, 15, tzinfo=timezone.utc)

start_ts = int(start_date.timestamp() * 1000)
end_ts = int(end_date.timestamp() * 1000)

print("\nDownloading MELANIA full 2025 data...")

all_candles = []
current_ts = start_ts

while current_ts < end_ts:
    candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='1h', since=current_ts, limit=1000)
    if not candles:
        break
    all_candles.extend(candles)
    current_ts = candles[-1][0] + 3600000
    time.sleep(0.5)

df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
df = df[(df['timestamp'] >= start_date.replace(tzinfo=None)) & (df['timestamp'] <= end_date.replace(tzinfo=None))]
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Downloaded {len(df)} bars")

# Calculate indicators
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()

df['high_24h'] = df['high'].rolling(24).max()
df['low_24h'] = df['low'].rolling(24).min()
df['range_24h'] = ((df['high_24h'] - df['low_24h']) / df['low_24h']) * 100

MIN_RANGE_24H = 15.0
RSI_LOW = 25
RSI_HIGH = 70
LIMIT_PCT = 0.3
SL_MULT = 1.5
TP_MULT = 2.5

def backtest(df, method, risk_pct=15, max_leverage=None, tiered=False):
    trades = []
    equity = 100.0

    i = 168
    while i < len(df):
        row = df.iloc[i]
        prev_row = df.iloc[i-1] if i > 0 else None

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or prev_row is None or pd.isna(prev_row['rsi']):
            i += 1
            continue

        has_signal = False
        direction = None

        if prev_row['rsi'] < RSI_LOW and row['rsi'] >= RSI_LOW:
            has_signal = True
            direction = 'LONG'
        elif prev_row['rsi'] > RSI_HIGH and row['rsi'] <= RSI_HIGH:
            has_signal = True
            direction = 'SHORT'

        if not has_signal:
            i += 1
            continue

        if pd.notna(row['range_24h']) and row['range_24h'] < MIN_RANGE_24H:
            i += 1
            continue

        # Tiered risk
        if tiered:
            if row['range_24h'] > 25:
                current_risk = risk_pct * 1.2
            elif row['range_24h'] > 20:
                current_risk = risk_pct
            else:
                current_risk = risk_pct * 0.8
        else:
            current_risk = risk_pct

        signal_price = row['close']
        if direction == 'LONG':
            entry_price = signal_price * (1 + LIMIT_PCT / 100)
            sl_price = entry_price - (row['atr'] * SL_MULT)
            tp_price = entry_price + (row['atr'] * TP_MULT)
        else:
            entry_price = signal_price * (1 - LIMIT_PCT / 100)
            sl_price = entry_price + (row['atr'] * SL_MULT)
            tp_price = entry_price - (row['atr'] * TP_MULT)

        risk_dollars = equity * (current_risk / 100)
        sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100 if direction == 'LONG' else abs((sl_price - entry_price) / entry_price) * 100
        position_size_dollars = risk_dollars / (sl_distance_pct / 100)

        if max_leverage:
            position_size_dollars = min(position_size_dollars, equity * max_leverage)

        filled = False
        fill_idx = None
        for j in range(i + 1, min(i + 4, len(df))):
            if direction == 'LONG' and df.iloc[j]['low'] <= entry_price:
                filled = True
                fill_idx = j
                break
            elif direction == 'SHORT' and df.iloc[j]['high'] >= entry_price:
                filled = True
                fill_idx = j
                break

        if not filled:
            i += 1
            continue

        exit_idx = None
        exit_price = None
        exit_type = None

        for k in range(fill_idx + 1, len(df)):
            bar = df.iloc[k]
            prev_bar = df.iloc[k-1]

            if direction == 'LONG':
                if bar['low'] <= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['high'] >= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break
                if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                    if prev_bar['rsi'] > RSI_HIGH and bar['rsi'] <= RSI_HIGH:
                        exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                        break
            else:
                if bar['high'] >= sl_price:
                    exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                    break
                if bar['low'] <= tp_price:
                    exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                    break
                if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                    if prev_bar['rsi'] < RSI_LOW and bar['rsi'] >= RSI_LOW:
                        exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                        break

        if exit_idx is None:
            i += 1
            continue

        if direction == 'LONG':
            price_change_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            price_change_pct = ((entry_price - exit_price) / entry_price) * 100

        pnl_before_fees = position_size_dollars * (price_change_pct / 100)
        fees = position_size_dollars * 0.001
        pnl_dollars = pnl_before_fees - fees
        equity += pnl_dollars

        trades.append({'pnl_dollars': pnl_dollars, 'equity': equity})
        i = exit_idx + 1

    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100
    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    max_dd = ((eq - running_max) / running_max * 100).min()
    win_rate = (df_t['pnl_dollars'] > 0).sum() / len(df_t) * 100

    return {
        'method': method,
        'risk_pct': risk_pct,
        'max_leverage': max_leverage if max_leverage else 0,
        'tiered': tiered,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate
    }

# Run tests
print("\nRunning tests...")
results = []

print("  Baseline...")
results.append(backtest(df, 'Baseline', risk_pct=15, max_leverage=None, tiered=False))

print("  Position caps...")
for cap in [2.5, 3.0, 3.5, 4.0]:
    results.append(backtest(df, f'Cap {cap}x', risk_pct=15, max_leverage=cap, tiered=False))

print("  Risk %...")
for risk in [10, 12, 18, 20]:
    results.append(backtest(df, f'Risk {risk}%', risk_pct=risk, max_leverage=None, tiered=False))

print("  Tiered...")
for risk in [12, 15, 18]:
    results.append(backtest(df, f'Tiered {risk}%', risk_pct=risk, max_leverage=None, tiered=True))

print("  Combinations...")
for risk in [15, 18]:
    for cap in [3.0, 3.5]:
        results.append(backtest(df, f'Tier{risk}%+Cap{cap}x', risk_pct=risk, max_leverage=cap, tiered=True))

print(f"\nDone! {len(results)} tests")

# Sort
results_df = pd.DataFrame([r for r in results if r is not None])
results_df = results_df.sort_values('return_dd', ascending=False)

# Display
print("\n" + "=" * 80)
print("RESULTS (by R/DD):")
print("=" * 80)

print("\n| # | Method              | Risk | Cap  | Return  | DD     | R/DD   | Trades |")
print("|---|---------------------|------|------|---------|--------|--------|--------|")

for i, (idx, row) in enumerate(results_df.head(15).iterrows(), 1):
    cap_str = f"{row['max_leverage']:.1f}x" if row['max_leverage'] > 0 else "None"
    highlight = "🏆" if i == 1 else ""
    print(f"| {i:2d} | {row['method']:19s} | {row['risk_pct']:4.0f}% | {cap_str:4s} | "
          f"{row['return']:+6.0f}% | {row['max_dd']:5.1f}% | {row['return_dd']:6.2f}x | "
          f"{row['trades']:3.0f} | {highlight}")

# Best
best = results_df.iloc[0]
baseline = results_df[results_df['method'] == 'Baseline'].iloc[0]

print("\n" + "=" * 80)
print("🏆 WINNER:")
print("=" * 80)
print(f"\n  {best['method']}")
print(f"  Risk: {best['risk_pct']:.0f}%")
if best['max_leverage'] > 0:
    print(f"  Cap: {best['max_leverage']:.1f}x")
if best['tiered']:
    print(f"  Tiered: ±20% by 24h range")
print(f"\n  Return: {best['return']:+.2f}%")
print(f"  Max DD: {best['max_dd']:.2f}%")
print(f"  R/DD: {best['return_dd']:.2f}x")
print(f"  Trades: {best['trades']:.0f}")

print(f"\n  vs Baseline:")
print(f"    R/DD: {best['return_dd'] - baseline['return_dd']:+.2f}x ({(best['return_dd'] / baseline['return_dd'] - 1) * 100:+.1f}%)")

print("=" * 80)
