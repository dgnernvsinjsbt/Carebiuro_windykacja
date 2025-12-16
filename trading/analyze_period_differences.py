"""
DEEP ANALYSIS: Why did Sep-Dec work but Jul-Aug fail?

1. Compare market conditions between periods
2. Analyze trade characteristics
3. Find filters that work on BOTH periods
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("PERIOD COMPARISON ANALYSIS")
print("Understanding Jul-Aug vs Sep-Dec differences")
print("=" * 80)

exchange = ccxt.bingx({'enableRateLimit': True})

# Download both periods
periods = [
    {
        'name': 'Jul-Aug 2025',
        'start': datetime(2025, 7, 1, tzinfo=timezone.utc),
        'end': datetime(2025, 8, 31, 23, 59, 59, tzinfo=timezone.utc)
    },
    {
        'name': 'Sep-Dec 2025',
        'start': datetime(2025, 9, 16, tzinfo=timezone.utc),
        'end': datetime(2025, 12, 15, tzinfo=timezone.utc)
    }
]

all_period_data = []

for period in periods:
    print(f"\nDownloading {period['name']}...")

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
            print(f"Error: {e}")
            time.sleep(2)
            continue

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_localize(None)
    df = df[(df['timestamp'] >= period['start'].replace(tzinfo=None)) &
            (df['timestamp'] <= period['end'].replace(tzinfo=None))]
    df = df.sort_values('timestamp').reset_index(drop=True)

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
    df['atr_pct'] = (df['atr'] / df['close']) * 100

    df['ret_5'] = (df['close'] / df['close'].shift(5) - 1) * 100
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100
    df['ret_96'] = (df['close'] / df['close'].shift(96) - 1) * 100

    df['range_20'] = ((df['high'].rolling(20).max() - df['low'].rolling(20).min()) /
                      df['low'].rolling(20).min()) * 100
    df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) /
                      df['low'].rolling(96).min()) * 100

    # Volume
    df['volume_ma_20'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma_20']

    # Trend strength
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['trend_strength'] = ((df['ema_20'] - df['ema_50']) / df['ema_50']) * 100

    period['df'] = df
    all_period_data.append(period)
    print(f"  {len(df)} bars loaded")

print("\n" + "=" * 80)
print("MARKET CONDITION COMPARISON:")
print("=" * 80)

jul_aug_df = all_period_data[0]['df']
sep_dec_df = all_period_data[1]['df']

# Compare overall market conditions
print(f"\n{'Metric':<25} | {'Jul-Aug':<12} | {'Sep-Dec':<12} | {'Difference':<10}")
print("-" * 70)

metrics = {
    'Avg ATR%': ('atr_pct', 'mean'),
    'Avg Range20': ('range_20', 'mean'),
    'Avg Range96': ('range_96', 'mean'),
    'Avg ret_20': ('ret_20', 'mean'),
    'Avg ret_96': ('ret_96', 'mean'),
    'Avg Volume Ratio': ('volume_ratio', 'mean'),
    'Avg Trend Strength': ('trend_strength', 'mean'),
    'Price Change (total)': ('close', lambda x: (x.iloc[-1] / x.iloc[0] - 1) * 100),
}

conditions_diff = {}

for metric_name, (col, func) in metrics.items():
    if callable(func):
        jul_aug_val = func(jul_aug_df[col])
        sep_dec_val = func(sep_dec_df[col])
    else:
        jul_aug_val = getattr(jul_aug_df[col], func)()
        sep_dec_val = getattr(sep_dec_df[col], func)()

    diff = sep_dec_val - jul_aug_val
    diff_pct = (diff / abs(jul_aug_val) * 100) if jul_aug_val != 0 else 0

    conditions_diff[metric_name] = {
        'jul_aug': jul_aug_val,
        'sep_dec': sep_dec_val,
        'diff_pct': diff_pct
    }

    print(f"{metric_name:<25} | {jul_aug_val:>11.2f} | {sep_dec_val:>11.2f} | {diff_pct:>+9.1f}%")

# Now analyze TRADES in both periods
print("\n" + "=" * 80)
print("TRADE ANALYSIS - RSI 35/65 + ret_20 > 0%:")
print("=" * 80)

def analyze_trades(df, period_name):
    """Run strategy and analyze trades"""
    trades = []
    position = None

    i = 300
    while i < len(df):
        row = df.iloc[i]

        if pd.isna(row['rsi']) or pd.isna(row['atr']) or pd.isna(row['ret_20']):
            i += 1
            continue

        # Manage position
        if position is not None:
            bar = row

            if position['direction'] == 'LONG':
                if bar['low'] <= position['sl_price']:
                    position['exit_type'] = 'SL'
                    position['exit_idx'] = i
                    position['pnl_pct'] = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                    trades.append(position)
                    position = None
                    i += 1
                    continue

                if bar['high'] >= position['tp_price']:
                    position['exit_type'] = 'TP'
                    position['exit_idx'] = i
                    position['pnl_pct'] = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                    trades.append(position)
                    position = None
                    i += 1
                    continue

            elif position['direction'] == 'SHORT':
                if bar['high'] >= position['sl_price']:
                    position['exit_type'] = 'SL'
                    position['exit_idx'] = i
                    position['pnl_pct'] = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                    trades.append(position)
                    position = None
                    i += 1
                    continue

                if bar['low'] <= position['tp_price']:
                    position['exit_type'] = 'TP'
                    position['exit_idx'] = i
                    position['pnl_pct'] = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                    trades.append(position)
                    position = None
                    i += 1
                    continue

        # New entries
        if position is None and i > 0:
            prev_row = df.iloc[i-1]

            # Filter: ret_20 > 0%
            if row['ret_20'] <= 0:
                i += 1
                continue

            if not pd.isna(prev_row['rsi']):
                if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                    position = {
                        'direction': 'LONG',
                        'entry': row['close'],
                        'sl_price': row['close'] - (row['atr'] * 2.0),
                        'tp_price': row['close'] + (row['atr'] * 3.0),
                        'entry_idx': i,
                        'entry_rsi': row['rsi'],
                        'entry_atr_pct': row['atr_pct'],
                        'entry_ret_20': row['ret_20'],
                        'entry_ret_96': row['ret_96'],
                        'entry_range_20': row['range_20'],
                        'entry_range_96': row['range_96'],
                        'entry_volume_ratio': row['volume_ratio'],
                        'entry_trend_strength': row['trend_strength']
                    }

                elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                    position = {
                        'direction': 'SHORT',
                        'entry': row['close'],
                        'sl_price': row['close'] + (row['atr'] * 2.0),
                        'tp_price': row['close'] - (row['atr'] * 3.0),
                        'entry_idx': i,
                        'entry_rsi': row['rsi'],
                        'entry_atr_pct': row['atr_pct'],
                        'entry_ret_20': row['ret_20'],
                        'entry_ret_96': row['ret_96'],
                        'entry_range_20': row['range_20'],
                        'entry_range_96': row['range_96'],
                        'entry_volume_ratio': row['volume_ratio'],
                        'entry_trend_strength': row['trend_strength']
                    }

        i += 1

    return pd.DataFrame(trades)

jul_aug_trades = analyze_trades(jul_aug_df, 'Jul-Aug')
sep_dec_trades = analyze_trades(sep_dec_df, 'Sep-Dec')

print(f"\nJul-Aug: {len(jul_aug_trades)} trades ({(jul_aug_trades['pnl_pct'] > 0).sum()}/{len(jul_aug_trades)} wins = {(jul_aug_trades['pnl_pct'] > 0).sum()/len(jul_aug_trades)*100:.1f}%)")
print(f"Sep-Dec: {len(sep_dec_trades)} trades ({(sep_dec_trades['pnl_pct'] > 0).sum()}/{len(sep_dec_trades)} wins = {(sep_dec_trades['pnl_pct'] > 0).sum()/len(sep_dec_trades)*100:.1f}%)")

# Compare winner characteristics
jul_aug_winners = jul_aug_trades[jul_aug_trades['pnl_pct'] > 0]
jul_aug_losers = jul_aug_trades[jul_aug_trades['pnl_pct'] < 0]
sep_dec_winners = sep_dec_trades[sep_dec_trades['pnl_pct'] > 0]
sep_dec_losers = sep_dec_trades[sep_dec_trades['pnl_pct'] < 0]

print("\n" + "=" * 80)
print("WINNER CHARACTERISTICS COMPARISON:")
print("=" * 80)

features = ['entry_atr_pct', 'entry_ret_20', 'entry_ret_96', 'entry_range_20',
            'entry_range_96', 'entry_volume_ratio', 'entry_trend_strength']

print(f"\n{'Feature':<20} | {'Jul-Aug Win':<11} | {'Sep-Dec Win':<11} | {'Difference':<10}")
print("-" * 65)

for feature in features:
    jul_aug_win_avg = jul_aug_winners[feature].mean()
    sep_dec_win_avg = sep_dec_winners[feature].mean()
    diff = sep_dec_win_avg - jul_aug_win_avg

    print(f"{feature:<20} | {jul_aug_win_avg:>10.2f} | {sep_dec_win_avg:>10.2f} | {diff:>+9.2f}")

print("\n" + "=" * 80)
print("LOSER CHARACTERISTICS COMPARISON:")
print("=" * 80)

print(f"\n{'Feature':<20} | {'Jul-Aug Loss':<11} | {'Sep-Dec Loss':<11} | {'Difference':<10}")
print("-" * 65)

for feature in features:
    jul_aug_loss_avg = jul_aug_losers[feature].mean()
    sep_dec_loss_avg = sep_dec_losers[feature].mean()
    diff = sep_dec_loss_avg - jul_aug_loss_avg

    print(f"{feature:<20} | {jul_aug_loss_avg:>10.2f} | {sep_dec_loss_avg:>10.2f} | {diff:>+9.2f}")

# KEY INSIGHT: What separates winners from losers IN EACH PERIOD?
print("\n" + "=" * 80)
print("KEY DIFFERENCES (Winners vs Losers) IN EACH PERIOD:")
print("=" * 80)

print(f"\n{'Feature':<20} | {'Jul-Aug (W-L)':<13} | {'Sep-Dec (W-L)':<13} | {'Universal?':<10}")
print("-" * 70)

universal_filters = []

for feature in features:
    jul_aug_diff = jul_aug_winners[feature].mean() - jul_aug_losers[feature].mean()
    sep_dec_diff = sep_dec_winners[feature].mean() - sep_dec_losers[feature].mean()

    # Universal if both differences have same sign and are significant (>10%)
    jul_aug_pct = (jul_aug_diff / abs(jul_aug_losers[feature].mean()) * 100) if jul_aug_losers[feature].mean() != 0 else 0
    sep_dec_pct = (sep_dec_diff / abs(sep_dec_losers[feature].mean()) * 100) if sep_dec_losers[feature].mean() != 0 else 0

    is_universal = (jul_aug_diff * sep_dec_diff > 0) and (abs(jul_aug_pct) > 10 and abs(sep_dec_pct) > 10)
    universal_mark = "⭐ YES" if is_universal else "❌ No"

    if is_universal:
        universal_filters.append({
            'feature': feature,
            'jul_aug_diff': jul_aug_diff,
            'sep_dec_diff': sep_dec_diff,
            'direction': 'higher' if jul_aug_diff > 0 else 'lower'
        })

    print(f"{feature:<20} | {jul_aug_diff:>+12.2f} | {sep_dec_diff:>+12.2f} | {universal_mark:<10}")

print("\n" + "=" * 80)
print("🎯 UNIVERSAL FILTERS (Work in BOTH periods):")
print("=" * 80)

if len(universal_filters) > 0:
    print("\nThese features separate winners from losers in BOTH Jul-Aug AND Sep-Dec:")
    for f in universal_filters:
        print(f"\n  ⭐ {f['feature']}")
        print(f"     Winners have {f['direction']} values in BOTH periods")
        print(f"     Jul-Aug diff: {f['jul_aug_diff']:+.2f}")
        print(f"     Sep-Dec diff: {f['sep_dec_diff']:+.2f}")

    print("\n💡 RECOMMENDATION:")
    print("   Use these filters to improve strategy on BOTH periods!")
else:
    print("\n⚠️  No universal filters found!")
    print("   Winners in Jul-Aug have different characteristics than winners in Sep-Dec")
    print("   This explains why the strategy failed validation")

# Save analysis
jul_aug_trades.to_csv('jul_aug_trades_detailed.csv', index=False)
sep_dec_trades.to_csv('sep_dec_trades_detailed.csv', index=False)

print(f"\n💾 Saved trade details:")
print(f"   - jul_aug_trades_detailed.csv ({len(jul_aug_trades)} trades)")
print(f"   - sep_dec_trades_detailed.csv ({len(sep_dec_trades)} trades)")

print("\n" + "=" * 80)
