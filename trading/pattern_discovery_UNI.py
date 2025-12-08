#!/usr/bin/env python3
"""
UNI/USDT Pattern Discovery - Master Pattern Noticer
Exhaustive analysis to discover every exploitable pattern for strategy foundation.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("UNI/USDT MASTER PATTERN DISCOVERY")
print("=" * 80)

# Load data
print("\n[1/8] Loading and preparing data...")
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/uni_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate technical indicators
df['returns'] = df['close'].pct_change() * 100  # % returns
df['body'] = abs(df['close'] - df['open'])
df['body_pct'] = (df['body'] / df['open']) * 100
df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
df['range'] = df['high'] - df['low']
df['range_pct'] = (df['range'] / df['open']) * 100

# Volume
df['volume_sma'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_sma']

# ATR
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

# Moving averages
for period in [20, 50, 200]:
    df[f'sma{period}'] = df['close'].rolling(period).mean()
    df[f'dist_sma{period}'] = ((df['close'] - df[f'sma{period}']) / df[f'sma{period}']) * 100

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# Bollinger Bands
df['bb_middle'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_upper_2std'] = df['bb_middle'] + 2 * df['bb_std']
df['bb_lower_2std'] = df['bb_middle'] - 2 * df['bb_std']
df['bb_upper_3std'] = df['bb_middle'] + 3 * df['bb_std']
df['bb_lower_3std'] = df['bb_middle'] - 3 * df['bb_std']

# Time features
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday
df['session'] = df['hour'].apply(lambda h:
    'asia' if 0 <= h < 8 else
    'europe' if 8 <= h < 14 else
    'us' if 14 <= h < 21 else
    'overnight'
)

# Candle patterns
df['is_green'] = (df['close'] > df['open']).astype(int)
df['is_red'] = (df['close'] < df['open']).astype(int)
df['is_explosive_bull'] = ((df['body_pct'] > 1.2) & (df['is_green'] == 1) & (df['volume_ratio'] > 3)).astype(int)
df['is_explosive_bear'] = ((df['body_pct'] > 1.2) & (df['is_red'] == 1) & (df['volume_ratio'] > 3)).astype(int)

# Consecutive candles
df['consec_green'] = (df['is_green'].groupby((df['is_green'] != df['is_green'].shift()).cumsum()).cumsum())
df['consec_red'] = (df['is_red'].groupby((df['is_red'] != df['is_red'].shift()).cumsum()).cumsum())

df = df.dropna().reset_index(drop=True)

print(f"Data loaded: {len(df):,} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
print(f"Average volume: {df['volume'].mean():,.0f}")

# ============================================================================
# SESSION ANALYSIS
# ============================================================================
print("\n[2/8] Analyzing trading sessions...")

sessions = ['asia', 'europe', 'us', 'overnight']
session_stats = []

for session in sessions:
    session_data = df[df['session'] == session].copy()

    if len(session_data) == 0:
        continue

    # Calculate statistics
    avg_return = session_data['returns'].mean()
    volatility = session_data['returns'].std()
    avg_atr = session_data['atr'].mean()
    avg_volume_ratio = session_data['volume_ratio'].mean()

    # Long vs short performance
    longs = session_data[session_data['returns'] > 0]
    shorts = session_data[session_data['returns'] < 0]
    long_win_rate = len(longs) / len(session_data) * 100
    short_win_rate = len(shorts) / len(session_data) * 100

    # Best/worst hour
    hourly = session_data.groupby('hour')['returns'].mean()
    best_hour = hourly.idxmax()
    worst_hour = hourly.idxmin()

    session_stats.append({
        'session': session,
        'avg_return_pct': avg_return,
        'volatility_std': volatility,
        'avg_atr': avg_atr,
        'avg_volume_ratio': avg_volume_ratio,
        'long_win_rate': long_win_rate,
        'short_win_rate': short_win_rate,
        'best_hour': best_hour,
        'best_hour_return': hourly.max(),
        'worst_hour': worst_hour,
        'worst_hour_return': hourly.min(),
        'sample_size': len(session_data)
    })

session_df = pd.DataFrame(session_stats)
session_df = session_df.sort_values('avg_return_pct', ascending=False)
session_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/UNI_session_stats.csv', index=False)

print("\nSession Rankings (by avg return):")
for _, row in session_df.iterrows():
    print(f"  {row['session'].upper():10s} | Return: {row['avg_return_pct']:+.4f}% | Vol: {row['volatility_std']:.3f}% | "
          f"Long WR: {row['long_win_rate']:.1f}% | Volume: {row['avg_volume_ratio']:.2f}x")

# ============================================================================
# SEQUENTIAL PATTERNS
# ============================================================================
print("\n[3/8] Analyzing sequential patterns...")

sequential_patterns = []

# Pattern 1: After explosive candles
for explosive_type in ['explosive_bull', 'explosive_bear']:
    explosive_mask = df[f'is_{explosive_type}'] == 1
    explosive_indices = df[explosive_mask].index

    for lookforward in [1, 3, 5, 10]:
        returns_after = []
        for idx in explosive_indices:
            if idx + lookforward < len(df):
                ret = (df.loc[idx + lookforward, 'close'] - df.loc[idx, 'close']) / df.loc[idx, 'close'] * 100
                returns_after.append(ret)

        if len(returns_after) > 5:
            avg_return = np.mean(returns_after)
            win_rate = len([r for r in returns_after if r > 0]) / len(returns_after) * 100
            sequential_patterns.append({
                'pattern': f'after_{explosive_type}',
                'lookforward_candles': lookforward,
                'avg_return_pct': avg_return,
                'win_rate': win_rate,
                'sample_size': len(returns_after)
            })

# Pattern 2: After consecutive green/red candles
for consec_type, direction in [('consec_green', 'long'), ('consec_red', 'short')]:
    for min_consec in [3, 4, 5]:
        mask = df[consec_type] >= min_consec
        indices = df[mask].index

        for lookforward in [1, 3, 5]:
            returns_after = []
            for idx in indices:
                if idx + lookforward < len(df):
                    ret = (df.loc[idx + lookforward, 'close'] - df.loc[idx, 'close']) / df.loc[idx, 'close'] * 100
                    returns_after.append(ret)

            if len(returns_after) > 5:
                avg_return = np.mean(returns_after)
                win_rate = len([r for r in returns_after if r > 0]) / len(returns_after) * 100
                sequential_patterns.append({
                    'pattern': f'{consec_type}>={min_consec}',
                    'lookforward_candles': lookforward,
                    'avg_return_pct': avg_return,
                    'win_rate': win_rate,
                    'sample_size': len(returns_after)
                })

# Pattern 3: After rejection wicks
for wick_type in ['upper_wick', 'lower_wick']:
    mask = df[wick_type] > df['body'] * 2
    indices = df[mask].index

    for lookforward in [1, 3, 5]:
        returns_after = []
        for idx in indices:
            if idx + lookforward < len(df):
                ret = (df.loc[idx + lookforward, 'close'] - df.loc[idx, 'close']) / df.loc[idx, 'close'] * 100
                returns_after.append(ret)

        if len(returns_after) > 5:
            avg_return = np.mean(returns_after)
            win_rate = len([r for r in returns_after if r > 0]) / len(returns_after) * 100
            sequential_patterns.append({
                'pattern': f'{wick_type}_rejection',
                'lookforward_candles': lookforward,
                'avg_return_pct': avg_return,
                'win_rate': win_rate,
                'sample_size': len(returns_after)
            })

# Pattern 4: After BB touches
for bb_touch in ['bb_lower_2std', 'bb_lower_3std', 'bb_upper_2std', 'bb_upper_3std']:
    if bb_touch.startswith('bb_lower'):
        mask = df['close'] <= df[bb_touch]
    else:
        mask = df['close'] >= df[bb_touch]

    indices = df[mask].index

    for lookforward in [1, 5, 10, 20]:
        returns_after = []
        for idx in indices:
            if idx + lookforward < len(df):
                ret = (df.loc[idx + lookforward, 'close'] - df.loc[idx, 'close']) / df.loc[idx, 'close'] * 100
                returns_after.append(ret)

        if len(returns_after) > 5:
            avg_return = np.mean(returns_after)
            win_rate = len([r for r in returns_after if r > 0]) / len(returns_after) * 100
            sequential_patterns.append({
                'pattern': f'touch_{bb_touch}',
                'lookforward_candles': lookforward,
                'avg_return_pct': avg_return,
                'win_rate': win_rate,
                'sample_size': len(returns_after)
            })

# Pattern 5: Volume spikes
mask = df['volume_ratio'] > 3
indices = df[mask].index

for lookforward in [1, 3, 5, 10]:
    returns_after = []
    for idx in indices:
        if idx + lookforward < len(df):
            ret = (df.loc[idx + lookforward, 'close'] - df.loc[idx, 'close']) / df.loc[idx, 'close'] * 100
            returns_after.append(ret)

    if len(returns_after) > 5:
        avg_return = np.mean(returns_after)
        win_rate = len([r for r in returns_after if r > 0]) / len(returns_after) * 100
        sequential_patterns.append({
            'pattern': 'volume_spike_3x',
            'lookforward_candles': lookforward,
            'avg_return_pct': avg_return,
            'win_rate': win_rate,
            'sample_size': len(returns_after)
        })

sequential_df = pd.DataFrame(sequential_patterns)
sequential_df = sequential_df.sort_values('avg_return_pct', ascending=False)
sequential_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/UNI_sequential_patterns.csv', index=False)

print(f"\nTop 10 Sequential Patterns (by expected return):")
for idx, row in sequential_df.head(10).iterrows():
    print(f"  {row['pattern']:30s} → {row['lookforward_candles']:2.0f} bars | "
          f"Return: {row['avg_return_pct']:+.3f}% | WR: {row['win_rate']:5.1f}% | n={row['sample_size']:.0f}")

# ============================================================================
# REGIME CLASSIFICATION
# ============================================================================
print("\n[4/8] Classifying market regimes...")

def classify_regime(window_df):
    """Classify a window as trending, mean-reverting, explosive, or choppy"""
    if len(window_df) < 20:
        return 'insufficient_data'

    returns = window_df['returns'].values
    prices = window_df['close'].values

    # Trending: strong directional move
    price_change_pct = (prices[-1] - prices[0]) / prices[0] * 100
    if abs(price_change_pct) > 2:
        return 'trending_up' if price_change_pct > 0 else 'trending_down'

    # Explosive: large single-candle moves
    max_move = np.max(np.abs(returns))
    if max_move > 3:
        return 'explosive'

    # Mean-reverting: oscillates around mean
    mean_price = np.mean(prices)
    crosses = np.sum(np.diff((prices > mean_price).astype(int)) != 0)
    if crosses >= 3:
        return 'mean_reverting'

    # Choppy: small moves, no direction
    return 'choppy'

# Classify regimes in 60-minute windows
regime_data = []
window_size = 60

for i in range(0, len(df) - window_size, window_size):
    window = df.iloc[i:i+window_size]
    regime = classify_regime(window)

    regime_data.append({
        'timestamp': window['timestamp'].iloc[0],
        'regime': regime,
        'price_change_pct': (window['close'].iloc[-1] - window['close'].iloc[0]) / window['close'].iloc[0] * 100,
        'volatility': window['returns'].std(),
        'avg_volume_ratio': window['volume_ratio'].mean()
    })

regime_df = pd.DataFrame(regime_data)
regime_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/UNI_regime_analysis.csv', index=False)

regime_counts = regime_df['regime'].value_counts()
regime_pcts = (regime_counts / len(regime_df) * 100).round(2)

print("\nRegime Distribution:")
for regime, pct in regime_pcts.items():
    print(f"  {regime:20s}: {pct:5.1f}%")

# ============================================================================
# STATISTICAL EDGES
# ============================================================================
print("\n[5/8] Finding statistical edges...")

statistical_edges = []

# RSI extremes
for rsi_threshold, direction in [(30, 'oversold_bounce'), (70, 'overbought_fade')]:
    if direction == 'oversold_bounce':
        mask = df['rsi'] < rsi_threshold
    else:
        mask = df['rsi'] > rsi_threshold

    indices = df[mask].index

    for lookforward in [1, 5, 10, 20]:
        returns_after = []
        for idx in indices:
            if idx + lookforward < len(df):
                ret = (df.loc[idx + lookforward, 'close'] - df.loc[idx, 'close']) / df.loc[idx, 'close'] * 100
                returns_after.append(ret)

        if len(returns_after) > 5:
            avg_return = np.mean(returns_after)
            win_rate = len([r for r in returns_after if r > 0]) / len(returns_after) * 100
            statistical_edges.append({
                'edge_type': f'rsi_{direction}',
                'lookforward': lookforward,
                'avg_return': avg_return,
                'win_rate': win_rate,
                'sample_size': len(returns_after)
            })

# SMA crosses
for sma_period in [20, 50, 200]:
    # Cross above
    mask = (df['close'] > df[f'sma{sma_period}']) & (df['close'].shift(1) <= df[f'sma{sma_period}'].shift(1))
    indices = df[mask].index

    for lookforward in [1, 5, 10, 20]:
        returns_after = []
        for idx in indices:
            if idx + lookforward < len(df):
                ret = (df.loc[idx + lookforward, 'close'] - df.loc[idx, 'close']) / df.loc[idx, 'close'] * 100
                returns_after.append(ret)

        if len(returns_after) > 5:
            avg_return = np.mean(returns_after)
            win_rate = len([r for r in returns_after if r > 0]) / len(returns_after) * 100
            statistical_edges.append({
                'edge_type': f'cross_above_sma{sma_period}',
                'lookforward': lookforward,
                'avg_return': avg_return,
                'win_rate': win_rate,
                'sample_size': len(returns_after)
            })

    # Cross below
    mask = (df['close'] < df[f'sma{sma_period}']) & (df['close'].shift(1) >= df[f'sma{sma_period}'].shift(1))
    indices = df[mask].index

    for lookforward in [1, 5, 10, 20]:
        returns_after = []
        for idx in indices:
            if idx + lookforward < len(df):
                ret = (df.loc[idx + lookforward, 'close'] - df.loc[idx, 'close']) / df.loc[idx, 'close'] * 100
                returns_after.append(ret)

        if len(returns_after) > 5:
            avg_return = np.mean(returns_after)
            win_rate = len([r for r in returns_after if r > 0]) / len(returns_after) * 100
            statistical_edges.append({
                'edge_type': f'cross_below_sma{sma_period}',
                'lookforward': lookforward,
                'avg_return': avg_return,
                'win_rate': win_rate,
                'sample_size': len(returns_after)
            })

# Day of week patterns
dow_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
for dow in range(7):
    dow_data = df[df['day_of_week'] == dow]
    if len(dow_data) > 100:
        avg_return = dow_data['returns'].mean()
        win_rate = len(dow_data[dow_data['returns'] > 0]) / len(dow_data) * 100
        statistical_edges.append({
            'edge_type': f'day_{dow_names[dow]}',
            'lookforward': 1,
            'avg_return': avg_return,
            'win_rate': win_rate,
            'sample_size': len(dow_data)
        })

# Hour of day patterns
for hour in range(24):
    hour_data = df[df['hour'] == hour]
    if len(hour_data) > 50:
        avg_return = hour_data['returns'].mean()
        win_rate = len(hour_data[hour_data['returns'] > 0]) / len(hour_data) * 100
        statistical_edges.append({
            'edge_type': f'hour_{hour:02d}',
            'lookforward': 1,
            'avg_return': avg_return,
            'win_rate': win_rate,
            'sample_size': len(hour_data)
        })

edges_df = pd.DataFrame(statistical_edges)
edges_df = edges_df.sort_values('avg_return', ascending=False)
edges_df.to_csv('/workspaces/Carebiuro_windykacja/trading/results/UNI_statistical_edges.csv', index=False)

print(f"\nTop 10 Statistical Edges:")
for idx, row in edges_df.head(10).iterrows():
    print(f"  {row['edge_type']:35s} → {row['lookforward']:2.0f} bars | "
          f"Return: {row['avg_return']:+.4f}% | WR: {row['win_rate']:5.1f}% | n={row['sample_size']:.0f}")

# ============================================================================
# COIN PERSONALITY PROFILE
# ============================================================================
print("\n[6/8] Building coin personality profile...")

personality = {
    'volatility': {
        'daily_range_avg_pct': df.groupby(df['timestamp'].dt.date)['range_pct'].sum().mean(),
        'avg_candle_range_pct': df['range_pct'].mean(),
        'max_single_move_pct': df['returns'].abs().max(),
        'atr_avg': df['atr'].mean()
    },
    'liquidity': {
        'avg_volume': df['volume'].mean(),
        'volume_std': df['volume'].std(),
        'volume_cv': df['volume'].std() / df['volume'].mean()
    },
    'momentum': {
        'avg_return_after_up_move': df[df['returns'] > 1]['returns'].shift(-1).mean(),
        'avg_return_after_down_move': df[df['returns'] < -1]['returns'].shift(-1).mean(),
        'autocorrelation_1lag': df['returns'].autocorr(lag=1),
        'autocorrelation_5lag': df['returns'].autocorr(lag=5)
    },
    'risk': {
        'max_drawdown_pct': ((df['close'].cummax() - df['close']) / df['close'].cummax() * 100).max(),
        'avg_drawdown_duration_candles': None,  # Complex calculation
        'win_rate_overall': len(df[df['returns'] > 0]) / len(df) * 100
    }
}

print("\nCoin Personality Profile:")
print("  VOLATILITY:")
print(f"    - Daily range avg: {personality['volatility']['daily_range_avg_pct']:.2f}%")
print(f"    - Avg candle range: {personality['volatility']['avg_candle_range_pct']:.3f}%")
print(f"    - Max single move: {personality['volatility']['max_single_move_pct']:.2f}%")
print(f"    - ATR (14): {personality['volatility']['atr_avg']:.4f}")
print("  LIQUIDITY:")
print(f"    - Avg volume: {personality['liquidity']['avg_volume']:,.0f}")
print(f"    - Volume CV: {personality['liquidity']['volume_cv']:.2f}")
print("  MOMENTUM:")
print(f"    - Autocorr 1-lag: {personality['momentum']['autocorrelation_1lag']:+.4f}")
print(f"    - Autocorr 5-lag: {personality['momentum']['autocorrelation_5lag']:+.4f}")
print(f"    - After +1% move: {personality['momentum']['avg_return_after_up_move']:+.4f}%")
print(f"    - After -1% move: {personality['momentum']['avg_return_after_down_move']:+.4f}%")
print("  RISK:")
print(f"    - Max drawdown: {personality['risk']['max_drawdown_pct']:.2f}%")
print(f"    - Overall win rate: {personality['risk']['win_rate_overall']:.1f}%")

# ============================================================================
# HIGH CONFIDENCE PATTERNS
# ============================================================================
print("\n[7/8] Identifying high-confidence patterns...")

# Filter for actionable patterns
actionable_patterns = []

# From sequential patterns
for _, row in sequential_df.iterrows():
    edge = abs(row['avg_return_pct'])
    if edge > 0.1 and row['sample_size'] > 20:  # Edge > fees and sufficient samples
        confidence = 'HIGH' if row['win_rate'] > 60 else 'MEDIUM'
        actionable_patterns.append({
            'pattern_type': 'sequential',
            'pattern_name': row['pattern'],
            'edge_pct': row['avg_return_pct'],
            'win_rate': row['win_rate'],
            'sample_size': row['sample_size'],
            'confidence': confidence,
            'lookforward': row['lookforward_candles']
        })

# From statistical edges
for _, row in edges_df.iterrows():
    edge = abs(row['avg_return'])
    if edge > 0.1 and row['sample_size'] > 20:
        confidence = 'HIGH' if row['win_rate'] > 60 else 'MEDIUM'
        actionable_patterns.append({
            'pattern_type': 'statistical',
            'pattern_name': row['edge_type'],
            'edge_pct': row['avg_return'],
            'win_rate': row['win_rate'],
            'sample_size': row['sample_size'],
            'confidence': confidence,
            'lookforward': row['lookforward']
        })

patterns_summary = pd.DataFrame(actionable_patterns)
patterns_summary = patterns_summary.sort_values(['confidence', 'edge_pct'], ascending=[False, False])
patterns_summary.to_csv('/workspaces/Carebiuro_windykacja/trading/results/UNI_pattern_stats.csv', index=False)

high_conf = patterns_summary[patterns_summary['confidence'] == 'HIGH']
print(f"\nFound {len(high_conf)} HIGH CONFIDENCE patterns (WR > 60%, edge > 0.1%):")
for _, row in high_conf.head(10).iterrows():
    print(f"  {row['pattern_name']:40s} | Edge: {row['edge_pct']:+.3f}% | WR: {row['win_rate']:5.1f}% | n={row['sample_size']:.0f}")

# ============================================================================
# STRATEGY RECOMMENDATIONS
# ============================================================================
print("\n[8/8] Generating strategy recommendations...")

recommendations = []

# Analyze momentum characteristics
autocorr = personality['momentum']['autocorrelation_1lag']
if autocorr > 0.05:
    recommendations.append("TREND-FOLLOWING: Positive 1-lag autocorrelation suggests momentum continuation")
elif autocorr < -0.05:
    recommendations.append("MEAN-REVERSION: Negative 1-lag autocorrelation suggests reversals after moves")
else:
    recommendations.append("MIXED: Weak autocorrelation suggests both trend and mean-reversion may work")

# Analyze regime distribution
choppy_pct = regime_pcts.get('choppy', 0)
if choppy_pct > 70:
    recommendations.append(f"AVOID 1M TRADING: {choppy_pct:.0f}% choppy regime makes consistent profits difficult")
elif choppy_pct > 50:
    recommendations.append(f"SELECTIVE TRADING: {choppy_pct:.0f}% choppy - use strong filters and session restrictions")

# Analyze volatility
if personality['volatility']['avg_candle_range_pct'] < 0.15:
    recommendations.append("LOW VOLATILITY: Tight stops difficult, consider wider targets or longer timeframes")
else:
    recommendations.append("NORMAL VOLATILITY: Standard ATR-based stops should work")

# Best session
best_session = session_df.iloc[0]
if best_session['avg_return_pct'] > 0.001:
    recommendations.append(f"BEST SESSION: {best_session['session'].upper()} (avg return: +{best_session['avg_return_pct']:.4f}%)")

# Top pattern
if len(high_conf) > 0:
    top_pattern = high_conf.iloc[0]
    recommendations.append(f"TOP PATTERN: {top_pattern['pattern_name']} (WR: {top_pattern['win_rate']:.1f}%, edge: {top_pattern['edge_pct']:+.3f}%)")

print("\n" + "=" * 80)
print("STRATEGY RECOMMENDATIONS")
print("=" * 80)
for i, rec in enumerate(recommendations, 1):
    print(f"{i}. {rec}")

# ============================================================================
# GENERATE MARKDOWN REPORT
# ============================================================================
print("\n[9/9] Writing comprehensive report...")

report = f"""# UNI/USDT Pattern Discovery Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Dataset Summary
- **Candles**: {len(df):,} (30 days of 1-minute data)
- **Date Range**: {df['timestamp'].min()} to {df['timestamp'].max()}
- **Price Range**: ${df['close'].min():.2f} - ${df['close'].max():.2f}
- **Average Volume**: {df['volume'].mean():,.0f}

