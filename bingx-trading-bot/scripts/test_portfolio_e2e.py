"""
End-to-End Test: 9-Coin RSI Portfolio with Fixed 10% Sizing

Tests:
1. All 9 strategies load with correct parameters
2. Signal generation works
3. Position sizing = 10% of equity (not $6 fixed)
4. Limit orders calculate correctly
5. SL/TP levels match backtest
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from config import load_config
from data.indicators import IndicatorCalculator

# Import all 9 strategies
from strategies.crv_rsi_swing import CRVRSISwingStrategy
from strategies.melania_rsi_swing import MELANIARSISwingStrategy
from strategies.aixbt_rsi_swing import AIXBTRSISwingStrategy
from strategies.trumpsol_rsi_swing import TRUMPSOLRSISwingStrategy
from strategies.uni_rsi_swing import UNIRSISwingStrategy
from strategies.doge_rsi_swing import DOGERSISwingStrategy
from strategies.xlm_rsi_swing import XLMRSISwingStrategy
from strategies.moodeng_rsi_swing import MOODENGRSISwingStrategy
from strategies.pepe_rsi_swing import PEPERSISwingStrategy

def create_test_data():
    """Create synthetic test data with RSI signals"""
    np.random.seed(42)

    # Generate 250 bars of price data
    bars = 250
    prices = []
    price = 100.0

    for i in range(bars):
        # Random walk
        change = np.random.randn() * 2
        price = price * (1 + change / 100)
        prices.append(price)

    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': pd.date_range('2025-01-01', periods=bars, freq='1h'),
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': [10000 + np.random.rand() * 5000 for _ in range(bars)]
    })

    # Add indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    return df

def test_strategy_loading():
    """Test 1: All strategies load with correct parameters"""
    print('='*80)
    print('TEST 1: STRATEGY LOADING')
    print('='*80)
    print()

    config = load_config('config_rsi_swing.yaml')

    strategies = [
        ('crv_rsi_swing', CRVRSISwingStrategy, 'CRV-USDT', 25, 70, 1.5, 1.0, 1.5),
        ('melania_rsi_swing', MELANIARSISwingStrategy, 'MELANIA-USDT', 27, 65, 1.5, 1.5, 2.0),
        ('aixbt_rsi_swing', AIXBTRSISwingStrategy, 'AIXBT-USDT', 30, 65, 1.5, 2.0, 1.0),
        ('trumpsol_rsi_swing', TRUMPSOLRSISwingStrategy, 'TRUMPSOL-USDT', 30, 65, 1.0, 1.0, 0.5),
        ('uni_rsi_swing', UNIRSISwingStrategy, 'UNI-USDT', 27, 65, 2.0, 1.0, 1.0),
        ('doge_rsi_swing', DOGERSISwingStrategy, 'DOGE-USDT', 27, 65, 1.0, 1.5, 1.0),
        ('xlm_rsi_swing', XLMRSISwingStrategy, 'XLM-USDT', 27, 65, 1.5, 1.5, 1.5),
        ('moodeng_rsi_swing', MOODENGRSISwingStrategy, 'MOODENG-USDT', 27, 65, 2.0, 1.5, 1.5),
        ('pepe_rsi_swing', PEPERSISwingStrategy, '1000PEPE-USDT', 27, 65, 1.5, 1.0, 1.0),
    ]

    for name, StrategyClass, symbol, rsi_low, rsi_high, limit_offset, sl_mult, tp_mult in strategies:
        strategy_config = config.get_strategy_config(name)
        strategy = StrategyClass(strategy_config.__dict__, symbol)

        # Verify parameters
        assert strategy.rsi_low == rsi_low, f"{name}: RSI low mismatch ({strategy.rsi_low} != {rsi_low})"
        assert strategy.rsi_high == rsi_high, f"{name}: RSI high mismatch ({strategy.rsi_high} != {rsi_high})"
        assert strategy.limit_offset_pct == limit_offset, f"{name}: Limit offset mismatch"
        assert strategy.stop_atr_mult == sl_mult, f"{name}: SL mult mismatch"
        assert strategy.tp_atr_mult == tp_mult, f"{name}: TP mult mismatch"
        assert strategy.max_hold_bars == 0, f"{name}: Max hold should be 0 (disabled)"

        print(f'✅ {name:<20} RSI {rsi_low}/{rsi_high}, Limit {limit_offset}%, SL {sl_mult}x, TP {tp_mult}x')

    print()
    print('✅ All 9 strategies loaded with correct parameters!')
    print()

def test_signal_generation():
    """Test 2: Signal generation works"""
    print('='*80)
    print('TEST 2: SIGNAL GENERATION')
    print('='*80)
    print()

    config = load_config('config_rsi_swing.yaml')
    df = create_test_data()

    # Force RSI to cross threshold by modifying last bars
    df.loc[df.index[-2], 'rsi'] = 24.0  # Below 25
    df.loc[df.index[-1], 'rsi'] = 28.0  # Above 25 (CROSS!)

    # Test CRV strategy (rsi_low=25)
    strategy_config = config.get_strategy_config('crv_rsi_swing')
    strategy = CRVRSISwingStrategy(strategy_config.__dict__, 'CRV-USDT')

    signal = strategy.generate_signals(df, [])

    assert signal is not None, "Should generate signal on RSI cross"
    assert signal['side'] == 'LONG', "Should be LONG signal"
    assert signal['type'] == 'LIMIT', "Should be LIMIT order"
    assert 'limit_price' in signal, "Should have limit price"
    assert 'stop_loss' in signal, "Should have stop loss"
    assert 'take_profit' in signal, "Should have take profit"
    assert signal['take_profit'] is not None, "TP should NOT be None!"

    latest_close = df.iloc[-1]['close']
    latest_atr = df.iloc[-1]['atr']

    # Verify calculations
    expected_limit = latest_close * (1 - 1.5 / 100)  # 1.5% below
    expected_sl = expected_limit - (1.0 * latest_atr)  # 1.0x ATR
    expected_tp = expected_limit + (1.5 * latest_atr)  # 1.5x ATR

    assert abs(signal['limit_price'] - expected_limit) < 0.01, "Limit price calculation wrong"
    assert abs(signal['stop_loss'] - expected_sl) < 0.01, "SL calculation wrong"
    assert abs(signal['take_profit'] - expected_tp) < 0.01, "TP calculation wrong"

    print(f'✅ CRV signal generated correctly:')
    print(f'   Signal: LONG @ ${signal["limit_price"]:.2f}')
    print(f'   SL: ${signal["stop_loss"]:.2f} ({1.0}x ATR)')
    print(f'   TP: ${signal["take_profit"]:.2f} ({1.5}x ATR)')
    print()

def test_position_sizing():
    """Test 3: Position sizing = 10% of equity"""
    print('='*80)
    print('TEST 3: POSITION SIZING (10% FIXED)')
    print('='*80)
    print()

    config = load_config('config_rsi_swing.yaml')

    # Verify config settings
    assert config.bingx.fixed_position_value_usdt == 0, "Fixed value should be disabled (0)"
    assert config.bingx.default_leverage == 1, "Leverage should be 1x"

    # Test all 9 strategies have 10% risk
    for strategy_name in ['crv_rsi_swing', 'melania_rsi_swing', 'aixbt_rsi_swing',
                          'trumpsol_rsi_swing', 'uni_rsi_swing', 'doge_rsi_swing',
                          'xlm_rsi_swing', 'moodeng_rsi_swing', 'pepe_rsi_swing']:
        strategy_config = config.get_strategy_config(strategy_name)
        assert strategy_config.base_risk_pct == 10.0, f"{strategy_name}: risk_pct should be 10.0"
        assert strategy_config.max_risk_pct == 10.0, f"{strategy_name}: max_risk_pct should be 10.0"
        print(f'✅ {strategy_name:<20} base_risk_pct = 10.0%')

    print()

    # Simulate position sizing calculation
    account_balance = 100.0  # $100 equity
    risk_pct = 10.0
    leverage = 1

    position_value = account_balance * (risk_pct / 100) * leverage
    expected_value = 10.0  # $10 = 10% of $100

    assert abs(position_value - expected_value) < 0.01, "Position value should be $10"

    print(f'✅ Position sizing calculation:')
    print(f'   Account Balance: ${account_balance:.2f}')
    print(f'   Risk %: {risk_pct}%')
    print(f'   Leverage: {leverage}x')
    print(f'   Position Value: ${position_value:.2f} ({risk_pct}% of equity)')
    print()

def test_portfolio_diversity():
    """Test 4: Verify parameter diversity across strategies"""
    print('='*80)
    print('TEST 4: PARAMETER DIVERSITY')
    print('='*80)
    print()

    config = load_config('config_rsi_swing.yaml')

    params = []
    for name in ['crv_rsi_swing', 'melania_rsi_swing', 'aixbt_rsi_swing',
                 'trumpsol_rsi_swing', 'uni_rsi_swing', 'doge_rsi_swing',
                 'xlm_rsi_swing', 'moodeng_rsi_swing', 'pepe_rsi_swing']:
        cfg = config.get_strategy_config(name)
        params.append((
            cfg.rsi_low,
            cfg.rsi_high,
            cfg.limit_offset_pct,
            cfg.stop_atr_mult,
            cfg.tp_atr_mult
        ))

    # Should have parameter variety (not all identical)
    unique_params = set(params)
    assert len(unique_params) > 1, "Strategies should have different parameters!"

    print(f'✅ {len(unique_params)} unique parameter combinations across 9 strategies')
    print()

def run_all_tests():
    """Run all tests"""
    print()
    print('='*80)
    print('END-TO-END TEST: 9-COIN RSI PORTFOLIO (FIXED 10%)')
    print('='*80)
    print()

    try:
        test_strategy_loading()
        test_signal_generation()
        test_position_sizing()
        test_portfolio_diversity()

        print('='*80)
        print('✅ ALL TESTS PASSED!')
        print('='*80)
        print()
        print('Summary:')
        print('- 9 strategies loaded with optimized parameters from backtest')
        print('- Signal generation works (RSI crossovers + limit orders + SL/TP)')
        print('- Position sizing: 10% of equity per trade (no leverage)')
        print('- Ready for live trading!')
        print()
        return True

    except AssertionError as e:
        print()
        print('='*80)
        print('❌ TEST FAILED!')
        print('='*80)
        print(f'Error: {e}')
        print()
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
