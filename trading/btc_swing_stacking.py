#!/usr/bin/env python3
"""
BTC Swing Trading with Position Stacking
Inspired by BingX trader profile: patient, position stacking, 1-7 day holds
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Load 1h data for swing signals
df_1h = pd.read_csv('btc_1h_90d.csv')
df_1h.columns = df_1h.columns.str.lower()
df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
df_1h = df_1h.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("BTC SWING TRADING - Position Stacking Strategy")
print("=" * 80)
print(f"\nData: {len(df_1h)} 1h candles (90 days)")
print(f"Price range: ${df_1h['close'].min():.0f} - ${df_1h['close'].max():.0f}")

# Calculate indicators on 1h chart
df_1h['ema_fast'] = calculate_ema(df_1h['close'], 12)
df_1h['ema_slow'] = calculate_ema(df_1h['close'], 26)
df_1h['ema_trend'] = calculate_ema(df_1h['close'], 50)
df_1h['rsi'] = calculate_rsi(df_1h['close'], 14)

# Trend signals
df_1h['bullish_trend'] = (df_1h['ema_fast'] > df_1h['ema_slow']) & (df_1h['close'] > df_1h['ema_trend'])
df_1h['bearish_trend'] = (df_1h['ema_fast'] < df_1h['ema_slow']) & (df_1h['close'] < df_1h['ema_trend'])

# Test multiple swing strategies
strategies = []

# Strategy 1: EMA Crossover with Trend (Basic Swing)
print("\n" + "-" * 80)
print("STRATEGY 1: EMA Crossover Swing (12/26/50)")
print("-" * 80)

positions = []
for i in range(50, len(df_1h)):
    row = df_1h.iloc[i]
    prev = df_1h.iloc[i-1]

    # LONG: Fast EMA crosses above slow, price above trend EMA
    if (prev['ema_fast'] <= prev['ema_slow'] and
        row['ema_fast'] > row['ema_slow'] and
        row['close'] > row['ema_trend']):

        entry_price = row['close']
        entry_time = row['timestamp']
        direction = 'LONG'

        # Find exit (opposite signal or 7 days)
        exit_found = False
        for j in range(i+1, min(i+168, len(df_1h))):  # 168h = 7 days
            exit_row = df_1h.iloc[j]

            # Exit on opposite signal
            if exit_row['ema_fast'] < exit_row['ema_slow']:
                exit_price = exit_row['close']
                exit_time = exit_row['timestamp']
                exit_reason = 'SIGNAL'
                exit_found = True
                break

        if not exit_found:
            j = min(i+167, len(df_1h)-1)
            exit_price = df_1h.iloc[j]['close']
            exit_time = df_1h.iloc[j]['timestamp']
            exit_reason = 'TIME'

        pnl_pct = (exit_price - entry_price) / entry_price * 100
        hold_hours = (exit_time - entry_time).total_seconds() / 3600

        positions.append({
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'hold_hours': hold_hours,
            'exit_reason': exit_reason
        })

    # SHORT: Fast EMA crosses below slow, price below trend EMA
    elif (prev['ema_fast'] >= prev['ema_slow'] and
          row['ema_fast'] < row['ema_slow'] and
          row['close'] < row['ema_trend']):

        entry_price = row['close']
        entry_time = row['timestamp']
        direction = 'SHORT'

        exit_found = False
        for j in range(i+1, min(i+168, len(df_1h))):
            exit_row = df_1h.iloc[j]

            if exit_row['ema_fast'] > exit_row['ema_slow']:
                exit_price = exit_row['close']
                exit_time = exit_row['timestamp']
                exit_reason = 'SIGNAL'
                exit_found = True
                break

        if not exit_found:
            j = min(i+167, len(df_1h)-1)
            exit_price = df_1h.iloc[j]['close']
            exit_time = df_1h.iloc[j]['timestamp']
            exit_reason = 'TIME'

        pnl_pct = (entry_price - exit_price) / entry_price * 100
        hold_hours = (exit_time - entry_time).total_seconds() / 3600

        positions.append({
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'hold_hours': hold_hours,
            'exit_reason': exit_reason
        })

if positions:
    df_pos = pd.DataFrame(positions)

    # Calculate metrics
    df_pos['cum_pnl'] = df_pos['pnl_pct'].cumsum()
    equity = 100 + df_pos['cum_pnl']
    dd = ((equity - equity.cummax()) / equity.cummax() * 100).min()
    total_return = df_pos['pnl_pct'].sum()
    rdd = total_return / abs(dd) if dd != 0 else 0

    long_trades = df_pos[df_pos['direction'] == 'LONG']
    short_trades = df_pos[df_pos['direction'] == 'SHORT']

    print(f"\nTotal trades: {len(df_pos)}")
    print(f"  LONG: {len(long_trades)} trades, {long_trades['pnl_pct'].sum():+.2f}%")
    print(f"  SHORT: {len(short_trades)} trades, {short_trades['pnl_pct'].sum():+.2f}%")
    print(f"\nPerformance:")
    print(f"  Total return: {total_return:+.2f}%")
    print(f"  Max DD: {dd:.2f}%")
    print(f"  R/DD: {rdd:.2f}x")
    print(f"  Win rate: {(df_pos['pnl_pct'] > 0).mean() * 100:.1f}%")
    print(f"  Avg hold: {df_pos['hold_hours'].mean():.1f}h ({df_pos['hold_hours'].mean()/24:.1f} days)")

    strategies.append({
        'name': 'EMA Crossover 12/26/50',
        'trades': len(df_pos),
        'return': total_return,
        'dd': dd,
        'rdd': rdd,
        'long_pnl': long_trades['pnl_pct'].sum() if len(long_trades) > 0 else 0,
        'short_pnl': short_trades['pnl_pct'].sum() if len(short_trades) > 0 else 0
    })

# Strategy 2: LONG only (test if short bias is better)
print("\n" + "-" * 80)
print("STRATEGY 2: LONG Only (vs SHORT Only)")
print("-" * 80)

# Test LONG only
long_only_return = long_trades['pnl_pct'].sum() if len(long_trades) > 0 else 0
print(f"LONG only: {len(long_trades)} trades, {long_only_return:+.2f}%")

# Test SHORT only
short_only_return = short_trades['pnl_pct'].sum() if len(short_trades) > 0 else 0
print(f"SHORT only: {len(short_trades)} trades, {short_only_return:+.2f}%")

if abs(short_only_return) > abs(long_only_return):
    print(f"\n✅ SHORT bias confirmed! SHORT outperforms LONG by {abs(short_only_return) - abs(long_only_return):.2f}%")
else:
    print(f"\n❌ SHORT bias not confirmed. LONG better by {abs(long_only_return) - abs(short_only_return):.2f}%")

print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)
print("\n1. Test position stacking (add to winners)")
print("2. Optimize entry timing (use 15m/5m for precision)")
print("3. Add filters (RSI, volume, volatility)")
print("4. Test different EMA combinations")
print("5. Backtest on full 90 days with all rules")

# Save positions for analysis
df_pos.to_csv('results/btc_swing_basic_trades.csv', index=False)
print(f"\n✅ Trades saved to: results/btc_swing_basic_trades.csv")
