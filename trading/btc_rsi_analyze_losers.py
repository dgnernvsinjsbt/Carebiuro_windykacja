#!/usr/bin/env python3
"""
Analyze BTC RSI 30/65 trades - What do losers have in common?
"""

import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# Load data
df = pd.read_csv('btc_1h_90d.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("BTC RSI 30/65 - WINNERS vs LOSERS ANALYSIS")
print("=" * 80)

# Calculate indicators
df['rsi'] = calculate_rsi(df['close'], 14)
df['ema21'] = calculate_ema(df['close'], 21)
df['ema50'] = calculate_ema(df['close'], 50)
df['ema200'] = calculate_ema(df['close'], 200)
df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)
df['atr_pct'] = (df['atr'] / df['close'] * 100)

# Volume
df['volume_ma'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma']

# Price vs EMAs
df['above_ema21'] = df['close'] > df['ema21']
df['above_ema50'] = df['close'] > df['ema50']
df['above_ema200'] = df['close'] > df['ema200']

# Distance from EMAs
df['dist_ema21'] = (df['close'] - df['ema21']) / df['ema21'] * 100
df['dist_ema50'] = (df['close'] - df['ema50']) / df['ema50'] * 100

# Body size
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

# Backtest RSI 30/65 with detailed trade data
rsi_low = 30
rsi_high = 65

trades = []

for i in range(200, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i-1]

    # LONG signal
    if prev['rsi'] <= rsi_low and row['rsi'] > rsi_low:
        entry_price = row['close']
        entry_time = row['timestamp']
        direction = 'LONG'

        # Capture entry conditions
        entry_conditions = {
            'rsi_entry': row['rsi'],
            'above_ema21': row['above_ema21'],
            'above_ema50': row['above_ema50'],
            'above_ema200': row['above_ema200'],
            'dist_ema21': row['dist_ema21'],
            'dist_ema50': row['dist_ema50'],
            'volume_ratio': row['volume_ratio'],
            'atr_pct': row['atr_pct'],
            'body_pct': row['body_pct'],
            'hour': row['timestamp'].hour,
            'day_of_week': row['timestamp'].dayofweek
        }

        # Find exit
        exit_found = False
        for j in range(i+1, min(i+168, len(df))):
            if df.iloc[j]['rsi'] >= rsi_high:
                exit_price = df.iloc[j]['close']
                exit_time = df.iloc[j]['timestamp']
                exit_reason = 'RSI'
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
            'direction': direction,
            'pnl_pct': pnl_pct,
            'hold_hours': hold_hours,
            'exit_reason': exit_reason,
            **entry_conditions
        })

    # SHORT signal
    elif prev['rsi'] >= rsi_high and row['rsi'] < rsi_high:
        entry_price = row['close']
        entry_time = row['timestamp']
        direction = 'SHORT'

        entry_conditions = {
            'rsi_entry': row['rsi'],
            'above_ema21': row['above_ema21'],
            'above_ema50': row['above_ema50'],
            'above_ema200': row['above_ema200'],
            'dist_ema21': row['dist_ema21'],
            'dist_ema50': row['dist_ema50'],
            'volume_ratio': row['volume_ratio'],
            'atr_pct': row['atr_pct'],
            'body_pct': row['body_pct'],
            'hour': row['timestamp'].hour,
            'day_of_week': row['timestamp'].dayofweek
        }

        exit_found = False
        for j in range(i+1, min(i+168, len(df))):
            if df.iloc[j]['rsi'] <= rsi_low:
                exit_price = df.iloc[j]['close']
                exit_time = df.iloc[j]['timestamp']
                exit_reason = 'RSI'
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
            'direction': direction,
            'pnl_pct': pnl_pct,
            'hold_hours': hold_hours,
            'exit_reason': exit_reason,
            **entry_conditions
        })

df_trades = pd.DataFrame(trades)

print(f"\nTotal trades: {len(df_trades)}")
print(f"Baseline performance: {df_trades['pnl_pct'].sum():+.2f}%")

