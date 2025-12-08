"""
PENGU Pattern Discovery - Exhaustive Analysis
Analyzes 30 days of 1-minute PENGU data to find all exploitable patterns
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import warnings
warnings.filterwarnings('ignore')

# Load data
print("Loading PENGU data...")
df = pd.read_csv('pengu_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
print("Calculating indicators...")
df['body'] = ((df['close'] - df['open']) / df['open'] * 100).round(4)
df['range'] = ((df['high'] - df['low']) / df['open'] * 100).round(4)
df['upper_wick'] = ((df['high'] - df[['open', 'close']].max(axis=1)) / df['open'] * 100).round(4)
df['lower_wick'] = ((df[['open', 'close']].min(axis=1) - df['low']) / df['open'] * 100).round(4)

# SMAs
for period in [20, 50, 200]:
    df[f'sma{period}'] = df['close'].rolling(period).mean()
    df[f'dist_sma{period}'] = ((df['close'] - df[f'sma{period}']) / df[f'sma{period}'] * 100).round(4)

# Bollinger Bands
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
df['bb_position'] = ((df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']) * 100).round(2)

# RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = (100 - (100 / (1 + rs))).round(2)

# ATR
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()
df['atr_pct'] = (df['atr'] / df['close'] * 100).round(4)

# Volume analysis
df['vol_ma'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = (df['volume'] / df['vol_ma']).round(2)

# Forward returns
for i in [1, 3, 5, 10, 20]:
    df[f'fwd_{i}'] = ((df['close'].shift(-i) - df['close']) / df['close'] * 100).round(4)

# Session classification
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek
df['session'] = pd.cut(df['hour'], bins=[0, 8, 14, 21, 24],
                       labels=['Asia', 'Europe', 'US', 'Overnight'],
                       include_lowest=True, right=False)

print(f"Data loaded: {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Price range: ${df['close'].min():.6f} - ${df['close'].max():.6f}")

# ============================================================================
# 1. SESSION ANALYSIS
# ============================================================================
print("\n" + "="*80)
print("SESSION ANALYSIS")
print("="*80)

session_stats = []
for session in ['Asia', 'Europe', 'US', 'Overnight']:
    session_df = df[df['session'] == session].copy()

    # Overall stats
    avg_return = session_df['body'].mean()
    avg_volatility = session_df['range'].mean()
    avg_volume = session_df['volume'].mean()

    # Long performance (next candle after bullish body >0.3%)
    bullish = session_df[session_df['body'] > 0.3]
    long_win_rate = (bullish['fwd_1'] > 0.1).sum() / len(bullish) * 100 if len(bullish) > 0 else 0
    avg_long_return = bullish['fwd_1'].mean() if len(bullish) > 0 else 0

    # Short performance (next candle after bearish body <-0.3%)
    bearish = session_df[session_df['body'] < -0.3]
    short_win_rate = (bearish['fwd_1'] < -0.1).sum() / len(bearish) * 100 if len(bearish) > 0 else 0
    avg_short_return = bearish['fwd_1'].mean() if len(bearish) > 0 else 0

    session_stats.append({
        'session': session,
        'candles': len(session_df),
        'avg_body': avg_return,
        'avg_range': avg_volatility,
        'avg_volume': avg_volume,
        'long_signals': len(bullish),
        'long_win_rate': long_win_rate,
        'avg_long_fwd1': avg_long_return,
        'short_signals': len(bearish),
        'short_win_rate': short_win_rate,
        'avg_short_fwd1': avg_short_return
    })

session_df = pd.DataFrame(session_stats)
print(session_df.to_string(index=False))
session_df.to_csv('results/PENGU_session_stats.csv', index=False)

# Hour-by-hour analysis
print("\nBest/Worst Hours:")
hourly_stats = df.groupby('hour').agg({
    'body': 'mean',
    'range': 'mean',
    'volume': 'mean',
    'fwd_1': 'mean'
}).round(4)
hourly_stats = hourly_stats.sort_values('fwd_1', ascending=False)
print("Top 5 hours for momentum continuation:")
print(hourly_stats.head().to_string())
print("\nWorst 5 hours (reversal hours):")
print(hourly_stats.tail().to_string())

# ============================================================================
# 2. SEQUENTIAL PATTERNS
# ============================================================================
print("\n" + "="*80)
print("SEQUENTIAL PATTERNS")
print("="*80)

sequential_patterns = []

# Pattern 1: After explosive candle (>2% body)
print("\nPattern 1: After >2% body candle")
explosive_bull = df[df['body'] > 2.0].copy()
explosive_bear = df[df['body'] < -2.0].copy()

if len(explosive_bull) > 0:
    print(f"Explosive bullish candles: {len(explosive_bull)}")
    print(f"  Next 1 candle avg: {explosive_bull['fwd_1'].mean():.4f}%")
    print(f"  Next 3 candles avg: {explosive_bull['fwd_3'].mean():.4f}%")
    print(f"  Next 5 candles avg: {explosive_bull['fwd_5'].mean():.4f}%")
    print(f"  Continuation rate (>0.1%): {(explosive_bull['fwd_1'] > 0.1).sum() / len(explosive_bull) * 100:.2f}%")

    sequential_patterns.append({
        'pattern': 'explosive_bull_>2%',
        'count': len(explosive_bull),
        'fwd_1_avg': explosive_bull['fwd_1'].mean(),
        'fwd_3_avg': explosive_bull['fwd_3'].mean(),
        'fwd_5_avg': explosive_bull['fwd_5'].mean(),
        'win_rate_fwd1': (explosive_bull['fwd_1'] > 0.1).sum() / len(explosive_bull) * 100,
        'edge': 'continuation' if explosive_bull['fwd_1'].mean() > 0.1 else 'reversal'
    })

if len(explosive_bear) > 0:
    print(f"\nExplosive bearish candles: {len(explosive_bear)}")
    print(f"  Next 1 candle avg: {explosive_bear['fwd_1'].mean():.4f}%")
    print(f"  Next 3 candles avg: {explosive_bear['fwd_3'].mean():.4f}%")
    print(f"  Next 5 candles avg: {explosive_bear['fwd_5'].mean():.4f}%")
    print(f"  Continuation rate (<-0.1%): {(explosive_bear['fwd_1'] < -0.1).sum() / len(explosive_bear) * 100:.2f}%")

    sequential_patterns.append({
        'pattern': 'explosive_bear_<-2%',
        'count': len(explosive_bear),
        'fwd_1_avg': explosive_bear['fwd_1'].mean(),
        'fwd_3_avg': explosive_bear['fwd_3'].mean(),
        'fwd_5_avg': explosive_bear['fwd_5'].mean(),
        'win_rate_fwd1': (explosive_bear['fwd_1'] < -0.1).sum() / len(explosive_bear) * 100,
        'edge': 'continuation' if explosive_bear['fwd_1'].mean() < -0.1 else 'reversal'
    })

# Pattern 2: Consecutive candles (streaks)
print("\n\nPattern 2: Consecutive Green/Red Streaks")
df['is_green'] = df['body'] > 0
df['is_red'] = df['body'] < 0
df['streak'] = (df['is_green'] != df['is_green'].shift()).cumsum()
df['streak_length'] = df.groupby('streak').cumcount() + 1

# After 3+ consecutive greens
three_green = df[(df['is_green']) & (df['streak_length'] >= 3)].copy()
if len(three_green) > 0:
    print(f"After 3+ consecutive green: {len(three_green)}")
    print(f"  Next candle avg: {three_green['fwd_1'].mean():.4f}%")
    print(f"  Reversal rate (<-0.1%): {(three_green['fwd_1'] < -0.1).sum() / len(three_green) * 100:.2f}%")

    sequential_patterns.append({
        'pattern': '3+_consecutive_green',
        'count': len(three_green),
        'fwd_1_avg': three_green['fwd_1'].mean(),
        'fwd_3_avg': three_green['fwd_3'].mean(),
        'fwd_5_avg': three_green['fwd_5'].mean(),
        'win_rate_fwd1': (three_green['fwd_1'] < -0.1).sum() / len(three_green) * 100,
        'edge': 'reversal' if three_green['fwd_1'].mean() < 0 else 'continuation'
    })

# After 3+ consecutive reds
three_red = df[(df['is_red']) & (df['streak_length'] >= 3)].copy()
if len(three_red) > 0:
    print(f"\nAfter 3+ consecutive red: {len(three_red)}")
    print(f"  Next candle avg: {three_red['fwd_1'].mean():.4f}%")
    print(f"  Reversal rate (>0.1%): {(three_red['fwd_1'] > 0.1).sum() / len(three_red) * 100:.2f}%")

    sequential_patterns.append({
        'pattern': '3+_consecutive_red',
        'count': len(three_red),
        'fwd_1_avg': three_red['fwd_1'].mean(),
        'fwd_3_avg': three_red['fwd_3'].mean(),
        'fwd_5_avg': three_red['fwd_5'].mean(),
        'win_rate_fwd1': (three_red['fwd_1'] > 0.1).sum() / len(three_red) * 100,
        'edge': 'reversal' if three_red['fwd_1'].mean() > 0 else 'continuation'
    })

# Pattern 3: Wick rejections
print("\n\nPattern 3: Wick Rejections")
# Upper wick rejection (wick > 2x body)
df['wick_body_ratio_upper'] = df['upper_wick'] / abs(df['body']).replace(0, 0.01)
df['wick_body_ratio_lower'] = df['lower_wick'] / abs(df['body']).replace(0, 0.01)

upper_rejection = df[(df['upper_wick'] > abs(df['body']) * 2) & (abs(df['body']) > 0.1)].copy()
if len(upper_rejection) > 0:
    print(f"Upper wick rejection (wick > 2x body): {len(upper_rejection)}")
    print(f"  Next candle avg: {upper_rejection['fwd_1'].mean():.4f}%")
    print(f"  Bearish continuation (<-0.1%): {(upper_rejection['fwd_1'] < -0.1).sum() / len(upper_rejection) * 100:.2f}%")

    sequential_patterns.append({
        'pattern': 'upper_wick_rejection',
        'count': len(upper_rejection),
        'fwd_1_avg': upper_rejection['fwd_1'].mean(),
        'fwd_3_avg': upper_rejection['fwd_3'].mean(),
        'fwd_5_avg': upper_rejection['fwd_5'].mean(),
        'win_rate_fwd1': (upper_rejection['fwd_1'] < -0.1).sum() / len(upper_rejection) * 100,
        'edge': 'bearish_reversal'
    })

lower_rejection = df[(df['lower_wick'] > abs(df['body']) * 2) & (abs(df['body']) > 0.1)].copy()
if len(lower_rejection) > 0:
    print(f"\nLower wick rejection (wick > 2x body): {len(lower_rejection)}")
    print(f"  Next candle avg: {lower_rejection['fwd_1'].mean():.4f}%")
    print(f"  Bullish continuation (>0.1%): {(lower_rejection['fwd_1'] > 0.1).sum() / len(lower_rejection) * 100:.2f}%")

    sequential_patterns.append({
        'pattern': 'lower_wick_rejection',
        'count': len(lower_rejection),
        'fwd_1_avg': lower_rejection['fwd_1'].mean(),
        'fwd_3_avg': lower_rejection['fwd_3'].mean(),
        'fwd_5_avg': lower_rejection['fwd_5'].mean(),
        'win_rate_fwd1': (lower_rejection['fwd_1'] > 0.1).sum() / len(lower_rejection) * 100,
        'edge': 'bullish_reversal'
    })

# Pattern 4: SMA breakouts
print("\n\nPattern 4: SMA Breakouts")
for sma in [20, 50, 200]:
    # Bullish break (cross above)
    df[f'cross_above_{sma}'] = (df['close'] > df[f'sma{sma}']) & (df['close'].shift(1) <= df[f'sma{sma}'].shift(1))
    cross_above = df[df[f'cross_above_{sma}']].copy()

    if len(cross_above) > 0:
        print(f"\nCross above SMA{sma}: {len(cross_above)}")
        print(f"  Next 1 candle avg: {cross_above['fwd_1'].mean():.4f}%")
        print(f"  Next 5 candles avg: {cross_above['fwd_5'].mean():.4f}%")
        print(f"  Follow-through rate (>0.1%): {(cross_above['fwd_1'] > 0.1).sum() / len(cross_above) * 100:.2f}%")

        sequential_patterns.append({
            'pattern': f'cross_above_sma{sma}',
            'count': len(cross_above),
            'fwd_1_avg': cross_above['fwd_1'].mean(),
            'fwd_3_avg': cross_above['fwd_3'].mean(),
            'fwd_5_avg': cross_above['fwd_5'].mean(),
            'win_rate_fwd1': (cross_above['fwd_1'] > 0.1).sum() / len(cross_above) * 100,
            'edge': 'bullish_continuation' if cross_above['fwd_1'].mean() > 0.1 else 'fade'
        })

    # Bearish break (cross below)
    df[f'cross_below_{sma}'] = (df['close'] < df[f'sma{sma}']) & (df['close'].shift(1) >= df[f'sma{sma}'].shift(1))
    cross_below = df[df[f'cross_below_{sma}']].copy()

    if len(cross_below) > 0:
        print(f"\nCross below SMA{sma}: {len(cross_below)}")
        print(f"  Next 1 candle avg: {cross_below['fwd_1'].mean():.4f}%")
        print(f"  Next 5 candles avg: {cross_below['fwd_5'].mean():.4f}%")
        print(f"  Follow-through rate (<-0.1%): {(cross_below['fwd_1'] < -0.1).sum() / len(cross_below) * 100:.2f}%")

        sequential_patterns.append({
            'pattern': f'cross_below_sma{sma}',
            'count': len(cross_below),
            'fwd_1_avg': cross_below['fwd_1'].mean(),
            'fwd_3_avg': cross_below['fwd_3'].mean(),
            'fwd_5_avg': cross_below['fwd_5'].mean(),
            'win_rate_fwd1': (cross_below['fwd_1'] < -0.1).sum() / len(cross_below) * 100,
            'edge': 'bearish_continuation' if cross_below['fwd_1'].mean() < -0.1 else 'fade'
        })

# Pattern 5: Bollinger Band touches
print("\n\nPattern 5: Bollinger Band Touches")
bb_upper_touch = df[df['bb_position'] > 95].copy()
if len(bb_upper_touch) > 0:
    print(f"Upper BB touch (>95%): {len(bb_upper_touch)}")
    print(f"  Next candle avg: {bb_upper_touch['fwd_1'].mean():.4f}%")
    print(f"  Mean reversion rate (<-0.1%): {(bb_upper_touch['fwd_1'] < -0.1).sum() / len(bb_upper_touch) * 100:.2f}%")

    sequential_patterns.append({
        'pattern': 'bb_upper_touch',
        'count': len(bb_upper_touch),
        'fwd_1_avg': bb_upper_touch['fwd_1'].mean(),
        'fwd_3_avg': bb_upper_touch['fwd_3'].mean(),
        'fwd_5_avg': bb_upper_touch['fwd_5'].mean(),
        'win_rate_fwd1': (bb_upper_touch['fwd_1'] < -0.1).sum() / len(bb_upper_touch) * 100,
        'edge': 'mean_reversion'
    })

bb_lower_touch = df[df['bb_position'] < 5].copy()
if len(bb_lower_touch) > 0:
    print(f"\nLower BB touch (<5%): {len(bb_lower_touch)}")
    print(f"  Next candle avg: {bb_lower_touch['fwd_1'].mean():.4f}%")
    print(f"  Mean reversion rate (>0.1%): {(bb_lower_touch['fwd_1'] > 0.1).sum() / len(bb_lower_touch) * 100:.2f}%")

    sequential_patterns.append({
        'pattern': 'bb_lower_touch',
        'count': len(bb_lower_touch),
        'fwd_1_avg': bb_lower_touch['fwd_1'].mean(),
        'fwd_3_avg': bb_lower_touch['fwd_3'].mean(),
        'fwd_5_avg': bb_lower_touch['fwd_5'].mean(),
        'win_rate_fwd1': (bb_lower_touch['fwd_1'] > 0.1).sum() / len(bb_lower_touch) * 100,
        'edge': 'mean_reversion'
    })

# Pattern 6: Volume patterns
print("\n\nPattern 6: Volume Patterns")
vol_spike = df[df['vol_ratio'] > 3.0].copy()
if len(vol_spike) > 0:
    print(f"Volume spike (>3x avg): {len(vol_spike)}")
    print(f"  Next candle avg: {vol_spike['fwd_1'].mean():.4f}%")
    print(f"  Continuation if bullish body: {vol_spike[vol_spike['body'] > 0]['fwd_1'].mean():.4f}%")
    print(f"  Continuation if bearish body: {vol_spike[vol_spike['body'] < 0]['fwd_1'].mean():.4f}%")

    sequential_patterns.append({
        'pattern': 'volume_spike_>3x',
        'count': len(vol_spike),
        'fwd_1_avg': vol_spike['fwd_1'].mean(),
        'fwd_3_avg': vol_spike['fwd_3'].mean(),
        'fwd_5_avg': vol_spike['fwd_5'].mean(),
        'win_rate_fwd1': (abs(vol_spike['fwd_1']) > 0.1).sum() / len(vol_spike) * 100,
        'edge': 'volatility_continuation'
    })

vol_dryup = df[df['vol_ratio'] < 0.5].copy()
if len(vol_dryup) > 0:
    print(f"\nVolume dry-up (<0.5x avg): {len(vol_dryup)}")
    print(f"  Next candle avg: {vol_dryup['fwd_1'].mean():.4f}%")
    print(f"  Range next candle: {vol_dryup['fwd_1'].abs().mean():.4f}%")

    sequential_patterns.append({
        'pattern': 'volume_dryup_<0.5x',
        'count': len(vol_dryup),
        'fwd_1_avg': vol_dryup['fwd_1'].mean(),
        'fwd_3_avg': vol_dryup['fwd_3'].mean(),
        'fwd_5_avg': vol_dryup['fwd_5'].mean(),
        'win_rate_fwd1': (abs(vol_dryup['fwd_1']) < 0.1).sum() / len(vol_dryup) * 100,
        'edge': 'low_volatility'
    })

# Pattern 7: ATR expansion/contraction
print("\n\nPattern 7: ATR Patterns")
atr_expansion = df[df['atr_pct'] > df['atr_pct'].shift(1) * 1.5].copy()
if len(atr_expansion) > 0:
    print(f"ATR expansion (>1.5x previous): {len(atr_expansion)}")
    print(f"  Next candle avg: {atr_expansion['fwd_1'].mean():.4f}%")
    print(f"  Volatility continuation: {(abs(atr_expansion['fwd_1']) > 0.3).sum() / len(atr_expansion) * 100:.2f}%")

    sequential_patterns.append({
        'pattern': 'atr_expansion_>1.5x',
        'count': len(atr_expansion),
        'fwd_1_avg': atr_expansion['fwd_1'].mean(),
        'fwd_3_avg': atr_expansion['fwd_3'].mean(),
        'fwd_5_avg': atr_expansion['fwd_5'].mean(),
        'win_rate_fwd1': (abs(atr_expansion['fwd_1']) > 0.3).sum() / len(atr_expansion) * 100,
        'edge': 'volatility_expansion'
    })

# ============================================================================
# 3. REGIME CLASSIFICATION
# ============================================================================
print("\n" + "="*80)
print("REGIME CLASSIFICATION")
print("="*80)

# Define regimes based on price action
df['regime'] = 'unknown'

# Trending: consistent SMA alignment and distance
df.loc[(df['close'] > df['sma20']) & (df['sma20'] > df['sma50']) & (df['dist_sma20'] > 1.0), 'regime'] = 'uptrend'
df.loc[(df['close'] < df['sma20']) & (df['sma20'] < df['sma50']) & (df['dist_sma20'] < -1.0), 'regime'] = 'downtrend'

# Mean-reverting: price oscillating around SMA
df.loc[(abs(df['dist_sma20']) < 0.5) & (df['atr_pct'] < 1.0), 'regime'] = 'mean_reverting'

# Explosive: high ATR + large body candles
df.loc[(df['atr_pct'] > 2.0) & (abs(df['body']) > 1.0), 'regime'] = 'explosive'

# Choppy: low ATR, small bodies, no trend
df.loc[(df['atr_pct'] < 0.5) & (abs(df['body']) < 0.3), 'regime'] = 'choppy'

regime_counts = df['regime'].value_counts()
regime_pct = (regime_counts / len(df) * 100).round(2)

print("\nRegime Distribution:")
for regime, count in regime_counts.items():
    pct = regime_pct[regime]
    avg_duration = df[df['regime'] == regime].groupby((df['regime'] != df['regime'].shift()).cumsum()).size().mean()
    print(f"  {regime:15s}: {count:6d} candles ({pct:5.2f}%), avg duration: {avg_duration:.1f} candles")

# Best strategy per regime
print("\nBest Strategy per Regime:")
regime_analysis = []
for regime in df['regime'].unique():
    if regime == 'unknown':
        continue
    regime_df = df[df['regime'] == regime].copy()

    # Long signals (body > 0.3%)
    long_signals = regime_df[regime_df['body'] > 0.3]
    long_win_rate = (long_signals['fwd_1'] > 0.1).sum() / len(long_signals) * 100 if len(long_signals) > 0 else 0
    long_avg_return = long_signals['fwd_1'].mean() if len(long_signals) > 0 else 0

    # Short signals (body < -0.3%)
    short_signals = regime_df[regime_df['body'] < -0.3]
    short_win_rate = (short_signals['fwd_1'] < -0.1).sum() / len(short_signals) * 100 if len(short_signals) > 0 else 0
    short_avg_return = short_signals['fwd_1'].mean() if len(short_signals) > 0 else 0

    # Mean reversion (RSI extremes)
    mr_long = regime_df[regime_df['rsi'] < 30]
    mr_long_return = mr_long['fwd_3'].mean() if len(mr_long) > 0 else 0

    mr_short = regime_df[regime_df['rsi'] > 70]
    mr_short_return = mr_short['fwd_3'].mean() if len(mr_short) > 0 else 0

    best_strategy = 'long' if long_avg_return > short_avg_return else 'short'
    if abs(mr_long_return) > abs(long_avg_return) or abs(mr_short_return) > abs(short_avg_return):
        best_strategy = 'mean_reversion'

    print(f"\n  {regime}:")
    print(f"    Long momentum: {long_avg_return:.4f}% avg, {long_win_rate:.2f}% WR ({len(long_signals)} signals)")
    print(f"    Short momentum: {short_avg_return:.4f}% avg, {short_win_rate:.2f}% WR ({len(short_signals)} signals)")
    print(f"    MR long (RSI<30): {mr_long_return:.4f}% avg ({len(mr_long)} signals)")
    print(f"    MR short (RSI>70): {mr_short_return:.4f}% avg ({len(mr_short)} signals)")
    print(f"    → Best strategy: {best_strategy}")

    regime_analysis.append({
        'regime': regime,
        'candles': len(regime_df),
        'pct_time': regime_pct[regime],
        'long_signals': len(long_signals),
        'long_win_rate': long_win_rate,
        'long_avg_return': long_avg_return,
        'short_signals': len(short_signals),
        'short_win_rate': short_win_rate,
        'short_avg_return': short_avg_return,
        'best_strategy': best_strategy
    })

regime_df_export = pd.DataFrame(regime_analysis)
regime_df_export.to_csv('results/PENGU_regime_analysis.csv', index=False)

# ============================================================================
# 4. STATISTICAL EDGES
# ============================================================================
print("\n" + "="*80)
print("STATISTICAL EDGES")
print("="*80)

statistical_edges = []

# Day of week
print("\nDay of Week Analysis:")
dow_stats = df.groupby('day_of_week').agg({
    'body': 'mean',
    'range': 'mean',
    'fwd_1': 'mean',
    'fwd_5': 'mean'
}).round(4)
dow_stats['day_name'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
print(dow_stats.to_string())

best_day = dow_stats['fwd_1'].idxmax()
worst_day = dow_stats['fwd_1'].idxmin()
print(f"\nBest day for longs: {dow_stats.loc[best_day, 'day_name']} ({dow_stats.loc[best_day, 'fwd_1']:.4f}%)")
print(f"Worst day for longs: {dow_stats.loc[worst_day, 'day_name']} ({dow_stats.loc[worst_day, 'fwd_1']:.4f}%)")

statistical_edges.append({
    'edge_type': 'day_of_week',
    'best_day': dow_stats.loc[best_day, 'day_name'],
    'best_day_return': dow_stats.loc[best_day, 'fwd_1'],
    'worst_day': dow_stats.loc[worst_day, 'day_name'],
    'worst_day_return': dow_stats.loc[worst_day, 'fwd_1']
})

# RSI extremes
print("\nRSI Extreme Analysis:")
rsi_oversold = df[df['rsi'] < 30].copy()
rsi_overbought = df[df['rsi'] > 70].copy()

if len(rsi_oversold) > 0:
    print(f"RSI < 30 (oversold): {len(rsi_oversold)}")
    print(f"  Next 1 candle: {rsi_oversold['fwd_1'].mean():.4f}%")
    print(f"  Next 3 candles: {rsi_oversold['fwd_3'].mean():.4f}%")
    print(f"  Reversal rate (>0.1%): {(rsi_oversold['fwd_1'] > 0.1).sum() / len(rsi_oversold) * 100:.2f}%")

    statistical_edges.append({
        'edge_type': 'rsi_oversold_<30',
        'count': len(rsi_oversold),
        'fwd_1_avg': rsi_oversold['fwd_1'].mean(),
        'fwd_3_avg': rsi_oversold['fwd_3'].mean(),
        'reversal_rate': (rsi_oversold['fwd_1'] > 0.1).sum() / len(rsi_oversold) * 100
    })

if len(rsi_overbought) > 0:
    print(f"\nRSI > 70 (overbought): {len(rsi_overbought)}")
    print(f"  Next 1 candle: {rsi_overbought['fwd_1'].mean():.4f}%")
    print(f"  Next 3 candles: {rsi_overbought['fwd_3'].mean():.4f}%")
    print(f"  Reversal rate (<-0.1%): {(rsi_overbought['fwd_1'] < -0.1).sum() / len(rsi_overbought) * 100:.2f}%")

    statistical_edges.append({
        'edge_type': 'rsi_overbought_>70',
        'count': len(rsi_overbought),
        'fwd_1_avg': rsi_overbought['fwd_1'].mean(),
        'fwd_3_avg': rsi_overbought['fwd_3'].mean(),
        'reversal_rate': (rsi_overbought['fwd_1'] < -0.1).sum() / len(rsi_overbought) * 100
    })

# Export pattern stats
patterns_df = pd.DataFrame(sequential_patterns)
if len(patterns_df) > 0:
    patterns_df = patterns_df.sort_values('fwd_1_avg', key=abs, ascending=False)
    patterns_df.to_csv('results/PENGU_sequential_patterns.csv', index=False)

# ============================================================================
# 5. COIN PERSONALITY PROFILE
# ============================================================================
print("\n" + "="*80)
print("PENGU PERSONALITY PROFILE")
print("="*80)

daily_ranges = df.groupby(df['timestamp'].dt.date)['range'].sum()
typical_daily_range = daily_ranges.mean()
max_daily_range = daily_ranges.max()
min_daily_range = daily_ranges.min()

print(f"\nVolatility Character:")
print(f"  Typical daily range: {typical_daily_range:.2f}%")
print(f"  Max daily range: {max_daily_range:.2f}%")
print(f"  Min daily range: {min_daily_range:.2f}%")
print(f"  Avg 1-min body: {df['body'].abs().mean():.4f}%")
print(f"  Avg 1-min range: {df['range'].mean():.4f}%")
print(f"  ATR (14): {df['atr_pct'].mean():.4f}%")

print(f"\nMomentum Character:")
# Measure follow-through on strong candles
strong_bull = df[df['body'] > 0.5].copy()
strong_bear = df[df['body'] < -0.5].copy()

bull_continuation = (strong_bull['fwd_1'] > 0.1).sum() / len(strong_bull) * 100 if len(strong_bull) > 0 else 0
bear_continuation = (strong_bear['fwd_1'] < -0.1).sum() / len(strong_bear) * 100 if len(strong_bear) > 0 else 0

print(f"  Bullish momentum follow-through: {bull_continuation:.2f}%")
print(f"  Bearish momentum follow-through: {bear_continuation:.2f}%")

if bull_continuation > 55 and bear_continuation > 55:
    momentum_type = "STRONG MOMENTUM (both directions follow through)"
elif bull_continuation > 55:
    momentum_type = "BULLISH MOMENTUM (longs follow through, shorts fade)"
elif bear_continuation > 55:
    momentum_type = "BEARISH MOMENTUM (shorts follow through, longs fade)"
else:
    momentum_type = "MEAN REVERTING (moves tend to fade)"

print(f"  → {momentum_type}")

print(f"\nRisk Character:")
# Calculate maximum drawdown periods
equity = (1 + df['body'] / 100).cumprod()
running_max = equity.expanding().max()
drawdown = (equity - running_max) / running_max * 100
max_drawdown = drawdown.min()

print(f"  Max drawdown (buy & hold): {max_drawdown:.2f}%")
print(f"  Avg drawdown: {drawdown.mean():.2f}%")
print(f"  Black swan events (>5% move): {(abs(df['body']) > 5.0).sum()}")
print(f"  High volatility events (>2% move): {(abs(df['body']) > 2.0).sum()}")

# ============================================================================
# FINAL SUMMARY & RECOMMENDATION
# ============================================================================
print("\n" + "="*80)
print("EXECUTIVE SUMMARY - TOP 5 PATTERNS")
print("="*80)

if len(patterns_df) > 0:
    print("\nTop 5 patterns by absolute forward return:")
    patterns_df['abs_fwd_1'] = patterns_df['fwd_1_avg'].abs()
    top_patterns = patterns_df.nlargest(5, 'abs_fwd_1')
    for idx, row in top_patterns.iterrows():
        print(f"\n{row['pattern']}:")
        print(f"  Count: {row['count']}")
        print(f"  Fwd 1 avg: {row['fwd_1_avg']:.4f}%")
        print(f"  Fwd 3 avg: {row['fwd_3_avg']:.4f}%")
        print(f"  Win rate: {row['win_rate_fwd1']:.2f}%")
        print(f"  Edge: {row['edge']}")

print("\n" + "="*80)
print("FINAL RECOMMENDATION")
print("="*80)

# Determine if PENGU is better for trend-following or mean-reversion
uptrend_pct = regime_pct.get('uptrend', 0)
downtrend_pct = regime_pct.get('downtrend', 0)
mean_rev_pct = regime_pct.get('mean_reverting', 0)
explosive_pct = regime_pct.get('explosive', 0)

trend_pct = uptrend_pct + downtrend_pct
volatility_pct = explosive_pct

if trend_pct > mean_rev_pct:
    recommendation = "TREND-FOLLOWING"
    reason = f"PENGU spends {trend_pct:.1f}% of time trending vs {mean_rev_pct:.1f}% mean-reverting"
else:
    recommendation = "MEAN-REVERSION"
    reason = f"PENGU spends {mean_rev_pct:.1f}% of time mean-reverting vs {trend_pct:.1f}% trending"

if volatility_pct > 10:
    recommendation += " + BREAKOUT"
    reason += f", with {volatility_pct:.1f}% explosive volatility events"

print(f"\n{recommendation}")
print(f"Reason: {reason}")
print(f"\nMomentum type: {momentum_type}")

print("\n✅ Analysis complete!")
print("Results saved to:")
print("  - results/PENGU_PATTERN_ANALYSIS.md")
print("  - results/PENGU_session_stats.csv")
print("  - results/PENGU_sequential_patterns.csv")
print("  - results/PENGU_regime_analysis.csv")

# ============================================================================
# GENERATE MARKDOWN REPORT
# ============================================================================

report = f"""# PENGU Pattern Discovery Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Data Summary
- **Total Candles**: {len(df):,}
- **Date Range**: {df['timestamp'].min()} to {df['timestamp'].max()}
- **Price Range**: ${df['close'].min():.6f} - ${df['close'].max():.6f}
- **Total Price Change**: {((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100):.2f}%

## 1. Session Analysis

| Session | Candles | Avg Body % | Avg Range % | Long Win Rate | Short Win Rate | Best For |
|---------|---------|------------|-------------|---------------|----------------|----------|
"""

for _, row in session_df.iterrows():
    best_for = 'LONG' if row['long_win_rate'] > row['short_win_rate'] else 'SHORT'
    report += f"| {row['session']} | {row['candles']:,} | {row['avg_body']:.4f} | {row['avg_range']:.4f} | {row['long_win_rate']:.2f}% | {row['short_win_rate']:.2f}% | {best_for} |\n"

report += f"""
## 2. Top Sequential Patterns

"""

if len(patterns_df) > 0:
    if 'abs_fwd_1' not in patterns_df.columns:
        patterns_df['abs_fwd_1'] = patterns_df['fwd_1_avg'].abs()
    top_5 = patterns_df.nlargest(5, 'abs_fwd_1')
    for idx, (_, row) in enumerate(top_5.iterrows(), 1):
        report += f"""
### Pattern {idx}: {row['pattern']}
- **Count**: {row['count']}
- **Forward 1 avg**: {row['fwd_1_avg']:.4f}%
- **Forward 3 avg**: {row['fwd_3_avg']:.4f}%
- **Forward 5 avg**: {row['fwd_5_avg']:.4f}%
- **Win Rate**: {row['win_rate_fwd1']:.2f}%
- **Edge**: {row['edge']}
"""

report += f"""
## 3. Regime Distribution

| Regime | Candles | % Time | Best Strategy |
|--------|---------|--------|---------------|
"""

for _, row in regime_df_export.iterrows():
    report += f"| {row['regime']} | {row['candles']:,} | {row['pct_time']:.2f}% | {row['best_strategy']} |\n"

report += f"""
## 4. PENGU Personality Profile

### Volatility Character
- **Typical daily range**: {typical_daily_range:.2f}%
- **Avg 1-min body**: {df['body'].abs().mean():.4f}%
- **Avg 1-min range**: {df['range'].mean():.4f}%
- **ATR (14)**: {df['atr_pct'].mean():.4f}%

### Momentum Character
- **Bullish follow-through**: {bull_continuation:.2f}%
- **Bearish follow-through**: {bear_continuation:.2f}%
- **Type**: {momentum_type}

### Risk Character
- **Max drawdown**: {max_drawdown:.2f}%
- **Black swan events (>5%)**: {(abs(df['body']) > 5.0).sum()}
- **High volatility events (>2%)**: {(abs(df['body']) > 2.0).sum()}

## 5. Final Recommendation

### **{recommendation}**

**Reason**: {reason}

**Momentum Type**: {momentum_type}

### Trading Implications
"""

if 'TREND-FOLLOWING' in recommendation:
    report += """
- Focus on breakout strategies
- Look for strong directional moves with volume confirmation
- Use wide stops to avoid getting chopped out
- Best sessions: Check session stats above for highest momentum sessions
"""
else:
    report += """
- Focus on mean-reversion strategies
- Look for oversold/overbought extremes (RSI, BB)
- Use tight stops and quick profit targets
- Best sessions: Check session stats above for lowest volatility sessions
"""

report += f"""
## Key Actionable Insights

1. **Best Trading Hours**: {hourly_stats.head(1).index[0]}:00 UTC (avg fwd return: {hourly_stats.head(1)['fwd_1'].values[0]:.4f}%)
2. **Worst Trading Hours**: {hourly_stats.tail(1).index[0]}:00 UTC (avg fwd return: {hourly_stats.tail(1)['fwd_1'].values[0]:.4f}%)
3. **Most Frequent Regime**: {regime_counts.index[0]} ({regime_pct[regime_counts.index[0]]:.2f}% of time)
4. **Strongest Pattern**: {patterns_df.iloc[0]['pattern'] if len(patterns_df) > 0 else 'N/A'}
5. **Momentum Style**: {momentum_type}

---
*All statistics calculated on {len(df):,} 1-minute candles spanning 30 days*
"""

with open('results/PENGU_PATTERN_ANALYSIS.md', 'w') as f:
    f.write(report)

print("\n📊 Markdown report generated successfully!")
