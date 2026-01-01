#!/usr/bin/env python3
"""
LIVE TEST: Verify limit order routing for ALL coins
Tests: BTC, ETH, 1000PEPE, DOGE, FARTCOIN
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal, ROUND_DOWN

sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient

def load_env():
    env_path = Path(__file__).parent / '.env'
    env = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    return env

async def test_coin_routing(client, symbol, limit_offset_pct, test_position_usdt=3.0):
    """Test limit order routing for one coin"""

    print(f"\n{'='*80}")
    print(f"TESTING: {symbol}")
    print(f"{'='*80}")

    try:
        # Get contract info and price
        contracts = await client.get_contract_info(symbol)
        contract = contracts[0] if isinstance(contracts, list) else contracts

        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('price', 0))

        if current_price == 0:
            print(f"❌ Price is $0 - coin not available")
            return {'symbol': symbol, 'success': False, 'error': 'Price is $0'}

        price_precision = contract.get('pricePrecision', 6)
        quantity_precision = contract.get('quantityPrecision', 1)
        min_qty = float(contract.get('minQty', 1))

        print(f"Current price: ${current_price:.6f}")
        print(f"Precision: price={price_precision}, qty={quantity_precision}")

        # Calculate quantity
        quantity = test_position_usdt / current_price
        precision_factor = Decimal(10) ** quantity_precision
        quantity = float(Decimal(str(quantity)).quantize(
            Decimal('1') / precision_factor,
            rounding=ROUND_DOWN
        ))

        if quantity < min_qty:
            quantity = min_qty

        actual_value = quantity * current_price

        print(f"Quantity: {quantity} | Value: ${actual_value:.2f} USDT")

        # TEST 1: LONG (limit below price)
        print(f"\n[TEST 1] LONG limit ({limit_offset_pct}% below)")

        long_limit = current_price * (1 - limit_offset_pct / 100)
        long_limit = round(long_limit, price_precision)

        print(f"  Market: ${current_price:.6f}")
        print(f"  Limit:  ${long_limit:.6f} ({limit_offset_pct}% below)")

        try:
            long_order = await client.place_order(
                symbol=symbol,
                side="BUY",
                position_side="LONG",
                order_type="LIMIT",
                quantity=quantity,
                price=long_limit,
                time_in_force="GTC"
            )

            long_order_id = long_order.get('order', {}).get('orderId')
            print(f"  ✅ LONG order placed! ID: {long_order_id}")

            await asyncio.sleep(0.5)

            # Cancel immediately
            await client.cancel_order(symbol, long_order_id)
            print(f"  ✅ LONG order canceled")

            long_success = True

        except Exception as e:
            print(f"  ❌ LONG failed: {e}")
            long_success = False

        await asyncio.sleep(1)

        # TEST 2: SHORT (limit above price)
        print(f"\n[TEST 2] SHORT limit ({limit_offset_pct}% above)")

        # Get fresh price
        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('price', 0))

        short_limit = current_price * (1 + limit_offset_pct / 100)
        short_limit = round(short_limit, price_precision)

        print(f"  Market: ${current_price:.6f}")
        print(f"  Limit:  ${short_limit:.6f} ({limit_offset_pct}% above)")

        try:
            short_order = await client.place_order(
                symbol=symbol,
                side="SELL",
                position_side="SHORT",
                order_type="LIMIT",
                quantity=quantity,
                price=short_limit,
                time_in_force="GTC"
            )

            short_order_id = short_order.get('order', {}).get('orderId')
            print(f"  ✅ SHORT order placed! ID: {short_order_id}")

            await asyncio.sleep(0.5)

            # Cancel immediately
            await client.cancel_order(symbol, short_order_id)
            print(f"  ✅ SHORT order canceled")

            short_success = True

        except Exception as e:
            print(f"  ❌ SHORT failed: {e}")
            short_success = False

        # Summary
        if long_success and short_success:
            print(f"\n✅ {symbol} - BOTH DIRECTIONS WORK")
            return {'symbol': symbol, 'success': True, 'long': True, 'short': True}
        elif long_success or short_success:
            print(f"\n⚠️ {symbol} - PARTIAL SUCCESS (LONG: {long_success}, SHORT: {short_success})")
            return {'symbol': symbol, 'success': False, 'long': long_success, 'short': short_success}
        else:
            print(f"\n❌ {symbol} - BOTH DIRECTIONS FAILED")
            return {'symbol': symbol, 'success': False, 'long': False, 'short': False}

    except Exception as e:
        print(f"\n❌ {symbol} - ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {'symbol': symbol, 'success': False, 'error': str(e)}


async def test_all_coins():
    """Test limit order routing for all coins"""

    env = load_env()
    client = BingXClient(env['BINGX_API_KEY'], env['BINGX_API_SECRET'], testnet=False)

    print("=" * 80)
    print("LIVE TEST: All Coins Limit Order Routing")
    print("=" * 80)
    print("Mode: PRODUCTION")
    print("Position size: $3 USDT per test")
    print("=" * 80)

    # Coin configs (symbol, limit_offset_pct)
    coins = [
        ("BTC-USDT", 0.5),       # BTC: 0.5% offset
        ("ETH-USDT", 0.6),       # ETH: 0.6% offset
        ("1000PEPE-USDT", 0.6),  # PEPE: 0.6% offset
        ("DOGE-USDT", 0.1),      # DOGE: 0.1% offset
        ("FARTCOIN-USDT", 1.0),  # FARTCOIN: 1.0% offset
    ]

    results = []

    try:
        # Test each coin
        for symbol, offset in coins:
            result = await test_coin_routing(client, symbol, offset, test_position_usdt=3.0)
            results.append(result)
            await asyncio.sleep(2)  # Pause between coins

        # Final summary
        print(f"\n{'='*80}")
        print("FINAL SUMMARY")
        print(f"{'='*80}")

        print(f"\n{'Coin':<20} {'Offset':<10} {'LONG':<10} {'SHORT':<10} {'Status'}")
        print("-" * 60)

        for r in results:
            symbol = r['symbol']

            if r['success']:
                long_status = "✅" if r.get('long') else "❌"
                short_status = "✅" if r.get('short') else "❌"
                status = "✅ PASS"
            else:
                long_status = "✅" if r.get('long') else "❌"
                short_status = "✅" if r.get('short') else "❌"
                status = "❌ FAIL"

            # Get offset for this coin
            offset = next((o for s, o in coins if s == symbol), 'N/A')

            print(f"{symbol:<20} {offset}%{'':<7} {long_status:<10} {short_status:<10} {status}")

        # Overall result
        all_passed = all(r['success'] for r in results)

        print(f"\n{'='*80}")
        if all_passed:
            print("✅ ALL COINS PASSED - Ready for live trading!")
        else:
            failed = [r['symbol'] for r in results if not r['success']]
            print(f"⚠️ SOME COINS FAILED: {', '.join(failed)}")
            print("Check errors above for details")
        print(f"{'='*80}")

        # Clean up any remaining orders
        print(f"\n[CLEANUP] Checking for any remaining open orders...")
        for symbol, _ in coins:
            try:
                open_orders = await client.get_open_orders(symbol)
                if open_orders:
                    print(f"  Found {len(open_orders)} open order(s) on {symbol}, canceling...")
                    for order in open_orders:
                        order_id = order.get('orderId')
                        await client.cancel_order(symbol, order_id)
                        print(f"    ✅ Canceled {order_id}")
            except:
                pass

        print(f"✅ Cleanup complete")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_all_coins())