# Split winners vs losers
winners = df_trades[df_trades['pnl_pct'] > 0]
losers = df_trades[df_trades['pnl_pct'] <= 0]

print(f"\nWinners: {len(winners)} ({len(winners)/len(df_trades)*100:.1f}%)")
print(f"Losers: {len(losers)} ({len(losers)/len(df_trades)*100:.1f}%)")

print(f"\n" + "=" * 80)
print("WINNERS vs LOSERS BREAKDOWN")
print("=" * 80)

print(f"\n{'Metric':<20} {'Winners (n={})'.format(len(winners)):<20} {'Losers (n={})'.format(len(losers)):<20} {'Difference'}")
print("-" * 80)

metrics = ['rsi_entry', 'dist_ema21', 'dist_ema50', 'volume_ratio', 'atr_pct', 'body_pct', 'hold_hours']

for metric in metrics:
    w_avg = winners[metric].mean()
    l_avg = losers[metric].mean()
    diff = w_avg - l_avg
    diff_pct = (diff / l_avg * 100) if l_avg != 0 else 0
    print(f"{metric:<20} {w_avg:<20.2f} {l_avg:<20.2f} {diff:+.2f} ({diff_pct:+.1f}%)")

# EMA position analysis
print(f"\n" + "=" * 80)
print("TREND ALIGNMENT (% of trades)")
print("=" * 80)

print(f"\n{'Condition':<30} {'Winners':<15} {'Losers':<15} {'Edge'}")
print("-" * 65)

for ema in ['above_ema21', 'above_ema50', 'above_ema200']:
    w_pct = winners[ema].mean() * 100
    l_pct = losers[ema].mean() * 100
    edge = w_pct - l_pct
    print(f"{ema:<30} {w_pct:<15.1f}% {l_pct:<15.1f}% {edge:+.1f}%")

# Direction breakdown
print(f"\n" + "=" * 80)
print("DIRECTION BREAKDOWN")
print("=" * 80)

long_winners = winners[winners['direction'] == 'LONG']
long_losers = losers[losers['direction'] == 'LONG']
short_winners = winners[winners['direction'] == 'SHORT']
short_losers = losers[losers['direction'] == 'SHORT']

print(f"\nLONG trades:")
print(f"  Winners: {len(long_winners)}, Total PnL: {long_winners['pnl_pct'].sum():+.2f}%")
print(f"  Losers: {len(long_losers)}, Total PnL: {long_losers['pnl_pct'].sum():+.2f}%")
print(f"  LONG Win Rate: {len(long_winners)/(len(long_winners)+len(long_losers))*100:.1f}%")

print(f"\nSHORT trades:")
print(f"  Winners: {len(short_winners)}, Total PnL: {short_winners['pnl_pct'].sum():+.2f}%")
print(f"  Losers: {len(short_losers)}, Total PnL: {short_losers['pnl_pct'].sum():+.2f}%")
print(f"  SHORT Win Rate: {len(short_winners)/(len(short_winners)+len(short_losers))*100:.1f}%")

# Hour analysis
print(f"\n" + "=" * 80)
print("HOUR ANALYSIS (UTC)")
print("=" * 80)

hour_stats = df_trades.groupby('hour').agg({
    'pnl_pct': ['count', 'sum', 'mean']
}).round(2)

print(f"\n{'Hour':<6} {'Trades':<8} {'Total PnL':<12} {'Avg PnL':<10}")
print("-" * 40)
for hour, row in hour_stats.iterrows():
    total_pnl = row[('pnl_pct', 'sum')]
    marker = "✅" if total_pnl > 0 else "❌"
    print(f"{hour:<6} {int(row[('pnl_pct', 'count')]):<8} {total_pnl:+11.2f}% {row[('pnl_pct', 'mean')]:+9.2f}% {marker}")

# Save detailed trades
df_trades.to_csv('results/btc_rsi_30_65_detailed.csv', index=False)
print(f"\n✅ Detailed trades saved: results/btc_rsi_30_65_detailed.csv")
