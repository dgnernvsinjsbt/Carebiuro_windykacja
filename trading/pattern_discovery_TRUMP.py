"""
TRUMP Pattern Discovery Analysis
Deep pattern analysis to discover exploitable trading edges
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import matplotlib.pyplot as plt
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("TRUMP CRYPTOCURRENCY - DEEP PATTERN DISCOVERY")
print("="*80)
print()

# Load data
print("[1/7] Loading data...")
df = pd.read_csv('./trump_usdt_1m_mexc.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate returns and indicators
df['return'] = (df['close'] - df['open']) / df['open'] * 100
df['body_pct'] = abs(df['close'] - df['open']) / df['open'] * 100
df['upper_wick'] = df['high'] - df[['close', 'open']].max(axis=1)
df['lower_wick'] = df[['close', 'open']].min(axis=1) - df['low']
df['range_pct'] = (df['high'] - df['low']) / df['low'] * 100
df['is_green'] = (df['close'] > df['open']).astype(int)

# Calculate technical indicators
df['sma_20'] = df['close'].rolling(20).mean()
df['sma_50'] = df['close'].rolling(50).mean()
df['sma_200'] = df['close'].rolling(200).mean()
df['ema_12'] = df['close'].ewm(span=12).mean()
df['ema_26'] = df['close'].ewm(span=26).mean()

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# ATR
high_low = df['high'] - df['low']
high_close = abs(df['high'] - df['close'].shift())
low_close = abs(df['low'] - df['close'].shift())
true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
df['atr'] = true_range.rolling(14).mean()
df['atr_pct'] = df['atr'] / df['close'] * 100

# Bollinger Bands
df['bb_middle'] = df['close'].rolling(20).mean()
bb_std = df['close'].rolling(20).std()
df['bb_upper'] = df['bb_middle'] + 2 * bb_std
df['bb_lower'] = df['bb_middle'] - 2 * bb_std
df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

# Volume analysis
df['volume_ma'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma']

# Time features
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek
df['day_name'] = df['timestamp'].dt.day_name()

print(f"Data loaded: {len(df):,} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Date range: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
print()

# Define sessions
def get_session(hour):
    if 0 <= hour < 8:
        return 'Asia'
    elif 8 <= hour < 14:
        return 'Europe'
    elif 14 <= hour < 21:
        return 'US'
    else:
        return 'Overnight'

df['session'] = df['hour'].apply(get_session)

# ============================================================================
# 1. SESSION ANALYSIS
# ============================================================================
print("[2/7] Analyzing trading sessions...")
print()

session_stats = []
for session in ['Asia', 'Europe', 'US', 'Overnight']:
    session_df = df[df['session'] == session].copy()

    if len(session_df) == 0:
        continue

    longs = session_df[session_df['return'] > 0]
    shorts = session_df[session_df['return'] < 0]

    stats_dict = {
        'session': session,
        'avg_return': session_df['return'].mean(),
        'volatility_atr': session_df['atr_pct'].mean(),
        'volatility_std': session_df['return'].std(),
        'avg_volume': session_df['volume'].mean(),
        'volume_vs_24h': session_df['volume'].mean() / df['volume'].mean(),
        'long_win_rate': len(longs) / len(session_df) * 100,
        'short_win_rate': len(shorts) / len(session_df) * 100,
        'avg_range': session_df['range_pct'].mean(),
        'total_candles': len(session_df)
    }

    # Find best and worst hours
    hour_returns = session_df.groupby('hour')['return'].mean()
    if len(hour_returns) > 0:
        stats_dict['best_hour'] = hour_returns.idxmax()
        stats_dict['best_hour_return'] = hour_returns.max()
        stats_dict['worst_hour'] = hour_returns.idxmin()
        stats_dict['worst_hour_return'] = hour_returns.min()

    session_stats.append(stats_dict)

session_df_results = pd.DataFrame(session_stats)

# ============================================================================
# 2. SEQUENTIAL PATTERNS (X → Y Analysis)
# ============================================================================
print("[3/7] Discovering sequential patterns...")
print()

sequential_patterns = []

# Pattern 1: Large candle body → next candles
for threshold in [1.0, 1.5, 2.0]:
    large_bodies = df[df['body_pct'] > threshold].index
    if len(large_bodies) > 30:
        next_1_returns = []
        next_3_returns = []
        next_5_returns = []

        for idx in large_bodies:
            if idx + 5 < len(df):
                next_1_returns.append(df.loc[idx+1, 'return'])
                next_3_returns.append(df.loc[idx+1:idx+3, 'return'].sum())
                next_5_returns.append(df.loc[idx+1:idx+5, 'return'].sum())

        sequential_patterns.append({
            'pattern': f'Body >{threshold}%',
            'occurrences': len(large_bodies),
            'next_1_avg': np.mean(next_1_returns),
            'next_3_avg': np.mean(next_3_returns),
            'next_5_avg': np.mean(next_5_returns),
            'next_1_winrate': sum(1 for r in next_1_returns if r > 0) / len(next_1_returns) * 100,
        })

# Pattern 2: Consecutive green/red candles
for num_candles in [3, 4, 5]:
    # Consecutive green
    df['consecutive_green'] = (df['is_green'].rolling(num_candles).sum() == num_candles).astype(int)
    green_streaks = df[df['consecutive_green'] == 1].index

    if len(green_streaks) > 30:
        next_returns = []
        reversals = 0
        for idx in green_streaks:
            if idx + 1 < len(df):
                next_ret = df.loc[idx+1, 'return']
                next_returns.append(next_ret)
                if next_ret < 0:
                    reversals += 1

        sequential_patterns.append({
            'pattern': f'{num_candles} consecutive green',
            'occurrences': len(green_streaks),
            'next_1_avg': np.mean(next_returns),
            'reversal_rate': reversals / len(green_streaks) * 100,
            'continuation_rate': 100 - (reversals / len(green_streaks) * 100),
        })

    # Consecutive red
    df['consecutive_red'] = ((1-df['is_green']).rolling(num_candles).sum() == num_candles).astype(int)
    red_streaks = df[df['consecutive_red'] == 1].index

    if len(red_streaks) > 30:
        next_returns = []
        reversals = 0
        for idx in red_streaks:
            if idx + 1 < len(df):
                next_ret = df.loc[idx+1, 'return']
                next_returns.append(next_ret)
                if next_ret > 0:
                    reversals += 1

        sequential_patterns.append({
            'pattern': f'{num_candles} consecutive red',
            'occurrences': len(red_streaks),
            'next_1_avg': np.mean(next_returns),
            'reversal_rate': reversals / len(red_streaks) * 100,
            'continuation_rate': 100 - (reversals / len(red_streaks) * 100),
        })

# Pattern 3: Wick rejections
df['large_upper_wick'] = df['upper_wick'] > 2 * abs(df['close'] - df['open'])
df['large_lower_wick'] = df['lower_wick'] > 2 * abs(df['close'] - df['open'])

upper_wick_indices = df[df['large_upper_wick']].index
if len(upper_wick_indices) > 30:
    next_returns = [df.loc[idx+1, 'return'] for idx in upper_wick_indices if idx+1 < len(df)]
    sequential_patterns.append({
        'pattern': 'Large upper wick (rejection)',
        'occurrences': len(upper_wick_indices),
        'next_1_avg': np.mean(next_returns),
        'next_1_winrate': sum(1 for r in next_returns if r < 0) / len(next_returns) * 100,
    })

lower_wick_indices = df[df['large_lower_wick']].index
if len(lower_wick_indices) > 30:
    next_returns = [df.loc[idx+1, 'return'] for idx in lower_wick_indices if idx+1 < len(df)]
    sequential_patterns.append({
        'pattern': 'Large lower wick (support)',
        'occurrences': len(lower_wick_indices),
        'next_1_avg': np.mean(next_returns),
        'next_1_winrate': sum(1 for r in next_returns if r > 0) / len(next_returns) * 100,
    })

# Pattern 4: Volume spikes
volume_spike_indices = df[df['volume_ratio'] > 3].index
if len(volume_spike_indices) > 30:
    continuations = 0
    exhaustions = 0
    for idx in volume_spike_indices:
        if idx + 5 < len(df):
            current_direction = 1 if df.loc[idx, 'return'] > 0 else -1
            next_5_sum = df.loc[idx+1:idx+5, 'return'].sum()
            if (current_direction > 0 and next_5_sum > 0) or (current_direction < 0 and next_5_sum < 0):
                continuations += 1
            else:
                exhaustions += 1

    if continuations + exhaustions > 0:
        sequential_patterns.append({
            'pattern': 'Volume spike (>3x avg)',
            'occurrences': len(volume_spike_indices),
            'continuation_rate': continuations / (continuations + exhaustions) * 100,
            'exhaustion_rate': exhaustions / (continuations + exhaustions) * 100,
        })

# Pattern 5: Bollinger Band touches
bb_upper_touches = df[df['close'] >= df['bb_upper']].index
if len(bb_upper_touches) > 30:
    mean_reversions = 0
    for idx in bb_upper_touches:
        if idx + 5 < len(df):
            next_5_low = df.loc[idx+1:idx+5, 'close'].min()
            if next_5_low < df.loc[idx, 'bb_middle']:
                mean_reversions += 1

    sequential_patterns.append({
        'pattern': 'BB upper touch',
        'occurrences': len(bb_upper_touches),
        'mean_reversion_rate': mean_reversions / len(bb_upper_touches) * 100,
    })

bb_lower_touches = df[df['close'] <= df['bb_lower']].index
if len(bb_lower_touches) > 30:
    mean_reversions = 0
    for idx in bb_lower_touches:
        if idx + 5 < len(df):
            next_5_high = df.loc[idx+1:idx+5, 'close'].max()
            if next_5_high > df.loc[idx, 'bb_middle']:
                mean_reversions += 1

    sequential_patterns.append({
        'pattern': 'BB lower touch',
        'occurrences': len(bb_lower_touches),
        'mean_reversion_rate': mean_reversions / len(bb_lower_touches) * 100,
    })

# Pattern 6: ATR expansion/contraction
df['atr_ma'] = df['atr_pct'].rolling(20).mean()
df['atr_ratio'] = df['atr_pct'] / df['atr_ma']

low_vol_indices = df[df['atr_ratio'] < 0.5].index
if len(low_vol_indices) > 30:
    expansions = 0
    for idx in low_vol_indices:
        if idx + 10 < len(df):
            future_atr_max = df.loc[idx+1:idx+10, 'atr_ratio'].max()
            if future_atr_max > 1.5:
                expansions += 1

    sequential_patterns.append({
        'pattern': 'ATR contraction (<0.5x avg)',
        'occurrences': len(low_vol_indices),
        'expansion_follows_rate': expansions / len(low_vol_indices) * 100,
    })

sequential_df = pd.DataFrame(sequential_patterns)

# ============================================================================
# 3. REGIME CLASSIFICATION
# ============================================================================
print("[4/7] Classifying market regimes...")
print()

# Define regimes
df['regime'] = 'CHOPPY'  # default

# TRENDING: Price consistently above/below SMA50, strong directional moves
df.loc[(df['close'] > df['sma_50']) & (df['close'].shift(1) > df['sma_50'].shift(1)) &
       (df['close'].shift(2) > df['sma_50'].shift(2)) & (df['sma_50'] > df['sma_50'].shift(5)), 'regime'] = 'TRENDING_UP'
df.loc[(df['close'] < df['sma_50']) & (df['close'].shift(1) < df['sma_50'].shift(1)) &
       (df['close'].shift(2) < df['sma_50'].shift(2)) & (df['sma_50'] < df['sma_50'].shift(5)), 'regime'] = 'TRENDING_DOWN'

# MEAN-REVERTING: Price oscillating around SMA, RSI in middle range
df.loc[(abs(df['close'] - df['sma_50']) / df['sma_50'] < 0.01) &
       (df['rsi'] > 40) & (df['rsi'] < 60) & (df['atr_ratio'] < 1.2), 'regime'] = 'MEAN_REVERTING'

# EXPLOSIVE: Large body candles with volume spikes
df.loc[(df['body_pct'] > 1.5) & (df['volume_ratio'] > 2.5), 'regime'] = 'EXPLOSIVE'

regime_stats = df['regime'].value_counts()
regime_pct = regime_stats / len(df) * 100

regime_analysis = []
for regime in ['TRENDING_UP', 'TRENDING_DOWN', 'MEAN_REVERTING', 'EXPLOSIVE', 'CHOPPY']:
    regime_df = df[df['regime'] == regime]
    if len(regime_df) > 0:
        regime_analysis.append({
            'regime': regime,
            'pct_of_time': len(regime_df) / len(df) * 100,
            'avg_return': regime_df['return'].mean(),
            'avg_volatility': regime_df['atr_pct'].mean(),
            'total_candles': len(regime_df),
        })

regime_results_df = pd.DataFrame(regime_analysis)

# ============================================================================
# 4. STATISTICAL EDGES
# ============================================================================
print("[5/7] Discovering statistical edges...")
print()

statistical_edges = []

# Day of week patterns
for day in range(7):
    day_df = df[df['day_of_week'] == day]
    if len(day_df) > 100:
        day_name = day_df['day_name'].iloc[0]
        statistical_edges.append({
            'edge_type': 'Day of Week',
            'condition': day_name,
            'avg_return': day_df['return'].mean(),
            'volatility': day_df['return'].std(),
            'sample_size': len(day_df),
            'significance': 'High' if abs(day_df['return'].mean()) > 0.01 else 'Low'
        })

# Hour of day patterns
hourly_returns = df.groupby('hour')['return'].agg(['mean', 'std', 'count'])
for hour in hourly_returns.index:
    if hourly_returns.loc[hour, 'count'] > 100:
        statistical_edges.append({
            'edge_type': 'Hour of Day',
            'condition': f'{hour:02d}:00',
            'avg_return': hourly_returns.loc[hour, 'mean'],
            'volatility': hourly_returns.loc[hour, 'std'],
            'sample_size': hourly_returns.loc[hour, 'count'],
            'significance': 'High' if abs(hourly_returns.loc[hour, 'mean']) > 0.01 else 'Low'
        })

# RSI extremes
rsi_low = df[df['rsi'] < 30]
if len(rsi_low) > 30:
    next_5_returns = []
    for idx in rsi_low.index:
        if idx + 5 < len(df):
            next_5_returns.append(df.loc[idx+1:idx+5, 'return'].sum())
    statistical_edges.append({
        'edge_type': 'RSI Extreme',
        'condition': 'RSI < 30',
        'avg_return': np.mean(next_5_returns),
        'win_rate': sum(1 for r in next_5_returns if r > 0) / len(next_5_returns) * 100,
        'sample_size': len(rsi_low),
        'significance': 'High' if sum(1 for r in next_5_returns if r > 0) / len(next_5_returns) > 0.6 else 'Medium'
    })

rsi_high = df[df['rsi'] > 70]
if len(rsi_high) > 30:
    next_5_returns = []
    for idx in rsi_high.index:
        if idx + 5 < len(df):
            next_5_returns.append(df.loc[idx+1:idx+5, 'return'].sum())
    statistical_edges.append({
        'edge_type': 'RSI Extreme',
        'condition': 'RSI > 70',
        'avg_return': np.mean(next_5_returns),
        'win_rate': sum(1 for r in next_5_returns if r < 0) / len(next_5_returns) * 100,
        'sample_size': len(rsi_high),
        'significance': 'High' if sum(1 for r in next_5_returns if r < 0) / len(next_5_returns) > 0.6 else 'Medium'
    })

statistical_edges_df = pd.DataFrame(statistical_edges)

# ============================================================================
# 5. BEHAVIORAL PROFILE
# ============================================================================
print("[6/7] Creating behavioral profile...")
print()

profile_stats = {
    'avg_daily_range_pct': df.groupby(df['timestamp'].dt.date)['range_pct'].sum().mean(),
    'avg_candle_range_pct': df['range_pct'].mean(),
    'avg_body_pct': df['body_pct'].mean(),
    'explosive_moves_pct': len(df[df['body_pct'] > 2.0]) / len(df) * 100,
    'avg_volume': df['volume'].mean(),
    'volume_consistency_cv': df['volume'].std() / df['volume'].mean(),
    'trending_pct': len(df[df['regime'].str.contains('TRENDING')]) / len(df) * 100,
    'mean_reverting_pct': len(df[df['regime'] == 'MEAN_REVERTING']) / len(df) * 100,
    'choppy_pct': len(df[df['regime'] == 'CHOPPY']) / len(df) * 100,
    'avg_win_return': df[df['return'] > 0]['return'].mean(),
    'avg_loss_return': df[df['return'] < 0]['return'].mean(),
    'win_rate': len(df[df['return'] > 0]) / len(df) * 100,
    'max_single_move_up': df['return'].max(),
    'max_single_move_down': df['return'].min(),
    'price_range_total': ((df['close'].max() - df['close'].min()) / df['close'].min() * 100),
}

# ============================================================================
# 6. SAVE RESULTS
# ============================================================================
print("[7/7] Generating reports and saving results...")
print()

# Save raw statistics
session_df_results.to_csv('./results/TRUMP_session_stats.csv', index=False)
sequential_df.to_csv('./results/TRUMP_sequential_patterns.csv', index=False)
regime_results_df.to_csv('./results/TRUMP_regime_analysis.csv', index=False)
statistical_edges_df.to_csv('./results/TRUMP_statistical_edges.csv', index=False)

# Combine all pattern statistics
pattern_stats = pd.DataFrame([profile_stats])
pattern_stats.to_csv('./results/TRUMP_pattern_stats.csv', index=False)

# ============================================================================
# GENERATE MARKDOWN REPORT
# ============================================================================

report = f"""# TRUMP Pattern Discovery Analysis
**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Data Period:** {df['timestamp'].min().strftime('%Y-%m-%d')} to {df['timestamp'].max().strftime('%Y-%m-%d')}
**Total Candles:** {len(df):,} (1-minute timeframe)
**Days of Data:** {(df['timestamp'].max() - df['timestamp'].min()).days}

