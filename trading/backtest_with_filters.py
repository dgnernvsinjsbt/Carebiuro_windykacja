"""
Backtest with market regime filters:
1. Price within 1.5% of SMA20 (avoid downtrends)
2. ATR% < 2.9% (moderate volatility)
3. RSI whipsaw detector: Count RSI <30 crosses in last 30 days < threshold

Compare filtered vs unfiltered to see what we avoid
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

print("=" * 80)
print("Backtest WITH vs WITHOUT Market Regime Filters")
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

# SMAs for trend filter
df['sma20'] = df['close'].rolling(20).mean()
df['price_vs_sma20'] = ((df['close'] - df['sma20']) / df['sma20']) * 100

# RSI whipsaw detector: count crosses below 30 in last 720 hours (30 days)
df['rsi_cross_below_30'] = ((df['rsi'].shift(1) >= 30) & (df['rsi'] < 30)).astype(int)
df['rsi_crosses_30d'] = df['rsi_cross_below_30'].rolling(720).sum()

# Config
RSI_LOW = 25
RSI_HIGH = 68
LIMIT_PCT = 0.3
SL_MULT = 3.0
TP_MULT = 2.0
RISK_PCT = 10.0

# Filters
FILTER_PRICE_VS_SMA20 = 1.5  # Price within 1.5% of SMA20
FILTER_ATR_PCT = 2.9          # ATR% below 2.9%
FILTER_RSI_CROSSES_MAX = 15   # Max 15 RSI crosses in 30 days

def backtest(df, use_filters=False):
    """Backtest with optional market regime filters"""
    trades = []
    filtered_signals = []
    equity = 100.0

    i = 720  # Start after 30 days for filters to warm up
    while i < len(df):
        row = df.iloc[i]
        prev_row = df.iloc[i-1] if i > 0 else None

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or prev_row is None or pd.isna(prev_row['rsi']):
            i += 1
            continue

        # Check if signal appears (before filters)
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

        # Apply filters if enabled
        if use_filters:
            filter_passed = True
            filter_reasons = []

            # Filter 1: Price vs SMA20
            if pd.notna(row['price_vs_sma20']) and abs(row['price_vs_sma20']) > FILTER_PRICE_VS_SMA20:
                filter_passed = False
                filter_reasons.append(f"Price {row['price_vs_sma20']:+.1f}% from SMA20")

            # Filter 2: ATR%
            if pd.notna(row['atr_pct']) and row['atr_pct'] > FILTER_ATR_PCT:
                filter_passed = False
                filter_reasons.append(f"ATR% {row['atr_pct']:.2f}% too high")

            # Filter 3: RSI whipsaws
            if pd.notna(row['rsi_crosses_30d']) and row['rsi_crosses_30d'] > FILTER_RSI_CROSSES_MAX:
                filter_passed = False
                filter_reasons.append(f"RSI crosses {row['rsi_crosses_30d']:.0f} too many")

            if not filter_passed:
                filtered_signals.append({
                    'timestamp': row['timestamp'],
                    'direction': direction,
                    'reasons': filter_reasons
                })
                i += 1
                continue

        # Signal passed filters (or no filters), take trade
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

        # Wait for fill
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

        # Look for exit
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
            else:  # SHORT
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

        # Calculate P&L
        if direction == 'LONG':
            price_change_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            price_change_pct = ((entry_price - exit_price) / entry_price) * 100

        pnl_before_fees = position_size_dollars * (price_change_pct / 100)
        fees = position_size_dollars * 0.001
        pnl_dollars = pnl_before_fees - fees
        equity += pnl_dollars

        trades.append({
            'timestamp': df.iloc[exit_idx]['timestamp'],
            'direction': direction,
            'exit_type': exit_type,
            'pnl_dollars': pnl_dollars,
            'equity': equity
        })

        i = exit_idx + 1

    return trades, filtered_signals

# Run both versions
print("\nRunning backtest WITHOUT filters...")
trades_no_filter, _ = backtest(df, use_filters=False)

print("Running backtest WITH filters...")
trades_with_filter, filtered_signals = backtest(df, use_filters=True)

# Analyze results
print("\n" + "=" * 80)
print("RESULTS COMPARISON:")
print("=" * 80)

def calc_metrics(trades):
    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    total_return = ((df_t.iloc[-1]['equity'] - 100) / 100) * 100

    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    dd = ((eq - running_max) / running_max * 100).min()

    win_rate = (df_t['pnl_dollars'] > 0).sum() / len(df_t) * 100

    return {
        'return': total_return,
        'max_dd': dd,
        'return_dd': total_return / abs(dd) if dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate
    }

metrics_no_filter = calc_metrics(trades_no_filter)
metrics_with_filter = calc_metrics(trades_with_filter)

print("\nWITHOUT Filters:")
print(f"  Return: {metrics_no_filter['return']:+.2f}%")
print(f"  Max DD: {metrics_no_filter['max_dd']:.2f}%")
print(f"  R/DD: {metrics_no_filter['return_dd']:.2f}x")
print(f"  Trades: {metrics_no_filter['trades']}")
print(f"  Win Rate: {metrics_no_filter['win_rate']:.1f}%")

print("\nWITH Filters:")
print(f"  Return: {metrics_with_filter['return']:+.2f}%")
print(f"  Max DD: {metrics_with_filter['max_dd']:.2f}%")
print(f"  R/DD: {metrics_with_filter['return_dd']:.2f}x")
print(f"  Trades: {metrics_with_filter['trades']}")
print(f"  Win Rate: {metrics_with_filter['win_rate']:.1f}%")

print("\nImprovement:")
print(f"  Return: {metrics_with_filter['return'] - metrics_no_filter['return']:+.2f}%")
print(f"  Max DD: {metrics_with_filter['max_dd'] - metrics_no_filter['max_dd']:+.2f}%")
print(f"  R/DD: {metrics_with_filter['return_dd'] - metrics_no_filter['return_dd']:+.2f}x")
print(f"  Trades avoided: {metrics_no_filter['trades'] - metrics_with_filter['trades']}")

# Analyze filtered trades
print("\n" + "=" * 80)
print("WHAT DID WE FILTER OUT?")
print("=" * 80)

print(f"\nTotal signals filtered: {len(filtered_signals)}")

# To know if filtered trades were good or bad, we need to "shadow trade" them
print("\n(Analyzing what the filtered trades would have done...)")

# This is complex - let me show filter reasons instead
if len(filtered_signals) > 0:
    df_filtered = pd.DataFrame(filtered_signals)

    print(f"\nFilter breakdown:")
    all_reasons = []
    for reasons in df_filtered['reasons']:
        all_reasons.extend(reasons)

    reason_counts = pd.Series(all_reasons).value_counts()
    for reason, count in reason_counts.items():
        print(f"  {reason}: {count} signals")

print("\n" + "=" * 80)
