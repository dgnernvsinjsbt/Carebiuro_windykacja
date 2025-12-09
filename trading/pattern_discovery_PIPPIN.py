"""
PIPPIN/USDT Deep Pattern Discovery Analysis
============================================
Exhaustive pattern analysis to discover exploitable trading edges.

Data: 7 days of BingX 1-minute candles (11,129 candles)
Objective: Find actionable patterns for strategy development
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# DATA LOADING AND PREPARATION
# ============================================================================

print("=" * 80)
print("PIPPIN/USDT PATTERN DISCOVERY ANALYSIS")
print("=" * 80)
print("\n[1/8] Loading and preparing data...")

df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/pippin_7d_bingx.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Data loaded: {len(df)} candles")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

# Calculate derived features
df['returns'] = df['close'].pct_change() * 100  # Percentage returns
df['body'] = ((df['close'] - df['open']) / df['open']) * 100  # Body size %
df['body_abs'] = abs(df['body'])
df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
df['total_range'] = df['high'] - df['low']
df['wick_ratio'] = (df['upper_wick'] + df['lower_wick']) / (df['total_range'] + 1e-10)

# ATR (14 period)
df['tr'] = df[['high', 'low', 'close']].apply(
    lambda x: max(x['high'] - x['low'],
                  abs(x['high'] - df['close'].shift(1).loc[x.name]) if x.name > 0 else 0,
                  abs(x['low'] - df['close'].shift(1).loc[x.name]) if x.name > 0 else 0),
    axis=1
)
df['atr_14'] = df['tr'].rolling(14).mean()
df['atr_pct'] = (df['atr_14'] / df['close']) * 100

# Moving averages
df['sma_20'] = df['close'].rolling(20).mean()
df['sma_50'] = df['close'].rolling(50).mean()
df['sma_200'] = df['close'].rolling(200).mean()
df['dist_sma20'] = ((df['close'] - df['sma_20']) / df['sma_20']) * 100

# Bollinger Bands (20, 2 std)
df['bb_middle'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-10)

# RSI (14 period)
delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / (loss + 1e-10)
df['rsi_14'] = 100 - (100 / (1 + rs))

# Volume analysis
df['volume_sma'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / (df['volume_sma'] + 1e-10)

# Time-based features
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
df['date'] = df['timestamp'].dt.date

# Session classification
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

# Consecutive candle patterns
df['is_green'] = (df['close'] > df['open']).astype(int)
df['is_red'] = (df['close'] < df['open']).astype(int)

def count_consecutive(series):
    """Count consecutive True values"""
    result = pd.Series(0, index=series.index)
    count = 0
    for i in range(len(series)):
        if series.iloc[i]:
            count += 1
            result.iloc[i] = count
        else:
            count = 0
    return result

df['consecutive_green'] = count_consecutive(df['is_green'] == 1)
df['consecutive_red'] = count_consecutive(df['is_red'] == 1)

print("✓ Derived features calculated (returns, ATR, RSI, BBands, SMAs, volume, time)")

# ============================================================================
# SESSION ANALYSIS
# ============================================================================

print("\n[2/8] Analyzing trading sessions...")

session_stats = []

for session in ['Asia', 'Europe', 'US', 'Overnight']:
    session_data = df[df['session'] == session].copy()

    if len(session_data) == 0:
        continue

    stats = {
        'Session': session,
        'Candles': len(session_data),
        'Avg_Return_%': session_data['returns'].mean(),
        'Volatility_ATR_%': session_data['atr_pct'].mean(),
        'Avg_Volume': session_data['volume'].mean(),
        'Volume_vs_24h': (session_data['volume'].mean() / df['volume'].mean()) * 100,
        'Long_WinRate_%': (session_data[session_data['returns'] > 0.1].shape[0] / len(session_data)) * 100,
        'Short_WinRate_%': (session_data[session_data['returns'] < -0.1].shape[0] / len(session_data)) * 100,
    }

    # Best/worst hour
    hour_returns = session_data.groupby('hour')['returns'].mean()
    if len(hour_returns) > 0:
        stats['Best_Hour'] = f"{hour_returns.idxmax()}:00 (+{hour_returns.max():.3f}%)"
        stats['Worst_Hour'] = f"{hour_returns.idxmin()}:00 ({hour_returns.min():.3f}%)"

    session_stats.append(stats)

session_df = pd.DataFrame(session_stats)
print("\nSession Analysis:")
print(session_df.to_string(index=False))

# ============================================================================
# SEQUENTIAL PATTERN ANALYSIS
# ============================================================================

print("\n[3/8] Discovering sequential patterns (When X → Then Y)...")

patterns = []

# Pattern 1: After large body candle
large_body_threshold = 2.0
large_body_mask = df['body_abs'] > large_body_threshold
large_body_indices = df[large_body_mask].index

if len(large_body_indices) > 30:
    next_1_returns = [df.loc[i+1, 'returns'] if i+1 < len(df) else np.nan for i in large_body_indices]
    next_3_returns = [df.loc[i+1:i+3, 'returns'].sum() if i+3 < len(df) else np.nan for i in large_body_indices]
    next_5_returns = [df.loc[i+1:i+5, 'returns'].sum() if i+5 < len(df) else np.nan for i in large_body_indices]

    patterns.append({
        'Pattern': f'After >2% body candle',
        'Count': len(large_body_indices),
        'Next_1_Bar_%': np.nanmean(next_1_returns),
        'Next_3_Bars_%': np.nanmean(next_3_returns),
        'Next_5_Bars_%': np.nanmean(next_5_returns),
        'Win_Rate_%': (sum([1 for r in next_1_returns if r > 0]) / len([r for r in next_1_returns if not np.isnan(r)])) * 100
    })

# Pattern 2: After 3+ consecutive greens
consec_3_green = df[df['consecutive_green'] >= 3].index
if len(consec_3_green) > 30:
    next_returns = [df.loc[i+1, 'returns'] if i+1 < len(df) else np.nan for i in consec_3_green]
    reversal_rate = sum([1 for r in next_returns if r < 0]) / len([r for r in next_returns if not np.isnan(r)]) * 100

    patterns.append({
        'Pattern': 'After 3+ consecutive greens',
        'Count': len(consec_3_green),
        'Next_1_Bar_%': np.nanmean(next_returns),
        'Reversal_Rate_%': reversal_rate,
        'Continuation_Rate_%': 100 - reversal_rate,
    })

# Pattern 3: After 3+ consecutive reds
consec_3_red = df[df['consecutive_red'] >= 3].index
if len(consec_3_red) > 30:
    next_returns = [df.loc[i+1, 'returns'] if i+1 < len(df) else np.nan for i in consec_3_red]
    reversal_rate = sum([1 for r in next_returns if r > 0]) / len([r for r in next_returns if not np.isnan(r)]) * 100

    patterns.append({
        'Pattern': 'After 3+ consecutive reds',
        'Count': len(consec_3_red),
        'Next_1_Bar_%': np.nanmean(next_returns),
        'Reversal_Rate_%': reversal_rate,
        'Continuation_Rate_%': 100 - reversal_rate,
    })

# Pattern 4: After wick > 2x body (rejection)
rejection_mask = df['wick_ratio'] > 0.67  # Wicks dominate
rejection_indices = df[rejection_mask].index
if len(rejection_indices) > 30:
    next_returns = [df.loc[i+1, 'returns'] if i+1 < len(df) else np.nan for i in rejection_indices]

    patterns.append({
        'Pattern': 'After rejection candle (wick > 2x body)',
        'Count': len(rejection_indices),
        'Next_1_Bar_%': np.nanmean(next_returns),
        'Win_Rate_%': (sum([1 for r in next_returns if abs(r) > 0.1]) / len([r for r in next_returns if not np.isnan(r)])) * 100
    })

# Pattern 5: After volume spike > 3x average
volume_spike_mask = df['volume_ratio'] > 3.0
volume_spike_indices = df[volume_spike_mask].index
if len(volume_spike_indices) > 30:
    next_1_returns = [df.loc[i+1, 'returns'] if i+1 < len(df) else np.nan for i in volume_spike_indices]
    next_5_returns = [df.loc[i+1:i+5, 'returns'].sum() if i+5 < len(df) else np.nan for i in volume_spike_indices]

    patterns.append({
        'Pattern': 'After volume spike >3x avg',
        'Count': len(volume_spike_indices),
        'Next_1_Bar_%': np.nanmean(next_1_returns),
        'Next_5_Bars_%': np.nanmean(next_5_returns),
        'Continuation_%': (sum([1 for r in next_5_returns if r > 0]) / len([r for r in next_5_returns if not np.isnan(r)])) * 100
    })

# Pattern 6: ATR expansion
df['atr_ratio'] = df['atr_14'] / df['atr_14'].rolling(20).mean()
atr_expansion_mask = df['atr_ratio'] > 1.5
atr_expansion_indices = df[atr_expansion_mask].index
if len(atr_expansion_indices) > 30:
    next_5_returns = [df.loc[i+1:i+5, 'returns'].sum() if i+5 < len(df) else np.nan for i in atr_expansion_indices]

    patterns.append({
        'Pattern': 'After ATR expansion >1.5x',
        'Count': len(atr_expansion_indices),
        'Next_5_Bars_%': np.nanmean(next_5_returns),
        'Win_Rate_%': (sum([1 for r in next_5_returns if r > 0.5]) / len([r for r in next_5_returns if not np.isnan(r)])) * 100
    })

# Pattern 7: ATR contraction
atr_contraction_mask = df['atr_ratio'] < 0.5
atr_contraction_indices = df[atr_contraction_mask].index
if len(atr_contraction_indices) > 30:
    next_10_returns = [df.loc[i+1:i+10, 'returns'].sum() if i+10 < len(df) else np.nan for i in atr_contraction_indices]

    patterns.append({
        'Pattern': 'After ATR contraction <0.5x',
        'Count': len(atr_contraction_indices),
        'Next_10_Bars_%': np.nanmean(next_10_returns),
        'Expansion_Follows_%': (sum([1 for idx in atr_contraction_indices if idx+10 < len(df) and df.loc[idx+10, 'atr_ratio'] > 1.0]) / len(atr_contraction_indices)) * 100
    })

# Pattern 8: RSI extremes
rsi_oversold = df[df['rsi_14'] < 30].index
if len(rsi_oversold) > 30:
    next_returns = [df.loc[i+1:i+5, 'returns'].sum() if i+5 < len(df) else np.nan for i in rsi_oversold]

    patterns.append({
        'Pattern': 'RSI < 30 (oversold)',
        'Count': len(rsi_oversold),
        'Next_5_Bars_%': np.nanmean(next_returns),
        'Reversal_Up_%': (sum([1 for r in next_returns if r > 0.5]) / len([r for r in next_returns if not np.isnan(r)])) * 100
    })

rsi_overbought = df[df['rsi_14'] > 70].index
if len(rsi_overbought) > 30:
    next_returns = [df.loc[i+1:i+5, 'returns'].sum() if i+5 < len(df) else np.nan for i in rsi_overbought]

    patterns.append({
        'Pattern': 'RSI > 70 (overbought)',
        'Count': len(rsi_overbought),
        'Next_5_Bars_%': np.nanmean(next_returns),
        'Reversal_Down_%': (sum([1 for r in next_returns if r < -0.5]) / len([r for r in next_returns if not np.isnan(r)])) * 100
    })

# Pattern 9: BB touches
bb_lower_touch = df[df['close'] <= df['bb_lower']].index
if len(bb_lower_touch) > 30:
    next_returns = [df.loc[i+1:i+5, 'returns'].sum() if i+5 < len(df) else np.nan for i in bb_lower_touch]

    patterns.append({
        'Pattern': 'BB lower band touch',
        'Count': len(bb_lower_touch),
        'Next_5_Bars_%': np.nanmean(next_returns),
        'Mean_Reversion_%': (sum([1 for r in next_returns if r > 0]) / len([r for r in next_returns if not np.isnan(r)])) * 100
    })

bb_upper_touch = df[df['close'] >= df['bb_upper']].index
if len(bb_upper_touch) > 30:
    next_returns = [df.loc[i+1:i+5, 'returns'].sum() if i+5 < len(df) else np.nan for i in bb_upper_touch]

    patterns.append({
        'Pattern': 'BB upper band touch',
        'Count': len(bb_upper_touch),
        'Next_5_Bars_%': np.nanmean(next_returns),
        'Mean_Reversion_%': (sum([1 for r in next_returns if r < 0]) / len([r for r in next_returns if not np.isnan(r)])) * 100
    })

print(f"\n✓ Discovered {len(patterns)} sequential patterns")
for p in patterns:
    print(f"  - {p['Pattern']}: {p['Count']} occurrences")

# ============================================================================
# REGIME CLASSIFICATION
# ============================================================================

print("\n[4/8] Classifying market regimes...")

# Trending: ADX-like calculation (simplified)
df['price_change_20'] = df['close'].pct_change(20) * 100
df['is_trending'] = (abs(df['price_change_20']) > 3.0) & (df['atr_ratio'] > 1.2)

# Mean-reverting: Price near SMA, low volatility
df['is_mean_reverting'] = (abs(df['dist_sma20']) < 1.0) & (df['atr_ratio'] < 0.8)

# Explosive: Sudden large moves
df['is_explosive'] = (abs(df['returns']) > 2.0) | (df['volume_ratio'] > 4.0)

# Choppy: Everything else
df['is_choppy'] = ~(df['is_trending'] | df['is_mean_reverting'] | df['is_explosive'])

regime_stats = {
    'Trending': (df['is_trending'].sum() / len(df)) * 100,
    'Mean_Reverting': (df['is_mean_reverting'].sum() / len(df)) * 100,
    'Explosive': (df['is_explosive'].sum() / len(df)) * 100,
    'Choppy': (df['is_choppy'].sum() / len(df)) * 100,
}

print("\nRegime Distribution:")
for regime, pct in regime_stats.items():
    print(f"  {regime:15s}: {pct:5.2f}% of time")

# Average duration in each regime
for regime in ['is_trending', 'is_mean_reverting', 'is_explosive', 'is_choppy']:
    regime_series = df[regime].astype(int)
    durations = []
    current_duration = 0

    for val in regime_series:
        if val == 1:
            current_duration += 1
        else:
            if current_duration > 0:
                durations.append(current_duration)
            current_duration = 0

    if durations:
        avg_duration = np.mean(durations)
        print(f"  Avg {regime.replace('is_', '')} duration: {avg_duration:.1f} bars ({avg_duration:.1f} minutes)")

# ============================================================================
# STATISTICAL EDGES
# ============================================================================

print("\n[5/8] Searching for statistical edges...")

edges = []

# Day of week analysis
day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
day_returns = df.groupby('day_of_week')['returns'].agg(['mean', 'std', 'count'])
day_returns['day_name'] = [day_names[i] for i in day_returns.index]

best_day = day_returns['mean'].idxmax()
worst_day = day_returns['mean'].idxmin()

edges.append({
    'Edge': f'Best day: {day_names[best_day]}',
    'Metric': f"+{day_returns.loc[best_day, 'mean']:.3f}% avg return",
    'Sample_Size': int(day_returns.loc[best_day, 'count']),
    'Confidence': 'Medium' if day_returns.loc[best_day, 'count'] > 1000 else 'Low'
})

edges.append({
    'Edge': f'Worst day: {day_names[worst_day]}',
    'Metric': f"{day_returns.loc[worst_day, 'mean']:.3f}% avg return",
    'Sample_Size': int(day_returns.loc[worst_day, 'count']),
    'Confidence': 'Medium' if day_returns.loc[worst_day, 'count'] > 1000 else 'Low'
})

# Time of day analysis
hour_stats = df.groupby('hour').agg({
    'returns': ['mean', 'std', 'count'],
    'volume': 'mean'
}).round(4)

best_hour_long = hour_stats[('returns', 'mean')].idxmax()
best_hour_short = hour_stats[('returns', 'mean')].idxmin()

edges.append({
    'Edge': f'Best hour for longs: {best_hour_long}:00 UTC',
    'Metric': f"+{hour_stats.loc[best_hour_long, ('returns', 'mean')]:.3f}% avg",
    'Sample_Size': int(hour_stats.loc[best_hour_long, ('returns', 'count')]),
    'Confidence': 'High' if hour_stats.loc[best_hour_long, ('returns', 'count')] > 200 else 'Medium'
})

edges.append({
    'Edge': f'Best hour for shorts: {best_hour_short}:00 UTC',
    'Metric': f"{hour_stats.loc[best_hour_short, ('returns', 'mean')]:.3f}% avg",
    'Sample_Size': int(hour_stats.loc[best_hour_short, ('returns', 'count')]),
    'Confidence': 'High' if hour_stats.loc[best_hour_short, ('returns', 'count')] > 200 else 'Medium'
})

# RSI mean reversion edge
rsi_oversold_bounce = df[(df['rsi_14'] < 30)].copy()
if len(rsi_oversold_bounce) > 30:
    rsi_oversold_bounce['next_5_return'] = rsi_oversold_bounce.index.map(
        lambda i: df.loc[i+1:i+5, 'returns'].sum() if i+5 < len(df) else np.nan
    )
    avg_bounce = rsi_oversold_bounce['next_5_return'].mean()
    win_rate = (rsi_oversold_bounce['next_5_return'] > 0.5).sum() / len(rsi_oversold_bounce) * 100

    edges.append({
        'Edge': 'RSI < 30 mean reversion',
        'Metric': f"+{avg_bounce:.3f}% avg 5-bar return, {win_rate:.1f}% WR",
        'Sample_Size': len(rsi_oversold_bounce),
        'Confidence': 'High' if win_rate > 60 else 'Medium'
    })

# Volume spike continuation
volume_spike_data = df[df['volume_ratio'] > 3.0].copy()
if len(volume_spike_data) > 30:
    volume_spike_data['next_3_return'] = volume_spike_data.index.map(
        lambda i: df.loc[i+1:i+3, 'returns'].sum() if i+3 < len(df) else np.nan
    )
    avg_continuation = volume_spike_data['next_3_return'].mean()
    win_rate = (volume_spike_data['next_3_return'].abs() > 0.3).sum() / len(volume_spike_data) * 100

    edges.append({
        'Edge': 'Volume spike >3x continuation',
        'Metric': f"{avg_continuation:+.3f}% avg 3-bar return, {win_rate:.1f}% move >0.3%",
        'Sample_Size': len(volume_spike_data),
        'Confidence': 'Medium'
    })

print(f"\n✓ Identified {len(edges)} statistical edges")

# ============================================================================
# BEHAVIORAL PROFILE
# ============================================================================

print("\n[6/8] Creating coin personality profile...")

profile = {
    'Volatility': {
        'Avg_Daily_Range_%': ((df.groupby('date')['high'].max() - df.groupby('date')['low'].min()) / df.groupby('date')['open'].first() * 100).mean(),
        'Avg_ATR_%': df['atr_pct'].mean(),
        'Typical_Move_Size_%': df['returns'].abs().mean(),
        'Max_1min_Move_%': df['returns'].abs().max(),
    },
    'Liquidity': {
        'Avg_Volume': df['volume'].mean(),
        'Volume_Consistency_CV': df['volume'].std() / df['volume'].mean(),
        'Volume_Spikes_per_Day': len(df[df['volume_ratio'] > 3]) / 7,
    },
    'Momentum': {
        'Follow_Through_Rate_%': (df[df['returns'].shift(1) > 0.2]['returns'] > 0).sum() / len(df[df['returns'].shift(1) > 0.2]) * 100 if len(df[df['returns'].shift(1) > 0.2]) > 0 else 0,
        'Fade_Rate_%': (df[df['returns'].shift(1) > 0.2]['returns'] < 0).sum() / len(df[df['returns'].shift(1) > 0.2]) * 100 if len(df[df['returns'].shift(1) > 0.2]) > 0 else 0,
    },
    'Risk': {
        'Avg_Loss_Size_%': df[df['returns'] < -0.1]['returns'].mean(),
        'Max_Consecutive_Losses': max([len(list(g)) for k, g in df.groupby((df['returns'] > 0).cumsum()) if k == 0] + [0]),
        'Extreme_Moves_per_Day': len(df[abs(df['returns']) > 2.0]) / 7,
    }
}

print("\nBehavioral Profile:")
for category, metrics in profile.items():
    print(f"\n  {category}:")
    for metric, value in metrics.items():
        if isinstance(value, float):
            print(f"    {metric}: {value:.3f}")
        else:
            print(f"    {metric}: {value}")

# ============================================================================
# SAVE OUTPUTS
# ============================================================================

print("\n[7/8] Generating comprehensive report...")

report = f"""# PIPPIN/USDT PATTERN ANALYSIS REPORT
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Data:** {len(df)} candles ({df['timestamp'].min()} to {df['timestamp'].max()})
**Duration:** 7 days (BingX)

