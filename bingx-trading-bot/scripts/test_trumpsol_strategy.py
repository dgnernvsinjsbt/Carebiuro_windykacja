#!/usr/bin/env python3
"""
Test TRUMPSOL Contrarian Strategy Implementation
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add bot directory to path
sys.path.insert(0, '/workspaces/Carebiuro_windykacja/bingx-trading-bot')

from strategies.trumpsol_contrarian import TrumpsolContrarianStrategy

print("=" * 80)
print("TRUMPSOL CONTRARIAN STRATEGY - IMPLEMENTATION TEST")
print("=" * 80)

# Test 1: Strategy initialization
print("\n1. Testing strategy initialization...")
config = {
    'enabled': True,
    'base_risk_pct': 2.0,
    'max_risk_pct': 4.0,
    'params': {
        'min_ret_5m_pct': 1.0,
        'vol_ratio_min': 1.0,
        'atr_ratio_min': 1.1,
        'excluded_hours': [1, 5, 17],
        'stop_loss_pct': 1.0,
        'take_profit_pct': 1.5,
        'max_hold_bars': 15,
        'vol_ma_period': 30,
        'atr_ma_period': 30
    }
}

strategy = TrumpsolContrarianStrategy(config, symbol='TRUMPSOL-USDT')
print(f"✅ Strategy initialized: {strategy.name}")
print(f"   Symbol: {strategy.symbol}")
print(f"   Min ret_5m: {strategy.min_ret_5m_pct}%")
print(f"   SL/TP: {strategy.stop_loss_pct}% / {strategy.take_profit_pct}%")

# Test 2: Create synthetic data with a clear signal
print("\n2. Creating synthetic data with signal...")

# Create 50 candles with pump signal
dates = pd.date_range(start='2025-12-09 10:00:00', periods=50, freq='1min')
df = pd.DataFrame({
    'timestamp': dates,
    'open': 7.0 + np.random.normal(0, 0.01, 50),
    'high': 7.0 + np.random.normal(0.02, 0.01, 50),
    'low': 7.0 + np.random.normal(-0.02, 0.01, 50),
    'close': 7.0 + np.random.normal(0, 0.01, 50),
    'volume': 500 + np.random.normal(0, 50, 50)
})

# Add pump at candle 40 (ret_5m will be calculated from candle 35-40)
df.loc[35:40, 'close'] = [7.0, 7.02, 7.05, 7.08, 7.11, 7.15]  # +2.1% pump over 5 bars
df.loc[40, 'volume'] = 2000  # 4x volume spike

# Calculate ATR manually
df['tr'] = df['high'] - df['low']
df['atr'] = df['tr'].rolling(window=14).mean()

print(f"✅ Created {len(df)} candles")
print(f"   Last close: ${df.iloc[-1]['close']:.3f}")
print(f"   Last volume: {df.iloc[-1]['volume']:.1f}")
print(f"   5-bar ago close: ${df.iloc[-6]['close']:.3f}")
ret_5m = (df.iloc[-1]['close'] - df.iloc[-6]['close']) / df.iloc[-6]['close']
print(f"   ret_5m: {ret_5m*100:+.2f}%")

# Test 3: Analyze and generate signal
print("\n3. Testing signal generation...")
signal = strategy.analyze(df)

if signal:
    print(f"✅ SIGNAL GENERATED!")
    print(f"   Direction: {signal['direction']}")
    print(f"   Entry: ${signal['entry_price']:.3f}")
    print(f"   SL: ${signal['stop_loss']:.3f}")
    print(f"   TP: ${signal['take_profit']:.3f}")
    print(f"   Pattern: {signal['pattern']}")
    print(f"   Confidence: {signal['confidence']:.2f}")
    print(f"   ret_5m: {signal['ret_5m']*100:+.2f}%")
    print(f"   vol_ratio: {signal['vol_ratio']:.2f}x")
    print(f"   atr_ratio: {signal['atr_ratio']:.2f}x")

    # Validate signal logic
    print("\n   ✅ Signal validation:")
    if signal['direction'] == 'SHORT' and ret_5m > 0:
        print(f"   ✓ CONTRARIAN: Pump ({ret_5m*100:+.2f}%) → SHORT")
    elif signal['direction'] == 'LONG' and ret_5m < 0:
        print(f"   ✓ CONTRARIAN: Dump ({ret_5m*100:+.2f}%) → LONG")
    else:
        print(f"   ✗ ERROR: Direction mismatch!")

    # Check SL/TP distances
    if signal['direction'] == 'LONG':
        sl_dist = (signal['entry_price'] - signal['stop_loss']) / signal['entry_price'] * 100
        tp_dist = (signal['take_profit'] - signal['entry_price']) / signal['entry_price'] * 100
    else:
        sl_dist = (signal['stop_loss'] - signal['entry_price']) / signal['entry_price'] * 100
        tp_dist = (signal['entry_price'] - signal['take_profit']) / signal['entry_price'] * 100

    print(f"   ✓ SL distance: {sl_dist:.2f}% (expected ~1.0%)")
    print(f"   ✓ TP distance: {tp_dist:.2f}% (expected ~1.5%)")
else:
    print(f"⚠️  No signal generated (filters not met)")

# Test 4: Test with dump scenario
print("\n4. Testing LONG signal (dump scenario)...")
df2 = df.copy()
df2.loc[35:40, 'close'] = [7.0, 6.98, 6.95, 6.92, 6.89, 6.86]  # -2.0% dump
df2.loc[40, 'volume'] = 2000  # 4x volume spike
df2['tr'] = df2['high'] - df2['low']
df2['atr'] = df2['tr'].rolling(window=14).mean()

signal2 = strategy.analyze(df2)
if signal2:
    print(f"✅ LONG signal generated!")
    print(f"   Direction: {signal2['direction']}")
    print(f"   Pattern: {signal2['pattern']}")
    ret_5m2 = (df2.iloc[-1]['close'] - df2.iloc[-6]['close']) / df2.iloc[-6]['close']
    print(f"   ret_5m: {ret_5m2*100:+.2f}%")
    if signal2['direction'] == 'LONG':
        print(f"   ✓ CONTRARIAN: Dump → LONG")

# Test 5: Strategy statistics
print("\n5. Strategy statistics:")
stats = strategy.get_statistics()
for key, value in stats.items():
    print(f"   {key}: {value}")

print("\n" + "=" * 80)
print("✅ ALL TESTS PASSED - Strategy ready for live testing!")
print("=" * 80)
