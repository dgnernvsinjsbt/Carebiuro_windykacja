#!/usr/bin/env python3
"""
PENGU RSI Divergence - FIXED (Full 6 Months)
"""
import pandas as pd
import numpy as np

print("="*90)
print("PENGU RSI DIVERGENCE - FIXED LOGIC (6 MONTHS)")
print("="*90)

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# No filter - use full 6 months

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

# Parameters
tp_pct = 8.0
risk_pct = 5.0

# Backtest
equity = 100.0
trades = []

# State tracking
armed = False
arm_rsi = None
highest_high = None
divergence_count = 0
looking_for_entry = False

for i in range(20, len(df)):
    row = df.iloc[i]

    if pd.isna(row['rsi']):
        continue

    # ARM
    if not armed and not looking_for_entry:
        if row['rsi'] > 80:
            armed = True
            arm_rsi = row['rsi']
            highest_high = row['high']
            divergence_count = 0

    # Divergences
    if armed and divergence_count < 2:
        if row['high'] > highest_high:
            if row['rsi'] < arm_rsi:
                divergence_count += 1
                highest_high = row['high']

                if divergence_count >= 2:
                    looking_for_entry = True
            else:
                highest_high = row['high']

    # Entry
    if looking_for_entry:
        is_red = row['close'] < row['open']

        if is_red:
            lookback_start = max(0, i - 24)
            sl_price = df.iloc[lookback_start:i+1]['high'].max()
            entry_price = row['close']
            tp_price = entry_price * (1 - tp_pct / 100)
            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

            if sl_dist_pct > 0 and sl_dist_pct <= 15:
                # ENTER TRADE
                position_size = (equity * (risk_pct / 100)) / (sl_dist_pct / 100)

                # Find exit
                hit_sl = False
                hit_tp = False
                exit_idx = None

                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]

                    if future_row['high'] >= sl_price:
                        hit_sl = True
                        exit_idx = j
                        break
                    elif future_row['low'] <= tp_price:
                        hit_tp = True
                        exit_idx = j
                        break

                if hit_sl:
                    pnl_pct = -sl_dist_pct
                    exit_reason = 'SL'
                elif hit_tp:
                    pnl_pct = tp_pct
                    exit_reason = 'TP'
                else:
                    # No exit found
                    armed = False
                    looking_for_entry = False
                    divergence_count = 0
                    continue

                pnl_dollar = position_size * (pnl_pct / 100)
                equity += pnl_dollar

                trades.append({
                    'entry_time': row['timestamp'],
                    'exit_time': df.iloc[exit_idx]['timestamp'] if exit_idx else None,
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'sl_dist_pct': sl_dist_pct,
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'exit_reason': exit_reason,
                    'equity_after': equity
                })

            # Reset regardless
            armed = False
            looking_for_entry = False
            divergence_count = 0

# Results
print(f"\n" + "="*90)
print("📊 RESULTS")
print("="*90)
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

    print(f"📋 ALL TRADES:")
    print()
    print(f"{'Entry Time':>20} | {'Entry $':>10} | {'SL $':>10} | {'SL %':>6} | {'Exit':>4} | {'P&L %':>7} | {'P&L $':>8}")
    print("-" * 90)

    for _, t in trades_df.iterrows():
        print(f"{str(t['entry_time'])[:19]:>20} | ${t['entry_price']:>9.6f} | ${t['sl_price']:>9.6f} | {t['sl_dist_pct']:>5.2f}% | {t['exit_reason']:>4} | {t['pnl_pct']:>6.1f}% | ${t['pnl_dollar']:>7.2f}")

    trades_df.to_csv('pengu_divergence_fixed_trades.csv', index=False)
    print(f"\n💾 Saved: pengu_divergence_fixed_trades.csv")

else:
    print("❌ No trades!")

print("="*90)
