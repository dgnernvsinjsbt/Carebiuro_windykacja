"""
BingX WebSocket Feed

Real-time market data and account updates via WebSocket
Documentation: https://bingx-api.github.io/docs/#/en-us/swapV2/socket/market.html
"""

import asyncio
import json
import gzip
import time
import hmac
import hashlib
from typing import Callable, Dict, Any, List, Optional
from datetime import datetime
import websockets
import logging


class BingXWebSocketFeed:
    """
    BingX WebSocket client for real-time data

    Features:
    - Market data streams (klines, trades, orderbook)
    - Account updates (orders, positions)
    - Auto-reconnect with exponential backoff
    - GZIP decompression
    - Ping/pong heartbeat
    """

    # WebSocket URLs
    WS_URL_PROD = "wss://open-api-swap.bingx.com/swap-market"
    WS_URL_TESTNET = "wss://open-api-swap-vst.bingx.com/swap-market"

    # User data stream (authenticated)
    WS_USER_URL_PROD = "wss://open-api-swap.bingx.com/swap-market"
    WS_USER_URL_TESTNET = "wss://open-api-swap-vst.bingx.com/swap-market"

    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        testnet: bool = True,
        on_message: Callable = None,
        on_kline: Callable = None,
        on_trade: Callable = None,
        on_orderbook: Callable = None,
        on_account_update: Callable = None
    ):
        """
        Initialize WebSocket feed

        Args:
            api_key: API key (required for account streams)
            api_secret: API secret (required for account streams)
            testnet: Use testnet
            on_message: Callback for all messages
            on_kline: Callback for kline updates
            on_trade: Callback for trade updates
            on_orderbook: Callback for orderbook updates
            on_account_update: Callback for account updates
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # Set WebSocket URL
        self.ws_url = self.WS_URL_TESTNET if testnet else self.WS_URL_PROD
        self.user_ws_url = self.WS_USER_URL_TESTNET if testnet else self.WS_USER_URL_PROD

        # Callbacks
        self.on_message = on_message
        self.on_kline = on_kline
        self.on_trade = on_trade
        self.on_orderbook = on_orderbook
        self.on_account_update = on_account_update

        # Connection state
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.user_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.subscriptions: List[Dict[str, Any]] = []

        # Reconnection
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60
        self.reconnect_attempts = 0

        # Heartbeat
        self.ping_interval = 20  # seconds
        self.last_pong_time = time.time()
        self.pong_timeout = 30  # seconds

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"BingX WebSocket initialized (testnet={testnet})")

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature"""
        sorted_params = sorted(params.items())
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])

        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _decompress_message(self, data: bytes) -> str:
        """Decompress GZIP message"""
        try:
            return gzip.decompress(data).decode('utf-8')
        except:
            # Not compressed
            return data.decode('utf-8')

    async def _send_ping(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Send ping message"""
        ping_msg = {"ping": int(time.time() * 1000)}
        await ws.send(json.dumps(ping_msg))
        self.logger.debug("Ping sent")

    async def _heartbeat_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Heartbeat loop to keep connection alive"""
        while self.running:
            try:
                await asyncio.sleep(self.ping_interval)

                # Check if we've received pong recently
                if time.time() - self.last_pong_time > self.pong_timeout:
                    self.logger.warning("Pong timeout, reconnecting...")
                    await ws.close()
                    break

                await self._send_ping(ws)

            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                break

    def _parse_message(self, message: str) -> None:
        """Parse and route WebSocket message"""
        try:
            data = json.loads(message)

            # Handle pong
            if 'pong' in data:
                self.last_pong_time = time.time()
                self.logger.debug("Pong received")
                return

            # Call general message callback
            if self.on_message:
                self.on_message(data)

            # Route to specific callbacks
            data_type = data.get('dataType', '')

            if data_type and '@kline_' in data_type:
                # Kline update
                if self.on_kline:
                    self.on_kline(data.get('data'))

            elif data_type and '@trade' in data_type:
                # Trade update
                if self.on_trade:
                    self.on_trade(data.get('data'))

            elif data_type and '@depth' in data_type:
                # Orderbook update
                if self.on_orderbook:
                    self.on_orderbook(data.get('data'))

            elif 'e' in data:
                # Account update event
                event_type = data.get('e')

                if event_type in ['ORDER_TRADE_UPDATE', 'ACCOUNT_UPDATE'] and self.on_account_update:
                    self.on_account_update(data)

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)

    async def _listen(self, ws: websockets.WebSocketClientProtocol) -> None:
        """Listen for WebSocket messages"""
        try:
            async for message in ws:
                if isinstance(message, bytes):
                    message = self._decompress_message(message)

                self._parse_message(message)

        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket connection closed")
        except Exception as e:
            self.logger.error(f"Error in listen loop: {e}", exc_info=True)

    async def _connect(self) -> websockets.WebSocketClientProtocol:
        """Establish WebSocket connection"""
        try:
            ws = await websockets.connect(
                self.ws_url,
                ping_interval=None,  # We handle pings manually
                close_timeout=10
            )

            self.logger.info(f"WebSocket connected: {self.ws_url}")
            self.reconnect_attempts = 0
            self.last_pong_time = time.time()

            return ws

        except Exception as e:
            self.logger.error(f"Failed to connect WebSocket: {e}")
            raise

    async def _connect_user_stream(self) -> websockets.WebSocketClientProtocol:
        """Establish authenticated user data stream"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret required for user stream")

        try:
            # Generate listen key first (requires REST API call)
            # For now, use same connection with auth in subscribe
            ws = await websockets.connect(
                self.user_ws_url,
                ping_interval=None,
                close_timeout=10
            )

            self.logger.info(f"User WebSocket connected: {self.user_ws_url}")

            return ws

        except Exception as e:
            self.logger.error(f"Failed to connect user WebSocket: {e}")
            raise

    async def _reconnect(self) -> None:
        """Reconnect with exponential backoff"""
        delay = min(
            self.reconnect_delay * (2 ** self.reconnect_attempts),
            self.max_reconnect_delay
        )

        self.logger.info(f"Reconnecting in {delay}s (attempt {self.reconnect_attempts + 1})")
        await asyncio.sleep(delay)

        self.reconnect_attempts += 1

        # Re-establish connection
        await self.start()

    async def subscribe(self, data_type: str, symbol: str = None, interval: str = None) -> None:
        """
        Subscribe to a data stream

        Args:
            data_type: Stream type ('kline', 'trade', 'depth', etc.)
            symbol: Trading pair (e.g., "BTC-USDT")
            interval: For klines: '1m', '5m', '15m', '1h', '4h', '1d'
        """
        # Build subscription message
        subscribe_msg = {
            "id": f"sub_{int(time.time() * 1000)}",
            "reqType": "sub"
        }

        if data_type == 'kline':
            if not symbol or not interval:
                raise ValueError("Symbol and interval required for kline subscription")
            subscribe_msg["dataType"] = f"{symbol}@kline_{interval}"

        elif data_type == 'trade':
            if not symbol:
                raise ValueError("Symbol required for trade subscription")
            subscribe_msg["dataType"] = f"{symbol}@trade"

        elif data_type == 'depth':
            if not symbol:
                raise ValueError("Symbol required for depth subscription")
            # Options: @depth (full), @depth5, @depth10, @depth20
            subscribe_msg["dataType"] = f"{symbol}@depth20"

        elif data_type == 'ticker':
            if not symbol:
                raise ValueError("Symbol required for ticker subscription")
            subscribe_msg["dataType"] = f"{symbol}@ticker"

        else:
            raise ValueError(f"Unknown data type: {data_type}")

        # Store subscription for reconnect
        self.subscriptions.append(subscribe_msg)

        # Send subscription if connected
        if self.ws and not self.ws.closed:
            await self.ws.send(json.dumps(subscribe_msg))
            self.logger.info(f"Subscribed: {subscribe_msg['dataType']}")

    async def unsubscribe(self, data_type: str, symbol: str = None, interval: str = None) -> None:
        """Unsubscribe from a data stream"""
        unsubscribe_msg = {
            "id": f"unsub_{int(time.time() * 1000)}",
            "reqType": "unsub"
        }

        if data_type == 'kline':
            unsubscribe_msg["dataType"] = f"{symbol}@kline_{interval}"
        elif data_type == 'trade':
            unsubscribe_msg["dataType"] = f"{symbol}@trade"
        elif data_type == 'depth':
            unsubscribe_msg["dataType"] = f"{symbol}@depth20"
        elif data_type == 'ticker':
            unsubscribe_msg["dataType"] = f"{symbol}@ticker"

        # Remove from stored subscriptions
        self.subscriptions = [
            s for s in self.subscriptions
            if s.get('dataType') != unsubscribe_msg.get('dataType')
        ]

        if self.ws and not self.ws.closed:
            await self.ws.send(json.dumps(unsubscribe_msg))
            self.logger.info(f"Unsubscribed: {unsubscribe_msg['dataType']}")

    async def subscribe_user_updates(self) -> None:
        """Subscribe to account updates (orders, positions, balance)"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret required for user updates")

        # This requires authenticated connection
        # Implementation depends on BingX listen key mechanism
        self.logger.info("User updates subscription (requires listen key implementation)")

    async def start(self) -> None:
        """Start WebSocket feed"""
        if self.running:
            self.logger.warning("WebSocket already running")
            return

        self.running = True

        try:
            # Connect
            self.ws = await self._connect()

            # Resubscribe to all streams
            for sub in self.subscriptions:
                await self.ws.send(json.dumps(sub))
                self.logger.info(f"Resubscribed: {sub.get('dataType')}")

            # Start heartbeat
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(self.ws))

            # Listen for messages
            await self._listen(self.ws)

            # Cancel heartbeat
            heartbeat_task.cancel()

        except Exception as e:
            self.logger.error(f"WebSocket error: {e}", exc_info=True)

        finally:
            if self.running:
                # Auto-reconnect
                await self._reconnect()

    async def stop(self) -> None:
        """Stop WebSocket feed"""
        self.logger.info("Stopping WebSocket feed...")
        self.running = False

        if self.ws and not self.ws.closed:
            await self.ws.close()

        if self.user_ws and not self.user_ws.closed:
            await self.user_ws.close()

        self.logger.info("WebSocket feed stopped")


# Example usage
async def example():
    """Example WebSocket usage"""

    def on_kline(data):
        print(f"Kline update: {data}")

    def on_trade(data):
        print(f"Trade: {data}")

    # Create feed
    ws_feed = BingXWebSocketFeed(
        testnet=True,
        on_kline=on_kline,
        on_trade=on_trade
    )

    # Subscribe to streams
    await ws_feed.subscribe('kline', 'BTC-USDT', '1m')
    await ws_feed.subscribe('trade', 'BTC-USDT')

    # Start listening
    await ws_feed.start()


if __name__ == "__main__":
    asyncio.run(example())
