"""
Test RSI Calculation - Verify Bug

Shows that current bot RSI (SMA-based) differs from correct Wilder's RSI (EMA-based)
"""

import pandas as pd
import numpy as np


def rsi_buggy(data: pd.Series, period: int = 14) -> pd.Series:
    """Current bot implementation - BUGGY (uses SMA)"""
    delta = data.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()  # ❌ WRONG
    avg_loss = loss.rolling(window=period).mean()  # ❌ WRONG

    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))
    return rsi_values


def rsi_correct(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Correct Wilder's RSI implementation (EMA-based)

    This matches TradingView, BingX, and all standard charting platforms
    """
    delta = data.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Initialize series
    avg_gain = pd.Series(index=data.index, dtype=float)
    avg_loss = pd.Series(index=data.index, dtype=float)

    # First value: SMA of first 'period' values
    avg_gain.iloc[period] = gain.iloc[1:period+1].mean()
    avg_loss.iloc[period] = loss.iloc[1:period+1].mean()

    # Subsequent values: Wilder's smoothing (EMA with alpha=1/period)
    for i in range(period + 1, len(data)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))

    return rsi_values


# Create test data that shows the difference
print("=" * 80)
print("RSI CALCULATION BUG DEMONSTRATION")
print("=" * 80)

# Generate sample price data
np.random.seed(42)
prices = 100 + np.cumsum(np.random.randn(100) * 2)
df = pd.DataFrame({'close': prices})

# Calculate both versions
df['rsi_buggy'] = rsi_buggy(df['close'], 14)
df['rsi_correct'] = rsi_correct(df['close'], 14)
df['diff'] = df['rsi_correct'] - df['rsi_buggy']

# Show last 20 values
print("\nLast 20 candles:")
print(f"{'Index':<8} {'Price':<12} {'RSI (Buggy)':<15} {'RSI (Correct)':<15} {'Difference':<12}")
print("-" * 80)

for idx in range(80, 100):
    row = df.iloc[idx]
    if not pd.isna(row['rsi_buggy']) and not pd.isna(row['rsi_correct']):
        print(f"{idx:<8} ${row['close']:<11.2f} {row['rsi_buggy']:<15.2f} "
              f"{row['rsi_correct']:<15.2f} {row['diff']:<+12.2f}")

# Statistics
df_valid = df[df['rsi_buggy'].notna() & df['rsi_correct'].notna()]
print("\n" + "=" * 80)
print("STATISTICS")
print("=" * 80)
print(f"Mean absolute difference: {abs(df_valid['diff']).mean():.2f}")
print(f"Max difference: {df_valid['diff'].max():.2f}")
print(f"Min difference: {df_valid['diff'].min():.2f}")
print(f"Std deviation of difference: {df_valid['diff'].std():.2f}")

# Show example of false signal
print("\n" + "=" * 80)
print("EXAMPLE: How this causes FALSE SIGNALS")
print("=" * 80)

# Look for crossovers
for i in range(15, len(df)):
    curr = df.iloc[i]
    prev = df.iloc[i-1]

    # Check if buggy version shows signal but correct doesn't
    buggy_cross_65 = prev['rsi_buggy'] >= 65 and curr['rsi_buggy'] < 65
    correct_cross_65 = prev['rsi_correct'] >= 65 and curr['rsi_correct'] < 65

    if buggy_cross_65 and not correct_cross_65:
        print(f"\n❌ FALSE SHORT SIGNAL at index {i}:")
        print(f"   Buggy RSI: {prev['rsi_buggy']:.2f} → {curr['rsi_buggy']:.2f} (crosses below 65)")
        print(f"   Correct RSI: {prev['rsi_correct']:.2f} → {curr['rsi_correct']:.2f} (NO cross)")
        print(f"   Price: ${prev['close']:.2f} → ${curr['close']:.2f}")
        break

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("✅ The bug is CONFIRMED:")
print("   - Bot uses SMA-based RSI (simple rolling average)")
print("   - Standard RSI uses EMA-based (Wilder's smoothing)")
print("   - This causes different RSI values")
print("   - Which causes false signals!")
print("\n✅ FIX: Replace rolling().mean() with Wilder's smoothing in indicators.py")
print("=" * 80)
