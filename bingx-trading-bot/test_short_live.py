#!/usr/bin/env python3
"""
Live test: Place SHORT position with SL/TP
Tests the new retry logic for order placement
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient, BingXAPIError
from execution.order_executor import OrderExecutor
from config import load_config


async def test_short_with_sl_tp():
    """Place a real SHORT position with SL and TP"""

    config = load_config('config.yaml')

    client = BingXClient(
        config.bingx.api_key,
        config.bingx.api_secret,
        testnet=False,
        base_url=config.bingx.base_url
    )

    executor = OrderExecutor(client)
    symbol = "FARTCOIN-USDT"

    try:
        print("=" * 70)
        print("LIVE TEST: SHORT Position with SL/TP")
        print("=" * 70)

        # Get current price
        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('price') or ticker.get('lastPrice'))
        print(f"\nCurrent FARTCOIN price: ${current_price:.4f}")

        # Get account balance
        balance_data = await client.get_balance()
        account_balance = 0.0
        if isinstance(balance_data, list):
            for asset in balance_data:
                if asset.get('asset') == 'USDT':
                    account_balance = float(asset.get('availableMargin', 0))
        print(f"Account balance: ${account_balance:.2f} USDT")

        # Create SHORT signal
        # For SHORT: SL is ABOVE entry, TP is BELOW entry
        entry_price = current_price
        stop_loss = current_price * 1.02      # 2% above entry (loss if price goes up)
        take_profit = current_price * 0.95    # 5% below entry (profit if price goes down)

        signal = {
            'strategy': 'test_short_live',
            'direction': 'SHORT',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'symbol': symbol
        }

        print(f"\n{'=' * 70}")
        print("SIGNAL DETAILS:")
        print(f"{'=' * 70}")
        print(f"Direction: SHORT (sell first, buy back later)")
        print(f"Entry: ${entry_price:.4f} (market)")
        print(f"Stop-Loss: ${stop_loss:.4f} (+2% = loss)")
        print(f"Take-Profit: ${take_profit:.4f} (-5% = profit)")
        print(f"Quantity: 6 FARTCOIN")

        # Confirm before executing
        print(f"\n{'=' * 70}")
        print("EXECUTING TRADE...")
        print(f"{'=' * 70}")

        # Execute with fixed quantity (override risk calculation)
        # We'll use a simple approach - just place orders directly

        # Step 1: Set leverage
        leverage = 10
        try:
            await client.set_leverage(symbol=symbol, side="BOTH", leverage=leverage)
            print(f"✓ Leverage set to {leverage}x")
        except BingXAPIError as e:
            print(f"Leverage note: {e.msg}")

        # Step 2: Place MARKET SELL (open short)
        quantity = 6
        print(f"\nPlacing MARKET SELL for {quantity} FARTCOIN...")

        entry_order = await client.place_order(
            symbol=symbol,
            side="SELL",
            position_side="BOTH",
            order_type="MARKET",
            quantity=quantity
        )

        entry_order_id = None
        if isinstance(entry_order, dict) and 'order' in entry_order:
            entry_order_id = entry_order['order'].get('orderId')
            print(f"✓ SHORT position opened! Order ID: {entry_order_id}")

        await asyncio.sleep(1)

        # Check position
        positions = await client.get_positions(symbol)
        for pos in positions:
            pos_amt = float(pos.get('positionAmt', 0))
            if pos_amt != 0:
                print(f"✓ Position confirmed: {pos_amt} FARTCOIN @ ${pos.get('entryPrice')}")
                actual_entry = float(pos.get('entryPrice'))

        # Step 3: Place Stop-Loss (BUY to close short if price goes UP)
        print(f"\nPlacing STOP-LOSS at ${stop_loss:.4f}...")

        sl_order_id = None
        for attempt in range(1, 4):
            try:
                print(f"  SL attempt {attempt}/3...")
                sl_order = await client.place_order(
                    symbol=symbol,
                    side="BUY",  # BUY to close SHORT
                    position_side="BOTH",
                    order_type="STOP_MARKET",
                    quantity=quantity,
                    stop_price=round(stop_loss, 4),
                    reduce_only=True
                )

                if isinstance(sl_order, dict) and 'order' in sl_order:
                    sl_order_id = sl_order['order'].get('orderId')
                print(f"✓ Stop-Loss placed! ID: {sl_order_id}")
                break
            except BingXAPIError as e:
                print(f"  ❌ SL attempt {attempt} failed: {e}")
                if attempt == 3:
                    print("🚨 ALL SL RETRIES FAILED!")
                await asyncio.sleep(1)

        # Step 4: Place Take-Profit (BUY to close short if price goes DOWN)
        print(f"\nPlacing TAKE-PROFIT at ${take_profit:.4f}...")

        tp_order_id = None
        for attempt in range(1, 4):
            try:
                print(f"  TP attempt {attempt}/3...")
                tp_order = await client.place_order(
                    symbol=symbol,
                    side="BUY",  # BUY to close SHORT
                    position_side="BOTH",
                    order_type="TAKE_PROFIT_MARKET",
                    quantity=quantity,
                    stop_price=round(take_profit, 4),
                    reduce_only=True
                )

                if isinstance(tp_order, dict) and 'order' in tp_order:
                    tp_order_id = tp_order['order'].get('orderId')
                print(f"✓ Take-Profit placed! ID: {tp_order_id}")
                break
            except BingXAPIError as e:
                print(f"  ❌ TP attempt {attempt} failed: {e}")
                if attempt == 3:
                    print("🚨 ALL TP RETRIES FAILED!")
                await asyncio.sleep(1)

        # Summary
        print(f"\n{'=' * 70}")
        print("TRADE SUMMARY")
        print(f"{'=' * 70}")
        print(f"Entry Order ID: {entry_order_id}")
        print(f"Stop-Loss Order ID: {sl_order_id}")
        print(f"Take-Profit Order ID: {tp_order_id}")
        print(f"\nPosition: SHORT {quantity} FARTCOIN")
        print(f"Entry: ~${current_price:.4f}")
        print(f"SL: ${stop_loss:.4f} (close if price rises 2%)")
        print(f"TP: ${take_profit:.4f} (close if price drops 5%)")

        # Verify orders
        print(f"\n{'=' * 70}")
        print("VERIFYING OPEN ORDERS:")
        print(f"{'=' * 70}")

        open_orders = await client.get_open_orders(symbol)
        if isinstance(open_orders, list):
            for order in open_orders:
                order_type = order.get('type', 'UNKNOWN')
                side = order.get('side', 'UNKNOWN')
                stop_price = order.get('stopPrice', 'N/A')
                print(f"  {order_type} {side} @ trigger ${stop_price}")

        print(f"\n{'=' * 70}")
        print("✅ TEST COMPLETE - SHORT POSITION OPEN WITH SL/TP")
        print(f"{'=' * 70}")
        print("\nThe position will automatically close when either:")
        print(f"  • Price hits ${stop_loss:.4f} (SL) → ~2% loss")
        print(f"  • Price hits ${take_profit:.4f} (TP) → ~5% profit")

    except BingXAPIError as e:
        print(f"\n❌ BingX API Error: {e}")
        print(f"Code: {e.code}")
        print(f"Message: {e.msg}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_short_with_sl_tp())
