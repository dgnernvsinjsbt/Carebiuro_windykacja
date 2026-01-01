#!/usr/bin/env python3
"""
ETH RSI Optimization - Find better SL/TP and filters
"""

import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

# Load ETH data
df = pd.read_csv('eth_1h_90d.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("ETH RSI OPTIMIZATION - Winners vs Losers Analysis")
print("=" * 80)

# Calculate indicators
df['rsi'] = calculate_rsi(df['close'], 14)
df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)
df['ema21'] = calculate_ema(df['close'], 21)
df['ema50'] = calculate_ema(df['close'], 50)
df['above_ema21'] = df['close'] > df['ema21']
df['above_ema50'] = df['close'] > df['ema50']
df['dist_ema21'] = (df['close'] - df['ema21']) / df['ema21'] * 100
df['volume_ma'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma']
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

# Baseline backtest with detailed trade data
trades = []

for i in range(50, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i-1]

    # LONG
    if prev['rsi'] <= 30 and row['rsi'] > 30:
        entry_price = row['close']
        entry_time = row['timestamp']
        atr_val = row['atr']
        sl_price = entry_price - (2.0 * atr_val)

        entry_conditions = {
            'rsi_entry': row['rsi'],
            'above_ema21': row['above_ema21'],
            'above_ema50': row['above_ema50'],
            'dist_ema21': row['dist_ema21'],
            'volume_ratio': row['volume_ratio'],
            'body_pct': row['body_pct']
        }

        exit_found = False
        for j in range(i+1, min(i+168, len(df))):
            exit_row = df.iloc[j]

            if exit_row['low'] <= sl_price:
                exit_price = sl_price
                exit_time = exit_row['timestamp']
                exit_reason = 'SL'
                exit_found = True
                break

            if exit_row['rsi'] >= 65:
                exit_price = exit_row['close']
                exit_time = exit_row['timestamp']
                exit_reason = 'TP'
                exit_found = True
                break

        if not exit_found:
            j = min(i+167, len(df)-1)
            exit_price = df.iloc[j]['close']
            exit_time = df.iloc[j]['timestamp']
            exit_reason = 'TIME'

        pnl_pct = (exit_price - entry_price) / entry_price * 100
        hold_hours = (exit_time - entry_time).total_seconds() / 3600

        trades.append({
            'direction': 'LONG',
            'pnl_pct': pnl_pct,
            'hold_hours': hold_hours,
            'exit_reason': exit_reason,
            **entry_conditions
        })

    # SHORT
    elif prev['rsi'] >= 65 and row['rsi'] < 65:
        entry_price = row['close']
        entry_time = row['timestamp']
        atr_val = row['atr']
        sl_price = entry_price + (2.0 * atr_val)

        entry_conditions = {
            'rsi_entry': row['rsi'],
            'above_ema21': row['above_ema21'],
            'above_ema50': row['above_ema50'],
            'dist_ema21': row['dist_ema21'],
            'volume_ratio': row['volume_ratio'],
            'body_pct': row['body_pct']
        }

        exit_found = False
        for j in range(i+1, min(i+168, len(df))):
            exit_row = df.iloc[j]

            if exit_row['high'] >= sl_price:
                exit_price = sl_price
                exit_time = exit_row['timestamp']
                exit_reason = 'SL'
                exit_found = True
                break

            if exit_row['rsi'] <= 30:
                exit_price = exit_row['close']
                exit_time = exit_row['timestamp']
                exit_reason = 'TP'
                exit_found = True
                break

        if not exit_found:
            j = min(i+167, len(df)-1)
            exit_price = df.iloc[j]['close']
            exit_time = df.iloc[j]['timestamp']
            exit_reason = 'TIME'

        pnl_pct = (entry_price - exit_price) / entry_price * 100
        hold_hours = (exit_time - entry_time).total_seconds() / 3600

        trades.append({
            'direction': 'SHORT',
            'pnl_pct': pnl_pct,
            'hold_hours': hold_hours,
            'exit_reason': exit_reason,
            **entry_conditions
        })

df_trades = pd.DataFrame(trades)

print(f"\nBaseline: {len(df_trades)} trades, {df_trades['pnl_pct'].sum():+.2f}% total return")

# Winners vs Losers
winners = df_trades[df_trades['pnl_pct'] > 0]
losers = df_trades[df_trades['pnl_pct'] <= 0]

print(f"\n" + "=" * 80)
print("WINNERS vs LOSERS")
print("=" * 80)

print(f"\n{'Metric':<20} {'Winners (n={})'.format(len(winners)):<20} {'Losers (n={})'.format(len(losers)):<20} {'Diff %'}")
print("-" * 75)

metrics = ['rsi_entry', 'dist_ema21', 'volume_ratio', 'body_pct', 'hold_hours']

for metric in metrics:
    w = winners[metric].mean()
    l = losers[metric].mean()
    diff_pct = (w - l) / l * 100 if l != 0 else 0
    print(f"{metric:<20} {w:<20.2f} {l:<20.2f} {diff_pct:+.1f}%")

# EMA filters
print(f"\n{'EMA Position':<20} {'Winners %':<20} {'Losers %':<20} {'Edge'}")
print("-" * 65)
for ema in ['above_ema21', 'above_ema50']:
    w_pct = winners[ema].mean() * 100
    l_pct = losers[ema].mean() * 100
    print(f"{ema:<20} {w_pct:<20.1f} {l_pct:<20.1f} {w_pct - l_pct:+.1f}%")

print(f"\n✅ Analysis saved for filter testing...")
df_trades.to_csv('results/eth_rsi_trades_detailed.csv', index=False)
