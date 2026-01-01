#!/usr/bin/env python3
"""
FARTCOIN Strategy - Direction Filter Research

Test configurations:
1. Current (both directions, allows overlaps) - BASELINE
2. LONG-only + strict 1 trade max
3. SHORT-only + strict 1 trade max
4. Both directions + strict 1 trade max
5. LONG-only + allows overlaps
6. SHORT-only + allows overlaps

Goal: Find if direction filtering + 1 trade max can be profitable
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
    """Generate ALL signals (LONG + SHORT)"""
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

def backtest(df, signals, direction_filter=None, strict_1_trade=False, config_name="TEST"):
    """
    Backtest with configurable direction filter and overlap control

    Args:
        direction_filter: None (both), 'LONG', or 'SHORT'
        strict_1_trade: If True, only 1 trade open at a time (no overlaps)
    """
    df = df.copy()
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'])

    # Filter signals by direction if specified
    if direction_filter:
        signals = [(d, idx) for d, idx in signals if d == direction_filter]

    trades = []
    current_position_exit = -1 if strict_1_trade else None

    for direction, signal_idx in signals:
        if signal_idx >= len(df) - 1:
            continue

        # Check if we're in strict 1-trade mode and position still open
        if strict_1_trade and signal_idx <= current_position_exit:
            continue  # Skip signal - position still open

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
            'direction': direction,
            'fill_idx': fill_idx,
            'exit_idx': exit_idx,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

        # Update current position exit for strict mode
        if strict_1_trade:
            current_position_exit = exit_idx

    return trades

def calculate_metrics(trades, config_name):
    """Calculate performance metrics"""
    if not trades:
        return {
            'config': config_name,
            'trades': 0,
            'win_rate': 0,
            'tp_rate': 0,
            'total_return': 0,
            'max_dd': 0,
            'return_dd': 0,
            'avg_winner': 0,
            'avg_loser': 0
        }

    df = pd.DataFrame(trades)
    df['cumulative'] = df['pnl_pct'].cumsum()
    equity = 100 + df['cumulative']
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max * 100
    max_dd = drawdown.min()

    total_return = df['pnl_pct'].sum()
    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = df[df['pnl_pct'] > 0]
    losers = df[df['pnl_pct'] <= 0]

    win_rate = len(winners) / len(df) * 100
    tp_rate = (df['exit_reason'] == 'TP').sum() / len(df) * 100

    return {
        'config': config_name,
        'trades': len(df),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'avg_winner': winners['pnl_pct'].mean() if len(winners) > 0 else 0,
        'avg_loser': losers['pnl_pct'].mean() if len(losers) > 0 else 0
    }

print("=" * 80)
print("FARTCOIN - DIRECTION FILTER RESEARCH")
print("=" * 80)

# Load data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_30d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\nData: {len(df):,} candles (30 days)")

# Generate signals
signals = generate_signals(df)
long_signals = [s for s in signals if s[0] == 'LONG']
short_signals = [s for s in signals if s[0] == 'SHORT']

print(f"Signals: {len(signals)} total ({len(long_signals)} LONG, {len(short_signals)} SHORT)")

# Test configurations
configs = [
    # Baseline
    {'name': '1. BASELINE (Both, Overlaps OK)', 'filter': None, 'strict': False},

    # Direction filters with overlaps
    {'name': '2. LONG-only (Overlaps OK)', 'filter': 'LONG', 'strict': False},
    {'name': '3. SHORT-only (Overlaps OK)', 'filter': 'SHORT', 'strict': False},

    # Strict 1 trade max
    {'name': '4. Both (Strict 1 Trade)', 'filter': None, 'strict': True},
    {'name': '5. LONG-only (Strict 1 Trade)', 'filter': 'LONG', 'strict': True},
    {'name': '6. SHORT-only (Strict 1 Trade)', 'filter': 'SHORT', 'strict': True},
]

print(f"\n{'='*80}")
print("TESTING CONFIGURATIONS")
print("=" * 80)

results = []

for config in configs:
    print(f"\nTesting: {config['name']}")
    trades = backtest(
        df,
        signals,
        direction_filter=config['filter'],
        strict_1_trade=config['strict'],
        config_name=config['name']
    )

    metrics = calculate_metrics(trades, config['name'])
    results.append(metrics)

    print(f"  Trades: {metrics['trades']}")
    print(f"  Win Rate: {metrics['win_rate']:.1f}%")
    print(f"  TP Rate: {metrics['tp_rate']:.1f}%")
    print(f"  Return: {metrics['total_return']:+.2f}%")
    print(f"  Max DD: {metrics['max_dd']:.2f}%")
    print(f"  Return/DD: {metrics['return_dd']:.2f}x")

# Summary table
print("\n" + "=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)

df_results = pd.DataFrame(results)
df_results = df_results.sort_values('return_dd', ascending=False)

print("\nSorted by Return/DD:")
print(df_results[['config', 'trades', 'win_rate', 'tp_rate', 'total_return', 'max_dd', 'return_dd']].to_string(index=False))

# Find best configurations
print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

baseline = results[0]
best_overall = df_results.iloc[0]

strict_results = df_results[df_results['config'].str.contains('Strict')]
best_strict = strict_results.iloc[0] if not strict_results.empty else None

print(f"""
BASELINE (Current Backtest):
  {baseline['trades']} trades, {baseline['total_return']:+.2f}% return, {baseline['return_dd']:.2f}x R/DD

