#!/usr/bin/env python3
"""
Test placing order with correct signature for POST requests
BingX requires different signature format for POST
"""

import asyncio
import hmac
import hashlib
import time
import aiohttp
import os
import urllib.parse

API_KEY = os.getenv('BINGX_API_KEY')
API_SECRET = os.getenv('BINGX_API_SECRET')
BASE_URL = "https://open-api.bingx.com"

async def place_order_test():
    """Test placing and cancelling order with correct POST signature"""

    # Get current price first
    async with aiohttp.ClientSession() as session:
        ticker_url = f"{BASE_URL}/openApi/swap/v1/ticker/price"
        async with session.get(ticker_url, params={'symbol': 'FARTCOIN-USDT'}) as response:
            ticker = await response.json()
            current_price = float(ticker['data']['price'])

    print("="*70)
    print("BingX Order Placement Test")
    print("="*70)
    print(f"\nCurrent FARTCOIN-USDT price: ${current_price}")

    # Prepare order parameters
    test_price = round(current_price * 0.9, 4)  # 10% below market
    test_qty = 1

    params = {
        'symbol': 'FARTCOIN-USDT',
        'side': 'BUY',
        'positionSide': 'LONG',
        'type': 'LIMIT',
        'quantity': test_qty,
        'price': test_price,
        'timestamp': int(time.time() * 1000)
    }

    # Generate signature - BingX uses URL-encoded params for POST
    sorted_params = sorted(params.items())
    query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])

    print(f"\nOrder details:")
    print(f"  Symbol: {params['symbol']}")
    print(f"  Side: {params['side']}")
    print(f"  Type: {params['type']}")
    print(f"  Quantity: {params['quantity']}")
    print(f"  Price: ${params['price']} (market: ${current_price})")
    print(f"\nQuery string for signature:")
    print(f"  {query_string}")

    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    params['signature'] = signature

    print(f"\nSignature: {signature[:32]}...")

    # Make POST request
    headers = {
        'X-BX-APIKEY': API_KEY,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    url = f"{BASE_URL}/openApi/swap/v2/trade/order"

    print(f"\nPlacing order...")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=params, headers=headers) as response:
            result = await response.json()

            print(f"\nResponse:")
            print(f"  Code: {result.get('code')}")
            print(f"  Message: {result.get('msg')}")

            if result['code'] == 0:
                order_id = result['data']['order']['orderId']
                print(f"  ✓ Order ID: {order_id}")
                print(f"\n✅ Order placed successfully!")

                # Wait 2 seconds
                print(f"\nWaiting 2 seconds before cancelling...")
                await asyncio.sleep(2)

                # Cancel order
                print(f"\nCancelling order...")

                cancel_params = {
                    'symbol': 'FARTCOIN-USDT',
                    'orderId': order_id,
                    'timestamp': int(time.time() * 1000)
                }

                sorted_cancel = sorted(cancel_params.items())
                cancel_query = '&'.join([f"{k}={v}" for k, v in sorted_cancel])
                cancel_sig = hmac.new(
                    API_SECRET.encode('utf-8'),
                    cancel_query.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()

                cancel_params['signature'] = cancel_sig

                async with session.delete(url, params=cancel_params, headers=headers) as cancel_response:
                    cancel_result = await cancel_response.json()

                    print(f"\nCancel response:")
                    print(f"  Code: {cancel_result.get('code')}")
                    print(f"  Message: {cancel_result.get('msg')}")

                    if cancel_result['code'] == 0:
                        print(f"\n✅ Order cancelled successfully!")
                        print("\n" + "="*70)
                        print("🎉 ALL TESTS PASSED!")
                        print("="*70)
                        print("\nYou can now:")
                        print("  • Place real orders")
                        print("  • Start trading bot")
                        print("  • Run automated strategies")
                    else:
                        print(f"\n⚠️  Cancel failed: {cancel_result}")

            else:
                print(f"\n❌ Order placement failed!")
                print(f"\nFull response: {result}")
                print("\nPossible issues:")
                print("  • Minimum order quantity not met (check contract specs)")
                print("  • Price too far from market")
                print("  • Insufficient margin")

if __name__ == "__main__":
    asyncio.run(place_order_test())
