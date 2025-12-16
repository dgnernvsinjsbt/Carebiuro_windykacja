"""
Analyze SIGNAL characteristics in bad vs good months
Find real-time indicators that separate losers from winners

NOT monthly averages - SIGNAL-LEVEL metrics we can check at entry time
"""

import pandas as pd
import numpy as np
import ccxt
from datetime import datetime, timezone
import time

print("=" * 80)
print("Signal-Level Analysis: What separates bad trades from good?")
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

# Calculate ALL potential indicators at signal time
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

# Moving averages
df['sma20'] = df['close'].rolling(20).mean()
df['sma50'] = df['close'].rolling(50).mean()
df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

# Distance from MAs (%)
df['price_vs_sma20'] = ((df['close'] - df['sma20']) / df['sma20']) * 100
df['price_vs_sma50'] = ((df['close'] - df['sma50']) / df['sma50']) * 100

# Volatility
df['returns'] = df['close'].pct_change() * 100
df['volatility_20'] = df['returns'].rolling(20).std()

# Volume
df['volume_sma20'] = df['volume'].rolling(20).mean()
df['volume_ratio'] = df['volume'] / df['volume_sma20']

# Recent price action
df['returns_24h'] = df['close'].pct_change(24) * 100  # Last 24 hours return
df['high_24h'] = df['high'].rolling(24).max()
df['low_24h'] = df['low'].rolling(24).min()
df['range_24h'] = ((df['high_24h'] - df['low_24h']) / df['low_24h']) * 100

# RSI extremes frequency (last 7 days = 168 hours)
df['rsi_oversold_7d'] = (df['rsi'] < 30).rolling(168).sum()
df['rsi_overbought_7d'] = (df['rsi'] > 70).rolling(168).sum()

# Trend direction (SMA20 vs SMA50)
df['trend'] = np.where(df['sma20'] > df['sma50'], 1, -1)  # 1 = uptrend, -1 = downtrend

# Month
df['month'] = df['timestamp'].dt.to_period('M').astype(str)

# Config
RSI_LOW = 25
RSI_HIGH = 68
LIMIT_PCT = 0.3
SL_MULT = 3.0
TP_MULT = 2.0
RISK_PCT = 10.0

# Track all signals with their characteristics
signals = []
equity = 100.0

i = 168  # Start after 7 days for indicators to warm up
while i < len(df):
    row = df.iloc[i]
    prev_row = df.iloc[i-1] if i > 0 else None

    if pd.isna(row['rsi']) or pd.isna(row['atr']) or prev_row is None or pd.isna(prev_row['rsi']):
        i += 1
        continue

    # Check if signal appears
    has_signal = False
    direction = None

    if prev_row['rsi'] < RSI_LOW and row['rsi'] >= RSI_LOW:
        has_signal = True
        direction = 'LONG'
    elif prev_row['rsi'] > RSI_HIGH and row['rsi'] <= RSI_HIGH:
        has_signal = True
        direction = 'SHORT'

    if not has_signal:
        i += 1
        continue

    # Capture signal characteristics AT THIS MOMENT
    signal_characteristics = {
        'timestamp': row['timestamp'],
        'month': row['month'],
        'direction': direction,
        'rsi': row['rsi'],
        'atr_pct': row['atr_pct'],
        'price_vs_sma20': row['price_vs_sma20'],
        'price_vs_sma50': row['price_vs_sma50'],
        'volatility_20': row['volatility_20'],
        'volume_ratio': row['volume_ratio'],
        'returns_24h': row['returns_24h'],
        'range_24h': row['range_24h'],
        'rsi_oversold_7d': row['rsi_oversold_7d'],
        'rsi_overbought_7d': row['rsi_overbought_7d'],
        'trend': row['trend']
    }

    # Simulate trade outcome
    signal_price = row['close']
    if direction == 'LONG':
        entry_price = signal_price * (1 + LIMIT_PCT / 100)
        sl_price = entry_price - (row['atr'] * SL_MULT)
        tp_price = entry_price + (row['atr'] * TP_MULT)
    else:
        entry_price = signal_price * (1 - LIMIT_PCT / 100)
        sl_price = entry_price + (row['atr'] * SL_MULT)
        tp_price = entry_price - (row['atr'] * TP_MULT)

    risk_dollars = equity * (RISK_PCT / 100)
    sl_distance_pct = abs((entry_price - sl_price) / entry_price) * 100 if direction == 'LONG' else abs((sl_price - entry_price) / entry_price) * 100
    position_size_dollars = risk_dollars / (sl_distance_pct / 100)

    # Wait for fill
    filled = False
    fill_idx = None
    for j in range(i + 1, min(i + 4, len(df))):
        if direction == 'LONG' and df.iloc[j]['low'] <= entry_price:
            filled = True
            fill_idx = j
            break
        elif direction == 'SHORT' and df.iloc[j]['high'] >= entry_price:
            filled = True
            fill_idx = j
            break

    if not filled:
        i += 1
        continue

    # Look for exit
    exit_idx = None
    exit_price = None
    exit_type = None

    for k in range(fill_idx + 1, len(df)):
        bar = df.iloc[k]
        prev_bar = df.iloc[k-1]

        if direction == 'LONG':
            if bar['low'] <= sl_price:
                exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                break
            if bar['high'] >= tp_price:
                exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                break
            if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                if prev_bar['rsi'] > RSI_HIGH and bar['rsi'] <= RSI_HIGH:
                    exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                    break
        else:
            if bar['high'] >= sl_price:
                exit_idx, exit_price, exit_type = k, sl_price, 'SL'
                break
            if bar['low'] <= tp_price:
                exit_idx, exit_price, exit_type = k, tp_price, 'TP'
                break
            if not pd.isna(bar['rsi']) and not pd.isna(prev_bar['rsi']):
                if prev_bar['rsi'] < RSI_LOW and bar['rsi'] >= RSI_LOW:
                    exit_idx, exit_price, exit_type = k, bar['close'], 'OPPOSITE'
                    break

    if exit_idx is None:
        i += 1
        continue

    # Calculate outcome
    if direction == 'LONG':
        price_change_pct = ((exit_price - entry_price) / entry_price) * 100
    else:
        price_change_pct = ((entry_price - exit_price) / entry_price) * 100

    pnl_before_fees = position_size_dollars * (price_change_pct / 100)
    fees = position_size_dollars * 0.001
    pnl_dollars = pnl_before_fees - fees

    signal_characteristics['exit_type'] = exit_type
    signal_characteristics['pnl_dollars'] = pnl_dollars
    signal_characteristics['winner'] = pnl_dollars > 0

    signals.append(signal_characteristics)

    equity += pnl_dollars
    i = exit_idx + 1

