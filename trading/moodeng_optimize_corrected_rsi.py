"""
MOODENG RSI Swing Optimization - WITH CORRECTED RSI

Test multiple parameter combinations to find what actually works
"""

import pandas as pd
import numpy as np
from itertools import product
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'bingx-trading-bot'))
from data.indicators import rsi, atr


def backtest(df_1h, rsi_low, rsi_high, limit_offset_pct, stop_atr_mult, tp_atr_mult, max_wait_bars=5, fees=0.001):
    """Run backtest with given parameters"""

    capital = 100.0
    position = None
    pending_order = None
    trades = []
    equity_curve = [capital]

    for i in range(1, len(df_1h)):
        bar = df_1h.iloc[i]
        prev_bar = df_1h.iloc[i-1]

        if pd.isna(bar['rsi']) or pd.isna(bar['atr']):
            equity_curve.append(equity_curve[-1])
            continue

        # Check pending limit order
        if pending_order is not None:
            bars_waiting = i - pending_order['signal_bar']

            filled = False
            if pending_order['side'] == 'LONG':
                if bar['low'] <= pending_order['limit_price']:
                    filled = True
            else:
                if bar['high'] >= pending_order['limit_price']:
                    filled = True

            if filled:
                position = {
                    'side': pending_order['side'],
                    'entry_bar': i,
                    'entry_price': pending_order['limit_price'],
                    'stop_loss': pending_order['stop_loss'],
                    'take_profit': pending_order['take_profit'],
                    'size': capital * 0.10
                }
                pending_order = None
            elif bars_waiting >= max_wait_bars:
                pending_order = None

        # Check existing position
        if position is not None:
            exit_price = None
            exit_reason = None

            # Stop loss
            if position['side'] == 'LONG':
                if bar['low'] <= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'SL'
            else:
                if bar['high'] >= position['stop_loss']:
                    exit_price = position['stop_loss']
                    exit_reason = 'SL'

            # Take profit
            if exit_price is None:
                if position['side'] == 'LONG':
                    if bar['high'] >= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'TP'
                else:
                    if bar['low'] <= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = 'TP'

            # RSI exit
            if exit_price is None:
                if position['side'] == 'LONG':
                    if bar['rsi'] < rsi_high and prev_bar['rsi'] >= rsi_high:
                        exit_price = bar['close']
                        exit_reason = 'RSI'
                else:
                    if bar['rsi'] > rsi_low and prev_bar['rsi'] <= rsi_low:
                        exit_price = bar['close']
                        exit_reason = 'RSI'

            if exit_price is not None:
                if position['side'] == 'LONG':
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                else:
                    pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']

                pnl_pct -= (fees * 2)
                pnl = position['size'] * pnl_pct
                capital += pnl

                trades.append({
                    'pnl': pnl,
                    'pnl_pct': pnl_pct * 100,
                    'exit_reason': exit_reason
                })

                position = None

        # Generate signals
        if position is None and pending_order is None:
            if bar['rsi'] > rsi_low and prev_bar['rsi'] <= rsi_low:
                signal_price = bar['close']
                limit_price = signal_price * (1 - limit_offset_pct / 100)
                stop_loss = limit_price - (stop_atr_mult * bar['atr'])
                take_profit = limit_price + (tp_atr_mult * bar['atr'])

                pending_order = {
                    'side': 'LONG',
                    'signal_bar': i,
                    'limit_price': limit_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }

            elif bar['rsi'] < rsi_high and prev_bar['rsi'] >= rsi_high:
                signal_price = bar['close']
                limit_price = signal_price * (1 + limit_offset_pct / 100)
                stop_loss = limit_price + (stop_atr_mult * bar['atr'])
                take_profit = limit_price - (tp_atr_mult * bar['atr'])

                pending_order = {
                    'side': 'SHORT',
                    'signal_bar': i,
                    'limit_price': limit_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }

        equity_curve.append(capital)

    # Calculate stats
    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    total_return = ((capital - 100) / 100) * 100
    winning_trades = trades_df[trades_df['pnl'] > 0]
    win_rate = (len(winning_trades) / len(trades_df)) * 100

    # Drawdown
    equity_series = pd.Series(equity_curve)
    running_max = equity_series.expanding().max()
    drawdown = ((equity_series - running_max) / running_max) * 100
    max_drawdown = drawdown.min()

    return_dd_ratio = abs(total_return / max_drawdown) if max_drawdown != 0 else 0

    return {
        'rsi_low': rsi_low,
        'rsi_high': rsi_high,
        'limit_offset_pct': limit_offset_pct,
        'stop_atr_mult': stop_atr_mult,
        'tp_atr_mult': tp_atr_mult,
        'trades': len(trades_df),
        'return_pct': total_return,
        'max_dd_pct': max_drawdown,
        'return_dd_ratio': return_dd_ratio,
        'win_rate': win_rate
    }


