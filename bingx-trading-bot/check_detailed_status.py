#!/usr/bin/env python3
"""
Check detailed bot status including raw data
"""

import asyncio
import json
import aiohttp
from datetime import datetime

SUPABASE_URL = 'https://gbylzdyyhnvmrgfgpfqh.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdieWx6ZHl5aG52bXJnZmdwZnFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk1Nzc5OTksImV4cCI6MjA3NTE1Mzk5OX0.UX76Ip2vz7nwywqSy2IWZxpnMN3KMn0mxj4cIV4BGFs'


async def check_status():
    """Get full bot status"""
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    }

    async with aiohttp.ClientSession() as session:
        # Get bot status
        async with session.get(
            f'{SUPABASE_URL}/rest/v1/bot_status?bot_id=eq.bingx-bot-1&select=*',
            headers=headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    print("=" * 60)
                    print("BOT STATUS (from Supabase)")
                    print("=" * 60)

                    row = data[0]
                    status = row.get('status', {})

                    print(f"Bot ID: {row.get('bot_id')}")
                    print(f"Last Update: {row.get('updated_at')}")
                    print()
                    print("Status Details:")
                    print(f"  Running: {status.get('running')}")
                    print(f"  Started: {status.get('started_at')}")
                    print(f"  Balance: ${status.get('balance', 0):.2f}")
                    print(f"  Open Positions: {status.get('open_positions', 0)}")
                    print(f"  Trades Today: {status.get('today_trades', 0)}")
                    print(f"  P&L Today: ${status.get('today_pnl', 0):.2f}")
                    print(f"  Candles Processed: {status.get('candles', 0)}")
                    print(f"  Message: {status.get('message', '')}")

                    if status.get('last_signal'):
                        print(f"  Last Signal: {status.get('last_signal')}")

                    if status.get('last_error'):
                        print(f"  ⚠️ Last Error: {status.get('last_error')}")

                    print()
                    print("=" * 60)
                    print("RAW STATUS JSON:")
                    print("=" * 60)
                    print(json.dumps(status, indent=2, default=str))

                    return True
                else:
                    print("❌ No bot status found in database")
                    return False
            else:
                print(f"❌ Failed to query Supabase: {response.status}")
                text = await response.text()
                print(f"Response: {text}")
                return False


async def main():
    await check_status()


if __name__ == "__main__":
    asyncio.run(main())
