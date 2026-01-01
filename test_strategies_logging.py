#!/usr/bin/env python3
"""Test all 4 SHORT reversal strategies with logging"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import logging

# Setup path
sys.path.insert(0, str(Path('bingx-trading-bot').resolve()))

# Setup logging to see output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from strategies.fartcoin_short_reversal import FartcoinShortReversal
from strategies.moodeng_short_reversal import MoodengShortReversal
from strategies.melania_short_reversal import MelaniaShortReversal
from strategies.doge_short_reversal import DogeShortReversal

print("="*80)
print("TESTING 4 SHORT REVERSAL STRATEGIES - LOGGING VERIFICATION")
print("="*80)

# Dummy config
config = {
    'base_risk_pct': 5.0,
    'max_risk_pct': 5.0,
    'max_positions': 1
}

# Create test data with RSI spike and support break
print("\n📊 Creating test data with RSI spike scenario...")
data = []
base_price = 1.2000
for i in range(50):
    # Normal market first 40 candles
    if i < 40:
        rsi = 55 + np.random.randn() * 5
        price = base_price + np.random.randn() * 0.01
    # RSI spike at candle 40
    elif i == 40:
        rsi = 75.0  # RSI > 70 - triggers ARM
        price = base_price + 0.02
    # Price consolidation then support break
    elif i < 45:
        rsi = 68.0
        price = base_price - 0.005 * (i - 40)  # Gradual decline
    else:
        rsi = 65.0
        price = base_price - 0.05  # Break below support

    data.append({
        'timestamp': pd.Timestamp('2025-12-16') + pd.Timedelta(minutes=15*i),
        'open': price,
        'high': price + 0.005,
        'low': price - 0.005,
        'close': price,
        'volume': 1000000
    })

df = pd.DataFrame(data)

# Calculate RSI manually
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# Calculate ATR
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()

print(f"✅ Created {len(df)} candles")
print(f"   RSI range: {df['rsi'].min():.2f} - {df['rsi'].max():.2f}")
print(f"   Price range: ${df['low'].min():.4f} - ${df['high'].max():.4f}")

# Test all 4 strategies
strategies = [
    ('FARTCOIN', FartcoinShortReversal(config, 'FARTCOIN-USDT')),
    ('MOODENG', MoodengShortReversal(config, 'MOODENG-USDT')),
    ('MELANIA', MelaniaShortReversal(config, 'MELANIA-USDT')),
    ('DOGE', DogeShortReversal(config, 'DOGE-USDT'))
]

print("\n" + "="*80)
print("TESTING STRATEGIES - WATCH FOR DETAILED LOGGING")
print("="*80)

for name, strategy in strategies:
    print(f"\n{'='*80}")
    print(f"Testing {name} Strategy")
    print(f"{'='*80}")

    try:
        # Simulate multiple polls
        for i in [35, 40, 42, 45, 47, 49]:  # Key candles
            test_df = df.iloc[:i+1].copy()
            signal = strategy.generate_signals(test_df, [])

            if signal:
                print(f"\n🎯 SIGNAL GENERATED at candle {i}:")
                print(f"   Type: {signal.get('type')}")
                print(f"   Side: {signal.get('side')}")
                print(f"   Limit Price: ${signal.get('limit_price', 0):.4f}")
                print(f"   Stop Loss: ${signal.get('stop_loss', 0):.4f}")
                print(f"   Take Profit: ${signal.get('take_profit', 0):.4f}")

        print(f"\n✅ {name} strategy test completed successfully")

    except Exception as e:
        print(f"\n❌ {name} strategy error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*80)
print("✅ ALL STRATEGY TESTS COMPLETED")
print("="*80)
print("\n📝 Check the logs above to verify:")
print("   1. Every poll shows state (IDLE/ARMED/PENDING)")
print("   2. RSI spike triggers ARMED state")
print("   3. Support break triggers limit order placement")
print("   4. All calculations are logged with details")
print("\nIf you see detailed [COIN] messages above, logging is working! 🎉")
