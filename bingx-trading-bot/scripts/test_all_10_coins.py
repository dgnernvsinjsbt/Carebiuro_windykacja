"""
Test $6 USDT positions on all 10 coins (LIVE API - REAL ORDERS!)

Tests LONG + SHORT limit orders with 10x leverage.

Top 10 Coins by R/DD:
1. CRV: 22.03x R/DD
2. MELANIA: 21.36x R/DD
3. AIXBT: 20.20x R/DD
4. TRUMPSOL: 13.28x R/DD
5. UNI: 12.38x R/DD
6. DOGE: 10.66x R/DD
7. XLM: 9.53x R/DD
8. MOODENG: 8.38x R/DD
9. FARTCOIN: 8.44x R/DD
10. PEPE: 7.13x R/DD
"""

import asyncio
import os
from decimal import Decimal, ROUND_UP
from execution.bingx_client import BingXClient


# Test coins (Top 10 by R/DD)
TEST_COINS = [
    'CRV-USDT',      # 22.03x R/DD 🏆 BEST!
    'MELANIA-USDT',  # 21.36x R/DD (77% WR!)
    'AIXBT-USDT',    # 20.20x R/DD
    'TRUMPSOL-USDT', # 13.28x R/DD
    'UNI-USDT',      # 12.38x R/DD
    'DOGE-USDT',     # 10.66x R/DD
    'XLM-USDT',      # 9.53x R/DD
    'MOODENG-USDT',  # 8.38x R/DD
    'FARTCOIN-USDT', # 8.44x R/DD
    '1000PEPE-USDT', # 7.13x R/DD
]


