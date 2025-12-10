#!/usr/bin/env python3
"""
TRUMPSOL Contrarian Strategy - Verification
Strategy: Fade violent moves with volume/volatility confirmation

Entry:
- abs(ret_5m) >= 1% (pump/dump)
- vol_ratio >= 1.0 (volume >= avg)
- atr_ratio >= 1.1 (volatility >= 110% avg)
- hour NOT IN {1, 5, 17} (Europe/Warsaw)
- CONTRARIAN: pump → SHORT, dump → LONG

Exit:
- SL: 1% from entry
- TP: 1.5% from entry
- Max hold: 15 minutes
"""

import pandas as pd
import numpy as np
from datetime import datetime

print("=" * 80)
print("TRUMPSOL CONTRARIAN STRATEGY - VERIFICATION")
print("=" * 80)

# Load data
print("\n1. Loading data...")
df = pd.read_csv('trading/trumpsol_30d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"✅ Loaded {len(df):,} candles")
print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Price range: ${df['close'].min():.3f} - ${df['close'].max():.3f}")

# Convert to Europe/Warsaw timezone
print("\n2. Converting to Europe/Warsaw timezone...")
df['timestamp_utc'] = df['timestamp']
df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('Europe/Warsaw')
df['hour_local'] = df['timestamp'].dt.hour
print(f"✅ Timezone converted")

# Calculate indicators
print("\n3. Calculating indicators...")

# 5-minute momentum
df['ret_5m'] = df['close'].pct_change(5)

# Volume ratio (30-minute rolling average)
df['vol_ma30'] = df['volume'].rolling(window=30).mean()
df['vol_ratio'] = df['volume'] / df['vol_ma30']

# ATR and ATR ratio
df['tr'] = df['high'] - df['low']  # Simplified TR
df['atr14'] = df['tr'].rolling(window=14).mean()
df['atr_ma30'] = df['atr14'].rolling(window=30).mean()
df['atr_ratio'] = df['atr14'] / df['atr_ma30']

print(f"✅ Indicators calculated")
print(f"   ret_5m range: {df['ret_5m'].min():.4f} to {df['ret_5m'].max():.4f}")
print(f"   vol_ratio mean: {df['vol_ratio'].mean():.2f}")
print(f"   atr_ratio mean: {df['atr_ratio'].mean():.2f}")

# Generate signals
print("\n4. Generating signals...")

signals = []
for i in range(30, len(df)):  # Start after indicators are ready
    row = df.iloc[i]

    # Check filters
    abs_ret_5m = abs(row['ret_5m'])

    # All conditions must be true
    momentum_filter = abs_ret_5m >= 0.01  # ±1% move
    volume_filter = row['vol_ratio'] >= 1.0
    volatility_filter = row['atr_ratio'] >= 1.1
    hour_filter = row['hour_local'] not in [1, 5, 17]

    if momentum_filter and volume_filter and volatility_filter and hour_filter:
        # CONTRARIAN direction
        if row['ret_5m'] >= 0.01:  # Pump up
            direction = 'SHORT'  # Fade it down
        elif row['ret_5m'] <= -0.01:  # Dump down
            direction = 'LONG'  # Fade it up
        else:
            continue

        signals.append({
            'index': i,
            'timestamp': row['timestamp_utc'],
            'direction': direction,
            'entry_price': row['close'],
            'ret_5m': row['ret_5m'],
            'vol_ratio': row['vol_ratio'],
            'atr_ratio': row['atr_ratio'],
            'hour_local': row['hour_local']
        })

print(f"✅ Generated {len(signals)} signals")

# Backtest
print("\n5. Backtesting with SL/TP logic...")

trades = []
for signal in signals:
    entry_idx = signal['index']
    direction = signal['direction']
    entry_price = signal['entry_price']

    # Set SL/TP
    if direction == 'LONG':
        sl_price = entry_price * 0.99  # -1%
        tp_price = entry_price * 1.015  # +1.5%
    else:  # SHORT
        sl_price = entry_price * 1.01  # +1%
        tp_price = entry_price * 0.985  # -1.5%

    # Check next 15 bars
    exit_reason = None
    exit_price = None
    bars_held = 0

    for k in range(entry_idx + 1, min(entry_idx + 16, len(df))):
        bars_held = k - entry_idx
        candle = df.iloc[k]

        if direction == 'LONG':
            # Check SL first (conservative)
            if candle['low'] <= sl_price:
                exit_reason = 'SL'
                exit_price = sl_price
                pnl_pct = -0.01  # -1%
                break
            # Then TP
            elif candle['high'] >= tp_price:
                exit_reason = 'TP'
                exit_price = tp_price
                pnl_pct = 0.015  # +1.5%
                break
        else:  # SHORT
            # Check SL first
            if candle['high'] >= sl_price:
                exit_reason = 'SL'
                exit_price = sl_price
                pnl_pct = -0.01  # -1%
                break
            # Then TP
            elif candle['low'] <= tp_price:
                exit_reason = 'TP'
                exit_price = tp_price
                pnl_pct = 0.015  # +1.5%
                break

    # If no SL/TP hit in 15 bars, exit at close
    if exit_reason is None:
        exit_idx = min(entry_idx + 15, len(df) - 1)
        exit_candle = df.iloc[exit_idx]
        exit_price = exit_candle['close']
        exit_reason = 'TIME'
        bars_held = exit_idx - entry_idx

        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price
        else:  # SHORT
            pnl_pct = (entry_price - exit_price) / entry_price

    trades.append({
        'entry_time': signal['timestamp'],
        'direction': direction,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'exit_reason': exit_reason,
        'bars_held': bars_held,
        'pnl_pct': pnl_pct,
        'ret_5m_signal': signal['ret_5m'],
        'vol_ratio': signal['vol_ratio'],
        'atr_ratio': signal['atr_ratio']
    })

trades_df = pd.DataFrame(trades)
print(f"✅ Backtested {len(trades_df)} trades")

# Calculate metrics with compounding
print("\n6. Calculating metrics (with compounding)...")

starting_equity = 100.0
equity = starting_equity
equity_curve = [equity]
peak = equity
drawdowns = []

for pnl in trades_df['pnl_pct']:
    equity = equity * (1 + pnl)
    equity_curve.append(equity)

    # Track drawdown
    if equity > peak:
        peak = equity
    dd = (equity - peak) / peak
    drawdowns.append(dd)

final_equity = equity
total_return_pct = (final_equity - starting_equity) / starting_equity * 100
max_dd_pct = min(drawdowns) * 100 if drawdowns else 0

# Basic stats
winners = trades_df[trades_df['pnl_pct'] > 0]
losers = trades_df[trades_df['pnl_pct'] <= 0]
win_rate = len(winners) / len(trades_df) * 100

avg_win = winners['pnl_pct'].mean() * 100 if len(winners) > 0 else 0
avg_loss = losers['pnl_pct'].mean() * 100 if len(losers) > 0 else 0

# Exit breakdown
tp_trades = len(trades_df[trades_df['exit_reason'] == 'TP'])
sl_trades = len(trades_df[trades_df['exit_reason'] == 'SL'])
time_trades = len(trades_df[trades_df['exit_reason'] == 'TIME'])

# Direction breakdown
long_trades = trades_df[trades_df['direction'] == 'LONG']
short_trades = trades_df[trades_df['direction'] == 'SHORT']

long_pnl = long_trades['pnl_pct'].sum() * 100 if len(long_trades) > 0 else 0
short_pnl = short_trades['pnl_pct'].sum() * 100 if len(short_trades) > 0 else 0

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)

