#!/usr/bin/env python3
"""Compare exact RSI signals between LBank and BingX"""
import pandas as pd
import numpy as np
from datetime import datetime

# Load LBank data (monthly files)
lbank_files = [
    'melania_june_2025_15m.csv',
    'melania_july_2025_15m.csv',
    'melania_august_2025_15m.csv',
    'melania_september_2025_15m.csv',
    'melania_october_2025_15m.csv',
    'melania_november_2025_15m.csv',
    'melania_december_2025_15m.csv'
]

lbank_dfs = []
for f in lbank_files:
    try:
        df = pd.read_csv(f)
        lbank_dfs.append(df)
    except:
        pass

lbank = pd.concat(lbank_dfs, ignore_index=True)
lbank['timestamp'] = pd.to_datetime(lbank['timestamp'])
lbank = lbank.sort_values('timestamp').reset_index(drop=True)

# Load BingX data
bingx = pd.read_csv('melania_6months_bingx.csv')
bingx['timestamp'] = pd.to_datetime(bingx['timestamp'])

# Calculate RSI for both
def calc_rsi(df):
    df = df.copy()
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['ret_20'] = (df['close'] / df['close'].shift(20) - 1) * 100

    return df

lbank = calc_rsi(lbank)
bingx = calc_rsi(bingx)

# Find RSI crossover signals (65 level)
def find_signals(df, name):
    signals = []
    for i in range(1, len(df)):
        if pd.isna(df.iloc[i-1]['rsi']) or pd.isna(df.iloc[i]['rsi']):
            continue

        # RSI crosses down through 65
        if df.iloc[i-1]['rsi'] > 65 and df.iloc[i]['rsi'] <= 65:
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'close': df.iloc[i]['close'],
                'rsi': df.iloc[i]['rsi'],
                'prev_rsi': df.iloc[i-1]['rsi'],
                'ret_20': df.iloc[i]['ret_20'],
                'source': name
            })

    return pd.DataFrame(signals)

lbank_signals = find_signals(lbank, 'LBank')
bingx_signals = find_signals(bingx, 'BingX')

print("=" * 80)
print("SIGNAL COUNT COMPARISON")
print("=" * 80)
print(f"\nLBank signals: {len(lbank_signals)}")
print(f"BingX signals: {len(bingx_signals)}")
print(f"Difference: {len(bingx_signals) - len(lbank_signals)} extra on BingX ({(len(bingx_signals)/len(lbank_signals)-1)*100:.1f}% more)")

# Merge on timestamp (within 15 min window for matching)
lbank_signals['ts_key'] = lbank_signals['timestamp'].dt.floor('15min')
bingx_signals['ts_key'] = bingx_signals['timestamp'].dt.floor('15min')

merged = bingx_signals.merge(lbank_signals, on='ts_key', how='left', suffixes=('_bingx', '_lbank'))

both = merged[~merged['rsi_lbank'].isna()]  # Signals on both exchanges
bingx_only = merged[merged['rsi_lbank'].isna()]  # BingX-only signals

print("\n" + "=" * 80)
print("SIGNAL OVERLAP")
print("=" * 80)
print(f"\nSignals on BOTH exchanges: {len(both)}")
print(f"BingX-ONLY signals: {len(bingx_only)} (THE NOISE!)")

print("\n" + "=" * 80)
print("BINGX-ONLY SIGNALS (what makes them different?)")
print("=" * 80)

print(f"\nRSI at signal:")
print(f"  Both exchanges: {both['rsi_bingx'].mean():.2f}")
print(f"  BingX-only: {bingx_only['rsi_bingx'].mean():.2f}")

print(f"\nPrevious RSI:")
print(f"  Both exchanges: {both['prev_rsi_bingx'].mean():.2f}")
print(f"  BingX-only: {bingx_only['prev_rsi_bingx'].mean():.2f}")

print(f"\nMomentum (ret_20):")
print(f"  Both exchanges: {both['ret_20_bingx'].mean():+.2f}%")
print(f"  BingX-only: {bingx_only['ret_20_bingx'].mean():+.2f}%")

# For signals on both, check if RSI values differ
print("\n" + "=" * 80)
print("RSI VALUE DIFFERENCES (same timestamp, both exchanges)")
print("=" * 80)

both['rsi_diff'] = abs(both['rsi_bingx'] - both['rsi_lbank'])
print(f"\nAverage RSI difference: {both['rsi_diff'].mean():.2f} points")
print(f"Max RSI difference: {both['rsi_diff'].max():.2f} points")

# Show sample BingX-only signals
print("\n" + "=" * 80)
print("SAMPLE BINGX-ONLY SIGNALS")
print("=" * 80)

for idx, sig in bingx_only.head(10).iterrows():
    ts = sig['timestamp_bingx']

    # Check what LBank RSI was at same time
    lbank_row = lbank[lbank['timestamp'] == ts]
    lbank_rsi = lbank_row['rsi'].values[0] if len(lbank_row) > 0 else None

    print(f"\n{ts} | BingX RSI: {sig['rsi_bingx']:.1f} | Ret20: {sig['ret_20_bingx']:+.1f}%")
    if lbank_rsi is not None:
        print(f"  LBank RSI at same time: {lbank_rsi:.1f} (no cross!)")
        print(f"  Reason: LBank RSI stayed {'above' if lbank_rsi > 65 else 'below'} 65")

print("\n" + "=" * 80)
print("FILTER RECOMMENDATION")
print("=" * 80)

# Find discriminating threshold
if bingx_only['ret_20_bingx'].mean() < both['ret_20_bingx'].mean():
    threshold = both['ret_20_bingx'].quantile(0.25)
    print(f"\nBingX-only signals have weaker momentum:")
    print(f"  Both: {both['ret_20_bingx'].mean():+.2f}%")
    print(f"  BingX-only: {bingx_only['ret_20_bingx'].mean():+.2f}%")
    print(f"\n✅ Filter: ret_20 >= {threshold:.1f}% (removes most BingX-only noise)")

print("\n" + "=" * 80)
