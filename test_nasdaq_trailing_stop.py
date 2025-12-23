#!/usr/bin/env python3
"""
Test TRAILING STOP on NASDAQ LONG reversal
Based on analysis: 94% of losers went +0.38% positive before hitting SL
"""
import pandas as pd
import numpy as np

print("="*90)
print("NASDAQ LONG REVERSAL - TRAILING STOP OPTIMIZATION")
print("="*90)

# Load NASDAQ data
df = pd.read_csv('trading/nasdaq_3months_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n📊 Data: {len(df)} candles")

# Calculate RSI
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Calculate ATR
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

def find_swing_high(df, idx, lookback):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['high'].max()

def find_swing_low(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['low'].min()

def backtest_trailing_stop(df, rsi_trigger, limit_offset, tp_pct,
                           activation_pct, trail_pct,
                           lookback=5, max_wait=20, max_sl_pct=5.0):
    """
    Backtest LONG reversal with trailing stop

    activation_pct: Move SL to breakeven when profit reaches this % (e.g., 0.3%)
    trail_pct: Trail this % below highest high after activation (e.g., 0.5%)
    """
    equity = 100.0
    trades = []

    armed = False
    signal_idx = None
    swing_high = None
    limit_pending = False
    limit_placed_idx = None
    swing_low_for_sl = None

    for i in range(lookback, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            continue

        # ARM
        if row['rsi'] < rsi_trigger:
            armed = True
            signal_idx = i
            swing_high = find_swing_high(df, i, lookback)
            limit_pending = False

        # Break
        if armed and swing_high is not None and not limit_pending:
            if row['high'] > swing_high:
                atr = row['atr']
                limit_price = swing_high - (atr * limit_offset)
                swing_low_for_sl = find_swing_low(df, signal_idx, i)
                limit_pending = True
                limit_placed_idx = i
                armed = False

        # Fill
        if limit_pending:
            if i - limit_placed_idx > max_wait:
                limit_pending = False
                continue

            if row['low'] <= limit_price:
                entry_price = limit_price
                initial_sl_price = swing_low_for_sl
                tp_price = entry_price * (1 + tp_pct / 100)

                sl_dist_pct = ((entry_price - initial_sl_price) / entry_price) * 100

                if sl_dist_pct <= 0 or sl_dist_pct > max_sl_pct:
                    limit_pending = False
                    continue

                size = (equity * 0.05) / (sl_dist_pct / 100)

                # Trailing stop variables
                current_sl = initial_sl_price
                highest_high = entry_price
                trailing_active = False

                # Find exit with trailing stop logic
                hit_sl = False
                hit_tp = False
                exit_bar = None
                exit_price = None

                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]

                    # Update highest high
                    if future_row['high'] > highest_high:
                        highest_high = future_row['high']

                    # Check if we should activate trailing stop
                    unrealized_profit_pct = ((highest_high - entry_price) / entry_price) * 100

                    if unrealized_profit_pct >= activation_pct:
                        trailing_active = True
                        # Update trailing stop
                        trail_price = highest_high * (1 - trail_pct / 100)
                        if trail_price > current_sl:
                            current_sl = trail_price

                    # Check SL hit
                    if future_row['low'] <= current_sl:
                        hit_sl = True
                        exit_bar = j
                        exit_price = current_sl
                        break

                    # Check TP hit
                    if future_row['high'] >= tp_price:
                        hit_tp = True
                        exit_bar = j
                        exit_price = tp_price
                        break

                if hit_sl:
                    pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                    exit_reason = 'TRAIL_SL' if trailing_active else 'INITIAL_SL'
                elif hit_tp:
                    pnl_pct = tp_pct
                    exit_reason = 'TP'
                    exit_price = tp_price
                else:
                    continue

                pnl_dollar = size * (pnl_pct / 100) - size * 0.001
                equity += pnl_dollar

                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'initial_sl': initial_sl_price,
                    'final_sl': current_sl,
                    'highest_high': highest_high,
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'exit_reason': exit_reason,
                    'trailing_active': trailing_active,
                    'max_unrealized_pct': ((highest_high - entry_price) / entry_price) * 100
                })

                limit_pending = False

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    total_return = ((equity - 100) / 100) * 100

    # Max DD
    equity_curve = [100.0]
    for pnl in trades_df['pnl_dollar']:
        equity_curve.append(equity_curve[-1] + pnl)

    eq_series = pd.Series(equity_curve)
    running_max = eq_series.expanding().max()
    drawdown = (eq_series - running_max) / running_max * 100
    max_dd = drawdown.min()

    return_dd = total_return / abs(max_dd) if max_dd != 0 else 0

    winners = trades_df[trades_df['pnl_dollar'] > 0]
    win_rate = (len(winners) / len(trades_df)) * 100

    tp_count = len(trades_df[trades_df['exit_reason'] == 'TP'])
    trail_sl_count = len(trades_df[trades_df['exit_reason'] == 'TRAIL_SL'])
    initial_sl_count = len(trades_df[trades_df['exit_reason'] == 'INITIAL_SL'])

    return {
        'activation_pct': activation_pct,
        'trail_pct': trail_pct,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'final_equity': equity,
        'tp_count': tp_count,
        'trail_sl_count': trail_sl_count,
        'initial_sl_count': initial_sl_count,
        'avg_max_unrealized': trades_df['max_unrealized_pct'].mean(),
        'trades_df': trades_df
    }

