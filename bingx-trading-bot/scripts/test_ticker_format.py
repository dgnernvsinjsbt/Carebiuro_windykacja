import asyncio
import os
from execution.bingx_client import BingXClient

async def test():
    client = BingXClient(
        os.getenv('BINGX_API_KEY'),
        os.getenv('BINGX_API_SECRET'),
        testnet=False
    )
    ticker = await client.get_ticker('MOODENG-USDT')
    print("Ticker response:")
    print(ticker)
    await client.close()

asyncio.run(test())
