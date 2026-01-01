#!/usr/bin/env python3
"""
FARTCOIN - FILTER OPTIMIZATION

Analyze trades and test various filters to improve Return/DD ratio
Optimal config: SL=3.5%, TP=10%
"""

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('fartcoin_6months_bingx_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Filter to December only
df_dec = df[df['timestamp'].dt.month == 12].copy().reset_index(drop=True)

# Calculate indicators
# ATR
high_low = df_dec['high'] - df_dec['low']
high_close = abs(df_dec['high'] - df_dec['close'].shift())
low_close = abs(df_dec['low'] - df_dec['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df_dec['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
df_dec['atr_pct'] = (df_dec['atr'] / df_dec['close']) * 100

# Moving averages
df_dec['ma_20'] = df_dec['close'].rolling(window=20).mean()
df_dec['ma_50'] = df_dec['close'].rolling(window=50).mean()

# RSI
period = 14
delta = df_dec['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
rs = avg_gain / avg_loss
df_dec['rsi'] = 100 - (100 / (1 + rs))

# Hour of day
df_dec['hour'] = df_dec['timestamp'].dt.hour

print("="*140)
print("FARTCOIN - COMPREHENSIVE FILTER OPTIMIZATION")
print("="*140)
print()

# Optimal parameters
ENTRY_OFFSET_PCT = 2.0
SL_PCT = 3.5
TP_PCT = 10.0
INITIAL_EQUITY = 100.0

def run_backtest(filter_func=None, filter_name="No Filter"):
    """Run backtest with optional filter function"""
    equity = INITIAL_EQUITY
    peak_equity = INITIAL_EQUITY
    max_dd = 0.0
    trades = []
    skipped = 0

    current_day = None
    daily_high = 0
    daily_high_bar = 0
    in_position = False
    tp_hit_today = False
    position = None
    prev_day_return = 0

    for i in range(50, len(df_dec)):  # Start at 50 for indicators
        row = df_dec.iloc[i]
        timestamp = row['timestamp']
        day = timestamp.date()

        # Check if new day (reset)
        if day != current_day:
            # Calculate previous day return
            if current_day is not None:
                prev_day_data = df_dec[df_dec['timestamp'].dt.date == current_day]
                if len(prev_day_data) > 0:
                    day_open = prev_day_data.iloc[0]['open']
                    day_close = prev_day_data.iloc[-1]['close']
                    prev_day_return = ((day_close - day_open) / day_open) * 100

            current_day = day
            daily_high = row['high']
            daily_high_bar = i
            tp_hit_today = False

            if in_position:
                exit_price = row['open']
                pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
                pnl_dollar = position['position_size'] * (pnl_pct / 100)
                equity += pnl_dollar
                trades.append({'result': 'DAY_CLOSE', 'pnl_pct': pnl_pct, 'pnl_dollar': pnl_dollar})
                in_position = False
                position = None

        # Update daily high
        if row['high'] > daily_high:
            daily_high = row['high']
            daily_high_bar = i

        # If not in position and haven't hit TP today, check for entry
        if not in_position and not tp_hit_today:
            trigger_price = daily_high * (1 - ENTRY_OFFSET_PCT / 100)

            if row['low'] <= trigger_price:
                # Prepare entry context for filter
                entry_context = {
                    'price': trigger_price,
                    'daily_high': daily_high,
                    'atr_pct': row['atr_pct'],
                    'ma_20': row['ma_20'],
                    'ma_50': row['ma_50'],
                    'rsi': row['rsi'],
                    'hour': row['hour'],
                    'bars_since_high': i - daily_high_bar,
                    'prev_day_return': prev_day_return,
                    'close': row['close'],
                    'open': row['open']
                }

                # Apply filter if provided
                if filter_func and not filter_func(entry_context):
                    skipped += 1
                    continue

                # ENTRY
                entry_price = trigger_price
                sl_price = entry_price * (1 + SL_PCT / 100)
                tp_price = entry_price * (1 - TP_PCT / 100)
                position_size = (equity * 5.0) / SL_PCT

                if position_size > 0:
                    in_position = True
                    position = {
                        'entry_price': entry_price,
                        'sl_price': sl_price,
                        'tp_price': tp_price,
                        'position_size': position_size,
                        'direction': 'SHORT',
                        'entry_context': entry_context
                    }

        # If in position, check for exit
        if in_position:
            hit_sl = False
            hit_tp = False
            exit_price = None

            if row['high'] >= position['sl_price']:
                hit_sl = True
                exit_price = position['sl_price']
            elif row['low'] <= position['tp_price']:
                hit_tp = True
                exit_price = position['tp_price']

            if hit_sl or hit_tp:
                pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price']) * 100
                pnl_dollar = position['position_size'] * (pnl_pct / 100)
                equity += pnl_dollar

                if equity > peak_equity:
                    peak_equity = equity
                dd = ((peak_equity - equity) / peak_equity) * 100
                if dd > max_dd:
                    max_dd = dd

                trades.append({
                    'result': 'TP' if hit_tp else 'SL',
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'entry_context': position['entry_context']
                })

                in_position = False
                position = None

                if hit_tp:
                    tp_hit_today = True

    # Calculate results
    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        total_return = ((equity - INITIAL_EQUITY) / INITIAL_EQUITY) * 100
        win_rate = (trades_df['result'] == 'TP').sum() / len(trades_df) * 100
        return_dd = total_return / max_dd if max_dd > 0 else 0

        return {
            'name': filter_name,
            'total_return': total_return,
            'max_dd': max_dd,
            'return_dd': return_dd,
            'total_trades': len(trades_df),
            'win_rate': win_rate,
            'skipped': skipped,
            'final_equity': equity
        }
    return None

# Define filters to test
filters = [
    {
        'name': 'No Filter (baseline)',
        'func': None
    },
    {
        'name': 'ATR > 1.0% (avoid low vol)',
        'func': lambda ctx: ctx['atr_pct'] > 1.0
    },
    {
        'name': 'ATR 0.8-2.5% (sweet spot)',
        'func': lambda ctx: 0.8 < ctx['atr_pct'] < 2.5
    },
    {
        'name': 'Price < MA20 (downtrend)',
        'func': lambda ctx: ctx['price'] < ctx['ma_20']
    },
    {
        'name': 'Price < MA50 (strong downtrend)',
        'func': lambda ctx: ctx['price'] < ctx['ma_50']
    },
    {
        'name': 'RSI > 60 before drop',
        'func': lambda ctx: ctx['rsi'] > 60
    },
    {
        'name': 'RSI > 70 before drop',
        'func': lambda ctx: ctx['rsi'] > 70
    },
    {
        'name': 'Avoid hours 0-8 (low vol)',
        'func': lambda ctx: ctx['hour'] >= 8
    },
    {
        'name': 'Avoid hours 0-6 (low vol)',
        'func': lambda ctx: ctx['hour'] >= 6
    },
    {
        'name': 'Trade only hours 12-20 (high vol)',
        'func': lambda ctx: 12 <= ctx['hour'] <= 20
    },
    {
        'name': 'Wait 4+ bars after high',
        'func': lambda ctx: ctx['bars_since_high'] >= 4
    },
    {
        'name': 'Wait 8+ bars after high',
        'func': lambda ctx: ctx['bars_since_high'] >= 8
    },
    {
        'name': 'Prev day not bullish (< +2%)',
        'func': lambda ctx: ctx['prev_day_return'] < 2.0
    },
    {
        'name': 'Prev day bearish (< 0%)',
        'func': lambda ctx: ctx['prev_day_return'] < 0
    },
    {
        'name': 'COMBO: ATR>1 + Price<MA20',
        'func': lambda ctx: ctx['atr_pct'] > 1.0 and ctx['price'] < ctx['ma_20']
    },
    {
        'name': 'COMBO: ATR>1 + RSI>60',
        'func': lambda ctx: ctx['atr_pct'] > 1.0 and ctx['rsi'] > 60
    },
    {
        'name': 'COMBO: Price<MA20 + RSI>60',
        'func': lambda ctx: ctx['price'] < ctx['ma_20'] and ctx['rsi'] > 60
    },
    {
        'name': 'COMBO: Hours 8+ + ATR>1',
        'func': lambda ctx: ctx['hour'] >= 8 and ctx['atr_pct'] > 1.0
    },
]

# Run all filters
print("Testing filters...")
print()

results = []
for filter_def in filters:
    result = run_backtest(filter_def['func'], filter_def['name'])
    if result:
        results.append(result)

results_df = pd.DataFrame(results)

# Display results
print("="*140)
print("FILTER OPTIMIZATION RESULTS")
print("="*140)
print()
print(f"{'Filter':<40} {'Return':<12} {'Max DD':<12} {'R/DD':<10} {'Trades':<10} {'WR %':<10} {'Skipped':<10}")
print("-"*140)

for _, row in results_df.iterrows():
    status = "🔥" if row['return_dd'] > 2.0 else ("✅" if row['return_dd'] > 1.5 else ("💚" if row['return_dd'] > 1.0 else "❌"))
    print(f"{row['name']:<40} {row['total_return']:>+10.2f}%  {row['max_dd']:>10.2f}%  {row['return_dd']:>8.2f}x  {row['total_trades']:<10.0f} {row['win_rate']:>8.1f}%  {row['skipped']:<10.0f}  {status}")

print()
print("="*140)
print()

# Find best filters
baseline = results_df[results_df['name'] == 'No Filter (baseline)'].iloc[0]
better_filters = results_df[results_df['return_dd'] > baseline['return_dd']].sort_values('return_dd', ascending=False)

if len(better_filters) > 0:
    print("🏆 FILTERS THAT IMPROVE R/DD:")
    print()
    for i, row in enumerate(better_filters.head(5).itertuples(), 1):
        improvement = row.return_dd - baseline['return_dd']
        print(f"{i}. {row.name}")
        print(f"   R/DD: {row.return_dd:.2f}x (baseline: {baseline['return_dd']:.2f}x, +{improvement:.2f}x improvement)")
        print(f"   Return: {row.total_return:+.2f}% vs {baseline['total_return']:+.2f}%")
        print(f"   Max DD: {row.max_dd:.2f}% vs {baseline['max_dd']:.2f}%")
        print(f"   Trades: {row.total_trades:.0f} vs {baseline['total_trades']:.0f} (skipped {row.skipped:.0f})")
        print(f"   Win Rate: {row.win_rate:.1f}% vs {baseline['win_rate']:.1f}%")
        print()
else:
    print("❌ NO FILTERS IMPROVED R/DD")
    print()
    print("Best alternative filters (by return):")
    top_return = results_df.nlargest(3, 'total_return')
    for i, row in enumerate(top_return.itertuples(), 1):
        print(f"{i}. {row.name}: {row.total_return:+.2f}% return, {row.return_dd:.2f}x R/DD")

print("="*140)
