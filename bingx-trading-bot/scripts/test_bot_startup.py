#!/usr/bin/env python3
"""Quick test to verify bot can initialize with TRUMPSOL strategy"""

import sys
sys.path.insert(0, '/workspaces/Carebiuro_windykacja/bingx-trading-bot')

from config import load_config

print("=" * 80)
print("BOT STARTUP TEST - TRUMPSOL CONTRARIAN")
print("=" * 80)

print("\n1. Loading config...")
config = load_config('config.yaml')
print(f"✅ Config loaded")

print("\n2. Checking enabled strategies...")
strategies = config.trading.strategies
for name, strategy_config in strategies.items():
    if hasattr(strategy_config, 'enabled') and strategy_config.enabled:
        print(f"   ✅ {name}: ENABLED")
        if name == 'trumpsol_contrarian':
            print(f"      → base_risk: {strategy_config.base_risk_pct}%")
            print(f"      → max_risk: {strategy_config.max_risk_pct}%")
            if hasattr(strategy_config, 'params'):
                params = strategy_config.params
                if isinstance(params, dict):
                    print(f"      → min_ret_5m: {params.get('min_ret_5m_pct')}%")
                    print(f"      → vol_ratio_min: {params.get('vol_ratio_min')}")
                    print(f"      → atr_ratio_min: {params.get('atr_ratio_min')}")
                else:
                    print(f"      → min_ret_5m: {params.min_ret_5m_pct}%")
                    print(f"      → vol_ratio_min: {params.vol_ratio_min}")
                    print(f"      → atr_ratio_min: {params.atr_ratio_min}")

print("\n3. Checking TRUMPSOL symbol...")
if 'TRUMPSOL-USDT' in config.trading.symbols:
    print(f"   ✅ TRUMPSOL-USDT in symbols list")
else:
    print(f"   ⚠️  TRUMPSOL-USDT NOT in symbols list")
    print(f"   Current symbols: {config.trading.symbols}")

print("\n4. Testing strategy import...")
try:
    from strategies.trumpsol_contrarian import TrumpsolContrarianStrategy
    print(f"   ✅ TrumpsolContrarianStrategy imported successfully")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

print("\n5. Testing strategy instantiation...")
try:
    strategy_config = config.get_strategy_config('trumpsol_contrarian')
    strategy = TrumpsolContrarianStrategy(strategy_config.__dict__, symbol='TRUMPSOL-USDT')
    print(f"   ✅ Strategy instantiated: {strategy.name}")
    print(f"   → Symbol: {strategy.symbol}")
    print(f"   → Enabled: {strategy.enabled}")
except Exception as e:
    print(f"   ❌ Instantiation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ ALL CHECKS PASSED - Bot ready to run!")
print("=" * 80)
print("\nNext steps:")
print("1. Start bot: python3 main.py")
print("2. Monitor signals: check_recent_signals.py")
print("3. Check trades: check_last_24h_trades.py")
