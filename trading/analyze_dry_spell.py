#!/usr/bin/env python3
"""
Investigate the 28-day dry spell: Oct 29 - Nov 26
Why were there no trades?
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
print("ANALYZING THE 28-DAY DRY SPELL (Oct 29 - Nov 26)")
print("=" * 80)

# Load data
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/fartcoin_60d_bingx.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# Calculate indicators
df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
df['atr_ma'] = df['atr'].rolling(20).mean()
df['atr_ratio'] = df['atr'] / df['atr_ma']
df['ema20'] = calculate_ema(df['close'], 20)
df['distance'] = abs((df['close'] - df['ema20']) / df['ema20'] * 100)
df['bullish'] = df['close'] > df['open']

# Calculate daily RSI
df_daily = df.set_index('timestamp').resample('1D').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

df_daily['rsi_daily'] = calculate_rsi(df_daily['close'], 14)

df = df.set_index('timestamp')
df = df.join(df_daily[['rsi_daily']], how='left')
df = df.ffill()
df = df.reset_index()

# Filter to dry spell period
dry_spell_start = pd.Timestamp('2025-10-30')
dry_spell_end = pd.Timestamp('2025-11-25')

df_gap = df[(df['timestamp'] >= dry_spell_start) & (df['timestamp'] <= dry_spell_end)].copy()

print(f"\nPeriod: {dry_spell_start.date()} to {dry_spell_end.date()}")
print(f"Days: {(dry_spell_end - dry_spell_start).days}")
print(f"Candles: {len(df_gap):,}")

# Count signals during this period
print("\n" + "=" * 80)
print("SIGNAL ANALYSIS DURING DRY SPELL")
print("=" * 80)

# All LONG signals (before RSI filter)
all_signals_gap = []
for i in range(len(df_gap)):
    idx = df_gap.index[i]
    row = df.loc[idx]

    if (row['atr_ratio'] > 1.5 and
        row['distance'] < 3.0 and
        row['bullish']):
        all_signals_gap.append({
            'timestamp': row['timestamp'],
            'price': row['close'],
            'daily_rsi': row['rsi_daily'],
            'atr_ratio': row['atr_ratio']
        })

print(f"\nTotal LONG signals (before RSI filter): {len(all_signals_gap)}")

# How many would pass RSI filter?
rsi_passed = [s for s in all_signals_gap if not pd.isna(s['daily_rsi']) and s['daily_rsi'] > 50]
print(f"Signals with RSI > 50: {len(rsi_passed)}")
print(f"Signals blocked by RSI: {len(all_signals_gap) - len(rsi_passed)}")

if len(rsi_passed) > 0:
    print(f"\n⚠️ There WERE {len(rsi_passed)} signals with RSI > 50 that didn't fill!")
    print("\nWhy didn't they fill? (limit orders 1% away)")
else:
    print(f"\n✅ Zero signals with RSI > 50 - filter working as designed")

# Daily RSI stats during gap
print("\n" + "=" * 80)
print("DAILY RSI DURING DRY SPELL")
print("=" * 80)

df_daily_gap = df_daily[(df_daily.index >= dry_spell_start) & (df_daily.index <= dry_spell_end)]

print(f"\nDaily RSI stats:")
print(f"  Average: {df_daily_gap['rsi_daily'].mean():.1f}")
print(f"  Median: {df_daily_gap['rsi_daily'].median():.1f}")
print(f"  Min: {df_daily_gap['rsi_daily'].min():.1f}")
print(f"  Max: {df_daily_gap['rsi_daily'].max():.1f}")

print(f"\nDays with RSI > 50: {(df_daily_gap['rsi_daily'] > 50).sum()} / {len(df_daily_gap)} days")
print(f"Days with RSI < 50: {(df_daily_gap['rsi_daily'] <= 50).sum()} / {len(df_daily_gap)} days")

# Show daily RSI timeline
print(f"\n" + "=" * 80)
print("DAILY RSI TIMELINE")
print("=" * 80)

print(f"\n{'Date':<12} {'Daily RSI':<12} {'Status'}")
print("-" * 40)

for date, row in df_daily_gap.iterrows():
    status = "✅ PASS" if row['rsi_daily'] > 50 else "❌ BLOCKED"
    print(f"{date.date():<12} {row['rsi_daily']:>8.1f}     {status}")

# Price action during gap
print(f"\n" + "=" * 80)
print("PRICE ACTION DURING DRY SPELL")
print("=" * 80)

gap_start_price = df_gap['close'].iloc[0]
gap_end_price = df_gap['close'].iloc[-1]
gap_return = (gap_end_price - gap_start_price) / gap_start_price * 100

print(f"\nStart price: ${gap_start_price:.6f}")
print(f"End price: ${gap_end_price:.6f}")
print(f"Change: {gap_return:+.2f}%")
print(f"\nHigh: ${df_gap['high'].max():.6f}")
print(f"Low: ${df_gap['low'].min():.6f}")
print(f"Range: {(df_gap['high'].max() - df_gap['low'].min()) / gap_start_price * 100:.2f}%")

# Volatility
print(f"\nAvg ATR during gap: {df_gap['atr'].mean():.6f}")
print(f"Avg ATR ratio: {df_gap['atr_ratio'].mean():.2f}x")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

if len(rsi_passed) == 0:
    print(f"""
✅ FILTER WORKING AS DESIGNED

The 28-day gap happened because:
1. Daily RSI stayed below 50 most of the time (bearish momentum)
2. {len(all_signals_gap)} LONG signals generated but ALL blocked by RSI filter
3. Price was {gap_return:+.1f}% during this period (consolidation/downtrend)

This is the filter doing its job - avoiding trading in bearish daily conditions.

Trade-off: You have to wait weeks/months for the right setup.
Benefit: When it fires, conditions are perfect (hence the Nov 26 explosion).
""")
else:
    print(f"""
⚠️ SIGNALS GENERATED BUT DIDN'T FILL

{len(rsi_passed)} signals with RSI > 50 were generated but limit orders didn't fill.
This suggests price was moving slowly (not confirming the breakout).

The filter passed them, but the 1% limit order threshold prevented execution.
""")

print("=" * 80)
