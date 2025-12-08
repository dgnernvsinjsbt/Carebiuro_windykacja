"""
PEPE Pattern Discovery - Master Analysis
Exhaustive pattern discovery for PEPE cryptocurrency
Analyzes: Sessions, Sequential Patterns, Regimes, Statistical Edges, Behavioral Profile
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# DATA LOADING & PREPARATION
# ============================================================================

print("=" * 80)
print("PEPE PATTERN DISCOVERY - MASTER ANALYSIS")
print("=" * 80)

# Load data
print("\n[1/7] Loading data...")
df = pd.read_csv('./trading/pepe_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"✓ Loaded {len(df):,} candles")
print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"  Duration: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

# Calculate derived features
print("\n[2/7] Calculating technical indicators...")

# Returns
df['returns'] = df['close'].pct_change() * 100  # Percentage returns
df['abs_returns'] = df['returns'].abs()

# Price metrics
df['body'] = ((df['close'] - df['open']) / df['open'] * 100).abs()
df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
df['total_wick'] = df['upper_wick'] + df['lower_wick']
df['wick_ratio'] = df['total_wick'] / (df['high'] - df['low'] + 1e-10)

# Moving averages
df['sma_20'] = df['close'].rolling(20).mean()
df['sma_50'] = df['close'].rolling(50).mean()
df['sma_200'] = df['close'].rolling(200).mean()

# Distance from SMAs
df['dist_sma20'] = (df['close'] - df['sma_20']) / df['sma_20'] * 100
df['dist_sma50'] = (df['close'] - df['sma_50']) / df['sma_50'] * 100
df['dist_sma200'] = (df['close'] - df['sma_200']) / df['sma_200'] * 100

# ATR (Average True Range)
df['tr'] = df[['high', 'low']].apply(lambda x: x['high'] - x['low'], axis=1)
df['atr'] = df['tr'].rolling(14).mean()
df['atr_pct'] = df['atr'] / df['close'] * 100

# RSI
def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

df['rsi'] = calculate_rsi(df['close'])

# Bollinger Bands
df['bb_middle'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

# Volume metrics
df['vol_sma'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / (df['vol_sma'] + 1e-10)

# Consecutive candles
df['is_green'] = (df['close'] > df['open']).astype(int)
df['is_red'] = (df['close'] < df['open']).astype(int)

def count_consecutive(series):
    """Count consecutive occurrences"""
    result = series * 0
    count = 0
    for i in range(len(series)):
        if series.iloc[i] == 1:
            count += 1
            result.iloc[i] = count
        else:
            count = 0
    return result

df['consecutive_green'] = count_consecutive(df['is_green'])
df['consecutive_red'] = count_consecutive(df['is_red'])

# Time features
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday
df['date'] = df['timestamp'].dt.date

# Define sessions (UTC)
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

print(f"✓ Calculated {len(df.columns)} features")

# ============================================================================
# SESSION ANALYSIS
# ============================================================================

print("\n[3/7] Analyzing trading sessions...")

session_stats = []
for session in ['Asia', 'Europe', 'US', 'Overnight']:
    session_df = df[df['session'] == session].copy()

    if len(session_df) == 0:
        continue

    # Calculate statistics
    avg_return = session_df['returns'].mean()
    volatility = session_df['returns'].std()
    avg_atr = session_df['atr_pct'].mean()
    avg_volume_ratio = session_df['vol_ratio'].mean()

    # Win rates
    long_wins = len(session_df[session_df['returns'] > 0])
    long_total = len(session_df[session_df['returns'] != 0])
    long_winrate = long_wins / long_total * 100 if long_total > 0 else 0

    short_wins = len(session_df[session_df['returns'] < 0])
    short_winrate = short_wins / long_total * 100 if long_total > 0 else 0

    # Best/worst hours
    hourly_returns = session_df.groupby('hour')['returns'].mean()
    best_hour = hourly_returns.idxmax() if len(hourly_returns) > 0 else None
    worst_hour = hourly_returns.idxmin() if len(hourly_returns) > 0 else None

    session_stats.append({
        'Session': session,
        'Avg_Return_%': avg_return,
        'Volatility_%': volatility,
        'Avg_ATR_%': avg_atr,
        'Avg_Volume_Ratio': avg_volume_ratio,
        'Long_WinRate_%': long_winrate,
        'Short_WinRate_%': short_winrate,
        'Best_Hour': best_hour,
        'Worst_Hour': worst_hour,
        'Candles': len(session_df)
    })

session_df_stats = pd.DataFrame(session_stats)
print("\n" + "=" * 80)
print("SESSION STATISTICS")
print("=" * 80)
print(session_df_stats.to_string(index=False))

# Save session stats
session_df_stats.to_csv('./trading/results/PEPE_session_stats.csv', index=False)

# ============================================================================
# SEQUENTIAL PATTERN ANALYSIS
# ============================================================================

print("\n[4/7] Discovering sequential patterns...")

sequential_patterns = []

# Pattern 1: Large body candles
print("  → Analyzing large body candles (>2%)...")
large_body = df[df['body'] > 2.0].copy()
if len(large_body) > 0:
    for horizon in [1, 3, 5]:
        avg_return = []
        for idx in large_body.index:
            if idx + horizon < len(df):
                avg_return.append(df.loc[idx+1:idx+horizon, 'returns'].sum())

        if len(avg_return) > 0:
            sequential_patterns.append({
                'Pattern': f'After >2% body candle',
                'Horizon': f'{horizon} candles',
                'Avg_Return_%': np.mean(avg_return),
                'WinRate_%': len([x for x in avg_return if x > 0]) / len(avg_return) * 100,
                'Sample_Size': len(avg_return)
            })

# Pattern 2: Consecutive candles
print("  → Analyzing consecutive candles (3+)...")
for direction, col in [('green', 'consecutive_green'), ('red', 'consecutive_red')]:
    consecutive_3plus = df[df[col] >= 3].copy()
    if len(consecutive_3plus) > 0:
        next_returns = []
        for idx in consecutive_3plus.index:
            if idx + 1 < len(df):
                next_returns.append(df.loc[idx+1, 'returns'])

        if len(next_returns) > 0:
            sequential_patterns.append({
                'Pattern': f'After 3+ consecutive {direction}',
                'Horizon': '1 candle',
                'Avg_Return_%': np.mean(next_returns),
                'WinRate_%': len([x for x in next_returns if (x > 0 and direction == 'green') or (x < 0 and direction == 'red')]) / len(next_returns) * 100,
                'Sample_Size': len(next_returns)
            })

# Pattern 3: Rejection wicks
print("  → Analyzing rejection wicks...")
rejection_wicks = df[df['wick_ratio'] > 0.6].copy()
if len(rejection_wicks) > 0:
    next_returns = []
    for idx in rejection_wicks.index:
        if idx + 1 < len(df):
            next_returns.append(df.loc[idx+1, 'returns'])

    if len(next_returns) > 0:
        sequential_patterns.append({
            'Pattern': 'After rejection wick (>60% of range)',
            'Horizon': '1 candle',
            'Avg_Return_%': np.mean(next_returns),
            'WinRate_%': len([x for x in next_returns if x > 0]) / len(next_returns) * 100,
            'Sample_Size': len(next_returns)
        })

# Pattern 4: Volume spikes
print("  → Analyzing volume spikes...")
volume_spikes = df[df['vol_ratio'] > 3.0].copy()
if len(volume_spikes) > 0:
    for horizon in [1, 3, 5]:
        returns = []
        for idx in volume_spikes.index:
            if idx + horizon < len(df):
                returns.append(df.loc[idx+1:idx+horizon, 'returns'].sum())

        if len(returns) > 0:
            sequential_patterns.append({
                'Pattern': 'After volume spike (>3x avg)',
                'Horizon': f'{horizon} candles',
                'Avg_Return_%': np.mean(returns),
                'WinRate_%': len([x for x in returns if x > 0]) / len(returns) * 100,
                'Sample_Size': len(returns)
            })

# Pattern 5: Bollinger Band touches
print("  → Analyzing Bollinger Band touches...")
bb_upper_touch = df[df['bb_position'] >= 0.95].copy()
bb_lower_touch = df[df['bb_position'] <= 0.05].copy()

for band_type, band_df in [('Upper BB touch', bb_upper_touch), ('Lower BB touch', bb_lower_touch)]:
    if len(band_df) > 0:
        for horizon in [1, 3, 5]:
            returns = []
            for idx in band_df.index:
                if idx + horizon < len(df):
                    returns.append(df.loc[idx+1:idx+horizon, 'returns'].sum())

            if len(returns) > 0:
                sequential_patterns.append({
                    'Pattern': f'After {band_type}',
                    'Horizon': f'{horizon} candles',
                    'Avg_Return_%': np.mean(returns),
                    'WinRate_%': len([x for x in returns if (x < 0 and 'Upper' in band_type) or (x > 0 and 'Lower' in band_type)]) / len(returns) * 100,
                    'Sample_Size': len(returns)
                })

# Pattern 6: SMA breakouts
print("  → Analyzing SMA breakouts...")
for sma_name, sma_col in [('SMA20', 'sma_20'), ('SMA50', 'sma_50')]:
    df['above_sma'] = df['close'] > df[sma_col]
    df['sma_cross'] = df['above_sma'].diff()

    # Bullish crossover
    bullish_cross = df[df['sma_cross'] == 1].copy()
    if len(bullish_cross) > 0:
        for horizon in [1, 5, 10]:
            returns = []
            for idx in bullish_cross.index:
                if idx + horizon < len(df):
                    returns.append(df.loc[idx+1:idx+horizon, 'returns'].sum())

            if len(returns) > 0:
                sequential_patterns.append({
                    'Pattern': f'After bullish {sma_name} cross',
                    'Horizon': f'{horizon} candles',
                    'Avg_Return_%': np.mean(returns),
                    'WinRate_%': len([x for x in returns if x > 0]) / len(returns) * 100,
                    'Sample_Size': len(returns)
                })

sequential_df = pd.DataFrame(sequential_patterns)
if len(sequential_df) > 0:
    sequential_df = sequential_df.sort_values('Avg_Return_%', ascending=False)
    print("\n" + "=" * 80)
    print("TOP 10 SEQUENTIAL PATTERNS")
    print("=" * 80)
    print(sequential_df.head(10).to_string(index=False))
    sequential_df.to_csv('./trading/results/PEPE_sequential_patterns.csv', index=False)

# ============================================================================
# REGIME CLASSIFICATION
# ============================================================================

print("\n[5/7] Classifying market regimes...")

# Define regimes
df['regime'] = 'UNKNOWN'

# TRENDING: Strong directional moves, price away from SMA
trending_condition = (
    ((df['close'] > df['sma_50']) & (df['dist_sma50'] > 1.0)) |  # Strong uptrend
    ((df['close'] < df['sma_50']) & (df['dist_sma50'] < -1.0))    # Strong downtrend
)
df.loc[trending_condition, 'regime'] = 'TRENDING'

# EXPLOSIVE: Large ATR and large body candles
explosive_condition = (df['atr_pct'] > df['atr_pct'].quantile(0.75)) & (df['body'] > 1.5)
df.loc[explosive_condition, 'regime'] = 'EXPLOSIVE'

# MEAN-REVERTING: Close to SMA, BB position in middle
mean_revert_condition = (
    (df['dist_sma50'].abs() < 0.5) &
    (df['bb_position'] > 0.3) &
    (df['bb_position'] < 0.7)
)
df.loc[mean_revert_condition, 'regime'] = 'MEAN_REVERTING'

# CHOPPY: High wick ratio, low body
choppy_condition = (df['wick_ratio'] > 0.5) & (df['body'] < 0.5)
df.loc[choppy_condition, 'regime'] = 'CHOPPY'

# Calculate regime statistics
regime_stats = df['regime'].value_counts()
regime_pct = regime_stats / len(df) * 100

print("\n" + "=" * 80)
print("REGIME DISTRIBUTION")
print("=" * 80)
for regime, pct in regime_pct.items():
    print(f"{regime:20s}: {pct:6.2f}% ({regime_stats[regime]:,} candles)")

# Regime performance
regime_analysis = []
for regime in df['regime'].unique():
    regime_df = df[df['regime'] == regime]
    if len(regime_df) > 0:
        regime_analysis.append({
            'Regime': regime,
            'Percentage_%': len(regime_df) / len(df) * 100,
            'Avg_Return_%': regime_df['returns'].mean(),
            'Volatility_%': regime_df['returns'].std(),
            'Long_WinRate_%': len(regime_df[regime_df['returns'] > 0]) / len(regime_df) * 100,
            'Avg_Duration_Minutes': len(regime_df) / (regime_stats[regime] / (regime_df.groupby((regime_df['regime'] != regime_df['regime'].shift()).cumsum()).size().mean() if len(regime_df) > 0 else 1))
        })

regime_analysis_df = pd.DataFrame(regime_analysis)
print("\n" + "=" * 80)
print("REGIME PERFORMANCE")
print("=" * 80)
print(regime_analysis_df.to_string(index=False))
regime_analysis_df.to_csv('./trading/results/PEPE_regime_analysis.csv', index=False)

# ============================================================================
# STATISTICAL EDGES
# ============================================================================

print("\n[6/7] Discovering statistical edges...")

statistical_edges = []

# Day of week patterns
print("  → Analyzing day-of-week patterns...")
for day in range(7):
    day_df = df[df['day_of_week'] == day]
    if len(day_df) > 30:
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        statistical_edges.append({
            'Edge_Type': 'Day_of_Week',
            'Condition': day_names[day],
            'Avg_Return_%': day_df['returns'].mean(),
            'Volatility_%': day_df['returns'].std(),
            'WinRate_%': len(day_df[day_df['returns'] > 0]) / len(day_df) * 100,
            'Sample_Size': len(day_df)
        })

# Hour of day patterns
print("  → Analyzing hour-of-day patterns...")
for hour in range(24):
    hour_df = df[df['hour'] == hour]
    if len(hour_df) > 30:
        statistical_edges.append({
            'Edge_Type': 'Hour_of_Day',
            'Condition': f'{hour:02d}:00',
            'Avg_Return_%': hour_df['returns'].mean(),
            'Volatility_%': hour_df['returns'].std(),
            'WinRate_%': len(hour_df[hour_df['returns'] > 0]) / len(hour_df) * 100,
            'Sample_Size': len(hour_df)
        })

# RSI extremes
print("  → Analyzing RSI extremes...")
for threshold, direction in [(30, 'Oversold'), (70, 'Overbought')]:
    if direction == 'Oversold':
        rsi_df = df[df['rsi'] < threshold].copy()
    else:
        rsi_df = df[df['rsi'] > threshold].copy()

    if len(rsi_df) > 30:
        next_returns = []
        for idx in rsi_df.index:
            if idx + 5 < len(df):
                next_returns.append(df.loc[idx+1:idx+5, 'returns'].sum())

        if len(next_returns) > 0:
            statistical_edges.append({
                'Edge_Type': 'RSI_Extreme',
                'Condition': f'{direction} (RSI {threshold})',
                'Avg_Return_%': np.mean(next_returns),
                'Volatility_%': np.std(next_returns),
                'WinRate_%': len([x for x in next_returns if (x > 0 and direction == 'Oversold') or (x < 0 and direction == 'Overbought')]) / len(next_returns) * 100,
                'Sample_Size': len(next_returns)
            })

# Distance from SMA patterns
print("  → Analyzing SMA distance patterns...")
for threshold, direction in [(2.0, 'Far_Above'), (-2.0, 'Far_Below')]:
    if direction == 'Far_Above':
        sma_df = df[df['dist_sma50'] > threshold].copy()
    else:
        sma_df = df[df['dist_sma50'] < threshold].copy()

    if len(sma_df) > 30:
        next_returns = []
        for idx in sma_df.index:
            if idx + 10 < len(df):
                next_returns.append(df.loc[idx+1:idx+10, 'returns'].sum())

        if len(next_returns) > 0:
            statistical_edges.append({
                'Edge_Type': 'SMA_Distance',
                'Condition': f'{direction} SMA50 ({abs(threshold)}%)',
                'Avg_Return_%': np.mean(next_returns),
                'Volatility_%': np.std(next_returns),
                'WinRate_%': len([x for x in next_returns if x < 0]) / len(next_returns) * 100,  # Mean reversion expectation
                'Sample_Size': len(next_returns)
            })

statistical_edges_df = pd.DataFrame(statistical_edges)
if len(statistical_edges_df) > 0:
    # Sort by absolute return
    statistical_edges_df['Abs_Return'] = statistical_edges_df['Avg_Return_%'].abs()
    statistical_edges_df = statistical_edges_df.sort_values('Abs_Return', ascending=False)
    print("\n" + "=" * 80)
    print("TOP 15 STATISTICAL EDGES")
    print("=" * 80)
    print(statistical_edges_df.head(15)[['Edge_Type', 'Condition', 'Avg_Return_%', 'WinRate_%', 'Sample_Size']].to_string(index=False))
    statistical_edges_df.to_csv('./trading/results/PEPE_statistical_edges.csv', index=False)

# ============================================================================
# BEHAVIORAL PROFILE
# ============================================================================

print("\n[7/7] Creating behavioral profile...")

profile = {
    'avg_daily_range_%': df.groupby('date').apply(lambda x: ((x['high'].max() - x['low'].min()) / x['open'].iloc[0] * 100)).mean(),
    'typical_move_before_pullback_%': df[df['returns'].abs() > 1.0]['returns'].abs().quantile(0.75),
    'trend_pct': regime_pct.get('TRENDING', 0),
    'chop_pct': regime_pct.get('CHOPPY', 0),
    'explosive_pct': regime_pct.get('EXPLOSIVE', 0),
    'avg_volume': df['volume'].mean(),
    'volume_std': df['volume'].std(),
    'momentum_followthrough_%': len(df[(df['returns'].shift(1) > 1.0) & (df['returns'] > 0)]) / len(df[df['returns'].shift(1) > 1.0]) * 100 if len(df[df['returns'].shift(1) > 1.0]) > 0 else 0,
    'avg_win_size_%': df[df['returns'] > 0]['returns'].mean(),
    'avg_loss_size_%': df[df['returns'] < 0]['returns'].mean(),
    'max_drawdown_observed_%': (df['close'].cummax() - df['close']).max() / df['close'].cummax().max() * 100,
    'extreme_moves_per_day': len(df[df['returns'].abs() > 3.0]) / df['date'].nunique()
}

print("\n" + "=" * 80)
print("PEPE BEHAVIORAL PROFILE")
print("=" * 80)
for key, value in profile.items():
    print(f"{key:40s}: {value:10.3f}")

# ============================================================================
# GENERATE MARKDOWN REPORT
# ============================================================================

print("\n[8/8] Generating comprehensive report...")

report = f"""# PEPE Pattern Analysis - Master Discovery Report