# Best config from previous tests
rsi_trigger = 28
limit_offset = 0.20
tp_pct = 2.0

print(f"\n🔄 Testing trailing stop configurations...")
print(f"   Base: RSI<{rsi_trigger}, Offset:{limit_offset}, TP:{tp_pct}%")
print()

# Test grid
configs = []

# Activation levels: 0.2%, 0.3%, 0.4%, 0.5%
# Trail distances: 0.3%, 0.5%, 0.75%, 1.0%
for activation in [0.2, 0.3, 0.4, 0.5]:
    for trail in [0.3, 0.5, 0.75, 1.0]:
        configs.append({'activation': activation, 'trail': trail})

# Also test baseline (no trailing stop)
print(f"Testing {len(configs)} trailing stop configs + baseline...")

results = []

# Add baseline first (use very high activation so trailing never activates)
baseline = backtest_trailing_stop(
    df,
    rsi_trigger=rsi_trigger,
    limit_offset=limit_offset,
    tp_pct=tp_pct,
    activation_pct=999.0,  # Never activate
    trail_pct=0.5
)
baseline['activation_pct'] = 0.0  # Mark as baseline
baseline['trail_pct'] = 0.0
baseline['config_name'] = 'Baseline (no trailing)'
results.append(baseline)

# Test trailing configs
for config in configs:
    result = backtest_trailing_stop(
        df,
        rsi_trigger=rsi_trigger,
        limit_offset=limit_offset,
        tp_pct=tp_pct,
        activation_pct=config['activation'],
        trail_pct=config['trail']
    )

    if result:
        result['config_name'] = f"Act:{config['activation']:.1f}% Trail:{config['trail']:.1f}%"
        results.append(result)

print(f"✅ Completed {len(results)} backtests")

# Sort by R/DD
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

# Display top 20
print("\n" + "="*90)
print("🏆 TOP 20 TRAILING STOP CONFIGS (by Return/DD)")
print("="*90)
print()

print(f"{'Rank':>4} | {'Config':<25} | {'R/DD':>7} | {'Return':>8} | {'DD':>8} | {'Win%':>6} | {'TP/Trail/Init':>15}")
print("-" * 90)

for idx, (i, row) in enumerate(results_df.head(20).iterrows()):
    emoji = "🏆" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx+1:2d}."

    exits = f"{int(row['tp_count'])}/{int(row['trail_sl_count'])}/{int(row['initial_sl_count'])}"

    print(f"{emoji:>4} | {row['config_name']:<25} | {row['return_dd']:>6.2f}x | {row['total_return']:>7.1f}% | {row['max_dd']:>7.2f}% | {row['win_rate']:>5.1f}% | {exits:>15}")

# Best vs baseline
best = results_df.iloc[0]
baseline_row = results_df[results_df['config_name'] == 'Baseline (no trailing)'].iloc[0]

print("\n" + "="*90)
print("🎯 BEST TRAILING STOP CONFIGURATION")
print("="*90)
print()
print(f"Config: {best['config_name']}")
print(f"  Activation: +{best['activation_pct']:.1f}% profit")
print(f"  Trail Distance: {best['trail_pct']:.1f}% below highest high")
print()
print(f"Performance:")
print(f"  Return/DD: {best['return_dd']:.2f}x")
print(f"  Total Return: {best['total_return']:+.1f}%")
print(f"  Max Drawdown: {best['max_dd']:.2f}%")
print(f"  Win Rate: {best['win_rate']:.1f}%")
print(f"  Final Equity: ${best['final_equity']:.2f}")
print()
print(f"Exit Breakdown:")
print(f"  TP: {int(best['tp_count'])}")
print(f"  Trailing SL: {int(best['trail_sl_count'])}")
print(f"  Initial SL: {int(best['initial_sl_count'])}")
print(f"  Avg Max Unrealized: {best['avg_max_unrealized']:.2f}%")

