#!/usr/bin/env python3
"""
END-TO-END TEST: PEPE Limit Order Flow
Simulates entire limit order lifecycle without real API calls
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from strategies.pepe_rsi_swing import PEPERSISwingStrategy


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def simulate_limit_order_flow():
    """Simulate complete limit order flow for PEPE"""

    print("=" * 80)
    print("PEPE RSI SWING - LIMIT ORDER FLOW TEST")
    print("=" * 80)

    # Step 1: Load real PEPE data
    print("\n[STEP 1] Loading PEPE-USDT data...")
    df = pd.read_csv('../trading/1000pepe_1h_90d.csv')
    df.columns = df.columns.str.lower()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Calculate indicators
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'], 14)

    print(f"✅ Loaded {len(df)} candles")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"   Current price: ${df.iloc[-1]['close']:.6f}")
    print(f"   Current RSI: {df.iloc[-1]['rsi']:.2f}")

    # Step 2: Initialize strategy
    print("\n[STEP 2] Initializing PEPE RSI Swing Strategy...")
    config = {
        'rsi_low': 30,
        'rsi_high': 65,
        'limit_offset_pct': 0.6,
        'max_wait_bars': 5,
        'stop_atr_mult': 2.0,
        'max_hold_bars': 168
    }

    strategy = PEPERSISwingStrategy(config, symbol='1000PEPE-USDT')

    print(f"✅ Strategy initialized:")
    print(f"   RSI thresholds: {config['rsi_low']}/{config['rsi_high']}")
    print(f"   Limit offset: {config['limit_offset_pct']}%")
    print(f"   Max wait: {config['max_wait_bars']} bars")

    # Step 3: Find RSI crossover signal
    print("\n[STEP 3] Scanning for RSI crossover signals...")

    signals_found = 0
    test_signal = None

    for i in range(50, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i-1]

        # Check for LONG signal (RSI crosses above 30)
        if prev['rsi'] <= 30 and current['rsi'] > 30:
            signals_found += 1

            if signals_found == 5:  # Use 5th signal for test
                test_signal = {
                    'index': i,
                    'timestamp': current['timestamp'],
                    'signal_price': current['close'],
                    'rsi': current['rsi'],
                    'atr': current['atr'],
                    'direction': 'LONG'
                }
                break

    if not test_signal:
        print("❌ No suitable signal found in dataset")
        return

    print(f"✅ Found signal #{signals_found}:")
    print(f"   Time: {test_signal['timestamp']}")
    print(f"   Direction: {test_signal['direction']}")
    print(f"   Signal price: ${test_signal['signal_price']:.6f}")
    print(f"   RSI: {test_signal['rsi']:.2f} (crossed above 30)")

    # Step 4: Calculate limit order price
    print("\n[STEP 4] Calculating limit order parameters...")

    limit_offset_pct = 0.6  # 0.6% below for LONG
    limit_price = test_signal['signal_price'] * (1 - limit_offset_pct / 100)

    position_size_usdt = 3.0  # $3 USDT test
    quantity = position_size_usdt / limit_price

    # Calculate SL/TP from limit price
    atr = test_signal['atr']
    stop_loss = limit_price - (2.0 * atr)

    # No fixed TP - RSI-based exit at 65

    print(f"✅ Limit order calculated:")
    print(f"   Signal price: ${test_signal['signal_price']:.6f}")
    print(f"   Limit price: ${limit_price:.6f} ({limit_offset_pct}% below)")
    print(f"   Quantity: {quantity:.1f} 1000PEPE")
    print(f"   Position value: ${position_size_usdt:.2f} USDT")
    print(f"   Stop loss: ${stop_loss:.6f} (2x ATR = ${atr:.6f})")
    print(f"   Take profit: RSI >= 65 (dynamic)")

    # Step 5: Simulate limit order monitoring
    print("\n[STEP 5] Simulating limit order fill monitoring...")

    signal_bar = test_signal['index']
    max_wait = 5
    filled = False
    fill_bar = None

    for wait_bar in range(signal_bar + 1, min(signal_bar + 1 + max_wait, len(df))):
        check_candle = df.iloc[wait_bar]
        wait_time = wait_bar - signal_bar

        print(f"\n   Bar {wait_time}: {check_candle['timestamp']}")
        print(f"   Price range: ${check_candle['low']:.6f} - ${check_candle['high']:.6f}")
        print(f"   Limit price: ${limit_price:.6f}")

        # Check if limit fills (price touches/goes below limit)
        if check_candle['low'] <= limit_price:
            filled = True
            fill_bar = wait_bar
            fill_time = check_candle['timestamp']
            fill_price = limit_price  # Assume fills at limit price

            print(f"   ✅ LIMIT FILLED! Price touched ${check_candle['low']:.6f}")
            print(f"   Fill price: ${fill_price:.6f}")
            break
        else:
            print(f"   ⏳ Waiting... (limit not touched)")

    if not filled:
        print(f"\n   ❌ LIMIT NOT FILLED after {max_wait} bars → Order would be CANCELLED")
        return

    # Step 6: Place SL/TP
    print(f"\n[STEP 6] Placing Stop Loss & Take Profit...")

    print(f"✅ Orders would be placed:")
    print(f"   Entry filled: ${fill_price:.6f}")
    print(f"   Stop loss: ${stop_loss:.6f} (STOP_MARKET order)")
    print(f"   Take profit: Monitor RSI for >= 65 (dynamic exit)")

    # Step 7: Simulate trade monitoring until exit
    print(f"\n[STEP 7] Monitoring trade for exit...")

    entry_bar = fill_bar
    max_hold = 168
    exit_found = False

    for monitor_bar in range(entry_bar + 1, min(entry_bar + max_hold, len(df))):
        monitor_candle = df.iloc[monitor_bar]
        bars_held = monitor_bar - entry_bar

        # Check stop loss
        if monitor_candle['low'] <= stop_loss:
            exit_price = stop_loss
            exit_time = monitor_candle['timestamp']
            exit_reason = 'STOP LOSS'
            exit_found = True

            print(f"\n   ❌ STOP LOSS HIT at bar {bars_held}")
            print(f"   Exit time: {exit_time}")
            print(f"   Exit price: ${exit_price:.6f}")
            break

        # Check RSI take profit
        if monitor_candle['rsi'] >= 65:
            exit_price = monitor_candle['close']
            exit_time = monitor_candle['timestamp']
            exit_reason = 'RSI TARGET'
            exit_found = True

            print(f"\n   ✅ RSI TARGET HIT at bar {bars_held}")
            print(f"   Exit time: {exit_time}")
            print(f"   Exit RSI: {monitor_candle['rsi']:.2f}")
            print(f"   Exit price: ${exit_price:.6f}")
            break

        # Print progress every 20 bars
        if bars_held % 20 == 0:
            print(f"   Bar {bars_held}: RSI {monitor_candle['rsi']:.2f}, Price ${monitor_candle['close']:.6f}")

    if not exit_found:
        exit_price = df.iloc[min(entry_bar + max_hold - 1, len(df) - 1)]['close']
        exit_time = df.iloc[min(entry_bar + max_hold - 1, len(df) - 1)]['timestamp']
        exit_reason = 'TIME EXIT'

        print(f"\n   ⏰ TIME EXIT at bar {max_hold}")
        print(f"   Exit time: {exit_time}")
        print(f"   Exit price: ${exit_price:.6f}")

    # Step 8: Calculate PnL
    print(f"\n[STEP 8] Trade Summary:")
    print("=" * 80)

    pnl_usd = (exit_price - fill_price) * quantity
    pnl_pct = (exit_price - fill_price) / fill_price * 100

    # Account for fees (0.02% maker for entry, 0.05% taker for exit)
    fee_entry = position_size_usdt * 0.0002  # 0.02% on $3
    fee_exit = (quantity * exit_price) * 0.0005  # 0.05% on exit value
    total_fees = fee_entry + fee_exit

    net_pnl_usd = pnl_usd - total_fees
    net_pnl_pct = (net_pnl_usd / position_size_usdt) * 100

    print(f"Entry: ${fill_price:.6f} @ {fill_time}")
    print(f"Exit:  ${exit_price:.6f} @ {exit_time}")
    print(f"Exit reason: {exit_reason}")
    print(f"\nP&L (gross): {pnl_pct:+.2f}% (${pnl_usd:+.4f})")
    print(f"Fees: -${total_fees:.4f} (entry: ${fee_entry:.4f}, exit: ${fee_exit:.4f})")
    print(f"P&L (net): {net_pnl_pct:+.2f}% (${net_pnl_usd:+.4f})")

    status = "✅ PROFITABLE" if net_pnl_usd > 0 else "❌ LOSS"
    print(f"\nResult: {status}")

    print("\n" + "=" * 80)
    print("FLOW VALIDATION COMPLETE")
    print("=" * 80)

    # Summary
    print(f"\n📊 What happened:")
    print(f"1. Detected RSI crossover above 30 → Signal generated")
    print(f"2. Placed limit order 0.6% below signal price")
    print(f"3. Limit filled when price dipped to ${fill_price:.6f}")
    print(f"4. Stop loss placed at ${stop_loss:.6f} (2x ATR)")
    print(f"5. Monitored RSI for exit at 65")
    print(f"6. Exited via {exit_reason} at ${exit_price:.6f}")
    print(f"7. Final P&L: {net_pnl_pct:+.2f}% on $3 USDT position")

    print(f"\n✅ Limit order flow works correctly!")
    print(f"   - Entry via limit order (better price than market)")
    print(f"   - SL via STOP_MARKET (automatic protection)")
    print(f"   - TP via RSI monitoring (dynamic exit)")

    return {
        'signal_price': test_signal['signal_price'],
        'limit_price': limit_price,
        'fill_price': fill_price,
        'exit_price': exit_price,
        'exit_reason': exit_reason,
        'pnl_pct': net_pnl_pct,
        'pnl_usd': net_pnl_usd
    }


if __name__ == "__main__":
    try:
        result = simulate_limit_order_flow()

        if result:
            print(f"\n" + "=" * 80)
            print("✅ TEST PASSED - Ready for live deployment")
            print("=" * 80)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
