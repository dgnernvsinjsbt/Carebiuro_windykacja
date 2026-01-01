#!/usr/bin/env python3
"""
BingX Connection Test Script

Tests all BingX API endpoints to ensure integration is working correctly.
Run this before deploying to production.
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient, BingXAPIError
from data.websocket_feed import BingXWebSocketFeed
from config import load_config


async def test_market_data(client: BingXClient, symbol: str = "BTC-USDT"):
    """Test market data endpoints"""
    print("\n=== Testing Market Data ===")

    try:
        # Test ticker
        print(f"\n1. Getting ticker for {symbol}...")
        ticker = await client.get_ticker(symbol)
        print(f"   ✓ Last Price: {ticker.get('lastPrice', 'N/A')}")

        # Test klines
        print(f"\n2. Getting klines for {symbol}...")
        klines = await client.get_klines(symbol, "1m", limit=10)
        if klines:
            last_candle = klines[-1]
            print(f"   ✓ Got {len(klines)} candles")
            print(f"   ✓ Last Close: {last_candle.get('close', 'N/A')}")
        else:
            print(f"   ⚠ No klines returned")

        # Test orderbook
        print(f"\n3. Getting orderbook for {symbol}...")
        orderbook = await client.get_orderbook(symbol, limit=5)
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        if bids and asks:
            print(f"   ✓ Best Bid: {bids[0][0] if bids else 'N/A'}")
            print(f"   ✓ Best Ask: {asks[0][0] if asks else 'N/A'}")
        else:
            print(f"   ⚠ Orderbook empty")

        # Test recent trades
        print(f"\n4. Getting recent trades for {symbol}...")
        trades = await client.get_recent_trades(symbol, limit=5)
        if trades:
            print(f"   ✓ Got {len(trades)} recent trades")
        else:
            print(f"   ⚠ No trades returned")

        # Test contract info
        print(f"\n5. Getting contract info for {symbol}...")
        contracts = await client.get_contract_info(symbol)
        if contracts:
            print(f"   ✓ Got {len(contracts)} contract(s)")
        else:
            print(f"   ⚠ No contracts returned")

        print("\n✓ Market data tests passed")
        return True

    except BingXAPIError as e:
        print(f"   ✗ API Error: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


async def test_account_endpoints(client: BingXClient):
    """Test account endpoints (requires API key)"""
    print("\n=== Testing Account Endpoints ===")

    try:
        # Test balance
        print("\n1. Getting account balance...")
        balance = await client.get_balance()
        if balance:
            print(f"   ✓ Balance retrieved")
            # Print USDT balance if available
            if 'balance' in balance:
                bal_data = balance['balance']
                print(f"   ✓ Asset: {bal_data.get('asset', 'N/A')}")
                print(f"   ✓ Available: {bal_data.get('balance', 'N/A')}")
        else:
            print(f"   ⚠ No balance data")

        # Test positions
        print("\n2. Getting positions...")
        positions = await client.get_positions()
        print(f"   ✓ Open Positions: {len(positions)}")
        if positions:
            for pos in positions[:3]:  # Show first 3
                print(f"      - {pos.get('symbol')} {pos.get('positionSide')}: {pos.get('positionAmt')}")

        # Test open orders
        print("\n3. Getting open orders...")
        orders = await client.get_open_orders()
        print(f"   ✓ Open Orders: {len(orders)}")

        print("\n✓ Account endpoint tests passed")
        return True

    except BingXAPIError as e:
        print(f"   ✗ API Error: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


async def test_websocket(symbol: str = "BTC-USDT", duration: int = 10):
    """Test WebSocket feed"""
    print("\n=== Testing WebSocket Feed ===")

    message_count = 0

    def on_kline(data):
        nonlocal message_count
        message_count += 1
        if message_count == 1:
            print(f"   ✓ First kline received: {data}")

    def on_message(data):
        if 'pong' not in data:
            print(f"   → Message: {data.get('dataType', 'unknown')}")

    try:
        # Create WebSocket feed
        ws = BingXWebSocketFeed(
            testnet=True,
            on_kline=on_kline,
            on_message=on_message
        )

        # Subscribe to kline stream
        print(f"\n1. Subscribing to {symbol} 1m klines...")
        await ws.subscribe('kline', symbol, '1m')

        # Start feed
        print(f"2. Listening for {duration} seconds...")
        listen_task = asyncio.create_task(ws.start())

        # Wait for specified duration
        await asyncio.sleep(duration)

        # Stop feed
        await ws.stop()

        # Cancel listen task
        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            pass

        if message_count > 0:
            print(f"\n✓ WebSocket test passed ({message_count} messages received)")
            return True
        else:
            print("\n⚠ WebSocket connected but no messages received")
            return False

    except Exception as e:
        print(f"\n✗ WebSocket Error: {e}")
        return False


async def test_trading_endpoints(client: BingXClient, symbol: str = "BTC-USDT"):
    """Test trading endpoints (TESTNET ONLY - places and cancels test order)"""
    print("\n=== Testing Trading Endpoints (Testnet) ===")

    if not client.testnet:
        print("⚠ SKIPPED: Only run trading tests on testnet!")
        return True

    try:
        # Get current price
        ticker = await client.get_ticker(symbol)
        current_price = float(ticker.get('lastPrice', 0))

        if current_price == 0:
            print("✗ Could not get current price")
            return False

        # Place a test limit order far from current price (won't fill)
        test_price = current_price * 0.5  # 50% below market
        test_qty = 0.001  # Small amount

        print(f"\n1. Placing test LIMIT order...")
        print(f"   Symbol: {symbol}")
        print(f"   Side: BUY")
        print(f"   Price: {test_price:.2f} (current: {current_price:.2f})")
        print(f"   Quantity: {test_qty}")

        order = await client.place_order(
            symbol=symbol,
            side="BUY",
            position_side="LONG",
            order_type="LIMIT",
            quantity=test_qty,
            price=test_price
        )

        order_id = order.get('orderId')
        print(f"   ✓ Order placed: ID {order_id}")

        # Query order
        print(f"\n2. Querying order {order_id}...")
        order_info = await client.get_order(symbol, order_id)
        print(f"   ✓ Order status: {order_info.get('status', 'UNKNOWN')}")

        # Cancel order
        print(f"\n3. Cancelling order {order_id}...")
        cancel_result = await client.cancel_order(symbol, order_id)
        print(f"   ✓ Order cancelled")

        print("\n✓ Trading endpoint tests passed")
        return True

    except BingXAPIError as e:
        print(f"   ✗ API Error: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("=" * 70)
    print("BingX API Integration Test")
    print("=" * 70)

    # Load config
    try:
        config = load_config('config.yaml')
        api_key = config.bingx.api_key
        api_secret = config.bingx.api_secret
        testnet = config.bingx.testnet
    except Exception as e:
        print(f"\n✗ Error loading config: {e}")
        print("\nPlease ensure config.yaml exists with BingX credentials:")
        print("  bingx:")
        print("    api_key: YOUR_KEY")
        print("    api_secret: YOUR_SECRET")
        print("    testnet: true")
        return 1

    # Validate credentials
    if api_key == "YOUR_API_KEY_HERE" or not api_key:
        print("\n✗ Please configure BingX API credentials in config.yaml")
        return 1

    print(f"\nTestnet Mode: {testnet}")
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")

    # Create client
    client = BingXClient(api_key, api_secret, testnet)

    # Test symbol
    test_symbol = "BTC-USDT"

    # Run tests
    results = {}

    # 1. Test connectivity
    print("\n=== Testing Connectivity ===")
    ping_result = await client.ping()
    results['connectivity'] = ping_result
    if ping_result:
        print("✓ API connectivity OK")
    else:
        print("✗ API connectivity FAILED")
        return 1

    # 2. Test market data
    results['market_data'] = await test_market_data(client, test_symbol)

    # 3. Test account endpoints
    results['account'] = await test_account_endpoints(client)

    # 4. Test WebSocket (optional - takes 10 seconds)
    print("\n" + "=" * 70)
    run_ws_test = input("Run WebSocket test? (takes 10 seconds) [y/N]: ").strip().lower()
    if run_ws_test == 'y':
        results['websocket'] = await test_websocket(test_symbol, duration=10)
    else:
        print("WebSocket test skipped")
        results['websocket'] = None

    # 5. Test trading (testnet only)
    if testnet:
        print("\n" + "=" * 70)
        run_trading_test = input("Run trading test? (places and cancels test order) [y/N]: ").strip().lower()
        if run_trading_test == 'y':
            results['trading'] = await test_trading_endpoints(client, test_symbol)
        else:
            print("Trading test skipped")
            results['trading'] = None
    else:
        print("\n⚠ Trading tests skipped (only available on testnet)")
        results['trading'] = None

    # Close client
    await client.close()

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, result in results.items():
        if result is None:
            status = "⊘ SKIPPED"
        elif result:
            status = "✓ PASSED"
        else:
            status = "✗ FAILED"

        print(f"{test_name.upper():20} {status}")

    # Overall result
    failed_tests = [k for k, v in results.items() if v is False]

    print("=" * 70)

    if failed_tests:
        print(f"\n✗ {len(failed_tests)} test(s) FAILED: {', '.join(failed_tests)}")
        return 1
    else:
        print("\n✓ All tests PASSED!")
        print("\nYou can now deploy the trading engine.")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
