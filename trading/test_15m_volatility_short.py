"""
15M VOLATILITY-FILTERED SHORT STRATEGY
Based on deep data analysis insights:
- SHORT only (59.9% vs 43.6% for LONG)
- RSI 70 sweet spot (72% win rate)
- ATR >3-4% filter (64-67% win rate)
- Range96 > 20% filter
- Scaling only in extreme setups
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("15M VOLATILITY SHORT STRATEGY - DATA-DRIVEN")
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
df['atr_pct'] = (df['atr'] / df['close']) * 100

df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100

print("Indicators calculated")

def backtest_short_only(df, config):
    """
    SHORT-only strategy with volatility filters
    """
    entry_rsi = config['entry_rsi']
    min_atr_pct = config['min_atr_pct']
    min_range_96 = config['min_range_96']
    sl_mult = config['sl_mult']
    tp_mult = config['tp_mult']
    risk_pct = config['risk_pct']

    # Scaling params (optional)
    use_scaling = config.get('use_scaling', False)
    scale_steps = config.get('scale_steps', [])
    scale_sizes = config.get('scale_sizes', [])

    trades = []
    equity = 100.0
    position = None

    i = 300
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['atr_pct']) or pd.isna(row['range_96']):
            i += 1
            continue

        # Manage position
        if position is not None:
            bar = row

            # Stop loss
            if bar['high'] >= position['sl_price']:
                pnl = position['total_size'] * ((position['avg_entry'] - position['sl_price']) / position['avg_entry'])
                pnl -= position['total_size'] * 0.001
                equity += pnl
                trades.append({'exit_type': 'SL', 'pnl': pnl, 'equity': equity, 'scales': position['scales']})
                position = None
                i += 1
                continue

            # Take profit
            for tp_idx, (tp_price, tp_size) in enumerate(zip(position['tp_prices'], position['tp_sizes'])):
                if tp_idx not in position['tps_hit'] and bar['low'] <= tp_price:
                    exit_size = position['initial_size'] * tp_size
                    pnl = exit_size * ((position['avg_entry'] - tp_price) / position['avg_entry'])
                    pnl -= exit_size * 0.001
                    equity += pnl

                    position['tps_hit'].append(tp_idx)
                    position['remaining_size'] -= exit_size

                    if len(position['tps_hit']) == len(position['tp_prices']):
                        trades.append({'exit_type': 'TP', 'pnl': pnl, 'equity': equity, 'scales': position['scales']})
                        position = None
                        break

            # Opposite signal (RSI crosses above 30)
            if position is not None and i > 0:
                prev_row = df.iloc[i-1]
                if not pd.isna(prev_row['rsi']) and prev_row['rsi'] < 30 and row['rsi'] >= 30:
                    if position['remaining_size'] > 0:
                        pnl = position['remaining_size'] * ((position['avg_entry'] - bar['close']) / position['avg_entry'])
                        pnl -= position['remaining_size'] * 0.001
                        equity += pnl
                        trades.append({'exit_type': 'OPPOSITE', 'pnl': pnl, 'equity': equity, 'scales': position['scales']})
                    position = None

        # New SHORT entries
        if position is None and i > 0:
            prev_row = df.iloc[i-1]

            # RSI cross
            if not pd.isna(prev_row['rsi']) and prev_row['rsi'] > entry_rsi and row['rsi'] <= entry_rsi:
                # Volatility filters
                if row['atr_pct'] < min_atr_pct:
                    i += 1
                    continue

                if row['range_96'] < min_range_96:
                    i += 1
                    continue

                # Enter SHORT
                entry_price = row['close']
                entry_atr = row['atr']
                sl_price = entry_price + (entry_atr * sl_mult)
                sl_distance_pct = abs((sl_price - entry_price) / entry_price) * 100

                risk_dollars = equity * (risk_pct / 100)
                total_size = risk_dollars / (sl_distance_pct / 100)
                first_size = total_size * (scale_sizes[0] if use_scaling else 1.0)

                # TPs
                tp_prices = [entry_price - (entry_atr * mult) for mult in tp_mult]
                tp_sizes_list = [1.0 / len(tp_mult)] * len(tp_mult) if not use_scaling else [0.33, 0.33, 0.34]

                # Scale-in prices
                scale_in_prices = []
                if use_scaling:
                    scale_in_prices = [entry_price + (entry_atr * step) for step in scale_steps]

                position = {
                    'initial_entry': entry_price,
                    'avg_entry': entry_price,
                    'entry_atr': entry_atr,
                    'sl_price': sl_price,
                    'tp_prices': tp_prices,
                    'tp_sizes': tp_sizes_list,
                    'scale_in_prices': scale_in_prices,
                    'initial_size': total_size,
                    'total_size': first_size,
                    'remaining_size': first_size,
                    'scales': 1,
                    'max_scales': len(scale_steps) + 1 if use_scaling else 1,
                    'tps_hit': [],
                    'sl_distance_pct': sl_distance_pct
                }

        # Scale-ins (if enabled)
        if use_scaling and position is not None and position['scales'] < position['max_scales']:
            next_idx = position['scales'] - 1

            if row['high'] >= position['scale_in_prices'][next_idx]:
                size_idx = min(position['scales'], len(scale_sizes) - 1)
                add_size = (equity * (risk_pct / 100) / position['sl_distance_pct']) * scale_sizes[size_idx]

                total_cost = position['avg_entry'] * position['total_size'] + position['scale_in_prices'][next_idx] * add_size
                position['total_size'] += add_size
                position['remaining_size'] += add_size
                position['avg_entry'] = total_cost / position['total_size']
                position['scales'] += 1

        i += 1

    if len(trades) == 0:
        return None

    df_t = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100
    equity_curve = [100.0] + df_t['equity'].tolist()
    eq = pd.Series(equity_curve)
    running_max = eq.expanding().max()
    max_dd = ((eq - running_max) / running_max * 100).min()
    win_rate = (df_t['pnl'] > 0).sum() / len(df_t) * 100

    exit_breakdown = df_t['exit_type'].value_counts().to_dict()
    avg_scales = df_t['scales'].mean()

    return {
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': total_return / abs(max_dd) if max_dd != 0 else 0,
        'trades': len(df_t),
        'win_rate': win_rate,
        'final_equity': equity,
        'avg_scales': avg_scales,
        'exits': exit_breakdown
    }

# Test configs based on data insights
configs = [
    # Pure RSI 70, high vol filter
    {
        'name': 'RSI70 ATR3%',
        'entry_rsi': 70,
        'min_atr_pct': 3.0,
        'min_range_96': 20.0,
        'sl_mult': 2.0,
        'tp_mult': [1.5, 3.0, 5.0],
        'risk_pct': 15,
        'use_scaling': False
    },
    # RSI 70, ultra-high vol
    {
        'name': 'RSI70 ATR4%',
        'entry_rsi': 70,
        'min_atr_pct': 4.0,
        'min_range_96': 20.0,
        'sl_mult': 2.0,
        'tp_mult': [2.0, 4.0, 6.0],
        'risk_pct': 15,
        'use_scaling': False
    },
    # RSI 65, high vol
    {
        'name': 'RSI65 ATR3%',
        'entry_rsi': 65,
        'min_atr_pct': 3.0,
        'min_range_96': 20.0,
        'sl_mult': 2.0,
        'tp_mult': [1.5, 3.0, 4.5],
        'risk_pct': 15,
        'use_scaling': False
    },
    # RSI 70 with scaling
    {
        'name': 'RSI70 ATR3% + Scaling',
        'entry_rsi': 70,
        'min_atr_pct': 3.0,
        'min_range_96': 20.0,
        'sl_mult': 2.5,
        'tp_mult': [1.0, 2.0, 3.0],
        'risk_pct': 15,
        'use_scaling': True,
        'scale_steps': [1.0, 2.0],  # Add at 1x and 2x ATR against
        'scale_sizes': [0.4, 0.3, 0.3]  # 40% first, 30% each scale
    },
    # Aggressive high risk
    {
        'name': 'RSI70 ATR3% 20%risk',
        'entry_rsi': 70,
        'min_atr_pct': 3.0,
        'min_range_96': 20.0,
        'sl_mult': 2.0,
        'tp_mult': [1.5, 3.0, 5.0],
        'risk_pct': 20,
        'use_scaling': False
    },
    # Conservative
    {
        'name': 'RSI70 ATR4% 12%risk',
        'entry_rsi': 70,
        'min_atr_pct': 4.0,
        'min_range_96': 25.0,
        'sl_mult': 2.5,
        'tp_mult': [2.0, 4.0, 6.0],
        'risk_pct': 12,
        'use_scaling': False
    },
]

print("\nRunning backtests...")
results = []

for config in configs:
    print(f"  Testing {config['name']}...")
    res = backtest_short_only(df, config)
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

    print("\n| # | Name                     | Return  | DD     | R/DD   | Trades | Win%  | Avg Scales | Final $ |")
    print("|---|--------------------------|---------|--------|--------|--------|-------|------------|---------|")

    for i, (idx, row) in enumerate(results_df.iterrows(), 1):
        highlight = "🏆" if i == 1 else ""
        print(f"| {i} | {row['name']:24s} | {row['return']:+6.0f}% | {row['max_dd']:5.1f}% | {row['return_dd']:6.2f}x | "
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
    print(f"  Avg Scales: {best['avg_scales']:.2f}")
    print(f"  Exit Types: {best['exits']}")
    print(f"  Final Equity: ${best['final_equity']:,.2f}")
    print("\n" + "=" * 80)
