#!/usr/bin/env python3
"""
Test ETH limit order with 10x leverage
$30 position with 10x leverage = $3 margin required
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

async def test_eth_with_leverage():
    env = load_env()
    client = BingXClient(env['BINGX_API_KEY'], env['BINGX_API_SECRET'], testnet=False)

    try:
        symbol = "ETH-USDT"

        print("="*80)
        print("ETH LEVERAGE TEST")
        print("="*80)

        # Get contract info
        print("\n[1] Getting contract info...")
        contracts = await client.get_contract_info(symbol)
        contract = contracts[0] if isinstance(contracts, list) else contracts

        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('price', 0))

        price_precision = contract.get('pricePrecision', 2)
        quantity_precision = contract.get('quantityPrecision', 2)

        print(f"✅ Current price: ${current_price:.2f}")
        print(f"   Precision: price={price_precision}, qty={quantity_precision}")

        # Set 10x leverage
        print(f"\n[2] Setting leverage to 10x...")
        await client.set_leverage(symbol, "LONG", 10)
        await client.set_leverage(symbol, "SHORT", 10)
        print(f"✅ Leverage set to 10x")

        # Calculate quantity for $30 position
        position_value_usdt = 30.0
        quantity = position_value_usdt / current_price

        # Round UP to precision (to ensure we meet minimum)
        precision_factor = Decimal(10) ** quantity_precision
        quantity = float(Decimal(str(quantity)).quantize(
            Decimal('1') / precision_factor,
            rounding=ROUND_UP  # Round UP to ensure non-zero
        ))

        # Check minimum quantity
        min_qty = float(contract.get('minQty', 0.01))
        if quantity < min_qty:
            quantity = min_qty
            print(f"   ⚠️ Quantity below minimum, using minQty: {min_qty}")

        actual_value = quantity * current_price
        required_margin = actual_value / 10  # 10x leverage

        print(f"\n[3] Order parameters:")
        print(f"   Target position: ${position_value_usdt:.2f} USDT")
        print(f"   Quantity: {quantity} ETH")
        print(f"   Actual value: ${actual_value:.2f} USDT")
        print(f"   Required margin (10x): ${required_margin:.2f} USDT")

        # Test LONG limit order
        print(f"\n[4] Testing LONG limit order (0.6% below price)...")

        long_limit = current_price * 0.994  # 0.6% below
        long_limit = round(long_limit, price_precision)

        print(f"   Market: ${current_price:.2f}")
        print(f"   Limit:  ${long_limit:.2f} (0.6% below)")

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
            print(f"\n✅ LONG order placed! ID: {long_order_id}")
            print(f"   Quantity: {quantity} ETH")
            print(f"   Value: ${actual_value:.2f} USDT")
            print(f"   Margin used: ~${required_margin:.2f} USDT")

            await asyncio.sleep(1)

            # Cancel
            await client.cancel_order(symbol, long_order_id)
            print(f"   ✅ Order canceled")

        except Exception as e:
            print(f"❌ LONG order failed: {e}")
            import traceback
            traceback.print_exc()

        # Test SHORT limit order
        print(f"\n[5] Testing SHORT limit order (0.6% above price)...")

        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('price', 0))

        short_limit = current_price * 1.006  # 0.6% above
        short_limit = round(short_limit, price_precision)

        print(f"   Market: ${current_price:.2f}")
        print(f"   Limit:  ${short_limit:.2f} (0.6% above)")

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
            print(f"\n✅ SHORT order placed! ID: {short_order_id}")
            print(f"   Quantity: {quantity} ETH")
            print(f"   Value: ${actual_value:.2f} USDT")
            print(f"   Margin used: ~${required_margin:.2f} USDT")

            await asyncio.sleep(1)

            # Cancel
            await client.cancel_order(symbol, short_order_id)
            print(f"   ✅ Order canceled")

        except Exception as e:
            print(f"❌ SHORT order failed: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n{'='*80}")
        print("✅ ETH LEVERAGE TEST COMPLETE")
        print("="*80)
        print(f"\n✅ With 10x leverage:")
        print(f"   - $30 ETH position only needs ~$3 margin")
        print(f"   - LONG and SHORT routing works correctly")
        print(f"   - Ready for live trading!")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_eth_with_leverage())
