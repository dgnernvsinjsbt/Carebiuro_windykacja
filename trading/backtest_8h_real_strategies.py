#!/usr/bin/env python3
"""
Run the ACTUAL strategy implementations against the 8-hour bot data.
This will definitively show if signals should have been generated.
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add bot directory to path
sys.path.insert(0, str(Path(__file__).parent / 'bingx-trading-bot'))

from strategies.fartcoin_atr_limit import FartcoinATRLimitStrategy
from strategies.trumpsol_contrarian import TrumpsolContrarianStrategy

def prepare_dataframe(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Prepare dataframe with required indicators"""
    df = df[df['symbol'] == symbol].copy()
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # The bot data already has most indicators, but let's verify/add missing ones

    # Add EMA_20 if not present (use SMA_20 as approximation)
    if 'ema_20' not in df.columns:
        df['ema_20'] = df['sma_20']

    # Ensure we have open/high/low (already present in bot data)

    return df

def test_fartcoin_strategy():
    """Test FARTCOIN ATR Limit strategy"""
    print("=" * 100)
    print("🔍 FARTCOIN ATR LIMIT STRATEGY - REAL CODE TEST")
    print("=" * 100)

    # Load bot data
    bot_df = pd.read_csv('/workspaces/Carebiuro_windykacja/bingx-trading-bot/bot_data_last_8h.csv')
    df = prepare_dataframe(bot_df, 'FARTCOIN-USDT')

    print(f"\nDataset: {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Initialize strategy with config
    config = {
        'atr_expansion_mult': 1.5,
        'atr_lookback_bars': 20,
        'ema_distance_max_pct': 3.0,
        'limit_offset_pct': 1.0,
        'max_wait_bars': 3,
        'stop_atr_mult': 2.0,
        'target_atr_mult': 8.0,
        'max_hold_bars': 200
    }

    strategy = FartcoinATRLimitStrategy(config, 'FARTCOIN-USDT')

    # Run through each candle
    signals = []

    for i in range(30, len(df)):  # Start from bar 30 (need lookback)
        df_slice = df.iloc[:i+1].copy()
        signal = strategy.analyze(df_slice)

        if signal:
            candle = df.iloc[i]
            signals.append({
                'timestamp': candle['timestamp'],
                'bar_index': i,
                'signal': signal
            })

    print(f"\n{'=' * 100}")
    print(f"📊 RESULTS")
    print(f"{'=' * 100}")
    print(f"\nTotal signals generated: {len(signals)}")

    if len(signals) > 0:
        print(f"\n⚠️  SIGNALS WERE FOUND! Bot should have detected these:\n")
        print(f"{'Timestamp':<20} {'Direction':<8} {'Signal Price':>12} {'Limit Price':>12} {'ATR Ratio':>10} {'EMA Dist':>10}")
        print("-" * 100)

        for s in signals:
            sig = s['signal']
            print(f"{str(s['timestamp']):<20} "
                  f"{sig['direction']:<8} "
                  f"${sig['signal_price']:>11.6f} "
                  f"${sig['limit_price']:>11.6f} "
                  f"{sig['atr_ratio']:>9.2f}x "
                  f"{sig['ema_distance_pct']:>9.2f}%")
    else:
        print("\n✅ No signals generated - Bot was correct")

    return signals

def test_trumpsol_strategy():
    """Test TRUMPSOL Contrarian strategy"""
    print("\n" + "=" * 100)
    print("🔍 TRUMPSOL CONTRARIAN STRATEGY - REAL CODE TEST")
    print("=" * 100)

    # Load bot data
    bot_df = pd.read_csv('/workspaces/Carebiuro_windykacja/bingx-trading-bot/bot_data_last_8h.csv')
    df = prepare_dataframe(bot_df, 'TRUMPSOL-USDT')

    print(f"\nDataset: {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Initialize strategy with config
    config = {
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

    strategy = TrumpsolContrarianStrategy(config, 'TRUMPSOL-USDT')

    # Run through each candle
    signals = []

    for i in range(35, len(df)):  # Start from bar 35 (need 30 for MA + 5 for ret_5m)
        df_slice = df.iloc[:i+1].copy()
        signal = strategy.analyze(df_slice)

        if signal:
            candle = df.iloc[i]
            signals.append({
                'timestamp': candle['timestamp'],
                'bar_index': i,
                'signal': signal
            })

    print(f"\n{'=' * 100}")
    print(f"📊 RESULTS")
    print(f"{'=' * 100}")
    print(f"\nTotal signals generated: {len(signals)}")

    if len(signals) > 0:
        print(f"\n⚠️  SIGNALS WERE FOUND! Bot should have detected these:\n")
        print(f"{'Timestamp':<20} {'Direction':<8} {'Entry Price':>12} {'5min Ret':>10} {'Vol Ratio':>10} {'ATR Ratio':>10}")
        print("-" * 100)

        for s in signals:
            sig = s['signal']
            print(f"{str(s['timestamp']):<20} "
                  f"{sig['direction']:<8} "
                  f"${sig['entry_price']:>11.6f} "
                  f"{sig['ret_5m']*100:>9.2f}% "
                  f"{sig['vol_ratio']:>9.2f}x "
                  f"{sig['atr_ratio']:>9.2f}x")
    else:
        print("\n✅ No signals generated - Bot was correct")

    return signals

if __name__ == '__main__':
    print("\n" + "=" * 100)
    print("🔬 RUNNING ACTUAL STRATEGY CODE AGAINST 8-HOUR BOT DATA")
    print("=" * 100)
    print("\nThis test uses the REAL strategy implementations from bingx-trading-bot/strategies/")
    print("If signals are found, the bot has a bug. If no signals, the bot is working correctly.\n")

    # Test FARTCOIN
    fartcoin_signals = test_fartcoin_strategy()

    # Test TRUMPSOL
    trumpsol_signals = test_trumpsol_strategy()

    # Final verdict
    print("\n" + "=" * 100)
    print("🎯 FINAL VERDICT")
    print("=" * 100)

    total_signals = len(fartcoin_signals) + len(trumpsol_signals)

    if total_signals == 0:
        print("\n✅ BOT IS WORKING CORRECTLY")
        print("   - Ran actual strategy code against 8 hours of data")
        print("   - Zero signals generated by both strategies")
        print("   - Bot correctly identified no trading opportunities")
        print("   - This is EXPECTED for highly selective strategies\n")
    else:
        print(f"\n❌ POTENTIAL BUG DETECTED")
        print(f"   - {len(fartcoin_signals)} FARTCOIN signals should have been detected")
        print(f"   - {len(trumpsol_signals)} TRUMPSOL signals should have been detected")
        print(f"   - Bot may have a signal detection issue\n")
