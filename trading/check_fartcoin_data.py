"""
Check FARTCOIN 1H data quality from BingX
"""
import pandas as pd
import numpy as np

# Load FARTCOIN 1H data
df = pd.read_csv('trading/fartcoin_1h_jun_dec_2025.csv', parse_dates=['timestamp'])

print("="*60)
print("FARTCOIN 1H DATA QUALITY CHECK")
print("="*60)

print(f"\n📅 Data Range:")
print(f"   Start: {df['timestamp'].min()}")
print(f"   End: {df['timestamp'].max()}")
print(f"   Total candles: {len(df)}")

# Check for gaps
df_sorted = df.sort_values('timestamp')
time_diff = df_sorted['timestamp'].diff()
expected_diff = pd.Timedelta(hours=1)
gaps = time_diff[time_diff > expected_diff]
print(f"\n🔍 Data Gaps (>1h):")
if len(gaps) > 0:
    print(f"   Found {len(gaps)} gaps")
    for idx in gaps.index[:5]:  # Show first 5
        prev_time = df_sorted.loc[idx-1, 'timestamp'] if idx > 0 else 'N/A'
        curr_time = df_sorted.loc[idx, 'timestamp']
        print(f"   - {prev_time} → {curr_time} (gap: {gaps.loc[idx]})")
else:
    print("   ✅ No gaps found - data is continuous")

print(f"\n💰 Price Statistics:")
print(f"   Min: ${df['low'].min():.4f}")
print(f"   Max: ${df['high'].max():.4f}")
print(f"   Current: ${df['close'].iloc[-1]:.4f}")
print(f"   Range: {((df['high'].max() - df['low'].min()) / df['low'].min() * 100):.1f}%")

print(f"\n📊 Volume Statistics:")
print(f"   Avg volume: {df['volume'].mean():.0f}")
print(f"   Zero volume candles: {(df['volume'] == 0).sum()}")

# Check for invalid data
print(f"\n⚠️ Data Quality:")
print(f"   High < Low (invalid): {(df['high'] < df['low']).sum()}")
print(f"   Close outside H/L: {((df['close'] > df['high']) | (df['close'] < df['low'])).sum()}")
print(f"   Open outside H/L: {((df['open'] > df['high']) | (df['open'] < df['low'])).sum()}")
print(f"   NaN values: {df.isna().sum().sum()}")

# Compare with expected candle count
expected_days = (df['timestamp'].max() - df['timestamp'].min()).days
expected_candles = expected_days * 24
print(f"\n📈 Completeness:")
print(f"   Expected candles: ~{expected_candles}")
print(f"   Actual candles: {len(df)}")
print(f"   Completeness: {len(df) / expected_candles * 100:.1f}%")

