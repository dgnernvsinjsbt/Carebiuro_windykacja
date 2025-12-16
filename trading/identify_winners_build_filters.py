"""
SMART APPROACH: Find the 40-60 BEST trades, then build filters around them

Instead of guessing filters, let the winners tell us what works!
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone, timedelta
import time

print("=" * 80)
print("WINNER-DRIVEN FILTER DISCOVERY")
print("Find top 40-60 trades, then reverse-engineer the filters")
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

# Calculate ALL indicators we might use for filtering
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

# Various range measures
df['range_20'] = ((df['high'].rolling(20).max() - df['low'].rolling(20).min()) / df['low'].rolling(20).min()) * 100
df['range_96'] = ((df['high'].rolling(96).max() - df['low'].rolling(96).min()) / df['low'].rolling(96).min()) * 100

# Volume
df['volume_ma_20'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_ma_20']

# Momentum
df['ret_5'] = (df['close'] / df['close'].shift(5) - 1) * 100  # 5-bar momentum
df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100  # 20-bar momentum

# EMA
df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
df['ema_dist'] = ((df['close'] - df['ema_20']) / df['ema_20']) * 100

print("All indicators calculated")

# Run VERY loose baseline - get as many trades as possible
print("\n" + "=" * 80)
print("BASELINE: RSI 35/65, NO FILTERS - Capture ALL possible trades")
print("=" * 80)

trades = []
position = None

i = 300
while i < len(df):
    row = df.iloc[i]

    if pd.isna(row['rsi']) or pd.isna(row['atr']):
        i += 1
        continue

    # Manage position
    if position is not None:
        bar = row

        if position['direction'] == 'LONG':
            if bar['low'] <= position['sl_price']:
                position['exit_type'] = 'SL'
                position['exit_price'] = position['sl_price']
                position['exit_idx'] = i
                position['pnl_pct'] = ((position['sl_price'] - position['entry']) / position['entry']) * 100
                position['bars_held'] = i - position['entry_idx']
                trades.append(position)
                position = None
                i += 1
                continue

            if bar['high'] >= position['tp_price']:
                position['exit_type'] = 'TP'
                position['exit_price'] = position['tp_price']
                position['exit_idx'] = i
                position['pnl_pct'] = ((position['tp_price'] - position['entry']) / position['entry']) * 100
                position['bars_held'] = i - position['entry_idx']
                trades.append(position)
                position = None
                i += 1
                continue

        elif position['direction'] == 'SHORT':
            if bar['high'] >= position['sl_price']:
                position['exit_type'] = 'SL'
                position['exit_price'] = position['sl_price']
                position['exit_idx'] = i
                position['pnl_pct'] = ((position['entry'] - position['sl_price']) / position['entry']) * 100
                position['bars_held'] = i - position['entry_idx']
                trades.append(position)
                position = None
                i += 1
                continue

            if bar['low'] <= position['tp_price']:
                position['exit_type'] = 'TP'
                position['exit_price'] = position['tp_price']
                position['exit_idx'] = i
                position['pnl_pct'] = ((position['entry'] - position['tp_price']) / position['entry']) * 100
                position['bars_held'] = i - position['entry_idx']
                trades.append(position)
                position = None
                i += 1
                continue

    # New entries
    if position is None and i > 0:
        prev_row = df.iloc[i-1]

        if not pd.isna(prev_row['rsi']):
            # LONG signal
            if prev_row['rsi'] < 35 and row['rsi'] >= 35:
                entry_price = row['close']
                sl_price = entry_price - (row['atr'] * 2.0)
                tp_price = entry_price + (row['atr'] * 3.0)

                position = {
                    'direction': 'LONG',
                    'entry': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'entry_idx': i,
                    'entry_rsi': row['rsi'],
                    'entry_atr_pct': row['atr_pct'],
                    'entry_range_20': row['range_20'],
                    'entry_range_96': row['range_96'],
                    'entry_volume_ratio': row['volume_ratio'],
                    'entry_ret_5': row['ret_5'],
                    'entry_ret_20': row['ret_20'],
                    'entry_ema_dist': row['ema_dist'],
                    'entry_price_val': entry_price,
                    'entry_ema_20': row['ema_20'],
                    'entry_ema_50': row['ema_50']
                }

            # SHORT signal
            elif prev_row['rsi'] > 65 and row['rsi'] <= 65:
                entry_price = row['close']
                sl_price = entry_price + (row['atr'] * 2.0)
                tp_price = entry_price - (row['atr'] * 3.0)

                position = {
                    'direction': 'SHORT',
                    'entry': entry_price,
                    'sl_price': sl_price,
                    'tp_price': tp_price,
                    'entry_idx': i,
                    'entry_rsi': row['rsi'],
                    'entry_atr_pct': row['atr_pct'],
                    'entry_range_20': row['range_20'],
                    'entry_range_96': row['range_96'],
                    'entry_volume_ratio': row['volume_ratio'],
                    'entry_ret_5': row['ret_5'],
                    'entry_ret_20': row['ret_20'],
                    'entry_ema_dist': row['ema_dist'],
                    'entry_price_val': entry_price,
                    'entry_ema_20': row['ema_20'],
                    'entry_ema_50': row['ema_50']
                }

    i += 1

trades_df = pd.DataFrame(trades)

print(f"\nTotal trades captured: {len(trades_df)}")
print(f"LONG: {len(trades_df[trades_df['direction'] == 'LONG'])}")
print(f"SHORT: {len(trades_df[trades_df['direction'] == 'SHORT'])}")
print(f"Winners: {len(trades_df[trades_df['pnl_pct'] > 0])}")
print(f"Losers: {len(trades_df[trades_df['pnl_pct'] < 0])}")

# Rank by profit
trades_df = trades_df.sort_values('pnl_pct', ascending=False).reset_index(drop=True)

# Top 40-60 trades
top_n = min(60, max(40, len(trades_df) // 2))  # Get 40-60 or half, whichever is appropriate
top_trades = trades_df.head(top_n)
bottom_trades = trades_df[trades_df['pnl_pct'] < 0]  # All losers

print("\n" + "=" * 80)
print(f"ANALYZING TOP {len(top_trades)} WINNERS vs {len(bottom_trades)} LOSERS")
print("=" * 80)

# Compare characteristics
features = ['entry_rsi', 'entry_atr_pct', 'entry_range_20', 'entry_range_96',
            'entry_volume_ratio', 'entry_ret_5', 'entry_ret_20', 'entry_ema_dist']

print("\n📊 WINNER vs LOSER CHARACTERISTICS:\n")
print(f"{'Feature':<20} | {'Winners Avg':<12} | {'Losers Avg':<12} | {'Diff %':<10} | Rating")
print("-" * 80)

winner_profiles = {}
for feature in features:
    if feature in top_trades.columns and feature in bottom_trades.columns:
        winner_avg = top_trades[feature].mean()
        loser_avg = bottom_trades[feature].mean()
        diff_pct = ((winner_avg - loser_avg) / abs(loser_avg) * 100) if loser_avg != 0 else 0

        winner_profiles[feature] = winner_avg

        # Rating
        if abs(diff_pct) > 30:
            rating = "⭐⭐⭐ CRITICAL"
        elif abs(diff_pct) > 15:
            rating = "⭐⭐ IMPORTANT"
        elif abs(diff_pct) > 5:
            rating = "⭐ USEFUL"
        else:
            rating = "❌ WEAK"

        print(f"{feature:<20} | {winner_avg:>12.2f} | {loser_avg:>12.2f} | {diff_pct:>9.1f}% | {rating}")

# Separate LONG vs SHORT analysis
print("\n" + "=" * 80)
print("LONG vs SHORT BREAKDOWN:")
print("=" * 80)

top_longs = top_trades[top_trades['direction'] == 'LONG']
top_shorts = top_trades[top_trades['direction'] == 'SHORT']
loser_longs = bottom_trades[bottom_trades['direction'] == 'LONG']
loser_shorts = bottom_trades[bottom_trades['direction'] == 'SHORT']

print(f"\nLONG: {len(top_longs)} top winners, {len(loser_longs)} losers")
print(f"SHORT: {len(top_shorts)} top winners, {len(loser_shorts)} losers")

if len(top_longs) > 0:
    print(f"\nTop LONG avg profit: {top_longs['pnl_pct'].mean():.2f}%")
    print(f"  ATR%: {top_longs['entry_atr_pct'].mean():.2f}%")
    print(f"  Range96: {top_longs['entry_range_96'].mean():.2f}%")
    print(f"  Volume Ratio: {top_longs['entry_volume_ratio'].mean():.2f}x")
    print(f"  EMA Distance: {top_longs['entry_ema_dist'].mean():.2f}%")

if len(top_shorts) > 0:
    print(f"\nTop SHORT avg profit: {top_shorts['pnl_pct'].mean():.2f}%")
    print(f"  ATR%: {top_shorts['entry_atr_pct'].mean():.2f}%")
    print(f"  Range96: {top_shorts['entry_range_96'].mean():.2f}%")
    print(f"  Volume Ratio: {top_shorts['entry_volume_ratio'].mean():.2f}x")
    print(f"  EMA Distance: {top_shorts['entry_ema_dist'].mean():.2f}%")

# Suggest filters based on analysis
print("\n" + "=" * 80)
print("💡 SUGGESTED FILTERS (based on top winners):")
print("=" * 80)

print(f"\n✅ Keep winners by requiring:")
print(f"  ATR% > {winner_profiles.get('entry_atr_pct', 0) * 0.7:.1f}% (70% of winner avg)")
print(f"  Range96 > {winner_profiles.get('entry_range_96', 0) * 0.7:.1f}% (70% of winner avg)")

if winner_profiles.get('entry_volume_ratio', 1.0) > 1.5:
    print(f"  Volume Ratio > {winner_profiles.get('entry_volume_ratio', 0) * 0.8:.1f}x (80% of winner avg)")

if abs(winner_profiles.get('entry_ema_dist', 0)) < 5:
    print(f"  EMA Distance: Price within {abs(winner_profiles.get('entry_ema_dist', 0)) * 1.5:.1f}% of EMA20")

# Show top 10 best trades
print("\n" + "=" * 80)
print("🏆 TOP 10 BEST TRADES:")
print("=" * 80)

print(f"\n| # | Dir   | PnL   | ATR% | R96%  | Vol  | EMA% | Ret5% | Exit | Bars |")
print("|---|-------|-------|------|-------|------|------|-------|------|------|")

for idx, trade in top_trades.head(10).iterrows():
    print(f"| {idx+1:2d} | {trade['direction']:5s} | {trade['pnl_pct']:5.1f}% | "
          f"{trade['entry_atr_pct']:4.1f} | {trade['entry_range_96']:5.1f} | "
          f"{trade['entry_volume_ratio']:4.1f} | {trade['entry_ema_dist']:+4.1f}% | "
          f"{trade['entry_ret_5']:+5.1f}% | {trade['exit_type']:4s} | {trade['bars_held']:4.0f} |")

# Save for further analysis
trades_df.to_csv('all_trades_ranked.csv', index=False)
print(f"\n💾 Saved {len(trades_df)} ranked trades to: all_trades_ranked.csv")
print(f"   Top {len(top_trades)} winners marked for filter design")
