#!/usr/bin/env python3
"""
PENGU - RSI Divergence Strategy (CORRECTED LOGIC)
1. RSI >80 → ARM, track highest high + RSI
2. Price breaks highest high with lower RSI → Divergence #1
3. Price breaks NEW highest high with lower RSI → Divergence #2
4. After 2 divergences → Enter on next red candle
Nov-Dec 2025
"""
import pandas as pd
import numpy as np

print("="*90)
print("PENGU - RSI DIVERGENCE (CORRECTED LOGIC) - Nov-Dec 2025")
print("="*90)

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Filter to Nov-Dec 2025
df = df[(df['timestamp'] >= '2025-11-01') & (df['timestamp'] < '2026-01-01')].reset_index(drop=True)

print(f"\n📊 Data: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Period: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

# Calculate RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Strategy parameters
rsi_arm_threshold = 80
required_divergences = 2
tp_pct = 8.0
max_sl_pct = 15.0
risk_pct = 5.0

print(f"\n📋 Strategy:")
print(f"   1. RSI crosses >{rsi_arm_threshold} → ARM, track highest high + RSI")
print(f"   2. Price breaks highest high with lower RSI → Divergence #1")
print(f"   3. Price breaks NEW highest high with lower RSI → Divergence #2")
print(f"   4. After {required_divergences} divergences → Enter on next red candle")
print(f"   5. SL = highest high, TP = {tp_pct}%")

# Backtest
equity = 100.0
trades = []
signals = []

# State tracking
armed = False
arm_rsi = None
highest_high = None
highest_high_idx = None
divergence_count = 0
looking_for_entry = False

in_position = False
entry_price = None
sl_price = None
tp_price = None
entry_idx = None

for i in range(20, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']):
        continue

    # Check if in position
    if in_position:
        # Check for exit
        if row['high'] >= sl_price:
            # Hit SL
            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100
            pnl_pct = -sl_dist_pct
            position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)
            pnl_dollar = position_size * (pnl_pct / 100)
            equity += pnl_dollar

            trades.append({
                'entry_time': df.iloc[entry_idx]['timestamp'],
                'exit_time': row['timestamp'],
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'exit_price': sl_price,
                'sl_dist_pct': sl_dist_pct,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'exit_reason': 'SL',
                'equity_after': equity
            })

            in_position = False
            # Reset state
            armed = False
            divergence_count = 0
            looking_for_entry = False

        elif row['low'] <= tp_price:
            # Hit TP
            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100
            pnl_pct = tp_pct
            position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)
            pnl_dollar = position_size * (pnl_pct / 100)
            equity += pnl_dollar

            trades.append({
                'entry_time': df.iloc[entry_idx]['timestamp'],
                'exit_time': row['timestamp'],
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'exit_price': tp_price,
                'sl_dist_pct': sl_dist_pct,
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'exit_reason': 'TP',
                'equity_after': equity
            })

            in_position = False
            # Reset state
            armed = False
            divergence_count = 0
            looking_for_entry = False

        continue

    # STEP 1: ARM when RSI crosses >80
    if not armed and not in_position:
        if row['rsi'] > rsi_arm_threshold:
            armed = True
            arm_rsi = row['rsi']
            highest_high = row['high']
            highest_high_idx = i
            divergence_count = 0
            looking_for_entry = False

    # STEP 2: Track divergences while armed
    if armed and not looking_for_entry:
        # Check if price made a new high
        if row['high'] > highest_high:
            # New high! Check RSI
            if row['rsi'] < arm_rsi:
                # RSI lower than at ARM → DIVERGENCE!
                divergence_count += 1

                # Update highest high for next divergence check
                highest_high = row['high']
                highest_high_idx = i

                if divergence_count >= required_divergences:
                    # Ready to enter on next red candle
                    looking_for_entry = True

    # STEP 3: Looking for entry after divergences
    if looking_for_entry and not in_position:
        # Check if red candle
        is_red = row['close'] < row['open']

        if is_red:
            # ENTRY!
            entry_price = row['close']

            # SL = highest high in last 6 hours (24 bars on 15m)
            lookback_start = max(0, i - 24)
            sl_price = df.iloc[lookback_start:i+1]['high'].max()

            tp_price = entry_price * (1 - tp_pct / 100)
            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

            # Validate SL distance
            if sl_dist_pct > 0 and sl_dist_pct <= max_sl_pct:
                signals.append({
                    'time': row['timestamp'],
                    'arm_rsi': arm_rsi,
                    'divergences': divergence_count,
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'sl_dist_pct': sl_dist_pct
                })

                in_position = True
                entry_idx = i

            # Reset regardless of entry
            looking_for_entry = False
            armed = False
            divergence_count = 0

# Results
print(f"\n" + "="*90)
print("📊 RESULTS")
print("="*90)
print()

print(f"Signals Generated: {len(signals)}")
print(f"Trades Executed:   {len(trades)}")
print()

if len(trades) > 0:
    trades_df = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100

    # Max DD
    equity_curve = [100.0]
    for pnl in trades_df['pnl_dollar']:
        equity_curve.append(equity_curve[-1] + pnl)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = trades_df[trades_df['pnl_dollar'] > 0]
    losers = trades_df[trades_df['pnl_dollar'] < 0]
    win_rate = (len(winners) / len(trades_df)) * 100

    tp_count = len(trades_df[trades_df['exit_reason'] == 'TP'])
    sl_count = len(trades_df[trades_df['exit_reason'] == 'SL'])

    print(f"📈 Performance:")
    print(f"   Total Return:     {total_return:+.1f}%")
    print(f"   Max Drawdown:     {max_dd:.2f}%")
    print(f"   Return/DD:        {return_dd:.2f}x")
    print(f"   Final Equity:     ${equity:.2f}")
    print()

    print(f"📊 Trade Statistics:")
    print(f"   Total Trades:     {len(trades_df)}")
    print(f"   Winners:          {len(winners)} ({win_rate:.1f}%)")
    print(f"   Losers:           {len(losers)} ({100-win_rate:.1f}%)")
    print(f"   TP Hits:          {tp_count}")
    print(f"   SL Hits:          {sl_count}")
    print(f"   Avg SL Distance:  {trades_df['sl_dist_pct'].mean():.2f}%")
    print()

    # Show all trades
    print(f"📋 ALL TRADES:")
    print()
    print(f"{'Entry Time':>20} | {'Entry $':>10} | {'SL $':>10} | {'SL %':>6} | {'Exit':>4} | {'P&L %':>7} | {'P&L $':>8}")
    print("-" * 90)

    for _, t in trades_df.iterrows():
        print(f"{str(t['entry_time'])[:19]:>20} | ${t['entry_price']:>9.6f} | ${t['sl_price']:>9.6f} | {t['sl_dist_pct']:>5.2f}% | {t['exit_reason']:>4} | {t['pnl_pct']:>6.1f}% | ${t['pnl_dollar']:>7.2f}")

    trades_df.to_csv('pengu_divergence_correct_trades.csv', index=False)
    print(f"\n💾 Trades saved to: pengu_divergence_correct_trades.csv")

else:
    print("❌ No trades generated!")

print("="*90)
