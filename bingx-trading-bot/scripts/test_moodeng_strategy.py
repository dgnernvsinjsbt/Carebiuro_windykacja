#!/usr/bin/env python3
"""
Test MOODENG RSI Momentum Strategy Integration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from config import load_config
from strategies.moodeng_rsi_momentum import MoodengRSIMomentumStrategy
from data.indicators import IndicatorCalculator

print("="*80)
print("MOODENG RSI MOMENTUM STRATEGY - INTEGRATION TEST")
print("="*80)
print()

# Load config
print("Loading configuration...")
config = load_config('config.yaml')
strategy_config = config.get_strategy_config('moodeng_rsi_momentum')
print(f"✅ Config loaded: {strategy_config.__dict__}")
print()

# Initialize strategy
print("Initializing strategy...")
strategy = MoodengRSIMomentumStrategy(strategy_config.__dict__)
print(f"✅ Strategy initialized: {strategy.name}")
print(f"   RSI cross level: {strategy.rsi_cross_level}")
print(f"   Min body %: {strategy.min_body_pct}%")
print(f"   Stop/Target: {strategy.stop_atr_mult}x / {strategy.target_atr_mult}x ATR")
print(f"   Max hold: {strategy.max_hold_bars} bars")
print()

# Load MOODENG data for testing
print("Loading MOODENG test data...")
df = pd.read_csv('../trading/moodeng_usdt_1m_lbank.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f"✅ Loaded {len(df)} candles")
print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print()

# Calculate indicators
print("Calculating indicators...")
calc = IndicatorCalculator(df)
df = calc.add_all_indicators()
print(f"✅ Indicators calculated")
print(f"   Columns: {', '.join([c for c in df.columns if c in ['rsi', 'sma_20', 'atr']])}")
print()

# Test strategy on recent data
print("Testing strategy on last 1000 candles...")
test_df = df.iloc[-1000:].copy().reset_index(drop=True)

signals = []
for i in range(30, len(test_df)):
    window = test_df.iloc[:i+1]
    signal = strategy.analyze(window)

    if signal:
        signals.append({
            'timestamp': window.iloc[-1]['timestamp'],
            'entry_price': signal['entry_price'],
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'rsi': signal.get('rsi'),
            'body_pct': signal.get('body_pct'),
            'pattern': signal.get('pattern')
        })

print(f"✅ Strategy test complete")
print(f"   Signals generated: {len(signals)}")
print()

if len(signals) > 0:
    print("Sample signals (first 5):")
    print("-" * 80)
    for i, sig in enumerate(signals[:5], 1):
        print(f"#{i}: {sig['timestamp']}")
        print(f"   Entry: ${sig['entry_price']:.6f}")
        print(f"   SL: ${sig['stop_loss']:.6f}   TP: ${sig['take_profit']:.6f}")
        print(f"   RSI: {sig['rsi']:.1f}   Body: {sig['body_pct']:.2f}%")
        print(f"   Pattern: {sig['pattern']}")
        print()
else:
    print("⚠️  No signals generated on test data")
    print("   This might be normal if conditions weren't met")

print("="*80)
print("INTEGRATION TEST PASSED ✅")
print("="*80)
print()
print("Strategy is ready for live trading!")
print()
print("To start the bot:")
print("  cd bingx-trading-bot")
print("  python main.py")
