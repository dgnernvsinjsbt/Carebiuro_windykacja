#!/usr/bin/env python3
"""
PI/USDT Final Strategy - Ultra-Selective Scalping
==================================================
Based on deep dive findings:
- RSI extremes (weak but present edge)
- Volume spikes >5x (rare but strong)
- Mean reversion in strong trends
- Three-bar patterns

Strategy: Combine ALL filters for ultra-selectivity
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Load data
df = pd.read_csv('pi_30d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
df['returns'] = (df['close'] - df['open']) / df['open'] * 100
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100

# Volume
df['volume_ma_30'] = df['volume'].rolling(30).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma_30']

# ATR
df['tr'] = df[['high', 'low']].apply(lambda x: x['high'] - x['low'], axis=1)
df['atr_14'] = df['tr'].rolling(14).mean()
df['atr_pct'] = df['atr_14'] / df['close'] * 100

# EMA
df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
df['ema_dist_pct'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi_14'] = 100 - (100 / (1 + rs))

# Multi-bar patterns
df['up_bar'] = (df['close'] > df['open']).astype(int)
df['down_bar'] = (df['close'] < df['open']).astype(int)

print("="*70)
print("PI/USDT ULTRA-SELECTIVE SCALPING STRATEGY")
print("="*70)

def backtest_strategy(df, config):
    """Backtest ultra-selective strategy"""
    trades = []

    for i in range(100, len(df) - config['max_hold']):
        row = df.iloc[i]

        # LONG CONDITIONS (Buy Panic)
        long_signal = False
        if (pd.notna(row['rsi_14']) and row['rsi_14'] < config['rsi_oversold'] and
            pd.notna(row['volume_ratio']) and row['volume_ratio'] >= config['min_volume'] and
            pd.notna(row['ema_dist_pct']) and row['ema_dist_pct'] < -config['min_ema_dist']):

            # Check if preceded by down bars
            prev_bars = df.iloc[i-2:i+1]
            if len(prev_bars[prev_bars['down_bar'] == 1]) >= 2:  # At least 2 of last 3 down
                long_signal = True

        # SHORT CONDITIONS (Sell Euphoria)
        short_signal = False
        if (pd.notna(row['rsi_14']) and row['rsi_14'] > config['rsi_overbought'] and
            pd.notna(row['volume_ratio']) and row['volume_ratio'] >= config['min_volume'] and
            pd.notna(row['ema_dist_pct']) and row['ema_dist_pct'] > config['min_ema_dist']):

            # Check if preceded by up bars
            prev_bars = df.iloc[i-2:i+1]
            if len(prev_bars[prev_bars['up_bar'] == 1]) >= 2:  # At least 2 of last 3 up
                short_signal = True

        if not (long_signal or short_signal):
            continue

        # Entry
        if long_signal:
            direction = 'LONG'
            entry_price = row['close']
            tp_price = entry_price * (1 + config['tp_pct']/100)
            sl_price = entry_price * (1 - config['sl_pct']/100)
        else:
            direction = 'SHORT'
            entry_price = row['close']
            tp_price = entry_price * (1 - config['tp_pct']/100)
            sl_price = entry_price * (1 + config['sl_pct']/100)

        # Simulate trade
        exit_bar = i + 1
        exit_reason = 'TIME'

        for j in range(i+1, min(i+config['max_hold']+1, len(df))):
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
            'timestamp': df.iloc[i]['timestamp'],
            'entry_bar': i,
            'exit_bar': exit_bar,
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason,
            'rsi': row['rsi_14'],
            'volume_ratio': row['volume_ratio'],
            'ema_dist': row['ema_dist_pct']
        })

    return pd.DataFrame(trades) if trades else None

# ==================== TEST CONFIGURATIONS ====================

configs = [
    # (rsi_oversold, rsi_overbought, min_volume, min_ema_dist, tp_pct, sl_pct, max_hold)
    {'name': 'Moderate', 'rsi_oversold': 30, 'rsi_overbought': 70, 'min_volume': 2.0, 'min_ema_dist': 0.3, 'tp_pct': 0.5, 'sl_pct': 0.3, 'max_hold': 30},
    {'name': 'Selective', 'rsi_oversold': 25, 'rsi_overbought': 75, 'min_volume': 3.0, 'min_ema_dist': 0.5, 'tp_pct': 0.6, 'sl_pct': 0.3, 'max_hold': 40},
    {'name': 'Ultra', 'rsi_oversold': 20, 'rsi_overbought': 80, 'min_volume': 4.0, 'min_ema_dist': 0.7, 'tp_pct': 0.8, 'sl_pct': 0.4, 'max_hold': 50},
    {'name': 'Extreme', 'rsi_oversold': 15, 'rsi_overbought': 85, 'min_volume': 5.0, 'min_ema_dist': 1.0, 'tp_pct': 1.0, 'sl_pct': 0.5, 'max_hold': 60},
]

results = []

for config in configs:
    trades_df = backtest_strategy(df, config)

    if trades_df is not None and len(trades_df) >= 5:
        total_return = trades_df['pnl_pct'].sum()

        cumulative = (1 + trades_df['pnl_pct']/100).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max * 100
        max_dd = abs(drawdown.min())

        return_dd = total_return / max_dd if max_dd > 0 else 0

        win_rate = (trades_df['pnl_pct'] > 0).mean() * 100
        tp_rate = (trades_df['exit_reason'] == 'TP').mean() * 100

        avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if len(trades_df[trades_df['pnl_pct'] > 0]) > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if len(trades_df[trades_df['pnl_pct'] < 0]) > 0 else 0

        # Count LONG vs SHORT
        long_pnl = trades_df[trades_df['direction'] == 'LONG']['pnl_pct'].sum()
        short_pnl = trades_df[trades_df['direction'] == 'SHORT']['pnl_pct'].sum()

        results.append({
            'name': config['name'],
            'config': config,
            'trades': len(trades_df),
            'return': total_return,
            'max_dd': max_dd,
            'return_dd': return_dd,
            'win_rate': win_rate,
            'tp_rate': tp_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'long_pnl': long_pnl,
            'short_pnl': short_pnl,
            'trades_df': trades_df
        })
    else:
        print(f"❌ {config['name']}: Not enough trades (< 5)")

# ==================== RESULTS ====================

print("\n" + "="*70)
print("RESULTS")
print("="*70 + "\n")

if results:
    results.sort(key=lambda x: x['return_dd'], reverse=True)

    for i, r in enumerate(results, 1):
        print(f"{i}. {r['name'].upper()}")
        print(f"   Return/DD: {r['return_dd']:.2f}x | Return: {r['return']:+.2f}% | Max DD: {r['max_dd']:.2f}%")
        print(f"   Trades: {r['trades']} | Win: {r['win_rate']:.1f}% | TP: {r['tp_rate']:.1f}%")
        print(f"   Avg Win: {r['avg_win']:+.2f}% | Avg Loss: {r['avg_loss']:+.2f}%")
        print(f"   LONG PnL: {r['long_pnl']:+.2f}% | SHORT PnL: {r['short_pnl']:+.2f}%")
        print()

    # Save best strategy
    if results[0]['return_dd'] > 0:
        best = results[0]
        best['trades_df'].to_csv('results/pi_ultra_selective_trades.csv', index=False)
        print(f"✅ Saved best strategy trades to results/pi_ultra_selective_trades.csv")

        # Analyze winners vs losers
        winners = best['trades_df'][best['trades_df']['pnl_pct'] > 0]
        losers = best['trades_df'][best['trades_df']['pnl_pct'] < 0]

        print("\n" + "-"*70)
        print("WINNER vs LOSER ANALYSIS")
        print("-"*70)

        print(f"\nWINNERS ({len(winners)}):")
        print(f"  Avg RSI: {winners['rsi'].mean():.1f}")
        print(f"  Avg Volume Ratio: {winners['volume_ratio'].mean():.2f}x")
        print(f"  Avg EMA Dist: {winners['ema_dist'].abs().mean():.3f}%")
        print(f"  LONG: {len(winners[winners['direction']=='LONG'])} | SHORT: {len(winners[winners['direction']=='SHORT'])}")

        print(f"\nLOSERS ({len(losers)}):")
        print(f"  Avg RSI: {losers['rsi'].mean():.1f}")
        print(f"  Avg Volume Ratio: {losers['volume_ratio'].mean():.2f}x")
        print(f"  Avg EMA Dist: {losers['ema_dist'].abs().mean():.3f}%")
        print(f"  LONG: {len(losers[losers['direction']=='LONG'])} | SHORT: {len(losers[losers['direction']=='SHORT'])}")

    else:
        print("❌ No profitable configuration found.\n")

else:
    print("❌ No configurations generated enough trades.\n")

print("="*70 + "\n")
