#!/usr/bin/env python3
"""
BTC Swing Trading - Trend Following with Position Stacking
Strategy: Ride strong trends, stack positions on pullbacks
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# Load 1h data
df = pd.read_csv('btc_1h_90d.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("BTC TREND FOLLOWING - Position Stacking on Pullbacks")
print("=" * 80)

# Calculate indicators
df['ema21'] = calculate_ema(df['close'], 21)
df['ema50'] = calculate_ema(df['close'], 50)
df['ema200'] = calculate_ema(df['close'], 200)
df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)

# Define trends
df['strong_uptrend'] = (df['ema21'] > df['ema50']) & (df['ema50'] > df['ema200'])
df['strong_downtrend'] = (df['ema21'] < df['ema50']) & (df['ema50'] < df['ema200'])

# Pullbacks
df['pullback_up'] = (df['close'] < df['ema21']) & df['strong_uptrend']  # Price dips below EMA21 in uptrend
df['pullback_down'] = (df['close'] > df['ema21']) & df['strong_downtrend']  # Price above EMA21 in downtrend

print(f"\nData: {len(df)} candles")
print(f"Price: ${df['close'].min():.0f} - ${df['close'].max():.0f}")

# Test Strategy: Enter on pullbacks in strong trends
positions = []

for i in range(200, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i-1]

    # LONG: Pullback in uptrend (price dips to EMA21 then bounces)
    if (prev['pullback_up'] and  # Was below EMA21
        row['close'] > row['ema21']):  # Now bounces above

        entry_price = row['close']
        entry_time = row['timestamp']
        direction = 'LONG'
        atr_val = row['atr']

        # Exit: Price crosses below EMA21 or 7 days
        exit_found = False
        for j in range(i+1, min(i+168, len(df))):
            exit_row = df.iloc[j]

            # Exit if price drops below EMA21 (trend weakening)
            if exit_row['close'] < exit_row['ema21']:
                exit_price = exit_row['close']
                exit_time = exit_row['timestamp']
                exit_reason = 'TREND_EXIT'
                exit_found = True
                break

        if not exit_found:
            j = min(i+167, len(df)-1)
            exit_price = df.iloc[j]['close']
            exit_time = df.iloc[j]['timestamp']
            exit_reason = 'TIME'

        pnl_pct = (exit_price - entry_price) / entry_price * 100
        hold_hours = (exit_time - entry_time).total_seconds() / 3600

        positions.append({
            'direction': 'LONG',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'hold_hours': hold_hours,
            'exit_reason': exit_reason
        })

    # SHORT: Pullback in downtrend (price rallies to EMA21 then drops)
    elif (prev['pullback_down'] and
          row['close'] < row['ema21']):

        entry_price = row['close']
        entry_time = row['timestamp']
        direction = 'SHORT'

        exit_found = False
        for j in range(i+1, min(i+168, len(df))):
            exit_row = df.iloc[j]

            if exit_row['close'] > exit_row['ema21']:
                exit_price = exit_row['close']
                exit_time = exit_row['timestamp']
                exit_reason = 'TREND_EXIT'
                exit_found = True
                break

        if not exit_found:
            j = min(i+167, len(df)-1)
            exit_price = df.iloc[j]['close']
            exit_time = df.iloc[j]['timestamp']
            exit_reason = 'TIME'

        pnl_pct = (entry_price - exit_price) / entry_price * 100
        hold_hours = (exit_time - entry_time).total_seconds() / 3600

        positions.append({
            'direction': 'SHORT',
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'hold_hours': hold_hours,
            'exit_reason': exit_reason
        })

if not positions:
    print("\n❌ No trades generated")
else:
    df_pos = pd.DataFrame(positions)

    # Calculate metrics
    df_pos['cum_pnl'] = df_pos['pnl_pct'].cumsum()
    equity = 100 + df_pos['cum_pnl']
    dd = ((equity - equity.cummax()) / equity.cummax() * 100).min()
    total_return = df_pos['pnl_pct'].sum()
    rdd = total_return / abs(dd) if dd != 0 else 0

    long_trades = df_pos[df_pos['direction'] == 'LONG']
    short_trades = df_pos[df_pos['direction'] == 'SHORT']

    print(f"\n" + "-" * 80)
    print("RESULTS - Trend Following with Pullback Entry")
    print("-" * 80)

    print(f"\nTotal trades: {len(df_pos)}")
    print(f"  LONG: {len(long_trades)} ({len(long_trades)/len(df_pos)*100:.0f}%)")
    print(f"  SHORT: {len(short_trades)} ({len(short_trades)/len(df_pos)*100:.0f}%)")

    print(f"\nPerformance:")
    print(f"  Total return: {total_return:+.2f}%")
    print(f"  Max DD: {dd:.2f}%")
    print(f"  R/DD: {rdd:.2f}x")
    print(f"  Win rate: {(df_pos['pnl_pct'] > 0).mean() * 100:.1f}%")
    print(f"  Avg hold: {df_pos['hold_hours'].mean():.1f}h ({df_pos['hold_hours'].mean()/24:.1f} days)")

    if len(long_trades) > 0:
        print(f"\nLONG breakdown:")
        print(f"  PnL: {long_trades['pnl_pct'].sum():+.2f}%")
        print(f"  Win rate: {(long_trades['pnl_pct'] > 0).mean() * 100:.1f}%")
        print(f"  Avg: {long_trades['pnl_pct'].mean():+.2f}%")

    if len(short_trades) > 0:
        print(f"\nSHORT breakdown:")
        print(f"  PnL: {short_trades['pnl_pct'].sum():+.2f}%")
        print(f"  Win rate: {(short_trades['pnl_pct'] > 0).mean() * 100:.1f}%")
        print(f"  Avg: {short_trades['pnl_pct'].mean():+.2f}%")

    print(f"\n" + "=" * 80)
    if rdd >= 5:
        print(f"✅ TARGET HIT: {rdd:.2f}x R/DD (target: 5x+)")
    else:
        print(f"❌ BELOW TARGET: {rdd:.2f}x R/DD (target: 5x+)")
        print("   Need to optimize further...")
    print("=" * 80)

    # Save
    df_pos.to_csv('results/btc_trend_following_trades.csv', index=False)
    print(f"\n✅ Trades saved: results/btc_trend_following_trades.csv")
