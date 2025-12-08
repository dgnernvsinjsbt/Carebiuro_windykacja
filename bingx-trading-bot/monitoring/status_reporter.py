"""
Status Reporter Module

Simple status reporting to Supabase.
Bot writes status, you can query it on-demand from anywhere.
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Your Supabase credentials (same as main project)
SUPABASE_URL = 'https://gbylzdyyhnvmrgfgpfqh.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdieWx6ZHl5aG52bXJnZmdwZnFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk1Nzc5OTksImV4cCI6MjA3NTE1Mzk5OX0.UX76Ip2vz7nwywqSy2IWZxpnMN3KMn0mxj4cIV4BGFs'


class StatusReporter:
    """Reports bot status to Supabase"""

    def __init__(self, bot_id: str = "bingx-bot-1"):
        self.bot_id = bot_id
        self.status = {
            'running': False,
            'started_at': None,
            'balance': 0,
            'open_positions': 0,
            'today_trades': 0,
            'today_pnl': 0,
            'candles': 0,
            'last_signal': None,
            'last_error': None,
            'message': 'Initializing...'
        }

    async def report(self, message: str = None) -> bool:
        """Send current status to Supabase"""
        if message:
            self.status['message'] = message

        try:
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'resolution=merge-duplicates'
            }

            payload = {
                'bot_id': self.bot_id,
                'status': self.status,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{SUPABASE_URL}/rest/v1/bot_status',
                    headers=headers,
                    json=payload
                ) as response:
                    return response.status in [200, 201]

        except Exception as e:
            logger.error(f"Status report error: {e}")
            return False

    def update(self, **kwargs) -> None:
        """Update status fields"""
        self.status.update(kwargs)


# Global instance
_reporter: Optional[StatusReporter] = None


def get_reporter(bot_id: str = "bingx-bot-1") -> StatusReporter:
    """Get or create status reporter"""
    global _reporter
    if _reporter is None:
        _reporter = StatusReporter(bot_id)
    return _reporter


# ============================================
# QUERY FUNCTION - Run this from Claude Code
# ============================================

async def ping_bot(bot_id: str = "bingx-bot-1") -> Dict[str, Any]:
    """
    Query bot status from Supabase.
    Run this from any Claude Code instance to check on the bot.
    """
    try:
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{SUPABASE_URL}/rest/v1/bot_status?bot_id=eq.{bot_id}&select=*',
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        row = data[0]
                        updated = row.get('updated_at', 'unknown')
                        status = row.get('status', {})
                        return {
                            'online': status.get('running', False),
                            'last_update': updated,
                            'balance': status.get('balance', 0),
                            'positions': status.get('open_positions', 0),
                            'trades_today': status.get('today_trades', 0),
                            'pnl_today': status.get('today_pnl', 0),
                            'candles': status.get('candles', 0),
                            'message': status.get('message', ''),
                            'last_error': status.get('last_error'),
                            'raw': status
                        }
                    return {'online': False, 'message': 'No status found - bot may not be running'}
                else:
                    return {'online': False, 'error': f'Query failed: {response.status}'}

    except Exception as e:
        return {'online': False, 'error': str(e)}


# Quick CLI check
if __name__ == "__main__":
    import json

    async def main():
        print("🔍 Pinging bot...")
        result = await ping_bot()
        print(json.dumps(result, indent=2, default=str))

    asyncio.run(main())
