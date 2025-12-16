#!/usr/bin/env python3
"""Compare RSI values at same timestamps between LBank and BingX"""
import pandas as pd
import numpy as np

# Load LBank data
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

    return df

lbank = calc_rsi(lbank)
bingx = calc_rsi(bingx)

# Find BingX signals
bingx_signals = []
for i in range(1, len(bingx)):
    if pd.isna(bingx.iloc[i-1]['rsi']) or pd.isna(bingx.iloc[i]['rsi']):
        continue

    if bingx.iloc[i-1]['rsi'] > 65 and bingx.iloc[i]['rsi'] <= 65:
        bingx_signals.append({
            'timestamp': bingx.iloc[i]['timestamp'],
            'bingx_rsi': bingx.iloc[i]['rsi'],
            'bingx_prev_rsi': bingx.iloc[i-1]['rsi'],
            'bingx_close': bingx.iloc[i]['close']
        })

bingx_signals_df = pd.DataFrame(bingx_signals)

# For each BingX signal, find LBank RSI at exact same time
results = []
for idx, sig in bingx_signals_df.iterrows():
    ts = sig['timestamp']

    # Get LBank data at same timestamp
    lbank_row = lbank[lbank['timestamp'] == ts]

    if len(lbank_row) > 0:
        lbank_rsi = lbank_row['rsi'].values[0]
        lbank_close = lbank_row['close'].values[0]

        # Check if LBank also had signal
        lbank_prev = lbank[lbank['timestamp'] < ts].tail(1)
        lbank_prev_rsi = lbank_prev['rsi'].values[0] if len(lbank_prev) > 0 else None

        had_lbank_signal = False
        if lbank_prev_rsi is not None:
            had_lbank_signal = lbank_prev_rsi > 65 and lbank_rsi <= 65

        results.append({
            'timestamp': ts,
            'bingx_rsi': sig['bingx_rsi'],
            'bingx_prev_rsi': sig['bingx_prev_rsi'],
            'bingx_close': sig['bingx_close'],
            'lbank_rsi': lbank_rsi,
            'lbank_prev_rsi': lbank_prev_rsi,
            'lbank_close': lbank_close,
            'rsi_diff': abs(sig['bingx_rsi'] - lbank_rsi),
            'price_diff_pct': abs(sig['bingx_close'] - lbank_close) / lbank_close * 100,
            'had_lbank_signal': had_lbank_signal
        })

results_df = pd.DataFrame(results)

# Split into signals that appeared on both vs BingX-only
both = results_df[results_df['had_lbank_signal']]
bingx_only = results_df[~results_df['had_lbank_signal']]

print("=" * 80)
print("WHY BINGX-ONLY SIGNALS DIDN'T TRIGGER ON LBANK")
print("=" * 80)

print(f"\nTotal BingX signals with LBank data: {len(results_df)}")
print(f"Appeared on both: {len(both)}")
print(f"BingX-only: {len(bingx_only)}")

print("\n" + "=" * 80)
print("RSI COMPARISON AT SAME TIMESTAMP")
print("=" * 80)

print(f"\nSignals on BOTH exchanges:")
print(f"  BingX RSI: {both['bingx_rsi'].mean():.2f} (prev: {both['bingx_prev_rsi'].mean():.2f})")
print(f"  LBank RSI: {both['lbank_rsi'].mean():.2f} (prev: {both['lbank_prev_rsi'].mean():.2f})")
print(f"  RSI difference: {both['rsi_diff'].mean():.2f} points")

print(f"\nBingX-ONLY signals:")
print(f"  BingX RSI: {bingx_only['bingx_rsi'].mean():.2f} (prev: {bingx_only['bingx_prev_rsi'].mean():.2f})")
print(f"  LBank RSI at same time: {bingx_only['lbank_rsi'].mean():.2f} (prev: {bingx_only['lbank_prev_rsi'].mean():.2f})")
print(f"  RSI difference: {bingx_only['rsi_diff'].mean():.2f} points")

print("\n" + "=" * 80)
print("WHY NO LBANK SIGNAL?")
print("=" * 80)

# Analyze why LBank didn't signal
lbank_stayed_above = bingx_only[bingx_only['lbank_rsi'] > 65]
lbank_was_below = bingx_only[bingx_only['lbank_rsi'] <= 65]

print(f"\nLBank RSI stayed ABOVE 65: {len(lbank_stayed_above)} ({len(lbank_stayed_above)/len(bingx_only)*100:.1f}%)")
print(f"  Avg LBank RSI: {lbank_stayed_above['lbank_rsi'].mean():.2f}")
print(f"  Avg BingX RSI: {lbank_stayed_above['bingx_rsi'].mean():.2f}")
print(f"  → BingX crossed but LBank didn't")

print(f"\nLBank RSI already BELOW 65: {len(lbank_was_below)} ({len(lbank_was_below)/len(bingx_only)*100:.1f}%)")
print(f"  Avg LBank RSI: {lbank_was_below['lbank_rsi'].mean():.2f}")
print(f"  Avg LBank prev RSI: {lbank_was_below['lbank_prev_rsi'].mean():.2f}")
print(f"  → LBank crossed earlier or never was overbought")

print("\n" + "=" * 80)
print("PRICE DIVERGENCE")
print("=" * 80)

print(f"\nBoth exchanges:")
print(f"  Price difference: {both['price_diff_pct'].mean():.3f}%")

print(f"\nBingX-only:")
print(f"  Price difference: {bingx_only['price_diff_pct'].mean():.3f}%")

print("\n" + "=" * 80)
print("SAMPLE BINGX-ONLY SIGNALS")
print("=" * 80)

for idx, row in bingx_only.head(10).iterrows():
    print(f"\n{row['timestamp']}")
    print(f"  BingX: RSI {row['bingx_prev_rsi']:.1f} → {row['bingx_rsi']:.1f} (crossed 65)")
    print(f"  LBank: RSI {row['lbank_prev_rsi']:.1f} → {row['lbank_rsi']:.1f} (no cross)")

    if row['lbank_rsi'] > 65:
        print(f"  → LBank stayed overbought")
    elif row['lbank_prev_rsi'] <= 65:
        print(f"  → LBank never was overbought")
    else:
        print(f"  → LBank crossed earlier")

print("\n" + "=" * 80)
print("KEY FINDING")
print("=" * 80)

pct_stayed_above = len(lbank_stayed_above) / len(bingx_only) * 100
pct_was_below = len(lbank_was_below) / len(bingx_only) * 100

print(f"\nBingX-only signals breakdown:")
print(f"  {pct_stayed_above:.1f}% - LBank RSI stayed above 65 (BingX dropped, LBank didn't)")
print(f"  {pct_was_below:.1f}% - LBank RSI already below 65 (different timing)")
print(f"\nAverage RSI difference: {bingx_only['rsi_diff'].mean():.1f} points")
print(f"Average price difference: {bingx_only['price_diff_pct'].mean():.2f}%")

print("\n" + "=" * 80)
