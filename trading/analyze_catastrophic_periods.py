#!/usr/bin/env python3
"""
Analyze the catastrophic drawdown periods to identify what conditions caused them
Goal: Find filters that would have stopped trading during March 2025 wipeout
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Load data and trades
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv')
trades_df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_optimal_filter.csv')

# Convert timestamps
df['timestamp'] = pd.to_datetime(df['timestamp'])
trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])

# Identify worst periods
trades_df['week'] = trades_df['entry_time'].dt.to_period('W')
weekly = trades_df.groupby('week').agg({
    'pnl_pct': ['count', 'sum', 'mean'],
    'winner': 'mean'
}).round(2)

weekly.columns = ['Trades', 'Total P&L %', 'Avg P&L %', 'Win Rate']
worst_weeks = weekly.nsmallest(5, 'Total P&L %')

print("=" * 80)
print("WORST PERFORMING WEEKS")
print("=" * 80)
print(worst_weeks)

# Focus on the catastrophic March period
march_trades = trades_df[(trades_df['entry_time'] >= '2025-03-10') &
                         (trades_df['entry_time'] <= '2025-03-30')]

print("\n" + "=" * 80)
print("MARCH 2025 CATASTROPHIC PERIOD ANALYSIS")
print("=" * 80)
print(f"\nTotal Trades: {len(march_trades)}")
print(f"Total P&L: {march_trades['pnl_pct'].sum():.2f}%")
print(f"Win Rate: {march_trades['winner'].mean()*100:.1f}%")
print(f"\nRegime Distribution:")
print(march_trades['regime_type'].value_counts())

# Get market conditions during March
march_bars = df[(df['timestamp'] >= '2025-03-10') & (df['timestamp'] <= '2025-03-30')]

# Calculate indicators
def calculate_ema(prices, period):
    return prices.ewm(span=period, adjust=False).mean()

df['ema5'] = calculate_ema(df['close'], 5)
df['ema20'] = calculate_ema(df['close'], 20)
df['ema50'] = calculate_ema(df['close'], 50)
df['ema100'] = calculate_ema(df['close'], 100)
df['ema200'] = calculate_ema(df['close'], 200)

# Volatility
df['returns'] = df['close'].pct_change()
df['volatility_20'] = df['returns'].rolling(20).std() * 100
df['volatility_50'] = df['returns'].rolling(50).std() * 100

# ATR
high_low = df['high'] - df['low']
high_close = np.abs(df['high'] - df['close'].shift())
low_close = np.abs(df['low'] - df['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = tr.rolling(14).mean()
df['atr_pct'] = df['atr'] / df['close'] * 100

# Volume (if available)
if 'volume' in df.columns:
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']

# Price momentum
df['momentum_5d'] = df['close'].pct_change(20) * 100  # 5 days = 20 bars at 15m
df['momentum_10d'] = df['close'].pct_change(40) * 100

# Trend strength (ADX-like concept)
df['price_vs_ema50'] = (df['close'] - df['ema50']) / df['ema50'] * 100
df['price_vs_ema100'] = (df['close'] - df['ema100']) / df['ema100'] * 100
df['price_vs_ema200'] = (df['close'] - df['ema200']) / df['ema200'] * 100

# EMA slopes
df['ema50_slope'] = df['ema50'].pct_change(20) * 100
df['ema100_slope'] = df['ema100'].pct_change(20) * 100

march_bars_analyzed = df[(df['timestamp'] >= '2025-03-10') & (df['timestamp'] <= '2025-03-30')]

print("\n" + "=" * 80)
print("MARKET CONDITIONS DURING MARCH CATASTROPHE")
print("=" * 80)

print(f"\nPrice Movement:")
print(f"  Start: ${march_bars_analyzed['close'].iloc[0]:.4f}")
print(f"  End: ${march_bars_analyzed['close'].iloc[-1]:.4f}")
print(f"  Change: {(march_bars_analyzed['close'].iloc[-1]/march_bars_analyzed['close'].iloc[0]-1)*100:+.1f}%")

print(f"\nVolatility:")
print(f"  Avg 20-bar volatility: {march_bars_analyzed['volatility_20'].mean():.2f}%")
print(f"  Max 20-bar volatility: {march_bars_analyzed['volatility_20'].max():.2f}%")
print(f"  Avg ATR%: {march_bars_analyzed['atr_pct'].mean():.2f}%")

print(f"\nTrend Indicators:")
print(f"  Avg price vs EMA50: {march_bars_analyzed['price_vs_ema50'].mean():+.1f}%")
print(f"  Avg price vs EMA100: {march_bars_analyzed['price_vs_ema100'].mean():+.1f}%")
print(f"  Avg EMA50 slope: {march_bars_analyzed['ema50_slope'].mean():+.2f}%")
print(f"  Avg EMA100 slope: {march_bars_analyzed['ema100_slope'].mean():+.2f}%")

if 'volume_ratio' in march_bars_analyzed.columns:
    print(f"\nVolume:")
    print(f"  Avg volume ratio: {march_bars_analyzed['volume_ratio'].mean():.2f}x")

# Now analyze ALL trades and their entry conditions
print("\n" + "=" * 80)
print("COMPARING WINNING VS LOSING TRADE CONDITIONS")
print("=" * 80)

# Merge trades with market data at entry time
trades_with_conditions = []

for idx, trade in trades_df.iterrows():
    entry_time = trade['entry_time']
    entry_idx = trade['entry_idx']

    # Find corresponding market conditions
    if entry_idx < len(df):
        market_row = df.iloc[entry_idx]

        trades_with_conditions.append({
            'pnl_pct': trade['pnl_pct'],
            'winner': trade['winner'],
            'regime_type': trade['regime_type'],
            'volatility_20': market_row['volatility_20'],
            'atr_pct': market_row['atr_pct'],
            'price_vs_ema50': market_row['price_vs_ema50'],
            'price_vs_ema100': market_row['price_vs_ema100'],
            'price_vs_ema200': market_row['price_vs_ema200'],
            'ema50_slope': market_row['ema50_slope'],
            'ema100_slope': market_row['ema100_slope'],
            'momentum_5d': market_row['momentum_5d'],
            'momentum_10d': market_row['momentum_10d'],
        })

conditions_df = pd.DataFrame(trades_with_conditions)

winners = conditions_df[conditions_df['winner'] == True]
losers = conditions_df[conditions_df['winner'] == False]

print(f"\nWinners (n={len(winners)}):")
print(f"  Volatility 20: {winners['volatility_20'].mean():.2f}% (std: {winners['volatility_20'].std():.2f})")
print(f"  ATR%: {winners['atr_pct'].mean():.2f}%")
print(f"  Price vs EMA100: {winners['price_vs_ema100'].mean():+.1f}%")
print(f"  EMA50 slope: {winners['ema50_slope'].mean():+.2f}%")
print(f"  EMA100 slope: {winners['ema100_slope'].mean():+.2f}%")
print(f"  5-day momentum: {winners['momentum_5d'].mean():+.1f}%")

print(f"\nLosers (n={len(losers)}):")
print(f"  Volatility 20: {losers['volatility_20'].mean():.2f}% (std: {losers['volatility_20'].std():.2f})")
print(f"  ATR%: {losers['atr_pct'].mean():.2f}%")
print(f"  Price vs EMA100: {losers['price_vs_ema100'].mean():+.1f}%")
print(f"  EMA50 slope: {losers['ema50_slope'].mean():+.2f}%")
print(f"  EMA100 slope: {losers['ema100_slope'].mean():+.2f}%")
print(f"  5-day momentum: {losers['momentum_5d'].mean():+.1f}%")

# Identify conditions that predict losses
print("\n" + "=" * 80)
print("PROPOSED FILTERS TO REDUCE DRAWDOWN")
print("=" * 80)

print("\n1. EMA Alignment Filter:")
print("   Problem: Losses occur when EMA50 > EMA100 (uptrend)")
print(f"   Winners with EMA50 < EMA100: {len(winners[winners['price_vs_ema100'] < 0])/len(winners)*100:.1f}%")
print(f"   Losers with EMA50 < EMA100: {len(losers[losers['price_vs_ema100'] < 0])/len(losers)*100:.1f}%")
print("   ✅ Filter: Only trade when price < EMA100 AND EMA50 < EMA100")

print("\n2. Strong Trend Filter:")
print("   Problem: Losses in choppy/weak trends")
print(f"   Winners with strong downtrend (price < EMA100 by >5%): {len(winners[winners['price_vs_ema100'] < -5])/len(winners)*100:.1f}%")
print(f"   Losers with strong downtrend: {len(losers[losers['price_vs_ema100'] < -5])/len(losers)*100:.1f}%")
print("   ✅ Filter: Only trade when price < EMA100 by at least 3%")

print("\n3. EMA Slope Confirmation:")
print("   Problem: Losses when EMAs are rising or flat")
print(f"   Winners with declining EMA100 (slope < -0.5%): {len(winners[winners['ema100_slope'] < -0.5])/len(winners)*100:.1f}%")
print(f"   Losers with declining EMA100: {len(losers[losers['ema100_slope'] < -0.5])/len(losers)*100:.1f}%")
print("   ✅ Filter: Only trade when EMA100 slope < -0.3%")

print("\n4. Momentum Filter:")
print("   Problem: Losses when recent momentum is positive")
print(f"   Winners with negative 5-day momentum: {len(winners[winners['momentum_5d'] < 0])/len(winners)*100:.1f}%")
print(f"   Losers with negative 5-day momentum: {len(losers[losers['momentum_5d'] < 0])/len(losers)*100:.1f}%")
print("   ✅ Filter: Only trade when 5-day momentum < -5%")

print("\n5. Volatility Filter:")
print("   Problem: Need sufficient volatility for TP targets")
print(f"   Winners ATR% > 2%: {len(winners[winners['atr_pct'] > 2])/len(winners)*100:.1f}%")
print(f"   Losers ATR% > 2%: {len(losers[losers['atr_pct'] > 2])/len(losers)*100:.1f}%")
print("   ✅ Filter: Only trade when ATR% > 2.5%")

# Calculate how many trades would be filtered
print("\n" + "=" * 80)
print("FILTER EFFECTIVENESS SIMULATION")
print("=" * 80)

# Test combined filters
filtered_winners = winners[
    (winners['price_vs_ema100'] < -3) &
    (winners['ema100_slope'] < -0.3) &
    (winners['momentum_5d'] < -5) &
    (winners['atr_pct'] > 2.5)
]

filtered_losers = losers[
    (losers['price_vs_ema100'] < -3) &
    (losers['ema100_slope'] < -0.3) &
    (losers['momentum_5d'] < -5) &
    (losers['atr_pct'] > 2.5)
]

total_filtered = len(filtered_winners) + len(filtered_losers)
filtered_win_rate = len(filtered_winners) / total_filtered * 100 if total_filtered > 0 else 0

print(f"\nWith ALL filters combined:")
print(f"  Winners kept: {len(filtered_winners)} of {len(winners)} ({len(filtered_winners)/len(winners)*100:.1f}%)")
print(f"  Losers kept: {len(filtered_losers)} of {len(losers)} ({len(filtered_losers)/len(losers)*100:.1f}%)")
print(f"  Total trades kept: {total_filtered} of {len(conditions_df)} ({total_filtered/len(conditions_df)*100:.1f}%)")
print(f"  New win rate: {filtered_win_rate:.1f}%")
print(f"  Estimated return: {(filtered_winners['pnl_pct'].sum() + filtered_losers['pnl_pct'].sum()):.2f}%")