print(f"\n📊 PERFORMANCE (Compounding)")
print(f"   Starting Equity:  ${starting_equity:.2f}")
print(f"   Final Equity:     ${final_equity:.2f}")
print(f"   Total Return:     {total_return_pct:+.2f}%")
print(f"   Max Drawdown:     {max_dd_pct:.2f}%")
if abs(max_dd_pct) > 0:
    return_dd_ratio = abs(total_return_pct / max_dd_pct)
    print(f"   Return/DD Ratio:  {return_dd_ratio:.2f}x")

print(f"\n📈 TRADE STATISTICS")
print(f"   Total Trades:     {len(trades_df)}")
print(f"   Win Rate:         {win_rate:.1f}%")
print(f"   Avg Winner:       {avg_win:+.2f}%")
print(f"   Avg Loser:        {avg_loss:+.2f}%")
if abs(avg_loss) > 0:
    print(f"   Win/Loss Ratio:   {abs(avg_win / avg_loss):.2f}")

print(f"\n🎯 EXIT BREAKDOWN")
print(f"   TP Hit:           {tp_trades} ({tp_trades/len(trades_df)*100:.1f}%)")
print(f"   SL Hit:           {sl_trades} ({sl_trades/len(trades_df)*100:.1f}%)")
print(f"   Time Exit:        {time_trades} ({time_trades/len(trades_df)*100:.1f}%)")

print(f"\n📊 DIRECTION BREAKDOWN")
print(f"   LONG Trades:      {len(long_trades)} ({len(long_trades)/len(trades_df)*100:.1f}%)")
print(f"   LONG Total PnL:   {long_pnl:+.2f}%")
print(f"   SHORT Trades:     {len(short_trades)} ({len(short_trades)/len(trades_df)*100:.1f}%)")
print(f"   SHORT Total PnL:  {short_pnl:+.2f}%")

print(f"\n⏱️  HOLDING TIME")
print(f"   Avg Bars Held:    {trades_df['bars_held'].mean():.1f} minutes")
print(f"   Max Bars Held:    {trades_df['bars_held'].max():.0f} minutes")

# Filter analysis
print(f"\n🔍 SIGNAL QUALITY")
print(f"   Avg |ret_5m|:     {trades_df['ret_5m_signal'].abs().mean():.4f} ({trades_df['ret_5m_signal'].abs().mean()*100:.2f}%)")
print(f"   Avg vol_ratio:    {trades_df['vol_ratio'].mean():.2f}")
print(f"   Avg atr_ratio:    {trades_df['atr_ratio'].mean():.2f}")

# Save results
trades_df.to_csv('trading/results/trumpsol_contrarian_trades.csv', index=False)
print(f"\n✅ Trade log saved to trading/results/trumpsol_contrarian_trades.csv")

print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

if total_return_pct > 20 and abs(max_dd_pct) < 5 and return_dd_ratio > 5:
    print("✅ STRATEGY PERFORMS AS CLAIMED!")
    print(f"   Return: {total_return_pct:.2f}% ✓")
    print(f"   Max DD: {max_dd_pct:.2f}% ✓")
    print(f"   Return/DD: {return_dd_ratio:.2f}x ✓")
elif total_return_pct > 0:
    print("⚠️  STRATEGY IS PROFITABLE BUT UNDERPERFORMS CLAIMED RESULTS")
    print(f"   Return: {total_return_pct:.2f}%")
    print(f"   Max DD: {max_dd_pct:.2f}%")
    print(f"   Return/DD: {return_dd_ratio:.2f}x" if abs(max_dd_pct) > 0 else "")
else:
    print("❌ STRATEGY NOT PROFITABLE ON THIS DATA")
    print(f"   Return: {total_return_pct:.2f}%")
    print(f"   Strategy may not work on TRUMPSOL")

print("=" * 80)
