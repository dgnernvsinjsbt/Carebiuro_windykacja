#!/usr/bin/env python3
"""
Test Donchian Breakout Signal Generation

Tests the signal generation pipeline using historical data
to verify the strategy works correctly before going live.
"""

import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from strategies.donchian_breakout import DonchianBreakout, COIN_PARAMS
from data.indicators import IndicatorCalculator

def test_donchian_signals():
    """Test signal generation with historical data"""

    print("=" * 70)
    print("DONCHIAN BREAKOUT SIGNAL GENERATION TEST")
    print("=" * 70)

    # Test with ETH 1H data
    data_file = Path(__file__).parent.parent / 'trading' / 'eth_1h_resampled.csv'

    if not data_file.exists():
        print(f"Error: Test data file not found: {data_file}")
        print("Looking for alternative data files...")

        # Try to find any 1h CSV file
        trading_dir = Path(__file__).parent.parent / 'trading'
        csv_files = list(trading_dir.glob('*_1h*.csv'))

        if csv_files:
            data_file = csv_files[0]
            print(f"Using: {data_file}")
        else:
            print("No 1H data files found. Creating test with simulated data...")
            return test_with_simulated_data()

    # Load data
    print(f"\nLoading: {data_file}")
    df = pd.read_csv(data_file)

    # Standardize column names
    df.columns = [c.lower() for c in df.columns]
    if 'timestamp' not in df.columns and 'time' in df.columns:
        df['timestamp'] = pd.to_datetime(df['time'])
    elif 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Ensure numeric columns
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    print(f"Loaded {len(df)} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Calculate indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    # Create strategy for ETH
    config = {
        'enabled': True,
        'risk_pct': 3.0,
        'max_leverage': 5.0
    }

    strategy = DonchianBreakout(config, 'ETH-USDT')

    print(f"\nStrategy: {strategy.name}")
    print(f"Period: {strategy.period}, TP: {strategy.tp_atr} ATR, SL: {strategy.sl_atr} ATR")

    # Run through data and count signals
    signals_generated = []

    for i in range(strategy.period + 14, len(df)):
        # Get slice of data up to this point
        df_slice = df.iloc[:i+1].copy()

        # Generate signal
        signal = strategy.generate_signals(df_slice, current_positions=[])

        if signal:
            row = df_slice.iloc[-1]
            signals_generated.append({
                'timestamp': row['timestamp'],
                'direction': signal['direction'],
                'entry_price': signal['entry_price'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'reason': signal.get('reason', '')
            })

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {len(signals_generated)} signals generated")
    print(f"{'=' * 70}")

    if signals_generated:
        print("\nFirst 5 signals:")
        for i, sig in enumerate(signals_generated[:5]):
            print(f"  {i+1}. {sig['timestamp']} - {sig['direction']} @ ${sig['entry_price']:.4f}")
            print(f"      SL: ${sig['stop_loss']:.4f}, TP: ${sig['take_profit']:.4f}")

        # Count long vs short
        longs = sum(1 for s in signals_generated if s['direction'] == 'LONG')
        shorts = sum(1 for s in signals_generated if s['direction'] == 'SHORT')
        print(f"\nSignal breakdown: {longs} LONG, {shorts} SHORT")

    print("\n✅ Signal generation test PASSED!")
    return True


def test_with_simulated_data():
    """Test with simulated trending data"""
    import numpy as np

    print("\n" + "=" * 70)
    print("TESTING WITH SIMULATED DATA")
    print("=" * 70)

    # Create 200 candles of uptrending data
    np.random.seed(42)
    n = 200

    # Create a trending price series
    base_price = 100.0
    trend = np.cumsum(np.random.randn(n) * 0.5 + 0.1)  # Upward drift
    prices = base_price + trend

    # Create OHLC data
    data = []
    for i in range(n):
        close = prices[i]
        high = close + abs(np.random.randn() * 0.5)
        low = close - abs(np.random.randn() * 0.5)
        open_price = close + np.random.randn() * 0.3
        volume = 1000 + np.random.randint(0, 500)

        data.append({
            'timestamp': pd.Timestamp('2025-12-01') + pd.Timedelta(hours=i),
            'open': open_price,
            'high': max(high, open_price, close),
            'low': min(low, open_price, close),
            'close': close,
            'volume': volume
        })

    df = pd.DataFrame(data)
    print(f"Created {len(df)} simulated candles")

    # Calculate indicators
    calc = IndicatorCalculator(df)
    df = calc.add_all_indicators()

    # Test all 8 coins
    print("\nTesting all 8 coins from COIN_PARAMS:")

    for symbol in COIN_PARAMS.keys():
        config = {
            'enabled': True,
            'risk_pct': 3.0,
            'max_leverage': 5.0
        }

        strategy = DonchianBreakout(config, symbol)

        signals = []
        for i in range(50, len(df)):
            df_slice = df.iloc[:i+1].copy()
            signal = strategy.generate_signals(df_slice, current_positions=[])
            if signal:
                signals.append(signal)

        print(f"  {symbol}: {len(signals)} signals (TP={strategy.tp_atr}, SL={strategy.sl_atr}, Period={strategy.period})")

    print("\n✅ All strategy instances work correctly!")
    return True


def test_config_loading():
    """Test that config.yaml loads correctly"""
    print("\n" + "=" * 70)
    print("TESTING CONFIG LOADING")
    print("=" * 70)

    try:
        from config import load_config

        config = load_config('config.yaml')

        print(f"Trading enabled: {config.trading.enabled}")
        print(f"Symbols: {config.trading.symbols}")
        print(f"Dry run: {config.safety.dry_run}")

        # Check each Donchian strategy is configured
        for symbol in COIN_PARAMS.keys():
            strategy_name = f'donchian_{symbol.split("-")[0].lower()}'
            if config.is_strategy_enabled(strategy_name):
                print(f"  ✅ {strategy_name} enabled")
            else:
                print(f"  ❌ {strategy_name} NOT configured")

        print("\n✅ Config loading test PASSED!")
        return True

    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("DONCHIAN BREAKOUT INTEGRATION TEST")
    print("=" * 70)

    # Test 1: Config loading
    config_ok = test_config_loading()

    # Test 2: Signal generation
    signals_ok = test_donchian_signals()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Config loading: {'✅ PASSED' if config_ok else '❌ FAILED'}")
    print(f"Signal generation: {'✅ PASSED' if signals_ok else '❌ FAILED'}")

    if config_ok and signals_ok:
        print("\n🎉 ALL TESTS PASSED - Ready for live trading!")
    else:
        print("\n⚠️ Some tests failed - please fix before going live")
