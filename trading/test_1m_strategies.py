#!/usr/bin/env python3
"""Test multiple strategies on FARTCOIN 1m data"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import pickle

def calculate_indicators(df):
    """Calculate technical indicators"""
    df = df.copy()

    # EMAs
    df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'] * 100

    # Volume
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['vol_spike'] = df['volume'] > df['vol_ma'] * 2

    # ATR for volatility
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['atr'] = ranges.max(axis=1).rolling(14).mean()

    return df

def backtest_strategy(df, strategy_name, entry_logic, exit_sl_pct, exit_tp_pct, max_hold_candles=None):
    """Generic backtesting function"""
    equity = 1.0
    peak = 1.0
    max_dd = 0
    equity_curve = []
    trades = []
    in_position = False
    position_type = None
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    entry_candle = 0

    fee = 0.0005  # 0.05% taker fee

    for i in range(50, len(df)):  # Start after indicators warm up
        row = df.iloc[i]

        if not in_position:
            # Check entry conditions
            signal = entry_logic(df, i)

            if signal == 'LONG':
                in_position = True
                position_type = 'LONG'
                entry_price = row['close']
                entry_candle = i
                stop_loss = entry_price * (1 - exit_sl_pct/100)
                take_profit = entry_price * (1 + exit_tp_pct/100)

            elif signal == 'SHORT':
                in_position = True
                position_type = 'SHORT'
                entry_price = row['close']
                entry_candle = i
                stop_loss = entry_price * (1 + exit_sl_pct/100)
                take_profit = entry_price * (1 - exit_tp_pct/100)

        else:
            # Check exit conditions
            exit_type = None
            exit_price = None

            # Max hold time
            if max_hold_candles and (i - entry_candle) >= max_hold_candles:
                exit_price = row['close']
                exit_type = 'TIME'

            # Stop loss and take profit
            elif position_type == 'LONG':
                if row['low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                elif row['high'] >= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'

            elif position_type == 'SHORT':
                if row['high'] >= stop_loss:
                    exit_price = stop_loss
                    exit_type = 'SL'
                elif row['low'] <= take_profit:
                    exit_price = take_profit
                    exit_type = 'TP'

            if exit_type:
                # Calculate P&L
                if position_type == 'LONG':
                    pnl = (exit_price - entry_price) / entry_price - fee * 2
                else:  # SHORT
                    pnl = (entry_price - exit_price) / entry_price - fee * 2

                equity *= (1 + pnl)

                trades.append({
                    'type': position_type,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl_pct': pnl * 100,
                    'exit_type': exit_type,
                    'hold_time': i - entry_candle
                })

                in_position = False

        # Track drawdown
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)

        equity_curve.append(equity)

    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    winners = trades_df[trades_df['pnl_pct'] > 0]

    return {
        'strategy': strategy_name,
        'total_return': (equity - 1) * 100,
        'max_drawdown': max_dd,
        'r_r_score': (equity - 1) * 100 / max_dd if max_dd > 0 else 0,
        'total_trades': len(trades),
        'win_rate': len(winners) / len(trades) * 100,
        'avg_hold': trades_df['hold_time'].mean(),
        'equity_curve': equity_curve,
        'trades': trades_df
    }

# Load and prepare data
df = pd.read_csv('fartcoin_1m_3months.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = calculate_indicators(df)

print('=' * 80)
print('TESTING MULTIPLE STRATEGIES ON FARTCOIN 1M DATA')
print('=' * 80)
print()

# Strategy 1: RSI Mean Reversion LONG
def rsi_long(df, i):
    if df.iloc[i]['rsi'] < 30 and df.iloc[i-1]['rsi'] >= 30:
        return 'LONG'
    return None

result1 = backtest_strategy(df, 'RSI Mean Reversion LONG', rsi_long, 1.5, 2.0, 60)

# Strategy 2: RSI Mean Reversion SHORT
def rsi_short(df, i):
    if df.iloc[i]['rsi'] > 70 and df.iloc[i-1]['rsi'] <= 70:
        return 'SHORT'
    return None

result2 = backtest_strategy(df, 'RSI Mean Reversion SHORT', rsi_short, 1.5, 2.0, 60)

# Strategy 3: Bollinger Band Bounce LONG
def bb_long(df, i):
    if df.iloc[i]['close'] < df.iloc[i]['bb_lower'] and df.iloc[i-1]['close'] >= df.iloc[i-1]['bb_lower']:
        return 'LONG'
    return None

result3 = backtest_strategy(df, 'Bollinger Bounce LONG', bb_long, 1.0, 1.5, 45)

# Strategy 4: Bollinger Band Bounce SHORT
def bb_short(df, i):
    if df.iloc[i]['close'] > df.iloc[i]['bb_upper'] and df.iloc[i-1]['close'] <= df.iloc[i-1]['bb_upper']:
        return 'SHORT'
    return None

result4 = backtest_strategy(df, 'Bollinger Bounce SHORT', bb_short, 1.0, 1.5, 45)

# Strategy 5: EMA Crossover LONG
def ema_long(df, i):
    if df.iloc[i]['ema_5'] > df.iloc[i]['ema_20'] and df.iloc[i-1]['ema_5'] <= df.iloc[i-1]['ema_20']:
        return 'LONG'
    return None

result5 = backtest_strategy(df, 'EMA 5/20 Cross LONG', ema_long, 1.0, 1.5, 30)

# Strategy 6: EMA Crossover SHORT
def ema_short(df, i):
    if df.iloc[i]['ema_5'] < df.iloc[i]['ema_20'] and df.iloc[i-1]['ema_5'] >= df.iloc[i-1]['ema_20']:
        return 'SHORT'
    return None

result6 = backtest_strategy(df, 'EMA 5/20 Cross SHORT', ema_short, 1.0, 1.5, 30)

# Strategy 7: Volume Spike + Momentum LONG
def vol_momentum_long(df, i):
    if (df.iloc[i]['vol_spike'] and
        df.iloc[i]['close'] > df.iloc[i]['ema_5'] and
        df.iloc[i]['rsi'] > 50 and df.iloc[i]['rsi'] < 70):
        return 'LONG'
    return None

result7 = backtest_strategy(df, 'Volume Momentum LONG', vol_momentum_long, 1.5, 2.5, 20)

# Strategy 8: Combined Mean Reversion (RSI + BB)
def combined_mr(df, i):
    # LONG when oversold
    if df.iloc[i]['rsi'] < 35 and df.iloc[i]['close'] < df.iloc[i]['bb_lower']:
        return 'LONG'
    # SHORT when overbought
    elif df.iloc[i]['rsi'] > 65 and df.iloc[i]['close'] > df.iloc[i]['bb_upper']:
        return 'SHORT'
    return None

result8 = backtest_strategy(df, 'Combined Mean Reversion', combined_mr, 1.2, 2.0, 50)

# Collect results
results = []
for r in [result1, result2, result3, result4, result5, result6, result7, result8]:
    if r:
        results.append(r)

# Sort by R:R score (best risk-adjusted return)
results.sort(key=lambda x: x['r_r_score'], reverse=True)

print(f"{'Strategy':<30} {'Return':>10} {'Max DD':>10} {'R:R':>8} {'Trades':>8} {'Win%':>8} {'Avg Hold':>10}")
print('-' * 100)

for r in results:
    print(f"{r['strategy']:<30} {r['total_return']:>9.2f}% {r['max_drawdown']:>9.2f}% {r['r_r_score']:>7.2f} {r['total_trades']:>8.0f} {r['win_rate']:>7.1f}% {r['avg_hold']:>9.1f}m")

print('=' * 100)

# Find best strategy with DD < 30%
best = None
for r in results:
    if r['max_drawdown'] < 30:
        best = r
        break

if best:
    print()
    print('🏆 BEST STRATEGY (DD < 30%):')
    print(f"   {best['strategy']}")
    print(f"   Return: +{best['total_return']:.2f}%")
    print(f"   Max DD: {best['max_drawdown']:.2f}%")
    print(f"   R:R Score: {best['r_r_score']:.2f}")
    print(f"   Trades: {best['total_trades']:.0f}")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Avg Hold: {best['avg_hold']:.1f} minutes")
    print()

    # Save best result for plotting
    with open('best_1m_strategy.pkl', 'wb') as f:
        pickle.dump(best, f)

    print('✓ Saved best strategy data for plotting')
else:
    print()
    print('⚠ No strategy found with DD < 30%')
    print('   Showing all results above')
