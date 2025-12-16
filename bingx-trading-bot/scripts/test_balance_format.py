import asyncio
import os
from execution.bingx_client import BingXClient

async def test():
    client = BingXClient(
        os.getenv('BINGX_API_KEY'),
        os.getenv('BINGX_API_SECRET'),
        testnet=False
    )
    balance = await client.get_balance()
    print("Balance response:")
    print(balance)
    await client.close()

asyncio.run(test())
