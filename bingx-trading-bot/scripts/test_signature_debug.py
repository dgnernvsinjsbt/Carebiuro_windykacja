#!/usr/bin/env python3
"""
Debug BingX API signature - test different approaches
"""

import asyncio
import hmac
import hashlib
import time
import aiohttp
import os

async def test_spot_balance():
    """Test SPOT balance endpoint (different from futures)"""

    api_key = os.getenv('BINGX_API_KEY')
    api_secret = os.getenv('BINGX_API_SECRET')

    print("="*70)
    print("Testing BingX SPOT API (not futures)")
    print("="*70)

    # SPOT API endpoints (different from swap/futures)
    base_url = "https://open-api.bingx.com"
    endpoint = "/openApi/spot/v1/account/balance"  # SPOT balance

    # Generate timestamp
    timestamp = int(time.time() * 1000)

    # Create params for signature
    params = {
        'timestamp': timestamp
    }

    # Generate signature (sorted params)
    sorted_params = sorted(params.items())
    query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])

    signature = hmac.new(
        api_secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Add signature to params
    params['signature'] = signature

    # Make request
    headers = {
        'X-BX-APIKEY': api_key
    }

    url = f"{base_url}{endpoint}"

    print(f"\n📍 Testing endpoint: {endpoint}")
    print(f"🔑 API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"⏱️  Timestamp: {timestamp}")
    print(f"📝 Query string: {query_string}")
    print(f"🔐 Signature: {signature[:16]}...{signature[-16:]}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers) as response:
                data = await response.json()

                print(f"\n✓ Response code: {data.get('code')}")
                print(f"✓ Response msg: {data.get('msg')}")

                if data.get('code') == 0:
                    print(f"✓ SUCCESS! Balance data:")
                    print(f"  {data.get('data')}")
                    return True
                else:
                    print(f"❌ API Error: {data}")
                    return False

        except Exception as e:
            print(f"❌ Error: {e}")
            return False

async def test_futures_balance():
    """Test FUTURES balance endpoint"""

    api_key = os.getenv('BINGX_API_KEY')
    api_secret = os.getenv('BINGX_API_SECRET')

    print("\n" + "="*70)
    print("Testing BingX FUTURES/SWAP API")
    print("="*70)

    # FUTURES API endpoints
    base_url = "https://open-api.bingx.com"
    endpoint = "/openApi/swap/v3/user/balance"  # FUTURES balance

    timestamp = int(time.time() * 1000)

    params = {
        'timestamp': timestamp
    }

    sorted_params = sorted(params.items())
    query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])

    signature = hmac.new(
        api_secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    params['signature'] = signature

    headers = {
        'X-BX-APIKEY': api_key
    }

    url = f"{base_url}{endpoint}"

    print(f"\n📍 Testing endpoint: {endpoint}")
    print(f"🔑 API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"⏱️  Timestamp: {timestamp}")
    print(f"📝 Query string: {query_string}")
    print(f"🔐 Signature: {signature[:16]}...{signature[-16:]}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers) as response:
                data = await response.json()

                print(f"\n✓ Response code: {data.get('code')}")
                print(f"✓ Response msg: {data.get('msg')}")

                if data.get('code') == 0:
                    print(f"✓ SUCCESS! Balance data:")
                    print(f"  {data.get('data')}")
                    return True
                else:
                    print(f"❌ API Error: {data}")
                    return False

        except Exception as e:
            print(f"❌ Error: {e}")
            return False

async def main():
    # Test both SPOT and FUTURES endpoints
    spot_result = await test_spot_balance()
    futures_result = await test_futures_balance()

    print("\n" + "="*70)
    print("RESULTS:")
    print("="*70)
    print(f"SPOT API:    {'✓ WORKS' if spot_result else '❌ FAILED'}")
    print(f"FUTURES API: {'✓ WORKS' if futures_result else '❌ FAILED'}")

    if spot_result:
        print("\n💡 Your API keys are for SPOT trading")
        print("   Use /openApi/spot/ endpoints")
    elif futures_result:
        print("\n💡 Your API keys are for FUTURES trading")
        print("   Use /openApi/swap/ endpoints")
    else:
        print("\n❌ Neither SPOT nor FUTURES worked - check API keys")

if __name__ == "__main__":
    asyncio.run(main())