---

## 1. Session Analysis

Best performing sessions (by average return):

| Session | Avg Return | Volatility | Long WR | Short WR | Avg Volume | Best Hour | Sample Size |
|---------|-----------|-----------|---------|----------|------------|-----------|-------------|
"""

for _, row in session_df.iterrows():
    report += f"| {row['session'].upper()} | {row['avg_return_pct']:+.4f}% | {row['volatility_std']:.3f}% | "
    report += f"{row['long_win_rate']:.1f}% | {row['short_win_rate']:.1f}% | {row['avg_volume_ratio']:.2f}x | "
    report += f"{row['best_hour']:02.0f}:00 ({row['best_hour_return']:+.4f}%) | {row['sample_size']:,} |\n"

report += f"""
### Key Insights:
- **Best session**: {session_df.iloc[0]['session'].upper()} (+{session_df.iloc[0]['avg_return_pct']:.4f}% avg)
- **Highest volatility**: {session_df.sort_values('volatility_std', ascending=False).iloc[0]['session'].upper()} ({session_df.sort_values('volatility_std', ascending=False).iloc[0]['volatility_std']:.3f}% std)
- **Best volume**: {session_df.sort_values('avg_volume_ratio', ascending=False).iloc[0]['session'].upper()} ({session_df.sort_values('avg_volume_ratio', ascending=False).iloc[0]['avg_volume_ratio']:.2f}x avg)