---

## EXECUTIVE SUMMARY

### Top 5 Most Significant Patterns

"""

# Rank patterns by actionability
pattern_df = pd.DataFrame(patterns)
if len(pattern_df) > 0:
    # Calculate edge score (simple heuristic)
    for i, p in enumerate(patterns):
        edge_score = 0
        if 'Next_1_Bar_%' in p:
            edge_score += abs(p['Next_1_Bar_%']) * 2
        if 'Next_5_Bars_%' in p:
            edge_score += abs(p['Next_5_Bars_%'])
        if 'Win_Rate_%' in p and p['Win_Rate_%'] > 55:
            edge_score += 10
        if p['Count'] > 100:
            edge_score += 5
        patterns[i]['Edge_Score'] = edge_score

    top_patterns = sorted(patterns, key=lambda x: x.get('Edge_Score', 0), reverse=True)[:5]

    for i, p in enumerate(top_patterns, 1):
        report += f"{i}. **{p['Pattern']}** ({p['Count']} occurrences)\n"
        for k, v in p.items():
            if k not in ['Pattern', 'Count', 'Edge_Score']:
                if isinstance(v, (int, float)):
                    report += f"   - {k}: {v:.3f}\n"
                else:
                    report += f"   - {k}: {v}\n"
        report += "\n"

report += f"""
### Key Insights

