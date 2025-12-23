#!/usr/bin/env python3
"""
FARTCOIN - DAILY RESET STRATEGY - WEEKLY TREND FILTER

Compare optimal config with and without weekly trend filter:
- Filter: Only trade if price < Monday open (bearish week)
- Config: SL=3.5%, TP=10%
"""

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Filter to December only
df_dec = df[df['timestamp'].dt.month == 12].copy().reset_index(drop=True)

# Add week tracking
df_dec['week'] = df_dec['timestamp'].dt.isocalendar().week
df_dec['day_of_week'] = df_dec['timestamp'].dt.dayofweek  # Monday=0, Sunday=6

print("="*140)
print("FARTCOIN - WEEKLY TREND FILTER TEST")
print("="*140)
print()

# Optimal parameters
ENTRY_OFFSET_PCT = 2.0
SL_PCT = 3.5
TP_PCT = 10.0
INITIAL_EQUITY = 100.0

# Find Monday open for each week
weekly_opens = {}
for week in df_dec['week'].unique():
    week_data = df_dec[df_dec['week'] == week].sort_values('timestamp')
    # Find first Monday (day_of_week == 0) or first day of week
    monday_data = week_data[week_data['day_of_week'] == 0]
    if len(monday_data) > 0:
        monday_open = monday_data.iloc[0]['open']
    else:
        # If no Monday data, use first available day
        monday_open = week_data.iloc[0]['open']
    weekly_opens[week] = monday_open

print("WEEKLY OPENS:")
for week, open_price in sorted(weekly_opens.items()):
    print(f"  Week {week}: ${open_price:.6f}")
print()
print("="*140)
print()

# Test both scenarios
scenarios = [
    {'name': 'NO FILTER (original)', 'filter': False},
    {'name': 'WEEKLY FILTER (below Monday open)', 'filter': True}
]

results = []

for scenario in scenarios:
    use_filter = scenario['filter']

    # Initialize
    equity = INITIAL_EQUITY
    peak_equity = INITIAL_EQUITY
    max_dd = 0.0
    trades = []
    skipped_entries = 0

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
        week = row['week']
        current_price = row['close']
        monday_open = weekly_opens[week]

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
                # Apply weekly filter if enabled
                if use_filter and current_price >= monday_open:
                    # Skip entry - we're above Monday open (bullish week)
                    skipped_entries += 1
                    continue

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
                        'week': week,
                        'monday_open': monday_open
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

        results.append({
            'scenario': scenario['name'],
            'total_return': total_return,
            'max_dd': max_dd,
            'return_dd': total_return / max_dd if max_dd > 0 else 0,
            'total_trades': len(trades_df),
            'win_rate': win_rate,
            'winners': len(winners),
            'losers': len(losers),
            'skipped_entries': skipped_entries,
            'final_equity': equity
        })

# Display results
results_df = pd.DataFrame(results)

print("RESULTS COMPARISON:")
print("="*140)
print()

for _, row in results_df.iterrows():
    status = "🔥" if row['total_return'] > 30 else ("✅" if row['total_return'] > 20 else ("💚" if row['total_return'] > 0 else "❌"))
    print(f"{'='*140}")
    print(f"{row['scenario']}")
    print(f"{'='*140}")
    print(f"  Return:          {row['total_return']:>+10.2f}%")
    print(f"  Max DD:          {row['max_dd']:>10.2f}%")
    print(f"  Return/DD:       {row['return_dd']:>10.2f}x")
    print(f"  Total Trades:    {row['total_trades']:>10.0f}")
    print(f"  Win Rate:        {row['win_rate']:>10.1f}%")
    print(f"  Winners:         {row['winners']:>10.0f}")
    print(f"  Losers:          {row['losers']:>10.0f}")
    if row['skipped_entries'] > 0:
        print(f"  Skipped Entries: {row['skipped_entries']:>10.0f} (above Monday open)")
    print(f"  Final Equity:    ${row['final_equity']:>9.2f}  {status}")
    print()

print("="*140)
print()

# Compare
no_filter = results_df[results_df['scenario'].str.contains('NO FILTER')].iloc[0]
with_filter = results_df[results_df['scenario'].str.contains('WEEKLY FILTER')].iloc[0]

print("COMPARISON:")
print()
print(f"Return:       {no_filter['total_return']:>+10.2f}% (no filter) vs {with_filter['total_return']:>+10.2f}% (with filter)")
print(f"Trades:       {no_filter['total_trades']:>10.0f} (no filter) vs {with_filter['total_trades']:>10.0f} (with filter)")
print(f"Win Rate:     {no_filter['win_rate']:>10.1f}% (no filter) vs {with_filter['win_rate']:>10.1f}% (with filter)")
print(f"Max DD:       {no_filter['max_dd']:>10.2f}% (no filter) vs {with_filter['max_dd']:>10.2f}% (with filter)")
print()

if with_filter['total_return'] > no_filter['total_return']:
    improvement = with_filter['total_return'] - no_filter['total_return']
    print(f"✅ IMPROVEMENT: Weekly filter improves return by {improvement:+.2f}%")
    print(f"   Filter skipped {with_filter['skipped_entries']:.0f} entries (above Monday open)")
else:
    decline = no_filter['total_return'] - with_filter['total_return']
    print(f"❌ DECLINE: Weekly filter reduces return by {decline:.2f}%")
    print(f"   Filter skipped {with_filter['skipped_entries']:.0f} entries that may have been profitable")

print()
print("="*140)