**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Data Period**: {df['timestamp'].min()} to {df['timestamp'].max()}
**Total Candles**: {len(df):,} (1-minute timeframe)
**Duration**: {(df['timestamp'].max() - df['timestamp'].min()).days} days

---

## Executive Summary - Top 5 Patterns Discovered

"""

# Add top sequential patterns
if len(sequential_df) > 0:
    report += "### Top Sequential Patterns\n\n"
    for idx, row in sequential_df.head(5).iterrows():
        report += f"**{idx+1}. {row['Pattern']}** (Horizon: {row['Horizon']})\n"
        report += f"   - Average Return: {row['Avg_Return_%']:.3f}%\n"
        report += f"   - Win Rate: {row['WinRate_%']:.1f}%\n"
        report += f"   - Sample Size: {row['Sample_Size']}\n\n"

# Add session analysis
report += f"""
---

## Session Analysis Results

{session_df_stats.to_markdown(index=False)}

### Key Session Insights:
"""

best_session = session_df_stats.loc[session_df_stats['Avg_Return_%'].idxmax()]
most_volatile = session_df_stats.loc[session_df_stats['Volatility_%'].idxmax()]

report += f"""
- **Best Performance**: {best_session['Session']} session (Avg: {best_session['Avg_Return_%']:.4f}%)
- **Most Volatile**: {most_volatile['Session']} session (StdDev: {most_volatile['Volatility_%']:.3f}%)
- **Best Long Win Rate**: {session_df_stats.loc[session_df_stats['Long_WinRate_%'].idxmax(), 'Session']} ({session_df_stats['Long_WinRate_%'].max():.1f}%)
- **Best Short Win Rate**: {session_df_stats.loc[session_df_stats['Short_WinRate_%'].idxmax(), 'Session']} ({session_df_stats['Short_WinRate_%'].max():.1f}%)