**Regime Character:** PIPPIN spends {regime_stats['Choppy']:.1f}% in choppy regime, {regime_stats['Trending']:.1f}% trending, {regime_stats['Mean_Reverting']:.1f}% mean-reverting

**Best Session:** {session_df.loc[session_df['Avg_Return_%'].idxmax(), 'Session']} (avg {session_df['Avg_Return_%'].max():.3f}% return per candle)

**Volatility:** Average ATR {df['atr_pct'].mean():.3f}%, daily range {profile['Volatility']['Avg_Daily_Range_%']:.2f}%

**Volume Character:** {profile['Liquidity']['Volume_Spikes_per_Day']:.1f} volume spikes >3x per day

**Momentum Type:** {"Follow-through dominant" if profile['Momentum']['Follow_Through_Rate_%'] > 50 else "Mean-reverting / Fade dominant"}

---

## SESSION ANALYSIS

{session_df.to_markdown(index=False)}

### Session Interpretation

"""

best_session = session_df.loc[session_df['Avg_Return_%'].idxmax()]
worst_session = session_df.loc[session_df['Avg_Return_%'].idxmin()]

report += f"""
- **Best performing:** {best_session['Session']} session (+{best_session['Avg_Return_%']:.3f}% avg, {best_session['Volatility_ATR_%']:.3f}% ATR)
- **Worst performing:** {worst_session['Session']} session ({worst_session['Avg_Return_%']:.3f}% avg)
- **Highest volatility:** {session_df.loc[session_df['Volatility_ATR_%'].idxmax(), 'Session']} ({session_df['Volatility_ATR_%'].max():.3f}% ATR)
- **Most liquid:** {session_df.loc[session_df['Avg_Volume'].idxmax(), 'Session']} ({session_df['Avg_Volume'].max():.0f} avg volume)

