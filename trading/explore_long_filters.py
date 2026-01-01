#!/usr/bin/env python3
"""
FARTCOIN LONG-only - Filter Exploration
Test MANY filter ideas to improve LONG-only performance

Categories:
1. Session/Time filters (certain hours)
2. Daily trend filters (daily SMA, daily EMA)
3. Volatility regime filters (high/low vol periods)
4. Volume regime filters (high/low volume periods)
5. Price position filters (vs daily EMAs)
6. Momentum filters (daily RSI)
7. Recent performance filters (stop after losses)
"""

import pandas as pd
import numpy as np

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

print("=" * 80)
print("FARTCOIN LONG-ONLY - COMPREHENSIVE FILTER EXPLORATION")
print("=" * 80)

# Load 60-day data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"\nData: {len(df):,} candles (60 days)")

# Calculate 1m indicators
df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
df['atr_ma'] = df['atr'].rolling(20).mean()
df['atr_ratio'] = df['atr'] / df['atr_ma']
df['ema20'] = calculate_ema(df['close'], 20)
df['distance'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)
df['bullish'] = df['close'] > df['open']

# Add time features
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday

# Calculate daily indicators (resample to daily)
df_daily = df.set_index('timestamp').resample('1D').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

df_daily['sma_20'] = df_daily['close'].rolling(20).mean()
df_daily['sma_50'] = df_daily['close'].rolling(50).mean()
df_daily['ema_10'] = calculate_ema(df_daily['close'], 10)
df_daily['ema_20'] = calculate_ema(df_daily['close'], 20)
df_daily['atr_daily'] = calculate_atr(df_daily['high'], df_daily['low'], df_daily['close'], 14)
df_daily['atr_pct'] = (df_daily['atr_daily'] / df_daily['close']) * 100
df_daily['rsi_daily'] = calculate_rsi(df_daily['close'], 14)
df_daily['vol_ma'] = df_daily['volume'].rolling(20).mean()
df_daily['vol_ratio'] = df_daily['volume'] / df_daily['vol_ma']

# Merge daily data back to 1m (forward fill)
df = df.set_index('timestamp')
df = df.join(df_daily[['sma_20', 'sma_50', 'ema_10', 'ema_20', 'atr_daily', 'atr_pct', 'rsi_daily', 'vol_ma', 'vol_ratio']], how='left')
df = df.fillna(method='ffill')
df = df.reset_index()

# Rename to avoid confusion
df.rename(columns={
    'sma_20': 'daily_sma20',
    'sma_50': 'daily_sma50',
    'ema_10': 'daily_ema10',
    'ema_20': 'daily_ema20',
    'atr_pct': 'daily_atr_pct',
    'rsi_daily': 'daily_rsi',
    'vol_ratio': 'daily_vol_ratio'
}, inplace=True)

print("✅ Indicators calculated")

def generate_long_signals(df):
    """Generate LONG signals only"""
    signals = []
    for i in range(len(df)):
        row = df.iloc[i]
        if (row['atr_ratio'] > 1.5 and
            row['distance'] < 3.0 and
            row['bullish']):
            signals.append(i)
    return signals

def backtest_with_filter(df, signals, filter_func, filter_name):
    """
    Backtest with custom filter function
    filter_func(df, idx) returns True if signal should be taken
    """
    trades = []

    for signal_idx in signals:
        if signal_idx >= len(df) - 1:
            continue

        # Apply filter
        if not filter_func(df, signal_idx):
            continue

        signal_price = df['close'].iloc[signal_idx]
        signal_atr = df['atr'].iloc[signal_idx]

        if pd.isna(signal_atr) or signal_atr == 0:
            continue

        # Limit order
        limit_price = signal_price * 1.01

        # Try to fill
        filled = False
        fill_idx = None

        for i in range(signal_idx + 1, min(signal_idx + 4, len(df))):
            if df['high'].iloc[i] >= limit_price:
                filled = True
                fill_idx = i
                break

        if not filled:
            continue

        # Trade filled
        entry_price = limit_price
        entry_atr = df['atr'].iloc[fill_idx]

        sl_price = entry_price - (2.0 * entry_atr)
        tp_price = entry_price + (8.0 * entry_atr)

        # Find exit
        exit_idx = None
        exit_price = None
        exit_reason = None

        for i in range(fill_idx + 1, min(fill_idx + 200, len(df))):
            if df['low'].iloc[i] <= sl_price:
                exit_idx = i
                exit_price = sl_price
                exit_reason = 'SL'
                break
            if df['high'].iloc[i] >= tp_price:
                exit_idx = i
                exit_price = tp_price
                exit_reason = 'TP'
                break

        if exit_idx is None:
            exit_idx = min(fill_idx + 199, len(df) - 1)
            exit_price = df['close'].iloc[exit_idx]
            exit_reason = 'TIME'

        pnl_pct = (exit_price - entry_price) / entry_price * 100 - 0.10

        trades.append({
            'pnl_pct': pnl_pct,
            'exit_reason': exit_reason
        })

    return trades