print("\n" + "="*90)
print("📊 BEST vs BASELINE COMPARISON")
print("="*90)
print()

print(f"{'Metric':<25} | {'Baseline':<15} | {'Best Trailing':<15} | {'Improvement':<15}")
print("-" * 75)
print(f"{'Return/DD':<25} | {baseline_row['return_dd']:<15.2f}x | {best['return_dd']:<15.2f}x | {best['return_dd'] - baseline_row['return_dd']:+.2f}x ({((best['return_dd'] - baseline_row['return_dd']) / baseline_row['return_dd'] * 100):+.1f}%)")
print(f"{'Total Return':<25} | {baseline_row['total_return']:<15.1f}% | {best['total_return']:<15.1f}% | {best['total_return'] - baseline_row['total_return']:+.1f}pp")
print(f"{'Max Drawdown':<25} | {baseline_row['max_dd']:<15.2f}% | {best['max_dd']:<15.2f}% | {best['max_dd'] - baseline_row['max_dd']:+.2f}pp")
print(f"{'Win Rate':<25} | {baseline_row['win_rate']:<15.1f}% | {best['win_rate']:<15.1f}% | {best['win_rate'] - baseline_row['win_rate']:+.1f}pp")
print(f"{'Final Equity':<25} | ${baseline_row['final_equity']:<14.2f} | ${best['final_equity']:<14.2f} | ${best['final_equity'] - baseline_row['final_equity']:+.2f}")

print()
print(f"Exit Changes:")
print(f"  TP: {int(baseline_row['tp_count'])} → {int(best['tp_count'])} ({int(best['tp_count']) - int(baseline_row['tp_count']):+d})")
print(f"  Initial SL: {int(baseline_row['initial_sl_count'])} → {int(best['initial_sl_count'])} ({int(best['initial_sl_count']) - int(baseline_row['initial_sl_count']):+d})")
print(f"  NEW Trailing SL: 0 → {int(best['trail_sl_count'])}")

# Analyze trail SL trades
if best['trail_sl_count'] > 0:
    best_trades = best['trades_df']
    trail_trades = best_trades[best_trades['exit_reason'] == 'TRAIL_SL']

    print("\n" + "="*90)
    print(f"🔍 TRAILING STOP ANALYSIS ({int(best['trail_sl_count'])} trades)")
    print("="*90)
    print()
    print(f"Avg Entry → Exit: {trail_trades['pnl_pct'].mean():+.2f}%")
    print(f"Avg Max Unrealized: {trail_trades['max_unrealized_pct'].mean():+.2f}%")
    print(f"Avg Profit Given Back: {(trail_trades['max_unrealized_pct'] - trail_trades['pnl_pct']).mean():.2f}%")
    print()

    trail_winners = trail_trades[trail_trades['pnl_pct'] > 0]
    trail_losers = trail_trades[trail_trades['pnl_pct'] < 0]
    trail_be = trail_trades[abs(trail_trades['pnl_pct']) < 0.05]

    print(f"Trailing SL Outcomes:")
    print(f"  Winners: {len(trail_winners)} (avg: {trail_winners['pnl_pct'].mean():+.2f}%)" if len(trail_winners) > 0 else "  Winners: 0")
    print(f"  Breakeven: {len(trail_be)} (avg: {trail_be['pnl_pct'].mean():+.2f}%)" if len(trail_be) > 0 else "  Breakeven: 0")
    print(f"  Small Losers: {len(trail_losers)} (avg: {trail_losers['pnl_pct'].mean():+.2f}%)" if len(trail_losers) > 0 else "  Small Losers: 0")
    print()
    print(f"💡 These would have been INITIAL SL hits at avg -{baseline_row['max_dd']/(baseline_row['trades']-baseline_row['tp_count']):.2f}% each")
    print(f"   Trailing stop saved avg {abs(baseline_row['max_dd']/(baseline_row['trades']-baseline_row['tp_count'])) - abs(trail_trades['pnl_pct'].mean()):.2f}% per trade!")

# Save best config trades
best['trades_df'].to_csv('nasdaq_trailing_stop_best_trades.csv', index=False)
results_df.to_csv('nasdaq_trailing_stop_all_results.csv', index=False)

print(f"\n💾 Best trades saved to: nasdaq_trailing_stop_best_trades.csv")
print(f"💾 All results saved to: nasdaq_trailing_stop_all_results.csv")
print("="*90)
