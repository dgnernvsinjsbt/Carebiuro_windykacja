#!/usr/bin/env python3
"""Cancel test orders"""

import asyncio
import sys
from pathlib import Path

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

async def cancel_orders():
    env = load_env()
    client = BingXClient(env['BINGX_API_KEY'], env['BINGX_API_SECRET'], testnet=False)

    try:
        symbol = "1000PEPE-USDT"

        # Get all open orders
        print("Fetching open orders...")
        open_orders = await client.get_open_orders(symbol)

        if not open_orders:
            print("✅ No open orders to cancel")
            return

        print(f"\nFound {len(open_orders)} open order(s):")
        for order in open_orders:
            order_id = order.get('orderId')
            side = order.get('side')
            position_side = order.get('positionSide')
            price = order.get('price')
            qty = order.get('quantity')

            print(f"  - Order {order_id}: {side} {position_side} @ ${price} ({qty} qty)")

        print(f"\nCanceling all orders...")
        for order in open_orders:
            order_id = order.get('orderId')
            try:
                await client.cancel_order(symbol, order_id)
                print(f"  ✅ Canceled order {order_id}")
            except Exception as e:
                print(f"  ❌ Failed to cancel {order_id}: {e}")

        print(f"\n✅ All orders canceled")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(cancel_orders())
