#!/usr/bin/env python3
"""Debug ticker API"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from execution.bingx_client import BingXClient

def load_env():
    env_path = Path(__file__).parent / '.env'
    env = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    return env

async def debug_ticker():
    env = load_env()
    client = BingXClient(env['BINGX_API_KEY'], env['BINGX_API_SECRET'], testnet=False)

    try:
        symbol = "1000PEPE-USDT"

        print("Testing ticker API...")
        ticker = await client.get_ticker(symbol)

        print(f"\nRaw ticker response:")
        import json
        print(json.dumps(ticker, indent=2))

        print(f"\n\nTesting contract info...")
        contracts = await client.get_contract_info(symbol)
        contract = contracts[0] if isinstance(contracts, list) else contracts

        print(f"\nRaw contract response:")
        print(json.dumps(contract, indent=2))

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(debug_ticker())
