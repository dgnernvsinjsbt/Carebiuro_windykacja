#!/usr/bin/env python3
"""Quick test to verify UNI data and RSI strategy basics"""

import pandas as pd
import numpy as np
import sys

print("=" * 80, flush=True)
print("UNI RSI Strategy - Quick Test", flush=True)
print("=" * 80, flush=True)

# Load data
print("\n1. Loading data...", flush=True)
try:
    df = pd.read_csv('trading/uni_30d_bingx.csv')
    print(f"✅ Loaded {len(df):,} candles", flush=True)
except Exception as e:
    print(f"❌ Error loading data: {e}", flush=True)
    sys.exit(1)

# Parse timestamps
print("\n2. Parsing timestamps...", flush=True)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)
print(f"✅ Date range: {df['timestamp'].min()} to {df['timestamp'].max()}", flush=True)
print(f"✅ Price range: ${df['close'].min():.3f} - ${df['close'].max():.3f}", flush=True)

# Calculate indicators
print("\n3. Calculating indicators...", flush=True)

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))
print(f"✅ RSI calculated, range: {df['rsi'].min():.1f} - {df['rsi'].max():.1f}", flush=True)

# SMA
df['sma20'] = df['close'].rolling(window=20).mean()
print(f"✅ SMA(20) calculated", flush=True)

# ATR
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(window=14).mean()
print(f"✅ ATR calculated, mean: {df['atr'].mean():.4f}", flush=True)

# Body
df['body'] = abs(df['close'] - df['open'])
df['body_pct'] = (df['body'] / df['open']) * 100
print(f"✅ Body % calculated, mean: {df['body_pct'].mean():.3f}%", flush=True)

# Test single configuration
print("\n4. Testing baseline config (MOODENG parameters)...", flush=True)
print("   RSI threshold: 55, Min body: 0.5%, SL: 1.0x ATR, TP: 4.0x ATR", flush=True)

trades = []
in_position = False
entry_price = 0
entry_idx = 0
stop_loss = 0
take_profit = 0

signals = 0
for i in range(20, len(df)):
    current = df.iloc[i]
    prev = df.iloc[i-1]

    # Check exit
    if in_position:
        bars_held = i - entry_idx

        if current['low'] <= stop_loss:
            pnl_pct = ((stop_loss - entry_price) / entry_price) * 100 - 0.10
            trades.append({'pnl': pnl_pct, 'bars': bars_held, 'exit': 'SL'})
            in_position = False
            continue

        if current['high'] >= take_profit:
            pnl_pct = ((take_profit - entry_price) / entry_price) * 100 - 0.10
            trades.append({'pnl': pnl_pct, 'bars': bars_held, 'exit': 'TP'})
            in_position = False
            continue

        if bars_held >= 60:
            pnl_pct = ((current['close'] - entry_price) / entry_price) * 100 - 0.10
            trades.append({'pnl': pnl_pct, 'bars': bars_held, 'exit': 'TIME'})
            in_position = False
            continue

    # Check entry
    if not in_position:
        rsi_cross = prev['rsi'] < 55 and current['rsi'] >= 55
        bullish = current['close'] > current['open'] and current['body_pct'] > 0.5
        above_sma = current['close'] > current['sma20']

        if rsi_cross and bullish and above_sma and not pd.isna(current['atr']):
            signals += 1
            in_position = True
            entry_price = current['close']
            entry_idx = i
            stop_loss = entry_price - (1.0 * current['atr'])
            take_profit = entry_price + (4.0 * current['atr'])

print(f"✅ Backtest complete: {signals} signals generated, {len(trades)} trades closed", flush=True)

if len(trades) > 0:
    trades_df = pd.DataFrame(trades)
    total_return = trades_df['pnl'].sum()
    winners = trades_df[trades_df['pnl'] > 0]
    win_rate = len(winners) / len(trades) * 100

    cumulative = trades_df['pnl'].cumsum()
    running_max = cumulative.expanding().max()
    drawdown = cumulative - running_max
    max_dd = abs(drawdown.min())
    return_dd = total_return / max_dd if max_dd > 0 else 0

    print("\n5. RESULTS:", flush=True)
    print(f"   Total Return: {total_return:+.2f}%", flush=True)
    print(f"   Max Drawdown: {max_dd:.2f}%", flush=True)
    print(f"   Return/DD: {return_dd:.2f}x", flush=True)
    print(f"   Win Rate: {win_rate:.1f}%", flush=True)
    print(f"   Avg Trade: {trades_df['pnl'].mean():+.2f}%", flush=True)
    print(f"   Avg Bars Held: {trades_df['bars'].mean():.0f}", flush=True)

    tp_count = len(trades_df[trades_df['exit'] == 'TP'])
    sl_count = len(trades_df[trades_df['exit'] == 'SL'])
    time_count = len(trades_df[trades_df['exit'] == 'TIME'])
    print(f"   Exits: TP={tp_count}, SL={sl_count}, TIME={time_count}", flush=True)

    if total_return > 0:
        print(f"\n✅ PROFITABLE! UNI shows potential with RSI momentum strategy", flush=True)
    else:
        print(f"\n❌ Not profitable with baseline config", flush=True)
else:
    print("\n❌ No trades closed (all signals still open or no signals)", flush=True)

print("\n" + "=" * 80, flush=True)
print("Test complete!", flush=True)
print("=" * 80, flush=True)
