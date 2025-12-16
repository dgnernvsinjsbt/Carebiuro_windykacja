#!/usr/bin/env python3
"""
Test $6 USDT positions on all coins (ETH, PEPE, DOGE, FARTCOIN)
BTC excluded per user request
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal, ROUND_DOWN, ROUND_UP

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

async def test_coin(client, symbol, limit_offset_pct, target_usdt=6.0):
    """Test placing $6 USDT order for one coin"""

    print(f"\n{'='*80}")
    print(f"TESTING: {symbol} (${target_usdt} USDT position)")
    print(f"{'='*80}")

    try:
        # Get contract info
        contracts = await client.get_contract_info(symbol)
        contract = contracts[0] if isinstance(contracts, list) else contracts

        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('price', 0))

        price_precision = contract.get('pricePrecision', 6)
        quantity_precision = contract.get('quantityPrecision', 1)

        print(f"Current price: ${current_price:.6f}")

        # Set leverage to 10x
        await client.set_leverage(symbol, "LONG", 10)
        await client.set_leverage(symbol, "SHORT", 10)

        # Calculate quantity
        quantity = target_usdt / current_price

        precision_factor = Decimal(10) ** quantity_precision
        quantity = float(Decimal(str(quantity)).quantize(
            Decimal('1') / precision_factor,
            rounding=ROUND_UP  # Round UP to ensure we meet minimum
        ))

        # Ensure minimum
        min_qty = float(contract.get('minQty', 0.001))
        if quantity < min_qty:
            quantity = min_qty
            print(f"⚠️ Using minQty: {min_qty} (target was {target_usdt / current_price:.6f})")

        actual_value = quantity * current_price
        required_margin = actual_value / 10  # 10x leverage

        print(f"Quantity: {quantity} | Value: ${actual_value:.2f} | Margin: ${required_margin:.2f}")

        # TEST LONG
        print(f"\n[LONG] Placing limit {limit_offset_pct}% below price...")
        long_limit = current_price * (1 - limit_offset_pct / 100)
        long_limit = round(long_limit, price_precision)

        print(f"  Market: ${current_price:.6f}")
        print(f"  Limit:  ${long_limit:.6f}")

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
            print(f"  ✅ Order placed! ID: {long_order_id}")

            await asyncio.sleep(0.5)
            await client.cancel_order(symbol, long_order_id)
            print(f"  ✅ Canceled")

            long_success = True
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            long_success = False

        await asyncio.sleep(1)

        # TEST SHORT
        print(f"\n[SHORT] Placing limit {limit_offset_pct}% above price...")

        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('price', 0))

        short_limit = current_price * (1 + limit_offset_pct / 100)
        short_limit = round(short_limit, price_precision)

        print(f"  Market: ${current_price:.6f}")
        print(f"  Limit:  ${short_limit:.6f}")

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
            print(f"  ✅ Order placed! ID: {short_order_id}")

            await asyncio.sleep(0.5)
            await client.cancel_order(symbol, short_order_id)
            print(f"  ✅ Canceled")

            short_success = True
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            short_success = False

        return {
            'symbol': symbol,
            'success': long_success and short_success,
            'long': long_success,
            'short': short_success,
            'value': actual_value,
            'margin': required_margin
        }

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {'symbol': symbol, 'success': False, 'error': str(e)}


async def test_all():
    env = load_env()
    client = BingXClient(env['BINGX_API_KEY'], env['BINGX_API_SECRET'], testnet=False)

    print("="*80)
    print("$6 USDT POSITION TEST - ALL COINS (10x Leverage)")
    print("="*80)
    print("Testing: ETH, PEPE, DOGE, FARTCOIN")
    print("BTC excluded (user request)")
    print("="*80)

    # Coin configs (symbol, limit_offset_pct)
    coins = [
        ("ETH-USDT", 0.6),
        ("1000PEPE-USDT", 0.6),
        ("DOGE-USDT", 0.1),
        ("FARTCOIN-USDT", 1.0),
    ]

    results = []

    try:
        for symbol, offset in coins:
            result = await test_coin(client, symbol, offset, target_usdt=6.0)
            results.append(result)
            await asyncio.sleep(2)

        # Summary
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")

        print(f"\n{'Coin':<20} {'Position':<12} {'Margin':<12} {'LONG':<8} {'SHORT':<8} {'Status'}")
        print("-"*70)

        for r in results:
            symbol = r['symbol']

            if r.get('success'):
                value = f"${r.get('value', 0):.2f}"
                margin = f"${r.get('margin', 0):.2f}"
                long_st = "✅" if r.get('long') else "❌"
                short_st = "✅" if r.get('short') else "❌"
                status = "✅ PASS"
            else:
                value = "N/A"
                margin = "N/A"
                long_st = "❌"
                short_st = "❌"
                status = "❌ FAIL"

            print(f"{symbol:<20} {value:<12} {margin:<12} {long_st:<8} {short_st:<8} {status}")

        all_passed = all(r.get('success', False) for r in results)

        print(f"\n{'='*80}")
        if all_passed:
            print("✅ ALL COINS PASSED - Ready to deploy!")
        else:
            failed = [r['symbol'] for r in results if not r.get('success', False)]
            print(f"⚠️ SOME FAILED: {', '.join(failed)}")
        print(f"{'='*80}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_all())
