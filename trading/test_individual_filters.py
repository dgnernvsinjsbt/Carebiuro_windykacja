"""
Test each momentum filter INDIVIDUALLY to find the best one
Then try relaxing the thresholds
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

print("=" * 80)
print("Individual Filter Testing: Find the best single filter")
print("=" * 80)

# Download full 2025 data
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
df['atr_pct'] = (df['atr'] / df['close']) * 100

# Momentum indicators
df['returns_24h'] = df['close'].pct_change(24) * 100
df['high_24h'] = df['high'].rolling(24).max()
df['low_24h'] = df['low'].rolling(24).min()
df['range_24h'] = ((df['high_24h'] - df['low_24h']) / df['low_24h']) * 100

df['month'] = df['timestamp'].dt.to_period('M').astype(str)

# Config
RSI_LOW = 25
RSI_HIGH = 68
LIMIT_PCT = 0.3
SL_MULT = 3.0
TP_MULT = 2.0
RISK_PCT = 10.0

def backtest(df, filter_name, threshold=None):
    """Backtest with single filter"""
    trades = []
    filtered_count = 0
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

        # Apply single filter
        if filter_name == '24h_return':
            if pd.notna(row['returns_24h']) and abs(row['returns_24h']) < threshold:
                filtered_count += 1
                i += 1
                continue
        elif filter_name == '24h_range':
            if pd.notna(row['range_24h']) and row['range_24h'] < threshold:
                filtered_count += 1
                i += 1
                continue
        elif filter_name == 'atr_pct':
            if pd.notna(row['atr_pct']) and row['atr_pct'] < threshold:
                filtered_count += 1
                i += 1
                continue

        # Take trade
        signal_price = row['close']
        if direction == 'LONG':
            entry_price = signal_price * (1 + LIMIT_PCT / 100)
            sl_price = entry_price - (row['atr'] * SL_MULT)
            tp_price = entry_price + (row['atr'] * TP_MULT)
        else:
            entry_price = signal_price * (1 - LIMIT_PCT / 100)
            sl_price = entry_price + (row['atr'] * SL_MULT)
            tp_price = entry_price - (row['atr'] * TP_MULT)

        risk_dollars = equity * (RISK_PCT / 100)
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

        trades.append({
            'exit_type': exit_type,
            'pnl_dollars': pnl_dollars,
            'equity': equity
        })

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
        'filter': filter_name,
        'threshold': threshold,
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'filtered_count': filtered_count
    }

# Baseline (no filters)
print("\nBaseline (no filters):")
baseline = backtest(df, None, None)
print(f"  Return: {baseline['return']:+.2f}% | DD: {baseline['max_dd']:.2f}% | R/DD: {baseline['return_dd']:.2f}x")
print(f"  Trades: {baseline['trades']} | Win Rate: {baseline['win_rate']:.1f}%")

# Test each filter at RELAXED thresholds (25th percentile instead of midpoint)
print("\n" + "=" * 80)
print("Testing individual filters at RELAXED thresholds:")
print("=" * 80)

filters_to_test = [
    ('24h_return', [0.5, 1.0, 1.44, 2.0]),  # Original: 1.44
    ('24h_range', [15.0, 18.0, 21.18, 25.0]),  # Original: 21.18
    ('atr_pct', [2.0, 2.5, 2.87, 3.0])  # Original: 2.87
]

results = []

for filter_name, thresholds in filters_to_test:
    print(f"\n{filter_name.upper()}:")
    for threshold in thresholds:
        result = backtest(df, filter_name, threshold)
        if result:
            results.append(result)
            print(f"  Threshold {threshold:5.2f}: Return {result['return']:+6.2f}% | DD {result['max_dd']:6.2f}% | "
                  f"R/DD {result['return_dd']:5.2f}x | Trades {result['trades']:2d} | "
                  f"Win% {result['win_rate']:4.1f}% | Filtered {result['filtered_count']}")

# Find best by R/DD
print("\n" + "=" * 80)
print("BEST CONFIGURATION (by Return/DD):")
print("=" * 80)

best = max(results, key=lambda x: x['return_dd'])

print(f"\nFilter: {best['filter'].upper()}")
print(f"Threshold: >{best['threshold']:.2f}")
print(f"Return: {best['return']:+.2f}%")
print(f"Max DD: {best['max_dd']:.2f}%")
print(f"R/DD: {best['return_dd']:.2f}x ⭐")
print(f"Trades: {best['trades']}")
print(f"Win Rate: {best['win_rate']:.1f}%")
print(f"Filtered: {best['filtered_count']} signals")

print(f"\nImprovement vs baseline:")
print(f"  Return: {best['return'] - baseline['return']:+.2f}%")
print(f"  Max DD: {best['max_dd'] - baseline['max_dd']:+.2f}%")
print(f"  R/DD: {best['return_dd'] - baseline['return_dd']:+.2f}x")

print("\n" + "=" * 80)
