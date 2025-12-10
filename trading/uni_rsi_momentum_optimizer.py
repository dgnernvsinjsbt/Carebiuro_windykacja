#!/usr/bin/env python3
"""
UNI RSI Momentum Strategy Optimizer
Adapted from MOODENG RSI Momentum LONG strategy
Tests 30 configurations to find profitable setups
"""

import pandas as pd
import numpy as np
from itertools import product
from datetime import datetime

# Load data
print("Loading UNI data...", flush=True)
df = pd.read_csv('trading/uni_30d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Data: {len(df):,} candles from {df['timestamp'].min()} to {df['timestamp'].max()}", flush=True)
print(f"Price range: ${df['close'].min():.3f} - ${df['close'].max():.3f}", flush=True)

def calculate_indicators(df):
    """Calculate RSI, SMA, ATR"""
    # RSI(14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # SMA(20)
    df['sma20'] = df['close'].rolling(window=20).mean()

    # ATR(14)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(window=14).mean()

    # Candle body
    df['body'] = abs(df['close'] - df['open'])
    df['body_pct'] = (df['body'] / df['open']) * 100

    return df

def backtest_rsi_momentum(df, rsi_threshold=55, min_body_pct=0.5, sl_atr=1.0, tp_atr=4.0, time_exit=60):
    """
    RSI Momentum LONG Strategy

    Entry:
    - RSI(14) crosses ABOVE threshold (previous < threshold, current >= threshold)
    - Bullish candle with body > min_body_pct%
    - Price ABOVE SMA(20)

    Exit:
    - Stop Loss: sl_atr × ATR below entry
    - Take Profit: tp_atr × ATR above entry
    - Time Exit: time_exit bars if neither SL/TP hit
    """
    trades = []
    in_position = False
    entry_price = 0
    entry_idx = 0
    stop_loss = 0
    take_profit = 0
    entry_atr = 0

    for i in range(20, len(df)):  # Start after indicators are ready
        current = df.iloc[i]
        prev = df.iloc[i-1]

        # Check exit conditions first
        if in_position:
            bars_held = i - entry_idx

            # Stop Loss
            if current['low'] <= stop_loss:
                exit_price = stop_loss
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                trades.append({
                    'entry_time': df.iloc[entry_idx]['timestamp'],
                    'exit_time': current['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'bars_held': bars_held,
                    'exit_reason': 'SL',
                    'atr_at_entry': entry_atr
                })
                in_position = False
                continue

            # Take Profit
            if current['high'] >= take_profit:
                exit_price = take_profit
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                trades.append({
                    'entry_time': df.iloc[entry_idx]['timestamp'],
                    'exit_time': current['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'bars_held': bars_held,
                    'exit_reason': 'TP',
                    'atr_at_entry': entry_atr
                })
                in_position = False
                continue

            # Time Exit
            if bars_held >= time_exit:
                exit_price = current['close']
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                trades.append({
                    'entry_time': df.iloc[entry_idx]['timestamp'],
                    'exit_time': current['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'bars_held': bars_held,
                    'exit_reason': 'TIME',
                    'atr_at_entry': entry_atr
                })
                in_position = False
                continue

        # Check entry conditions
        if not in_position:
            # RSI crosses above threshold
            rsi_cross = prev['rsi'] < rsi_threshold and current['rsi'] >= rsi_threshold

            # Bullish candle with body > min_body_pct%
            bullish_candle = current['close'] > current['open'] and current['body_pct'] > min_body_pct

            # Price above SMA(20)
            above_sma = current['close'] > current['sma20']

            if rsi_cross and bullish_candle and above_sma and not pd.isna(current['atr']):
                in_position = True
                entry_price = current['close']
                entry_idx = i
                entry_atr = current['atr']
                stop_loss = entry_price - (sl_atr * entry_atr)
                take_profit = entry_price + (tp_atr * entry_atr)

    # Close any open position at end
    if in_position:
        current = df.iloc[-1]
        exit_price = current['close']
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        bars_held = len(df) - 1 - entry_idx
        trades.append({
            'entry_time': df.iloc[entry_idx]['timestamp'],
            'exit_time': current['timestamp'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'bars_held': bars_held,
            'exit_reason': 'EOD',
            'atr_at_entry': entry_atr
        })

    return pd.DataFrame(trades)

def calculate_metrics(trades_df, fee_pct=0.10):
    """Calculate performance metrics"""
    if len(trades_df) == 0:
        return {
            'total_return': 0,
            'num_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'max_dd': 0,
            'return_dd_ratio': 0,
            'sharpe': 0
        }

    # Apply fees
    trades_df['pnl_net'] = trades_df['pnl_pct'] - fee_pct

    # Calculate metrics
    total_return = trades_df['pnl_net'].sum()
    num_trades = len(trades_df)

    winners = trades_df[trades_df['pnl_net'] > 0]
    losers = trades_df[trades_df['pnl_net'] <= 0]

    win_rate = (len(winners) / num_trades * 100) if num_trades > 0 else 0
    avg_win = winners['pnl_net'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl_net'].mean() if len(losers) > 0 else 0

    # Max drawdown
    cumulative = trades_df['pnl_net'].cumsum()
    running_max = cumulative.expanding().max()
    drawdown = cumulative - running_max
    max_dd = abs(drawdown.min()) if len(drawdown) > 0 else 0

    # Return/DD ratio
    return_dd_ratio = (total_return / max_dd) if max_dd > 0 else 0

    # Sharpe (annualized, assuming ~21,000 1-min bars per month)
    sharpe = (trades_df['pnl_net'].mean() / trades_df['pnl_net'].std() * np.sqrt(num_trades)) if trades_df['pnl_net'].std() > 0 else 0

    return {
        'total_return': total_return,
        'num_trades': num_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_dd': max_dd,
        'return_dd_ratio': return_dd_ratio,
        'sharpe': sharpe
    }

# Calculate indicators
print("\nCalculating indicators...", flush=True)
df = calculate_indicators(df)

# Define parameter grid (30 configurations)
print("\nTesting 30 configurations...", flush=True)
print("=" * 80, flush=True)

configs = [
    # Baseline (MOODENG default)
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 4.0, 'time_exit': 60},

    # Vary RSI threshold
    {'rsi_threshold': 50, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 4.0, 'time_exit': 60},
    {'rsi_threshold': 52, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 4.0, 'time_exit': 60},
    {'rsi_threshold': 57, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 4.0, 'time_exit': 60},
    {'rsi_threshold': 60, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 4.0, 'time_exit': 60},

    # Vary SL ATR
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 0.8, 'tp_atr': 4.0, 'time_exit': 60},
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 1.2, 'tp_atr': 4.0, 'time_exit': 60},
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 1.5, 'tp_atr': 4.0, 'time_exit': 60},

    # Vary TP ATR
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 3.0, 'time_exit': 60},
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 5.0, 'time_exit': 60},
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 6.0, 'time_exit': 60},

    # Vary min body
    {'rsi_threshold': 55, 'min_body_pct': 0.3, 'sl_atr': 1.0, 'tp_atr': 4.0, 'time_exit': 60},
    {'rsi_threshold': 55, 'min_body_pct': 0.8, 'sl_atr': 1.0, 'tp_atr': 4.0, 'time_exit': 60},

    # Vary time exit
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 4.0, 'time_exit': 30},
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 4.0, 'time_exit': 90},
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 4.0, 'time_exit': 120},

    # Combinations - tighter SL with higher TP
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 0.8, 'tp_atr': 5.0, 'time_exit': 60},
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 0.8, 'tp_atr': 6.0, 'time_exit': 60},

    # Combinations - wider SL with lower TP
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 1.5, 'tp_atr': 3.0, 'time_exit': 60},
    {'rsi_threshold': 55, 'min_body_pct': 0.5, 'sl_atr': 1.2, 'tp_atr': 3.0, 'time_exit': 60},

    # Lower RSI + tighter params
    {'rsi_threshold': 50, 'min_body_pct': 0.3, 'sl_atr': 1.0, 'tp_atr': 4.0, 'time_exit': 60},
    {'rsi_threshold': 50, 'min_body_pct': 0.5, 'sl_atr': 0.8, 'tp_atr': 5.0, 'time_exit': 60},

    # Higher RSI + wider params
    {'rsi_threshold': 60, 'min_body_pct': 0.8, 'sl_atr': 1.2, 'tp_atr': 4.0, 'time_exit': 60},
    {'rsi_threshold': 60, 'min_body_pct': 0.5, 'sl_atr': 1.5, 'tp_atr': 3.0, 'time_exit': 90},

    # Aggressive scalping
    {'rsi_threshold': 52, 'min_body_pct': 0.3, 'sl_atr': 0.8, 'tp_atr': 3.0, 'time_exit': 30},
    {'rsi_threshold': 55, 'min_body_pct': 0.3, 'sl_atr': 1.0, 'tp_atr': 3.0, 'time_exit': 45},

    # Conservative swing
    {'rsi_threshold': 57, 'min_body_pct': 0.8, 'sl_atr': 1.5, 'tp_atr': 6.0, 'time_exit': 120},
    {'rsi_threshold': 60, 'min_body_pct': 0.8, 'sl_atr': 1.2, 'tp_atr': 5.0, 'time_exit': 90},

    # Balanced variations
    {'rsi_threshold': 52, 'min_body_pct': 0.5, 'sl_atr': 1.2, 'tp_atr': 4.0, 'time_exit': 60},
    {'rsi_threshold': 57, 'min_body_pct': 0.5, 'sl_atr': 1.0, 'tp_atr': 5.0, 'time_exit': 75},
]