---

## 2. Sequential Patterns

Top 20 patterns by expected return:

| Rank | Pattern | Lookforward | Avg Return | Win Rate | Sample Size |
|------|---------|-------------|------------|----------|-------------|
"""

for i, (_, row) in enumerate(sequential_df.head(20).iterrows(), 1):
    report += f"| {i} | {row['pattern']} | {row['lookforward_candles']:.0f} bars | "
    report += f"{row['avg_return_pct']:+.3f}% | {row['win_rate']:.1f}% | {row['sample_size']:.0f} |\n"

report += f"""
### Pattern Categories Tested:
1. **After explosive candles** (>1.2% body + 3x volume)
2. **After consecutive green/red bars** (3, 4, 5+ in a row)
3. **After rejection wicks** (wick > 2x body)
4. **After Bollinger Band touches** (2std and 3std)
5. **After volume spikes** (>3x average)

---

## 3. Market Regime Analysis

Regime distribution (60-minute windows):

| Regime | Percentage | Description |
|--------|-----------|-------------|
"""

for regime, pct in regime_pcts.items():
    report += f"| {regime} | {pct:.1f}% | "
    if regime == 'trending_up' or regime == 'trending_down':
        report += "Strong directional move (>2%) |\n"
    elif regime == 'explosive':
        report += "Large single-candle moves (>3%) |\n"
    elif regime == 'mean_reverting':
        report += "Oscillates around mean (3+ crosses) |\n"
    elif regime == 'choppy':
        report += "Small moves, no clear direction |\n"
    else:
        report += "Other |\n"

report += f"""
### Regime Implications:
"""

if regime_pcts.get('choppy', 0) > 70:
    report += f"- **CRITICAL**: {regime_pcts['choppy']:.0f}% choppy regime makes UNI very difficult to trade on 1m\n"
    report += "- Consider higher timeframes (5m, 15m) for cleaner signals\n"
elif regime_pcts.get('choppy', 0) > 50:
    report += f"- **WARNING**: {regime_pcts['choppy']:.0f}% choppy - requires strong filters and selective entries\n"

trending_pct = regime_pcts.get('trending_up', 0) + regime_pcts.get('trending_down', 0)
if trending_pct > 15:
    report += f"- **OPPORTUNITY**: {trending_pct:.0f}% trending regime supports trend-following strategies\n"

mean_rev_pct = regime_pcts.get('mean_reverting', 0)
if mean_rev_pct > 10:
    report += f"- **OPPORTUNITY**: {mean_rev_pct:.0f}% mean-reverting regime supports bounce/fade strategies\n"

report += f"""
---

