#!/usr/bin/env python3
"""
Analyze TRUMPSOL trades to find filters that eliminate losers
"""

import pandas as pd
import numpy as np

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Load data
df = pd.read_csv('trumpsol_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print("=" * 80)
print("TRUMPSOL TRADE ANALYSIS - Winners vs Losers")
print("=" * 80)

# Calculate indicators
df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
df['atr_ma'] = df['atr'].rolling(20).mean()
df['atr_ratio'] = df['atr'] / df['atr_ma']
df['ema20'] = calculate_ema(df['close'], 20)
df['distance'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)
df['bullish'] = df['close'] > df['open']
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['rsi'] = calculate_rsi(df['close'], 14)

# Volume indicators
df['volume_ma'] = df['volume'].rolling(30).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma']

# Daily RSI
df_daily = df.set_index('timestamp').resample('1D').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

df_daily['rsi_daily'] = calculate_rsi(df_daily['close'], 14)

df = df.set_index('timestamp')
df = df.join(df_daily[['rsi_daily']], how='left')
df = df.ffill()
df = df.reset_index()

# Best config from optimization
params = {
    'atr_mult': 1.5,
    'ema_dist': 2.0,
    'tp_mult': 8.0,
    'sl_mult': 1.5,
    'limit_offset': 0.5
}

# Generate signals
signals = []
for i in range(len(df)):
    row = df.iloc[i]

    if (row['atr_ratio'] > params['atr_mult'] and
        row['distance'] < params['ema_dist'] and
        row['bullish'] and
        not pd.isna(row['rsi_daily']) and
        row['rsi_daily'] > 50):
        signals.append(i)

print(f"\nTotal signals: {len(signals)}")

# Backtest with detailed trade data
trades = []

for signal_idx in signals:
    if signal_idx >= len(df) - 1:
        continue

    signal_row = df.iloc[signal_idx]
    signal_price = signal_row['close']
    signal_atr = signal_row['atr']

    if pd.isna(signal_atr) or signal_atr == 0:
        continue

    limit_price = signal_price * (1 + params['limit_offset'] / 100)

    filled = False
    fill_idx = None

    for i in range(signal_idx + 1, min(signal_idx + 4, len(df))):
        if df['high'].iloc[i] >= limit_price:
            filled = True
            fill_idx = i
            break

    if not filled:
        continue

    entry_price = limit_price
    entry_atr = df['atr'].iloc[fill_idx]

    sl_price = entry_price - (params['sl_mult'] * entry_atr)
    tp_price = entry_price + (params['tp_mult'] * entry_atr)

    exit_idx = None
    exit_price = None
    exit_reason = None

    for i in range(fill_idx + 1, min(fill_idx + 200, len(df))):
        if df['low'].iloc[i] <= sl_price:
            exit_idx = i
            exit_price = sl_price
            exit_reason = 'SL'
            break
        if df['high'].iloc[i] >= tp_price:
            exit_idx = i
            exit_price = tp_price
            exit_reason = 'TP'
            break

    if exit_idx is None:
        exit_idx = min(fill_idx + 199, len(df) - 1)
        exit_price = df['close'].iloc[exit_idx]
        exit_reason = 'TIME'

    pnl_pct = (exit_price - entry_price) / entry_price * 100 - 0.10

    trades.append({
        'timestamp': signal_row['timestamp'],
        'entry_price': entry_price,
        'exit_price': exit_price,
        'pnl_pct': pnl_pct,
        'exit_reason': exit_reason,
        'bars_held': exit_idx - fill_idx,
        # Entry conditions
        'atr_ratio': signal_row['atr_ratio'],
        'ema_distance': signal_row['distance'],
        'rsi': signal_row['rsi'],
        'rsi_daily': signal_row['rsi_daily'],
        'volume_ratio': signal_row['volume_ratio'],
        'body_pct': signal_row['body_pct'],
        'hour': signal_row['timestamp'].hour,
    })

df_trades = pd.DataFrame(trades)

print(f"Filled trades: {len(df_trades)}")
print(f"\nBaseline Performance:")
print(f"  Total Return: {df_trades['pnl_pct'].sum():+.2f}%")
print(f"  Win Rate: {(df_trades['pnl_pct'] > 0).mean() * 100:.1f}%")
print(f"  TP Rate: {(df_trades['exit_reason'] == 'TP').sum() / len(df_trades) * 100:.1f}%")

# Split winners vs losers
winners = df_trades[df_trades['pnl_pct'] > 0]
losers = df_trades[df_trades['pnl_pct'] <= 0]

print(f"\n" + "=" * 80)
print("WINNERS vs LOSERS ANALYSIS")
print("=" * 80)

print(f"\n{'Metric':<20} {'Winners (n={})'.format(len(winners)):<20} {'Losers (n={})'.format(len(losers)):<20} {'Difference'}")
print("-" * 80)

metrics = ['atr_ratio', 'ema_distance', 'rsi', 'rsi_daily', 'volume_ratio', 'body_pct', 'bars_held']

for metric in metrics:
    w_avg = winners[metric].mean()
    l_avg = losers[metric].mean()
    diff = w_avg - l_avg
    diff_pct = (diff / l_avg * 100) if l_avg != 0 else 0
    print(f"{metric:<20} {w_avg:<20.2f} {l_avg:<20.2f} {diff:+.2f} ({diff_pct:+.1f}%)")

# Hour analysis
print(f"\n" + "=" * 80)
print("HOUR ANALYSIS")
print("=" * 80)

hour_stats = df_trades.groupby('hour').agg({
    'pnl_pct': ['count', 'sum', 'mean']
}).round(2)

print(f"\n{'Hour':<6} {'Trades':<8} {'Total PnL':<12} {'Avg PnL':<10}")
print("-" * 40)
for hour, row in hour_stats.iterrows():
    print(f"{hour:<6} {int(row[('pnl_pct', 'count')]):<8} {row[('pnl_pct', 'sum')]:+11.2f}% {row[('pnl_pct', 'mean')]:+9.2f}%")

# Exit reason by winner/loser
print(f"\n" + "=" * 80)
print("EXIT REASON BREAKDOWN")
print("=" * 80)

print(f"\nWinners ({len(winners)} trades):")
print(winners['exit_reason'].value_counts())

print(f"\nLosers ({len(losers)} trades):")
print(losers['exit_reason'].value_counts())

# Save detailed trades
df_trades.to_csv('results/trumpsol_trades_detailed.csv', index=False)
print(f"\n✅ Detailed trades saved to: results/trumpsol_trades_detailed.csv")
