#!/usr/bin/env python3
"""
Ping the trading bot to check its status.
Run this from any machine to see if the bot is OK.

Usage:
    python ping_bot.py
"""

import asyncio
import json
from monitoring.status_reporter import ping_bot


async def main():
    print("🔍 Pinging trading bot...")
    print("-" * 40)

    result = await ping_bot()

    if result.get('online'):
        print(f"✅ BOT IS ONLINE")
        print(f"   Last update: {result.get('last_update')}")
        print(f"   Balance: ${result.get('balance', 0):.2f}")
        print(f"   Open positions: {result.get('positions', 0)}")
        print(f"   Trades today: {result.get('trades_today', 0)}")
        print(f"   P&L today: ${result.get('pnl_today', 0):.2f}")
        print(f"   Candles: {result.get('candles', 0)}")
        print(f"   Message: {result.get('message', '')}")

        if result.get('last_error'):
            print(f"   ⚠️ Last error: {result['last_error']}")
    else:
        print(f"❌ BOT OFFLINE OR NOT RESPONDING")
        print(f"   {result.get('message', result.get('error', 'Unknown'))}")

    print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())
