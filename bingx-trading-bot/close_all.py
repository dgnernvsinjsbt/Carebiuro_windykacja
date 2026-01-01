"""Close all positions and cancel all orders"""
import asyncio
from config import load_config
from execution.bingx_client import BingXClient

async def close_all():
    config = load_config('config_donchian.yaml')
    client = BingXClient(config.bingx.api_key, config.bingx.api_secret, config.bingx.testnet)

    print("🔍 Checking all positions and orders...\n")

    # 1. Get all positions
    positions = await client.get_positions()

    if positions and isinstance(positions, list):
        open_positions = [pos for pos in positions if float(pos.get('positionAmt', 0)) != 0]

        if open_positions:
            print(f"📊 Found {len(open_positions)} open positions:")
            for pos in open_positions:
                symbol = pos.get('symbol')
                amt = float(pos['positionAmt'])
                side = pos['positionSide']
                entry = float(pos['avgPrice'])
                pnl = float(pos.get('unrealizedProfit', 0))

                print(f"\n  {symbol}:")
                print(f"    Side: {side}")
                print(f"    Amount: {amt}")
                print(f"    Entry: ${entry:.6f}")
                print(f"    PnL: ${pnl:.4f}")

                # Close position
                close_side = 'SELL' if side == 'LONG' else 'BUY'
                print(f"    📤 Closing with {close_side} order...")

                close_order = await client.place_order(
                    symbol=symbol,
                    side=close_side,
                    order_type='MARKET',
                    quantity=abs(amt),
                    position_side=side
                )

                if close_order:
                    print(f"    ✅ Closed! Order ID: {close_order.get('order', {}).get('orderId')}")
                else:
                    print(f"    ❌ Failed to close")
        else:
            print("✅ No open positions")
    else:
        print("✅ No open positions")

    # 2. Get all open orders (pending SL/TP)
    print(f"\n🔍 Checking open orders...")

    # Check each symbol for open orders
    symbols = ['DOGE-USDT', 'UNI-USDT', 'PI-USDT', 'PENGU-USDT', 'ETH-USDT',
               'AIXBT-USDT', 'FARTCOIN-USDT', 'CRV-USDT']

    total_orders = 0
    for symbol in symbols:
        try:
            orders = await client.get_open_orders(symbol)
            if orders and len(orders) > 0:
                print(f"\n  {symbol}: {len(orders)} open orders")
                for order in orders:
                    order_id = order.get('orderId')
                    order_type = order.get('type')
                    side = order.get('side')
                    price = order.get('stopPrice') or order.get('price')

                    print(f"    Order {order_id}: {order_type} {side} @ ${price}")

                    # Cancel order
                    cancel_result = await client.cancel_order(symbol, order_id)
                    if cancel_result:
                        print(f"    ✅ Cancelled")
                        total_orders += 1
                    else:
                        print(f"    ❌ Failed to cancel")
        except Exception as e:
            # Symbol might not have orders, skip
            pass

    if total_orders == 0:
        print("✅ No pending orders")
    else:
        print(f"\n✅ Cancelled {total_orders} orders")

    await client.close()
    print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    asyncio.run(close_all())