async def test_coin(client: BingXClient, symbol: str, target_usdt: float = 6.0):
    """Test LONG and SHORT limit orders for a coin"""

    print(f"\n{'='*70}")
    print(f"Testing {symbol} with ${target_usdt} USDT positions")
    print(f"{'='*70}")

    try:
        # Get current price
        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('price', 0))

        if not current_price:
            print(f"❌ {symbol}: Failed to get price (ticker: {ticker})")
            return False

        print(f"Current price: ${current_price}")

        # Get contract info (precision)
        contracts = await client.get_contract_info(symbol)
        contract = contracts[0] if isinstance(contracts, list) else contracts

        if not contract:
            print(f"❌ {symbol}: Contract not found")
            return False

        quantity_precision = int(contract.get('quantityPrecision', 1))
        price_precision = int(contract.get('pricePrecision', 6))
        min_qty = float(contract.get('minQty', 0))

        print(f"Contract info: qty_prec={quantity_precision}, price_prec={price_precision}, min_qty={min_qty}")

        # Set leverage to 10x for LONG and SHORT
        try:
            await client.set_leverage(symbol, 'LONG', 10)
            await client.set_leverage(symbol, 'SHORT', 10)
            print(f"✅ Leverage set to 10x (LONG + SHORT)")
        except Exception as e:
            print(f"⚠️ Leverage already set or error: {e}")

        # Calculate quantity for $6 position (with 10x leverage)
        # Position value = quantity * price
        # With 10x leverage, margin = position_value / 10
        # We want position_value = $6, so margin = $0.60
        quantity = target_usdt / current_price

        # Round UP to ensure non-zero quantity
        precision_factor = Decimal(10) ** quantity_precision
        quantity = float(
            Decimal(str(quantity)).quantize(
                Decimal('1') / precision_factor,
                rounding=ROUND_UP
            )
        )

        # Ensure meets minimum quantity
        if quantity < min_qty:
            quantity = min_qty
            print(f"⚠️ Adjusted quantity to minimum: {quantity}")

        # Calculate actual values
        actual_value = quantity * current_price
        required_margin = actual_value / 10  # 10x leverage

        print(f"\nPosition details:")
        print(f"  Quantity: {quantity}")
        print(f"  Actual value: ${actual_value:.2f} USDT")
        print(f"  Required margin: ${required_margin:.2f} USDT (10x leverage)")

        # Calculate limit prices (1% away from current price)
        long_limit_price = current_price * 0.99   # 1% below
        short_limit_price = current_price * 1.01  # 1% above

        # Round limit prices to precision
        price_precision_factor = Decimal(10) ** price_precision
        long_limit_price = float(
            Decimal(str(long_limit_price)).quantize(
                Decimal('1') / price_precision_factor,
                rounding=ROUND_UP
            )
        )
        short_limit_price = float(
            Decimal(str(short_limit_price)).quantize(
                Decimal('1') / price_precision_factor,
                rounding=ROUND_UP
            )
        )

        print(f"\n🔹 Testing LONG limit order @ ${long_limit_price} (1% below ${current_price})")

        # Test LONG limit order
        long_order = await client.place_order(
            symbol=symbol,
            side='BUY',
            position_side='LONG',
            order_type='LIMIT',
            quantity=quantity,
            price=long_limit_price,
            time_in_force='GTC'
        )

        long_order_id = long_order.get('order', {}).get('orderId')

        if long_order_id:
            print(f"✅ LONG limit order placed: ID={long_order_id}")

            # Cancel immediately
            await asyncio.sleep(1)
            cancel = await client.cancel_order(symbol, long_order_id)
            print(f"✅ LONG order cancelled: {cancel}")
        else:
            print(f"❌ LONG order failed: {long_order}")
            return False

        print(f"\n🔹 Testing SHORT limit order @ ${short_limit_price} (1% above ${current_price})")

        # Test SHORT limit order
        short_order = await client.place_order(
            symbol=symbol,
            side='SELL',
            position_side='SHORT',
            order_type='LIMIT',
            quantity=quantity,
            price=short_limit_price,
            time_in_force='GTC'
        )

        short_order_id = short_order.get('order', {}).get('orderId')

        if short_order_id:
            print(f"✅ SHORT limit order placed: ID={short_order_id}")

            # Cancel immediately
            await asyncio.sleep(1)
            cancel = await client.cancel_order(symbol, short_order_id)
            print(f"✅ SHORT order cancelled: {cancel}")
        else:
            print(f"❌ SHORT order failed: {short_order}")
            return False

        print(f"\n✅ {symbol} PASSED - Both LONG and SHORT orders work!")
        return True

    except Exception as e:
        print(f"\n❌ {symbol} FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Test all 10 coins"""

    # Load API keys from .env file
    api_key = None
    api_secret = None

    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('BINGX_API_KEY='):
                    api_key = line.split('=', 1)[1]
                elif line.startswith('BINGX_API_SECRET='):
                    api_secret = line.split('=', 1)[1]

    if not api_key or not api_secret:
        print("❌ Error: BINGX_API_KEY and BINGX_API_SECRET must be set in .env file")
        return

    # Initialize client (PRODUCTION MODE!)
    client = BingXClient(
        api_key=api_key,
        api_secret=api_secret,
        testnet=False,  # PRODUCTION!
        base_url='https://open-api.bingx.com'
    )

    print("\n" + "="*70)
    print("🚀 TESTING ALL 10 COINS WITH $6 USDT POSITIONS (10x LEVERAGE)")
    print("="*70)
    print("\nCoins to test:")
    for i, coin in enumerate(TEST_COINS, 1):
        print(f"{i}. {coin}")

    # Test all coins
    results = {}
    for symbol in TEST_COINS:
        success = await test_coin(client, symbol, target_usdt=6.0)
        results[symbol] = success
        await asyncio.sleep(2)  # Rate limit protection

    # Summary
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    print(f"\n✅ Passed: {passed}/{len(TEST_COINS)}")
    print(f"❌ Failed: {failed}/{len(TEST_COINS)}")

    print("\nDetailed results:")
    for symbol, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {symbol}: {status}")

    if passed == len(TEST_COINS):
        print("\n🎉 ALL TESTS PASSED! Bot is ready for production!")
    else:
        print("\n⚠️ Some tests failed. Review errors above.")


if __name__ == '__main__':
    asyncio.run(main())
