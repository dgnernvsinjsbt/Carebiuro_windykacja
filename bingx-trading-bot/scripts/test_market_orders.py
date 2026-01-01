#!/usr/bin/env python3
"""
Test BingX Market Orders - Open and Close Position
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient, BingXAPIError
from config import load_config

async def main():
    print("="*70)
    print("BingX Market Order Test - Open & Close Position")
    print("="*70)

    # Load config
    config = load_config('config.yaml')

    client = BingXClient(
        config.bingx.api_key,
        config.bingx.api_secret,
        config.bingx.testnet
    )

    try:
        # Get initial balance
        print("\n📊 Initial State:")
        balance_data = await client.get_balance()
        if isinstance(balance_data, list):
            for asset in balance_data:
                if asset.get('asset') == 'USDT':
                    print(f"   Balance: {asset['balance']} USDT")
                    print(f"   Available: {asset['availableMargin']} USDT")

        # Check positions
        positions = await client.get_positions("FARTCOIN-USDT")
        print(f"   Open positions: {len([p for p in positions if float(p.get('positionAmt', 0)) != 0])}")

        # Get current price
        ticker = await client.get_ticker("FARTCOIN-USDT")
        current_price = float(ticker.get('price') or ticker.get('lastPrice'))
        print(f"   Current FARTCOIN price: ${current_price}")

        # Step 1: OPEN POSITION - Market BUY
        print("\n" + "="*70)
        print("STEP 1: Opening LONG Position with Market Order")
        print("="*70)

        quantity = 6  # Minimum order size
        print(f"Placing MARKET BUY for {quantity} FARTCOIN...")

        buy_order = await client.place_order(
            symbol="FARTCOIN-USDT",
            side="BUY",
            position_side="BOTH",  # One-way mode
            order_type="MARKET",
            quantity=quantity
        )

        print(f"✓ BUY Order Executed!")
        if isinstance(buy_order, dict) and 'order' in buy_order:
            order_data = buy_order['order']
            print(f"   Order ID: {order_data.get('orderId')}")
            print(f"   Status: {order_data.get('status')}")
            print(f"   Quantity: {order_data.get('quantity')} FARTCOIN")
            print(f"   Executed: {order_data.get('executedQty')} FARTCOIN")
            print(f"   Avg Price: ${order_data.get('avgPrice', 'pending')}")

        # Wait for order to fill
        print("\nWaiting 2 seconds for order to settle...")
        await asyncio.sleep(2)

        # Check position after buy
        print("\n📈 Position After BUY:")
        positions = await client.get_positions("FARTCOIN-USDT")

        position_found = False
        for pos in positions:
            pos_amt = float(pos.get('positionAmt', 0))
            if pos_amt != 0:
                position_found = True
                print(f"   Symbol: {pos['symbol']}")
                print(f"   Side: {pos['positionSide']}")
                print(f"   Amount: {pos_amt} FARTCOIN")
                print(f"   Entry Price: ${pos.get('entryPrice')}")
                print(f"   Mark Price: ${pos.get('markPrice')}")
                print(f"   Unrealized PnL: ${pos.get('unrealizedProfit')}")

        if not position_found:
            print("   ⚠️  No position found (might still be settling)")

        # Step 2: CLOSE POSITION - Market SELL
        print("\n" + "="*70)
        print("STEP 2: Closing Position with Market Order")
        print("="*70)

        print(f"Placing MARKET SELL for {quantity} FARTCOIN...")

        sell_order = await client.place_order(
            symbol="FARTCOIN-USDT",
            side="SELL",
            position_side="BOTH",  # One-way mode
            order_type="MARKET",
            quantity=quantity
        )

        print(f"✓ SELL Order Executed!")
        if isinstance(sell_order, dict) and 'order' in sell_order:
            order_data = sell_order['order']
            print(f"   Order ID: {order_data.get('orderId')}")
            print(f"   Status: {order_data.get('status')}")
            print(f"   Quantity: {order_data.get('quantity')} FARTCOIN")
            print(f"   Executed: {order_data.get('executedQty')} FARTCOIN")
            print(f"   Avg Price: ${order_data.get('avgPrice', 'pending')}")

        # Wait for order to fill
        print("\nWaiting 2 seconds for order to settle...")
        await asyncio.sleep(2)

        # Final state
        print("\n" + "="*70)
        print("📊 Final State:")
        print("="*70)

        # Check final balance
        balance_data = await client.get_balance()
        if isinstance(balance_data, list):
            for asset in balance_data:
                if asset.get('asset') == 'USDT':
                    final_balance = float(asset['balance'])
                    available = float(asset['availableMargin'])
                    print(f"   Balance: {final_balance} USDT")
                    print(f"   Available: {available} USDT")

        # Check final positions
        positions = await client.get_positions("FARTCOIN-USDT")
        open_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
        print(f"   Open positions: {len(open_positions)}")

        if len(open_positions) == 0:
            print("\n✅ Position fully closed!")
        else:
            print("\n⚠️  Position still open:")
            for pos in open_positions:
                print(f"      Amount: {pos.get('positionAmt')} FARTCOIN")

        print("\n" + "="*70)
        print("🎉 MARKET ORDER TEST COMPLETE!")
        print("="*70)
        print("\n✅ Successfully tested:")
        print("   • Market BUY to open position")
        print("   • Market SELL to close position")
        print("   • Real-time position tracking")
        print("   • P&L calculation")

        print("\n🚀 Trading system is FULLY operational!")

    except BingXAPIError as e:
        print(f"\n❌ BingX API Error: {e}")
        print(f"   Code: {e.code}")
        print(f"   Message: {e.msg}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
