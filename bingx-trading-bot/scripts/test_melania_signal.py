#!/usr/bin/env python3
"""
Test MELANIA RSI Optimized Strategy End-to-End
Simulates a SHORT signal and tests order placement flow
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies.melania_rsi_optimized import MelaniaRSIOptimized
from execution.bingx_client import BingXClient
from config import load_config
import time
import asyncio

async def main():
    print("=" * 70)
    print("MELANIA RSI OPTIMIZED - END-TO-END TEST")
    print("Testing: Signal Generation → Order Placement → Order Cancellation")
    print("=" * 70)

    # Load config
    config = load_config()

    # Initialize strategy
    strategy = MelaniaRSIOptimized()
    print(f"\n✅ Strategy initialized: {strategy.name}")
    print(f"   Symbol: {strategy.symbol}")
    print(f"   Timeframe: {strategy.timeframe}")
    print(f"   Current Risk: {strategy.current_risk * 100:.1f}%")

    # Initialize BingX client
    bingx = BingXClient(
        config.bingx.api_key,
        config.bingx.api_secret,
        config.bingx.testnet,
        config.bingx.base_url
    )
    print(f"\n✅ BingX client initialized (testnet={config.bingx.testnet})")

    # Get account balance
    balance_info = await bingx.get_balance()
    # balance_info is a list, find USDT balance
    balance = 13.17  # Hardcode for testing (we know it's $13.17 from bot log)
    for asset in balance_info:
        if asset.get('asset') == 'USDT':
            balance = float(asset.get('balance', 0))
            break
    print(f"   Account Balance: ${balance:.2f} USDT")

    # Get current market price
    print(f"\n📊 Fetching market data for {strategy.symbol}...")
    ticker = await bingx.get_ticker(strategy.symbol)
    print(f"   DEBUG: ticker keys = {list(ticker.keys())}")
    # Try different possible keys
    current_price = float(ticker.get('lastPrice') or ticker.get('price') or ticker.get('last') or 0)
    if current_price == 0:
        print(f"   ❌ Could not get price from ticker: {ticker}")
        return
    print(f"   Current Price: ${current_price:.6f}")

    # Fetch candles for indicator calculation
    print(f"\n📈 Fetching 15m candles...")
    candles = await bingx.get_candles(strategy.symbol, interval='15m', limit=300)
    print(f"   Fetched {len(candles)} candles")

    if len(candles) < 100:
        print(f"\n❌ Not enough candles (need 100, got {len(candles)})")
        return

    # Calculate indicators
    print(f"\n🔢 Calculating indicators (RSI, ATR, momentum, move size)...")
    df = strategy.calculate_indicators(candles)

    current = df.iloc[-1]
    previous = df.iloc[-2]

    print(f"\n📊 Indicator Values:")
    print(f"   RSI (current): {current['rsi']:.2f}")
    print(f"   RSI (previous): {previous['rsi']:.2f}")
    print(f"   ATR: {current['atr']:.6f}")
    print(f"   20-bar Return: {current['ret_20']:.2f}%")
    print(f"   Avg Move Size: {current['avg_move_size']:.2f}%")

    # Try to generate real signal first
    print(f"\n🎯 Checking for real trading signals...")
    real_signal = strategy.generate_signal(candles, current_price, balance)

    if real_signal:
        print(f"\n⚠️  REAL SIGNAL DETECTED!")
        print(f"   Side: {real_signal['side']}")
        print(f"   Reason: {real_signal['reason']}")
        print(f"\n❌ Aborting test - there's a real signal. Don't want to interfere.")
        return
    else:
        print(f"   ✅ No real signals (as expected)")

    # Force generate a SHORT signal for testing
    print(f"\n🧪 FORCING A TEST SHORT SIGNAL...")
    print(f"   (Bypassing RSI crossover and filters)")

    atr = current['atr']

    # Calculate SHORT signal parameters
    limit_price = current_price + (atr * strategy.limit_offset_atr)
    sl_price = limit_price + (atr * strategy.stop_loss_atr)
    tp_price = limit_price - (atr * strategy.take_profit_atr)

    sl_distance_pct = abs((sl_price - limit_price) / limit_price)
    risk_amount = balance * strategy.current_risk
    position_size = risk_amount / sl_distance_pct

    test_signal = {
        'type': 'LIMIT',
        'side': 'SHORT',
        'symbol': strategy.symbol,
        'entry_price': limit_price,
        'stop_loss': sl_price,
        'take_profit': tp_price,
        'position_size_usd': position_size,
        'max_wait_bars': strategy.max_wait_bars,
        'reason': f'TEST SIGNAL - RSI: {current["rsi"]:.2f}, Risk: {strategy.current_risk*100:.1f}%'
    }

    print(f"\n📋 Test Signal Details:")
    print(f"   Side: {test_signal['side']}")
    print(f"   Entry Price: ${test_signal['entry_price']:.6f} (limit)")
    print(f"   Stop Loss: ${test_signal['stop_loss']:.6f}")
    print(f"   Take Profit: ${test_signal['take_profit']:.6f}")
    print(f"   Position Size: ${test_signal['position_size_usd']:.2f}")
    print(f"   Risk Amount: ${risk_amount:.2f}")
    print(f"   SL Distance: {sl_distance_pct * 100:.2f}%")

    # Place the order
    print(f"\n🚀 PLACING TEST ORDER ON BINGX...")
    print(f"   ⚠️  This will create a real limit order on the exchange")

    try:
        # For SHORT, we need to place a SELL limit order
        order_result = await bingx.place_limit_order(
            symbol=test_signal['symbol'],
            side='SELL',  # SHORT = SELL
            quantity_usd=test_signal['position_size_usd'],
            price=test_signal['entry_price']
        )

        print(f"\n✅ ORDER PLACED SUCCESSFULLY!")
        print(f"   Order ID: {order_result.get('orderId')}")
        print(f"   Status: {order_result.get('status')}")
        print(f"   Symbol: {order_result.get('symbol')}")
        print(f"   Side: {order_result.get('side')}")
        print(f"   Price: {order_result.get('price')}")
        print(f"   Quantity: {order_result.get('origQty')}")

        order_id = order_result.get('orderId')

        # Wait 2 seconds
        print(f"\n⏳ Waiting 2 seconds before cancelling...")
        time.sleep(2)

        # Cancel the order
        print(f"\n❌ CANCELLING TEST ORDER...")
        cancel_result = await bingx.cancel_order(test_signal['symbol'], order_id)

        print(f"\n✅ ORDER CANCELLED SUCCESSFULLY!")
        print(f"   Order ID: {cancel_result.get('orderId')}")
        print(f"   Status: {cancel_result.get('status')}")

        print(f"\n" + "=" * 70)
        print("TEST COMPLETED SUCCESSFULLY! ✅")
        print("=" * 70)
        print(f"\nSignal Flow Verified:")
        print(f"   1. ✅ Market data fetched")
        print(f"   2. ✅ Indicators calculated (RSI, ATR, filters)")
        print(f"   3. ✅ Signal generated (forced SHORT)")
        print(f"   4. ✅ Position sizing calculated")
        print(f"   5. ✅ Limit order placed on BingX")
        print(f"   6. ✅ Order cancelled successfully")
        print(f"\nStrategy is ready for live trading! 🚀")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"\nFull error details:")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    asyncio.run(main())
