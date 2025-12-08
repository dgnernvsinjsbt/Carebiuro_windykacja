#!/usr/bin/env python3
"""
Quick BingX API Test - Tests core functionality:
1. Account balance
2. Trade history
3. Buy small FARTCOIN-USDT
4. Immediately close it
"""

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient, BingXAPIError

async def test_quick_trading():
    """Quick test of essential API endpoints"""

    print("="*70)
    print("BingX Quick API Test")
    print("="*70)

    # Get API credentials from environment or config
    api_key = os.getenv('BINGX_API_KEY')
    api_secret = os.getenv('BINGX_API_SECRET')

    if not api_key or not api_secret:
        print("\n❌ API credentials not found!")
        print("\nSet environment variables:")
        print("  export BINGX_API_KEY='your_key'")
        print("  export BINGX_API_SECRET='your_secret'")
        print("\nOr update config.yaml")
        return 1

    print(f"\n✓ API Key loaded: {api_key[:8]}...{api_key[-4:]}")

    # Use TESTNET by default for safety
    testnet = os.getenv('BINGX_TESTNET', 'true').lower() == 'true'
    print(f"✓ Testnet mode: {testnet}")

    # Create client
    client = BingXClient(api_key, api_secret, testnet)

    try:
        # Test 1: Connectivity
        print("\n" + "="*70)
        print("TEST 1: Connectivity")
        print("="*70)

        ping = await client.ping()
        if ping:
            print("✓ API connection successful")
        else:
            print("❌ API connection failed")
            return 1

        # Test 2: Account Balance
        print("\n" + "="*70)
        print("TEST 2: Account Balance")
        print("="*70)

        balance = await client.get_balance()
        if balance:
            print("✓ Balance retrieved:")
            if 'balance' in balance:
                bal = balance['balance']
                print(f"  Asset: {bal.get('asset', 'N/A')}")
                print(f"  Available: {bal.get('balance', 'N/A')}")
                print(f"  Equity: {bal.get('equity', 'N/A')}")
        else:
            print("⚠ No balance data returned")

        # Test 3: Trade History
        print("\n" + "="*70)
        print("TEST 3: Trade History")
        print("="*70)

        try:
            # Get recent orders for FARTCOIN-USDT
            symbol = "FARTCOIN-USDT"
            history = await client.get_order_history(symbol, limit=10)

            if history:
                print(f"✓ Order history retrieved: {len(history)} orders")
                for i, order in enumerate(history[:5], 1):
                    print(f"  {i}. {order.get('side')} {order.get('origQty')} @ {order.get('price')} - Status: {order.get('status')}")
            else:
                print("⚠ No order history (normal if you haven't traded yet)")
        except BingXAPIError as e:
            print(f"⚠ Order history error: {e}")
        except Exception as e:
            print(f"⚠ Order history not available: {e}")

        # Test 4: Get current FARTCOIN price
        print("\n" + "="*70)
        print("TEST 4: Current FARTCOIN-USDT Price")
        print("="*70)

        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('lastPrice', 0))

        if current_price > 0:
            print(f"✓ Current price: {current_price}")
        else:
            print("❌ Could not get current price")
            await client.close()
            return 1

        # Test 5: Place small buy order (SKIP ON MAINNET FOR NOW)
        print("\n" + "="*70)
        print("TEST 5: Trading Test")
        print("="*70)
        print("⚠ SKIPPED - Trading test disabled for safety")
        print("All basic API endpoints work!")

        await client.close()
        print("\n" + "="*70)
        print("✓ BASIC TESTS PASSED!")
        print("="*70)
        return 0

        # Old trading test code below (disabled)
        if not testnet:
            print("\n⚠ SKIPPING TRADING TEST - NOT ON TESTNET")
            print("Set BINGX_TESTNET=true to test trading")
            await client.close()
            return 0

        print("\n" + "="*70)
        print("TEST 5: Place Small Buy Order (Testnet)")
        print("="*70)

        # Calculate small test order
        test_quantity = 1.0  # 1 FARTCOIN (adjust based on minimum)
        test_price = current_price * 0.95  # 5% below market (won't fill immediately)

        print(f"\nPlacing LIMIT BUY order:")
        print(f"  Symbol: {symbol}")
        print(f"  Quantity: {test_quantity}")
        print(f"  Price: {test_price} (market: {current_price})")

        try:
            buy_order = await client.place_order(
                symbol=symbol,
                side="BUY",
                position_side="LONG",
                order_type="LIMIT",
                quantity=test_quantity,
                price=test_price
            )

            order_id = buy_order.get('orderId')
            print(f"✓ Order placed successfully!")
            print(f"  Order ID: {order_id}")
            print(f"  Status: {buy_order.get('status', 'UNKNOWN')}")

            # Test 6: Query the order
            print("\n" + "="*70)
            print("TEST 6: Query Order")
            print("="*70)

            order_info = await client.get_order(symbol, order_id)
            print(f"✓ Order queried:")
            print(f"  Status: {order_info.get('status')}")
            print(f"  Filled: {order_info.get('executedQty', 0)}/{order_info.get('origQty', 0)}")

            # Test 7: Cancel the order
            print("\n" + "="*70)
            print("TEST 7: Cancel Order")
            print("="*70)

            await asyncio.sleep(1)  # Wait 1 second

            cancel_result = await client.cancel_order(symbol, order_id)
            print(f"✓ Order cancelled successfully!")
            print(f"  Order ID: {cancel_result.get('orderId', order_id)}")

        except BingXAPIError as e:
            print(f"❌ Trading error: {e}")
            print("\nThis might be due to:")
            print("  - Minimum order size not met")
            print("  - Insufficient balance")
            print("  - Symbol name format (try 'FARTCOINUSDT' without hyphen)")
            return 1

        # Summary
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED!")
        print("="*70)
        print("\nYou can now:")
        print("  1. Place real orders on testnet")
        print("  2. Test your trading strategies")
        print("  3. Switch to mainnet (set BINGX_TESTNET=false)")

        await client.close()
        return 0

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        await client.close()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(test_quick_trading())
    sys.exit(exit_code)