#!/usr/bin/env python3
"""
Test S&P 500 LONG reversal with trailing stop
S&P 500 is 0.75x NASDAQ volatility - less volatile
"""
import pandas as pd
import numpy as np

print("="*90)
print("S&P 500 LONG REVERSAL - WITH TRAILING STOP")
print("="*90)

# Load S&P 500 data
df = pd.read_csv('trading/sp500_3months_15m.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\n📊 Data Loaded:")
print(f"   Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"   Candles: {len(df)}")
print(f"   Avg Price: ${df['close'].mean():,.2f}")

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

                # Find exit with trailing stop
                hit_sl = False
                hit_tp = False
                exit_bar = None
                exit_price = None

                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]

                    # Update highest high
                    if future_row['high'] > highest_high:
                        highest_high = future_row['high']

                    # Check activation
                    unrealized_profit_pct = ((highest_high - entry_price) / entry_price) * 100

                    if unrealized_profit_pct >= activation_pct:
                        trailing_active = True
                        trail_price = highest_high * (1 - trail_pct / 100)
                        if trail_price > current_sl:
                            current_sl = trail_price

                    # Check SL
                    if future_row['low'] <= current_sl:
                        hit_sl = True
                        exit_bar = j
                        exit_price = current_sl
                        break

                    # Check TP
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
        'rsi_trigger': rsi_trigger,
        'limit_offset': limit_offset,
        'tp_pct': tp_pct,
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
        'initial_sl_count': initial_sl_count
    }

print(f"\n🔄 Testing parameter combinations...")
print()

# Test grid
# RSI: Lower levels (S&P 500 less volatile, may need different triggers)
# Offset/TP: Scale for 0.75x volatility vs NASDAQ
# Trailing: Test NASDAQ winner params + variations

configs = []

# RSI triggers: 25-35 (similar to NASDAQ)
# Offset: 0.15-0.25 (NASDAQ best was 0.20)
# TP: 1.5-2.5% (NASDAQ best was 2.0%, scale down slightly)
# Trailing: activation 0.4-0.6%, trail 0.8-1.2%

for rsi in [25, 28, 30, 32]:
    for offset in [0.15, 0.20, 0.25]:
        for tp in [1.5, 2.0, 2.5]:
            for activation in [0.4, 0.5, 0.6]:
                for trail in [0.8, 1.0, 1.2]:
                    configs.append({
                        'rsi': rsi,
                        'offset': offset,
                        'tp': tp,
                        'activation': activation,
                        'trail': trail
                    })

print(f"Testing {len(configs)} configurations...")

results = []

for config in configs:
    result = backtest_trailing_stop(
        df,
        rsi_trigger=config['rsi'],
        limit_offset=config['offset'],
        tp_pct=config['tp'],
        activation_pct=config['activation'],
        trail_pct=config['trail']
    )

    if result:
        results.append(result)

print(f"✅ Completed {len(results)} successful backtests")

# Sort by R/DD
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

# Display top 20
print("\n" + "="*90)
print("🏆 TOP 20 S&P 500 LONG CONFIGS (by Return/DD)")
print("="*90)
print()

print(f"{'Rank':>4} | {'RSI':>4} | {'Off':>5} | {'TP':>5} | {'Act':>5} | {'Trail':>6} | {'R/DD':>7} | {'Return':>8} | {'DD':>8} | {'Win%':>6} | {'TP/Tr/Init':>12}")
print("-" * 90)

for idx, (i, row) in enumerate(results_df.head(20).iterrows()):
    emoji = "🏆" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx+1:2d}."

    exits = f"{int(row['tp_count'])}/{int(row['trail_sl_count'])}/{int(row['initial_sl_count'])}"

    print(f"{emoji:>4} | <{int(row['rsi_trigger']):>3} | {row['limit_offset']:>5.2f} | {row['tp_pct']:>4.1f}% | {row['activation_pct']:>4.1f}% | {row['trail_pct']:>5.1f}% | {row['return_dd']:>6.2f}x | {row['total_return']:>7.1f}% | {row['max_dd']:>7.2f}% | {row['win_rate']:>5.1f}% | {exits:>12}")

