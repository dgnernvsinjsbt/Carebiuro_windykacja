"""
Scaling In/Out Strategy on 15m MELANIA
- Scale IN as RSI gets more extreme (average down/up)
- Scale OUT at multiple profit targets (lock gains)
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("SCALING IN/OUT STRATEGY - 15m MELANIA")
print("=" * 80)

# Download data
exchange = ccxt.bingx({'enableRateLimit': True})

end_date = datetime(2025, 12, 15, tzinfo=timezone.utc)
start_date = end_date - timedelta(days=90)  # 3 months

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

# 24h range (96 bars for 15m)
df['high_24h'] = df['high'].rolling(96).max()
df['low_24h'] = df['low'].rolling(96).min()
df['range_24h'] = ((df['high_24h'] - df['low_24h']) / df['low_24h']) * 100

print("Indicators calculated")

def backtest_scaling(df, config):
    """
    Scaling strategy:
    - Scale IN based on ATR moves against position (intelligent, volatility-adjusted)
    - Scale OUT at multiple TP levels
    """

    entry_rsi = config['entry_rsi']  # Initial RSI trigger (25 for LONG, 70 for SHORT)
    scale_in_atr_steps = config['scale_in_atr_steps']  # e.g., [0.5, 1.0, 1.5] ATR against position
    position_sizes = config['position_sizes']  # e.g., [0.3, 0.3, 0.4] (30%, 30%, 40% of total)
    tp_levels = config['tp_levels']  # e.g., [1.0, 2.0, 3.0, 4.0] in ATR multiples
    tp_sizes = config['tp_sizes']  # e.g., [0.25, 0.25, 0.25, 0.25] (25% each)
    sl_mult = config['sl_mult']
    total_risk_pct = config['total_risk_pct']
    min_range_24h = config['min_range_24h']

    trades = []
    equity = 100.0

    position = None  # Current position state

    i = 300  # Skip warmup
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            i += 1
            continue

        # Manage existing position
        if position is not None:
            # Check exits (SL, TPs, opposite signal)
            bar = row

            if position['direction'] == 'LONG':
                # Stop loss
                if bar['low'] <= position['sl_price']:
                    # Full exit on SL
                    pnl = position['total_size'] * ((position['sl_price'] - position['avg_entry']) / position['avg_entry'])
                    pnl -= position['total_size'] * 0.001  # Fees
                    equity += pnl

                    trades.append({
                        'exit_type': 'SL',
                        'pnl_dollars': pnl,
                        'equity': equity,
                        'scales_in': position['scales_in'],
                        'scales_out': position['scales_out']
                    })

                    position = None
                    i += 1
                    continue

                # Take profits
                for tp_idx, (tp_mult, tp_size_pct) in enumerate(zip(tp_levels, tp_sizes)):
                    if tp_idx >= len(position['tps_hit']) and bar['high'] >= position['tp_prices'][tp_idx]:
                        # Hit this TP
                        exit_size = position['total_size'] * tp_size_pct
                        pnl = exit_size * ((position['tp_prices'][tp_idx] - position['avg_entry']) / position['avg_entry'])
                        pnl -= exit_size * 0.001  # Fees
                        equity += pnl

                        position['tps_hit'].append(tp_idx)
                        position['scales_out'] += 1
                        position['remaining_size'] -= exit_size

                        # If all TPs hit, close position
                        if len(position['tps_hit']) == len(tp_levels):
                            trades.append({
                                'exit_type': 'TP_ALL',
                                'pnl_dollars': pnl,
                                'equity': equity,
                                'scales_in': position['scales_in'],
                                'scales_out': position['scales_out']
                            })
                            position = None
                            break

                # Opposite signal (RSI crosses to SHORT level - use 70)
                if i > 0 and position is not None:
                    prev_row = df.iloc[i-1]
                    opposite_rsi = 70  # Exit LONG when SHORT signal appears
                    if not pd.isna(prev_row['rsi']) and prev_row['rsi'] > opposite_rsi and row['rsi'] <= opposite_rsi:
                        # Exit remaining position
                        if position['remaining_size'] > 0:
                            pnl = position['remaining_size'] * ((bar['close'] - position['avg_entry']) / position['avg_entry'])
                            pnl -= position['remaining_size'] * 0.001  # Fees
                            equity += pnl

                            trades.append({
                                'exit_type': 'OPPOSITE',
                                'pnl_dollars': pnl,
                                'equity': equity,
                                'scales_in': position['scales_in'],
                                'scales_out': position['scales_out']
                            })

                        position = None

            elif position['direction'] == 'SHORT':
                # Stop loss
                if bar['high'] >= position['sl_price']:
                    pnl = position['total_size'] * ((position['avg_entry'] - position['sl_price']) / position['avg_entry'])
                    pnl -= position['total_size'] * 0.001
                    equity += pnl

                    trades.append({
                        'exit_type': 'SL',
                        'pnl_dollars': pnl,
                        'equity': equity,
                        'scales_in': position['scales_in'],
                        'scales_out': position['scales_out']
                    })

                    position = None
                    i += 1
                    continue

                # Take profits
                for tp_idx, (tp_mult, tp_size_pct) in enumerate(zip(tp_levels, tp_sizes)):
                    if tp_idx >= len(position['tps_hit']) and bar['low'] <= position['tp_prices'][tp_idx]:
                        exit_size = position['total_size'] * tp_size_pct
                        pnl = exit_size * ((position['avg_entry'] - position['tp_prices'][tp_idx]) / position['avg_entry'])
                        pnl -= exit_size * 0.001
                        equity += pnl

                        position['tps_hit'].append(tp_idx)
                        position['scales_out'] += 1
                        position['remaining_size'] -= exit_size

                        if len(position['tps_hit']) == len(tp_levels):
                            trades.append({
                                'exit_type': 'TP_ALL',
                                'pnl_dollars': pnl,
                                'equity': equity,
                                'scales_in': position['scales_in'],
                                'scales_out': position['scales_out']
                            })
                            position = None
                            break

                # Opposite signal (RSI crosses to LONG level)
                if i > 0 and position is not None:
                    prev_row = df.iloc[i-1]
                    opposite_rsi = 100 - entry_rsi  # If entry was 70, opposite is 30
                    if not pd.isna(prev_row['rsi']) and prev_row['rsi'] > (100 - opposite_rsi) and row['rsi'] <= (100 - opposite_rsi):
                        if position['remaining_size'] > 0:
                            pnl = position['remaining_size'] * ((position['avg_entry'] - bar['close']) / position['avg_entry'])
                            pnl -= position['remaining_size'] * 0.001
                            equity += pnl

                            trades.append({
                                'exit_type': 'OPPOSITE',
                                'pnl_dollars': pnl,
                                'equity': equity,
                                'scales_in': position['scales_in'],
                                'scales_out': position['scales_out']
                            })

                        position = None

        # Check for new position entries
        if position is None:
            # 24h range filter
            if pd.notna(row['range_24h']) and row['range_24h'] < min_range_24h:
                i += 1
                continue

            # LONG entry (RSI crosses above entry_rsi)
            if i > 0:
                prev_row = df.iloc[i-1]
                if not pd.isna(prev_row['rsi']) and prev_row['rsi'] < entry_rsi and row['rsi'] >= entry_rsi:
                    # Start LONG position
                    direction = 'LONG'

                    # Calculate position size based on total risk
                    risk_dollars = equity * (total_risk_pct / 100)

                    # First entry
                    entry_price = row['close']
                    entry_atr = row['atr']
                    sl_price = entry_price - (entry_atr * sl_mult)
                    sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100

                    # Total position size based on risk
                    total_position_size = risk_dollars / (sl_distance_pct / 100)

                    # First scale-in
                    first_size = total_position_size * position_sizes[0]

                    # Calculate TPs
                    tp_prices = [entry_price + (entry_atr * tp_mult) for tp_mult in tp_levels]

                    # Calculate scale-in prices (based on ATR from initial entry)
                    scale_in_prices = [entry_price - (entry_atr * step) for step in scale_in_atr_steps]

                    position = {
                        'direction': direction,
                        'initial_entry': entry_price,
                        'entry_atr': entry_atr,
                        'avg_entry': entry_price,
                        'sl_price': sl_price,
                        'tp_prices': tp_prices,
                        'scale_in_prices': scale_in_prices,
                        'total_size': first_size,
                        'remaining_size': first_size,
                        'scales_in': 1,
                        'scales_out': 0,
                        'tps_hit': [],
                        'max_scales': len(scale_in_atr_steps) + 1,
                        'sl_distance_pct': sl_distance_pct
                    }

                # SHORT entry (RSI crosses below entry_rsi)
                elif not pd.isna(prev_row['rsi']) and prev_row['rsi'] > entry_rsi and row['rsi'] <= entry_rsi:
                    direction = 'SHORT'

                    risk_dollars = equity * (total_risk_pct / 100)

                    entry_price = row['close']
                    entry_atr = row['atr']
                    sl_price = entry_price + (entry_atr * sl_mult)
                    sl_distance_pct = abs((sl_price - entry_price) / entry_price) * 100

                    total_position_size = risk_dollars / (sl_distance_pct / 100)
                    first_size = total_position_size * position_sizes[0]

                    tp_prices = [entry_price - (entry_atr * tp_mult) for tp_mult in tp_levels]

                    # Calculate scale-in prices (based on ATR from initial entry)
                    scale_in_prices = [entry_price + (entry_atr * step) for step in scale_in_atr_steps]

                    position = {
                        'direction': direction,
                        'initial_entry': entry_price,
                        'entry_atr': entry_atr,
                        'avg_entry': entry_price,
                        'sl_price': sl_price,
                        'tp_prices': tp_prices,
                        'scale_in_prices': scale_in_prices,
                        'total_size': first_size,
                        'remaining_size': first_size,
                        'scales_in': 1,
                        'scales_out': 0,
                        'tps_hit': [],
                        'max_scales': len(scale_in_atr_steps) + 1,
                        'sl_distance_pct': sl_distance_pct
                    }

        # Check for additional scale-ins (if position exists)
        if position is not None and position['scales_in'] < position['max_scales']:
            next_scale_idx = position['scales_in'] - 1  # -1 because we already did first scale

            if position['direction'] == 'LONG':
                # Scale in if price drops to next ATR level
                if row['low'] <= position['scale_in_prices'][next_scale_idx]:
                    # Add to position
                    add_size = (equity * (total_risk_pct / 100) / position['sl_distance_pct']) * position_sizes[position['scales_in']]

                    # Update average entry
                    total_cost = position['avg_entry'] * position['total_size'] + position['scale_in_prices'][next_scale_idx] * add_size
                    position['total_size'] += add_size
                    position['remaining_size'] += add_size
                    position['avg_entry'] = total_cost / position['total_size']
                    position['scales_in'] += 1

            elif position['direction'] == 'SHORT':
                # Scale in if price rises to next ATR level
                if row['high'] >= position['scale_in_prices'][next_scale_idx]:
                    add_size = (equity * (total_risk_pct / 100) / position['sl_distance_pct']) * position_sizes[position['scales_in']]

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

    avg_scales_in = df_t['scales_in'].mean()
    avg_scales_out = df_t['scales_out'].mean()

    return {
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'final_equity': equity,
        'avg_scales_in': avg_scales_in,
        'avg_scales_out': avg_scales_out
    }

# Test configurations
configs = [
    # Conservative ATR-based scaling
    {
        'name': 'Conservative ATR',
        'entry_rsi': 25,  # Initial RSI trigger (LONG: 25, SHORT: 70)
        'scale_in_atr_steps': [0.5, 1.0, 1.5],  # Scale in at 0.5, 1.0, 1.5 ATR against position
        'position_sizes': [0.3, 0.3, 0.4],  # 30%, 30%, 40% of total position
        'tp_levels': [1.0, 2.0, 3.0, 4.0],  # Take profit at 1x, 2x, 3x, 4x ATR
        'tp_sizes': [0.25, 0.25, 0.25, 0.25],  # 25% each
        'sl_mult': 2.0,
        'total_risk_pct': 15,
        'min_range_24h': 15.0
    },
    # Aggressive deep averaging
    {
        'name': 'Aggressive ATR',
        'entry_rsi': 25,
        'scale_in_atr_steps': [0.3, 0.7, 1.2],  # Tighter spacing
        'position_sizes': [0.2, 0.3, 0.5],  # Pyramid up
        'tp_levels': [0.5, 1.0, 2.0, 3.0],  # Quick TPs
        'tp_sizes': [0.25, 0.25, 0.25, 0.25],
        'sl_mult': 2.5,
        'total_risk_pct': 20,
        'min_range_24h': 15.0
    },
    # Wide spacing (patient)
    {
        'name': 'Patient ATR',
        'entry_rsi': 25,
        'scale_in_atr_steps': [1.0, 2.0],  # Only scale if REALLY moves against
        'position_sizes': [0.5, 0.5],  # Split evenly
        'tp_levels': [2.0, 4.0],  # Big targets
        'tp_sizes': [0.5, 0.5],
        'sl_mult': 3.0,
        'total_risk_pct': 15,
        'min_range_24h': 15.0
    },
    # Tight RSI entry
    {
        'name': 'Tight RSI 30',
        'entry_rsi': 30,  # Less extreme entry
        'scale_in_atr_steps': [0.5, 1.0, 1.5],
        'position_sizes': [0.3, 0.3, 0.4],
        'tp_levels': [1.0, 2.0, 3.0],
        'tp_sizes': [0.33, 0.33, 0.34],
        'sl_mult': 2.0,
        'total_risk_pct': 15,
        'min_range_24h': 15.0
    },
    # Ultra-aggressive 4-scale
    {
        'name': 'Ultra 4-scale',
        'entry_rsi': 25,
        'scale_in_atr_steps': [0.4, 0.8, 1.2, 1.6],  # 4 additional scales
        'position_sizes': [0.2, 0.2, 0.2, 0.2, 0.2],  # Equal sizing
        'tp_levels': [0.5, 1.0, 1.5, 2.0],
        'tp_sizes': [0.25, 0.25, 0.25, 0.25],
        'sl_mult': 2.0,
        'total_risk_pct': 20,
        'min_range_24h': 15.0
    },
]

print("\nRunning backtests...")
results = []

for config in configs:
    print(f"  Testing {config['name']}...")
    res = backtest_scaling(df, config)
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

    print("\n| # | Name                  | Return  | DD     | R/DD   | Trades | Win%  | Avg In | Avg Out | Final $ |")
    print("|---|-----------------------|---------|--------|--------|--------|-------|--------|---------|---------|")

    for i, (idx, row) in enumerate(results_df.iterrows(), 1):
        highlight = "🏆" if i == 1 else ""
        print(f"| {i} | {row['name']:21s} | {row['return']:+6.0f}% | {row['max_dd']:5.1f}% | {row['return_dd']:6.2f}x | "
              f"{row['trades']:3.0f} | {row['win_rate']:4.1f}% | {row['avg_scales_in']:6.2f} | {row['avg_scales_out']:7.2f} | "
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
    print(f"  Avg Scales In: {best['avg_scales_in']:.2f}")
    print(f"  Avg Scales Out: {best['avg_scales_out']:.2f}")
    print(f"  Final Equity: ${best['final_equity']:,.2f}")
    print("\n" + "=" * 80)
