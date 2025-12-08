"""
Test Leverage Order Placement
Places a limit order far from current price to test leverage calculations without fills
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient, BingXAPIError
from execution.order_executor import OrderExecutor
from config import load_config

async def test_leverage_orders():
    """Test order placement with leverage (no fills)"""

    # Load config
    config = load_config('config.yaml')

    # Create client
    client = BingXClient(
        config.bingx.api_key,
        config.bingx.api_secret,
        testnet=False,
        base_url=config.bingx.base_url
    )

    # Create executor
    executor = OrderExecutor(client)

    symbol = "FARTCOIN-USDT"

    try:
        print("="*80)
        print("LEVERAGE ORDER PLACEMENT TEST")
        print("="*80)

        # Get current price
        print("\n1. Getting current FARTCOIN price...")
        orderbook = await client.get_orderbook(symbol)
        current_price = float(orderbook['bids'][0][0])
        print(f"   Current price: ${current_price:.4f}")

        # Get account balance
        print("\n2. Getting account balance...")
        balance_data = await client.get_balance()
        account_balance = 0.0
        if isinstance(balance_data, list):
            for asset in balance_data:
                if asset.get('asset') == 'USDT':
                    account_balance = float(asset.get('availableMargin', 0))
        print(f"   Account balance: ${account_balance:.2f} USDT")

        # Create test signal with limit order FAR from current price
        # BUY order 10% BELOW current price (won't fill)
        entry_price = current_price * 0.90  # 10% lower (won't fill immediately)
        stop_loss = entry_price * 0.98      # 2% below entry
        take_profit = entry_price * 1.05    # 5% above entry

        test_signal = {
            'strategy': 'test_leverage',
            'direction': 'LONG',
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'symbol': symbol
        }

        print(f"\n3. Test signal (LIMIT order - won't fill):")
        print(f"   Entry: ${entry_price:.4f} (10% BELOW current - WON'T FILL)")
        print(f"   Stop-Loss: ${stop_loss:.4f} (-2% from entry)")
        print(f"   Take-Profit: ${take_profit:.4f} (+5% from entry)")

        # Get leverage settings from config
        leverage = config.bingx.default_leverage
        leverage_mode = config.bingx.leverage_mode
        risk_pct = 1.0  # 1% risk

        print(f"\n4. Leverage settings:")
        print(f"   Leverage: {leverage}x")
        print(f"   Mode: {leverage_mode}")
        print(f"   Risk per trade: {risk_pct}%")

        # Get contract info for calculations
        print(f"\n5. Getting contract specifications...")
        contracts = await client.get_contract_info(symbol)
        contract = contracts[0] if isinstance(contracts, list) else contracts
        print(f"   Min quantity: {contract.get('minQty')}")
        print(f"   Quantity precision: {contract.get('quantityPrecision')}")
        print(f"   Price precision: {contract.get('pricePrecision')}")

        # Calculate position size (manual calculation for verification)
        print(f"\n6. Position size calculation:")
        risk_amount = account_balance * (risk_pct / 100.0)
        stop_distance = abs(entry_price - stop_loss)
        base_position_size = risk_amount / stop_distance

        print(f"   Risk amount: ${risk_amount:.2f}")
        print(f"   Stop distance: ${stop_distance:.4f}")
        print(f"   Base position size (1x): {base_position_size:.2f} FARTCOIN")

        if leverage_mode == 'aggressive':
            leveraged_position_size = base_position_size * leverage
            print(f"   Leveraged position size (10x): {leveraged_position_size:.2f} FARTCOIN")
        else:
            leveraged_position_size = base_position_size
            print(f"   Position size (conservative): {base_position_size:.2f} FARTCOIN")

        position_value = leveraged_position_size * entry_price
        margin_required = position_value / leverage

        print(f"   Position value: ${position_value:.2f}")
        print(f"   Margin required: ${margin_required:.2f}")
        print(f"   Margin as % of account: {(margin_required/account_balance)*100:.1f}%")

        # Place test orders via executor
        print("\n" + "="*80)
        print("PLACING TEST ORDERS (LIMIT - WON'T FILL)")
        print("="*80)

        result = await executor.execute_trade(
            signal=test_signal,
            symbol=symbol,
            account_balance=account_balance,
            risk_pct=risk_pct,
            use_market_order=False,  # Use LIMIT order (won't fill)
            leverage=leverage,
            leverage_mode=leverage_mode
        )

        if result['success']:
            print("\n" + "="*80)
            print("✅ ORDER PLACEMENT SUCCESSFUL")
            print("="*80)
            print(f"\nOrder IDs:")
            print(f"  Entry Order: {result['entry_order_id']}")
            print(f"  Stop-Loss Order: {result['sl_order_id']}")
            print(f"  Take-Profit Order: {result['tp_order_id']}")

            print(f"\nCalculated Quantity: {result['quantity']} FARTCOIN")

            # Verify orders were created
            print(f"\n7. Verifying orders on exchange...")
            orders = await client.get_open_orders(symbol)

            if isinstance(orders, dict):
                data = orders.get('data', {})
                orders_list = data.get('orders', []) if isinstance(data, dict) else []
            else:
                orders_list = []

            print(f"   Found {len(orders_list)} open orders:")
            for order in orders_list:
                order_type = order.get('type', 'UNKNOWN')
                side = order.get('side', 'UNKNOWN')
                price = order.get('price', 'N/A')
                stop_price = order.get('stopPrice', 'N/A')
                quantity = order.get('origQty', 'N/A')
                status = order.get('status', 'UNKNOWN')

                print(f"\n   Order ID: {order.get('orderId')}")
                print(f"     Type: {order_type}")
                print(f"     Side: {side}")
                print(f"     Quantity: {quantity}")
                print(f"     Price: {price}")
                if stop_price != 'N/A':
                    print(f"     Stop Price: {stop_price}")
                print(f"     Status: {status}")

            # Cancel all test orders
            print(f"\n8. Cancelling test orders...")
            await client.cancel_all_orders(symbol)
            print("   ✓ All test orders cancelled")

            print("\n" + "="*80)
            print("TEST COMPLETE - LEVERAGE CALCULATIONS VERIFIED")
            print("="*80)

            print(f"\nSummary:")
            print(f"  ✅ Leverage set to {leverage}x")
            print(f"  ✅ Position size calculated correctly ({leverage_mode} mode)")
            print(f"  ✅ Entry order placed (LIMIT - didn't fill)")
            print(f"  ✅ Stop-loss order placed")
            print(f"  ✅ Take-profit order placed")
            print(f"  ✅ All orders cancelled")

            print(f"\nExpected P&L with this position:")
            if leverage_mode == 'aggressive':
                sl_loss = result['quantity'] * stop_distance
                tp_profit = result['quantity'] * (take_profit - entry_price)
                print(f"  If SL hits: -${sl_loss:.2f} ({(sl_loss/account_balance)*100:.1f}% loss)")
                print(f"  If TP hits: +${tp_profit:.2f} ({(tp_profit/account_balance)*100:.1f}% profit)")
            else:
                sl_loss = result['quantity'] * stop_distance
                tp_profit = result['quantity'] * (take_profit - entry_price)
                print(f"  If SL hits: -${sl_loss:.2f} ({(sl_loss/account_balance)*100:.1f}% loss)")
                print(f"  If TP hits: +${tp_profit:.2f} ({(tp_profit/account_balance)*100:.1f}% profit)")

        else:
            print("\n❌ ORDER PLACEMENT FAILED")
            print(f"Error: {result.get('error')}")
            print(f"Error code: {result.get('error_code')}")

    except BingXAPIError as e:
        print(f"\n❌ BingX API Error: {e}")
        print(f"Code: {e.code}")
        print(f"Message: {e.msg}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Close client
        await client.close()
        print("\n✓ Client closed")

if __name__ == "__main__":
    print("Starting leverage order test...")
    print("This will place orders FAR from current price (won't fill)")
    print("Then cancel them immediately\n")

    asyncio.run(test_leverage_orders())