---

## Executive Summary

### Top 5 Most Significant Patterns Discovered

"""

# Find top patterns
top_patterns = []

# Best session
best_session = session_df_results.nlargest(1, 'avg_return').iloc[0]
top_patterns.append(f"**1. Best Trading Session:** {best_session['session']} session shows avg return of {best_session['avg_return']:.4f}% with {best_session['volatility_atr']:.4f}% ATR")

# Best sequential pattern
if len(sequential_df) > 0:
    best_seq = sequential_df.nlargest(1, 'next_1_avg').iloc[0] if 'next_1_avg' in sequential_df.columns else None
    if best_seq is not None:
        top_patterns.append(f"**2. Strongest Sequential Pattern:** '{best_seq['pattern']}' followed by {best_seq['next_1_avg']:.4f}% avg move ({best_seq['occurrences']} occurrences)")

# Dominant regime
dominant_regime = regime_results_df.nlargest(1, 'pct_of_time').iloc[0]
top_patterns.append(f"**3. Dominant Market Regime:** {dominant_regime['regime']} ({dominant_regime['pct_of_time']:.1f}% of time)")

# Best statistical edge
if len(statistical_edges_df) > 0 and 'avg_return' in statistical_edges_df.columns:
    best_edge = statistical_edges_df.nlargest(1, 'avg_return').iloc[0]
    top_patterns.append(f"**4. Strongest Statistical Edge:** {best_edge['condition']} shows {best_edge['avg_return']:.4f}% avg return")

# Behavioral insight
top_patterns.append(f"**5. Key Behavioral Trait:** {profile_stats['explosive_moves_pct']:.2f}% of candles are explosive (>2% body), indicating {'high' if profile_stats['explosive_moves_pct'] > 5 else 'moderate'} volatility character")

for pattern in top_patterns:
    report += f"\n{pattern}\n"

report += f"""