---

## SEQUENTIAL PATTERN CATALOG

"""

for p in sorted(patterns, key=lambda x: x.get('Count', 0), reverse=True):
    report += f"### {p['Pattern']}\n\n"
    report += f"**Occurrences:** {p['Count']} ({p['Count']/len(df)*100:.2f}% of data)\n\n"

    for k, v in p.items():
        if k not in ['Pattern', 'Count', 'Edge_Score']:
            if isinstance(v, (int, float)):
                report += f"- **{k}:** {v:.3f}\n"
            else:
                report += f"- **{k}:** {v}\n"

    report += "\n"

report += f"""
---

## REGIME ANALYSIS

PIPPIN's market regime distribution:

| Regime | Time % | Avg Duration (mins) |
|--------|--------|---------------------|
| Trending | {regime_stats['Trending']:.2f}% | - |
| Mean-Reverting | {regime_stats['Mean_Reverting']:.2f}% | - |
| Explosive | {regime_stats['Explosive']:.2f}% | - |
| Choppy | {regime_stats['Choppy']:.2f}% | - |

### Regime Interpretation

"""

dominant_regime = max(regime_stats.items(), key=lambda x: x[1])
report += f"PIPPIN is **{dominant_regime[0].lower()}** {dominant_regime[1]:.1f}% of the time. "

if dominant_regime[0] == 'Choppy':
    report += "This suggests generic trend-following and mean-reversion strategies may struggle. Look for volume-based or session-filtered approaches.\n"
elif dominant_regime[0] == 'Trending':
    report += "This suggests trend-following strategies with good follow-through logic will perform well.\n"
elif dominant_regime[0] == 'Mean_Reverting':
    report += "This suggests mean-reversion strategies with tight stops and quick targets will perform well.\n"
elif dominant_regime[0] == 'Explosive':
    report += "This suggests breakout strategies that can capture sudden moves will be profitable.\n"

report += f"""
---

