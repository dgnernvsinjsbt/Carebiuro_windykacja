"""
Test SIMPLEST filter: just skip Jan, Feb, May (bad months)
No other filters - just calendar-based
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

print("=" * 80)
print("Simple Month Filter: Skip Jan, Feb, May ONLY")
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

# Add month
df['month'] = df['timestamp'].dt.to_period('M').astype(str)

# Config
RSI_LOW = 25
RSI_HIGH = 68
LIMIT_PCT = 0.3
SL_MULT = 3.0
TP_MULT = 2.0
RISK_PCT = 10.0

# BAD MONTHS - calendar filter ONLY
BAD_MONTHS = ['2025-01', '2025-02', '2025-05']

trades = []
filtered_count = 0
equity = 100.0

i = 14
while i < len(df):
    row = df.iloc[i]
    prev_row = df.iloc[i-1] if i > 0 else None

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or prev_row is None or pd.isna(prev_row['rsi']):
        i += 1
        continue

    # Check if signal appears
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

    # ONLY filter: bad month
    if row['month'] in BAD_MONTHS:
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
        'month': df.iloc[exit_idx]['month'],
        'direction': direction,
        'exit_type': exit_type,
        'pnl_dollars': pnl_dollars,
        'equity': equity
    })

    i = exit_idx + 1

# Results
print("\n" + "=" * 80)
print("RESULTS:")
print("=" * 80)

if len(trades) == 0:
    print("\n❌ NO TRADES")
else:
    df_trades = pd.DataFrame(trades)

    total_return = ((equity - 100) / 100) * 100
    equity_curve = [100.0] + df_trades['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    max_dd = ((eq - running_max) / running_max * 100).min()
    win_rate = (df_trades['pnl_dollars'] > 0).sum() / len(df_trades) * 100

    print(f"\nTotal Return: {total_return:+.2f}%")
    print(f"Final Equity: ${equity:.2f}")
    print(f"Max Drawdown: {max_dd:.2f}%")
    print(f"Return/DD: {total_return / abs(max_dd):.2f}x" if max_dd != 0 else "Return/DD: N/A")
    print(f"Total Trades: {len(df_trades)}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"\nSignals filtered (bad months): {filtered_count}")

    # Monthly breakdown
    print("\n" + "=" * 80)
    print("MONTHLY BREAKDOWN:")
    print("=" * 80)

    print("\n| Month    | Trades | Winners | Win% | P&L     |")
    print("|----------|--------|---------|------|---------|")

    for month in sorted(df_trades['month'].unique()):
        month_trades = df_trades[df_trades['month'] == month]
        winners = (month_trades['pnl_dollars'] > 0).sum()
        total = len(month_trades)
        win_pct = (winners / total * 100) if total > 0 else 0
        pnl = month_trades['pnl_dollars'].sum()
        print(f"| {month} | {total:6d} | {winners:7d} | {win_pct:3.0f}% | {pnl:+7.2f} |")

    print("\n" + "=" * 80)
    print("COMPARISON:")
    print("=" * 80)

    print("\nNo filters (all 2025):")
    print("  Return: +312.37% | DD: -40.30% | R/DD: 7.75x | Trades: 77")

    print("\nComplex filters (price/ATR/whipsaw):")
    print("  Return: +28.25% | DD: 0.00% | R/DD: 0.00x | Trades: 4 (TOO STRICT)")

    print(f"\nMonth filter ONLY (skip Jan/Feb/May):")
    print(f"  Return: {total_return:+.2f}% | DD: {max_dd:.2f}% | R/DD: {total_return / abs(max_dd):.2f}x | Trades: {len(df_trades)}")

print("\n" + "=" * 80)
