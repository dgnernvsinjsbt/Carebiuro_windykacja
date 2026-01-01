#!/usr/bin/env python3
"""
FARTCOIN - DAILY RESET STRATEGY - TP SWEEP

Test different TP values from 6% to 15%
Keep everything else constant:
- Entry: 2% below daily high
- SL: at daily high
- Risk: 5% per trade
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
print("FARTCOIN - DAILY RESET STRATEGY - TP OPTIMIZATION")
print("="*140)
print()

# Trading parameters
ENTRY_OFFSET_PCT = 2.0  # Enter when 2% below daily high
INITIAL_EQUITY = 100.0

# Test different TP values
tp_values = list(range(6, 16))  # 6% to 15%

results = []

for TP_PCT in tp_values:
    # Initialize
    equity = INITIAL_EQUITY
    peak_equity = INITIAL_EQUITY
    max_dd = 0.0
    trades = []

    # Track current day state
    current_day = None
    daily_high = 0
    in_position = False
    tp_hit_today = False
    position = None

    # Iterate through candles
    for i in range(len(df_dec)):
        row = df_dec.iloc[i]
        timestamp = row['timestamp']
        day = timestamp.date()

        # Check if new day (reset)
        if day != current_day:
            current_day = day
            daily_high = row['high']
            tp_hit_today = False

            # If we're still in position from previous day, close it at open
            if in_position:
                exit_price = row['open']
                if position['direction'] == 'SHORT':
                    pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

                pnl_dollar = position['position_size'] * (pnl_pct / 100)
                equity += pnl_dollar

                trades.append({
                    'result': 'DAY_CLOSE',
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                })

                in_position = False
                position = None

        # Update daily high
        if row['high'] > daily_high:
            daily_high = row['high']

        # If not in position and haven't hit TP today, check for entry
        if not in_position and not tp_hit_today:
            trigger_price = daily_high * (1 - ENTRY_OFFSET_PCT / 100)

            # Check if price dropped to trigger (intra-candle entry)
            if row['low'] <= trigger_price:
                # ENTRY - SHORT position
                entry_price = trigger_price
                sl_price = daily_high
                tp_price = entry_price * (1 - TP_PCT / 100)

                # Calculate SL distance
                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                # Position size: risk 5% of equity
                position_size = (equity * 5.0) / sl_dist_pct if sl_dist_pct > 0 else 0

                if position_size > 0:
                    in_position = True
                    position = {
                        'entry_price': entry_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'sl_dist_pct': sl_dist_pct,
                        'position_size': position_size,
                        'direction': 'SHORT',
                    }

        # If in position, check for exit
        if in_position:
            hit_sl = False
            hit_tp = False
            exit_price = None

            # Check SL (price goes up to daily high)
            if row['high'] >= position['sl_price']:
                hit_sl = True
                exit_price = position['sl_price']

            # Check TP (price goes down to TP)
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
                    'result': 'TP' if hit_tp else 'SL',
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                })

                # Exit position
                in_position = False
                position = None

                # If TP hit, stop trading for the day
                if hit_tp:
                    tp_hit_today = True

    # Calculate results
    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)

        total_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
        win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100

        winners = trades_df[trades_df['result'] == 'TP']
        losers = trades_df[trades_df['result'] == 'SL']

        avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
        avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0

        # Calculate expectancy
        expectancy = (win_rate/100 * avg_win) + ((100-win_rate)/100 * avg_loss)

        results.append({
            'tp_pct': TP_PCT,
            'total_return': total_return,
            'max_dd': max_dd,
            'return_dd': total_return / max_dd if max_dd > 0 else 0,
            'total_trades': len(trades_df),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'expectancy': expectancy,
            'final_equity': equity
        })

# Display results
results_df = pd.DataFrame(results)

print("TP OPTIMIZATION RESULTS:")
print("="*140)
print()
print(f"{'TP %':<8} {'Return':<12} {'Max DD':<12} {'R/DD':<10} {'Trades':<10} {'WR %':<10} {'Avg Win':<12} {'Avg Loss':<12} {'Expectancy':<12} {'Final $':<12}")
print("-"*140)

for _, row in results_df.iterrows():
    status = "🔥" if row['total_return'] > 0 else "❌"
    print(f"{row['tp_pct']:<8.0f} {row['total_return']:>+10.2f}%  {row['max_dd']:>10.2f}%  {row['return_dd']:>8.2f}x  {row['total_trades']:<10.0f} {row['win_rate']:>8.1f}%  {row['avg_win']:>+10.2f}%  {row['avg_loss']:>+10.2f}%  {row['expectancy']:>+10.3f}%  ${row['final_equity']:>10.2f}  {status}")

print()
print("="*140)
print()

# Find best result
best_return = results_df.loc[results_df['total_return'].idxmax()]
best_return_dd = results_df.loc[results_df['return_dd'].idxmax()]
best_expectancy = results_df.loc[results_df['expectancy'].idxmax()]

print("BEST RESULTS:")
print()
print(f"🏆 Best Return: TP={best_return['tp_pct']:.0f}% → Return: {best_return['total_return']:+.2f}%, R/DD: {best_return['return_dd']:.2f}x")
print(f"🎯 Best R/DD: TP={best_return_dd['tp_pct']:.0f}% → Return: {best_return_dd['total_return']:+.2f}%, R/DD: {best_return_dd['return_dd']:.2f}x")
print(f"📊 Best Expectancy: TP={best_expectancy['tp_pct']:.0f}% → Expectancy: {best_expectancy['expectancy']:+.3f}%, Return: {best_expectancy['total_return']:+.2f}%")

print()
print("="*140)

# Summary
positive_returns = results_df[results_df['total_return'] > 0]
if len(positive_returns) > 0:
    print()
    print(f"✅ {len(positive_returns)}/{len(results_df)} TP values are profitable")
    print(f"   Range: {positive_returns['tp_pct'].min():.0f}% to {positive_returns['tp_pct'].max():.0f}%")
else:
    print()
    print(f"❌ NO PROFITABLE TP VALUES FOUND")
    print(f"   Best was TP={best_return['tp_pct']:.0f}% with {best_return['total_return']:+.2f}% return")

print()
print("="*140)
