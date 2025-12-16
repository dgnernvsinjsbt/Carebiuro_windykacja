"""
Monthly breakdown: 24h Range > 15% filter
Show how each month performs with the filter
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

print("=" * 80)
print("Monthly Breakdown: 24h Range > 15% Filter")
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

# 24h range
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

MIN_RANGE_24H = 15.0  # FILTER

def backtest(df, use_filter=False):
    """Backtest with optional 24h range filter"""
    trades = []
    signals_by_month = {}
    filtered_by_month = {}
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

        # Track signals by month
        month = row['month']
        if month not in signals_by_month:
            signals_by_month[month] = 0
            filtered_by_month[month] = 0
        signals_by_month[month] += 1

        # Apply filter
        if use_filter:
            if pd.notna(row['range_24h']) and row['range_24h'] < MIN_RANGE_24H:
                filtered_by_month[month] += 1
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
            'timestamp': df.iloc[exit_idx]['timestamp'],
            'month': df.iloc[exit_idx]['month'],
            'direction': direction,
            'exit_type': exit_type,
            'pnl_dollars': pnl_dollars,
            'equity': equity
        })

        i = exit_idx + 1

    return trades, signals_by_month, filtered_by_month

# Run both versions
print("\nRunning backtest WITHOUT filter...")
trades_no_filter, signals_no_filter, _ = backtest(df, use_filter=False)

print("Running backtest WITH 24h range > 15% filter...")
trades_with_filter, signals_with_filter, filtered_with_filter = backtest(df, use_filter=True)

# Monthly analysis
print("\n" + "=" * 80)
print("MONTHLY BREAKDOWN:")
print("=" * 80)

df_no_filter = pd.DataFrame(trades_no_filter)
df_with_filter = pd.DataFrame(trades_with_filter)

all_months = sorted(set(df_no_filter['month'].unique()) | set(df_with_filter['month'].unique()))

print("\n| Month    | No Filter         |           | With Filter       |           | Filtered | Status |")
print("|----------|-------------------|-----------|-------------------|-----------|----------|--------|")
print("|          | Trades   Win%  P&L| Equity    | Trades   Win%  P&L| Equity    | Out      |        |")
print("|----------|-------------------|-----------|-------------------|-----------|----------|--------|")

equity_no_filter = 100.0
equity_with_filter = 100.0

for month in all_months:
    # No filter stats
    month_trades_no = df_no_filter[df_no_filter['month'] == month]
    if len(month_trades_no) > 0:
        trades_no = len(month_trades_no)
        winners_no = (month_trades_no['pnl_dollars'] > 0).sum()
        win_rate_no = (winners_no / trades_no) * 100
        pnl_no = month_trades_no['pnl_dollars'].sum()
        equity_no_filter += pnl_no
        equity_end_no = month_trades_no.iloc[-1]['equity']
    else:
        trades_no = 0
        win_rate_no = 0
        pnl_no = 0
        equity_end_no = equity_no_filter

    # With filter stats
    month_trades_with = df_with_filter[df_with_filter['month'] == month]
    if len(month_trades_with) > 0:
        trades_with = len(month_trades_with)
        winners_with = (month_trades_with['pnl_dollars'] > 0).sum()
        win_rate_with = (winners_with / trades_with) * 100
        pnl_with = month_trades_with['pnl_dollars'].sum()
        equity_with_filter += pnl_with
        equity_end_with = month_trades_with.iloc[-1]['equity']
    else:
        trades_with = 0
        win_rate_with = 0
        pnl_with = 0
        equity_end_with = equity_with_filter

    # Filtered count
    filtered_count = filtered_with_filter.get(month, 0)

    # Status
    if pnl_no < -10:
        status = "❌ BAD"
    elif pnl_no < 0:
        status = "⚠️ LOSS"
    elif pnl_no < 10:
        status = "✅ OK"
    else:
        status = "✅ GOOD"

    print(f"| {month} | {trades_no:2d}  {win_rate_no:4.0f}% {pnl_no:+6.1f} | ${equity_end_no:6.1f} | "
          f"{trades_with:2d}  {win_rate_with:4.0f}% {pnl_with:+6.1f} | ${equity_end_with:6.1f} | "
          f"{filtered_count:2d}       | {status:6s} |")

# Summary
print("\n" + "=" * 80)
print("SUMMARY:")
print("=" * 80)

def calc_summary(trades):
    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    equity = df_t.iloc[-1]['equity']
    total_return = ((equity - 100) / 100) * 100

    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    max_dd = ((eq - running_max) / running_max * 100).min()

    win_rate = (df_t['pnl_dollars'] > 0).sum() / len(df_t) * 100

    # Best/worst months
    monthly_pnl = df_t.groupby('month')['pnl_dollars'].sum().sort_values()
    best_month = monthly_pnl.idxmax()
    best_month_pnl = monthly_pnl.max()
    worst_month = monthly_pnl.idxmin()
    worst_month_pnl = monthly_pnl.min()

    return {
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'equity': equity,
        'best_month': best_month,
        'best_month_pnl': best_month_pnl,
        'worst_month': worst_month,
        'worst_month_pnl': worst_month_pnl
    }

summary_no = calc_summary(trades_no_filter)
summary_with = calc_summary(trades_with_filter)

print("\nWITHOUT Filter (baseline):")
print(f"  Return: {summary_no['return']:+.2f}% | DD: {summary_no['max_dd']:.2f}% | R/DD: {summary_no['return_dd']:.2f}x")
print(f"  Trades: {summary_no['trades']} | Win Rate: {summary_no['win_rate']:.1f}%")
print(f"  Best Month: {summary_no['best_month']} (+${summary_no['best_month_pnl']:.2f})")
print(f"  Worst Month: {summary_no['worst_month']} (${summary_no['worst_month_pnl']:.2f})")

print("\nWITH 24h Range > 15% Filter:")
print(f"  Return: {summary_with['return']:+.2f}% | DD: {summary_with['max_dd']:.2f}% | R/DD: {summary_with['return_dd']:.2f}x")
print(f"  Trades: {summary_with['trades']} | Win Rate: {summary_with['win_rate']:.1f}%")
print(f"  Best Month: {summary_with['best_month']} (+${summary_with['best_month_pnl']:.2f})")
print(f"  Worst Month: {summary_with['worst_month']} (${summary_with['worst_month_pnl']:.2f})")

print("\nImprovement:")
print(f"  Return: {summary_with['return'] - summary_no['return']:+.2f}%")
print(f"  Max DD: {summary_with['max_dd'] - summary_no['max_dd']:+.2f}%")
print(f"  R/DD: {summary_with['return_dd'] - summary_no['return_dd']:+.2f}x ⭐")
print(f"  Win Rate: {summary_with['win_rate'] - summary_no['win_rate']:+.1f}%")

print("\n" + "=" * 80)
