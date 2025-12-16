#!/usr/bin/env python3
"""
Quick test: Place a SHORT limit order on MELANIA and immediately cancel it
Tests the core order placement flow end-to-end
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execution.bingx_client import BingXClient
from config import load_config
import asyncio
import time

async def main():
    print("=" * 70)
    print("MELANIA ORDER PLACEMENT TEST")
    print("=" * 70)

    # Load config
    config = load_config()

    # Initialize BingX client
    bingx = BingXClient(
        config.bingx.api_key,
        config.bingx.api_secret,
        config.bingx.testnet,
        config.bingx.base_url
    )
    print(f"\n✅ BingX client initialized")

    # Get current price
    print(f"\n📊 Fetching MELANIA-USDT price...")
    ticker = await bingx.get_ticker("MELANIA-USDT")
    current_price = float(ticker.get('price'))
    print(f"   Current Price: ${current_price:.6f}")

    # Calculate test order parameters
    # SHORT: Place limit order ABOVE current price (won't fill immediately)
    limit_price = current_price * 1.05  # 5% above current price
    quantity = 100  # 100 MELANIA tokens (about $10)

    print(f"\n🧪 TEST ORDER PARAMETERS:")
    print(f"   Side: SHORT (SELL)")
    print(f"   Type: LIMIT")
    print(f"   Entry Price: ${limit_price:.6f} (5% above market)")
    print(f"   Quantity: {quantity} MELANIA")
    print(f"   Position Side: SHORT")

    try:
        # Place the SHORT limit order
        print(f"\n🚀 PLACING SHORT LIMIT ORDER...")
        order_result = await bingx.place_order(
            symbol="MELANIA-USDT",
            side="SELL",
            position_side="SHORT",
            order_type="LIMIT",
            quantity=quantity,
            price=limit_price
        )

        print(f"\n✅ ORDER PLACED SUCCESSFULLY!")
        print(f"   DEBUG: order_result = {order_result}")
        print(f"   Order ID: {order_result.get('orderId') or order_result.get('order', {}).get('orderId')}")
        print(f"   Status: {order_result.get('status')}")

        # Try to extract order ID from various possible response structures
        order_id = order_result.get('orderId') or order_result.get('order', {}).get('orderId')

        if not order_id:
            print(f"\n⚠️  Could not extract order ID from response. Checking open orders...")
            orders = await bingx.get_open_orders("MELANIA-USDT")
            if orders:
                # Get the most recent order
                order_id = orders[0].get('orderId')
                print(f"   Found order ID from open orders: {order_id}")

        # Wait 2 seconds
        print(f"\n⏳ Waiting 2 seconds before cancelling...")
        await asyncio.sleep(2)

        # Cancel the order
        print(f"\n❌ CANCELLING ORDER...")
        cancel_result = await bingx.cancel_order("MELANIA-USDT", order_id)

        print(f"\n✅ ORDER CANCELLED SUCCESSFULLY!")
        print(f"   Order ID: {cancel_result.get('orderId')}")
        print(f"   Status: {cancel_result.get('status')}")

        print(f"\n" + "=" * 70)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\nOrder Flow Verified:")
        print(f"   1. ✅ Market price fetched")
        print(f"   2. ✅ SHORT limit order placed on BingX")
        print(f"   3. ✅ Order cancelled successfully")
        print(f"\nMELANIA strategy is ready for live trading! 🚀")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"\nFull error details:")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    asyncio.run(main())
