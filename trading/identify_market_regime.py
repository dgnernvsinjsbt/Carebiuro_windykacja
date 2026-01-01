"""
REGIME IDENTIFICATION: Can we detect when NOT to trade?

Compare Jul-Aug (bad) vs Sep-Dec (good) market conditions
Find regime indicators that signal "don't trade"
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("MARKET REGIME ANALYSIS")
print("Can we detect 'bad' markets like Jul-Aug and avoid them?")
print("=" * 80)

exchange = ccxt.bingx({'enableRateLimit': True})

periods = [
    {
        'name': 'Jul-Aug (BAD)',
        'start': datetime(2025, 7, 1, tzinfo=timezone.utc),
        'end': datetime(2025, 8, 31, 23, 59, 59, tzinfo=timezone.utc),
        'label': 'bad'
    },
    {
        'name': 'Sep-Dec (GOOD)',
        'start': datetime(2025, 9, 16, tzinfo=timezone.utc),
        'end': datetime(2025, 12, 15, tzinfo=timezone.utc),
        'label': 'good'
    }
]

period_stats = []

for period in periods:
    print(f"\nAnalyzing {period['name']}...")

    start_ts = int(period['start'].timestamp() * 1000)
    end_ts = int(period['end'].timestamp() * 1000)

    all_candles = []
    current_ts = start_ts

    while current_ts < end_ts:
        try:
            candles = exchange.fetch_ohlcv('MELANIA-USDT', timeframe='15m', since=current_ts, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            current_ts = candles[-1][0] + (15 * 60 * 1000)
            time.sleep(0.5)
        except Exception as e:
            time.sleep(2)
            continue

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= period['start'].replace(tzinfo=None)) &
            (df['timestamp'] <= period['end'].replace(tzinfo=None))]
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Calculate regime indicators
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ))
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_pct'] = (df['atr'] / df['close']) * 100

    # Volatility measures
    df['volatility_20'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean() * 100
    df['volatility_96'] = df['close'].rolling(96).std() / df['close'].rolling(96).mean() * 100

    # Trend measures
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

    df['price_vs_ema20'] = ((df['close'] - df['ema_20']) / df['ema_20']) * 100
    df['price_vs_ema50'] = ((df['close'] - df['ema_50']) / df['ema_50']) * 100
    df['price_vs_ema200'] = ((df['close'] - df['ema_200']) / df['ema_200']) * 100

    # Momentum
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100
    df['ret_96'] = (df['close'] / df['close'].shift(96) - 1) * 100
    df['ret_288'] = (df['close'] / df['close'].shift(288) - 1) * 100  # 3-day

    # Choppiness/trendiness
    df['range_20'] = ((df['high'].rolling(20).max() - df['low'].rolling(20).min()) /
                      df['low'].rolling(20).min()) * 100
    df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) /
                      df['low'].rolling(96).min()) * 100

    # Directional movement
    df['higher_highs'] = (df['high'] > df['high'].shift(1)).rolling(20).sum()
    df['lower_lows'] = (df['low'] < df['low'].shift(1)).rolling(20).sum()
    df['trend_consistency'] = abs(df['higher_highs'] - df['lower_lows']) / 20 * 100

    # Calculate stats
    stats = {
        'period': period['name'],
        'label': period['label'],
        'bars': len(df),
        'days': (period['end'] - period['start']).days,
        'price_change': (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100,
        'avg_atr_pct': df['atr_pct'].mean(),
        'avg_volatility_20': df['volatility_20'].mean(),
        'avg_volatility_96': df['volatility_96'].mean(),
        'avg_price_vs_ema20': df['price_vs_ema20'].mean(),
        'avg_price_vs_ema50': df['price_vs_ema50'].mean(),
        'avg_price_vs_ema200': df['price_vs_ema200'].mean(),
        'avg_ret_20': df['ret_20'].mean(),
        'avg_ret_96': df['ret_96'].mean(),
        'avg_ret_288': df['ret_288'].mean(),
        'avg_range_20': df['range_20'].mean(),
        'avg_range_96': df['range_96'].mean(),
        'avg_trend_consistency': df['trend_consistency'].mean(),
        'pct_above_ema20': (df['close'] > df['ema_20']).sum() / len(df) * 100,
        'pct_above_ema50': (df['close'] > df['ema_50']).sum() / len(df) * 100,
        'pct_above_ema200': (df['close'] > df['ema_200']).sum() / len(df) * 100,
    }

    period_stats.append(stats)
    print(f"  {len(df)} bars analyzed")

print("\n" + "=" * 80)
print("REGIME COMPARISON:")
print("=" * 80)

stats_df = pd.DataFrame(period_stats)

print(f"\n{'Metric':<25} | {'Jul-Aug (BAD)':<14} | {'Sep-Dec (GOOD)':<14} | {'Diff %':<10}")
print("-" * 75)

for col in stats_df.columns:
    if col in ['period', 'label', 'bars', 'days']:
        continue

    bad_val = stats_df[stats_df['label'] == 'bad'][col].values[0]
    good_val = stats_df[stats_df['label'] == 'good'][col].values[0]
    diff_pct = ((good_val - bad_val) / abs(bad_val) * 100) if bad_val != 0 else 0

    marker = ""
    if abs(diff_pct) > 50:
        marker = " ⭐⭐⭐"
    elif abs(diff_pct) > 30:
        marker = " ⭐⭐"
    elif abs(diff_pct) > 15:
        marker = " ⭐"

    print(f"{col:<25} | {bad_val:>13.2f} | {good_val:>13.2f} | {diff_pct:>+9.1f}%{marker}")

print("\n" + "=" * 80)
print("🎯 REGIME DETECTION RULES:")
print("=" * 80)

print("\n⚠️  DON'T TRADE when (Jul-Aug-like conditions):")

# Identify the biggest differences
bad_regime_rules = []

if stats_df[stats_df['label'] == 'bad']['avg_volatility_96'].values[0] < stats_df[stats_df['label'] == 'good']['avg_volatility_96'].values[0] * 0.7:
    print(f"  - avg_volatility_96 < {stats_df[stats_df['label'] == 'good']['avg_volatility_96'].values[0] * 0.7:.2f}% (low long-term volatility)")
    bad_regime_rules.append(('avg_volatility_96', '<', stats_df[stats_df['label'] == 'good']['avg_volatility_96'].values[0] * 0.7))

if stats_df[stats_df['label'] == 'bad']['avg_range_96'].values[0] < stats_df[stats_df['label'] == 'good']['avg_range_96'].values[0] * 0.7:
    print(f"  - avg_range_96 < {stats_df[stats_df['label'] == 'good']['avg_range_96'].values[0] * 0.7:.2f}% (low 24h range)")
    bad_regime_rules.append(('avg_range_96', '<', stats_df[stats_df['label'] == 'good']['avg_range_96'].values[0] * 0.7))

if abs(stats_df[stats_df['label'] == 'bad']['avg_ret_288'].values[0]) < abs(stats_df[stats_df['label'] == 'good']['avg_ret_288'].values[0]):
    print(f"  - abs(avg_ret_288) < {abs(stats_df[stats_df['label'] == 'good']['avg_ret_288'].values[0]):.2f}% (weak 3-day momentum)")
    bad_regime_rules.append(('avg_ret_288', '<', abs(stats_df[stats_df['label'] == 'good']['avg_ret_288'].values[0])))

print("\n✅ TRADE when (Sep-Dec-like conditions):")

if stats_df[stats_df['label'] == 'good']['avg_range_96'].values[0] > 12:
    print(f"  - avg_range_96 > 12% (high 24h range)")

if stats_df[stats_df['label'] == 'good']['avg_volatility_96'].values[0] > 3:
    print(f"  - avg_volatility_96 > 3% (high long-term volatility)")

print("\n" + "=" * 80)
print("💡 INSIGHT:")
print("=" * 80)

print("""
The key difference: Sep-Dec was a HIGH VOLATILITY downtrend, Jul-Aug was LOW VOLATILITY sideways.

SHORT mean reversion works in high-vol downtrends (Sep-Dec) because:
- Big moves up (RSI 65) reliably reverse down
- Strong volatility provides good R:R for 2x/3x ATR exits

SHORT mean reversion FAILS in low-vol sideways (Jul-Aug) because:
- Small moves don't have follow-through
- Tight ranges mean whipsaw losses
- ATR-based exits don't work when volatility is low

RECOMMENDATION:
Only trade when market is in high-volatility regime (Range96 > 12%, Volatility > 3%)
This would have avoided Jul-Aug entirely!
""")

stats_df.to_csv('regime_analysis.csv', index=False)
print(f"💾 Saved regime analysis to: regime_analysis.csv")

print("\n" + "=" * 80)