## 4. Statistical Edges

Top 20 edges by expected return:

| Rank | Edge Type | Lookforward | Avg Return | Win Rate | Sample Size |
|------|-----------|-------------|------------|----------|-------------|
"""

for i, (_, row) in enumerate(edges_df.head(20).iterrows(), 1):
    report += f"| {i} | {row['edge_type']} | {row['lookforward']:.0f} bars | "
    report += f"{row['avg_return']:+.4f}% | {row['win_rate']:.1f}% | {row['sample_size']:.0f} |\n"

report += """
### Edge Categories Tested:
1. **RSI extremes** (oversold bounce < 30, overbought fade > 70)
2. **SMA crossovers** (20, 50, 200 period)
3. **Day of week** patterns
4. **Hour of day** patterns

---

## 5. Coin Personality Profile

### Volatility Character
"""

report += f"- **Daily range**: {personality['volatility']['daily_range_avg_pct']:.2f}% average\n"
report += f"- **Candle range**: {personality['volatility']['avg_candle_range_pct']:.3f}% average\n"
report += f"- **Max single move**: {personality['volatility']['max_single_move_pct']:.2f}%\n"
report += f"- **ATR(14)**: {personality['volatility']['atr_avg']:.4f}\n"

if personality['volatility']['avg_candle_range_pct'] < 0.15:
    report += "- **Assessment**: LOW volatility - tight stops difficult, fees eat small moves\n"
elif personality['volatility']['avg_candle_range_pct'] > 0.30:
    report += "- **Assessment**: HIGH volatility - good for swing trades, wide stops needed\n"
else:
    report += "- **Assessment**: NORMAL volatility - standard risk management applies\n"

report += """
### Liquidity Character
"""

report += f"- **Average volume**: {personality['liquidity']['avg_volume']:,.0f}\n"
report += f"- **Volume CV**: {personality['liquidity']['volume_cv']:.2f}\n"

if personality['liquidity']['volume_cv'] > 2:
    report += "- **Assessment**: INCONSISTENT volume - spiky, avoid low-volume periods\n"
else:
    report += "- **Assessment**: CONSISTENT volume - reliable liquidity\n"

report += """
### Momentum Character
"""

report += f"- **1-lag autocorr**: {personality['momentum']['autocorrelation_1lag']:+.4f}\n"
report += f"- **5-lag autocorr**: {personality['momentum']['autocorrelation_5lag']:+.4f}\n"
report += f"- **After +1% move**: {personality['momentum']['avg_return_after_up_move']:+.4f}% avg next candle\n"
report += f"- **After -1% move**: {personality['momentum']['avg_return_after_down_move']:+.4f}% avg next candle\n"

if personality['momentum']['autocorrelation_1lag'] > 0.05:
    report += "- **Assessment**: MOMENTUM coin - moves continue in same direction\n"
elif personality['momentum']['autocorrelation_1lag'] < -0.05:
    report += "- **Assessment**: MEAN-REVERTING coin - moves tend to reverse\n"
else:
    report += "- **Assessment**: NEUTRAL momentum - no strong continuation/reversal bias\n"

report += """
### Risk Character
"""

report += f"- **Max drawdown**: {personality['risk']['max_drawdown_pct']:.2f}%\n"
report += f"- **Overall win rate**: {personality['risk']['win_rate_overall']:.1f}%\n"

report += """
---

