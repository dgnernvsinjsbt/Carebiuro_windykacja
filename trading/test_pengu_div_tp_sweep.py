#!/usr/bin/env python3
"""
PENGU RSI Divergence - Test different TP levels
"""
import pandas as pd
import numpy as np

# Load PENGU data
df = pd.read_csv('penguusdt_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

print("="*100)
print("PENGU RSI DIVERGENCE - TP LEVEL SWEEP")
print("="*100)
print(f"\nData: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Period: {(df['timestamp'].max() - df['timestamp'].min()).days} days\n")

# Test different TP levels
tp_levels = [3.0, 4.0, 5.0, 6.0, 8.0]
results = []

for tp_pct in tp_levels:
    equity = 100.0
    trades = []
    risk_pct = 5.0

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

    # Calculate metrics
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
        win_rate = (len(winners) / len(trades_df)) * 100

        tp_count = len(trades_df[trades_df['exit_reason'] == 'TP'])

        results.append({
            'tp_pct': tp_pct,
            'total_return': total_return,
            'max_dd': max_dd,
            'return_dd': return_dd,
            'final_equity': equity,
            'total_trades': len(trades_df),
            'winners': len(winners),
            'win_rate': win_rate,
            'tp_hits': tp_count
        })

# Display results
print("="*100)
print(f"{'TP %':>6} | {'Return':>8} | {'Max DD':>8} | {'R/DD':>7} | {'Trades':>7} | {'Winners':>8} | {'Win %':>7} | {'Final $':>9}")
print("-"*100)

for r in results:
    print(f"{r['tp_pct']:>5.1f}% | {r['total_return']:>7.1f}% | {r['max_dd']:>7.2f}% | {r['return_dd']:>6.2f}x | {r['total_trades']:>7} | {r['winners']:>8} | {r['win_rate']:>6.1f}% | ${r['final_equity']:>8.2f}")

print("="*100)

# Find best by Return/DD
best = max(results, key=lambda x: x['return_dd'])
print(f"\n🏆 Best Return/DD: TP={best['tp_pct']:.1f}% with {best['return_dd']:.2f}x R/DD, {best['win_rate']:.1f}% win rate")

# Find best by Win Rate
best_wr = max(results, key=lambda x: x['win_rate'])
print(f"🎯 Best Win Rate: TP={best_wr['tp_pct']:.1f}% with {best_wr['win_rate']:.1f}% win rate, {best_wr['return_dd']:.2f}x R/DD")
