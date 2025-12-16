#!/usr/bin/env python3
"""
Final API test using the actual BingXClient from the project
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient, BingXAPIError
from config import load_config

async def main():
    print("="*70)
    print("Final BingX API Test - Using BingXClient")
    print("="*70)

    # Load config
    config = load_config('config.yaml')

    client = BingXClient(
        config.bingx.api_key,
        config.bingx.api_secret,
        config.bingx.testnet
    )

    try:
        # Test 1: Balance
        print("\n✅ TEST 1: Account Balance")
        balance = await client.get_balance()
        if balance and 'balance' in balance:
            for asset in balance['balance']:
                if float(asset.get('balance', 0)) > 0:
                    print(f"   {asset['asset']}: {asset['balance']} USDT")

        # Test 2: Positions
        print("\n✅ TEST 2: Positions")
        positions = await client.get_positions()
        print(f"   Open positions: {len(positions)}")

        # Test 3: Open orders
        print("\n✅ TEST 3: Open Orders")
        orders = await client.get_open_orders()
        print(f"   Open orders: {len(orders)}")

        # Test 4: Price
        print("\n✅ TEST 4: FARTCOIN Price")
        ticker = await client.get_ticker("FARTCOIN-USDT")
        print(f"   Raw ticker: {ticker}")
        price = ticker.get('lastPrice') or ticker.get('price')
        print(f"   Current price: ${price}")

        # Test 5: Place & Cancel (very small order)
        print("\n✅ TEST 5: Place & Cancel Order")
        print("   Placing BUY 6 FARTCOIN @ 10% below market...")

        current_price = float(price)
        test_price = round(current_price * 0.9, 4)

        try:
            order = await client.place_order(
                symbol="FARTCOIN-USDT",
                side="BUY",
                position_side="BOTH",  # One-way mode (not hedge mode)
                order_type="LIMIT",
                quantity=6,  # Minimum is 5.618 FARTCOIN
                price=test_price
            )

            print(f"   ✓ Order placed! Full response: {order}")

            # Extract order ID from response
            order_id = None
            if isinstance(order, dict):
                order_id = order.get('orderId') or order.get('order', {}).get('orderId')

            print(f"   ✓ Order ID: {order_id}")

            # Wait 2 sec
            await asyncio.sleep(2)

            # Cancel
            await client.cancel_order("FARTCOIN-USDT", order_id)
            print(f"   ✓ Order cancelled!")

            print("\n" + "="*70)
            print("🎉 ALL TESTS PASSED!")
            print("="*70)
            print("\n✅ API is fully functional:")
            print("   • Balance: Working")
            print("   • Positions: Working")
            print("   • Orders: Working")
            print("   • Price data: Working")
            print("   • Trading (place/cancel): Working")
            print("\n🚀 Ready to start automated trading!")

        except BingXAPIError as e:
            print(f"   ❌ Trading error: {e}")
            print("\n⚠️  Note: GET endpoints work, POST might need adjustment")
            print("   This could be due to:")
            print("   - Minimum order size (check contract specs)")
            print("   - API signature format for POST")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