results = []

for idx, config in enumerate(configs, 1):
    trades = backtest_rsi_momentum(df, **config)
    metrics = calculate_metrics(trades)

    result = {
        'config_id': idx,
        **config,
        **metrics
    }
    results.append(result)

    if idx % 5 == 0:
        print(f"Completed {idx}/30 configurations...", flush=True)

results_df = pd.DataFrame(results)

# Sort by Return/DD ratio
results_df = results_df.sort_values('return_dd_ratio', ascending=False)

# Save results
output_file = 'trading/results/uni_rsi_momentum_optimization.csv'
results_df.to_csv(output_file, index=False)
print(f"\n✅ Results saved to {output_file}", flush=True)

# Display top 10 configurations
print("\n" + "=" * 80, flush=True)
print("TOP 10 CONFIGURATIONS (by Return/DD Ratio)", flush=True)
print("=" * 80, flush=True)

top10 = results_df.head(10)
for idx, row in top10.iterrows():
    print(f"\n🏆 Rank #{row['config_id']} - Return/DD: {row['return_dd_ratio']:.2f}x", flush=True)
    print(f"   RSI: {row['rsi_threshold']:.0f} | Body: {row['min_body_pct']:.1f}% | SL: {row['sl_atr']:.1f}x ATR | TP: {row['tp_atr']:.1f}x ATR | TimeExit: {row['time_exit']:.0f} bars", flush=True)
    print(f"   Return: {row['total_return']:+.2f}% | Max DD: {row['max_dd']:.2f}% | Trades: {row['num_trades']:.0f}", flush=True)
    print(f"   Win Rate: {row['win_rate']:.1f}% | Avg Win: {row['avg_win']:+.2f}% | Avg Loss: {row['avg_loss']:+.2f}%", flush=True)
    print(f"   Sharpe: {row['sharpe']:.2f}", flush=True)

