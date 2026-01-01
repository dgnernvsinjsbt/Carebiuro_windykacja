#!/usr/bin/env python3
"""
Test SHORT reversal strategy on NASDAQ-100
Parameters scaled for lower volatility + lower RSI levels
"""
import pandas as pd
import numpy as np

print("="*90)
print("NASDAQ-100 SHORT REVERSAL STRATEGY - PARAMETER OPTIMIZATION")
print("="*90)

# Load NASDAQ data
df = pd.read_csv('trading/nasdaq_3months_15m.csv')
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

def find_swing_low(df, idx, lookback):
    start = max(0, idx - lookback)
    return df.iloc[start:idx+1]['low'].min()

def find_swing_high(df, start_idx, end_idx):
    return df.iloc[start_idx:end_idx+1]['high'].max()

def backtest_config(df, rsi_trigger, limit_offset, tp_pct, lookback=5, max_wait=20, max_sl_pct=5.0):
    """
    Backtest one parameter configuration
    """
    equity = 100.0
    trades = []

    armed = False
    signal_idx = None
    swing_low = None
    limit_pending = False
    limit_placed_idx = None
    swing_high_for_sl = None

    for i in range(lookback, len(df)):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']):
            continue

        # ARM signal
        if row['rsi'] > rsi_trigger:
            armed = True
            signal_idx = i
            swing_low = find_swing_low(df, i, lookback)
            limit_pending = False

        # Support break
        if armed and swing_low is not None and not limit_pending:
            if row['low'] < swing_low:
                atr = row['atr']
                limit_price = swing_low + (atr * limit_offset)
                swing_high_for_sl = find_swing_high(df, signal_idx, i)
                limit_pending = True
                limit_placed_idx = i
                armed = False

        # Limit order fill check
        if limit_pending:
            # Timeout
            if i - limit_placed_idx > max_wait:
                limit_pending = False
                continue

            # Check fill
            if row['high'] >= limit_price:
                entry_price = limit_price
                sl_price = swing_high_for_sl
                tp_price = entry_price * (1 - tp_pct / 100)

                sl_dist_pct = ((sl_price - entry_price) / entry_price) * 100

                # Skip if SL too wide
                if sl_dist_pct <= 0 or sl_dist_pct > max_sl_pct:
                    limit_pending = False
                    continue

                # Position sizing
                size = (equity * 0.05) / (sl_dist_pct / 100)

                # Find exit
                hit_sl = False
                hit_tp = False
                exit_bar = None

                for j in range(i + 1, min(i + 500, len(df))):
                    future_row = df.iloc[j]

                    if future_row['high'] >= sl_price:
                        hit_sl = True
                        exit_bar = j
                        break
                    elif future_row['low'] <= tp_price:
                        hit_tp = True
                        exit_bar = j
                        break

                if hit_sl:
                    pnl_pct = -sl_dist_pct
                    exit_reason = 'SL'
                elif hit_tp:
                    pnl_pct = tp_pct
                    exit_reason = 'TP'
                else:
                    continue

                pnl_dollar = size * (pnl_pct / 100) - size * 0.001  # 0.1% fees
                equity += pnl_dollar

                trades.append({
                    'entry_time': row['timestamp'],
                    'exit_time': df.iloc[exit_bar]['timestamp'],
                    'pnl_pct': pnl_pct,
                    'pnl_dollar': pnl_dollar,
                    'exit_reason': exit_reason,
                    'sl_dist_pct': sl_dist_pct
                })

                limit_pending = False

    if len(trades) == 0:
        return None

    # Calculate metrics
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

    return {
        'rsi_trigger': rsi_trigger,
        'limit_offset': limit_offset,
        'tp_pct': tp_pct,
        'trades': len(trades_df),
        'win_rate': win_rate,
        'total_return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'final_equity': equity,
        'avg_sl_dist': trades_df['sl_dist_pct'].mean()
    }

# Parameter grid (20 combinations)
# RSI: Lower levels for NASDAQ (less volatile)
# Limit offset: Scaled down from MELANIA (0.8 → ~0.2)
# TP: Scaled down from MELANIA (10% → ~2%)

