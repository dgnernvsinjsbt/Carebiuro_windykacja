"""
Analyze market conditions in good vs bad months
to find filters for when NOT to trade

Good months: Mar, Apr, Jun (77-80% win rate)
Bad months: Jan, Feb, May (25-58% win rate)
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

print("=" * 80)
print("Market Regime Analysis: Good vs Bad Months")
print("=" * 80)

# Download full 2025 data
exchange = ccxt.bingx({'enableRateLimit': True})

start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
end_date = datetime(2025, 12, 15, tzinfo=timezone.utc)

start_ts = int(start_date.timestamp() * 1000)
end_ts = int(end_date.timestamp() * 1000)

print("\nDownloading MELANIA full 2025 data...")

all_candles = []
current_ts = start_ts

while current_ts < end_ts:
    candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='1h', since=current_ts, limit=1000)
    if not candles:
        break
    all_candles.extend(candles)
    current_ts = candles[-1][0] + 3600000
    time.sleep(0.5)

df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
df = df[(df['timestamp'] >= start_date.replace(tzinfo=None)) & (df['timestamp'] <= end_date.replace(tzinfo=None))]
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Downloaded {len(df)} bars")

# Calculate indicators
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
    abs(df['high'] - df['close'].shift(1)),
    abs(df['low'] - df['close'].shift(1))
))
df['atr'] = df['tr'].rolling(14).mean()
df['atr_pct'] = (df['atr'] / df['close']) * 100  # ATR as % of price

# Moving averages for trend
df['sma20'] = df['close'].rolling(20).mean()
df['sma50'] = df['close'].rolling(50).mean()
df['price_vs_sma20'] = ((df['close'] - df['sma20']) / df['sma20']) * 100
df['price_vs_sma50'] = ((df['close'] - df['sma50']) / df['sma50']) * 100

# Volatility
df['returns'] = df['close'].pct_change() * 100
df['volatility'] = df['returns'].rolling(20).std()

# Volume
df['volume_sma'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_sma']

# RSI extreme frequency
df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
df['rsi_overbought'] = (df['rsi'] > 70).astype(int)

# Add month column
df['month'] = df['timestamp'].dt.to_period('M').astype(str)

# Define good vs bad months
good_months = ['2025-03', '2025-04', '2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12']
bad_months = ['2025-01', '2025-02', '2025-05']

# Analyze each month
print("\n" + "=" * 80)
print("MONTHLY MARKET CHARACTERISTICS:")
print("=" * 80)

print("\n| Month | Type | Avg ATR% | Volatility | Vol Ratio | RSI<30 | RSI>70 | Price vs SMA20 | Trend |")
print("|-------|------|----------|------------|-----------|--------|--------|----------------|-------|")

monthly_stats = []

for month in sorted(df['month'].unique()):
    month_data = df[df['month'] == month]

    if len(month_data) < 50:
        continue

    month_type = '✅ GOOD' if month in good_months else '❌ BAD'

    stats = {
        'month': month,
        'type': month_type,
        'avg_atr_pct': month_data['atr_pct'].mean(),
        'avg_volatility': month_data['volatility'].mean(),
        'avg_volume_ratio': month_data['volume_ratio'].mean(),
        'rsi_oversold_pct': (month_data['rsi_oversold'].sum() / len(month_data)) * 100,
        'rsi_overbought_pct': (month_data['rsi_overbought'].sum() / len(month_data)) * 100,
        'avg_price_vs_sma20': month_data['price_vs_sma20'].mean(),
        'avg_price_vs_sma50': month_data['price_vs_sma50'].mean(),
        'price_range': ((month_data['close'].max() - month_data['close'].min()) / month_data['close'].min()) * 100
    }

    # Determine trend
    if stats['avg_price_vs_sma50'] > 5:
        trend = 'UP'
    elif stats['avg_price_vs_sma50'] < -5:
        trend = 'DOWN'
    else:
        trend = 'FLAT'

    print(f"| {month} | {month_type} | {stats['avg_atr_pct']:.2f}% | {stats['avg_volatility']:.3f} | "
          f"{stats['avg_volume_ratio']:.2f}x | {stats['rsi_oversold_pct']:.1f}% | "
          f"{stats['rsi_overbought_pct']:.1f}% | {stats['avg_price_vs_sma20']:+.1f}% | {trend} |")

    monthly_stats.append(stats)

# Compare good vs bad months
print("\n" + "=" * 80)
print("GOOD MONTHS vs BAD MONTHS COMPARISON:")
print("=" * 80)

df_stats = pd.DataFrame(monthly_stats)

good_stats = df_stats[df_stats['month'].isin(good_months)]
bad_stats = df_stats[df_stats['month'].isin(bad_months)]

if len(good_stats) > 0 and len(bad_stats) > 0:
    print("\nAverage characteristics:")
    print("\n                        GOOD MONTHS  |  BAD MONTHS  | Difference")
    print("                        -------------|--------------|------------")

    metrics = [
        ('ATR % (volatility)', 'avg_atr_pct'),
        ('Volatility (std)', 'avg_volatility'),
        ('Volume Ratio', 'avg_volume_ratio'),
        ('RSI < 30 %', 'rsi_oversold_pct'),
        ('RSI > 70 %', 'rsi_overbought_pct'),
        ('Price vs SMA20 %', 'avg_price_vs_sma20'),
        ('Price vs SMA50 %', 'avg_price_vs_sma50'),
        ('Price Range %', 'price_range')
    ]

    for label, metric in metrics:
        good_avg = good_stats[metric].mean()
        bad_avg = bad_stats[metric].mean()
        diff = good_avg - bad_avg
        diff_pct = (diff / bad_avg * 100) if bad_avg != 0 else 0

        print(f"{label:25s} {good_avg:8.2f}     | {bad_avg:8.2f}     | {diff:+7.2f} ({diff_pct:+.0f}%)")

    # Find the most differentiating factors
    print("\n" + "=" * 80)
    print("KEY DIFFERENTIATORS (sorted by difference %):")
    print("=" * 80)

    diffs = []
    for label, metric in metrics:
        good_avg = good_stats[metric].mean()
        bad_avg = bad_stats[metric].mean()
        diff_pct = abs((good_avg - bad_avg) / bad_avg * 100) if bad_avg != 0 else 0
        diffs.append((label, metric, good_avg, bad_avg, diff_pct))

    diffs.sort(key=lambda x: x[4], reverse=True)

    for label, metric, good_avg, bad_avg, diff_pct in diffs[:5]:
        direction = "HIGHER" if good_avg > bad_avg else "LOWER"
        print(f"\n{label}:")
        print(f"  Good months: {good_avg:.2f}")
        print(f"  Bad months: {bad_avg:.2f}")
        print(f"  → Good months have {direction} {label.lower()} ({diff_pct:.0f}% difference)")

    # Suggest filters
    print("\n" + "=" * 80)
    print("SUGGESTED TRADING FILTERS:")
    print("=" * 80)

    print("\nBased on the analysis, consider trading ONLY when:")

    # Find thresholds that separate good from bad
    for label, metric in metrics[:5]:  # Top 5 differentiators
        good_avg = good_stats[metric].mean()
        bad_avg = bad_stats[metric].mean()

        if good_avg > bad_avg:
            threshold = (good_avg + bad_avg) / 2
            print(f"  ✅ {label} > {threshold:.2f}")
        else:
            threshold = (good_avg + bad_avg) / 2
            print(f"  ✅ {label} < {threshold:.2f}")

print("\n" + "=" * 80)
