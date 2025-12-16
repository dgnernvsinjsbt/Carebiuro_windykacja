"""
Detailed monthly breakdown for WINNER config (20% risk)
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

print("=" * 80)
print("MONTHLY BREAKDOWN - 20% RISK CONFIGURATION")
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
df['month'] = df['timestamp'].dt.to_period('M').astype(str)

# WINNER CONFIG
MIN_RANGE_24H = 15.0
RSI_LOW = 25
RSI_HIGH = 70
LIMIT_PCT = 0.3
SL_MULT = 1.5
TP_MULT = 2.5
RISK_PCT = 20.0  # Winner

print("\n" + "=" * 80)
print("CONFIGURATION:")
print("=" * 80)
print(f"  RSI: {RSI_LOW}/{RSI_HIGH}")
print(f"  Offset: {LIMIT_PCT}%")
print(f"  SL: {SL_MULT}x ATR")
print(f"  TP: {TP_MULT}x ATR")
print(f"  Risk: {RISK_PCT}% per trade")
print(f"  Filter: 24h Range > {MIN_RANGE_24H}%")

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
        'timestamp': df.iloc[exit_idx]['timestamp'],
        'month': df.iloc[exit_idx]['month'],
        'direction': direction,
        'exit_type': exit_type,
        'pnl_dollars': pnl_dollars,
        'equity': equity
    })

    i = exit_idx + 1

# Analysis
df_trades = pd.DataFrame(trades)

print("\n" + "=" * 80)
print("OVERALL PERFORMANCE:")
print("=" * 80)

total_return = ((equity - 100) / 100) * 100
equity_curve = [100.0] + df_trades['equity'].tolist()
eq = pd.Series(equity_curve)
running_max = eq.expanding().max()
max_dd = ((eq - running_max) / running_max * 100).min()

win_rate = (df_trades['pnl_dollars'] > 0).sum() / len(df_trades) * 100
tp_rate = (df_trades['exit_type'] == 'TP').sum() / len(df_trades) * 100
sl_rate = (df_trades['exit_type'] == 'SL').sum() / len(df_trades) * 100

print(f"\n  Starting: $100.00")
print(f"  Ending: ${equity:,.2f}")
print(f"  Total Return: {total_return:+.2f}%")
print(f"  Max Drawdown: {max_dd:.2f}%")
print(f"  Return/DD: {total_return / abs(max_dd):.2f}x ⭐⭐⭐")
print(f"\n  Total Trades: {len(df_trades)}")
print(f"  Win Rate: {win_rate:.1f}%")
print(f"  TP Rate: {tp_rate:.1f}%")
print(f"  SL Rate: {sl_rate:.1f}%")

# Monthly breakdown
print("\n" + "=" * 80)
print("MONTHLY BREAKDOWN:")
print("=" * 80)

print("\n| Month    | Trades | Winners | Losers | Win%  | TP%  | SL%  | Monthly P&L | Monthly Return | Equity      | Monthly DD |")
print("|----------|--------|---------|--------|-------|------|------|-------------|----------------|-------------|------------|")

equity_start = 100.0

for month in sorted(df_trades['month'].unique()):
    month_trades = df_trades[df_trades['month'] == month]
    
    winners = (month_trades['pnl_dollars'] > 0).sum()
    losers = (month_trades['pnl_dollars'] < 0).sum()
    total = len(month_trades)
    win_pct = (winners / total * 100) if total > 0 else 0
    
    tp = (month_trades['exit_type'] == 'TP').sum()
    tp_pct = (tp / total * 100) if total > 0 else 0
    sl = (month_trades['exit_type'] == 'SL').sum()
    sl_pct = (sl / total * 100) if total > 0 else 0
    
    pnl = month_trades['pnl_dollars'].sum()
    equity_end = month_trades.iloc[-1]['equity']
    monthly_return = ((equity_end - equity_start) / equity_start) * 100
    
    # Monthly DD
    month_equity = [equity_start] + month_trades['equity'].tolist()
    month_eq = pd.Series(month_equity)
    month_max = month_eq.expanding().max()
    month_dd = ((month_eq - month_max) / month_max * 100).min()
    
    print(f"| {month} | {total:6d} | {winners:7d} | {losers:6d} | {win_pct:5.1f}% | {tp_pct:4.0f}% | {sl_pct:4.0f}% | "
          f"{pnl:+11.2f} | {monthly_return:+13.2f}% | ${equity_end:10,.2f} | {month_dd:9.2f}% |")
    
    equity_start = equity_end

# Best/Worst months
print("\n" + "=" * 80)
print("BEST & WORST MONTHS:")
print("=" * 80)

monthly_returns = []
equity_tracker = 100.0
for month in sorted(df_trades['month'].unique()):
    month_trades = df_trades[df_trades['month'] == month]
    month_end = month_trades.iloc[-1]['equity']
    month_return = ((month_end - equity_tracker) / equity_tracker) * 100
    monthly_returns.append({'month': month, 'return': month_return})
    equity_tracker = month_end

monthly_returns_df = pd.DataFrame(monthly_returns).sort_values('return', ascending=False)

print("\n🏆 Best Months:")
for i, row in monthly_returns_df.head(3).iterrows():
    print(f"  {row['month']}: {row['return']:+.2f}%")

print("\n❌ Worst Months:")
for i, row in monthly_returns_df.tail(3).iterrows():
    print(f"  {row['month']}: {row['return']:+.2f}%")

# Save
df_trades.to_csv('melania_20pct_risk_trades.csv', index=False)
print(f"\n💾 Saved to: melania_20pct_risk_trades.csv")

print("\n" + "=" * 80)
print("✅ ANALYSIS COMPLETE")
print("=" * 80)