---

## 1. Session Analysis

Trading sessions analyzed (UTC time):
- **Asia:** 00:00-08:00 (Tokyo/Singapore/Hong Kong)
- **Europe:** 08:00-14:00 (London through US pre-market)
- **US:** 14:00-21:00 (NYSE/NASDAQ active)
- **Overnight:** 21:00-00:00 (low liquidity transition)

### Session Performance Comparison

| Session | Avg Return | Volatility (ATR) | Volume vs 24h | Long Win% | Short Win% | Best Hour | Worst Hour |
|---------|------------|------------------|---------------|-----------|------------|-----------|------------|
"""

for _, row in session_df_results.iterrows():
    report += f"| {row['session']:10s} | {row['avg_return']:8.4f}% | {row['volatility_atr']:12.4f}% | {row['volume_vs_24h']:10.2f}x | {row['long_win_rate']:7.1f}% | {row['short_win_rate']:8.1f}% | {int(row.get('best_hour', 0)):02d}:00 ({row.get('best_hour_return', 0):.3f}%) | {int(row.get('worst_hour', 0)):02d}:00 ({row.get('worst_hour_return', 0):.3f}%) |\n"

report += f"""

### Session Insights:
- **Most Profitable Session:** {session_df_results.nlargest(1, 'avg_return').iloc[0]['session']} with {session_df_results.nlargest(1, 'avg_return').iloc[0]['avg_return']:.4f}% avg return
- **Most Volatile Session:** {session_df_results.nlargest(1, 'volatility_atr').iloc[0]['session']} with {session_df_results.nlargest(1, 'volatility_atr').iloc[0]['volatility_atr']:.4f}% ATR
- **Highest Volume Session:** {session_df_results.nlargest(1, 'volume_vs_24h').iloc[0]['session']} at {session_df_results.nlargest(1, 'volume_vs_24h').iloc[0]['volume_vs_24h']:.2f}x average volume

