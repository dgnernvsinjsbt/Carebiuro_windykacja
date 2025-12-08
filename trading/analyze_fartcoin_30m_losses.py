"""
Analyze FARTCOIN 30M losing trades to identify filters that eliminate losses
while preserving winning trades
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def calculate_ema(df, span):
    return df['close'].ewm(span=span, adjust=False).mean()

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    tr = ranges.max(axis=1)
    return tr.rolling(period).mean()

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Load data
df = pd.read_csv('fartcoin_30m_jan2025.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print("="*100)
print("FARTCOIN 30M LOSING TRADE ANALYSIS")
print("="*100)
print(f"\nData: {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")

# Calculate all indicators
df['ema_3'] = calculate_ema(df, 3)
df['ema_15'] = calculate_ema(df, 15)
df['ema_50'] = calculate_ema(df, 50)
df['ema_100'] = calculate_ema(df, 100)

# Momentum
df['momentum_7d'] = df['close'].pct_change(336) * 100  # 7 days
df['momentum_14d'] = df['close'].pct_change(672) * 100  # 14 days

# Volatility indicators
df['atr'] = calculate_atr(df)
df['atr_pct'] = (df['atr'] / df['close']) * 100

# RSI
df['rsi'] = calculate_rsi(df)

# Volume
df['volume_ma'] = df['volume'].rolling(50).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma']

# Bollinger Bands
df['bb_mid'] = df['close'].rolling(20).mean()
bb_std = df['close'].rolling(20).std()
df['bb_upper'] = df['bb_mid'] + 2 * bb_std
df['bb_lower'] = df['bb_mid'] - 2 * bb_std
df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid'] * 100

# Price position relative to EMAs
df['above_ema50'] = df['close'] > df['ema_50']
df['above_ema100'] = df['close'] > df['ema_100']

# Current strategy filter
df['allow_short'] = (df['momentum_7d'] < 5) & (df['momentum_14d'] < 10)

# Run original strategy to get trades
trades = []
in_position = False
entry_price = 0
entry_date = None
entry_idx = 0
stop_loss = 0
take_profit = 0
fee = 0.0001

for i in range(1, len(df)):
    row = df.iloc[i]
    prev_row = df.iloc[i-1]

    if not in_position:
        if (row['ema_3'] < row['ema_15'] and
            prev_row['ema_3'] >= prev_row['ema_15'] and
            row['allow_short']):

            in_position = True
            entry_price = row['close']
            entry_date = row['timestamp']
            entry_idx = i
            stop_loss = entry_price * 1.03
            take_profit = entry_price * 0.95
    else:
        exit_type = None
        exit_price = None

        if row['high'] >= stop_loss:
            exit_price = stop_loss
            exit_type = 'SL'
            pnl = (entry_price - stop_loss) / entry_price - fee
        elif row['low'] <= take_profit:
            exit_price = take_profit
            exit_type = 'TP'
            pnl = (entry_price - take_profit) / entry_price - fee

        if exit_type:
            # Capture entry conditions
            entry_row = df.iloc[entry_idx]
            trades.append({
                'entry_date': entry_date,
                'exit_date': row['timestamp'],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl_pct': pnl * 100,
                'exit_type': exit_type,
                'win': pnl > 0,
                # Entry conditions
                'entry_rsi': entry_row['rsi'],
                'entry_atr_pct': entry_row['atr_pct'],
                'entry_volume_ratio': entry_row['volume_ratio'],
                'entry_bb_width': entry_row['bb_width'],
                'entry_above_ema50': entry_row['above_ema50'],
                'entry_above_ema100': entry_row['above_ema100'],
                'entry_momentum_7d': entry_row['momentum_7d'],
                'entry_momentum_14d': entry_row['momentum_14d'],
            })
            in_position = False

trades_df = pd.DataFrame(trades)

print("\n" + "="*100)
print("ORIGINAL STRATEGY RESULTS")
print("="*100)
print(f"Total Trades: {len(trades_df)}")
print(f"Winners: {len(trades_df[trades_df['win']])} ({len(trades_df[trades_df['win']])/len(trades_df)*100:.1f}%)")
print(f"Losers: {len(trades_df[~trades_df['win']])} ({len(trades_df[~trades_df['win']])/len(trades_df)*100:.1f}%)")
print(f"Total Return: {trades_df['pnl_pct'].sum():.2f}%")

# Analyze differences between winners and losers
winners = trades_df[trades_df['win']]
losers = trades_df[~trades_df['win']]

print("\n" + "="*100)
print("WINNERS vs LOSERS - ENTRY CONDITIONS")
print("="*100)

metrics = [
    ('RSI', 'entry_rsi'),
    ('ATR %', 'entry_atr_pct'),
    ('Volume Ratio', 'entry_volume_ratio'),
    ('BB Width %', 'entry_bb_width'),
    ('7d Momentum', 'entry_momentum_7d'),
    ('14d Momentum', 'entry_momentum_14d'),
]

print(f"\n{'Metric':<20} {'Winners (avg)':<15} {'Losers (avg)':<15} {'Difference':<15}")
print("-"*65)

filter_candidates = []

for name, col in metrics:
    w_avg = winners[col].mean()
    l_avg = losers[col].mean()
    diff = w_avg - l_avg
    print(f"{name:<20} {w_avg:<15.2f} {l_avg:<15.2f} {diff:<15.2f}")

    # Identify potential filters
    if abs(diff) > 0:  # Any difference
        filter_candidates.append({
            'name': name,
            'col': col,
            'w_avg': w_avg,
            'l_avg': l_avg,
            'diff': diff
        })

# Test additional filters
print("\n" + "="*100)
print("TESTING ADDITIONAL FILTERS")
print("="*100)

def test_filter(trades_df, filter_name, filter_func):
    """Test a filter and return results"""
    filtered = trades_df[filter_func(trades_df)]

    if len(filtered) == 0:
        return None

    total_return = filtered['pnl_pct'].sum()
    win_rate = len(filtered[filtered['win']]) / len(filtered) * 100
    trades_kept = len(filtered)
    trades_removed = len(trades_df) - len(filtered)
    winners_kept = len(filtered[filtered['win']])
    losers_removed = len(trades_df[~trades_df['win']]) - len(filtered[~filtered['win']])

    return {
        'filter': filter_name,
        'trades': trades_kept,
        'removed': trades_removed,
        'return': total_return,
        'win_rate': win_rate,
        'winners_kept': winners_kept,
        'losers_removed': losers_removed,
    }

# Define filters to test
filters = [
    ('RSI < 60', lambda df: df['entry_rsi'] < 60),
    ('RSI < 55', lambda df: df['entry_rsi'] < 55),
    ('RSI < 50', lambda df: df['entry_rsi'] < 50),
    ('ATR% < 6', lambda df: df['entry_atr_pct'] < 6),
    ('ATR% < 5', lambda df: df['entry_atr_pct'] < 5),
    ('ATR% < 4', lambda df: df['entry_atr_pct'] < 4),
    ('Volume > 0.7x', lambda df: df['entry_volume_ratio'] > 0.7),
    ('Volume > 0.8x', lambda df: df['entry_volume_ratio'] > 0.8),
    ('Volume > 1.0x', lambda df: df['entry_volume_ratio'] > 1.0),
    ('BB Width < 15%', lambda df: df['entry_bb_width'] < 15),
    ('BB Width < 12%', lambda df: df['entry_bb_width'] < 12),
    ('BB Width < 10%', lambda df: df['entry_bb_width'] < 10),
    ('Below EMA50', lambda df: ~df['entry_above_ema50']),
    ('Below EMA100', lambda df: ~df['entry_above_ema100']),
    ('Mom7d < 0%', lambda df: df['entry_momentum_7d'] < 0),
    ('Mom7d < -5%', lambda df: df['entry_momentum_7d'] < -5),
    ('Mom14d < 0%', lambda df: df['entry_momentum_14d'] < 0),
    ('Mom14d < -5%', lambda df: df['entry_momentum_14d'] < -5),
]

results = []
for name, func in filters:
    result = test_filter(trades_df, name, func)
    if result:
        results.append(result)

results_df = pd.DataFrame(results)
results_df['return_improvement'] = results_df['return'] - trades_df['pnl_pct'].sum()
results_df['efficiency'] = results_df['losers_removed'] / results_df['removed'] if len(results_df) > 0 else 0
results_df = results_df.sort_values('return', ascending=False)

print(f"\n{'Filter':<18} {'Trades':<8} {'Removed':<9} {'Return':<10} {'WinRate':<10} {'L.Removed':<11} {'Efficiency':<12}")
print("-"*100)

for _, row in results_df.head(15).iterrows():
    eff = row['efficiency'] * 100 if row['removed'] > 0 else 0
    print(f"{row['filter']:<18} {row['trades']:<8.0f} {row['removed']:<9.0f} {row['return']:<9.1f}% {row['win_rate']:<9.1f}% {row['losers_removed']:<11.0f} {eff:<11.1f}%")

print("\n" + "="*100)
print("BEST FILTERS (by return improvement)")
print("="*100)

best = results_df.head(5)
for idx, row in best.iterrows():
    print(f"\n{row['filter']}:")
    print(f"  Return: {row['return']:.2f}% (original: {trades_df['pnl_pct'].sum():.2f}%)")
    print(f"  Improvement: {row['return_improvement']:+.2f}%")
    print(f"  Trades: {row['trades']:.0f}/{len(trades_df)} ({row['trades']/len(trades_df)*100:.1f}% kept)")
    print(f"  Win Rate: {row['win_rate']:.1f}%")
    print(f"  Losers Removed: {row['losers_removed']:.0f}/{len(losers)} ({row['losers_removed']/len(losers)*100:.1f}%)")

# Save detailed analysis
trades_df.to_csv('results/fartcoin_30m_trade_analysis.csv', index=False)
results_df.to_csv('results/fartcoin_30m_filter_tests.csv', index=False)

print("\n✓ Saved detailed analysis to results/")
print("="*100)