## 6. High-Confidence Patterns

Patterns with win rate > 60% AND edge > 0.1% (above fees):

| Pattern Type | Pattern Name | Edge | Win Rate | Sample Size | Lookforward |
|--------------|--------------|------|----------|-------------|-------------|
"""

for _, row in high_conf.head(20).iterrows():
    report += f"| {row['pattern_type']} | {row['pattern_name']} | {row['edge_pct']:+.3f}% | "
    report += f"{row['win_rate']:.1f}% | {row['sample_size']:.0f} | {row['lookforward']:.0f} bars |\n"

if len(high_conf) == 0:
    report += "| - | **NO HIGH-CONFIDENCE PATTERNS FOUND** | - | - | - | - |\n"
    report += "\n**This suggests UNI is very difficult to trade profitably on 1-minute timeframe.**\n"

report += """
---

## 7. Strategy Recommendations

"""

for i, rec in enumerate(recommendations, 1):
    report += f"{i}. **{rec}**\n\n"

report += """
---

## 8. Next Steps for Strategy Development

Based on this analysis, here are the recommended approaches for backtesting:

"""

if len(high_conf) > 0:
    report += f"### Approach 1: Pattern-Based Strategy\n"
    report += f"- **Focus**: Top 3 high-confidence patterns\n"
    report += f"- **Best pattern**: {high_conf.iloc[0]['pattern_name']} (WR: {high_conf.iloc[0]['win_rate']:.1f}%, edge: {high_conf.iloc[0]['edge_pct']:+.3f}%)\n"
    report += f"- **Session filter**: {session_df.iloc[0]['session'].upper()} session only\n"
    report += f"- **Risk management**: ATR-based stops, 2-3:1 R:R\n\n"

best_session = session_df.iloc[0]
if best_session['long_win_rate'] > 52 or best_session['short_win_rate'] > 52:
    report += f"### Approach 2: Session-Based Directional Bias\n"
    if best_session['long_win_rate'] > best_session['short_win_rate']:
        report += f"- **Direction**: LONG bias during {best_session['session'].upper()} session\n"
        report += f"- **Win rate**: {best_session['long_win_rate']:.1f}% for longs\n"
    else:
        report += f"- **Direction**: SHORT bias during {best_session['session'].upper()} session\n"
        report += f"- **Win rate**: {best_session['short_win_rate']:.1f}% for shorts\n"
    report += f"- **Entry**: Simple momentum or mean-reversion depending on top patterns\n"
    report += f"- **Volume filter**: Only trade when volume > {best_session['avg_volume_ratio']:.1f}x average\n\n"

if personality['momentum']['autocorrelation_1lag'] > 0.05:
    report += f"### Approach 3: Momentum Continuation\n"
    report += f"- **Entry**: After explosive moves in trend direction\n"
    report += f"- **Confirmation**: Volume spike + price above/below key SMA\n"
    report += f"- **Exit**: Trailing stop or opposite signal\n\n"
elif personality['momentum']['autocorrelation_1lag'] < -0.05:
    report += f"### Approach 3: Mean Reversion\n"
    report += f"- **Entry**: After exhaustion moves (4+ consecutive bars, BB touches)\n"
    report += f"- **Confirmation**: RSI extreme + rejection wick\n"
    report += f"- **Exit**: Return to mean (SMA20) or opposite extreme\n\n"

report += f"""
### Risk Management Guidelines
- **Position size**: Start with 0.5-1% risk per trade
- **Stop loss**: 1.5-2.0x ATR(14) = ~${personality['volatility']['atr_avg'] * 1.5:.4f} - ${personality['volatility']['atr_avg'] * 2:.4f}
- **Take profit**: 3-4:1 R:R minimum to overcome {regime_pcts.get('choppy', 0):.0f}% choppy regime
- **Max trades/day**: Limit to 5-10 to avoid overtrading in chop
- **Session filter**: Stick to {session_df.iloc[0]['session'].upper()} session for best odds