## STATISTICAL EDGES (Ranked by Confidence)

"""

for i, edge in enumerate(sorted(edges, key=lambda x: x['Sample_Size'], reverse=True), 1):
    report += f"{i}. **{edge['Edge']}**\n"
    report += f"   - {edge['Metric']}\n"
    report += f"   - Sample: {edge['Sample_Size']} occurrences\n"
    report += f"   - Confidence: {edge['Confidence']}\n\n"

report += f"""
---

## COIN PERSONALITY PROFILE

### Volatility Character
- **Average daily range:** {profile['Volatility']['Avg_Daily_Range_%']:.2f}%
- **Average ATR:** {profile['Volatility']['Avg_ATR_%']:.3f}%
- **Typical move size:** {profile['Volatility']['Typical_Move_Size_%']:.3f}%
- **Max 1-minute move:** {profile['Volatility']['Max_1min_Move_%']:.2f}%

**Assessment:** {"High volatility" if profile['Volatility']['Avg_ATR_%'] > 1.0 else "Moderate volatility" if profile['Volatility']['Avg_ATR_%'] > 0.5 else "Low volatility"} coin. {"Explosive price action with large sudden moves." if profile['Volatility']['Max_1min_Move_%'] > 5.0 else "Gradual price movements with occasional spikes."}

