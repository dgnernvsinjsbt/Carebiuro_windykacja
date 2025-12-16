"""
ADAPTIVE SCALING STRATEGY - 15m MELANIA
Intelligent position sizing based on volatility and risk management

Key Features:
1. Entry RSI adapts to volatility (high vol = more conservative)
2. Scaling steps adapt to ATR (high vol = wider steps)
3. Goal shifts from profit to breakeven as position averages down
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("ADAPTIVE VOLATILITY SCALING - 15m MELANIA")
print("=" * 80)

# Download data
exchange = ccxt.bingx({'enableRateLimit': True})

end_date = datetime(2025, 12, 15, tzinfo=timezone.utc)
start_date = end_date - timedelta(days=90)

start_ts = int(start_date.timestamp() * 1000)
end_ts = int(end_date.timestamp() * 1000)

print(f"\nDownloading MELANIA 15m data...")

all_candles = []
current_ts = start_ts

while current_ts < end_ts:
    try:
        candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
        if not candles:
            break
        all_candles.extend(candles)
        current_ts = candles[-1][0] + (15 * 60 * 1000)
        time.sleep(0.5)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)
        continue

df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
df = df[(df['timestamp'] >= start_date.replace(tzinfo=None)) & (df['timestamp'] <= end_date.replace(tzinfo=None))]
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Downloaded {len(df)} bars")

# Calculate indicators
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()

# ATR ratio (current vs 24h average) - volatility indicator
df['atr_24h_avg'] = df['atr'].rolling(96).mean()  # 24h on 15m = 96 bars
df['atr_ratio'] = df['atr'] / df['atr_24h_avg']

# 24h range filter
df['high_24h'] = df['high'].rolling(96).max()
df['low_24h'] = df['low'].rolling(96).min()
df['range_24h'] = ((df['high_24h'] - df['low_24h']) / df['low_24h']) * 100

print("Indicators calculated")

def backtest_adaptive(df, config):
    """
    Adaptive scaling based on volatility:
    - High ATR → conservative entry, wider steps
    - Low ATR → aggressive entry, tighter steps
    - Goal: breakeven as position averages down
    """

    base_entry_rsi = config['base_entry_rsi']  # Base RSI for LONG (e.g., 25)
    base_scale_steps = config['base_scale_steps']  # Base ATR steps (e.g., [0.5, 1.0, 1.5])
    position_sizes = config['position_sizes']  # Position allocation per scale
    sl_mult = config['sl_mult']
    total_risk_pct = config['total_risk_pct']
    min_range_24h = config['min_range_24h']

    # Volatility thresholds
    high_vol_threshold = config.get('high_vol_threshold', 1.5)  # ATR ratio > 1.5 = high vol
    low_vol_threshold = config.get('low_vol_threshold', 0.8)   # ATR ratio < 0.8 = low vol

    trades = []
    equity = 100.0
    position = None

    i = 300  # Skip warmup
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['atr_ratio']):
            i += 1
            continue

        # Manage existing position
        if position is not None:
            bar = row

            if position['direction'] == 'LONG':
                # Stop loss
                if bar['low'] <= position['sl_price']:
                    pnl = position['total_size'] * ((position['sl_price'] - position['avg_entry']) / position['avg_entry'])
                    pnl -= position['total_size'] * 0.001
                    equity += pnl
                    trades.append({'exit_type': 'SL', 'pnl_dollars': pnl, 'equity': equity, 'scales_in': position['scales_in']})
                    position = None
                    i += 1
                    continue

                # Breakeven exit (after 2+ scales, aim for BE)
                if position['scales_in'] >= 2 and bar['high'] >= position['avg_entry']:
                    pnl = position['remaining_size'] * 0  # Breakeven
                    pnl -= position['remaining_size'] * 0.001  # Just fees
                    equity += pnl
                    trades.append({'exit_type': 'BE', 'pnl_dollars': pnl, 'equity': equity, 'scales_in': position['scales_in']})
                    position = None
                    i += 1
                    continue

                # Take profits (for first scale only - aim for profit)
                if position['scales_in'] == 1:
                    for tp_idx, (tp_price, tp_size_pct) in enumerate(zip(position['tp_prices'], position['tp_sizes'])):
                        if tp_idx not in position['tps_hit'] and bar['high'] >= tp_price:
                            exit_size = position['total_size'] * tp_size_pct
                            pnl = exit_size * ((tp_price - position['avg_entry']) / position['avg_entry'])
                            pnl -= exit_size * 0.001
                            equity += pnl

                            position['tps_hit'].append(tp_idx)
                            position['remaining_size'] -= exit_size

                            if len(position['tps_hit']) == len(position['tp_prices']):
                                trades.append({'exit_type': 'TP_ALL', 'pnl_dollars': pnl, 'equity': equity, 'scales_in': position['scales_in']})
                                position = None
                                break

                # Opposite signal
                if position is not None and i > 0:
                    prev_row = df.iloc[i-1]
                    if not pd.isna(prev_row['rsi']) and prev_row['rsi'] > 70 and row['rsi'] <= 70:
                        if position['remaining_size'] > 0:
                            pnl = position['remaining_size'] * ((bar['close'] - position['avg_entry']) / position['avg_entry'])
                            pnl -= position['remaining_size'] * 0.001
                            equity += pnl
                            trades.append({'exit_type': 'OPPOSITE', 'pnl_dollars': pnl, 'equity': equity, 'scales_in': position['scales_in']})
                        position = None

            elif position['direction'] == 'SHORT':
                # Stop loss
                if bar['high'] >= position['sl_price']:
                    pnl = position['total_size'] * ((position['avg_entry'] - position['sl_price']) / position['avg_entry'])
                    pnl -= position['total_size'] * 0.001
                    equity += pnl
                    trades.append({'exit_type': 'SL', 'pnl_dollars': pnl, 'equity': equity, 'scales_in': position['scales_in']})
                    position = None
                    i += 1
                    continue

                # Breakeven exit
                if position['scales_in'] >= 2 and bar['low'] <= position['avg_entry']:
                    pnl = position['remaining_size'] * 0
                    pnl -= position['remaining_size'] * 0.001
                    equity += pnl
                    trades.append({'exit_type': 'BE', 'pnl_dollars': pnl, 'equity': equity, 'scales_in': position['scales_in']})
                    position = None
                    i += 1
                    continue

                # Take profits (first scale only)
                if position['scales_in'] == 1:
                    for tp_idx, (tp_price, tp_size_pct) in enumerate(zip(position['tp_prices'], position['tp_sizes'])):
                        if tp_idx not in position['tps_hit'] and bar['low'] <= tp_price:
                            exit_size = position['total_size'] * tp_size_pct
                            pnl = exit_size * ((position['avg_entry'] - tp_price) / position['avg_entry'])
                            pnl -= exit_size * 0.001
                            equity += pnl

                            position['tps_hit'].append(tp_idx)
                            position['remaining_size'] -= exit_size

                            if len(position['tps_hit']) == len(position['tp_prices']):
                                trades.append({'exit_type': 'TP_ALL', 'pnl_dollars': pnl, 'equity': equity, 'scales_in': position['scales_in']})
                                position = None
                                break

                # Opposite signal
                if position is not None and i > 0:
                    prev_row = df.iloc[i-1]
                    if not pd.isna(prev_row['rsi']) and prev_row['rsi'] < 30 and row['rsi'] >= 30:
                        if position['remaining_size'] > 0:
                            pnl = position['remaining_size'] * ((position['avg_entry'] - bar['close']) / position['avg_entry'])
                            pnl -= position['remaining_size'] * 0.001
                            equity += pnl
                            trades.append({'exit_type': 'OPPOSITE', 'pnl_dollars': pnl, 'equity': equity, 'scales_in': position['scales_in']})
                        position = None

        # Check for new entries
        if position is None:
            # 24h range filter
            if pd.notna(row['range_24h']) and row['range_24h'] < min_range_24h:
                i += 1
                continue

            # Adaptive RSI based on volatility
            atr_ratio = row['atr_ratio']

            if atr_ratio > high_vol_threshold:
                # High volatility - more conservative
                entry_rsi_long = base_entry_rsi - 5  # 25 → 20 (more oversold)
                entry_rsi_short = (100 - base_entry_rsi) + 5  # 75 → 80 (more overbought)
                scale_multiplier = 1.5  # Wider steps
            elif atr_ratio < low_vol_threshold:
                # Low volatility - more aggressive
                entry_rsi_long = base_entry_rsi + 5  # 25 → 30 (less oversold)
                entry_rsi_short = (100 - base_entry_rsi) - 5  # 75 → 70
                scale_multiplier = 0.7  # Tighter steps
            else:
                # Normal volatility
                entry_rsi_long = base_entry_rsi
                entry_rsi_short = 100 - base_entry_rsi
                scale_multiplier = 1.0

            # Adaptive scale steps
            adapted_steps = [step * scale_multiplier for step in base_scale_steps]

            # LONG entry
            if i > 0:
                prev_row = df.iloc[i-1]
                if not pd.isna(prev_row['rsi']) and prev_row['rsi'] < entry_rsi_long and row['rsi'] >= entry_rsi_long:
                    direction = 'LONG'
                    risk_dollars = equity * (total_risk_pct / 100)

                    entry_price = row['close']
                    entry_atr = row['atr']
                    sl_price = entry_price - (entry_atr * sl_mult)
                    sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100

                    total_position_size = risk_dollars / (sl_distance_pct / 100)
                    first_size = total_position_size * position_sizes[0]

                    # TP prices (only for first scale)
                    tp_prices = [entry_price + (entry_atr * mult) for mult in [1.0, 2.0, 3.0]]
                    tp_sizes = [0.33, 0.33, 0.34]

                    # Scale-in prices
                    scale_in_prices = [entry_price - (entry_atr * step) for step in adapted_steps]

                    position = {
                        'direction': direction,
                        'initial_entry': entry_price,
                        'entry_atr': entry_atr,
                        'avg_entry': entry_price,
                        'sl_price': sl_price,
                        'tp_prices': tp_prices,
                        'tp_sizes': tp_sizes,
                        'scale_in_prices': scale_in_prices,
                        'total_size': first_size,
                        'remaining_size': first_size,
                        'scales_in': 1,
                        'tps_hit': [],
                        'max_scales': len(adapted_steps) + 1,
                        'sl_distance_pct': sl_distance_pct
                    }

                # SHORT entry
                elif not pd.isna(prev_row['rsi']) and prev_row['rsi'] > entry_rsi_short and row['rsi'] <= entry_rsi_short:
                    direction = 'SHORT'
                    risk_dollars = equity * (total_risk_pct / 100)

                    entry_price = row['close']
                    entry_atr = row['atr']
                    sl_price = entry_price + (entry_atr * sl_mult)
                    sl_distance_pct = abs((sl_price - entry_price) / entry_price) * 100

                    total_position_size = risk_dollars / (sl_distance_pct / 100)
                    first_size = total_position_size * position_sizes[0]

                    tp_prices = [entry_price - (entry_atr * mult) for mult in [1.0, 2.0, 3.0]]
                    tp_sizes = [0.33, 0.33, 0.34]

                    scale_in_prices = [entry_price + (entry_atr * step) for step in adapted_steps]

                    position = {
                        'direction': direction,
                        'initial_entry': entry_price,
                        'entry_atr': entry_atr,
                        'avg_entry': entry_price,
                        'sl_price': sl_price,
                        'tp_prices': tp_prices,
                        'tp_sizes': tp_sizes,
                        'scale_in_prices': scale_in_prices,
                        'total_size': first_size,
                        'remaining_size': first_size,
                        'scales_in': 1,
                        'tps_hit': [],
                        'max_scales': len(adapted_steps) + 1,
                        'sl_distance_pct': sl_distance_pct
                    }

        # Additional scale-ins
        if position is not None and position['scales_in'] < position['max_scales']:
            next_scale_idx = position['scales_in'] - 1

            if position['direction'] == 'LONG':
                if row['low'] <= position['scale_in_prices'][next_scale_idx]:
                    # Use position_sizes index, cap at max
                    size_idx = min(position['scales_in'], len(position_sizes) - 1)
                    add_size = (equity * (total_risk_pct / 100) / position['sl_distance_pct']) * position_sizes[size_idx]

                    total_cost = position['avg_entry'] * position['total_size'] + position['scale_in_prices'][next_scale_idx] * add_size
                    position['total_size'] += add_size
                    position['remaining_size'] += add_size
                    position['avg_entry'] = total_cost / position['total_size']
                    position['scales_in'] += 1

            elif position['direction'] == 'SHORT':
                if row['high'] >= position['scale_in_prices'][next_scale_idx]:
                    # Use position_sizes index, cap at max
                    size_idx = min(position['scales_in'], len(position_sizes) - 1)
                    add_size = (equity * (total_risk_pct / 100) / position['sl_distance_pct']) * position_sizes[size_idx]

                    total_cost = position['avg_entry'] * position['total_size'] + position['scale_in_prices'][next_scale_idx] * add_size
                    position['total_size'] += add_size
                    position['remaining_size'] += add_size
                    position['avg_entry'] = total_cost / position['total_size']
                    position['scales_in'] += 1

        i += 1

    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100
    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    max_dd = ((eq - running_max) / running_max * 100).min()
    win_rate = (df_t['pnl_dollars'] > 0).sum() / len(df_t) * 100
    avg_scales = df_t['scales_in'].mean()

    # Exit type breakdown
    exit_types = df_t['exit_type'].value_counts().to_dict()

    return {
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'final_equity': equity,
        'avg_scales': avg_scales,
        'exits': exit_types
    }

# Test configs
configs = [
    {
        'name': 'Balanced Adaptive',
        'base_entry_rsi': 25,
        'base_scale_steps': [0.5, 1.0, 1.5],
        'position_sizes': [0.3, 0.3, 0.4],
        'sl_mult': 2.0,
        'total_risk_pct': 15,
        'min_range_24h': 15.0,
        'high_vol_threshold': 1.5,
        'low_vol_threshold': 0.8
    },
    {
        'name': 'Conservative Adaptive',
        'base_entry_rsi': 20,  # More extreme
        'base_scale_steps': [1.0, 2.0],  # Wider spacing
        'position_sizes': [0.5, 0.5],
        'sl_mult': 2.5,
        'total_risk_pct': 12,
        'min_range_24h': 15.0,
        'high_vol_threshold': 1.3,
        'low_vol_threshold': 0.9
    },
    {
        'name': 'Aggressive Adaptive',
        'base_entry_rsi': 30,  # Less extreme
        'base_scale_steps': [0.3, 0.7, 1.0, 1.5],  # More scales, tighter
        'position_sizes': [0.25, 0.25, 0.25, 0.25],
        'sl_mult': 2.0,
        'total_risk_pct': 18,
        'min_range_24h': 15.0,
        'high_vol_threshold': 1.6,
        'low_vol_threshold': 0.7
    },
]

print("\nRunning adaptive backtests...")
results = []

for config in configs:
    print(f"  Testing {config['name']}...")
    res = backtest_adaptive(df, config)
    if res:
        res['name'] = config['name']
        results.append(res)

if len(results) == 0:
    print("\nNo results!")
else:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('return_dd', ascending=False)

    print("\n" + "=" * 80)
    print("RESULTS (by R/DD):")
    print("=" * 80)

    print("\n| # | Name                  | Return  | DD     | R/DD   | Trades | Win%  | Avg Scales | Final $ |")
    print("|---|-----------------------|---------|--------|--------|--------|-------|------------|---------|")

    for i, (idx, row) in enumerate(results_df.iterrows(), 1):
        highlight = "🏆" if i == 1 else ""
        print(f"| {i} | {row['name']:21s} | {row['return']:+6.0f}% | {row['max_dd']:5.1f}% | {row['return_dd']:6.2f}x | "
              f"{row['trades']:3.0f} | {row['win_rate']:4.1f}% | {row['avg_scales']:10.2f} | "
              f"${row['final_equity']:6.0f} | {highlight}")

    # Best
    best = results_df.iloc[0]
    print("\n" + "=" * 80)
    print("🏆 WINNER:")
    print("=" * 80)
    print(f"\n  {best['name']}")
    print(f"  Return: {best['return']:+.2f}%")
    print(f"  Max DD: {best['max_dd']:.2f}%")
    print(f"  R/DD: {best['return_dd']:.2f}x")
    print(f"  Trades: {best['trades']:.0f}")
    print(f"  Win Rate: {best['win_rate']:.1f}%")
    print(f"  Avg Scales In: {best['avg_scales']:.2f}")
    print(f"  Exit Types: {best['exits']}")
    print(f"  Final Equity: ${best['final_equity']:,.2f}")
    print("\n" + "=" * 80)