BEST OVERALL:
  {best_overall['config']}
  {best_overall['trades']} trades, {best_overall['total_return']:+.2f}% return, {best_overall['return_dd']:.2f}x R/DD
  Improvement: {(best_overall['return_dd'] / baseline['return_dd'] - 1) * 100:+.1f}%
""")

if best_strict is not None:
    print(f"""BEST STRICT 1-TRADE:
  {best_strict['config']}
  {best_strict['trades']} trades, {best_strict['total_return']:+.2f}% return, {best_strict['return_dd']:.2f}x R/DD
  vs Baseline: {(best_strict['return_dd'] / baseline['return_dd'] - 1) * 100:+.1f}%
""")

# Direction analysis
long_only_overlap = df_results[df_results['config'].str.contains('LONG-only.*Overlaps')].iloc[0]
short_only_overlap = df_results[df_results['config'].str.contains('SHORT-only.*Overlaps')].iloc[0]
long_only_strict = df_results[df_results['config'].str.contains('LONG-only.*Strict')].iloc[0]
short_only_strict = df_results[df_results['config'].str.contains('SHORT-only.*Strict')].iloc[0]

print(f"""
DIRECTION COMPARISON:

With Overlaps:
  LONG-only:  {long_only_overlap['trades']} trades, {long_only_overlap['total_return']:+.2f}% ({long_only_overlap['return_dd']:.2f}x R/DD)
  SHORT-only: {short_only_overlap['trades']} trades, {short_only_overlap['total_return']:+.2f}% ({short_only_overlap['return_dd']:.2f}x R/DD)
  Combined:   {baseline['trades']} trades, {baseline['total_return']:+.2f}% ({baseline['return_dd']:.2f}x R/DD)

  LONG contributes: {long_only_overlap['total_return'] / baseline['total_return'] * 100:.1f}% of profit
  SHORT contributes: {short_only_overlap['total_return'] / baseline['total_return'] * 100:.1f}% of profit

Strict 1-Trade:
  LONG-only:  {long_only_strict['trades']} trades, {long_only_strict['total_return']:+.2f}% ({long_only_strict['return_dd']:.2f}x R/DD)
  SHORT-only: {short_only_strict['trades']} trades, {short_only_strict['total_return']:+.2f}% ({short_only_strict['return_dd']:.2f}x R/DD)
""")

print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

# Determine best approach
if best_overall['return_dd'] > baseline['return_dd'] * 1.2:
    print(f"""
✅ STRONG IMPROVEMENT FOUND!

{best_overall['config']} shows {(best_overall['return_dd'] / baseline['return_dd'] - 1) * 100:.0f}% better Return/DD.

Recommended next steps:
1. Test on different time periods (7d, 14d, 60d)
2. Optimize parameters for this direction filter
3. Consider implementing in live bot
""")
elif best_strict and best_strict['return_dd'] > 0 and best_strict['total_return'] > 20:
    print(f"""
⚠️ STRICT 1-TRADE IS VIABLE

{best_strict['config']}:
- {best_strict['trades']} trades (fewer = less risk)
- {best_strict['total_return']:+.2f}% return (still profitable)
- {best_strict['return_dd']:.2f}x R/DD (reasonable)

This is a more conservative approach that matches how humans trade.
Trade-off: Lower absolute returns but simpler execution.
""")
else:
    print(f"""
❌ NO SIGNIFICANT IMPROVEMENT

Direction filters and strict 1-trade don't improve performance.
Current approach (both directions, overlaps allowed) remains best.

The multiple-position strategy is working as designed.
""")

print("=" * 80)

# Save results
df_results.to_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_direction_filter_research.csv', index=False)
print("\n✅ Results saved to: trading/results/fartcoin_direction_filter_research.csv")