### Liquidity Character
- **Average volume:** {profile['Liquidity']['Avg_Volume']:.0f}
- **Volume consistency (CV):** {profile['Liquidity']['Volume_Consistency_CV']:.2f}
- **Volume spikes per day:** {profile['Liquidity']['Volume_Spikes_per_Day']:.1f}

**Assessment:** {"Consistent liquidity" if profile['Liquidity']['Volume_Consistency_CV'] < 1.0 else "Sporadic volume"} with {profile['Liquidity']['Volume_Spikes_per_Day']:.0f} major spikes daily. {"Good for consistent execution." if profile['Liquidity']['Volume_Consistency_CV'] < 1.0 else "Watch for slippage during low volume periods."}

### Momentum Character
- **Follow-through rate:** {profile['Momentum']['Follow_Through_Rate_%']:.1f}%
- **Fade rate:** {profile['Momentum']['Fade_Rate_%']:.1f}%

**Assessment:** {"Strong momentum follow-through" if profile['Momentum']['Follow_Through_Rate_%'] > 55 else "Weak momentum - tends to fade"} - {"trend-following may work" if profile['Momentum']['Follow_Through_Rate_%'] > 55 else "mean-reversion preferred"}.

### Risk Character
- **Average loss size:** {profile['Risk']['Avg_Loss_Size_%']:.3f}%
- **Max consecutive losses:** {profile['Risk']['Max_Consecutive_Losses']}
- **Extreme moves per day:** {profile['Risk']['Extreme_Moves_per_Day']:.1f}