configs = [
    # RSI 60 (low)
    {'rsi': 60, 'offset': 0.15, 'tp': 1.5},
    {'rsi': 60, 'offset': 0.20, 'tp': 2.0},
    {'rsi': 60, 'offset': 0.25, 'tp': 2.5},

    # RSI 65 (medium-low)
    {'rsi': 65, 'offset': 0.15, 'tp': 1.5},
    {'rsi': 65, 'offset': 0.20, 'tp': 2.0},
    {'rsi': 65, 'offset': 0.20, 'tp': 2.5},
    {'rsi': 65, 'offset': 0.25, 'tp': 3.0},

    # RSI 68 (medium)
    {'rsi': 68, 'offset': 0.15, 'tp': 2.0},
    {'rsi': 68, 'offset': 0.20, 'tp': 2.5},
    {'rsi': 68, 'offset': 0.25, 'tp': 3.0},

    # RSI 70 (medium-high)
    {'rsi': 70, 'offset': 0.15, 'tp': 2.0},
    {'rsi': 70, 'offset': 0.20, 'tp': 2.5},
    {'rsi': 70, 'offset': 0.25, 'tp': 3.0},
    {'rsi': 70, 'offset': 0.30, 'tp': 3.5},

    # RSI 72 (MELANIA level - high)
    {'rsi': 72, 'offset': 0.15, 'tp': 2.0},
    {'rsi': 72, 'offset': 0.20, 'tp': 2.5},
    {'rsi': 72, 'offset': 0.25, 'tp': 3.0},

    # RSI 75 (very high)
    {'rsi': 75, 'offset': 0.20, 'tp': 2.0},
    {'rsi': 75, 'offset': 0.25, 'tp': 2.5},
    {'rsi': 75, 'offset': 0.30, 'tp': 3.0},
]

print(f"\n🔄 Testing {len(configs)} parameter combinations...")
print()

results = []

for config in configs:
    result = backtest_config(
        df,
        rsi_trigger=config['rsi'],
        limit_offset=config['offset'],
        tp_pct=config['tp']
    )

    if result:
        results.append(result)

print(f"✅ Completed {len(results)} successful backtests")

# Sort by Return/DD
results_df = pd.DataFrame(results)
results_df = results_df.sort_values('return_dd', ascending=False)

# Display results
print("\n" + "="*90)
print("🏆 TOP 20 NASDAQ-100 SHORT REVERSAL CONFIGS (by Return/DD)")
print("="*90)
print()

for idx, (i, row) in enumerate(results_df.head(20).iterrows()):
    emoji = "🏆" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"{idx+1:2d}"

    print(f"{emoji} RSI:{int(row['rsi_trigger']):2d}, Offset:{row['limit_offset']:.2f}, TP:{row['tp_pct']:.1f}%")
    print(f"    R/DD: {row['return_dd']:6.2f}x | Return: {row['total_return']:+6.1f}% | Max DD: {row['max_dd']:6.2f}%")
    print(f"    Trades: {int(row['trades']):2d} | Win%: {row['win_rate']:5.1f}% | Avg SL: {row['avg_sl_dist']:.2f}%")
    print()

# Best config details
best = results_df.iloc[0]

print("="*90)
print("🎯 BEST CONFIGURATION")
print("="*90)
print()
print(f"Parameters:")
print(f"  RSI Trigger: >{int(best['rsi_trigger'])}")
print(f"  Limit Offset: {best['limit_offset']:.2f}x ATR")
print(f"  Take Profit: {best['tp_pct']:.1f}%")
print(f"  Lookback: 5 candles")
print(f"  Max Wait: 20 bars (5 hours)")
print()
print(f"Performance:")
print(f"  Return/DD: {best['return_dd']:.2f}x")
print(f"  Total Return: {best['total_return']:+.1f}%")
print(f"  Max Drawdown: {best['max_dd']:.2f}%")
print(f"  Final Equity: ${best['final_equity']:.2f}")
print()
print(f"Trade Stats:")
print(f"  Total Trades: {int(best['trades'])}")
print(f"  Win Rate: {best['win_rate']:.1f}%")
print(f"  Avg SL Distance: {best['avg_sl_dist']:.2f}%")
print()

# Comparison to MELANIA
print("="*90)
print("📊 NASDAQ vs MELANIA COMPARISON")
print("="*90)
print()
print(f"{'Metric':<20} | {'MELANIA':<20} | {'NASDAQ (best)':<20}")
print("-" * 65)
print(f"{'Volatility (ATR%)':<20} | {'0.943%':<20} | {'0.202%':<20}")
print(f"{'RSI Trigger':<20} | {'72':<20} | {int(best['rsi_trigger']):<20}")
nasdaq_offset = f"{best['limit_offset']:.2f} ATR"
nasdaq_tp = f"{best['tp_pct']:.1f}%"
nasdaq_rdd = f"{best['return_dd']:.2f}x"
print(f"{'Limit Offset':<20} | {'0.8 ATR':<20} | {nasdaq_offset:<20}")
print(f"{'Take Profit':<20} | {'10.0%':<20} | {nasdaq_tp:<20}")
print(f"{'Return/DD':<20} | {'53.96x':<20} | {nasdaq_rdd:<20}")
print()

# Save results
results_df.to_csv('nasdaq_short_reversal_results.csv', index=False)
print("💾 Full results saved to: nasdaq_short_reversal_results.csv")
print("="*90)