---

## 2. Sequential Pattern Catalog

**"When X happens → Then Y follows"** patterns with statistical backing:

"""

if len(sequential_df) > 0:
    for idx, row in sequential_df.iterrows():
        report += f"\n### Pattern: {row['pattern']}\n"
        report += f"- **Occurrences:** {row['occurrences']:,}\n"

        if 'next_1_avg' in row and pd.notna(row['next_1_avg']):
            report += f"- **Next candle avg move:** {row['next_1_avg']:.4f}%\n"
        if 'next_3_avg' in row and pd.notna(row['next_3_avg']):
            report += f"- **Next 3 candles avg move:** {row['next_3_avg']:.4f}%\n"
        if 'next_5_avg' in row and pd.notna(row['next_5_avg']):
            report += f"- **Next 5 candles avg move:** {row['next_5_avg']:.4f}%\n"
        if 'next_1_winrate' in row and pd.notna(row['next_1_winrate']):
            report += f"- **Win rate:** {row['next_1_winrate']:.1f}%\n"
        if 'reversal_rate' in row and pd.notna(row['reversal_rate']):
            report += f"- **Reversal rate:** {row['reversal_rate']:.1f}%\n"
        if 'continuation_rate' in row and pd.notna(row['continuation_rate']):
            report += f"- **Continuation rate:** {row['continuation_rate']:.1f}%\n"
        if 'mean_reversion_rate' in row and pd.notna(row['mean_reversion_rate']):
            report += f"- **Mean reversion rate:** {row['mean_reversion_rate']:.1f}%\n"
        if 'expansion_follows_rate' in row and pd.notna(row['expansion_follows_rate']):
            report += f"- **Expansion follows rate:** {row['expansion_follows_rate']:.1f}%\n"

        report += "\n"

report += f"""