---

## Market Regime Analysis

{regime_analysis_df.to_markdown(index=False)}

### Regime Insights:
- PEPE spends **{regime_pct.get('TRENDING', 0):.1f}%** of time in trending mode
- **{regime_pct.get('MEAN_REVERTING', 0):.1f}%** in mean-reverting conditions
- **{regime_pct.get('EXPLOSIVE', 0):.1f}%** in explosive/breakout mode
- **{regime_pct.get('CHOPPY', 0):.1f}%** in choppy/unplayable conditions

**Strategy Implication**: {"PEPE is primarily a trending asset - trend-following strategies recommended" if regime_pct.get('TRENDING', 0) > 40 else "PEPE shows balanced regime distribution - hybrid strategies recommended"}

---

## Statistical Edges (Top 15)

"""

if len(statistical_edges_df) > 0:
    report += statistical_edges_df.head(15)[['Edge_Type', 'Condition', 'Avg_Return_%', 'WinRate_%', 'Sample_Size']].to_markdown(index=False)

report += f"""

---

## PEPE Behavioral Profile

### Volatility Character:
- **Average Daily Range**: {profile['avg_daily_range_%']:.2f}%
- **Typical Move Size**: {profile['typical_move_before_pullback_%']:.2f}% before pullback
- **Extreme Moves/Day**: {profile['extreme_moves_per_day']:.1f} (>3% moves)
- **Character**: {"Explosive mover" if profile['avg_daily_range_%'] > 10 else "Moderate mover" if profile['avg_daily_range_%'] > 5 else "Gradual mover"}

