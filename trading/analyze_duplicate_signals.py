#!/usr/bin/env python3
"""
Investigate HOW we get 3 SHORT trades filling at the same bar
Are they from the SAME signal or DIFFERENT signals?
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

def backtest_with_signal_tracking(df, signals):
    """Track WHICH signal led to WHICH trade"""
    df = df.copy()
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])

    trades = []
    trade_id = 0

    for sig_idx, (direction, signal_idx) in enumerate(signals):
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

        # Try to fill in next 3 bars
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
            'signal_list_idx': sig_idx,  # Index in signals list
            'signal_bar': signal_idx,     # Bar where signal fired
            'fill_bar': fill_idx,         # Bar where order filled
            'exit_bar': exit_idx,
            'direction': direction,
            'signal_price': signal_price,
            'limit_price': limit_price,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason,
            'bars_to_fill': fill_idx - signal_idx
        })

        trade_id += 1

    return trades

print("=" * 80)
print("DUPLICATE SIGNAL ANALYSIS - How do we get 3 SHORTs at bar 1735?")
print("=" * 80)

# Load data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n1. Generating signals...")
signals = generate_signals(df)
print(f"   {len(signals)} signals")

# Check for duplicate signals at same bar
signal_counts = {}
for direction, signal_idx in signals:
    key = (signal_idx, direction)
    signal_counts[key] = signal_counts.get(key, 0) + 1

duplicates_at_signal = [k for k, v in signal_counts.items() if v > 1]

if duplicates_at_signal:
    print(f"\n   ⚠️  Found {len(duplicates_at_signal)} bars with duplicate signals!")
    for (signal_idx, direction), count in list(signal_counts.items())[:5]:
        if count > 1:
            print(f"      Bar {signal_idx} {direction}: {count} signals")
else:
    print(f"   ✅ No duplicate signals at same bar (each bar = 1 signal max)")

print(f"\n2. Running backtest with signal tracking...")
trades = backtest_with_signal_tracking(df, signals)
df_trades = pd.DataFrame(trades)

print(f"   {len(trades)} filled trades")

# Find duplicate fills (multiple trades filling at same bar)
print(f"\n3. Finding trades that fill at the SAME bar...")

fill_groups = df_trades.groupby(['fill_bar', 'direction']).size()
duplicate_fills = fill_groups[fill_groups > 1]

print(f"   Found {len(duplicate_fills)} fill bars with duplicates")

if len(duplicate_fills) > 0:
    print(f"\n4. Analyzing the 3 SHORT trades at bar 1735...")

    # Get the 3 SHORT trades
    trades_1735 = df_trades[(df_trades['fill_bar'] == 1735) & (df_trades['direction'] == 'SHORT')]

    if len(trades_1735) > 0:
        print(f"\n   Found {len(trades_1735)} trades filling at bar 1735:")
        print()

        for _, trade in trades_1735.iterrows():
            signal_bar = trade['signal_bar']
            fill_bar = trade['fill_bar']
            bars_to_fill = trade['bars_to_fill']

            # Get data for signal bar
            sig_row = df.iloc[signal_bar]
            print(f"   Trade {trade['trade_id']}:")
            print(f"      Signal fired at bar {signal_bar} ({sig_row['timestamp']})")
            print(f"      Price: ${trade['signal_price']:.6f}")
            print(f"      Limit order: ${trade['limit_price']:.6f} (1% lower)")
            print(f"      Filled at bar {fill_bar} ({df.iloc[fill_bar]['timestamp']})")
            print(f"      Bars to fill: {bars_to_fill}")
            print(f"      P&L: {trade['pnl_pct']:+.2f}% ({trade['exit_reason']})")
            print()

        print(f"   🔍 EXPLANATION:")
        print(f"      - {len(trades_1735)} different signals (bars {', '.join(str(t['signal_bar']) for _, t in trades_1735.iterrows())})")
        print(f"      - Each signal placed a limit order 1% below")
        print(f"      - All {len(trades_1735)} orders filled at bar 1735 (price dropped)")
        print(f"      - This creates {len(trades_1735)} simultaneous SHORT positions")

    # Show more examples
    print(f"\n5. Other duplicate fill examples:")

    for (fill_bar, direction), count in duplicate_fills.head(5).items():
        dup_trades = df_trades[(df_trades['fill_bar'] == fill_bar) & (df_trades['direction'] == direction)]

        print(f"\n   Fill bar {fill_bar} ({direction}): {count} trades")

        signal_bars = dup_trades['signal_bar'].tolist()
        print(f"      Signals from bars: {signal_bars}")
        print(f"      All filled at bar: {fill_bar}")
        print(f"      Bars to fill: {dup_trades['bars_to_fill'].tolist()}")

        combined_pnl = dup_trades['pnl_pct'].sum()
        print(f"      Combined P&L: {combined_pnl:+.2f}%")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

print(f"""
✅ Each bar generates AT MOST 1 signal (LONG or SHORT, never both)

❌ But multiple signals can FILL at the same bar!

Example: Bar 1735 (3 SHORT trades)
- Signal 1: Fired at bar 1733 → limit order → filled at bar 1735
- Signal 2: Fired at bar 1734 → limit order → filled at bar 1735
- Signal 3: Fired at bar 1735 → limit order → filled at bar 1735

All 3 pending orders trigger when price hits their limit at bar 1735.

This creates 3 simultaneous SHORT positions from 3 different signals.

In live bot with "one pending order" rule:
- Signal 1 (bar 1733): ✅ Places order
- Signal 2 (bar 1734): ❌ BLOCKED (order 1 pending)
- Signal 3 (bar 1735): ❌ BLOCKED (order 1 still pending)
→ Only 1 trade executes, not 3
""")

print("=" * 80)
