#!/usr/bin/env python3
"""
Test Stop-Loss and Take-Profit using separate orders
This is the recommended approach for BingX
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient, BingXAPIError
from config import load_config

async def main():
    print("="*70)
    print("BingX Stop-Loss & Take-Profit Test")
    print("="*70)

    config = load_config('config.yaml')
    client = BingXClient(
        config.bingx.api_key,
        config.bingx.api_secret,
        config.bingx.testnet
    )

    try:
        # Get current price
        ticker = await client.get_ticker("FARTCOIN-USDT")
        current_price = float(ticker.get('price') or ticker.get('lastPrice'))
        print(f"\nCurrent FARTCOIN price: ${current_price}")

        # Strategy: Open position with market order, then set SL/TP
        quantity = 6

        # Calculate SL and TP prices
        # Stop-Loss: 2% below entry
        # Take-Profit: 5% above entry
        stop_loss_price = round(current_price * 0.98, 4)
        take_profit_price = round(current_price * 1.05, 4)

        print(f"\n📊 Trade Setup:")
        print(f"   Entry: ${current_price} (market)")
        print(f"   Quantity: {quantity} FARTCOIN")
        print(f"   Stop-Loss: ${stop_loss_price} (-2%)")
        print(f"   Take-Profit: ${take_profit_price} (+5%)")

        # Step 1: Open position with market order
        print(f"\n{'='*70}")
        print("STEP 1: Opening Position (Market BUY)")
        print("="*70)

        entry_order = await client.place_order(
            symbol="FARTCOIN-USDT",
            side="BUY",
            position_side="BOTH",
            order_type="MARKET",
            quantity=quantity
        )

        if isinstance(entry_order, dict) and 'order' in entry_order:
            order_data = entry_order['order']
            entry_order_id = order_data.get('orderId')
            print(f"✓ Position opened!")
            print(f"   Order ID: {entry_order_id}")
            print(f"   Status: {order_data.get('status')}")
            print(f"   Filled: {order_data.get('executedQty')} FARTCOIN")

        # Wait for order to settle
        await asyncio.sleep(2)

        # Check position
        positions = await client.get_positions("FARTCOIN-USDT")
        position = None
        for pos in positions:
            if float(pos.get('positionAmt', 0)) != 0:
                position = pos
                print(f"\n✓ Position confirmed:")
                print(f"   Amount: {pos.get('positionAmt')} FARTCOIN")
                print(f"   Entry Price: ${pos.get('entryPrice')}")

        # Step 2: Place Stop-Loss order
        print(f"\n{'='*70}")
        print("STEP 2: Placing Stop-Loss Order")
        print("="*70)

        try:
            stop_loss_order = await client.place_order(
                symbol="FARTCOIN-USDT",
                side="SELL",  # Close long position
                position_side="BOTH",
                order_type="STOP_MARKET",
                quantity=quantity,
                stop_price=stop_loss_price,
                reduce_only=True  # Only close existing position
            )

            if isinstance(stop_loss_order, dict) and 'order' in stop_loss_order:
                sl_data = stop_loss_order['order']
                sl_order_id = sl_data.get('orderId')
                print(f"✓ Stop-Loss order placed!")
                print(f"   Order ID: {sl_order_id}")
                print(f"   Trigger Price: ${sl_data.get('stopPrice')}")
                print(f"   Status: {sl_data.get('status')}")
        except BingXAPIError as e:
            print(f"⚠️  Stop-Loss error: {e}")
            print(f"   Note: {e.msg}")

        # Step 3: Place Take-Profit order
        print(f"\n{'='*70}")
        print("STEP 3: Placing Take-Profit Order")
        print("="*70)

        try:
            take_profit_order = await client.place_order(
                symbol="FARTCOIN-USDT",
                side="SELL",  # Close long position
                position_side="BOTH",
                order_type="TAKE_PROFIT_MARKET",
                quantity=quantity,
                stop_price=take_profit_price,
                reduce_only=True  # Only close existing position
            )

            if isinstance(take_profit_order, dict) and 'order' in take_profit_order:
                tp_data = take_profit_order['order']
                tp_order_id = tp_data.get('orderId')
                print(f"✓ Take-Profit order placed!")
                print(f"   Order ID: {tp_order_id}")
                print(f"   Trigger Price: ${tp_data.get('stopPrice')}")
                print(f"   Status: {tp_data.get('status')}")
        except BingXAPIError as e:
            print(f"⚠️  Take-Profit error: {e}")
            print(f"   Note: {e.msg}")

        # Step 4: Check all orders
        print(f"\n{'='*70}")
        print("STEP 4: Verifying Orders")
        print("="*70)

        open_orders = await client.get_open_orders("FARTCOIN-USDT")
        print(f"\nOpen orders: {len(open_orders)}")
        for order in open_orders:
            print(f"   {order.get('type')} - {order.get('side')} "
                  f"{order.get('origQty')} @ ${order.get('price') or order.get('stopPrice')}")

        # Step 5: Clean up - close position
        print(f"\n{'='*70}")
        print("STEP 5: Cleanup - Closing Position")
        print("="*70)

        # Cancel all pending orders first
        await client.cancel_all_orders("FARTCOIN-USDT")
        print("✓ All pending orders cancelled")

        # Close position with market sell
        close_order = await client.place_order(
            symbol="FARTCOIN-USDT",
            side="SELL",
            position_side="BOTH",
            order_type="MARKET",
            quantity=quantity
        )

        print("✓ Position closed")

        # Final verification
        await asyncio.sleep(2)

        positions = await client.get_positions("FARTCOIN-USDT")
        open_pos = [p for p in positions if float(p.get('positionAmt', 0)) != 0]

        if len(open_pos) == 0:
            print("\n✅ Position fully closed - test complete!")
        else:
            print(f"\n⚠️  {len(open_pos)} positions still open")

        print(f"\n{'='*70}")
        print("📊 SUMMARY")
        print("="*70)
        print("\n✅ What we tested:")
        print("   1. Market entry order")
        print("   2. Stop-loss with STOP_MARKET")
        print("   3. Take-profit with TAKE_PROFIT_MARKET")
        print("   4. Order management")
        print("   5. Position closing")

        print("\n💡 For your trading bot:")
        print("   • Use this 3-order approach for each trade")
        print("   • Entry -> immediately place SL -> immediately place TP")
        print("   • Use reduce_only=True for SL/TP to prevent reversals")
        print("   • Monitor orders and update trailing stops in code")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