def calc_metrics(trades):
    """Calculate metrics"""
    if not trades:
        return {'trades': 0, 'return': 0, 'dd': 0, 'rdd': 0, 'wr': 0, 'tp_rate': 0}

    df_t = pd.DataFrame(trades)
    df_t['cum'] = df_t['pnl_pct'].cumsum()
    equity = 100 + df_t['cum']
    dd = ((equity - equity.cummax()) / equity.cummax() * 100).min()
    total_return = df_t['pnl_pct'].sum()
    rdd = total_return / abs(dd) if dd != 0 else 0
    wr = (df_t['pnl_pct'] > 0).mean() * 100
    tp_rate = (df_t['exit_reason'] == 'TP').sum() / len(df_t) * 100

    return {
        'trades': len(trades),
        'return': total_return,
        'dd': dd,
        'rdd': rdd,
        'wr': wr,
        'tp_rate': tp_rate
    }

# Generate baseline signals
print("\nGenerating LONG signals...")
signals = generate_long_signals(df)
print(f"  {len(signals)} LONG signals")

# Define filters to test
filters = []

# 1. NO FILTER (baseline)
filters.append(('Baseline (No Filter)', lambda df, idx: True))

# 2. SESSION FILTERS
for start, end, name in [
    (0, 6, 'Session: 00-06 UTC'),
    (6, 12, 'Session: 06-12 UTC'),
    (12, 18, 'Session: 12-18 UTC'),
    (18, 24, 'Session: 18-24 UTC'),
    (8, 16, 'Session: 08-16 UTC (Asian/EU)'),
    (14, 22, 'Session: 14-22 UTC (EU/US)'),
]:
    filters.append((name, lambda df, idx, s=start, e=end: s <= df['hour'].iloc[idx] < e))

# 3. DAILY TREND FILTERS
filters.append(('Daily: Above SMA20', lambda df, idx: df['close'].iloc[idx] > df['daily_sma20'].iloc[idx]))
filters.append(('Daily: Above SMA50', lambda df, idx: df['close'].iloc[idx] > df['daily_sma50'].iloc[idx]))
filters.append(('Daily: SMA20 > SMA50', lambda df, idx: df['daily_sma20'].iloc[idx] > df['daily_sma50'].iloc[idx]))
filters.append(('Daily: Below SMA20', lambda df, idx: df['close'].iloc[idx] < df['daily_sma20'].iloc[idx]))

# 4. VOLATILITY REGIME FILTERS
filters.append(('Daily ATR > 3%', lambda df, idx: df['daily_atr_pct'].iloc[idx] > 3.0))
filters.append(('Daily ATR > 5%', lambda df, idx: df['daily_atr_pct'].iloc[idx] > 5.0))
filters.append(('Daily ATR < 3%', lambda df, idx: df['daily_atr_pct'].iloc[idx] < 3.0))

# 5. MOMENTUM FILTERS
filters.append(('Daily RSI > 50', lambda df, idx: df['daily_rsi'].iloc[idx] > 50))
filters.append(('Daily RSI > 60', lambda df, idx: df['daily_rsi'].iloc[idx] > 60))
filters.append(('Daily RSI < 50', lambda df, idx: df['daily_rsi'].iloc[idx] < 50))
filters.append(('Daily RSI 40-60', lambda df, idx: 40 <= df['daily_rsi'].iloc[idx] <= 60))

# 6. VOLUME REGIME FILTERS
filters.append(('Daily Vol > Avg', lambda df, idx: df['daily_vol_ratio'].iloc[idx] > 1.0))
filters.append(('Daily Vol > 1.5x Avg', lambda df, idx: df['daily_vol_ratio'].iloc[idx] > 1.5))

# 7. DAY OF WEEK FILTERS
filters.append(('Mon-Wed Only', lambda df, idx: df['day_of_week'].iloc[idx] < 3))
filters.append(('Thu-Fri Only', lambda df, idx: df['day_of_week'].iloc[idx] >= 3 and df['day_of_week'].iloc[idx] < 5))
filters.append(('Weekday Only', lambda df, idx: df['day_of_week'].iloc[idx] < 5))

# 8. COMBO FILTERS (most promising combinations)
filters.append(('Combo: Session 08-16 + Above Daily SMA20',
               lambda df, idx: (8 <= df['hour'].iloc[idx] < 16) and (df['close'].iloc[idx] > df['daily_sma20'].iloc[idx])))

