"""
Optimize for R/DD (risk-adjusted returns) 
Keep similar trade count (~40 trades)
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time
from itertools import product

print("=" * 80)
print("OPTIMIZE FOR R/DD (keeping ~40 trades)")
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

def backtest(df, rsi_low, rsi_high, limit_pct, sl_mult, tp_mult, risk_pct):
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

        if prev_row['rsi'] < rsi_low and row['rsi'] >= rsi_low:
            has_signal = True
            direction = 'LONG'
        elif prev_row['rsi'] > rsi_high and row['rsi'] <= rsi_high:
            has_signal = True
            direction = 'SHORT'

        if not has_signal:
            i += 1
            continue

        if pd.notna(row['range_24h']) and row['range_24h'] < MIN_RANGE_24H:
            i += 1
            continue

        signal_price = row['close']
        if direction == 'LONG':
            entry_price = signal_price * (1 + limit_pct / 100)
            sl_price = entry_price - (row['atr'] * sl_mult)
            tp_price = entry_price + (row['atr'] * tp_mult)
        else:
            entry_price = signal_price * (1 - limit_pct / 100)
            sl_price = entry_price + (row['atr'] * sl_mult)
            tp_price = entry_price - (row['atr'] * tp_mult)

        risk_dollars = equity * (risk_pct / 100)
        sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100 if direction == 'LONG' else abs((sl_price - entry_price) / entry_price) * 100
        position_size_dollars = risk_dollars / (sl_distance_pct / 100)

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
                    if prev_bar['rsi'] > rsi_high and bar['rsi'] <= rsi_high:
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
                    if prev_bar['rsi'] < rsi_low and bar['rsi'] >= rsi_low:
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

        trades.append({'exit_type': exit_type, 'pnl_dollars': pnl_dollars, 'equity': equity})
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
    tp_rate = (df_t['exit_type'] == 'TP').sum() / len(df_t) * 100

    return {
        'limit_pct': limit_pct, 'sl_mult': sl_mult, 'tp_mult': tp_mult,
        'return': total_return, 'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t), 'win_rate': win_rate, 'tp_rate': tp_rate
    }

# Parameter grid optimized for R/DD
print("\nParameter grid:")
param_grid = {
    'rsi_low': [25],
    'rsi_high': [70],
    'limit_pct': [0.3, 0.5, 1.0, 2.0, 3.0],
    'sl_mult': [1.0, 1.5, 2.0, 2.5, 3.0, 4.0],
    'tp_mult': [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0],
    'risk_pct': [15]
}

print(f"  Offset: {param_grid['limit_pct']}")
print(f"  SL: {param_grid['sl_mult']}")
print(f"  TP: {param_grid['tp_mult']}")

combinations = list(product(*param_grid.values()))
print(f"\nTotal combinations: {len(combinations)}")

# Run
results = []
print("\nRunning...")
for idx, combo in enumerate(combinations):
    if idx % 20 == 0:
        print(f"  {idx}/{len(combinations)} ({idx/len(combinations)*100:.0f}%)")
    result = backtest(df, *combo)
    if result:
        results.append(result)

print(f"\nDone! {len(results)} valid configs")

# Sort by R/DD
results_df = pd.DataFrame(results).sort_values('return_dd', ascending=False)
results_df.to_csv('melania_rdd_optimized.csv', index=False)
print(f"💾 Saved: melania_rdd_optimized.csv")

# Top 20
print("\n" + "=" * 80)
print("TOP 20 BY R/DD (with trade count filter):")
print("=" * 80)
print("\n| # | Offset | SL  | TP  | Return  | DD    | R/DD   | Trades | Win% | TP%  |")
print("|---|--------|-----|-----|---------|-------|--------|--------|------|------|")

for i, (idx, row) in enumerate(results_df.head(20).iterrows(), 1):
    highlight = "⭐" if row['trades'] >= 35 else ("⚠️" if row['trades'] < 20 else "")
    print(f"| {i:2d} | {row['limit_pct']:4.1f}% | {row['sl_mult']:.1f}x | {row['tp_mult']:.1f}x | "
          f"{row['return']:+6.0f}% | {row['max_dd']:5.1f}% | {row['return_dd']:6.2f}x | "
          f"{row['trades']:3.0f} {highlight:2s} | {row['win_rate']:4.1f}% | {row['tp_rate']:4.1f}% |")

# Best with good trade count (>35 trades)
print("\n" + "=" * 80)
print("🏆 BEST CONFIG (R/DD optimized, 35+ trades):")
print("=" * 80)

# Filter for configs with at least 35 trades
good_trade_count = results_df[results_df['trades'] >= 35]
if len(good_trade_count) > 0:
    best = good_trade_count.iloc[0]
else:
    best = results_df.iloc[0]
    print("\n⚠️  Top config has low trade count, showing best overall:")

print(f"\n  Offset: {best['limit_pct']:.1f}%")
print(f"  SL: {best['sl_mult']:.1f}x ATR")
print(f"  TP: {best['tp_mult']:.1f}x ATR")
print(f"  Risk: 15%")
print(f"  Filter: 24h Range > 15%")
print(f"\n  Return: {best['return']:+.1f}%")
print(f"  Max DD: {best['max_dd']:.1f}%")
print(f"  R/DD: {best['return_dd']:.2f}x ⭐")
print(f"  Trades: {best['trades']:.0f}")
print(f"  Win Rate: {best['win_rate']:.1f}%")
print(f"  TP Rate: {best['tp_rate']:.1f}%")

# Show trade count distribution
print("\n" + "=" * 80)
print("TRADE COUNT DISTRIBUTION:")
print("=" * 80)
trade_bins = [0, 20, 30, 35, 40, 50, 100]
for i in range(len(trade_bins)-1):
    count = len(results_df[(results_df['trades'] >= trade_bins[i]) & (results_df['trades'] < trade_bins[i+1])])
    print(f"  {trade_bins[i]}-{trade_bins[i+1]} trades: {count} configs")

print("=" * 80)