---

## 3. Regime Analysis

Market regime classification based on price action and indicators:

### Time Spent in Each Regime

"""

for _, row in regime_results_df.iterrows():
    report += f"- **{row['regime']}:** {row['pct_of_time']:.2f}% of time ({row['total_candles']:,} candles)\n"
    report += f"  - Avg return: {row['avg_return']:.4f}%\n"
    report += f"  - Avg volatility: {row['avg_volatility']:.4f}%\n\n"

report += f"""

### Regime Insights:

**Primary Character:** {"TRENDING" if profile_stats['trending_pct'] > 40 else "MEAN-REVERTING" if profile_stats['mean_reverting_pct'] > 40 else "CHOPPY/MIXED"}

- Trending behavior: {profile_stats['trending_pct']:.1f}% of time
- Mean-reverting behavior: {profile_stats['mean_reverting_pct']:.1f}% of time
- Choppy behavior: {profile_stats['choppy_pct']:.1f}% of time

**Strategy Suitability:**
"""

if profile_stats['trending_pct'] > profile_stats['mean_reverting_pct']:
    report += "- **BEST:** Trend-following strategies (breakout, momentum)\n"
    report += "- **GOOD:** Volatility expansion plays\n"
    report += "- **AVOID:** Pure mean-reversion during strong trends\n"
elif profile_stats['mean_reverting_pct'] > profile_stats['trending_pct']:
    report += "- **BEST:** Mean-reversion strategies (BB bounce, RSI extremes)\n"
    report += "- **GOOD:** Range-bound scalping\n"
    report += "- **AVOID:** Breakout strategies (high false breakout rate)\n"
else:
    report += "- **BEST:** Adaptive strategies that switch based on regime\n"
    report += "- **GOOD:** Multiple strategy portfolio approach\n"
    report += "- **AVOID:** Single-strategy approaches\n"

report += f"""

