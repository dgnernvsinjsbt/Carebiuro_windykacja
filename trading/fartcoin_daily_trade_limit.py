#!/usr/bin/env python3
"""
FARTCOIN - DAILY RESET STRATEGY - TRADE LIMIT OPTIMIZATION

Test optimal config (SL=3.5%, TP=10%) with different daily trade limits
"""

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Filter to December only
df_dec = df[df['timestamp'].dt.month == 12].copy().reset_index(drop=True)

print("="*140)
print("FARTCOIN - DAILY TRADE LIMIT OPTIMIZATION")
print("="*140)
print()

# Optimal parameters from grid search
ENTRY_OFFSET_PCT = 2.0
SL_PCT = 3.5
TP_PCT = 10.0
INITIAL_EQUITY = 100.0

# Test different daily trade limits (None = unlimited)
trade_limits = [None, 1, 2, 3, 4, 5]

results = []

for MAX_TRADES_PER_DAY in trade_limits:
    # Initialize
    equity = INITIAL_EQUITY
    peak_equity = INITIAL_EQUITY
    max_dd = 0.0
    trades = []
    daily_stats = []

    # Track current day state
    current_day = None
    daily_high = 0
    in_position = False
    tp_hit_today = False
    position = None
    trades_today = 0

    # Iterate through candles
    for i in range(len(df_dec)):
        row = df_dec.iloc[i]
        timestamp = row['timestamp']
        day = timestamp.date()

        # Check if new day (reset)
        if day != current_day:
            # Record previous day stats
            if current_day is not None:
                day_trades = [t for t in trades if t['day'] == current_day]
                daily_stats.append({
                    'day': current_day,
                    'trades': len(day_trades),
                    'pnl': sum([t['pnl_dollar'] for t in day_trades])
                })

            current_day = day
            daily_high = row['high']
            tp_hit_today = False
            trades_today = 0

            # If we're still in position from previous day, close it at open
            if in_position:
                exit_price = row['open']
                if position['direction'] == 'SHORT':
                    pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

                pnl_dollar = position['position_size'] * (pnl_pct / 100)
                equity += pnl_dollar

                trades.append({
                    'day': current_day,
                    'result': 'DAY_CLOSE',
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                })

                in_position = False
                position = None

        # Update daily high
        if row['high'] > daily_high:
            daily_high = row['high']

        # Check if we've hit daily trade limit
        if MAX_TRADES_PER_DAY is not None and trades_today >= MAX_TRADES_PER_DAY:
            continue

        # If not in position and haven't hit TP today, check for entry
        if not in_position and not tp_hit_today:
            trigger_price = daily_high * (1 - ENTRY_OFFSET_PCT / 100)

            # Check if price dropped to trigger (intra-candle entry)
            if row['low'] <= trigger_price:
                # ENTRY - SHORT position
                entry_price = trigger_price
                sl_price = entry_price * (1 + SL_PCT / 100)
                tp_price = entry_price * (1 - TP_PCT / 100)

                # Position size: risk 5% of equity
                position_size = (equity * 5.0) / SL_PCT

                if position_size > 0:
                    in_position = True
                    position = {
                        'entry_price': entry_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'position_size': position_size,
                        'direction': 'SHORT',
                    }

        # If in position, check for exit
        if in_position:
            hit_sl = False
            hit_tp = False
            exit_price = None

            # Check SL
            if row['high'] >= position['sl_price']:
                hit_sl = True
                exit_price = position['sl_price']

            # Check TP
            elif row['low'] <= position['tp_price']:
                hit_tp = True
                exit_price = position['tp_price']

            if hit_sl or hit_tp:
                # Calculate P&L
                if position['direction'] == 'SHORT':
                    pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

                pnl_dollar = position['position_size'] * (pnl_pct / 100)
                equity += pnl_dollar

                # Update peak equity and drawdown
                if equity > peak_equity:
                    peak_equity = equity
                dd = ((peak_equity - equity) / peak_equity) * 100
                if dd > max_dd:
                    max_dd = dd

                # Record trade
                trades.append({
                    'day': day,
                    'result': 'TP' if hit_tp else 'SL',
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                })

                # Exit position
                in_position = False
                position = None
                trades_today += 1

                # If TP hit, stop trading for the day
                if hit_tp:
                    tp_hit_today = True

    # Record last day
    if current_day is not None:
        day_trades = [t for t in trades if t['day'] == current_day]
        daily_stats.append({
            'day': current_day,
            'trades': len(day_trades),
            'pnl': sum([t['pnl_dollar'] for t in day_trades])
        })

    # Calculate results
    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)

        total_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
        win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100

        # Calculate max trades per day
        daily_df = pd.DataFrame(daily_stats)
        max_trades_day = daily_df['trades'].max()
        avg_trades_day = daily_df['trades'].mean()

        results.append({
            'max_trades_limit': 'Unlimited' if MAX_TRADES_PER_DAY is None else MAX_TRADES_PER_DAY,
            'total_return': total_return,
            'max_dd': max_dd,
            'return_dd': total_return / max_dd if max_dd > 0 else 0,
            'total_trades': len(trades_df),
            'win_rate': win_rate,
            'max_trades_day': max_trades_day,
            'avg_trades_day': avg_trades_day,
            'final_equity': equity
        })

# Display results
results_df = pd.DataFrame(results)

print(f"OPTIMAL CONFIG: SL=3.5%, TP=10%")
print("="*140)
print()
print(f"{'Limit':<12} {'Return':<12} {'Max DD':<12} {'R/DD':<10} {'Total Trades':<15} {'WR %':<10} {'Max/Day':<10} {'Avg/Day':<10} {'Final $':<12}")
print("-"*140)

for _, row in results_df.iterrows():
    status = "🔥" if row['total_return'] > 30 else ("✅" if row['total_return'] > 20 else ("💚" if row['total_return'] > 0 else "❌"))
    limit_str = str(row['max_trades_limit'])
    print(f"{limit_str:<12} {row['total_return']:>+10.2f}%  {row['max_dd']:>10.2f}%  {row['return_dd']:>8.2f}x  {row['total_trades']:<15.0f} {row['win_rate']:>8.1f}%  {row['max_trades_day']:<10.0f} {row['avg_trades_day']:<10.1f} ${row['final_equity']:>10.2f}  {status}")

print()
print("="*140)
print()

# Find best result
best_return = results_df.loc[results_df['total_return'].idxmax()]
best_return_dd = results_df.loc[results_df['return_dd'].idxmax()]

print("BEST RESULTS:")
print()
print(f"🏆 Best Return: {best_return['max_trades_limit']} trades/day → Return: {best_return['total_return']:+.2f}%, R/DD: {best_return['return_dd']:.2f}x")
print(f"🎯 Best R/DD: {best_return_dd['max_trades_limit']} trades/day → Return: {best_return_dd['total_return']:+.2f}%, R/DD: {best_return_dd['return_dd']:.2f}x")

print()

# Show improvement
unlimited = results_df[results_df['max_trades_limit'] == 'Unlimited'].iloc[0]
if best_return['total_return'] > unlimited['total_return']:
    improvement = best_return['total_return'] - unlimited['total_return']
    print(f"✅ IMPROVEMENT: Limiting to {best_return['max_trades_limit']} trades/day improves return by {improvement:+.2f}%")
else:
    print(f"❌ NO IMPROVEMENT: Unlimited trades is still best")

print()
print("="*140)
