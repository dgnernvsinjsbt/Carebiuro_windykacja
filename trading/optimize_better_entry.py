"""
Better Entry Optimization: Larger offset = Better entry = Tighter SL + Bigger TP
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time
from itertools import product

print("=" * 80)
print("BETTER ENTRY OPTIMIZATION")
print("Logic: Wait for better price → Tighter SL + Bigger TP")
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
    sl_rate = (df_t['exit_type'] == 'SL').sum() / len(df_t) * 100

    return {
        'rsi_low': rsi_low, 'rsi_high': rsi_high, 'limit_pct': limit_pct,
        'sl_mult': sl_mult, 'tp_mult': tp_mult, 'risk_pct': risk_pct,
        'return': total_return, 'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t), 'win_rate': win_rate, 'tp_rate': tp_rate, 'sl_rate': sl_rate
    }

# FOCUSED grid: Larger offsets + Tighter SL + Bigger TP
print("\nParameter grid (BETTER ENTRY focus):")
param_grid = {
    'rsi_low': [25],              # Keep best
    'rsi_high': [70],             # Keep best
    'limit_pct': [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],  # LARGER offsets
    'sl_mult': [1.5, 2.0, 2.5, 3.0],              # TIGHTER stops
    'tp_mult': [2.0, 2.5, 3.0, 4.0, 5.0],         # BIGGER targets
    'risk_pct': [12, 15]                           # Keep aggressive
}

for k, v in param_grid.items():
    print(f"  {k}: {v}")

combinations = list(product(*param_grid.values()))
print(f"\nTotal combinations: {len(combinations)}")

# Run optimization
results = []
print("\nRunning...")
for idx, combo in enumerate(combinations):
    if idx % 20 == 0:
        print(f"  {idx}/{len(combinations)} ({idx/len(combinations)*100:.0f}%)")
    result = backtest(df, *combo)
    if result:
        results.append(result)

print(f"\nDone! {len(results)} valid configs")

# Results
results_df = pd.DataFrame(results).sort_values('return_dd', ascending=False)
results_df.to_csv('melania_better_entry_results.csv', index=False)
print(f"💾 Saved: melania_better_entry_results.csv")

# Top 15
print("\n" + "=" * 80)
print("TOP 15 CONFIGURATIONS:")
print("=" * 80)
print("\n| # | Offset | SL  | TP  | Risk | Return  | DD    | R/DD   | Trades | Win% | TP%  | SL%  |")
print("|---|--------|-----|-----|------|---------|-------|--------|--------|------|------|------|")

for i, (idx, row) in enumerate(results_df.head(15).iterrows(), 1):
    print(f"| {i:2d} | {row['limit_pct']:4.1f}% | {row['sl_mult']:.1f}x | {row['tp_mult']:.1f}x | "
          f"{row['risk_pct']:2.0f}% | {row['return']:+6.0f}% | {row['max_dd']:5.1f}% | "
          f"{row['return_dd']:6.2f}x | {row['trades']:3.0f} | {row['win_rate']:4.1f}% | "
          f"{row['tp_rate']:4.1f}% | {row['sl_rate']:4.1f}% |")

# Winner
best = results_df.iloc[0]
print("\n" + "=" * 80)
print("🏆 BEST ENTRY CONFIG:")
print("=" * 80)
print(f"\n  RSI: 25/70")
print(f"  Offset: {best['limit_pct']:.1f}% (wait for better price)")
print(f"  SL: {best['sl_mult']:.1f}x ATR (tighter stop)")
print(f"  TP: {best['tp_mult']:.1f}x ATR (bigger target)")
print(f"  Risk: {best['risk_pct']:.0f}%")
print(f"\n  Return: {best['return']:+.1f}%")
print(f"  Max DD: {best['max_dd']:.1f}%")
print(f"  R/DD: {best['return_dd']:.2f}x ⭐")
print(f"  Trades: {best['trades']:.0f}")
print(f"  Win Rate: {best['win_rate']:.1f}%")
print(f"  TP Rate: {best['tp_rate']:.1f}% | SL Rate: {best['sl_rate']:.1f}%")
print(f"\n  vs Previous Best (16.22x): {best['return_dd'] - 16.22:+.2f}x ({(best['return_dd'] / 16.22 - 1) * 100:+.0f}%)")

# Show fill rate by offset
print("\n" + "=" * 80)
print("FILL RATE BY OFFSET (higher offset = fewer fills but better entries):")
print("=" * 80)
fill_rates = results_df.groupby('limit_pct')['trades'].mean().sort_index()
for offset, trades in fill_rates.items():
    print(f"  {offset:.1f}% offset → avg {trades:.0f} trades")

print("=" * 80)