### Liquidity Character:
- **Average Volume**: {profile['avg_volume']:,.0f}
- **Volume Variability**: {profile['volume_std']:,.0f} (StdDev)
- **Assessment**: {"Consistent liquidity" if profile['volume_std'] / profile['avg_volume'] < 1.0 else "Sporadic liquidity - use limit orders"}

### Momentum Character:
- **Follow-Through Rate**: {profile['momentum_followthrough_%']:.1f}% (after >1% move)
- **Average Win**: {profile['avg_win_size_%']:.3f}%
- **Average Loss**: {profile['avg_loss_size_%']:.3f}%
- **Win/Loss Ratio**: {abs(profile['avg_win_size_%'] / profile['avg_loss_size_%']):.2f}x

### Risk Character:
- **Max Observed Drawdown**: {profile['max_drawdown_observed_%']:.2f}%
- **Risk Assessment**: {"High volatility - use tight stops" if profile['avg_daily_range_%'] > 10 else "Moderate volatility - standard risk management"}

---

## Strategy Implications

### ✅ RECOMMENDED Strategies:

"""

# Determine best strategy types
if regime_pct.get('TRENDING', 0) > 40:
    report += """
**1. TREND-FOLLOWING** (Primary Strategy)
- PEPE spends significant time trending
- Use SMA crossovers and distance from SMA for entries
- Hold through pullbacks in strong trends
- Best sessions: """
    report += f"{session_df_stats.loc[session_df_stats['Avg_Return_%'].idxmax(), 'Session']}\n\n"

if regime_pct.get('MEAN_REVERTING', 0) > 30:
    report += """