---

## Files Generated
1. `UNI_session_stats.csv` - Session performance data
2. `UNI_sequential_patterns.csv` - X→Y pattern probabilities
3. `UNI_regime_analysis.csv` - Regime classification timeline
4. `UNI_statistical_edges.csv` - Technical indicator edges
5. `UNI_pattern_stats.csv` - High-confidence pattern summary
6. `UNI_PATTERN_ANALYSIS.md` - This comprehensive report

---

*Generated by Master Pattern Noticer*
*Analysis completed in deep discovery mode*
"""

with open('/workspaces/Carebiuro_windykacja/trading/results/UNI_PATTERN_ANALYSIS.md', 'w') as f:
    f.write(report)

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE!")
print("=" * 80)
print("\nFiles generated:")
print("  1. /workspaces/Carebiuro_windykacja/trading/results/UNI_session_stats.csv")
print("  2. /workspaces/Carebiuro_windykacja/trading/results/UNI_sequential_patterns.csv")
print("  3. /workspaces/Carebiuro_windykacja/trading/results/UNI_regime_analysis.csv")
print("  4. /workspaces/Carebiuro_windykacja/trading/results/UNI_statistical_edges.csv")
print("  5. /workspaces/Carebiuro_windykacja/trading/results/UNI_pattern_stats.csv")
print("  6. /workspaces/Carebiuro_windykacja/trading/results/UNI_PATTERN_ANALYSIS.md")
print("\nReview the markdown report for comprehensive insights and strategy recommendations.")
print("=" * 80)