print("=" * 100)
print("MOODENG RSI OPTIMIZATION - CORRECTED RSI")
print("=" * 100)

# Load data
df_1h = pd.read_csv('bingx-trading-bot/trading/moodeng_usdt_90d_1h.csv')
df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'])
df_1h = df_1h.sort_values('timestamp').reset_index(drop=True)

print(f"Data: {len(df_1h)} candles ({df_1h['timestamp'].min()} to {df_1h['timestamp'].max()})")

# Calculate indicators
print("Calculating indicators...")
df_1h['rsi'] = rsi(df_1h['close'], 14)
df_1h['atr'] = atr(df_1h['high'], df_1h['low'], df_1h['close'], 14)

# Parameter grid
rsi_low_values = [25, 27, 30]
rsi_high_values = [65, 70, 75]
limit_offset_values = [0.5, 1.0, 1.5, 2.0]
stop_atr_values = [1.0, 1.5, 2.0]
tp_atr_values = [1.0, 1.5, 2.0, 3.0]

print(f"\nTesting {len(rsi_low_values) * len(rsi_high_values) * len(limit_offset_values) * len(stop_atr_values) * len(tp_atr_values)} combinations...")

results = []
total_combos = len(rsi_low_values) * len(rsi_high_values) * len(limit_offset_values) * len(stop_atr_values) * len(tp_atr_values)
count = 0

for rsi_low, rsi_high, limit_offset, stop_atr, tp_atr in product(
    rsi_low_values, rsi_high_values, limit_offset_values, stop_atr_values, tp_atr_values
):
    count += 1
    if count % 50 == 0:
        print(f"Progress: {count}/{total_combos}...")

    result = backtest(df_1h, rsi_low, rsi_high, limit_offset, stop_atr, tp_atr)
    if result is not None:
        results.append(result)

print(f"\nCompleted {len(results)} valid backtests")

# Convert to DataFrame and sort
results_df = pd.DataFrame(results)

# Filter: at least 15 trades
results_df = results_df[results_df['trades'] >= 15]

print(f"After filtering (min 15 trades): {len(results_df)} configs")

if len(results_df) == 0:
    print("\n❌ No configs met minimum trade requirement!")
    sys.exit(1)

# Sort by Return/DD ratio
results_df = results_df.sort_values('return_dd_ratio', ascending=False)

print("\n" + "=" * 100)
print("TOP 20 CONFIGS BY RETURN/DD RATIO")
print("=" * 100)
print(f"{'Rank':<5} {'RSI':<10} {'Limit%':<8} {'SL_ATR':<8} {'TP_ATR':<8} {'Trades':<7} "
      f"{'Return%':<10} {'MaxDD%':<10} {'R/DD':<8} {'Win%':<7}")
print("-" * 100)

for idx, row in results_df.head(20).iterrows():
    print(f"{results_df.index.get_loc(idx)+1:<5} "
          f"{row['rsi_low']:.0f}/{row['rsi_high']:.0f}{'':<5} "
          f"{row['limit_offset_pct']:<8.1f} "
          f"{row['stop_atr_mult']:<8.1f} "
          f"{row['tp_atr_mult']:<8.1f} "
          f"{row['trades']:<7.0f} "
          f"{row['return_pct']:<10.2f} "
          f"{row['max_dd_pct']:<10.2f} "
          f"{row['return_dd_ratio']:<8.2f} "
          f"{row['win_rate']:<7.1f}")

# Save results
results_df.to_csv('moodeng_optimization_corrected_rsi.csv', index=False)
print(f"\n✅ Full results saved to moodeng_optimization_corrected_rsi.csv")

# Show best config
best = results_df.iloc[0]
print("\n" + "=" * 100)
print("BEST CONFIGURATION")
print("=" * 100)
print(f"RSI Thresholds: {best['rsi_low']:.0f} / {best['rsi_high']:.0f}")
print(f"Limit Offset: {best['limit_offset_pct']:.1f}%")
print(f"Stop Loss: {best['stop_atr_mult']:.1f}x ATR")
print(f"Take Profit: {best['tp_atr_mult']:.1f}x ATR")
print(f"\nPerformance:")
print(f"  Trades: {best['trades']:.0f}")
print(f"  Return: {best['return_pct']:+.2f}%")
print(f"  Max DD: {best['max_dd_pct']:.2f}%")
print(f"  Return/DD: {best['return_dd_ratio']:.2f}x")
print(f"  Win Rate: {best['win_rate']:.1f}%")
print("=" * 100)
