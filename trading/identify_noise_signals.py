#!/usr/bin/env python3
"""Identify characteristics of noisy BingX signals vs clean signals"""
import pandas as pd
import numpy as np

df = pd.read_csv('melania_6months_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = df[col].astype(float)

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
df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

# Calculate additional metrics for noise detection
df['range_pct'] = ((df['high'] - df['low']) / df['close']) * 100
df['body_pct'] = (abs(df['close'] - df['open']) / df['close']) * 100

# Price action after signal (next 5 bars)
df['next_5_high'] = df['high'].shift(-5).rolling(5).max()
df['next_5_low'] = df['low'].shift(-5).rolling(5).min()
df['next_5_range'] = ((df['next_5_high'] - df['next_5_low']) / df['close']) * 100

# Trend strength
df['sma_20'] = df['close'].rolling(20).mean()
df['dist_from_sma'] = ((df['close'] - df['sma_20']) / df['sma_20']) * 100

# Original config
rsi_ob = 65
limit_offset_atr = 0.1
sl_atr = 1.2
tp_atr = 3.0
min_move = 0.8

current_risk = 0.12
equity = 100.0
trades = []
position = None
pending_order = None

for i in range(300, len(df) - 10):  # -10 to have lookahead data
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
        continue

    if pending_order:
        if i - pending_order['signal_bar'] > 8:
            pending_order = None
        elif row['high'] >= pending_order['limit_price']:
            position = {
                'entry': pending_order['limit_price'],
                'sl_price': pending_order['sl_price'],
                'tp_price': pending_order['tp_price'],
                'size': pending_order['size'],
                'entry_bar': i,
                'signal_bar': pending_order['signal_bar']
            }
            pending_order = None

    if position:
        pnl_pct = None
        exit_reason = None
        bars_to_exit = i - position['entry_bar']

        if row['high'] >= position['sl_price']:
            pnl_pct = ((position['entry'] - position['sl_price']) / position['entry']) * 100
            exit_reason = 'SL'
        elif row['low'] <= position['tp_price']:
            pnl_pct = ((position['entry'] - position['tp_price']) / position['entry']) * 100
            exit_reason = 'TP'

        if pnl_pct is not None:
            pnl_dollar = position['size'] * (pnl_pct / 100) - position['size'] * 0.001
            equity += pnl_dollar

            signal_row = df.iloc[position['signal_bar']]

            trades.append({
                'signal_time': signal_row['timestamp'],
                'pnl_dollar': pnl_dollar,
                'exit_reason': exit_reason,
                'bars_to_exit': bars_to_exit,
                'signal_rsi': signal_row['rsi'],
                'signal_ret20': signal_row['ret_20'],
                'signal_range_pct': signal_row['range_pct'],
                'signal_body_pct': signal_row['body_pct'],
                'signal_next_5_range': signal_row['next_5_range'],
                'signal_dist_sma': signal_row['dist_from_sma']
            })

            won = pnl_pct > 0
            current_risk = min(current_risk * 1.5, 0.30) if won else max(current_risk * 0.5, 0.02)
            position = None

    if not position and not pending_order and i > 0:
        prev_row = df.iloc[i-1]

        if pd.isna(prev_row['rsi']):
            continue

        if prev_row['rsi'] > rsi_ob and row['rsi'] <= rsi_ob:
            signal_price = row['close']
            atr = row['atr']

            limit_price = signal_price + (atr * limit_offset_atr)
            sl_price = limit_price + (atr * sl_atr)
            tp_price = limit_price - (atr * tp_atr)

            sl_dist = abs((sl_price - limit_price) / limit_price) * 100
            size = (equity * current_risk) / (sl_dist / 100)

            pending_order = {
                'limit_price': limit_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'size': size,
                'signal_bar': i
            }

trades_df = pd.DataFrame(trades)
trades_df['winner'] = trades_df['pnl_dollar'] > 0

# Identify "noise" signals - quick stop-outs (likely the extra BingX signals)
noise_signals = trades_df[(trades_df['exit_reason'] == 'SL') & (trades_df['bars_to_exit'] <= 10)]
clean_signals = trades_df[trades_df['winner'] | (trades_df['bars_to_exit'] > 50)]

print("=" * 80)
print("NOISE SIGNAL ANALYSIS")
print("=" * 80)
print("\nHypothesis: Extra BingX signals = quick stop-outs (noisy/choppy)")
print("LBank had cleaner trends, fewer false signals\n")

print(f"Total trades: {len(trades_df)}")
print(f"'Noise' signals (SL ≤10 bars): {len(noise_signals)} ({len(noise_signals)/len(trades_df)*100:.1f}%)")
print(f"'Clean' signals (winners or held >50 bars): {len(clean_signals)} ({len(clean_signals)/len(trades_df)*100:.1f}%)")

print("\n" + "=" * 80)
print("NOISE vs CLEAN CHARACTERISTICS")
print("=" * 80)

print(f"\nBars to Exit:")
print(f"  Noise: {noise_signals['bars_to_exit'].mean():.1f} bars")
print(f"  Clean: {clean_signals['bars_to_exit'].mean():.1f} bars")

print(f"\nRSI at Signal:")
print(f"  Noise: {noise_signals['signal_rsi'].mean():.1f} (±{noise_signals['signal_rsi'].std():.1f})")
print(f"  Clean: {clean_signals['signal_rsi'].mean():.1f} (±{clean_signals['signal_rsi'].std():.1f})")

print(f"\nMomentum (ret_20):")
print(f"  Noise: {noise_signals['signal_ret20'].mean():+.2f}% (±{noise_signals['signal_ret20'].std():.2f})")
print(f"  Clean: {clean_signals['signal_ret20'].mean():+.2f}% (±{clean_signals['signal_ret20'].std():.2f})")

print(f"\nSignal Candle Range:")
print(f"  Noise: {noise_signals['signal_range_pct'].mean():.3f}%")
print(f"  Clean: {clean_signals['signal_range_pct'].mean():.3f}%")

print(f"\nSignal Candle Body:")
print(f"  Noise: {noise_signals['signal_body_pct'].mean():.3f}%")
print(f"  Clean: {clean_signals['signal_body_pct'].mean():.3f}%")

print(f"\nNext 5 Bars Range (choppiness):")
print(f"  Noise: {noise_signals['signal_next_5_range'].mean():.3f}% (CHOPPY)")
print(f"  Clean: {clean_signals['signal_next_5_range'].mean():.3f}% (TRENDING)")

print(f"\nDistance from SMA20:")
print(f"  Noise: {noise_signals['signal_dist_sma'].mean():+.3f}%")
print(f"  Clean: {clean_signals['signal_dist_sma'].mean():+.3f}%")

print("\n" + "=" * 80)
print("KEY DIFFERENCES (FILTERS TO TEST)")
print("=" * 80)

# Find the most discriminative features
if clean_signals['signal_ret20'].mean() > noise_signals['signal_ret20'].mean():
    diff = clean_signals['signal_ret20'].mean() - noise_signals['signal_ret20'].mean()
    threshold = noise_signals['signal_ret20'].quantile(0.75)
    print(f"\n✅ Momentum: Clean signals have {diff:+.1f}% MORE momentum")
    print(f"   Filter: ret_20 >= {threshold:.1f}%")

if noise_signals['signal_next_5_range'].mean() > clean_signals['signal_next_5_range'].mean():
    diff = noise_signals['signal_next_5_range'].mean() - clean_signals['signal_next_5_range'].mean()
    threshold = clean_signals['signal_next_5_range'].quantile(0.75)
    print(f"\n✅ Choppiness: Noise signals {diff:.2f}% MORE choppy after signal")
    print(f"   Filter: Avoid signals where next 5 bars range > {threshold:.2f}%")
    print(f"   (Hard to predict, skip this)")

if abs(clean_signals['signal_dist_sma'].mean()) > abs(noise_signals['signal_dist_sma'].mean()):
    print(f"\n✅ Trend strength: Clean signals further from SMA20")
    print(f"   Clean: {clean_signals['signal_dist_sma'].mean():+.2f}% from SMA")
    print(f"   Noise: {noise_signals['signal_dist_sma'].mean():+.2f}% from SMA")
    threshold = noise_signals['signal_dist_sma'].quantile(0.25)
    print(f"   Filter: Only SHORT when price > SMA20 by at least {abs(threshold):.1f}%")

# Show sample noise signals
print("\n" + "=" * 80)
print("SAMPLE NOISE SIGNALS (quick stop-outs)")
print("=" * 80)

for idx, trade in noise_signals.head(5).iterrows():
    print(f"\n{trade['signal_time']} | SL in {trade['bars_to_exit']} bars")
    print(f"  RSI: {trade['signal_rsi']:.1f} | Ret20: {trade['signal_ret20']:+.1f}% | Dist SMA: {trade['signal_dist_sma']:+.2f}%")
    print(f"  P&L: ${trade['pnl_dollar']:+.2f}")

print("\n" + "=" * 80)
