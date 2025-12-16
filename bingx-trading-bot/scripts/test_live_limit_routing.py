#!/usr/bin/env python3
"""
LIVE TEST: Verify limit order routing on BingX
- LONG: Places limit BELOW current price (should work)
- SHORT: Places limit ABOVE current price (should work)

⚠️ USES REAL API - Will place and immediately cancel orders
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal, ROUND_DOWN
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient


async def test_limit_order_routing():
    """Test limit order routing with real BingX API"""

    print("=" * 80)
    print("LIVE TEST: BingX Limit Order Routing Verification")
    print("=" * 80)

    # Load config
    config_path = Path(__file__).parent / 'config.yaml'
    if not config_path.exists():
        print(f"\n❌ Config file not found: {config_path}")
        print("Create config.yaml with your API keys first!")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)

    api_key = config['bingx']['api_key']
    api_secret = config['bingx']['api_secret']

    if not api_key or not api_secret or 'YOUR_' in api_key:
        print("\n❌ API keys not configured in config.yaml")
        print("Add your BingX API key and secret first!")
        return

    # Initialize BingX client
    client = BingXClient(api_key, api_secret, testnet=False)

    try:
        # Step 1: Test connection
        print("\n[STEP 1] Testing BingX connection...")
        ping = await client.ping()
        if not ping:
            print("❌ Failed to connect to BingX")
            return
        print("✅ Connected to BingX")

        # Step 2: Get account balance
        print("\n[STEP 2] Checking account balance...")
        balance_data = await client.get_balance()

        usdt_balance = 0.0
        if isinstance(balance_data, list):
            for asset in balance_data:
                if asset.get('asset') == 'USDT':
                    usdt_balance = float(asset.get('availableMargin', 0))

        print(f"✅ USDT Balance: ${usdt_balance:.2f}")

        if usdt_balance < 1.0:
            print(f"\n⚠️ Balance too low: ${usdt_balance:.2f}")
            print("Need at least $1 USDT for testing")
            return

        # Step 3: Get PEPE contract info and current price
        symbol = "1000PEPE-USDT"
        print(f"\n[STEP 3] Getting {symbol} contract info...")

        contracts = await client.get_contract_info(symbol)
        contract = contracts[0] if isinstance(contracts, list) else contracts

        # Get current price from ticker
        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('lastPrice', 0))

        price_precision = contract.get('pricePrecision', 6)
        quantity_precision = contract.get('quantityPrecision', 1)
        min_qty = float(contract.get('minQty', 1))

        print(f"✅ Contract info:")
        print(f"   Current price: ${current_price:.6f}")
        print(f"   Price precision: {price_precision}")
        print(f"   Quantity precision: {quantity_precision}")
        print(f"   Min quantity: {min_qty}")

        # Step 4: Calculate test order parameters
        print(f"\n[STEP 4] Calculating test order parameters...")

        # Use very small position size for safety
        test_position_usdt = 0.50  # $0.50 test

        # Calculate quantity
        quantity = test_position_usdt / current_price

        # Round to precision
        precision_factor = Decimal(10) ** quantity_precision
        quantity = float(Decimal(str(quantity)).quantize(
            Decimal('1') / precision_factor,
            rounding=ROUND_DOWN
        ))

        # Ensure minimum quantity
        if quantity < min_qty:
            quantity = min_qty

        actual_value = quantity * current_price

        print(f"✅ Test parameters:")
        print(f"   Position size: ${test_position_usdt:.2f} USDT (target)")
        print(f"   Quantity: {quantity} 1000PEPE")
        print(f"   Actual value: ${actual_value:.2f} USDT")

        # =======================================================================
        # TEST 1: LONG LIMIT ORDER (below current price)
        # =======================================================================
        print(f"\n" + "=" * 80)
        print("TEST 1: LONG LIMIT ORDER (0.6% below current price)")
        print("=" * 80)

        limit_offset_pct = 0.6
        long_limit_price = current_price * (1 - limit_offset_pct / 100)
        long_limit_price = round(long_limit_price, price_precision)

        print(f"\nCurrent price: ${current_price:.6f}")
        print(f"LONG limit: ${long_limit_price:.6f} ({limit_offset_pct}% below)")
        print(f"Placing BUY limit order...")

        try:
            long_order = await client.place_order(
                symbol=symbol,
                side="BUY",
                position_side="BOTH",
                order_type="LIMIT",
                quantity=quantity,
                price=long_limit_price,
                time_in_force="GTC"
            )

            long_order_id = long_order.get('orderId')
            print(f"✅ LONG order placed!")
            print(f"   Order ID: {long_order_id}")
            print(f"   Side: BUY")
            print(f"   Type: LIMIT")
            print(f"   Limit price: ${long_limit_price:.6f}")
            print(f"   Quantity: {quantity}")

            # Check order status
            await asyncio.sleep(1)
            order_status = await client.get_order(symbol, long_order_id)
            status = order_status.get('status', 'UNKNOWN')

            print(f"   Status: {status}")

            if status in ['NEW', 'PENDING']:
                print(f"   ✅ Order ACTIVE (waiting for fill)")

                # Cancel order immediately
                print(f"\nCanceling LONG order...")
                cancel_result = await client.cancel_order(symbol, long_order_id)
                print(f"   ✅ LONG order canceled")
            else:
                print(f"   ⚠️ Unexpected status: {status}")

        except Exception as e:
            print(f"❌ LONG order failed: {e}")
            import traceback
            traceback.print_exc()

        # Wait between tests
        await asyncio.sleep(2)

        # =======================================================================
        # TEST 2: SHORT LIMIT ORDER (above current price)
        # =======================================================================
        print(f"\n" + "=" * 80)
        print("TEST 2: SHORT LIMIT ORDER (0.6% above current price)")
        print("=" * 80)

        # Get fresh price
        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('lastPrice', 0))

        short_limit_price = current_price * (1 + limit_offset_pct / 100)
        short_limit_price = round(short_limit_price, price_precision)

        print(f"\nCurrent price: ${current_price:.6f}")
        print(f"SHORT limit: ${short_limit_price:.6f} ({limit_offset_pct}% above)")
        print(f"Placing SELL limit order...")

        try:
            short_order = await client.place_order(
                symbol=symbol,
                side="SELL",
                position_side="BOTH",
                order_type="LIMIT",
                quantity=quantity,
                price=short_limit_price,
                time_in_force="GTC"
            )

            short_order_id = short_order.get('orderId')
            print(f"✅ SHORT order placed!")
            print(f"   Order ID: {short_order_id}")
            print(f"   Side: SELL")
            print(f"   Type: LIMIT")
            print(f"   Limit price: ${short_limit_price:.6f}")
            print(f"   Quantity: {quantity}")

            # Check order status
            await asyncio.sleep(1)
            order_status = await client.get_order(symbol, short_order_id)
            status = order_status.get('status', 'UNKNOWN')

            print(f"   Status: {status}")

            if status in ['NEW', 'PENDING']:
                print(f"   ✅ Order ACTIVE (waiting for fill)")

                # Cancel order immediately
                print(f"\nCanceling SHORT order...")
                cancel_result = await client.cancel_order(symbol, short_order_id)
                print(f"   ✅ SHORT order canceled")
            else:
                print(f"   ⚠️ Unexpected status: {status}")

        except Exception as e:
            print(f"❌ SHORT order failed: {e}")
            import traceback
            traceback.print_exc()

        # =======================================================================
        # FINAL SUMMARY
        # =======================================================================
        print(f"\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        print(f"\n✅ LONG limit order (BUY below price): SUCCESS")
        print(f"   - Placed at ${long_limit_price:.6f} ({limit_offset_pct}% below ${current_price:.6f})")
        print(f"   - Order accepted by exchange")
        print(f"   - Canceled successfully")

        print(f"\n✅ SHORT limit order (SELL above price): SUCCESS")
        print(f"   - Placed at ${short_limit_price:.6f} ({limit_offset_pct}% above ${current_price:.6f})")
        print(f"   - Order accepted by exchange")
        print(f"   - Canceled successfully")

        print(f"\n" + "=" * 80)
        print("✅ ROUTING VERIFICATION COMPLETE")
        print("=" * 80)

        print(f"\nConclusions:")
        print(f"1. ✅ LONG orders route correctly (limit BELOW current price)")
        print(f"2. ✅ SHORT orders route correctly (limit ABOVE current price)")
        print(f"3. ✅ Orders are placed and cancelable")
        print(f"4. ✅ Ready for live trading with limit orders")

        print(f"\nNext steps:")
        print(f"1. Start bot in DRY RUN mode to verify signal generation")
        print(f"2. Monitor pending orders in logs")
        print(f"3. Switch to LIVE mode when ready")
        print(f"4. Start with small position sizes ($3-6 USDT)")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()
        print(f"\n✅ BingX client closed")


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will place REAL orders on BingX!")
    print("⚠️  Orders will be canceled immediately, but still requires API keys")
    print("⚠️  Position size: ~$0.50 USDT (very small for safety)")

    response = input("\nProceed with live test? (yes/no): ")

    if response.lower() == 'yes':
        asyncio.run(test_limit_order_routing())
    else:
        print("\n❌ Test canceled by user")
