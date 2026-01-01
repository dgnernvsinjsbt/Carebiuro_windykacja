#!/usr/bin/env python3
"""
BTC Swing Breakout Strategy - Hold 1-7 days
Enter on breakouts of consolidation ranges, exit on opposite breakout or time
"""

import pandas as pd
import numpy as np

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# Load 15m data for better swing signals
df = pd.read_csv('btc_15m_90d.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("BTC BREAKOUT SWING STRATEGY - 15m Chart")
print("=" * 80)

# Calculate indicators
df['high_20'] = df['high'].rolling(20).max()  # 20-bar high (5 hours)
df['low_20'] = df['low'].rolling(20).min()
df['ema50'] = calculate_ema(df['close'], 50)
df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)

# Range size
df['range_size'] = (df['high_20'] - df['low_20']) / df['low_20'] * 100

print(f"\nData: {len(df)} 15m candles")
print(f"Price: ${df['close'].min():.0f} - ${df['close'].max():.0f}")

# Breakout strategy
positions = []

for i in range(50, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i-1]

    # Upside breakout: Close above 20-bar high
    if (row['close'] > row['high_20'] and
        row['close'] > row['ema50'] and  # Trend filter
        row['range_size'] > 1.0):  # Meaningful range

        entry_price = row['close']
        entry_time = row['timestamp']
        atr_val = row['atr']

        # Exit: Downside breakout below 20-bar low OR 7 days
        max_hold_bars = 28 * 4  # 7 days * 4 bars/hour
        exit_found = False

        for j in range(i+1, min(i+max_hold_bars, len(df))):
            exit_row = df.iloc[j]

            # Exit on break below 20-bar low
            if exit_row['close'] < exit_row['low_20']:
                exit_price = exit_row['close']
                exit_time = exit_row['timestamp']
                exit_reason = 'BREAKDOWN'
                exit_found = True
                break

        if not exit_found:
            j = min(i+max_hold_bars-1, len(df)-1)
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

    # Downside breakout: Close below 20-bar low
    elif (row['close'] < row['low_20'] and
          row['close'] < row['ema50'] and
          row['range_size'] > 1.0):

        entry_price = row['close']
        entry_time = row['timestamp']

        max_hold_bars = 28 * 4
        exit_found = False

        for j in range(i+1, min(i+max_hold_bars, len(df))):
            exit_row = df.iloc[j]

            if exit_row['close'] > exit_row['high_20']:
                exit_price = exit_row['close']
                exit_time = exit_row['timestamp']
                exit_reason = 'BREAKOUT'
                exit_found = True
                break

        if not exit_found:
            j = min(i+max_hold_bars-1, len(df)-1)
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
    print("\n❌ No trades")
else:
    df_pos = pd.DataFrame(positions)

    df_pos['cum_pnl'] = df_pos['pnl_pct'].cumsum()
    equity = 100 + df_pos['cum_pnl']
    dd = ((equity - equity.cummax()) / equity.cummax() * 100).min()
    total_return = df_pos['pnl_pct'].sum()
    rdd = total_return / abs(dd) if dd != 0 else 0

    long_trades = df_pos[df_pos['direction'] == 'LONG']
    short_trades = df_pos[df_pos['direction'] == 'SHORT']

    print(f"\n" + "-" * 80)
    print("BREAKOUT STRATEGY RESULTS")
    print("-" * 80)

    print(f"\nTotal trades: {len(df_pos)}")
    print(f"  LONG: {len(long_trades)}")
    print(f"  SHORT: {len(short_trades)}")

    print(f"\nPerformance:")
    print(f"  Return: {total_return:+.2f}%")
    print(f"  Max DD: {dd:.2f}%")
    print(f"  R/DD: {rdd:.2f}x")
    print(f"  Win Rate: {(df_pos['pnl_pct'] > 0).mean() * 100:.1f}%")
    print(f"  Avg Hold: {df_pos['hold_hours'].mean():.1f}h ({df_pos['hold_hours'].mean()/24:.1f} days)")

    if len(long_trades) > 0:
        print(f"\nLONG:")
        print(f"  PnL: {long_trades['pnl_pct'].sum():+.2f}%")
        print(f"  WR: {(long_trades['pnl_pct'] > 0).mean() * 100:.1f}%")

    if len(short_trades) > 0:
        print(f"\nSHORT:")
        print(f"  PnL: {short_trades['pnl_pct'].sum():+.2f}%")
        print(f"  WR: {(short_trades['pnl_pct'] > 0).mean() * 100:.1f}%")

    print(f"\n" + "=" * 80)
    if rdd >= 5:
        print(f"✅ TARGET: {rdd:.2f}x R/DD")
    elif rdd >= 3:
        print(f"⚠️ CLOSE: {rdd:.2f}x R/DD (target 5x)")
    else:
        print(f"❌ FAR: {rdd:.2f}x R/DD (target 5x)")
    print("=" * 80)

    df_pos.to_csv('results/btc_breakout_trades.csv', index=False)
    print(f"\n✅ Saved: results/btc_breakout_trades.csv")