---

## 4. Statistical Edges

Ranked list of statistically significant patterns:

"""

if len(statistical_edges_df) > 0:
    # Sort by significance and return
    edges_sorted = statistical_edges_df.sort_values('sample_size', ascending=False)

    for idx, row in edges_sorted.head(15).iterrows():
        report += f"\n### {row['edge_type']}: {row['condition']}\n"
        if 'avg_return' in row and pd.notna(row['avg_return']):
            report += f"- **Avg Return:** {row['avg_return']:.4f}%\n"
        if 'win_rate' in row and pd.notna(row['win_rate']):
            report += f"- **Win Rate:** {row['win_rate']:.1f}%\n"
        if 'volatility' in row and pd.notna(row['volatility']):
            report += f"- **Volatility:** {row['volatility']:.4f}%\n"
        report += f"- **Sample Size:** {int(row['sample_size']):,}\n"
        report += f"- **Significance:** {row.get('significance', 'N/A')}\n"

report += f"""

---

## 5. Coin Personality Profile

### Volatility Character
- **Average daily range:** {profile_stats['avg_daily_range_pct']:.2f}%
- **Average candle range:** {profile_stats['avg_candle_range_pct']:.4f}%
- **Average body size:** {profile_stats['avg_body_pct']:.4f}%
- **Explosive moves (>2% body):** {profile_stats['explosive_moves_pct']:.2f}% of candles
- **Character:** {"EXPLOSIVE - rapid moves common" if profile_stats['explosive_moves_pct'] > 5 else "GRADUAL - smooth mover" if profile_stats['explosive_moves_pct'] < 2 else "MODERATE - balanced volatility"}