filters.append(('Combo: Daily Uptrend + High Vol',
               lambda df, idx: (df['daily_sma20'].iloc[idx] > df['daily_sma50'].iloc[idx]) and (df['daily_vol_ratio'].iloc[idx] > 1.0)))

filters.append(('Combo: RSI > 50 + Above SMA20',
               lambda df, idx: (df['daily_rsi'].iloc[idx] > 50) and (df['close'].iloc[idx] > df['daily_sma20'].iloc[idx])))

print(f"\nTesting {len(filters)} filters...")
print("=" * 80)

results = []

for filter_name, filter_func in filters:
    try:
        trades = backtest_with_filter(df, signals, filter_func, filter_name)
        metrics = calc_metrics(trades)
        metrics['filter'] = filter_name
        results.append(metrics)

        if metrics['trades'] > 0:
            print(f"{filter_name:<45} T:{metrics['trades']:<4} R:{metrics['return']:+7.1f}% DD:{metrics['dd']:6.2f}% RDD:{metrics['rdd']:5.2f}x")
    except Exception as e:
        print(f"{filter_name:<45} ERROR: {e}")

# Sort by R/DD
df_results = pd.DataFrame(results)
df_results = df_results[df_results['trades'] > 0].sort_values('rdd', ascending=False)

print("\n" + "=" * 80)
print("TOP 10 FILTERS (by Return/DD)")
print("=" * 80)

baseline = df_results[df_results['filter'] == 'Baseline (No Filter)'].iloc[0]

print(f"\n{'Filter':<45} {'Trades':<8} {'Return':<10} {'DD':<10} {'R/DD':<8} {'vs Base'}")
print("-" * 100)

for _, row in df_results.head(10).iterrows():
    improvement = (row['rdd'] / baseline['rdd'] - 1) * 100 if baseline['rdd'] != 0 else 0
    print(f"{row['filter']:<45} {row['trades']:<8.0f} {row['return']:+9.1f}% {row['dd']:9.2f}% {row['rdd']:7.2f}x {improvement:+6.1f}%")

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

best = df_results.iloc[0]

print(f"""
BASELINE (No Filter):
  {baseline['trades']:.0f} trades, {baseline['return']:+.1f}% return, {baseline['rdd']:.2f}x R/DD

BEST FILTER:
  {best['filter']}
  {best['trades']:.0f} trades, {best['return']:+.1f}% return, {best['rdd']:.2f}x R/DD
  Improvement: {(best['rdd'] / baseline['rdd'] - 1) * 100:+.0f}%
""")

if best['rdd'] > baseline['rdd'] * 1.2:
    print("✅ STRONG IMPROVEMENT - This filter is worth implementing!")
elif best['rdd'] > baseline['rdd'] * 1.1:
    print("⚠️ MODERATE IMPROVEMENT - Could be worth testing live")
else:
    print("❌ NO SIGNIFICANT IMPROVEMENT - Filters don't help much")

# Category analysis
print("\n" + "=" * 80)
print("FILTER CATEGORY ANALYSIS")
print("=" * 80)

categories = {
    'Session': [f for f in df_results['filter'] if 'Session' in f],
    'Daily Trend': [f for f in df_results['filter'] if 'Daily:' in f and 'SMA' in f],
    'Volatility': [f for f in df_results['filter'] if 'ATR' in f],
    'Momentum': [f for f in df_results['filter'] if 'RSI' in f],
    'Volume': [f for f in df_results['filter'] if 'Vol' in f and 'Combo' not in f],
    'Combo': [f for f in df_results['filter'] if 'Combo' in f],
}

for category, filter_list in categories.items():
    if filter_list:
        cat_results = df_results[df_results['filter'].isin(filter_list)]
        if not cat_results.empty:
            best_in_cat = cat_results.iloc[0]
            avg_rdd = cat_results['rdd'].mean()
            print(f"\n{category}:")
            print(f"  Best: {best_in_cat['filter']} ({best_in_cat['rdd']:.2f}x R/DD, {(best_in_cat['rdd']/baseline['rdd']-1)*100:+.0f}%)")
            print(f"  Avg R/DD: {avg_rdd:.2f}x ({(avg_rdd/baseline['rdd']-1)*100:+.0f}% vs baseline)")

print("\n" + "=" * 80)

# Save results
df_results.to_csv('/workspaces/Carebiuro_windykacja/trading/results/fartcoin_long_filter_exploration.csv', index=False)
print("\n✅ Results saved to: trading/results/fartcoin_long_filter_exploration.csv")
