"""
Analyze the 73 filtered trades - were they good or bad?
This will show if filters helped or hurt
"""

import pandas as pd
import numpy as np

print("Analyzing filtered vs accepted trades...")

# Load the full 2025 data (already downloaded)
df = pd.read_csv('trading/melania_full_2025.csv', parse_dates=['timestamp']) if False else None

# Since we can't easily reload, let me create a simpler version:
# Run backtest and track ALL signals (filtered + accepted) with their outcomes

import ccxt
from datetime import datetime, timezone
import time

exchange = ccxt.bingx({'enableRateLimit': True})

start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
end_date = datetime(2025, 12, 15, tzinfo=timezone.utc)

start_ts = int(start_date.timestamp() * 1000)
end_ts = int(end_date.timestamp() * 1000)

print("Downloading data...")
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

df['sma20'] = df['close'].rolling(20).mean()
df['price_vs_sma20'] = ((df['close'] - df['sma20']) / df['sma20']) * 100

df['rsi_cross_below_30'] = ((df['rsi'].shift(1) >= 30) & (df['rsi'] < 30)).astype(int)
df['rsi_crosses_30d'] = df['rsi_cross_below_30'].rolling(720).sum()

# Month
df['month'] = df['timestamp'].dt.to_period('M').astype(str)

# Config
RSI_LOW = 25
RSI_HIGH = 68
LIMIT_PCT = 0.3
SL_MULT = 3.0
TP_MULT = 2.0
RISK_PCT = 10.0

# Simpler approach: just check month
BAD_MONTHS = ['2025-01', '2025-02', '2025-05']  # Known bad months

all_signals = []
equity = 100.0

i = 720
while i < len(df):
    row = df.iloc[i]
    prev_row = df.iloc[i-1]

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(prev_row['rsi']):
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

    # Check filters
    in_bad_month = row['month'] in BAD_MONTHS
    price_too_far = pd.notna(row['price_vs_sma20']) and abs(row['price_vs_sma20']) > 1.5
    atr_too_high = pd.notna(row['atr_pct']) and row['atr_pct'] > 2.9
    too_many_whipsaws = pd.notna(row['rsi_crosses_30d']) and row['rsi_crosses_30d'] > 15

    filtered = in_bad_month or price_too_far or atr_too_high or too_many_whipsaws

    # Simulate trade outcome
    signal_price = row['close']
    if direction == 'LONG':
        entry_price = signal_price * (1 + LIMIT_PCT / 100)
        sl_price = entry_price - (row['atr'] * SL_MULT)
        tp_price = entry_price + (row['atr'] * TP_MULT)
    else:
        entry_price = signal_price * (1 - LIMIT_PCT / 100)
        sl_price = entry_price + (row['atr'] * SL_MULT)
        tp_price = entry_price - (row['atr'] * TP_MULT)

    # Check for fill
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

    # Find exit
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

    # Calculate outcome
    if direction == 'LONG':
        price_change_pct = ((exit_price - entry_price) / entry_price) * 100
    else:
        price_change_pct = ((entry_price - exit_price) / entry_price) * 100

    risk_dollars = equity * (RISK_PCT / 100)
    sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100 if direction == 'LONG' else abs((sl_price - entry_price) / entry_price) * 100
    position_size = risk_dollars / (sl_distance_pct / 100)

    pnl_dollars = position_size * (price_change_pct / 100) - (position_size * 0.001)

    all_signals.append({
        'timestamp': row['timestamp'],
        'month': row['month'],
        'direction': direction,
        'filtered': filtered,
        'in_bad_month': in_bad_month,
        'price_too_far': price_too_far,
        'atr_too_high': atr_too_high,
        'too_many_whipsaws': too_many_whipsaws,
        'exit_type': exit_type,
        'pnl_dollars': pnl_dollars,
        'winner': pnl_dollars > 0
    })

    if not filtered:
        equity += pnl_dollars

    i = exit_idx + 1

# Analyze
df_signals = pd.DataFrame(all_signals)

print("\n" + "=" * 80)
print("FILTER EFFECTIVENESS ANALYSIS:")
print("=" * 80)

filtered_trades = df_signals[df_signals['filtered'] == True]
accepted_trades = df_signals[df_signals['filtered'] == False]

print(f"\nAccepted trades: {len(accepted_trades)}")
print(f"  Winners: {accepted_trades['winner'].sum()} ({accepted_trades['winner'].sum()/len(accepted_trades)*100:.1f}%)")
print(f"  Losers: {(~accepted_trades['winner']).sum()}")
print(f"  Total P&L: ${accepted_trades['pnl_dollars'].sum():.2f}")

print(f"\nFiltered trades: {len(filtered_trades)}")
print(f"  Winners: {filtered_trades['winner'].sum()} ({filtered_trades['winner'].sum()/len(filtered_trades)*100:.1f}%)")
print(f"  Losers: {(~filtered_trades['winner']).sum()}")
print(f"  Total P&L if taken: ${filtered_trades['pnl_dollars'].sum():.2f}")

print("\n" + "=" * 80)
print("Filter breakdown:")
print(f"  Bad month filter: {filtered_trades['in_bad_month'].sum()} trades")
print(f"    Would have been: {filtered_trades[filtered_trades['in_bad_month']]['winner'].sum()} winners, "
      f"{(~filtered_trades[filtered_trades['in_bad_month']]['winner']).sum()} losers")
print(f"    Total P&L: ${filtered_trades[filtered_trades['in_bad_month']]['pnl_dollars'].sum():.2f}")

print(f"\n  Price filter: {filtered_trades['price_too_far'].sum()} trades")
print(f"  ATR filter: {filtered_trades['atr_too_high'].sum()} trades")
print(f"  Whipsaw filter: {filtered_trades['too_many_whipsaws'].sum()} trades")

print("\n" + "=" * 80)
print("VERDICT:")
print("=" * 80)

if filtered_trades['pnl_dollars'].sum() < 0:
    print(f"\n✅ Filters HELPED: Avoided ${abs(filtered_trades['pnl_dollars'].sum()):.2f} in losses")
else:
    print(f"\n❌ Filters HURT: Missed out on ${filtered_trades['pnl_dollars'].sum():.2f} in profits")

print("\n" + "=" * 80)