**Assessment:** {"Low risk" if abs(profile['Risk']['Avg_Loss_Size_%']) < 0.5 else "Moderate risk" if abs(profile['Risk']['Avg_Loss_Size_%']) < 1.0 else "High risk"} profile. Expect {profile['Risk']['Extreme_Moves_per_Day']:.0f} extreme moves (>2%) daily. {"Black swan events are rare." if profile['Risk']['Extreme_Moves_per_Day'] < 1 else "Watch for sudden volatility spikes."}

---

## STRATEGY IMPLICATIONS

### Recommended Approaches

"""

# Strategy recommendations based on regime and patterns
if regime_stats['Mean_Reverting'] > 40:
    report += """
**1. Mean-Reversion Strategy (PRIMARY)**
- Enter on RSI < 30 or BB lower band touches
- Target 0.5-1.0% profit
- Stop loss 0.3-0.5%
- Best during: """
    report += f"{session_df.loc[session_df['Volatility_ATR_%'].idxmin(), 'Session']} session\n"
    report += f"- **Why:** {regime_stats['Mean_Reverting']:.1f}% time in mean-reverting regime\n\n"

if regime_stats['Trending'] > 20:
    report += """
**2. Trend-Following Strategy**
- Enter on momentum confirmations (3+ consecutive candles)
- Use ATR-based stops (1.5-2.0x ATR)
- Trail profits
- Best during: """
    report += f"{session_df.loc[session_df['Avg_Return_%'].idxmax(), 'Session']} session\n"
    report += f"- **Why:** {regime_stats['Trending']:.1f}% time in trending regime\n\n"

if profile['Liquidity']['Volume_Spikes_per_Day'] > 3:
    report += """
**3. Volume Breakout Strategy**
- Enter on volume spikes >3x average with directional candle
- Target 1-2% (volume spikes suggest strong moves)
- Stop 0.5% (tight - volume = volatility)
- **Why:** """
    report += f"{profile['Liquidity']['Volume_Spikes_per_Day']:.1f} volume spikes daily provide multiple opportunities\n\n"

report += """
### When to AVOID Trading

"""

worst_conditions = []
if regime_stats['Choppy'] > 60:
    worst_conditions.append(f"- During choppy regime ({regime_stats['Choppy']:.1f}% of time) - use regime filters")

worst_hour = hour_stats[('returns', 'mean')].idxmin()
if abs(hour_stats.loc[worst_hour, ('returns', 'mean')]) > 0.01:
    worst_conditions.append(f"- Hour {worst_hour}:00 UTC (worst avg return: {hour_stats.loc[worst_hour, ('returns', 'mean')]:.3f}%)")

if worst_session['Avg_Return_%'] < -0.01:
    worst_conditions.append(f"- {worst_session['Session']} session ({worst_session['Avg_Return_%']:.3f}% avg return)")

if profile['Risk']['Extreme_Moves_per_Day'] > 5:
    worst_conditions.append(f"- After major volatility spike (>2% move) - wait for consolidation")

for condition in worst_conditions:
    report += f"{condition}\n"

report += f"""
---

