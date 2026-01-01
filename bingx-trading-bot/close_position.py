"""Quick script to close open position"""
import asyncio
from config import load_config
from execution.bingx_client import BingXClient

async def close_position():
    config = load_config('config_donchian.yaml')
    client = BingXClient(config.bingx.api_key, config.bingx.api_secret, config.bingx.testnet)

    symbol = 'DOGE-USDT'
    print(f"🔍 Checking for open {symbol} position...")

    # Get positions
    positions = await client.get_positions()

    if positions and isinstance(positions, list):
        print(f"  Found {len(positions)} position entries")
        for pos in positions:
            print(f"  Checking: {pos.get('symbol')} amt={pos.get('positionAmt', 0)}")
            if pos.get('symbol') == symbol and float(pos.get('positionAmt', 0)) != 0:
                position_amt = float(pos['positionAmt'])
                avg_price = float(pos['avgPrice'])
                unrealized_pnl = float(pos.get('unrealizedProfit', 0))

                print(f"\n📊 FOUND OPEN POSITION:")
                print(f"  Symbol: {symbol}")
                print(f"  Side: {pos['positionSide']}")
                print(f"  Amount: {position_amt}")
                print(f"  Entry: ${avg_price:.6f}")
                print(f"  Unrealized PnL: ${unrealized_pnl:.4f}")

                # Close position (LONG position = SELL order)
                print(f"\n📤 Closing position...")

                close_order = await client.place_order(
                    symbol=symbol,
                    side='SELL',  # Close LONG
                    order_type='MARKET',
                    quantity=abs(position_amt),
                    position_side='LONG'
                )

                if close_order:
                    print(f"✅ Position closed!")
                    print(f"  Order ID: {close_order.get('order', {}).get('orderId')}")
                else:
                    print(f"❌ Failed to close position")

                break
    else:
        print(f"❌ No open {symbol} position found")

    await client.close()

if __name__ == "__main__":
    asyncio.run(close_position())
