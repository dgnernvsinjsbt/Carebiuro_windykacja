#!/usr/bin/env python3
"""
FARTCOIN Strategy - Direction Filter Research (60 DAYS)
Validation test to confirm LONG-only edge
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

def backtest(df, signals, direction_filter=None, strict_1_trade=False):
    """Backtest with configurable direction filter and overlap control"""
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
            'direction': direction,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

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
            'return_dd': 0
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
    win_rate = len(winners) / len(df) * 100
    tp_rate = (df['exit_reason'] == 'TP').sum() / len(df) * 100

    return {
        'config': config_name,
        'trades': len(df),
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd
    }

print("=" * 80)
print("FARTCOIN - DIRECTION FILTER RESEARCH (60 DAYS)")
print("=" * 80)

# Load 60-day data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\nData: {len(df):,} candles (60 days)")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

# Generate signals
signals = generate_signals(df)
long_signals = [s for s in signals if s[0] == 'LONG']
short_signals = [s for s in signals if s[0] == 'SHORT']

print(f"Signals: {len(signals)} total ({len(long_signals)} LONG, {len(short_signals)} SHORT)")

# Test key configurations
configs = [
    {'name': 'BASELINE (Both, Overlaps)', 'filter': None, 'strict': False},
    {'name': 'LONG-only (Overlaps)', 'filter': 'LONG', 'strict': False},
    {'name': 'SHORT-only (Overlaps)', 'filter': 'SHORT', 'strict': False},
    {'name': 'LONG-only (Strict 1 Trade)', 'filter': 'LONG', 'strict': True},
    {'name': 'Both (Strict 1 Trade)', 'filter': None, 'strict': True},
]

print(f"\n{'='*80}")
print("TESTING CONFIGURATIONS")
print("=" * 80)

results = []

for config in configs:
    print(f"\n{config['name']}:")
    trades = backtest(df, signals, config['filter'], config['strict'])
    metrics = calculate_metrics(trades, config['name'])
    results.append(metrics)

    print(f"  Trades: {metrics['trades']}, WR: {metrics['win_rate']:.1f}%, TP: {metrics['tp_rate']:.1f}%")
    print(f"  Return: {metrics['total_return']:+.2f}%, DD: {metrics['max_dd']:.2f}%, R/DD: {metrics['return_dd']:.2f}x")

# Compare with 30-day results
print("\n" + "=" * 80)
print("60-DAY vs 30-DAY COMPARISON")
print("=" * 80)

# Load 30-day results
df_30d = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_direction_filter_research.csv')

# Map configs for comparison
config_map = {
    'BASELINE (Both, Overlaps)': '1. BASELINE (Both, Overlaps OK)',
    'LONG-only (Overlaps)': '2. LONG-only (Overlaps OK)',
    'SHORT-only (Overlaps)': '3. SHORT-only (Overlaps OK)',
    'LONG-only (Strict 1 Trade)': '5. LONG-only (Strict 1 Trade)',
    'Both (Strict 1 Trade)': '4. Both (Strict 1 Trade)',
}

print(f"\n{'Config':<30} {'Period':<10} {'Trades':<10} {'Return':<12} {'R/DD':<10}")
print("-" * 80)

for result in results:
    config_name = result['config']
    old_name = config_map.get(config_name)

    # 60-day
    print(f"{config_name:<30} {'60d':<10} {result['trades']:<10} {result['total_return']:+11.2f}% {result['return_dd']:<10.2f}")

    # 30-day
    if old_name:
        r30 = df_30d[df_30d['config'] == old_name].iloc[0]
        print(f"{'':<30} {'30d':<10} {r30['trades']:<10} {r30['total_return']:+11.2f}% {r30['return_dd']:<10.2f}")

        # Change
        return_change = result['total_return'] - r30['total_return']
        rdd_change = result['return_dd'] - r30['return_dd']
        print(f"{'':<30} {'Change':<10} {result['trades'] - r30['trades']:<10} {return_change:+11.2f}% {rdd_change:<+10.2f}x")
    print()

# Summary
print("=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)

baseline_60 = [r for r in results if 'BASELINE' in r['config']][0]
long_overlap_60 = [r for r in results if 'LONG-only (Overlaps)' in r['config']][0]
long_strict_60 = [r for r in results if 'LONG-only (Strict 1 Trade)' in r['config']][0]

baseline_30 = df_30d[df_30d['config'] == '1. BASELINE (Both, Overlaps OK)'].iloc[0]
long_overlap_30 = df_30d[df_30d['config'] == '2. LONG-only (Overlaps OK)'].iloc[0]
long_strict_30 = df_30d[df_30d['config'] == '5. LONG-only (Strict 1 Trade)'].iloc[0]

print(f"""
LONG-only (Overlaps) - BEST PERFORMER:
  30d: {long_overlap_30['trades']} trades, {long_overlap_30['total_return']:+.2f}%, {long_overlap_30['return_dd']:.2f}x R/DD
  60d: {long_overlap_60['trades']} trades, {long_overlap_60['total_return']:+.2f}%, {long_overlap_60['return_dd']:.2f}x R/DD

  30d improvement vs baseline: {(long_overlap_30['return_dd'] / baseline_30['return_dd'] - 1) * 100:+.0f}%
  60d improvement vs baseline: {(long_overlap_60['return_dd'] / baseline_60['return_dd'] - 1) * 100:+.0f}%

LONG-only (Strict 1 Trade) - CONSERVATIVE:
  30d: {long_strict_30['trades']} trades, {long_strict_30['total_return']:+.2f}%, {long_strict_30['return_dd']:.2f}x R/DD
  60d: {long_strict_60['trades']} trades, {long_strict_60['total_return']:+.2f}%, {long_strict_60['return_dd']:.2f}x R/DD

  30d improvement vs baseline: {(long_strict_30['return_dd'] / baseline_30['return_dd'] - 1) * 100:+.0f}%
  60d improvement vs baseline: {(long_strict_60['return_dd'] / baseline_60['return_dd'] - 1) * 100:+.0f}%
""")

# Verdict
if long_overlap_60['return_dd'] > baseline_60['return_dd'] * 1.5:
    verdict = "✅ CONFIRMED"
    explanation = f"LONG-only consistently outperforms on both 30d and 60d data ({(long_overlap_60['return_dd'] / baseline_60['return_dd'] - 1) * 100:.0f}% better on 60d)."
elif long_strict_60['return_dd'] > baseline_60['return_dd']:
    verdict = "⚠️ CONSERVATIVE WORKS"
    explanation = "LONG-only (Strict 1 Trade) is consistently better than baseline. Safe improvement."
else:
    verdict = "❌ NOT CONFIRMED"
    explanation = "LONG-only doesn't hold up on 60-day data. 30-day result was a fluke."

print("=" * 80)
print(f"VERDICT: {verdict}")
print("=" * 80)
print(f"{explanation}\n")

if "CONFIRMED" in verdict or "CONSERVATIVE" in verdict:
    print("Recommended action: Implement LONG-only filter in live bot.")
else:
    print("Recommended action: Keep current strategy (both directions).")

print("=" * 80)
