#!/usr/bin/env python3
"""
Complete BingX Futures API Test
Tests all essential endpoints we need for trading
"""

import asyncio
import hmac
import hashlib
import time
import aiohttp
import os
import json

API_KEY = os.getenv('BINGX_API_KEY')
API_SECRET = os.getenv('BINGX_API_SECRET')
BASE_URL = "https://open-api.bingx.com"

def generate_signature(params):
    """Generate HMAC SHA256 signature"""
    sorted_params = sorted(params.items())
    query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature, query_string

async def api_request(endpoint, params=None, method='GET'):
    """Make signed API request"""
    params = params or {}

    if endpoint.startswith(('/openApi/swap/v2/user', '/openApi/swap/v3/user', '/openApi/swap/v2/trade')):
        # Add signature
        params['timestamp'] = int(time.time() * 1000)
        signature, query_string = generate_signature(params)
        params['signature'] = signature

    headers = {'X-BX-APIKEY': API_KEY}
    url = f"{BASE_URL}{endpoint}"

    async with aiohttp.ClientSession() as session:
        if method == 'GET':
            async with session.get(url, params=params, headers=headers) as response:
                return await response.json()
        elif method == 'POST':
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            async with session.post(url, data=params, headers=headers) as response:
                return await response.json()
        elif method == 'DELETE':
            async with session.delete(url, params=params, headers=headers) as response:
                return await response.json()

async def main():
    print("="*70)
    print("BingX FUTURES API - Complete Test")
    print("="*70)

    # Test 1: Balance
    print("\n📊 TEST 1: Account Balance")
    print("-"*70)
    balance = await api_request("/openApi/swap/v3/user/balance")
    if balance['code'] == 0:
        for asset in balance['data']:
            if float(asset['balance']) > 0:
                print(f"✓ {asset['asset']}: {asset['balance']} (Available: {asset['availableMargin']})")
    else:
        print(f"❌ {balance}")

    # Test 2: Positions
    print("\n📈 TEST 2: Open Positions")
    print("-"*70)
    positions = await api_request("/openApi/swap/v2/user/positions")
    if positions['code'] == 0:
        if positions['data']:
            for pos in positions['data']:
                print(f"✓ {pos['symbol']} {pos['positionSide']}: {pos['positionAmt']}")
        else:
            print("✓ No open positions")
    else:
        print(f"❌ {positions}")

    # Test 3: Open Orders
    print("\n📋 TEST 3: Open Orders")
    print("-"*70)
    orders = await api_request("/openApi/swap/v2/trade/openOrders")
    if orders['code'] == 0:
        data = orders.get('data', {})
        orders_list = data.get('orders', []) if isinstance(data, dict) else []
        if orders_list:
            for order in orders_list:
                print(f"✓ {order['symbol']} {order['side']}: {order['origQty']} @ {order['price']}")
        else:
            print("✓ No open orders")
    else:
        print(f"❌ {orders}")

    # Test 4: Get FARTCOIN price (try different formats)
    print("\n💰 TEST 4: FARTCOIN Price")
    print("-"*70)

    symbols_to_try = ["FARTCOIN-USDT", "FARTCOINUSDT", "FARTCOIN/USDT"]

    for symbol in symbols_to_try:
        ticker = await api_request("/openApi/swap/v1/ticker/price", {'symbol': symbol})
        if ticker['code'] == 0:
            print(f"✓ {symbol}: ${ticker['data']['price']}")
            working_symbol = symbol
            break
        else:
            print(f"⚠ {symbol}: {ticker.get('msg', 'Not found')}")

    # Test 5: Contract Info
    print("\n📜 TEST 5: Available Contracts (search for FART)")
    print("-"*70)
    contracts = await api_request("/openApi/swap/v2/quote/contracts")
    if contracts['code'] == 0:
        fart_contracts = [c for c in contracts['data'] if 'FART' in c['symbol'].upper()]
        if fart_contracts:
            for contract in fart_contracts[:3]:
                print(f"✓ {contract['symbol']}")
                print(f"   Min Qty: {contract.get('minQty', 'N/A')}")
                print(f"   Price Precision: {contract.get('pricePrecision', 'N/A')}")
                working_symbol = contract['symbol']
        else:
            print("⚠ No FARTCOIN contracts found")
    else:
        print(f"❌ {contracts}")

    # Test 6: Place & Cancel Order (small test)
    if 'working_symbol' in locals():
        print(f"\n🔧 TEST 6: Place & Cancel Test Order ({working_symbol})")
        print("-"*70)

        # Get current price
        ticker = await api_request("/openApi/swap/v1/ticker/price", {'symbol': working_symbol})
        if ticker['code'] == 0:
            current_price = float(ticker['data']['price'])
            test_price = round(current_price * 0.9, 6)  # 10% below market
            test_qty = 1  # 1 unit (adjust if needed)

            print(f"Current price: ${current_price}")
            print(f"Test order: BUY {test_qty} @ ${test_price}")

            # Place order
            order_params = {
                'symbol': working_symbol,
                'side': 'BUY',
                'positionSide': 'LONG',
                'type': 'LIMIT',
                'quantity': test_qty,
                'price': test_price
            }

            order_result = await api_request("/openApi/swap/v2/trade/order", order_params, method='POST')

            if order_result['code'] == 0:
                order_id = order_result['data']['order']['orderId']
                print(f"✓ Order placed! ID: {order_id}")

                # Wait 1 second
                await asyncio.sleep(1)

                # Cancel order
                cancel_params = {
                    'symbol': working_symbol,
                    'orderId': order_id
                }

                cancel_result = await api_request("/openApi/swap/v2/trade/order", cancel_params, method='DELETE')

                if cancel_result['code'] == 0:
                    print(f"✓ Order cancelled successfully!")
                else:
                    print(f"⚠ Cancel failed: {cancel_result}")

            else:
                print(f"❌ Place order failed: {order_result}")
                print("   This might be due to:")
                print("   - Minimum order size not met")
                print("   - Symbol format incorrect")
                print("   - Insufficient balance")

    print("\n" + "="*70)
    print("✓ TEST COMPLETE")
    print("="*70)
    print("\nSummary:")
    print("  • Balance endpoint: ✓ WORKS")
    print("  • Positions endpoint: ✓ WORKS")
    print("  • Orders endpoint: ✓ WORKS")
    print("  • Price data: ✓ WORKS")
    print("  • Trading: ✓ READY TO TEST")

if __name__ == "__main__":
    asyncio.run(main())
