#!/usr/bin/env python3
"""Test script to verify leverage and position sizing configuration"""

import sys
sys.path.insert(0, '/workspaces/Carebiuro_windykacja/bingx-trading-bot')

from config import load_config

print("=" * 80)
print("LEVERAGE & POSITION SIZING TEST")
print("=" * 80)

# Load config
config = load_config('config.yaml')

print("\n1. BingX Configuration:")
print(f"   Default Leverage: {config.bingx.default_leverage}x")
print(f"   Leverage Mode: {config.bingx.leverage_mode}")
print(f"   Fixed Position Value: ${config.bingx.fixed_position_value_usdt} USDT")

print("\n2. Position Sizing Example:")
balance = 12.0  # USDT
leverage = config.bingx.default_leverage
fixed_value = config.bingx.fixed_position_value_usdt

print(f"   Account Balance: ${balance} USDT")
print(f"   Leverage: {leverage}x")

if fixed_value > 0:
    print(f"\n   ✅ FIXED VALUE MODE")
    print(f"   Position Value: ${fixed_value} USDT per trade")
    margin_per_trade = fixed_value / leverage
    print(f"   Margin Required: ${margin_per_trade:.2f} per trade")
    max_positions = balance / margin_per_trade
    print(f"   Max Simultaneous Positions: {int(max_positions)} trades")
else:
    print(f"\n   ⚠️  PERCENTAGE MODE")
    position_value = balance * leverage
    print(f"   Position Value: ${position_value} USDT (100% of equity × {leverage}x)")

print("\n3. Enabled Strategies:")
strategies = config.trading.strategies
enabled_count = 0

for name, strategy_config in strategies.items():
    if hasattr(strategy_config, 'enabled') and strategy_config.enabled:
        enabled_count += 1
        print(f"   ✅ {name}")
        print(f"      → Base risk: {strategy_config.base_risk_pct}%")
        print(f"      → Max positions: {strategy_config.max_positions}")

        if fixed_value > 0:
            margin = fixed_value / leverage
            print(f"      → Position: ${fixed_value} USDT (margin: ${margin:.2f})")

print(f"\n   Total Enabled: {enabled_count} strategies")

print("\n4. Symbols to Trade:")
for symbol in config.trading.symbols:
    print(f"   • {symbol}")

print("\n5. Risk Check:")
if fixed_value > 0 and leverage > 0:
    margin_per_trade = fixed_value / leverage
    max_positions = balance / margin_per_trade
    total_exposure = enabled_count * fixed_value

    print(f"   Max simultaneous positions: {int(max_positions)}")
    print(f"   Enabled strategies: {enabled_count}")
    print(f"   Total exposure (if all trigger): ${total_exposure:.2f} USDT")
    print(f"   Leverage multiplier: {leverage}x")
    print(f"   Total margin used (if all trigger): ${enabled_count * margin_per_trade:.2f} USDT")

    if enabled_count * margin_per_trade > balance:
        print(f"   ⚠️  WARNING: Not enough margin if all strategies trigger simultaneously!")
    else:
        print(f"   ✅ Sufficient margin for all strategies")

print("\n" + "=" * 80)
print("✅ Configuration Test Complete")
print("=" * 80)
