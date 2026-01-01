#!/usr/bin/env python3
"""
Analyze WHERE the extra profit comes from in the overlapping backtest
- Multiple LONGs at same time?
- Multiple SHORTs at same time?
- LONG + SHORT hedging?
- Which overlaps are profitable?
"""

import pandas as pd
import numpy as np

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def generate_signals(df):
    df = df.copy()
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
    df['atr_ma'] = df['atr'].rolling(20).mean()
    df['atr_ratio'] = df['atr'] / df['atr_ma']
    df['ema20'] = calculate_ema(df['close'], 20)
    df['distance'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)
    df['bullish'] = df['close'] > df['open']
    df['bearish'] = df['close'] < df['open']

    signals = []
    for i in range(len(df)):
        if df['atr_ratio'].iloc[i] > 1.5 and df['distance'].iloc[i] < 3.0:
            if df['bullish'].iloc[i]:
                signals.append(('LONG', i))
            elif df['bearish'].iloc[i]:
                signals.append(('SHORT', i))
    return signals

def backtest_with_tracking(df, signals):
    """Backtest that tracks WHICH trades overlap and their P&L"""
    df = df.copy()
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])

    trades = []
    trade_id = 0

    for direction, signal_idx in signals:
        if signal_idx >= len(df) - 1:
            continue

        signal_price = df['close'].iloc[signal_idx]
        signal_atr = df['atr'].iloc[signal_idx]

        if pd.isna(signal_atr) or signal_atr == 0:
            continue

        # Set limit order
        if direction == 'LONG':
            limit_price = signal_price * 1.01
        else:
            limit_price = signal_price * 0.99

        # Try to fill
        filled = False
        fill_idx = None

        for i in range(signal_idx + 1, min(signal_idx + 4, len(df))):
            if direction == 'LONG':
                if df['high'].iloc[i] >= limit_price:
                    filled = True
                    fill_idx = i
                    break
            else:
                if df['low'].iloc[i] <= limit_price:
                    filled = True
                    fill_idx = i
                    break

        if not filled:
            continue

        # Trade filled
        entry_price = limit_price
        entry_atr = df['atr'].iloc[fill_idx]

        sl_dist = 2.0 * entry_atr
        tp_dist = 8.0 * entry_atr

        if direction == 'LONG':
            sl_price = entry_price - sl_dist
            tp_price = entry_price + tp_dist
        else:
            sl_price = entry_price + sl_dist
            tp_price = entry_price - tp_dist

        # Find exit
        exit_idx = None
        exit_price = None
        exit_reason = None

        for i in range(fill_idx + 1, min(fill_idx + 200, len(df))):
            if direction == 'LONG':
                if df['low'].iloc[i] <= sl_price:
                    exit_idx = i
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break
                if df['high'].iloc[i] >= tp_price:
                    exit_idx = i
                    exit_price = tp_price
                    exit_reason = 'TP'
                    break
            else:
                if df['high'].iloc[i] >= sl_price:
                    exit_idx = i
                    exit_price = sl_price
                    exit_reason = 'SL'
                    break
                if df['low'].iloc[i] <= tp_price:
                    exit_idx = i
                    exit_price = tp_price
                    exit_reason = 'TP'
                    break

        if exit_idx is None:
            exit_idx = min(fill_idx + 199, len(df) - 1)
            exit_price = df['close'].iloc[exit_idx]
            exit_reason = 'TIME'

        # Calculate P&L
        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        pnl_pct -= 0.10

        trades.append({
            'trade_id': trade_id,
            'signal_idx': signal_idx,
            'fill_idx': fill_idx,
            'exit_idx': exit_idx,
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

        trade_id += 1

    return trades

print("=" * 80)
print("OVERLAP PROFIT ANALYSIS - Where does the extra profit come from?")
print("=" * 80)

# Load data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n1. Running backtest with overlap tracking...")
signals = generate_signals(df)
trades = backtest_with_tracking(df, signals)

df_trades = pd.DataFrame(trades).sort_values('fill_idx')

print(f"   {len(trades)} trades total")
print(f"   Total P&L: {df_trades['pnl_pct'].sum():.2f}%")

# Identify overlaps
print(f"\n2. Identifying overlap patterns...")

overlaps = []
for i in range(len(df_trades)):
    for j in range(i + 1, len(df_trades)):
        trade_a = df_trades.iloc[i]
        trade_b = df_trades.iloc[j]

        # Check if trade_b starts before trade_a ends
        if trade_b['fill_idx'] <= trade_a['exit_idx']:
            overlap_type = None
            if trade_a['direction'] == trade_b['direction']:
                overlap_type = f"SAME_{trade_a['direction']}"  # e.g., "SAME_LONG"
            else:
                overlap_type = "OPPOSITE"  # LONG + SHORT

            overlaps.append({
                'trade_a_id': trade_a['trade_id'],
                'trade_b_id': trade_b['trade_id'],
                'overlap_type': overlap_type,
                'trade_a_pnl': trade_a['pnl_pct'],
                'trade_b_pnl': trade_b['pnl_pct'],
                'combined_pnl': trade_a['pnl_pct'] + trade_b['pnl_pct'],
                'trade_a_fill': trade_a['fill_idx'],
                'trade_b_fill': trade_b['fill_idx'],
                'overlap_bars': trade_a['exit_idx'] - trade_b['fill_idx'] + 1
            })

df_overlaps = pd.DataFrame(overlaps)

print(f"   {len(overlaps)} overlapping pairs found")

# Count overlap types
if len(df_overlaps) > 0:
    print(f"\n3. Overlap breakdown by type:")
    overlap_counts = df_overlaps['overlap_type'].value_counts()
    for overlap_type, count in overlap_counts.items():
        subset = df_overlaps[df_overlaps['overlap_type'] == overlap_type]
        total_pnl = subset['combined_pnl'].sum()
        avg_pnl = subset['combined_pnl'].mean()
        print(f"   {overlap_type}: {count} pairs, Total P&L: {total_pnl:.2f}%, Avg: {avg_pnl:.2f}%")

# Find duplicate trades (same entry bar, same direction)
print(f"\n4. Finding DUPLICATE trades (same signal, multiple fills)...")

duplicates = df_trades.groupby(['fill_idx', 'direction']).size()
duplicates = duplicates[duplicates > 1]

if len(duplicates) > 0:
    print(f"   {len(duplicates)} duplicate groups found!")

    total_duplicate_pnl = 0
    for (fill_idx, direction), count in duplicates.items():
        dup_trades = df_trades[(df_trades['fill_idx'] == fill_idx) & (df_trades['direction'] == direction)]
        dup_pnl = dup_trades['pnl_pct'].sum()
        total_duplicate_pnl += dup_pnl

        print(f"\n   Fill {fill_idx} {direction}: {count} identical trades")
        for _, trade in dup_trades.iterrows():
            print(f"      Trade {trade['trade_id']}: {trade['pnl_pct']:+.2f}% ({trade['exit_reason']})")
        print(f"      Combined P&L: {dup_pnl:+.2f}%")

    print(f"\n   💰 Total P&L from DUPLICATES: {total_duplicate_pnl:.2f}%")
else:
    print(f"   No duplicate trades found (each fill is unique)")

# Compare overlapping vs non-overlapping trades
print(f"\n5. Overlapping vs Non-overlapping trade performance...")

# Get all trade IDs that are in overlaps
overlapping_trade_ids = set()
if len(df_overlaps) > 0:
    overlapping_trade_ids = set(df_overlaps['trade_a_id'].tolist() + df_overlaps['trade_b_id'].tolist())

df_trades['is_overlapping'] = df_trades['trade_id'].isin(overlapping_trade_ids)

overlapping = df_trades[df_trades['is_overlapping']]
non_overlapping = df_trades[~df_trades['is_overlapping']]

print(f"\n   Overlapping trades: {len(overlapping)}")
print(f"      Total P&L: {overlapping['pnl_pct'].sum():.2f}%")
print(f"      Avg P&L: {overlapping['pnl_pct'].mean():.2f}%")
print(f"      Win Rate: {(overlapping['pnl_pct'] > 0).sum() / len(overlapping) * 100:.1f}%")

print(f"\n   Non-overlapping trades: {len(non_overlapping)}")
print(f"      Total P&L: {non_overlapping['pnl_pct'].sum():.2f}%")
print(f"      Avg P&L: {non_overlapping['pnl_pct'].mean():.2f}%")
print(f"      Win Rate: {(non_overlapping['pnl_pct'] > 0).sum() / len(non_overlapping) * 100:.1f}%")

# Identify which trades would be BLOCKED by live bot logic
print(f"\n6. Simulating live bot blocking...")

blocked_trades = []
allowed_trades = []
current_position_exit = -1

for _, trade in df_trades.iterrows():
    if trade['fill_idx'] <= current_position_exit:
        # Would be BLOCKED
        blocked_trades.append(trade)
    else:
        # Would be ALLOWED
        allowed_trades.append(trade)
        current_position_exit = trade['exit_idx']

df_blocked = pd.DataFrame(blocked_trades)
df_allowed = pd.DataFrame(allowed_trades)

print(f"\n   Allowed trades (live bot): {len(allowed_trades)}")
print(f"      Total P&L: {df_allowed['pnl_pct'].sum():.2f}%")

print(f"\n   Blocked trades (duplicates): {len(blocked_trades)}")
if len(blocked_trades) > 0:
    print(f"      Total P&L: {df_blocked['pnl_pct'].sum():.2f}%")
    print(f"      Avg P&L: {df_blocked['pnl_pct'].mean():.2f}%")
    print(f"      Win Rate: {(df_blocked['pnl_pct'] > 0).sum() / len(blocked_trades) * 100:.1f}%")

    print(f"\n   💰 BLOCKED TRADES CONTRIBUTE: {df_blocked['pnl_pct'].sum():.2f}% to total")
    print(f"   🎯 This is {df_blocked['pnl_pct'].sum() / df_trades['pnl_pct'].sum() * 100:.1f}% of total profit!")

# Direction breakdown for blocked trades
if len(blocked_trades) > 0:
    print(f"\n7. Blocked trades by direction:")
    blocked_longs = df_blocked[df_blocked['direction'] == 'LONG']
    blocked_shorts = df_blocked[df_blocked['direction'] == 'SHORT']

    print(f"   LONG: {len(blocked_longs)} trades, {blocked_longs['pnl_pct'].sum():.2f}% P&L")
    print(f"   SHORT: {len(blocked_shorts)} trades, {blocked_shorts['pnl_pct'].sum():.2f}% P&L")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"""
Total trades in backtest: {len(df_trades)}
Total P&L: {df_trades['pnl_pct'].sum():.2f}%

Allowed trades (live bot): {len(allowed_trades)}
Allowed P&L: {df_allowed['pnl_pct'].sum():.2f}%

Blocked trades (overlaps): {len(blocked_trades)}
Blocked P&L: {df_blocked['pnl_pct'].sum():.2f}% ({df_blocked['pnl_pct'].sum() / df_trades['pnl_pct'].sum() * 100:.1f}% of total)

The extra {df_blocked['pnl_pct'].sum():.2f}% comes from {len(blocked_trades)} trades that:
- Enter WHILE another trade is still open
- Would be BLOCKED in live bot (one trade at a time)
- Are counted in backtest but won't happen in reality
""")

print("=" * 80)
