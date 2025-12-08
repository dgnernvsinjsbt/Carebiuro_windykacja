#!/usr/bin/env python3
"""
PENGU Optimized Short Strategy
Best SL/TP + Best Filters
"""

import pandas as pd
import numpy as np

def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    return prices.ewm(span=period, adjust=False).mean()

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

# Load data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/pengu_15m_3months.csv')

# Calculate indicators
df['ema5'] = calculate_ema(df['close'], 5)
df['ema20'] = calculate_ema(df['close'], 20)
df['ema50'] = calculate_ema(df['close'], 50)
df['atr'] = calculate_atr(df, 14)

# Price position
df['high_20'] = df['high'].rolling(20).max()
df['low_20'] = df['low'].rolling(20).min()
df['price_position'] = (df['close'] - df['low_20']) / (df['high_20'] - df['low_20'])

# Candle characteristics
df['upper_wick'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close'] * 100

# Trend
df['trend'] = (df['ema5'] - df['ema50']) / df['close'] * 100

# Signal
df['signal'] = 0
df.loc[(df['ema5'] < df['ema20']) & (df['ema5'].shift(1) >= df['ema20'].shift(1)), 'signal'] = -1

# Best configs to test
configs = [
    {'name': 'Baseline (no filters)', 'sl': 0.01, 'tp': 0.025, 'filters': {}},
    {'name': 'Best SL/TP only', 'sl': 0.01, 'tp': 0.025, 'filters': {}},
    {'name': '+ Price mid-range', 'sl': 0.01, 'tp': 0.025, 'filters': {'price_mid': True}},
    {'name': '+ Upper wick > 0.3%', 'sl': 0.01, 'tp': 0.025, 'filters': {'upper_wick': True}},
    {'name': '+ Both filters', 'sl': 0.01, 'tp': 0.025, 'filters': {'price_mid': True, 'upper_wick': True}},
    {'name': 'Max return (5% SL/TP)', 'sl': 0.05, 'tp': 0.05, 'filters': {}},
]

print("=" * 80)
print("PENGU OPTIMIZED SHORT STRATEGY")
print("=" * 80)
print(f"\n{'Config':<30} {'Trades':<8} {'Win%':<8} {'Return':<10} {'MaxDD':<8} {'R:R':<8}")
print("-" * 80)

results = []

for config in configs:
    equity = 1.0
    max_equity = 1.0
    trades = []

    in_position = False
    entry_price = 0

    for i in range(50, len(df)):
        row = df.iloc[i]

        if not in_position:
            if row['signal'] == -1:
                # Apply filters
                if config['filters'].get('price_mid') and not (0.3 <= row['price_position'] <= 0.7):
                    continue
                if config['filters'].get('upper_wick') and row['upper_wick'] <= 0.3:
                    continue

                in_position = True
                entry_price = row['close']
                stop_loss = entry_price * (1 + config['sl'])
                take_profit = entry_price * (1 - config['tp'])
        else:
            exit_price = None
            exit_reason = None

            if row['high'] >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'SL'
            elif row['low'] <= take_profit:
                exit_price = take_profit
                exit_reason = 'TP'

            if exit_price:
                pnl_pct = (entry_price - exit_price) / entry_price
                net_pnl = pnl_pct - 0.0001  # 0.01% fees

                equity *= (1 + net_pnl)
                max_equity = max(max_equity, equity)

                trades.append({
                    'pnl': net_pnl * 100,
                    'winner': net_pnl > 0,
                    'equity': equity,
                    'exit_reason': exit_reason
                })

                in_position = False

    if len(trades) > 0:
        trades_df = pd.DataFrame(trades)
        wins = trades_df['winner'].sum()
        win_rate = wins / len(trades) * 100
        total_return = (equity - 1) * 100

        # Calculate max DD
        eq_curve = [1.0] + list(trades_df['equity'])
        max_dd = 0
        peak = 1.0
        for eq in eq_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            max_dd = max(max_dd, dd)

        risk_reward = total_return / max_dd if max_dd > 0 else 0

        results.append({
            'config': config['name'],
            'trades': len(trades),
            'win_rate': win_rate,
            'return': total_return,
            'max_dd': max_dd,
            'risk_reward': risk_reward
        })

        print(f"{config['name']:<30} {len(trades):<8} {win_rate:<7.1f}% {total_return:<+9.2f}% {max_dd:<7.1f}% {risk_reward:<7.2f}x")

print("\n" + "=" * 80)
print("FINAL RECOMMENDATION")
print("=" * 80)

best = max(results, key=lambda x: x['risk_reward'])
print(f"\nBest config: {best['config']}")
print(f"  Return: {best['return']:+.2f}%")
print(f"  Max Drawdown: {best['max_dd']:.2f}%")
print(f"  Risk:Reward: {best['risk_reward']:.2f}x")
print(f"  Trades: {best['trades']}")
print(f"  Win Rate: {best['win_rate']:.1f}%")

print(f"\nWith this drawdown, you could use:")
print(f"  - 3x leverage → {best['return'] * 3:+.0f}% return, {best['max_dd'] * 3:.1f}% max DD")
print(f"  - 5x leverage → {best['return'] * 5:+.0f}% return, {best['max_dd'] * 5:.1f}% max DD")
print(f"  - 10x leverage → {best['return'] * 10:+.0f}% return, {best['max_dd'] * 10:.1f}% max DD")