**2. MEAN-REVERSION** (Secondary Strategy)
- Use Bollinger Band extremes for entries
- RSI oversold/overbought confirmation
- Quick profit targets (not a strong mean-reverter)
- Best sessions: """
    report += f"{session_df_stats.loc[session_df_stats['Volatility_%'].idxmin(), 'Session']}\n\n"

if regime_pct.get('EXPLOSIVE', 0) > 10:
    report += """
**3. BREAKOUT/MOMENTUM** (Opportunistic)
- Explosive moves occur frequently enough to trade
- Use volume spikes and large body candles for confirmation
- Wide stops, large profit targets
- Most common during: """
    report += f"{most_volatile['Session']} session\n\n"

report += f"""
### ❌ AVOID Trading When:

- Regime is **CHOPPY** ({regime_pct.get('CHOPPY', 0):.1f}% of time) - high wick ratios, small bodies
- During {session_df_stats.loc[session_df_stats['Volatility_%'].idxmin(), 'Session']} session (lowest opportunity)
- After extreme moves without volume confirmation (likely fake-outs)

---

## High-Confidence Patterns (Win Rate > 60% or Strong Returns)

"""

high_conf_patterns = []

# From sequential patterns
if len(sequential_df) > 0:
    high_conf_seq = sequential_df[(sequential_df['WinRate_%'] > 60) | (sequential_df['Avg_Return_%'].abs() > 0.1)]
    if len(high_conf_seq) > 0:
        report += "### Sequential Patterns:\n"
        for idx, row in high_conf_seq.head(5).iterrows():
            report += f"- **{row['Pattern']}** → {row['Avg_Return_%']:.3f}% avg return, {row['WinRate_%']:.1f}% win rate (n={row['Sample_Size']})\n"

# From statistical edges
if len(statistical_edges_df) > 0:
    high_conf_edges = statistical_edges_df[(statistical_edges_df['WinRate_%'] > 60) | (statistical_edges_df['Avg_Return_%'].abs() > 0.05)]
    if len(high_conf_edges) > 0:
        report += "\n### Statistical Edges:\n"
        for idx, row in high_conf_edges.head(5).iterrows():
            report += f"- **{row['Edge_Type']}: {row['Condition']}** → {row['Avg_Return_%']:.3f}% avg return, {row['WinRate_%']:.1f}% win rate (n={row['Sample_Size']})\n"

report += f"""

