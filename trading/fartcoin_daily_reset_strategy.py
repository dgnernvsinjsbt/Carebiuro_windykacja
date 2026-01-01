#!/usr/bin/env python3
"""
FARTCOIN - DAILY RESET STRATEGY

Strategy:
1. Daily reset at midnight (track highest high of the day)
2. Entry: Market order when price drops 2% below daily high (INTRA-CANDLE)
3. SL: At the highest high level
4. TP: 8% below entry
5. Rules:
   - Only ONE position at a time
   - If TP hit → stop trading for the day
   - If SL hit → monitor new highest high, can trade again
   - Multiple trades per day allowed SEQUENTIALLY
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
print("FARTCOIN - DAILY RESET STRATEGY (December 2025)")
print("="*140)
print()

# Trading parameters
ENTRY_OFFSET_PCT = 2.0  # Enter when 2% below daily high
TP_PCT = 8.0            # Take profit 8%
INITIAL_EQUITY = 100.0

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

print(f"Initial equity: ${equity:.2f}")
print(f"Entry trigger: 2% below daily high")
print(f"Take profit: 8%")
print(f"Stop loss: At daily high")
print()
print("="*140)
print()

# Iterate through candles
for i in range(len(df_dec)):
    row = df_dec.iloc[i]
    timestamp = row['timestamp']
    day = timestamp.date()

    # Check if new day (reset)
    if day != current_day:
        # New day started
        if current_day is not None:
            # Record previous day stats
            day_trades = [t for t in trades if t['day'] == current_day]
            daily_stats.append({
                'day': current_day,
                'trades': len(day_trades),
                'pnl': sum([t['pnl_dollar'] for t in day_trades]),
                'equity': equity
            })

        current_day = day
        daily_high = row['high']
        tp_hit_today = False

        # If we're still in position from previous day, close it at open
        if in_position:
            # Close at opening price
            exit_price = row['open']
            if position['direction'] == 'SHORT':
                pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100

            pnl_dollar = position['position_size'] * (pnl_pct / 100)
            equity += pnl_dollar

            trades.append({
                'day': current_day,
                'entry_time': position['entry_time'],
                'exit_time': timestamp,
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'result': 'DAY_CLOSE',
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'equity': equity
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
            entry_price = trigger_price  # Enter at trigger price
            sl_price = daily_high
            tp_price = entry_price * (1 - TP_PCT / 100)

            # Calculate SL distance
            sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

            # Position size: risk 5% of equity
            position_size = (equity * 5.0) / sl_dist_pct if sl_dist_pct > 0 else 0

            if position_size > 0:
                in_position = True
                position = {
                    'entry_time': timestamp,
                    'entry_price': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'sl_dist_pct': sl_dist_pct,
                    'position_size': position_size,
                    'direction': 'SHORT',
                    'day': day
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
                'day': day,
                'entry_time': position['entry_time'],
                'exit_time': timestamp,
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'sl_price': position['sl_price'],
                'tp_price': position['tp_price'],
                'result': 'TP' if hit_tp else 'SL',
                'pnl_pct': pnl_pct,
                'pnl_dollar': pnl_dollar,
                'equity': equity,
                'daily_high': daily_high
            })

            # Exit position
            in_position = False
            position = None

            # If TP hit, stop trading for the day
            if hit_tp:
                tp_hit_today = True

# Close last day
if current_day is not None:
    day_trades = [t for t in trades if t['day'] == current_day]
    daily_stats.append({
        'day': current_day,
        'trades': len(day_trades),
        'pnl': sum([t['pnl_dollar'] for t in day_trades]),
        'equity': equity
    })

# Calculate results
print("="*140)
print("RESULTS")
print("="*140)
print()

if len(trades) > 0:
    trades_df = pd.DataFrame(trades)

    total_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
    win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100

    winners = trades_df[trades_df['result'] == 'TP']
    losers = trades_df[trades_df['result'] == 'SL']

    print(f"📊 OVERALL PERFORMANCE:")
    print(f"   Initial Equity: ${INITIAL_EQUITY:.2f}")
    print(f"   Final Equity: ${equity:.2f}")
    print(f"   Total Return: {total_return:+.2f}%")
    print(f"   Max Drawdown: {max_dd:.2f}%")
    print(f"   Return/DD: {total_return/max_dd if max_dd > 0 else 0:.2f}x")
    print()

    print(f"📈 TRADE STATISTICS:")
    print(f"   Total Trades: {len(trades_df)}")
    print(f"   Winners: {len(winners)} ({win_rate:.1f}%)")
    print(f"   Losers: {len(losers)} ({100-win_rate:.1f}%)")
    print()

    if len(winners) > 0:
        print(f"   Avg Win: {winners['pnl_pct'].mean():.2f}% (${winners['pnl_dollar'].mean():.2f})")
        print(f"   Largest Win: {winners['pnl_pct'].max():.2f}% (${winners['pnl_dollar'].max():.2f})")

    if len(losers) > 0:
        print(f"   Avg Loss: {losers['pnl_pct'].mean():.2f}% (${losers['pnl_dollar'].mean():.2f})")
        print(f"   Largest Loss: {losers['pnl_pct'].min():.2f}% (${losers['pnl_dollar'].min():.2f})")

    print()

    # Daily breakdown
    print(f"📅 DAILY BREAKDOWN:")
    print()
    for day_stat in daily_stats:
        status = "✅" if day_stat['pnl'] >= 0 else "❌"
        print(f"   {day_stat['day']}: {day_stat['trades']} trades, P&L: ${day_stat['pnl']:+.2f}, Equity: ${day_stat['equity']:.2f} {status}")

    print()
    print("="*140)
    print()

    # Show sample trades
    print(f"🔍 SAMPLE TRADES (first 10):")
    print()
    for i, trade in enumerate(trades[:10]):
        print(f"Trade #{i+1}:")
        print(f"  Day: {trade['day']}")
        print(f"  Entry: {trade['entry_time']} @ ${trade['entry_price']:.6f}")
        print(f"  Exit: {trade['exit_time']} @ ${trade['exit_price']:.6f}")
        print(f"  Daily High: ${trade['daily_high']:.6f}")
        print(f"  SL: ${trade['sl_price']:.6f}, TP: ${trade['tp_price']:.6f}")
        print(f"  Result: {trade['result']}")
        print(f"  P&L: {trade['pnl_pct']:+.2f}% (${trade['pnl_dollar']:+.2f})")
        print(f"  Equity after: ${trade['equity']:.2f}")
        print()

    print("="*140)

    # Verdict
    if total_return > 20 and total_return / max_dd > 2:
        print(f"🔥 STRONG STRATEGY! Return: {total_return:+.2f}%, R/DD: {total_return/max_dd:.2f}x")
    elif total_return > 0:
        print(f"✅ PROFITABLE: Return: {total_return:+.2f}%, R/DD: {total_return/max_dd:.2f}x")
    else:
        print(f"❌ UNPROFITABLE: Return: {total_return:+.2f}%")

else:
    print("No trades executed!")

print("="*140)
