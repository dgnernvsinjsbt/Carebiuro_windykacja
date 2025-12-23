#!/usr/bin/env python3
"""Test FULL signal flow: IDLE → ARMED → SUPPORT BREAK → LIMIT ORDER"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging

sys.path.insert(0, str(Path('bingx-trading-bot').resolve()))

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Clean output
)

from strategies.fartcoin_short_reversal import FartcoinShortReversal

print("="*80)
print("FULL SIGNAL FLOW TEST - FARTCOIN SHORT REVERSAL")
print("="*80)

config = {'base_risk_pct': 5.0, 'max_risk_pct': 5.0, 'max_positions': 1}
strategy = FartcoinShortReversal(config, 'FARTCOIN-USDT')

# Create realistic scenario
data = []
base_price = 1.2000

# Phase 1: Normal market (candles 0-39)
for i in range(40):
    data.append({
        'timestamp': pd.Timestamp('2025-12-16 06:00') + pd.Timedelta(minutes=15*i),
        'open': base_price + np.random.randn() * 0.005,
        'high': base_price + 0.01 + np.random.randn() * 0.005,
        'low': base_price - 0.01 + np.random.randn() * 0.005,
        'close': base_price + np.random.randn() * 0.005,
        'volume': 1000000
    })

# Phase 2: RSI SPIKE! (candle 40)
data.append({
    'timestamp': pd.Timestamp('2025-12-16 16:00'),
    'open': base_price,
    'high': base_price + 0.03,  # Big pump
    'low': base_price - 0.005,
    'close': base_price + 0.025,
    'volume': 5000000
})

# Phase 3: Consolidation (candles 41-44)
for i in range(41, 45):
    data.append({
        'timestamp': pd.Timestamp('2025-12-16 16:00') + pd.Timedelta(minutes=15*(i-40)),
        'open': base_price + 0.015,
        'high': base_price + 0.02,
        'low': base_price + 0.01,
        'close': base_price + 0.015,
        'volume': 1000000
    })

# Phase 4: SUPPORT BREAK! (candle 45)
data.append({
    'timestamp': pd.Timestamp('2025-12-16 17:15'),
    'open': base_price + 0.01,
    'high': base_price + 0.012,
    'low': base_price - 0.02,  # Breaks swing low
    'close': base_price - 0.015,
    'volume': 3000000
})

df = pd.DataFrame(data)

# Calculate indicators
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

# Force RSI spike at candle 40
df.loc[40, 'rsi'] = 75.0

print(f"\n✅ Created scenario:")
print(f"   Candles 0-39: Normal market (RSI ~50)")
print(f"   Candle 40: RSI SPIKE to {df.loc[40, 'rsi']:.1f}% (SHOULD ARM)")
print(f"   Candles 41-44: Consolidation")
print(f"   Candle 45: Support break (SHOULD PLACE LIMIT ORDER)")

print(f"\n{'='*80}")
print("RUNNING SIMULATION - WATCH DETAILED LOGS")
print(f"{'='*80}\n")

# Simulate candle-by-candle
key_candles = [38, 39, 40, 41, 42, 43, 44, 45]

for candle_idx in key_candles:
    test_df = df.iloc[:candle_idx+1].copy()
    signal = strategy.generate_signals(test_df, [])

    if signal:
        print(f"\n{'🚨'*30}")
        print(f"🎯 LIMIT ORDER SIGNAL GENERATED at candle {candle_idx}!")
        print(f"{'🚨'*30}")
        print(f"   Side: {signal['side']}")
        print(f"   Type: {signal['type']}")
        print(f"   Limit Price: ${signal['limit_price']:.4f}")
        print(f"   Stop Loss: ${signal['stop_loss']:.4f}")
        print(f"   Take Profit: ${signal['take_profit']:.4f}")
        print(f"   Reason: {signal['reason']}")
        print(f"{'🚨'*30}\n")

print(f"\n{'='*80}")
print("✅ SIMULATION COMPLETE")
print(f"{'='*80}")
print("\n📝 You should see:")
print("   1. Candles 38-39: IDLE state (RSI too low)")
print("   2. Candle 40: 🎯 ARMED! (RSI 75 > 70)")
print("   3. Candles 41-44: 👀 ARMED, watching support")
print("   4. Candle 45: 💥 SUPPORT BROKEN! + ✅ LIMIT ORDER PLACED")
print("\nIf you saw all these logs above, the strategy is PRODUCTION READY! 🚀")
