"""
BingX API Client

Full implementation of BingX Perpetual Futures API v2/v3
Documentation: https://bingx-api.github.io/docs/
"""

import asyncio
import hmac
import hashlib
import time
import json
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal
import aiohttp
import logging


class BingXAPIError(Exception):
    """BingX API Error"""
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg
        super().__init__(f"BingX API Error {code}: {msg}")


class BingXClient:
    """
    BingX Perpetual Futures API Client

    Complete implementation with:
    - HMAC SHA256 authentication
    - Rate limiting (1200 req/min)
    - Exponential backoff retry logic
    - Error handling
    - Session management
    """

    # API Endpoints
    BASE_URL_PROD = "https://open-api.bingx.com"
    BASE_URL_TESTNET = "https://open-api-vst.bingx.com"

    # Market Data (no signature required)
    ENDPOINT_TICKER = "/openApi/swap/v1/ticker/price"
    ENDPOINT_KLINES = "/openApi/swap/v3/quote/klines"
    ENDPOINT_DEPTH = "/openApi/swap/v2/quote/depth"
    ENDPOINT_TRADES = "/openApi/swap/v2/quote/trades"
    ENDPOINT_CONTRACT_INFO = "/openApi/swap/v2/quote/contracts"

    # Trading (signature required)
    ENDPOINT_PLACE_ORDER = "/openApi/swap/v2/trade/order"
    ENDPOINT_CANCEL_ORDER = "/openApi/swap/v2/trade/order"
    ENDPOINT_CANCEL_ALL = "/openApi/swap/v2/trade/allOpenOrders"
    ENDPOINT_OPEN_ORDERS = "/openApi/swap/v2/trade/openOrders"
    ENDPOINT_QUERY_ORDER = "/openApi/swap/v2/trade/order"
    ENDPOINT_ORDER_HISTORY = "/openApi/swap/v2/trade/allOrders"

    # Account (signature required)
    ENDPOINT_BALANCE = "/openApi/swap/v3/user/balance"
    ENDPOINT_POSITIONS = "/openApi/swap/v2/user/positions"
    ENDPOINT_SET_LEVERAGE = "/openApi/swap/v2/trade/leverage"
    ENDPOINT_MARGIN_MODE = "/openApi/swap/v2/trade/marginType"
    ENDPOINT_POSITION_MODE = "/openApi/swap/v2/trade/positionSide/dual"

    # Income history
    ENDPOINT_INCOME = "/openApi/swap/v2/user/income"

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True, base_url: str = None):
        """
        Initialize BingX client

        Args:
            api_key: API key from BingX
            api_secret: API secret from BingX
            testnet: Use testnet (default: True)
            base_url: Override base URL
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # Set base URL
        if base_url:
            self.base_url = base_url
        else:
            self.base_url = self.BASE_URL_TESTNET if testnet else self.BASE_URL_PROD

        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)

        # Rate limiting (1200 req/min = 20 req/sec)
        self.requests_per_minute = 1200
        self.request_timestamps: List[float] = []

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds

        self.logger.info(f"BingX client initialized (testnet={testnet})")

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Generate HMAC SHA256 signature for BingX API

        BingX signature format:
        1. Sort parameters alphabetically
        2. Create query string: key1=value1&key2=value2
        3. Sign with HMAC SHA256

        Args:
            params: Request parameters

        Returns:
            Hex signature string
        """
        # Remove None values and sort
        filtered_params = {k: v for k, v in params.items() if v is not None}
        sorted_params = sorted(filtered_params.items())

        # Create query string
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])

        # Generate signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting to avoid bans"""
        now = time.time()

        # Remove timestamps older than 1 minute
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]

        # Check if we've hit the limit
        if len(self.request_timestamps) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.request_timestamps[0])
            if sleep_time > 0:
                self.logger.warning(f"Rate limit reached ({self.requests_per_minute}/min), sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)

        self.request_timestamps.append(now)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        signed: bool = False,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request to BingX API with retry logic

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether signature is required
            retry_count: Current retry attempt

        Returns:
            API response data

        Raises:
            BingXAPIError: If API returns error
        """
        await self._check_rate_limit()

        if self.session is None:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}{endpoint}"
        params = params or {}

        # Set headers
        headers = {}
        if self.api_key:
            headers['X-BX-APIKEY'] = self.api_key

        # Add timestamp and signature for signed endpoints
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            signature = self._generate_signature(params)

            # For POST/DELETE requests: signature goes in URL
            # For GET: signature goes in params
            if method in ['POST', 'DELETE']:
                # Build query string with signature
                filtered_params = {k: v for k, v in params.items() if v is not None}
                sorted_params = sorted(filtered_params.items())
                query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
                url = f"{url}?{query_string}&signature={signature}"
                # Clear params for POST (body should be empty)
                if method == 'POST':
                    params = {}
            else:
                # GET: add signature to params
                params['signature'] = signature

        try:
            # Make request
            if method == 'GET':
                async with self.session.get(url, params=params, headers=headers) as response:
                    data = await response.json()
            elif method == 'POST':
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
                async with self.session.post(url, headers=headers) as response:
                    data = await response.json()
            elif method == 'DELETE':
                # For signed DELETE, params already in URL; for unsigned, use params
                delete_params = {} if signed else params
                async with self.session.delete(url, params=delete_params, headers=headers) as response:
                    data = await response.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check response
            if data.get('code') == 0:
                return data.get('data', {})
            else:
                error_code = data.get('code', -1)
                error_msg = data.get('msg', 'Unknown error')

                # Retry on certain errors
                if retry_count < self.max_retries and error_code in [-1001, -1003, -1021]:
                    delay = self.retry_delay * (2 ** retry_count)  # Exponential backoff
                    self.logger.warning(f"API error {error_code}, retrying in {delay}s (attempt {retry_count + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                    return await self._request(method, endpoint, params, signed, retry_count + 1)

                raise BingXAPIError(error_code, error_msg)

        except aiohttp.ClientError as e:
            # Network error - retry
            if retry_count < self.max_retries:
                delay = self.retry_delay * (2 ** retry_count)
                self.logger.warning(f"Network error: {e}, retrying in {delay}s (attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(delay)
                return await self._request(method, endpoint, params, signed, retry_count + 1)

            self.logger.error(f"Network error after {self.max_retries} retries: {e}")
            raise

        except Exception as e:
            self.logger.error(f"Unexpected error in API request: {e}", exc_info=True)
            raise

    # ==================== MARKET DATA ====================

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest price ticker for a symbol

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")

        Returns:
            {
                'symbol': 'BTC-USDT',
                'priceChange': '1000.5',
                'priceChangePercent': '2.5',
                'lastPrice': '41000.5',
                'lastQty': '0.1',
                'highPrice': '42000',
                'lowPrice': '39000',
                'volume': '12345.67',
                'quoteVolume': '123456789.12',
                'openPrice': '40000',
                'openTime': 1234567890000,
                'closeTime': 1234567890000
            }
        """
        params = {'symbol': symbol}
        result = await self._request('GET', self.ENDPOINT_TICKER, params, signed=False)

        # Handle both single ticker and list response
        if isinstance(result, list):
            for ticker in result:
                if ticker.get('symbol') == symbol:
                    return ticker
            return {}
        return result

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        start_time: int = None,
        end_time: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical klines/candlestick data

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            interval: Kline interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
            limit: Number of klines (max 1440, default 500)
            start_time: Start timestamp in ms
            end_time: End timestamp in ms

        Returns:
            List of klines:
            [
                {
                    'open': '40000',
                    'high': '41000',
                    'low': '39500',
                    'close': '40500',
                    'volume': '123.45',
                    'time': 1234567890000
                },
                ...
            ]
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': min(limit, 1440)
        }

        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        return await self._request('GET', self.ENDPOINT_KLINES, params, signed=False)

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get current order book depth

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            limit: Depth limit (5, 10, 20, 50, 100, 500, 1000)

        Returns:
            {
                'bids': [['40000', '1.5'], ['39990', '2.0'], ...],
                'asks': [['40010', '1.2'], ['40020', '0.8'], ...],
                'time': 1234567890000
            }
        """
        params = {
            'symbol': symbol,
            'limit': limit
        }
        return await self._request('GET', self.ENDPOINT_DEPTH, params, signed=False)

    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent trades

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            limit: Number of trades (max 500)

        Returns:
            List of recent trades
        """
        params = {
            'symbol': symbol,
            'limit': min(limit, 500)
        }
        return await self._request('GET', self.ENDPOINT_TRADES, params, signed=False)

    async def get_contract_info(self, symbol: str = None) -> List[Dict[str, Any]]:
        """
        Get contract information

        Args:
            symbol: Trading pair (optional, returns all if not specified)

        Returns:
            List of contract specifications
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        return await self._request('GET', self.ENDPOINT_CONTRACT_INFO, params, signed=False)

    # ==================== TRADING ====================

    async def place_order(
        self,
        symbol: str,
        side: str,
        position_side: str,
        order_type: str,
        quantity: float,
        price: float = None,
        stop_price: float = None,
        stop_loss: Dict[str, Any] = None,
        take_profit: Dict[str, Any] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        client_order_id: str = None
    ) -> Dict[str, Any]:
        """
        Place a new order

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            side: Order side ("BUY" or "SELL")
            position_side: Position side ("LONG" or "SHORT")
            order_type: Order type ("MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT", "TAKE_PROFIT_MARKET", "TAKE_PROFIT_LIMIT")
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            stop_price: Stop price (required for STOP orders)
            stop_loss: Stop loss config {"type": "MARK_PRICE", "stopPrice": 40000, "price": 39900, "workingType": "MARK_PRICE"}
            take_profit: Take profit config {"type": "MARK_PRICE", "stopPrice": 42000, "price": 42100, "workingType": "MARK_PRICE"}
            time_in_force: Time in force ("GTC", "IOC", "FOK")
            reduce_only: Reduce only flag
            client_order_id: Client order ID

        Returns:
            {
                'orderId': 123456789,
                'symbol': 'BTC-USDT',
                'side': 'BUY',
                'positionSide': 'LONG',
                'type': 'LIMIT',
                'status': 'NEW',
                'price': '40000',
                'quantity': '0.1',
                'cumQty': '0',
                'avgPrice': '0',
                'workingType': 'MARK_PRICE'
            }
        """
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'positionSide': position_side.upper(),
            'type': order_type.upper(),
            'quantity': quantity,
            'timeInForce': time_in_force
        }

        # Add optional parameters
        if price is not None:
            params['price'] = price
        if stop_price is not None:
            params['stopPrice'] = stop_price
        if reduce_only:
            params['reduceOnly'] = 'true'
        if client_order_id:
            params['clientOrderID'] = client_order_id

        # Add stop loss
        if stop_loss:
            params['stopLoss'] = json.dumps(stop_loss)

        # Add take profit
        if take_profit:
            params['takeProfit'] = json.dumps(take_profit)

        result = await self._request('POST', self.ENDPOINT_PLACE_ORDER, params, signed=True)

        # Log trade
        self.logger.info(f"Order placed: {side} {quantity} {symbol} @ {price or 'MARKET'} (ID: {result.get('orderId')})")

        return result

    async def cancel_order(self, symbol: str, order_id: int = None, client_order_id: str = None) -> Dict[str, Any]:
        """
        Cancel an open order

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            order_id: Order ID (either this or client_order_id required)
            client_order_id: Client order ID

        Returns:
            Cancelled order details
        """
        params = {'symbol': symbol}

        if order_id:
            params['orderId'] = order_id
        elif client_order_id:
            params['clientOrderID'] = client_order_id
        else:
            raise ValueError("Either order_id or client_order_id must be provided")

        result = await self._request('DELETE', self.ENDPOINT_CANCEL_ORDER, params, signed=True)

        self.logger.info(f"Order cancelled: {order_id or client_order_id} for {symbol}")

        return result

    async def cancel_all_orders(self, symbol: str) -> Dict[str, Any]:
        """
        Cancel all open orders for a symbol

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")

        Returns:
            Cancellation result
        """
        params = {'symbol': symbol}
        result = await self._request('DELETE', self.ENDPOINT_CANCEL_ALL, params, signed=True)

        self.logger.info(f"All orders cancelled for {symbol}")

        return result

    async def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """
        Get all open orders

        Args:
            symbol: Trading pair (optional, returns all if not specified)

        Returns:
            List of open orders
        """
        params = {}
        if symbol:
            params['symbol'] = symbol

        result = await self._request('GET', self.ENDPOINT_OPEN_ORDERS, params, signed=True)

        # Handle both dict and list responses
        if isinstance(result, dict):
            return result.get('orders', [])
        return result or []

    async def get_order(self, symbol: str, order_id: int = None, client_order_id: str = None) -> Dict[str, Any]:
        """
        Query order details

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            order_id: Order ID (either this or client_order_id required)
            client_order_id: Client order ID

        Returns:
            Order details
        """
        params = {'symbol': symbol}

        if order_id:
            params['orderId'] = order_id
        elif client_order_id:
            params['clientOrderID'] = client_order_id
        else:
            raise ValueError("Either order_id or client_order_id must be provided")

        return await self._request('GET', self.ENDPOINT_QUERY_ORDER, params, signed=True)

    async def get_order_history(
        self,
        symbol: str,
        order_id: int = None,
        start_time: int = None,
        end_time: int = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get order history

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            order_id: Filter from this order ID
            start_time: Start timestamp in ms
            end_time: End timestamp in ms
            limit: Max results (default 100, max 1000)

        Returns:
            List of historical orders
        """
        params = {
            'symbol': symbol,
            'limit': min(limit, 1000)
        }

        if order_id:
            params['orderId'] = order_id
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        result = await self._request('GET', self.ENDPOINT_ORDER_HISTORY, params, signed=True)

        # Handle both dict and list responses
        if isinstance(result, dict):
            return result.get('orders', [])
        return result or []

    # ==================== POSITION MANAGEMENT ====================

    async def get_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """
        Get current positions

        Args:
            symbol: Trading pair (optional, returns all if not specified)

        Returns:
            List of positions:
            [
                {
                    'symbol': 'BTC-USDT',
                    'positionSide': 'LONG',
                    'positionAmt': '0.1',
                    'entryPrice': '40000',
                    'markPrice': '40500',
                    'unRealizedProfit': '50',
                    'liquidationPrice': '38000',
                    'leverage': '10',
                    'marginType': 'isolated'
                },
                ...
            ]
        """
        params = {}
        if symbol:
            params['symbol'] = symbol

        return await self._request('GET', self.ENDPOINT_POSITIONS, params, signed=True)

    async def set_leverage(self, symbol: str, side: str, leverage: int) -> Dict[str, Any]:
        """
        Set position leverage

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            side: Position side ("LONG" or "SHORT")
            leverage: Leverage value (1-125)

        Returns:
            Updated leverage info
        """
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'leverage': leverage
        }

        result = await self._request('POST', self.ENDPOINT_SET_LEVERAGE, params, signed=True)

        self.logger.info(f"Leverage set: {symbol} {side} {leverage}x")

        return result

    async def set_margin_mode(self, symbol: str, margin_type: str) -> Dict[str, Any]:
        """
        Set margin mode (ISOLATED or CROSSED)

        Args:
            symbol: Trading pair (e.g., "BTC-USDT")
            margin_type: "ISOLATED" or "CROSSED"

        Returns:
            Updated margin mode info
        """
        params = {
            'symbol': symbol,
            'marginType': margin_type.upper()
        }

        result = await self._request('POST', self.ENDPOINT_MARGIN_MODE, params, signed=True)

        self.logger.info(f"Margin mode set: {symbol} {margin_type}")

        return result

    async def set_position_mode(self, dual_side: bool) -> Dict[str, Any]:
        """
        Set position mode (hedge mode or one-way mode)

        Args:
            dual_side: True for hedge mode (LONG/SHORT), False for one-way mode

        Returns:
            Updated position mode info
        """
        params = {
            'dualSidePosition': 'true' if dual_side else 'false'
        }

        result = await self._request('POST', self.ENDPOINT_POSITION_MODE, params, signed=True)

        self.logger.info(f"Position mode set: {'Hedge' if dual_side else 'One-way'}")

        return result

    # ==================== ACCOUNT ====================

    async def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance

        Returns:
            {
                'balance': {
                    'userId': 123456,
                    'asset': 'USDT',
                    'balance': '10000.00000000',
                    'equity': '10050.00000000',
                    'unrealizedProfit': '50.00000000',
                    'realisedProfit': '100.00000000',
                    'availableMargin': '9500.00000000',
                    'usedMargin': '500.00000000',
                    'freezedMargin': '0.00000000'
                }
            }
        """
        return await self._request('GET', self.ENDPOINT_BALANCE, {}, signed=True)

    async def get_income_history(
        self,
        symbol: str = None,
        income_type: str = None,
        start_time: int = None,
        end_time: int = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get income history (realized PnL, funding fees, commissions, etc.)

        Args:
            symbol: Trading pair (optional)
            income_type: Type filter (REALIZED_PNL, FUNDING_FEE, COMMISSION, etc.)
            start_time: Start timestamp in ms
            end_time: End timestamp in ms
            limit: Max results (default 100, max 1000)

        Returns:
            List of income records
        """
        params = {
            'limit': min(limit, 1000)
        }

        if symbol:
            params['symbol'] = symbol
        if income_type:
            params['incomeType'] = income_type
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        return await self._request('GET', self.ENDPOINT_INCOME, params, signed=True)

    # ==================== UTILITY ====================

    async def ping(self) -> bool:
        """
        Test connectivity to API

        Returns:
            True if connection successful
        """
        try:
            # Use contract info endpoint as ping
            await self.get_contract_info()
            self.logger.debug("Ping successful")
            return True
        except Exception as e:
            self.logger.error(f"Ping failed: {e}")
            return False

    async def get_server_time(self) -> int:
        """
        Get server timestamp

        Returns:
            Server timestamp in milliseconds
        """
        # BingX doesn't have a dedicated server time endpoint
        # Use local time with network delay consideration
        return int(time.time() * 1000)

    async def close(self) -> None:
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            self.logger.info("BingX client session closed")
