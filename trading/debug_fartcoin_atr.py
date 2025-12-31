"""
Debug FARTCOIN ATR calculation
"""
import pandas as pd
import numpy as np

# Load FARTCOIN 1H data
df = pd.read_csv('trading/fartcoin_1h_jun_dec_2025.csv', parse_dates=['timestamp'])

# Parameters
PERIOD = 15
TP_ATR = 7.5
SL_ATR = 2.0

# Calculate ATR (simple: high - low average)
df['atr'] = (df['high'] - df['low']).rolling(14).mean()
df['atr_pct'] = df['atr'] / df['close'] * 100

# Calculate Donchian
df['donchian_upper'] = df['high'].rolling(PERIOD).max().shift(1)
df['donchian_lower'] = df['low'].rolling(PERIOD).min().shift(1)

print("="*60)
print("ATR ANALYSIS FOR FARTCOIN")
print("="*60)

print(f"\nATR Statistics:")
print(f"  Min ATR: ${df['atr'].min():.4f} ({df['atr_pct'].min():.2f}%)")
print(f"  Max ATR: ${df['atr'].max():.4f} ({df['atr_pct'].max():.2f}%)")
print(f"  Avg ATR: ${df['atr'].mean():.4f} ({df['atr_pct'].mean():.2f}%)")
print(f"  Median ATR: ${df['atr'].median():.4f}")

# At SL=2xATR, what's the typical SL distance?
print(f"\nAt SL = {SL_ATR}x ATR:")
print(f"  Avg SL distance: {SL_ATR * df['atr_pct'].mean():.2f}%")
print(f"  Min SL distance: {SL_ATR * df['atr_pct'].min():.2f}%")
print(f"  Max SL distance: {SL_ATR * df['atr_pct'].max():.2f}%")

# At TP=7.5xATR, what's the typical TP distance?
print(f"\nAt TP = {TP_ATR}x ATR:")
print(f"  Avg TP distance: {TP_ATR * df['atr_pct'].mean():.2f}%")

# Required win rate to break even
sl_dist = SL_ATR * df['atr_pct'].mean()
tp_dist = TP_ATR * df['atr_pct'].mean()
required_wr = sl_dist / (sl_dist + tp_dist)
print(f"\nRequired Win Rate to Break Even: {required_wr * 100:.1f}%")

# Sample data around first signal
print(f"\n{'='*60}")
print("SAMPLE DATA AROUND FIRST SIGNAL")
print("="*60)

# Find first signal
for i in range(30, 100):
    row = df.iloc[i]
    if row['close'] > row['donchian_upper'] or row['close'] < row['donchian_lower']:
        print(f"\nFirst signal at bar {i}:")
        print(f"  Date: {row['timestamp']}")
        print(f"  Close: ${row['close']:.4f}")
        print(f"  Donchian Upper: ${row['donchian_upper']:.4f}")
        print(f"  Donchian Lower: ${row['donchian_lower']:.4f}")
        print(f"  ATR: ${row['atr']:.4f} ({row['atr'] / row['close'] * 100:.2f}%)")
        
        if row['close'] > row['donchian_upper']:
            signal = 'LONG'
            sl = row['close'] - SL_ATR * row['atr']
            tp = row['close'] + TP_ATR * row['atr']
        else:
            signal = 'SHORT'
            sl = row['close'] + SL_ATR * row['atr']
            tp = row['close'] - TP_ATR * row['atr']
        
        print(f"\n  Signal: {signal}")
        print(f"  Entry: ${row['close']:.4f}")
        print(f"  SL: ${sl:.4f} ({abs(sl - row['close']) / row['close'] * 100:.2f}% away)")
        print(f"  TP: ${tp:.4f} ({abs(tp - row['close']) / row['close'] * 100:.2f}% away)")
        
        # Check next bars
        print(f"\nNext 10 bars:")
        for j in range(1, 11):
            next_row = df.iloc[i + j]
            hit_sl = (signal == 'LONG' and next_row['low'] <= sl) or (signal == 'SHORT' and next_row['high'] >= sl)
            hit_tp = (signal == 'LONG' and next_row['high'] >= tp) or (signal == 'SHORT' and next_row['low'] <= tp)
            status = "SL HIT!" if hit_sl else ("TP HIT!" if hit_tp else "")
            print(f"  Bar {i+j}: O=${next_row['open']:.4f} H=${next_row['high']:.4f} L=${next_row['low']:.4f} C=${next_row['close']:.4f} {status}")
            if hit_sl or hit_tp:
                break
        
        break

# Price volatility check
print(f"\n{'='*60}")
print("PRICE VOLATILITY CHECK")
print("="*60)

# How often does price move more than 2xATR in a single bar?
df['bar_range_pct'] = (df['high'] - df['low']) / df['close'] * 100
print(f"Avg bar range: {df['bar_range_pct'].mean():.2f}%")
print(f"Max bar range: {df['bar_range_pct'].max():.2f}%")
print(f"Bars with range > 5%: {(df['bar_range_pct'] > 5).sum()}")
print(f"Bars with range > 10%: {(df['bar_range_pct'] > 10).sum()}")

# How often does FARTCOIN move 7.5xATR in 24 bars?
# This would be needed for TP hit
print(f"\nTypical move needed for TP: {TP_ATR * df['atr_pct'].mean():.1f}%")
print(f"Typical move needed for SL: {SL_ATR * df['atr_pct'].mean():.1f}%")