# Best config
best = results_df.iloc[0]

print("\n" + "="*90)
print("🎯 BEST S&P 500 LONG CONFIGURATION")
print("="*90)
print()
print(f"Parameters:")
print(f"  RSI Trigger: <{int(best['rsi_trigger'])} (OVERSOLD)")
print(f"  Limit Offset: {best['limit_offset']:.2f}x ATR below breakout")
print(f"  Take Profit: {best['tp_pct']:.1f}% above entry")
print(f"  Trailing Activation: +{best['activation_pct']:.1f}% profit")
print(f"  Trailing Distance: {best['trail_pct']:.1f}% below highest high")
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
print(f"  Total Trades: {int(best['trades'])}")

# Compare to NASDAQ
print("\n" + "="*90)
print("📊 S&P 500 vs NASDAQ COMPARISON")
print("="*90)
print()

nasdaq_best = {
    'rsi': 28,
    'offset': 0.20,
    'tp': 2.0,
    'activation': 0.5,
    'trail': 1.0,
    'return_dd': 1.87,
    'return': 54.8,
    'max_dd': -29.37,
    'win_rate': 29.6
}

print(f"{'Metric':<25} | {'NASDAQ':<15} | {'S&P 500':<15} | {'Comparison':<15}")
print("-" * 75)
print(f"{'Volatility (ATR%)':<25} | {'0.202%':<15} | {'0.151%':<15} | {'0.75x':<15}")
print(f"{'RSI Trigger':<25} | {f'<{nasdaq_best["rsi"]}':<15} | {f'<{int(best["rsi_trigger"])}':<15} | {'':<15}")
print(f"{'Limit Offset':<25} | {f'{nasdaq_best["offset"]:.2f} ATR':<15} | {f'{best["limit_offset"]:.2f} ATR':<15} | {'':<15}")
print(f"{'Take Profit':<25} | {f'{nasdaq_best["tp"]:.1f}%':<15} | {f'{best["tp_pct"]:.1f}%':<15} | {'':<15}")
print(f"{'Trail Activation':<25} | {f'{nasdaq_best["activation"]:.1f}%':<15} | {f'{best["activation_pct"]:.1f}%':<15} | {'':<15}")
print(f"{'Trail Distance':<25} | {f'{nasdaq_best["trail"]:.1f}%':<15} | {f'{best["trail_pct"]:.1f}%':<15} | {'':<15}")
print()
print(f"{'Return/DD':<25} | {f'{nasdaq_best["return_dd"]:.2f}x':<15} | {f'{best["return_dd"]:.2f}x':<15} | {f'{best["return_dd"] - nasdaq_best["return_dd"]:+.2f}x':<15}")
print(f"{'Total Return':<25} | {f'{nasdaq_best["return"]:+.1f}%':<15} | {f'{best["total_return"]:+.1f}%':<15} | {f'{best["total_return"] - nasdaq_best["return"]:+.1f}pp':<15}")
print(f"{'Max Drawdown':<25} | {f'{nasdaq_best["max_dd"]:.2f}%':<15} | {f'{best["max_dd"]:.2f}%':<15} | {f'{best["max_dd"] - nasdaq_best["max_dd"]:+.2f}pp':<15}")
print(f"{'Win Rate':<25} | {f'{nasdaq_best["win_rate"]:.1f}%':<15} | {f'{best["win_rate"]:.1f}%':<15} | {f'{best["win_rate"] - nasdaq_best["win_rate"]:+.1f}pp':<15}")

# Save results
results_df.to_csv('sp500_long_trailing_results.csv', index=False)
print(f"\n💾 Full results saved to: sp500_long_trailing_results.csv")
print("="*90)