# Analyze
df_signals = pd.DataFrame(signals)

print("\n" + "=" * 80)
print("WINNERS vs LOSERS COMPARISON:")
print("=" * 80)

winners = df_signals[df_signals['winner'] == True]
losers = df_signals[df_signals['winner'] == False]

print(f"\nTotal signals: {len(df_signals)}")
print(f"Winners: {len(winners)} ({len(winners)/len(df_signals)*100:.1f}%)")
print(f"Losers: {len(losers)} ({len(losers)/len(df_signals)*100:.1f}%)")

# Compare characteristics
print("\n" + "=" * 80)
print("SIGNAL CHARACTERISTICS AT ENTRY TIME:")
print("=" * 80)

metrics = [
    ('ATR % (volatility)', 'atr_pct'),
    ('Price vs SMA20 %', 'price_vs_sma20'),
    ('Price vs SMA50 %', 'price_vs_sma50'),
    ('Volatility (20-bar std)', 'volatility_20'),
    ('Volume Ratio', 'volume_ratio'),
    ('24h Return %', 'returns_24h'),
    ('24h Range %', 'range_24h'),
    ('RSI Oversold (7d)', 'rsi_oversold_7d'),
    ('RSI Overbought (7d)', 'rsi_overbought_7d'),
    ('Trend (1=up, -1=down)', 'trend')
]

print("\n                              WINNERS  |  LOSERS  | Difference")
print("                              ---------|----------|------------")

differences = []

for label, metric in metrics:
    winner_avg = winners[metric].mean()
    loser_avg = losers[metric].mean()
    diff = winner_avg - loser_avg
    diff_pct = abs(diff / loser_avg * 100) if loser_avg != 0 else 0

    print(f"{label:30s} {winner_avg:8.2f} | {loser_avg:8.2f} | {diff:+8.2f} ({diff_pct:.0f}%)")

    differences.append({
        'label': label,
        'metric': metric,
        'winner_avg': winner_avg,
        'loser_avg': loser_avg,
        'diff': diff,
        'diff_pct': diff_pct
    })

# Find biggest differentiators
print("\n" + "=" * 80)
print("TOP DIFFERENTIATORS (sorted by % difference):")
print("=" * 80)

differences.sort(key=lambda x: x['diff_pct'], reverse=True)

for i, d in enumerate(differences[:5], 1):
    direction = "HIGHER" if d['diff'] > 0 else "LOWER"
    print(f"\n{i}. {d['label']}:")
    print(f"   Winners: {d['winner_avg']:.2f}")
    print(f"   Losers: {d['loser_avg']:.2f}")
    print(f"   → Winners have {direction} {d['label'].lower()} ({d['diff_pct']:.0f}% difference)")

# Suggest thresholds
print("\n" + "=" * 80)
print("SUGGESTED FILTER THRESHOLDS (to avoid losers):")
print("=" * 80)

print("\nTake trade ONLY when:")

for i, d in enumerate(differences[:5], 1):
    if d['diff'] > 0:
        # Winners have higher values - set minimum threshold
        threshold = (d['winner_avg'] + d['loser_avg']) / 2
        print(f"  {i}. {d['label']} > {threshold:.2f}")
    else:
        # Winners have lower values - set maximum threshold
        threshold = (d['winner_avg'] + d['loser_avg']) / 2
        print(f"  {i}. {d['label']} < {threshold:.2f}")

# Export for further analysis
df_signals.to_csv('signal_characteristics_analysis.csv', index=False)
print(f"\n💾 Saved detailed analysis to: signal_characteristics_analysis.csv")

print("\n" + "=" * 80)