### Liquidity Character
- **Average volume:** {profile_stats['avg_volume']:.2f} TRUMP
- **Volume consistency (CV):** {profile_stats['volume_consistency_cv']:.2f} ({"High variance - sporadic" if profile_stats['volume_consistency_cv'] > 2 else "Moderate variance" if profile_stats['volume_consistency_cv'] > 1 else "Low variance - consistent"})
- **Slippage risk:** {"HIGH - use limit orders" if profile_stats['volume_consistency_cv'] > 2 else "MODERATE - market orders OK with caution" if profile_stats['volume_consistency_cv'] > 1 else "LOW - good liquidity"}

### Momentum Character
- **Win rate (all candles):** {profile_stats['win_rate']:.1f}%
- **Average winning move:** {profile_stats['avg_win_return']:.4f}%
- **Average losing move:** {profile_stats['avg_loss_return']:.4f}%
- **Profit factor:** {abs(profile_stats['avg_win_return'] / profile_stats['avg_loss_return']):.2f}x
- **Character:** {"Momentum follows through - ride winners" if abs(profile_stats['avg_win_return'] / profile_stats['avg_loss_return']) > 1.5 else "Quick mean reversion - take profits fast"}

### Risk Character
- **Largest single move up:** {profile_stats['max_single_move_up']:.2f}%
- **Largest single move down:** {profile_stats['max_single_move_down']:.2f}%
- **Total price range (period):** {profile_stats['price_range_total']:.2f}%
- **Black swan frequency:** {"HIGH - rare extreme events" if max(abs(profile_stats['max_single_move_up']), abs(profile_stats['max_single_move_down'])) > 10 else "MODERATE" if max(abs(profile_stats['max_single_move_up']), abs(profile_stats['max_single_move_down'])) > 5 else "LOW - predictable ranges"}