---

## Next Steps - Strategy Development

Based on this analysis, the following strategy types should be developed and backtested:

1. **Primary**: {"Trend-following with SMA distance filters" if regime_pct.get('TRENDING', 0) > 40 else "Mean-reversion with BB bands and RSI"}
2. **Secondary**: Volume-confirmed breakout strategies
3. **Filters**: Avoid CHOPPY regime, focus on high-volatility sessions

---

## Data Files Generated

- `PEPE_session_stats.csv` - Session-by-session statistics
- `PEPE_sequential_patterns.csv` - Complete sequential pattern analysis
- `PEPE_regime_analysis.csv` - Regime classification results
- `PEPE_statistical_edges.csv` - All statistical edges discovered

**Analysis Complete** ✓

"""

# Save report
with open('./trading/results/PEPE_PATTERN_ANALYSIS.md', 'w') as f:
    f.write(report)

print("\n" + "=" * 80)
print("✓ Analysis complete!")
print("=" * 80)
print(f"\nFiles saved:")
print(f"  → ./trading/results/PEPE_PATTERN_ANALYSIS.md")
print(f"  → ./trading/results/PEPE_session_stats.csv")
print(f"  → ./trading/results/PEPE_sequential_patterns.csv")
print(f"  → ./trading/results/PEPE_regime_analysis.csv")
print(f"  → ./trading/results/PEPE_statistical_edges.csv")
print("\n" + "=" * 80)
