"""
DEEP ANALYSIS: Why is 15m failing?
Look at actual RSI crosses and what makes them work vs fail
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("DEEP 15M ANALYSIS - UNDERSTANDING THE DATA")
print("=" * 80)

# Download data
exchange = ccxt.bingx({'enableRateLimit': True})

end_date = datetime(2025, 12, 15, tzinfo=timezone.utc)
start_date = end_date - timedelta(days=90)

start_ts = int(start_date.timestamp() * 1000)
end_ts = int(end_date.timestamp() * 1000)

print(f"\nDownloading MELANIA 15m data...")

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
df['atr_pct'] = (df['atr'] / df['close']) * 100

# More context indicators
df['sma_20'] = df['close'].rolling(20).mean()
df['sma_50'] = df['close'].rolling(50).mean()
df['sma_100'] = df['close'].rolling(100).mean()
df['price_vs_sma20'] = ((df['close'] - df['sma_20']) / df['sma_20']) * 100
df['price_vs_sma50'] = ((df['close'] - df['sma_50']) / df['sma_50']) * 100

df['volume_ma'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma']

df['range_20'] = ((df['high'].rolling(20).max() - df['low'].rolling(20).min()) / df['low'].rolling(20).min()) * 100
df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100

print("Indicators calculated")

# Find all RSI crosses
print("\nFinding RSI crosses...")

crosses = []

for i in range(300, len(df)):
    row = df.iloc[i]
    prev_row = df.iloc[i-1]

    if pd.isna(row['rsi']) or pd.isna(prev_row['rsi']):
        continue

    direction = None
    rsi_level = None

    # Test multiple RSI levels
    for level in [20, 25, 30, 35]:
        if prev_row['rsi'] < level and row['rsi'] >= level:
            direction = 'LONG'
            rsi_level = level
            break

    if direction is None:
        for level in [65, 70, 75, 80]:
            if prev_row['rsi'] > level and row['rsi'] <= level:
                direction = 'SHORT'
                rsi_level = level
                break

    if direction is None:
        continue

    # Now check what happens next (forward-looking for analysis)
    entry_price = row['close']
    sl_price = entry_price - (row['atr'] * 2.0) if direction == 'LONG' else entry_price + (row['atr'] * 2.0)

    # Track next 50 bars (12.5 hours)
    best_profit = 0
    worst_drawdown = 0
    hit_sl = False
    bars_to_sl = None

    for j in range(i+1, min(i+51, len(df))):
        bar = df.iloc[j]

        if direction == 'LONG':
            profit = ((bar['high'] - entry_price) / entry_price) * 100
            drawdown = ((bar['low'] - entry_price) / entry_price) * 100

            if bar['low'] <= sl_price:
                hit_sl = True
                bars_to_sl = j - i
                break
        else:
            profit = ((entry_price - bar['low']) / entry_price) * 100
            drawdown = ((entry_price - bar['high']) / entry_price) * 100

            if bar['high'] >= sl_price:
                hit_sl = True
                bars_to_sl = j - i
                break

        best_profit = max(best_profit, profit)
        worst_drawdown = min(worst_drawdown, drawdown)

    # Record cross characteristics
    crosses.append({
        'timestamp': row['timestamp'],
        'direction': direction,
        'rsi_level': rsi_level,
        'entry_rsi': row['rsi'],
        'entry_price': entry_price,
        'atr_pct': row['atr_pct'],
        'price_vs_sma20': row['price_vs_sma20'],
        'price_vs_sma50': row['price_vs_sma50'],
        'volume_ratio': row['volume_ratio'],
        'range_20': row['range_20'],
        'range_96': row['range_96'],
        'best_profit': best_profit,
        'worst_drawdown': worst_drawdown,
        'hit_sl': hit_sl,
        'bars_to_sl': bars_to_sl if hit_sl else 50
    })

df_crosses = pd.DataFrame(crosses)

print(f"\nFound {len(df_crosses)} RSI crosses")
print(f"  LONG: {(df_crosses['direction'] == 'LONG').sum()}")
print(f"  SHORT: {(df_crosses['direction'] == 'SHORT').sum()}")

# Analysis
print("\n" + "=" * 80)
print("OVERALL STATISTICS:")
print("=" * 80)

print(f"\nSL Hit Rate: {(df_crosses['hit_sl']).sum() / len(df_crosses) * 100:.1f}%")
print(f"Avg Best Profit: {df_crosses['best_profit'].mean():.2f}%")
print(f"Avg Worst DD: {df_crosses['worst_drawdown'].mean():.2f}%")
print(f"Avg Bars to SL: {df_crosses['bars_to_sl'].mean():.1f}")

# Winners vs Losers (define winner as best_profit > 2% before hitting SL)
df_crosses['is_winner'] = (df_crosses['best_profit'] > 2.0) & (~df_crosses['hit_sl'] | (df_crosses['best_profit'] > abs(df_crosses['worst_drawdown'])))

winners = df_crosses[df_crosses['is_winner']]
losers = df_crosses[~df_crosses['is_winner']]

print(f"\nWinners (>2% profit, no SL): {len(winners)} ({len(winners)/len(df_crosses)*100:.1f}%)")
print(f"Losers: {len(losers)} ({len(losers)/len(df_crosses)*100:.1f}%)")

if len(winners) > 0 and len(losers) > 0:
    print("\n" + "=" * 80)
    print("WINNERS vs LOSERS COMPARISON:")
    print("=" * 80)

    metrics = ['entry_rsi', 'atr_pct', 'price_vs_sma20', 'price_vs_sma50', 'volume_ratio', 'range_20', 'range_96']

    print(f"\n{'Metric':<20} | {'Winners':<12} | {'Losers':<12} | {'Difference':<12}")
    print("-" * 80)

    for metric in metrics:
        w_avg = winners[metric].mean()
        l_avg = losers[metric].mean()
        diff = ((w_avg - l_avg) / abs(l_avg) * 100) if l_avg != 0 else 0
        print(f"{metric:<20} | {w_avg:>11.2f} | {l_avg:>11.2f} | {diff:>10.1f}%")

# By RSI level
print("\n" + "=" * 80)
print("BY RSI LEVEL:")
print("=" * 80)

for level in sorted(df_crosses['rsi_level'].unique()):
    level_data = df_crosses[df_crosses['rsi_level'] == level]
    level_winners = level_data[level_data['is_winner']]

    print(f"\nRSI {level}:")
    print(f"  Total: {len(level_data)}")
    print(f"  Winners: {len(level_winners)} ({len(level_winners)/len(level_data)*100:.1f}%)")
    print(f"  Avg Best Profit: {level_data['best_profit'].mean():.2f}%")
    print(f"  SL Hit Rate: {level_data['hit_sl'].sum() / len(level_data) * 100:.1f}%")

# By direction
print("\n" + "=" * 80)
print("BY DIRECTION:")
print("=" * 80)

for direction in ['LONG', 'SHORT']:
    dir_data = df_crosses[df_crosses['direction'] == direction]
    dir_winners = dir_data[dir_data['is_winner']]

    print(f"\n{direction}:")
    print(f"  Total: {len(dir_data)}")
    print(f"  Winners: {len(dir_winners)} ({len(dir_winners)/len(dir_data)*100:.1f}%)")
    print(f"  Avg Best Profit: {dir_data['best_profit'].mean():.2f}%")
    print(f"  SL Hit Rate: {dir_data['hit_sl'].sum() / len(dir_data) * 100:.1f}%")

# Find filters
print("\n" + "=" * 80)
print("POTENTIAL FILTERS:")
print("=" * 80)

# Test various filters
filters = [
    ('ATR% > 3%', df_crosses['atr_pct'] > 3.0),
    ('ATR% > 4%', df_crosses['atr_pct'] > 4.0),
    ('Volume > 1.5x', df_crosses['volume_ratio'] > 1.5),
    ('Volume > 2.0x', df_crosses['volume_ratio'] > 2.0),
    ('Price vs SMA20 < -5%', df_crosses['price_vs_sma20'] < -5),
    ('Price vs SMA50 < -10%', df_crosses['price_vs_sma50'] < -10),
    ('Range20 > 15%', df_crosses['range_20'] > 15),
    ('Range96 > 20%', df_crosses['range_96'] > 20),
]

print(f"\n{'Filter':<25} | {'Signals':<8} | {'Win%':<8} | {'Avg Profit':<12}")
print("-" * 80)

for filter_name, filter_mask in filters:
    filtered = df_crosses[filter_mask]
    if len(filtered) > 0:
        win_rate = (filtered['is_winner'].sum() / len(filtered)) * 100
        avg_profit = filtered['best_profit'].mean()
        print(f"{filter_name:<25} | {len(filtered):>7} | {win_rate:>6.1f}% | {avg_profit:>10.2f}%")

# Combo filters
print("\n" + "=" * 80)
print("COMBINATION FILTERS:")
print("=" * 80)

combos = [
    ('ATR>3% + Vol>1.5x', (df_crosses['atr_pct'] > 3.0) & (df_crosses['volume_ratio'] > 1.5)),
    ('ATR>4% + Vol>2.0x', (df_crosses['atr_pct'] > 4.0) & (df_crosses['volume_ratio'] > 2.0)),
    ('Price<SMA20 -5% + Range20>15%', (df_crosses['price_vs_sma20'] < -5) & (df_crosses['range_20'] > 15)),
    ('ATR>3% + Range96>20%', (df_crosses['atr_pct'] > 3.0) & (df_crosses['range_96'] > 20)),
]

print(f"\n{'Filter':<35} | {'Signals':<8} | {'Win%':<8} | {'Avg Profit':<12}")
print("-" * 80)

best_combo = None
best_score = 0

for filter_name, filter_mask in combos:
    filtered = df_crosses[filter_mask]
    if len(filtered) > 5:  # Need minimum signals
        win_rate = (filtered['is_winner'].sum() / len(filtered)) * 100
        avg_profit = filtered['best_profit'].mean()
        score = win_rate * avg_profit  # Simple scoring

        print(f"{filter_name:<35} | {len(filtered):>7} | {win_rate:>6.1f}% | {avg_profit:>10.2f}%")

        if score > best_score and win_rate > 30:
            best_score = score
            best_combo = (filter_name, filter_mask)

if best_combo:
    print("\n" + "=" * 80)
    print("🏆 BEST FILTER COMBO:")
    print("=" * 80)
    print(f"\n{best_combo[0]}")

    best_data = df_crosses[best_combo[1]]
    print(f"\nSignals: {len(best_data)}")
    print(f"Win Rate: {(best_data['is_winner'].sum() / len(best_data)) * 100:.1f}%")
    print(f"Avg Best Profit: {best_data['best_profit'].mean():.2f}%")
    print(f"SL Hit Rate: {best_data['hit_sl'].sum() / len(best_data) * 100:.1f}%")

    # Show winner characteristics
    best_winners = best_data[best_data['is_winner']]
    if len(best_winners) > 0:
        print(f"\nWinner Characteristics:")
        print(f"  Avg RSI at entry: {best_winners['entry_rsi'].mean():.1f}")
        print(f"  Avg ATR%: {best_winners['atr_pct'].mean():.2f}%")
        print(f"  Avg Price vs SMA20: {best_winners['price_vs_sma20'].mean():.2f}%")
        print(f"  Avg Volume Ratio: {best_winners['volume_ratio'].mean():.2f}x")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)

df_crosses.to_csv('melania_15m_crosses_analysis.csv', index=False)
print("\n💾 Saved: melania_15m_crosses_analysis.csv")