---

## 6. Strategy Implications

Based on the comprehensive pattern analysis, here are the BEST strategy types for TRUMP:

"""

# Determine best strategies based on profile
strategy_scores = {
    'Trend Following': profile_stats['trending_pct'] / 10,
    'Mean Reversion': profile_stats['mean_reverting_pct'] / 10,
    'Breakout Trading': profile_stats['explosive_moves_pct'] * 2,
    'Scalping': (100 - profile_stats['choppy_pct']) / 10,
}

sorted_strategies = sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)

report += "### Recommended Strategy Types (Ranked)\n\n"
for i, (strategy, score) in enumerate(sorted_strategies, 1):
    report += f"{i}. **{strategy}** (Score: {score:.1f}/10)\n"

report += f"""

### Specific Strategy Ideas

**HIGH CONFIDENCE (>60% win rate potential):**
"""

high_conf_patterns = []
if len(sequential_df) > 0:
    for _, row in sequential_df.iterrows():
        if 'next_1_winrate' in row and row['next_1_winrate'] > 60:
            high_conf_patterns.append(f"- {row['pattern']}: {row['next_1_winrate']:.1f}% win rate")
        if 'mean_reversion_rate' in row and row['mean_reversion_rate'] > 60:
            high_conf_patterns.append(f"- {row['pattern']}: {row['mean_reversion_rate']:.1f}% mean reversion rate")

if high_conf_patterns:
    for pattern in high_conf_patterns[:5]:
        report += f"{pattern}\n"
else:
    report += "- No single patterns exceeded 60% threshold - consider combination strategies\n"

report += f"""

**BEST TIMES TO TRADE:**
- {session_df_results.nlargest(1, 'avg_return').iloc[0]['session']} session (best avg return)
- Hour {int(hourly_returns['mean'].idxmax())}:00 (best hourly return: {hourly_returns['mean'].max():.4f}%)

**TIMES TO AVOID:**
- {session_df_results.nsmallest(1, 'avg_return').iloc[0]['session']} session (worst avg return)
- Hour {int(hourly_returns['mean'].idxmin())}:00 (worst hourly return: {hourly_returns['mean'].min():.4f}%)

---

## 7. Next Steps for Strategy Development

1. **Backtest the top 3 sequential patterns** identified in Section 2
2. **Focus development on {sorted_strategies[0][0].lower()}** strategies based on regime analysis
3. **Incorporate session filtering** - trade primarily during {session_df_results.nlargest(1, 'avg_return').iloc[0]['session']} session
4. **Test statistical edges** from Section 4 with minimum sample sizes
5. **Build regime detection** to switch between trend/mean-revert modes

---

## Data Files Generated

- `TRUMP_session_stats.csv` - Session performance metrics
- `TRUMP_sequential_patterns.csv` - X→Y pattern catalog
- `TRUMP_regime_analysis.csv` - Regime classification results
- `TRUMP_statistical_edges.csv` - Statistical edge rankings
- `TRUMP_pattern_stats.csv` - Overall behavioral statistics

**Analysis complete. Ready for strategy backtesting phase.**
"""

# Save report
with open('./results/TRUMP_PATTERN_ANALYSIS.md', 'w') as f:
    f.write(report)

print("="*80)
print("ANALYSIS COMPLETE!")
print("="*80)
print()
print("Files saved:")
print("  - ./results/TRUMP_PATTERN_ANALYSIS.md (comprehensive report)")
print("  - ./results/TRUMP_session_stats.csv")
print("  - ./results/TRUMP_sequential_patterns.csv")
print("  - ./results/TRUMP_regime_analysis.csv")
print("  - ./results/TRUMP_statistical_edges.csv")
print("  - ./results/TRUMP_pattern_stats.csv")
print()
print("Key Findings:")
print(f"  - Best session: {session_df_results.nlargest(1, 'avg_return').iloc[0]['session']}")
print(f"  - Dominant regime: {regime_results_df.nlargest(1, 'pct_of_time').iloc[0]['regime']}")
print(f"  - Best strategy type: {sorted_strategies[0][0]}")
print(f"  - Total patterns discovered: {len(sequential_df) + len(statistical_edges_df)}")
print()
