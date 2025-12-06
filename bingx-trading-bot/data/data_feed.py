"""
Real-Time Data Feed

Handles WebSocket connections and REST API fallback for market data
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import aiohttp
import websockets


class DataFeed:
    """Real-time market data feed with WebSocket support"""

    def __init__(self, provider: str, websocket_url: str, rest_api_url: str,
                 reconnect_attempts: int = 5, reconnect_delay: int = 5):
        self.provider = provider
        self.websocket_url = websocket_url
        self.rest_api_url = rest_api_url
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay

        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.is_running = False

        # Callbacks
        self.on_tick: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        self.logger = logging.getLogger(__name__)

    async def connect(self, symbol: str) -> None:
        """Connect to WebSocket feed"""
        self.is_running = True
        attempts = 0

        while self.is_running and attempts < self.reconnect_attempts:
            try:
                self.logger.info(f"Connecting to {self.provider} WebSocket...")

                async with websockets.connect(self.websocket_url) as ws:
                    self.websocket = ws
                    self.is_connected = True

                    # Subscribe to symbol
                    await self._subscribe(symbol)

                    self.logger.info(f"Connected and subscribed to {symbol}")

                    # Listen for messages
                    await self._listen()

            except Exception as e:
                attempts += 1
                self.is_connected = False
                self.logger.error(f"WebSocket error (attempt {attempts}): {e}")

                if attempts < self.reconnect_attempts:
                    await asyncio.sleep(self.reconnect_delay * attempts)
                else:
                    self.logger.error("Max reconnection attempts reached")
                    if self.on_error:
                        await self.on_error(f"Connection failed: {e}")

    async def _subscribe(self, symbol: str) -> None:
        """Subscribe to symbol (provider-specific implementation)"""
        if self.provider == 'binance':
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@trade"],
                "id": 1
            }
            await self.websocket.send(json.dumps(subscribe_msg))

        # Add other providers here

    async def _listen(self) -> None:
        """Listen for incoming messages"""
        async for message in self.websocket:
            try:
                data = json.loads(message)
                await self._process_message(data)
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")

    async def _process_message(self, data: Dict[str, Any]) -> None:
        """Process incoming message"""
        # Binance trade format
        if 'e' in data and data['e'] == 'trade':
            tick = {
                'timestamp': datetime.fromtimestamp(data['T'] / 1000),
                'price': float(data['p']),
                'volume': float(data['q']),
                'symbol': data['s']
            }

            if self.on_tick:
                await self.on_tick(tick)

    async def disconnect(self) -> None:
        """Disconnect from WebSocket"""
        self.is_running = False
        self.is_connected = False

        if self.websocket:
            await self.websocket.close()
            self.logger.info("WebSocket disconnected")

    async def get_historical_candles(self, symbol: str, interval: str,
                                    limit: int = 500) -> list:
        """Fetch historical candles via REST API"""
        # Binance example
        if self.provider == 'binance':
            url = f"{self.rest_api_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()

                    candles = []
                    for candle in data:
                        candles.append({
                            'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                            'open': float(candle[1]),
                            'high': float(candle[2]),
                            'low': float(candle[3]),
                            'close': float(candle[4]),
                            'volume': float(candle[5])
                        })

                    return candles

        return []
