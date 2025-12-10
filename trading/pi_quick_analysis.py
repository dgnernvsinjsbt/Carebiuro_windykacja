#!/usr/bin/env python3
"""
PI/USDT Quick Pattern Analysis
===============================
Fast version testing key strategy concepts on PI/USDT.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Load data
print("Loading PI/USDT data...")
df = pd.read_csv('pi_30d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate features
print("Calculating indicators...")
df['returns'] = (df['close'] - df['open']) / df['open'] * 100
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['range_pct'] = (df['high'] - df['low']) / df['open'] * 100

# Volume
df['volume_ma_30'] = df['volume'].rolling(30).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma_30']

# ATR
df['tr'] = df[['high', 'low']].apply(lambda x: x['high'] - x['low'], axis=1)
df['atr_14'] = df['tr'].rolling(14).mean()
df['atr_20'] = df['tr'].rolling(20).mean()
df['atr_ma_20'] = df['atr_14'].rolling(20).mean()
df['atr_ratio'] = df['atr_14'] / df['atr_ma_20']

# EMA
df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ema_dist_pct'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi_14'] = 100 - (100 / (1 + rs))

# Multi-bar momentum
df['ret_5m'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5) * 100
df['ret_10m'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10) * 100

# Session
df['hour'] = df['timestamp'].dt.hour

print(f"✅ Loaded {len(df):,} candles\n")

# ==================== BASELINE STATS ====================
print("="*70)
print("BASELINE STATISTICS")
print("="*70)
print(f"Price: ${df['close'].iloc[0]:.4f} → ${df['close'].iloc[-1]:.4f} ({(df['close'].iloc[-1]/df['close'].iloc[0]-1)*100:+.2f}%)")
print(f"Avg Returns: {df['returns'].mean():.4f}%")
print(f"Avg Body: {df['body_pct'].mean():.4f}%")
print(f"Avg ATR: {df['atr_14'].mean():.6f}")
print(f"Big Moves (>1%): {len(df[abs(df['returns'])>1])} ({len(df[abs(df['returns'])>1])/len(df)*100:.2f}%)")
print()

# ==================== TEST STRATEGIES ====================

def backtest_strategy(df, config, strategy_name):
    """Generic backtest function"""
    trades = []

    for i in range(100, len(df) - config.get('max_hold', 200)):
        row = df.iloc[i]

        # Entry logic based on strategy
        if strategy_name == 'mean_reversion':
            # TRUMPSOL-style contrarian
            momentum = abs(row['ret_5m'])
            if pd.isna(momentum) or momentum < config['min_ret']:
                continue
            if pd.isna(row['volume_ratio']) or row['volume_ratio'] < config['vol_min']:
                continue
            if pd.isna(row['atr_ratio']) or row['atr_ratio'] < config['atr_min']:
                continue

            # Contrarian direction
            if row['ret_5m'] > 0:
                direction = 'SHORT'
                entry_price = row['close']
                tp_price = entry_price * (1 - config['tp_pct']/100)
                sl_price = entry_price * (1 + config['sl_pct']/100)
            else:
                direction = 'LONG'
                entry_price = row['close']
                tp_price = entry_price * (1 + config['tp_pct']/100)
                sl_price = entry_price * (1 - config['sl_pct']/100)

        elif strategy_name == 'ema_cross':
            # PIPPIN-style EMA cross
            ema_cross = (df['ema_9'].iloc[i] - df['ema_21'].iloc[i]) * (df['ema_9'].iloc[i-1] - df['ema_21'].iloc[i-1])
            if ema_cross >= 0:  # No cross
                continue

            # RSI filter
            if config.get('min_rsi', 0) > 0:
                if pd.isna(row['rsi_14']) or row['rsi_14'] < config['min_rsi']:
                    continue

            # Body filter
            if config.get('max_body', 999) < 999:
                if pd.isna(row['body_pct']) or row['body_pct'] > config['max_body']:
                    continue

            # Direction
            if df['ema_9'].iloc[i] > df['ema_21'].iloc[i]:
                direction = 'LONG'
            else:
                direction = 'SHORT'

            entry_price = row['close']
            atr = row['atr_14'] if not pd.isna(row['atr_14']) else 0.001

            if direction == 'LONG':
                tp_price = entry_price + config['tp_atr'] * atr
                sl_price = entry_price - config['sl_atr'] * atr
            else:
                tp_price = entry_price - config['tp_atr'] * atr
                sl_price = entry_price + config['sl_atr'] * atr

        elif strategy_name == 'atr_expansion':
            # FARTCOIN-style ATR breakout
            if pd.isna(row['atr_ratio']) or row['atr_ratio'] < config['atr_mult']:
                continue
            if pd.isna(row['ema_dist_pct']) or abs(row['ema_dist_pct']) > config['ema_dist']:
                continue

            is_bullish = row['close'] > row['open']
            is_bearish = row['close'] < row['open']

            if not (is_bullish or is_bearish):
                continue

            direction = 'LONG' if is_bullish else 'SHORT'
            entry_price = row['close']
            atr = row['atr_14'] if not pd.isna(row['atr_14']) else 0.001

            if direction == 'LONG':
                tp_price = entry_price + config['tp_atr'] * atr
                sl_price = entry_price - config['sl_atr'] * atr
            else:
                tp_price = entry_price - config['tp_atr'] * atr
                sl_price = entry_price + config['sl_atr'] * atr

        else:
            continue

        # Simulate trade
        max_hold = config.get('max_hold', 200)
        exit_bar = i + 1
        exit_reason = 'TIME'

        for j in range(i+1, min(i+max_hold+1, len(df))):
            bar = df.iloc[j]

            if direction == 'LONG':
                if bar['low'] <= sl_price:
                    exit_bar = j
                    exit_reason = 'SL'
                    break
                if bar['high'] >= tp_price:
                    exit_bar = j
                    exit_reason = 'TP'
                    break
            else:
                if bar['high'] >= sl_price:
                    exit_bar = j
                    exit_reason = 'SL'
                    break
                if bar['low'] <= tp_price:
                    exit_bar = j
                    exit_reason = 'TP'
                    break

        # Calculate PnL
        exit_price = df.iloc[exit_bar]['close']
        if exit_reason == 'TP':
            exit_price = tp_price
        elif exit_reason == 'SL':
            exit_price = sl_price

        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        pnl_pct -= 0.10  # Fees

        trades.append({
            'entry_bar': i,
            'exit_bar': exit_bar,
            'direction': direction,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

    if not trades:
        return None

    trades_df = pd.DataFrame(trades)
    total_return = trades_df['pnl_pct'].sum()

    cumulative = (1 + trades_df['pnl_pct']/100).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    max_dd = abs(drawdown.min())

    return_dd = total_return / max_dd if max_dd > 0 else 0
    win_rate = (trades_df['pnl_pct'] > 0).mean() * 100
    tp_rate = (trades_df['exit_reason'] == 'TP').mean() * 100

    return {
        'strategy': strategy_name,
        'config': config,
        'trades': len(trades),
        'return': total_return,
        'max_dd': max_dd,
        'return_dd': return_dd,
        'win_rate': win_rate,
        'tp_rate': tp_rate,
        'trades_df': trades_df
    }

# ==================== TEST CONFIGS ====================

results = []

# 1. Mean Reversion
print("Testing Mean Reversion...")
for config in [
    {'min_ret': 0.5, 'vol_min': 1.0, 'atr_min': 1.0, 'tp_pct': 1.0, 'sl_pct': 0.5, 'max_hold': 15},
    {'min_ret': 0.8, 'vol_min': 1.2, 'atr_min': 1.1, 'tp_pct': 1.5, 'sl_pct': 0.8, 'max_hold': 20},
    {'min_ret': 1.0, 'vol_min': 1.5, 'atr_min': 1.2, 'tp_pct': 2.0, 'sl_pct': 1.0, 'max_hold': 30},
]:
    result = backtest_strategy(df, config, 'mean_reversion')
    if result and result['trades'] >= 10:
        results.append(result)

# 2. EMA Cross
print("Testing EMA Crosses...")
for config in [
    {'min_rsi': 0, 'max_body': 999, 'sl_atr': 1.5, 'tp_atr': 8.0, 'max_hold': 120},
    {'min_rsi': 50, 'max_body': 999, 'sl_atr': 1.5, 'tp_atr': 10.0, 'max_hold': 120},
    {'min_rsi': 55, 'max_body': 0.06, 'sl_atr': 1.5, 'tp_atr': 10.0, 'max_hold': 120},
]:
    result = backtest_strategy(df, config, 'ema_cross')
    if result and result['trades'] >= 10:
        results.append(result)

# 3. ATR Expansion
print("Testing ATR Expansion...")
for config in [
    {'atr_mult': 1.3, 'ema_dist': 2.0, 'sl_atr': 2.0, 'tp_atr': 6.0, 'max_hold': 200},
    {'atr_mult': 1.5, 'ema_dist': 3.0, 'sl_atr': 2.0, 'tp_atr': 8.0, 'max_hold': 200},
    {'atr_mult': 1.5, 'ema_dist': 4.0, 'sl_atr': 2.0, 'tp_atr': 10.0, 'max_hold': 200},
]:
    result = backtest_strategy(df, config, 'atr_expansion')
    if result and result['trades'] >= 10:
        results.append(result)

# ==================== RESULTS ====================

print("\n" + "="*70)
print("RESULTS - TOP STRATEGIES")
print("="*70 + "\n")

results.sort(key=lambda x: x['return_dd'], reverse=True)

for i, r in enumerate(results[:10], 1):
    print(f"{i}. {r['strategy'].upper()}")
    print(f"   Return/DD: {r['return_dd']:.2f}x | Return: {r['return']:+.2f}% | Max DD: {r['max_dd']:.2f}%")
    print(f"   Trades: {r['trades']} | Win: {r['win_rate']:.1f}% | TP: {r['tp_rate']:.1f}%")
    print(f"   Config: {r['config']}")
    print()

if results:
    # Save best strategy details
    best = results[0]
    best['trades_df'].to_csv('results/pi_best_strategy_trades.csv', index=False)
    print(f"✅ Saved best strategy trades to results/pi_best_strategy_trades.csv")

    # Summary
    summary = pd.DataFrame([{
        'strategy': r['strategy'],
        'return_dd': r['return_dd'],
        'return': r['return'],
        'max_dd': r['max_dd'],
        'trades': r['trades'],
        'win_rate': r['win_rate'],
        'tp_rate': r['tp_rate']
    } for r in results])
    summary.to_csv('results/pi_strategy_summary.csv', index=False)
    print(f"✅ Saved summary to results/pi_strategy_summary.csv")

print("\n✅ Analysis complete!\n")
