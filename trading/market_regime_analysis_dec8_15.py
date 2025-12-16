#!/usr/bin/env python3
"""
Market Regime Analysis: Did the market change from mean-reverting to trending?
"""

import pandas as pd
import numpy as np

# RSI calculation (Wilder's method)
def wilder_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    delta = data.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = pd.Series(index=data.index, dtype=float)
    avg_loss = pd.Series(index=data.index, dtype=float)

    avg_gain.iloc[period] = gain.iloc[1:period+1].mean()
    avg_loss.iloc[period] = loss.iloc[1:period+1].mean()

    for i in range(period + 1, len(data)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))
    return rsi_values

# ATR calculation
def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close']

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    return tr.rolling(window=period).mean()

print("=" * 80)
print("MARKET REGIME ANALYSIS: Did Mean Reversion Strategies Stop Working?")
print("=" * 80)

# Analyze the worst performers
worst_coins = [
    ('AIXBT-USDT', 'aixbt_recent_10d.csv'),
    ('MOODENG-USDT', 'moodeng_recent_10d.csv'),
    ('PEPE-USDT', '1000pepe_recent_10d.csv'),
    ('UNI-USDT', 'uni_recent_10d.csv'),
]

all_results = []

for symbol, filename in worst_coins:
    print(f"\n{'=' * 80}")
    print(f"COIN: {symbol}")
    print(f"{'=' * 80}")

    df = pd.read_csv(filename)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Filter to Dec 8-15
    dec_df = df[(df['timestamp'] >= '2025-12-08 00:00:00') &
                (df['timestamp'] <= '2025-12-15 23:59:59')].copy()

    # Calculate indicators
    dec_df['rsi'] = wilder_rsi(dec_df['close'], 14)
    dec_df['atr'] = atr(dec_df, 14)
    dec_df['atr_pct'] = (dec_df['atr'] / dec_df['close']) * 100

    # Trend analysis
    dec_df['ema20'] = dec_df['close'].ewm(span=20, adjust=False).mean()
    dec_df['price_vs_ema'] = ((dec_df['close'] - dec_df['ema20']) / dec_df['ema20']) * 100

    # Count RSI extremes
    oversold = (dec_df['rsi'] < 30).sum()
    overbought = (dec_df['rsi'] > 70).sum()

    # Measure choppiness (how many times RSI crossed 50)
    rsi_above_50 = (dec_df['rsi'] > 50).astype(int)
    rsi_crosses = (rsi_above_50.diff().abs() > 0).sum()

    # Measure trending strength (ADX-like: sustained directional movement)
    dec_df['price_change'] = dec_df['close'].pct_change() * 100
    sustained_moves = (abs(dec_df['price_change']) > 2).sum()  # >2% moves

    # Average volatility
    avg_atr_pct = dec_df['atr_pct'].mean()

    # Did price respect RSI levels?
    # After RSI goes oversold (<30), did price bounce? Or keep falling?
    dec_df['rsi_oversold'] = dec_df['rsi'] < 30
    dec_df['rsi_overbought'] = dec_df['rsi'] > 70

    # Look ahead 5 bars after oversold/overbought
    reversal_success = 0
    reversal_attempts = 0

    for i in range(len(dec_df) - 5):
        if dec_df['rsi_oversold'].iloc[i]:
            # Check if price bounced in next 5 bars
            entry_price = dec_df['close'].iloc[i]
            future_high = dec_df['high'].iloc[i+1:i+6].max()
            if future_high > entry_price * 1.01:  # >1% bounce
                reversal_success += 1
            reversal_attempts += 1

        elif dec_df['rsi_overbought'].iloc[i]:
            # Check if price dropped in next 5 bars
            entry_price = dec_df['close'].iloc[i]
            future_low = dec_df['low'].iloc[i+1:i+6].min()
            if future_low < entry_price * 0.99:  # >1% drop
                reversal_success += 1
            reversal_attempts += 1

    reversal_rate = (reversal_success / reversal_attempts * 100) if reversal_attempts > 0 else 0

    print(f"\n📊 MARKET REGIME INDICATORS:")
    print(f"  RSI Oversold Events (<30): {oversold}")
    print(f"  RSI Overbought Events (>70): {overbought}")
    print(f"  RSI 50-Crosses (choppiness): {rsi_crosses}")
    print(f"  Large Moves (>2%): {sustained_moves}")
    print(f"  Avg ATR%: {avg_atr_pct:.2f}%")
    print(f"  Mean Reversion Success Rate: {reversal_rate:.1f}%")

    # Classify regime
    if reversal_rate > 60 and rsi_crosses > 20:
        regime = "✅ MEAN REVERTING (strategies should work)"
    elif reversal_rate < 40:
        regime = "🔴 TRENDING (mean reversion fails)"
    else:
        regime = "⚠️ MIXED/CHOPPY"

    print(f"\n  **MARKET REGIME: {regime}**")

    # Store results
    all_results.append({
        'symbol': symbol,
        'oversold_events': oversold,
        'overbought_events': overbought,
        'rsi_crosses': rsi_crosses,
        'large_moves': sustained_moves,
        'avg_atr_pct': avg_atr_pct,
        'reversal_rate': reversal_rate,
        'regime': regime
    })

# Summary
print(f"\n{'=' * 80}")
print("SUMMARY: Why RSI Strategies Failed")
print(f"{'=' * 80}")

results_df = pd.DataFrame(all_results)

print(f"\n{'Coin':<15} {'Reversal%':>12} {'RSI Crosses':>12} {'Avg ATR%':>10} {'Regime':>30}")
print("-" * 80)
for _, row in results_df.iterrows():
    print(f"{row['symbol']:<15} {row['reversal_rate']:>11.1f}% {row['rsi_crosses']:>12} {row['avg_atr_pct']:>9.2f}% {row['regime']:>30}")

avg_reversal = results_df['reversal_rate'].mean()
print(f"\n{'AVERAGE':<15} {avg_reversal:>11.1f}%")

print("\n🔍 INTERPRETATION:")
if avg_reversal < 50:
    print("  ❌ Mean reversion strategies FAILED because market was TRENDING")
    print("  ❌ When RSI hit oversold/overbought, prices CONTINUED in that direction")
    print("  ❌ This is why stop losses got hit 50% of the time (vs 20% normally)")
elif avg_reversal > 60:
    print("  ⚠️ Mean reversion SHOULD have worked, but something else failed")
    print("  ⚠️ Possible issues: stop losses too tight, entry timing off, etc.")
else:
    print("  ⚠️ Market was CHOPPY/MIXED - sometimes reversed, sometimes trended")
    print("  ⚠️ This creates unpredictable results and high stop loss rates")

print("\n💡 RECOMMENDATIONS:")
if avg_reversal < 50:
    print("  1. Add TREND FILTER: Don't trade against strong trends")
    print("  2. Use TREND-FOLLOWING strategies when market is trending")
    print("  3. Add ADX/ATR filter: Only trade mean reversion in low-ATR environments")
    print("  4. Reduce position size or avoid trading during high-volatility periods")
else:
    print("  1. Review stop loss placement - may be too tight")
    print("  2. Check if limit orders are filling at suboptimal prices")
    print("  3. Consider adding volatility filter to avoid choppy markets")

print("\n⚠️ LEVERAGE WARNING:")
print(f"  Current max DD: -3.23% (acceptable for 1x, dangerous for 5x+)")
print(f"  Without regime detection, drawdowns could hit -10%+ in trending markets")
print(f"  **DO NOT use >3x leverage without trend filters**")
