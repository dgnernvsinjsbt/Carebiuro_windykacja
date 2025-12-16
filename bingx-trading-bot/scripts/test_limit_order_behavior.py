"""
TEST: Czy BUY LIMIT powyżej ceny rynkowej czeka czy filluje natychmiast?

Uruchom na serwerze:
    cd ~/bingx-trading-bot && python3 test_limit_order_behavior.py

Test:
1. Pobierz aktualną cenę FARTCOIN
2. Złóż BUY LIMIT 1% POWYŻEJ ceny za ~$3 USDT
3. Sprawdź czy order czeka (status=NEW) czy filluje natychmiast (status=FILLED)
4. Jeśli czeka - cancel po 10 sekundach
"""

import asyncio
import yaml
from execution.bingx_client import BingXClient


async def test_limit_order_behavior():
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    api_key = config['bingx']['api_key']
    api_secret = config['bingx']['api_secret']

    client = BingXClient(api_key, api_secret, testnet=False, base_url='https://open-api.bingx.com')

    symbol = 'FARTCOIN-USDT'

    try:
        # 1. Get current price
        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('lastPrice', ticker.get('price', 0)))
        print(f"\n{'='*60}")
        print(f"CURRENT PRICE: ${current_price:.6f}")
        print(f"{'='*60}")

        # 2. Get contract info
        contracts = await client.get_contract_info(symbol)
        contract = contracts[0] if isinstance(contracts, list) else contracts
        min_qty = float(contract.get('minQty', 1))
        price_precision = contract.get('pricePrecision', 4)
        qty_precision = contract.get('quantityPrecision', 1)

        print(f"Min Qty: {min_qty}")
        print(f"Price Precision: {price_precision}")
        print(f"Qty Precision: {qty_precision}")

        # 3. Calculate limit price (1% ABOVE current)
        limit_price = round(current_price * 1.01, price_precision)

        # 4. Calculate quantity for ~$3 USDT
        target_usdt = 3.0
        quantity = round(target_usdt / limit_price, qty_precision)
        if quantity < min_qty:
            quantity = min_qty

        actual_value = quantity * limit_price

        print(f"\n{'='*60}")
        print(f"TEST ORDER:")
        print(f"{'='*60}")
        print(f"  Type: BUY LIMIT")
        print(f"  Direction: LONG")
        print(f"  Current Price: ${current_price:.6f}")
        print(f"  Limit Price:   ${limit_price:.6f} (1% ABOVE)")
        print(f"  Quantity:      {quantity}")
        print(f"  Value:         ${actual_value:.2f} USDT")
        print(f"{'='*60}")

        input("\nPress ENTER to place order (Ctrl+C to cancel)...")

        # 5. Place the limit order
        print("\nPlacing BUY LIMIT order...")

        order = await client.place_order(
            symbol=symbol,
            side="BUY",
            position_side="LONG",  # Hedge mode
            order_type="LIMIT",
            price=limit_price,
            quantity=quantity
        )

        print(f"\nRAW RESPONSE:")
        print(f"{order}")

        # Extract order info
        order_data = order.get('order', order)
        order_id = order_data.get('orderId') or order_data.get('orderID')
        status = order_data.get('status')
        avg_price = order_data.get('avgPrice', 'N/A')
        executed_qty = order_data.get('executedQty', '0')

        print(f"\n{'='*60}")
        print(f"ORDER RESULT:")
        print(f"{'='*60}")
        print(f"  Order ID: {order_id}")
        print(f"  Status:   {status}")
        print(f"  Avg Price: {avg_price}")
        print(f"  Executed Qty: {executed_qty}")

        if status == 'FILLED':
            print(f"\n  >>> ORDER FILLED IMMEDIATELY! <<<")
            print(f"  This means BUY LIMIT above market price fills instantly.")
            print(f"  Backtest assumption was WRONG.")

            # Close the position
            print(f"\nClosing position...")
            close_order = await client.place_order(
                symbol=symbol,
                side="SELL",
                position_side="LONG",
                order_type="MARKET",
                quantity=float(executed_qty) if executed_qty else quantity
            )
            print(f"Position closed: {close_order}")

        elif status == 'NEW':
            print(f"\n  >>> ORDER IS WAITING (not filled yet) <<<")
            print(f"  This means BUY LIMIT above market CAN wait.")
            print(f"  Backtest assumption might be correct!")

            # Wait a few seconds then check status
            print(f"\nWaiting 5 seconds to check status...")
            await asyncio.sleep(5)

            order_status = await client.get_order(symbol, order_id)
            new_status = order_status.get('status')
            print(f"Status after 5s: {new_status}")

            if new_status == 'NEW':
                # Cancel the order
                print(f"\nCancelling order...")
                await client.cancel_order(symbol, order_id)
                print(f"Order cancelled.")
            else:
                print(f"Order status changed to: {new_status}")
                # If filled, close position
                if new_status == 'FILLED':
                    close_order = await client.place_order(
                        symbol=symbol,
                        side="SELL",
                        position_side="LONG",
                        order_type="MARKET",
                        quantity=quantity
                    )
                    print(f"Position closed: {close_order}")
        else:
            print(f"\n  >>> UNEXPECTED STATUS: {status} <<<")

        print(f"\n{'='*60}")
        print(f"TEST COMPLETE")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.close()


if __name__ == '__main__':
    asyncio.run(test_limit_order_behavior())