## DATA LIMITATIONS

⚠️ **IMPORTANT:** This analysis is based on only **7 days** of data ({len(df):,} 1-minute candles).

**Statistical Limitations:**
- Patterns with <100 occurrences have low confidence
- Day-of-week analysis may not be representative
- Rare events (extreme moves) have insufficient sample size
- Session patterns may vary significantly in longer timeframes

**Recommendations:**
1. Validate patterns with additional data (30+ days minimum)
2. Focus on HIGH FREQUENCY patterns (occur multiple times daily)
3. Paper trade strategies before live deployment
4. Re-run this analysis monthly to detect regime changes

---

## NEXT STEPS

1. **Backtest Priority Patterns**
   - Test top 3 patterns with realistic fees (0.1% round-trip)
   - Simulate slippage (0.05% worst case)
   - Validate on out-of-sample data

2. **Focus on Session-Filtered Strategies**
   - {session_df.loc[session_df['Avg_Return_%'].idxmax(), 'Session']} session shows best returns
   - Combine with volume/volatility filters

3. **Risk Management**
   - Max position size based on avg loss ({abs(profile['Risk']['Avg_Loss_Size_%']):.3f}%)
   - Daily loss limit: 3-5x avg loss
   - Monitor for regime changes weekly

4. **Collect More Data**
   - Extend to 30 days minimum
   - Compare to other exchanges (liquidity differences)
   - Track live performance vs backtest

---

**Analysis Complete:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Script:** `pattern_discovery_PIPPIN.py`
**Data Source:** `pippin_7d_bingx.csv`
"""

# Save report
report_path = '/workspaces/Carebiuro_windykacja/trading/results/PIPPIN_PATTERN_ANALYSIS.md'
with open(report_path, 'w') as f:
    f.write(report)

print(f"✓ Report saved: {report_path}")

# ============================================================================
# SAVE RAW DATA
# ============================================================================

print("\n[8/8] Saving raw statistics to CSV...")

# Combine all statistics into CSV
csv_data = []

# Session stats
for _, row in session_df.iterrows():
    csv_data.append({
        'Category': 'Session',
        'Metric': row['Session'],
        'Value': row['Avg_Return_%'],
        'Sample_Size': row['Candles'],
        'Notes': f"ATR: {row['Volatility_ATR_%']:.3f}%"
    })

# Patterns
for p in patterns:
    metric_value = p.get('Next_1_Bar_%', p.get('Next_5_Bars_%', 0))
    csv_data.append({
        'Category': 'Pattern',
        'Metric': p['Pattern'],
        'Value': metric_value,
        'Sample_Size': p['Count'],
        'Notes': f"Win Rate: {p.get('Win_Rate_%', 'N/A')}"
    })

# Edges
for e in edges:
    csv_data.append({
        'Category': 'Edge',
        'Metric': e['Edge'],
        'Value': 0,  # Metric contains text
        'Sample_Size': e['Sample_Size'],
        'Notes': e['Metric']
    })

# Regimes
for regime, pct in regime_stats.items():
    csv_data.append({
        'Category': 'Regime',
        'Metric': regime,
        'Value': pct,
        'Sample_Size': int(len(df) * pct / 100),
        'Notes': f"{pct:.2f}% of time"
    })

csv_df = pd.DataFrame(csv_data)
csv_path = '/workspaces/Carebiuro_windykacja/trading/results/PIPPIN_pattern_stats.csv'
csv_df.to_csv(csv_path, index=False)

print(f"✓ CSV saved: {csv_path}")

print("\n" + "=" * 80)
print("PATTERN DISCOVERY COMPLETE!")
print("=" * 80)
print(f"\nOutputs:")
print(f"  1. Analysis Report: {report_path}")
print(f"  2. Raw Statistics: {csv_path}")
print(f"\nKey Findings:")
print(f"  - {len(patterns)} sequential patterns discovered")
print(f"  - {len(edges)} statistical edges identified")
print(f"  - Dominant regime: {dominant_regime[0]} ({dominant_regime[1]:.1f}%)")
print(f"  - Best session: {session_df.loc[session_df['Avg_Return_%'].idxmax(), 'Session']}")
print(f"\n⚠️  Remember: Only 7 days of data - validate patterns with more data!")
print("=" * 80)
