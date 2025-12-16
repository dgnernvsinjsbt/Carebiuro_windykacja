#!/usr/bin/env python3
"""
Check if the FARTCOIN backtest allows overlapping positions
This would be a critical discrepancy vs live bot (which blocks duplicate signals)
"""

import pandas as pd
import numpy as np

# Run the backtest again and analyze trade overlaps
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

def backtest_with_overlap_check(df, signals):
    """Backtest that ALLOWS overlapping trades (original behavior)"""
    df = df.copy()
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])

    trades = []

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
            'signal_idx': signal_idx,
            'fill_idx': fill_idx,
            'exit_idx': exit_idx,
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

    return trades

def backtest_no_overlaps(df, signals):
    """Backtest that BLOCKS overlapping trades (live bot behavior)"""
    df = df.copy()
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])

    trades = []
    current_position = None  # Track if we have an open position

    for direction, signal_idx in signals:
        if signal_idx >= len(df) - 1:
            continue

        signal_price = df['close'].iloc[signal_idx]
        signal_atr = df['atr'].iloc[signal_idx]

        if pd.isna(signal_atr) or signal_atr == 0:
            continue

        # CHECK: Do we already have an open position or pending order?
        if current_position is not None:
            # Check if position is still open at this bar
            if signal_idx <= current_position['exit_idx']:
                # Position still open - BLOCK this signal
                continue
            else:
                # Position closed - we can take new signal
                current_position = None

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

        trade = {
            'signal_idx': signal_idx,
            'fill_idx': fill_idx,
            'exit_idx': exit_idx,
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        }

        trades.append(trade)
        current_position = trade  # Mark as having open position

    return trades

print("=" * 80)
print("BACKTEST OVERLAP ANALYSIS - Does backtest allow overlapping trades?")
print("=" * 80)

# Load data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n1. Generating signals...")
signals = generate_signals(df)
print(f"   {len(signals)} signals generated")

print(f"\n2. Running ORIGINAL backtest (allows overlaps)...")
trades_overlap = backtest_with_overlap_check(df, signals)
print(f"   {len(trades_overlap)} trades")

print(f"\n3. Running LIVE BOT backtest (blocks overlaps)...")
trades_no_overlap = backtest_no_overlaps(df, signals)
print(f"   {len(trades_no_overlap)} trades")

# Check for overlaps in original backtest
print(f"\n4. Checking for overlapping trades in ORIGINAL backtest...")

df_trades = pd.DataFrame(trades_overlap).sort_values('fill_idx')
overlaps = []

for i in range(len(df_trades)):
    for j in range(i + 1, len(df_trades)):
        trade_a = df_trades.iloc[i]
        trade_b = df_trades.iloc[j]

        # Check if trade_b starts before trade_a ends
        if trade_b['fill_idx'] <= trade_a['exit_idx']:
            overlaps.append({
                'trade_a_idx': i,
                'trade_b_idx': j,
                'trade_a_fill': trade_a['fill_idx'],
                'trade_a_exit': trade_a['exit_idx'],
                'trade_a_dir': trade_a['direction'],
                'trade_b_fill': trade_b['fill_idx'],
                'trade_b_exit': trade_b['exit_idx'],
                'trade_b_dir': trade_b['direction'],
            })

print(f"   Found {len(overlaps)} overlapping trade pairs")

if overlaps:
    print(f"\n   First 10 overlaps:")
    for overlap in overlaps[:10]:
        print(f"      Trade {overlap['trade_a_idx']} ({overlap['trade_a_dir']}): bars {overlap['trade_a_fill']}-{overlap['trade_a_exit']}")
        print(f"      Trade {overlap['trade_b_idx']} ({overlap['trade_b_dir']}): bars {overlap['trade_b_fill']}-{overlap['trade_b_exit']}")
        print(f"      → Overlap: {overlap['trade_b_fill']} to {overlap['trade_a_exit']} ({overlap['trade_a_exit'] - overlap['trade_b_fill'] + 1} bars)")
        print()

# Calculate metrics for both
def calc_metrics(trades):
    df = pd.DataFrame(trades)
    df['cumulative'] = df['pnl_pct'].cumsum()
    equity = 100 + df['cumulative']
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max * 100
    max_dd = drawdown.min()
    total_return = df['pnl_pct'].sum()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0
    win_rate = (df['pnl_pct'] > 0).sum() / len(df) * 100

    return {
        'trades': len(df),
        'win_rate': win_rate,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd
    }

metrics_overlap = calc_metrics(trades_overlap)
metrics_no_overlap = calc_metrics(trades_no_overlap)

print("=" * 80)
print("COMPARISON: Original Backtest vs Live Bot Behavior")
print("=" * 80)

print(f"\n{'Metric':<20} {'Original':<15} {'Live Bot':<15} {'Diff':<15}")
print("-" * 70)
print(f"{'Trades':<20} {metrics_overlap['trades']:<15} {metrics_no_overlap['trades']:<15} {metrics_no_overlap['trades'] - metrics_overlap['trades']:<15}")
print(f"{'Win Rate %':<20} {metrics_overlap['win_rate']:<15.1f} {metrics_no_overlap['win_rate']:<15.1f} {metrics_no_overlap['win_rate'] - metrics_overlap['win_rate']:<15.1f}")
print(f"{'Total Return %':<20} {metrics_overlap['total_return']:<15.2f} {metrics_no_overlap['total_return']:<15.2f} {metrics_no_overlap['total_return'] - metrics_overlap['total_return']:<15.2f}")
print(f"{'Max DD %':<20} {metrics_overlap['max_dd']:<15.2f} {metrics_no_overlap['max_dd']:<15.2f} {metrics_no_overlap['max_dd'] - metrics_overlap['max_dd']:<15.2f}")
print(f"{'Return/DD':<20} {metrics_overlap['return_dd']:<15.2f} {metrics_no_overlap['return_dd']:<15.2f} {metrics_no_overlap['return_dd'] - metrics_overlap['return_dd']:<15.2f}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

if len(overlaps) > 0:
    print(f"""
❌ DISCREPANCY FOUND!

The original backtest ALLOWS {len(overlaps)} overlapping trades.
This means multiple positions can be open simultaneously.

Live bot behavior: Only ONE pending order at a time (blocks duplicates)
Backtest behavior: Multiple positions can overlap

Results difference:
- Original: {metrics_overlap['trades']} trades, {metrics_overlap['total_return']:.2f}% return, {metrics_overlap['return_dd']:.2f}x R/DD
- Live Bot: {metrics_no_overlap['trades']} trades, {metrics_no_overlap['total_return']:.2f}% return, {metrics_no_overlap['return_dd']:.2f}x R/DD

The backtest may be overstating performance if overlaps contribute significantly.
""")
else:
    print(f"""
✅ NO DISCREPANCY

The original backtest does NOT have overlapping trades.
This matches live bot behavior (one trade at a time).

Both methods produce {metrics_overlap['trades']} trades with identical results.
""")

print("=" * 80)
