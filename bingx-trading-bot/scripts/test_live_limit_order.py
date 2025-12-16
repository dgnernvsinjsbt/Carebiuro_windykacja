"""
Test Live Limit Order with TP/SL

This script places a small test limit SHORT order on BingX with:
- Entry: Limit order above current price
- Stop Loss: Above entry price
- Take Profit: Below entry price

Uses minimum position size to minimize risk.
"""

import asyncio
import os
from execution.bingx_client import BingXClient
from datetime import datetime

async def test_limit_order():
    # Initialize BingX client
    api_key = os.getenv('BINGX_API_KEY')
    api_secret = os.getenv('BINGX_API_SECRET')

    if not api_key or not api_secret:
        print("❌ Error: BINGX_API_KEY and BINGX_API_SECRET must be set")
        return

    client = BingXClient(api_key, api_secret, testnet=False)

    # Test symbol - DOGE (best performer in backtest)
    symbol = 'DOGE-USDT'

    print("=" * 70)
    print("🧪 TESTING LIVE LIMIT ORDER WITH TP/SL")
    print("=" * 70)
    print(f"Symbol: {symbol}")
    print(f"Direction: SHORT")
    print(f"Order Type: LIMIT")
    print("")

    # Step 1: Get current price
    print("📊 Fetching current price...")
    ticker = await client.get_ticker(symbol)
    if not ticker:
        print("❌ Failed to get ticker data")
        return

    print(f"DEBUG: Ticker response: {ticker}")

    # Try different field names (BingX API varies)
    if 'lastPrice' in ticker:
        current_price = float(ticker['lastPrice'])
    elif 'last' in ticker:
        current_price = float(ticker['last'])
    elif 'price' in ticker:
        current_price = float(ticker['price'])
    else:
        print(f"❌ Could not find price in ticker: {ticker.keys()}")
        return

    print(f"Current Price: ${current_price:.6f}")
    print("")

    # Step 2: Calculate order parameters
    # For SHORT limit order: place order slightly ABOVE current price (wait for price to go up)
    limit_price = current_price * 1.002  # 0.2% above current (conservative)
    stop_loss = limit_price * 1.01      # 1% above entry (risk 1%)
    take_profit = limit_price * 0.995   # 0.5% below entry (profit 0.5%)

    # Calculate minimum quantity (BingX minimum ~$6 worth)
    min_notional = 6.0  # $6 minimum
    quantity = round(min_notional / limit_price, 2)  # Round to 2 decimals for DOGE

    print("💰 Order Parameters:")
    print(f"Limit Price: ${limit_price:.6f} (+0.2% from current)")
    print(f"Stop Loss:   ${stop_loss:.6f} (+1.0% from entry)")
    print(f"Take Profit: ${take_profit:.6f} (-0.5% from entry)")
    print(f"Quantity:    {quantity} DOGE")
    print(f"Notional:    ${quantity * limit_price:.2f}")
    print("")

    # Step 3: Confirm with user
    print("⚠️  THIS WILL PLACE A REAL ORDER ON BINGX PERPETUAL FUTURES")
    print("Press ENTER to confirm, or Ctrl+C to cancel...")
    input()

    # Step 4: Place limit order with TP and SL
    print("📤 Placing limit SHORT order with TP/SL...")
    try:
        # Create stop loss config (use STOP_MARKET type)
        stop_loss_config = {
            "type": "STOP_MARKET",
            "stopPrice": round(stop_loss, 6),
            "workingType": "MARK_PRICE"
        }

        # Create take profit config (use TAKE_PROFIT_MARKET type)
        take_profit_config = {
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": round(take_profit, 6),
            "workingType": "MARK_PRICE"
        }

        order = await client.place_order(
            symbol=symbol,
            side='SELL',  # SELL for SHORT
            position_side='SHORT',
            order_type='LIMIT',
            quantity=quantity,
            price=limit_price,
            stop_loss=stop_loss_config,
            take_profit=take_profit_config,
            time_in_force='GTC'
        )

        # Handle response (can be nested under 'order' key)
        order_data = order.get('order', order) if isinstance(order, dict) else {}

        if not order_data or 'orderId' not in order_data:
            print(f"❌ Failed to place order: {order}")
            return

        order_id = order_data['orderId']
        order_status = order_data.get('status', 'UNKNOWN')

        print(f"✅ Limit order placed successfully!")
        print(f"Order ID: {order_id}")
        print(f"Status: {order_status}")
        print(f"✅ Stop loss set at ${stop_loss:.6f}")
        print(f"✅ Take profit set at ${take_profit:.6f}")
        print("")

        # Step 7: Show summary
        print("=" * 70)
        print("📋 ORDER SUMMARY")
        print("=" * 70)
        print(f"Status: PENDING (waiting for price to reach ${limit_price:.6f})")
        print(f"If filled:")
        print(f"  - Entry: ${limit_price:.6f}")
        print(f"  - SL:    ${stop_loss:.6f} (Risk: 1.0%)")
        print(f"  - TP:    ${take_profit:.6f} (Profit: 0.5%)")
        print(f"  - R:R:   1:0.5")
        print("")
        print("Next steps:")
        print("1. Monitor order status in BingX interface")
        print("2. Wait for price to reach limit price for fill")
        print("3. If filled, position will auto-close at TP or SL")
        print("")
        print(f"To cancel: use order ID {order_id}")
        print("=" * 70)

    except Exception as e:
        print(f"❌ Error placing order: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_limit_order())