# Summary statistics
print("\n" + "=" * 80, flush=True)
print("SUMMARY STATISTICS", flush=True)
print("=" * 80, flush=True)
print(f"Profitable configs: {len(results_df[results_df['total_return'] > 0])}/30", flush=True)
print(f"Best Return: {results_df['total_return'].max():+.2f}%", flush=True)
print(f"Best Return/DD: {results_df['return_dd_ratio'].max():.2f}x", flush=True)
print(f"Best Win Rate: {results_df['win_rate'].max():.1f}%", flush=True)
print(f"Avg trades per config: {results_df['num_trades'].mean():.0f}", flush=True)

# Check if any configs are profitable
if results_df['total_return'].max() > 0:
    print(f"\n✅ PROFITABLE STRATEGY FOUND!", flush=True)
    best = results_df.iloc[0]
    print(f"\n🎯 BEST CONFIG:", flush=True)
    print(f"   RSI Threshold: {best['rsi_threshold']:.0f}", flush=True)
    print(f"   Min Body: {best['min_body_pct']:.1f}%", flush=True)
    print(f"   SL: {best['sl_atr']:.1f}x ATR", flush=True)
    print(f"   TP: {best['tp_atr']:.1f}x ATR", flush=True)
    print(f"   Time Exit: {best['time_exit']:.0f} bars", flush=True)
    print(f"\n   Return: {best['total_return']:+.2f}%", flush=True)
    print(f"   Max DD: {best['max_dd']:.2f}%", flush=True)
    print(f"   Return/DD: {best['return_dd_ratio']:.2f}x", flush=True)
    print(f"   Win Rate: {best['win_rate']:.1f}%", flush=True)
    print(f"   Trades: {best['num_trades']:.0f}", flush=True)
else:
    print(f"\n❌ NO PROFITABLE CONFIGURATIONS FOUND", flush=True)
    print(f"   Best Return: {results_df['total_return'].max():+.2f}%", flush=True)
    print(f"   UNI may not be suitable for RSI momentum strategy", flush=True)

print("\n" + "=" * 80, flush=True)
