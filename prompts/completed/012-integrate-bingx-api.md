<objective>
Integrate BingX API documentation into the trading engine, implementing all API methods and preparing for 24/7 deployment.

Complete the BingX client implementation with authentication, rate limiting, and all required endpoints for live trading.
</objective>

<context>
The trading engine architecture is complete at `./trading-engine/` with placeholder implementations in `execution/bingx_client.py`.

BingX API documentation has been provided covering:
- Authentication (HMAC SHA256 signatures)
- Market data endpoints (klines, depth, ticker, trades)
- Trading endpoints (place order, cancel order, query orders)
- Account endpoints (balance, positions, leverage)
- WebSocket endpoints (real-time data, account updates)
- Rate limits (typically 1200 req/min, varies by endpoint)

**Current Trading Engine Structure:**
```
trading-engine/
├── execution/
│   └── bingx_client.py          # ← NEEDS IMPLEMENTATION
├── strategies/                   # ← Already implemented
├── data/                        # ← Already implemented
├── monitoring/                  # ← Already implemented
└── config.yaml                  # ← Already configured
```

**Reference Documentation:**
The BingX API documentation is available in the uploaded document with full endpoint specifications.
</context>

<requirements>

### 1. Implement BingX Authentication

Update `./trading-engine/execution/bingx_client.py` with proper authentication:

```python
import hmac
import time
from hashlib import sha256
from urllib.parse import urlencode
import aiohttp
from typing import Dict, Optional, Any

class BingXClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # Base URLs
        self.base_url = "https://open-api-vst.bingx.com" if testnet else "https://open-api.bingx.com"

        # Rate limiting
        self.rate_limit = 1200  # requests per minute
        self.request_timestamps = []

        # Session
        self.session: Optional[aiohttp.ClientSession] = None

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature for API request"""
        # Sort parameters alphabetically
        sorted_params = sorted(params.items())
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params])

        # Create signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            digestmod=sha256
        ).hexdigest()

        return signature

    def _prepare_request(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Prepare request with timestamp and signature"""
        if params is None:
            params = {}

        # Add timestamp
        params['timestamp'] = int(time.time() * 1000)

        # Generate signature
        signature = self._generate_signature(params)
        params['signature'] = signature

        return params

    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        current_time = time.time()

        # Remove timestamps older than 1 minute
        self.request_timestamps = [
            ts for ts in self.request_timestamps
            if current_time - ts < 60
        ]

        # Check if we're at the limit
        if len(self.request_timestamps) >= self.rate_limit:
            # Calculate sleep time
            oldest = self.request_timestamps[0]
            sleep_time = 60 - (current_time - oldest)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        # Add current timestamp
        self.request_timestamps.append(current_time)

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, signed: bool = True) -> Dict:
        """Make HTTP request to BingX API"""
        await self._check_rate_limit()

        if self.session is None:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}{endpoint}"
        headers = {'X-BX-APIKEY': self.api_key}

        if signed:
            params = self._prepare_request(params)

        try:
            if method == 'GET':
                async with self.session.get(url, params=params, headers=headers) as response:
                    return await response.json()
            elif method == 'POST':
                async with self.session.post(url, params=params, headers=headers) as response:
                    return await response.json()
            elif method == 'DELETE':
                async with self.session.delete(url, params=params, headers=headers) as response:
                    return await response.json()
        except Exception as e:
            logging.error(f"BingX API request failed: {e}")
            raise
```

### 2. Implement Market Data Methods

**Get Ticker Price:**
```python
async def get_ticker(self, symbol: str) -> dict:
    """Get latest price for symbol"""
    params = {'symbol': symbol}
    return await self._request('GET', '/openApi/swap/v1/ticker/price', params, signed=False)
```

**Get Kline Data:**
```python
async def get_klines(self, symbol: str, interval: str, limit: int = 500) -> dict:
    """Get kline/candlestick data

    Args:
        symbol: Trading pair (e.g., BTC-USDT)
        interval: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
        limit: Number of candles (max 1440)
    """
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    return await self._request('GET', '/openApi/swap/v3/quote/klines', params, signed=False)
```

**Get Order Book:**
```python
async def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
    """Get current orderbook"""
    params = {'symbol': symbol, 'limit': limit}
    return await self._request('GET', '/openApi/swap/v2/quote/depth', params, signed=False)
```

### 3. Implement Trading Methods

**Place Order:**
```python
async def place_order(
    self,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float = None,
    position_side: str = "LONG",
    stop_loss: dict = None,
    take_profit: dict = None
) -> dict:
    """Place a new order

    Args:
        symbol: Trading pair (e.g., BTC-USDT)
        side: BUY or SELL
        order_type: MARKET, LIMIT, STOP_MARKET, TAKE_PROFIT_MARKET
        quantity: Order quantity in coins
        price: Order price (required for LIMIT orders)
        position_side: LONG or SHORT (BOTH for one-way mode)
        stop_loss: Stop loss configuration dict
        take_profit: Take profit configuration dict

    Returns:
        Order response with orderId
    """
    params = {
        'symbol': symbol,
        'side': side,
        'type': order_type,
        'quantity': quantity,
        'positionSide': position_side
    }

    if price is not None:
        params['price'] = price

    if stop_loss:
        params['stopLoss'] = json.dumps(stop_loss)

    if take_profit:
        params['takeProfit'] = json.dumps(take_profit)

    return await self._request('POST', '/openApi/swap/v2/trade/order', params)
```

**Cancel Order:**
```python
async def cancel_order(self, symbol: str, order_id: str) -> dict:
    """Cancel an open order"""
    params = {'symbol': symbol, 'orderId': order_id}
    return await self._request('DELETE', '/openApi/swap/v2/trade/order', params)
```

**Get Open Orders:**
```python
async def get_open_orders(self, symbol: str = None) -> dict:
    """Get all open orders"""
    params = {}
    if symbol:
        params['symbol'] = symbol
    return await self._request('GET', '/openApi/swap/v2/trade/openOrders', params)
```

### 4. Implement Account Methods

**Get Balance:**
```python
async def get_balance(self) -> dict:
    """Get account balance"""
    return await self._request('GET', '/openApi/swap/v3/user/balance')
```

**Get Positions:**
```python
async def get_positions(self, symbol: str = None) -> dict:
    """Get current positions"""
    params = {}
    if symbol:
        params['symbol'] = symbol
    return await self._request('GET', '/openApi/swap/v2/user/positions', params)
```

**Set Leverage:**
```python
async def set_leverage(self, symbol: str, side: str, leverage: int) -> dict:
    """Set position leverage

    Args:
        symbol: Trading pair
        side: LONG, SHORT, or BOTH
        leverage: Leverage value (1-125)
    """
    params = {
        'symbol': symbol,
        'side': side,
        'leverage': leverage
    }
    return await self._request('POST', '/openApi/swap/v2/trade/leverage', params)
```

### 5. Implement WebSocket for Real-Time Data

Create `./trading-engine/data/websocket_feed.py`:

```python
import asyncio
import websockets
import json
import gzip
from typing import Callable, List
import logging

class BingXWebSocket:
    def __init__(self, symbols: List[str], on_message: Callable):
        self.symbols = symbols
        self.on_message = on_message
        self.ws = None
        self.running = False

        # WebSocket URLs
        self.market_url = "wss://open-api-swap.bingx.com/swap-market"

    async def subscribe_klines(self, symbol: str, interval: str):
        """Subscribe to kline updates"""
        subscription = {
            "id": f"{symbol}@kline_{interval}",
            "reqType": "sub",
            "dataType": f"{symbol}@kline_{interval}"
        }
        await self.ws.send(json.dumps(subscription))

    async def subscribe_trades(self, symbol: str):
        """Subscribe to real-time trades"""
        subscription = {
            "id": f"{symbol}@trade",
            "reqType": "sub",
            "dataType": f"{symbol}@trade"
        }
        await self.ws.send(json.dumps(subscription))

    async def handle_message(self, message):
        """Handle incoming WebSocket message"""
        try:
            # Decompress if needed
            if isinstance(message, bytes):
                message = gzip.decompress(message).decode('utf-8')

            # Handle ping/pong
            if message == "Ping":
                await self.ws.send("Pong")
                return

            data = json.loads(message)

            # Pass to callback
            await self.on_message(data)

        except Exception as e:
            logging.error(f"Error handling WebSocket message: {e}")

    async def run(self):
        """Run WebSocket connection"""
        self.running = True

        while self.running:
            try:
                async with websockets.connect(self.market_url) as ws:
                    self.ws = ws

                    # Subscribe to all symbols
                    for symbol in self.symbols:
                        await self.subscribe_klines(symbol, '1m')
                        await self.subscribe_trades(symbol)

                    # Listen for messages
                    async for message in ws:
                        await self.handle_message(message)

            except Exception as e:
                logging.error(f"WebSocket connection error: {e}")
                await asyncio.sleep(5)  # Reconnect after 5 seconds

    async def stop(self):
        """Stop WebSocket connection"""
        self.running = False
        if self.ws:
            await self.ws.close()
```

### 6. Update Configuration

Update `./trading-engine/config.yaml` to use real BingX credentials:

```yaml
# BingX API (PRODUCTION CONFIG)
bingx:
  api_key: ${BINGX_API_KEY}  # Set via environment variable
  api_secret: ${BINGX_API_SECRET}  # Set via environment variable
  testnet: true  # Set to false for live trading

  # Base URLs (set automatically based on testnet flag)
  base_url_prod: https://open-api.bingx.com
  base_url_test: https://open-api-vst.bingx.com

  # Rate limits
  max_requests_per_minute: 1200
  max_orders_per_second: 5
```

Update `./trading-engine/.env.example`:

```bash
# BingX API Credentials
BINGX_API_KEY=your_api_key_here
BINGX_API_SECRET=your_api_secret_here
```

### 7. Integration with Existing Strategy Logic

Update `./trading-engine/main.py` to use BingX client:

```python
from execution.bingx_client import BingXClient
from data.websocket_feed import BingXWebSocket

async def main():
    # Load config
    config = load_config('config.yaml')

    # Initialize BingX client
    bingx = BingXClient(
        api_key=os.getenv('BINGX_API_KEY'),
        api_secret=os.getenv('BINGX_API_SECRET'),
        testnet=config['bingx']['testnet']
    )

    # Test connection
    balance = await bingx.get_balance()
    logger.info(f"Connected to BingX. Balance: {balance}")

    # Initialize strategies
    strategies = initialize_strategies(config)

    # Start WebSocket for real-time data
    async def on_kline_update(data):
        # Process candle and run strategies
        await process_candle(data, strategies, bingx)

    ws_feed = BingXWebSocket(
        symbols=config['trading']['symbols'],
        on_message=on_kline_update
    )

    # Run trading engine
    await asyncio.gather(
        ws_feed.run(),
        run_strategies(strategies, bingx)
    )
```

### 8. Error Handling and Retry Logic

Implement robust error handling:

```python
async def execute_order_with_retry(self, symbol, side, quantity, max_retries=3):
    """Execute order with automatic retry on failure"""
    for attempt in range(max_retries):
        try:
            result = await self.place_order(symbol, side, 'MARKET', quantity)

            if result['code'] == 0:
                return result
            else:
                logger.warning(f"Order failed: {result['msg']}, attempt {attempt+1}/{max_retries}")

        except Exception as e:
            logger.error(f"Order exception: {e}, attempt {attempt+1}/{max_retries}")

        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    raise Exception(f"Order failed after {max_retries} attempts")
```

</requirements>

<deployment>

## How to Run the Trading Engine 24/7

**IMPORTANT: NOT Vercel!**

Vercel is for serverless functions that run on-demand and shut down after execution. Your trading engine needs to run continuously to monitor markets and execute trades.

### Option 1: VPS with Systemd (RECOMMENDED)

**Best for: Production deployment, 24/7 uptime**

1. **Get a VPS:**
   - DigitalOcean Droplet ($6/month)
   - AWS EC2 t3.micro ($8/month)
   - Linode ($5/month)
   - Vultr ($6/month)

2. **Deploy:**
```bash
# On your VPS
cd /opt
git clone <your-repo>
cd trading-engine

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up environment
cp .env.example .env
nano .env  # Add your BingX API keys

# Install systemd service
sudo cp trading-engine.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable trading-engine
sudo systemctl start trading-engine

# Check status
sudo systemctl status trading-engine

# View logs
sudo journalctl -u trading-engine -f
```

3. **Automatic restart on crash:**
   - Systemd will automatically restart the service if it crashes
   - Survives server reboots
   - Built-in logging to journald

### Option 2: Docker + Docker Compose

**Best for: Easy deployment, portability**

Create `./trading-engine/Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-u", "main.py"]
```

Create `./trading-engine/docker-compose.yml`:

```yaml
version: '3.8'

services:
  trading-engine:
    build: .
    container_name: trading-engine
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**Deploy:**
```bash
docker-compose up -d          # Start in background
docker-compose logs -f        # View logs
docker-compose restart        # Restart service
docker-compose down           # Stop service
```

### Option 3: AWS ECS (Production Scale)

**Best for: Enterprise production, auto-scaling**

- Fully managed container orchestration
- Auto-restart on failure
- Monitoring with CloudWatch
- Scales automatically under load

### Option 4: Local Machine with Screen/Tmux (Development Only)

**Only for testing, NOT production:**

```bash
# Using screen
screen -S trading
cd trading-engine
python main.py

# Detach: Ctrl+A, then D
# Reattach: screen -r trading

# Using tmux
tmux new -s trading
cd trading-engine
python main.py

# Detach: Ctrl+B, then D
# Reattach: tmux attach -t trading
```

**WARNING:** This will stop if:
- Your computer shuts down
- You close your terminal
- Network disconnects

## Monitoring 24/7 Uptime

1. **Health Checks:**
   - UptimeRobot (free, pings every 5 min)
   - Healthchecks.io (free, expects ping from your app)

2. **Alerts:**
   - Discord webhook when trades execute
   - Email alerts on errors
   - SMS for critical failures

3. **Logging:**
   - Store logs in `/var/log/trading-engine/`
   - Rotate logs daily (max 30 days)
   - Monitor disk space usage

</deployment>

<output>

Update these files:

1. `./trading-engine/execution/bingx_client.py` - Full BingX API implementation
2. `./trading-engine/data/websocket_feed.py` - WebSocket for real-time data
3. `./trading-engine/main.py` - Integration with BingX client
4. `./trading-engine/config.yaml` - BingX configuration
5. `./trading-engine/.env.example` - Environment variables template
6. `./trading-engine/Dockerfile` - Docker containerization
7. `./trading-engine/docker-compose.yml` - Docker Compose setup
8. `./trading-engine/DEPLOYMENT.md` - Comprehensive deployment guide

</output>

<verification>

Test the integration:

```bash
# 1. Test API connection
python -c "import asyncio; from execution.bingx_client import BingXClient; client = BingXClient(api_key='TEST', api_secret='TEST', testnet=True); print(asyncio.run(client.get_balance()))"

# 2. Test authentication
# Should succeed with valid credentials
# Should fail with 100001 error for invalid credentials

# 3. Test market data
# Fetch klines for BTC-USDT
# Verify data format matches strategy requirements

# 4. Test WebSocket
# Connect and receive real-time candles
# Verify ping/pong heartbeat

# 5. Paper trading test
# Run in dry-run mode for 24 hours
# Verify signals generate correctly
# Ensure no actual orders placed
```

</verification>

<success_criteria>

✅ BingX API client fully implemented with all methods
✅ Authentication works (HMAC SHA256 signatures)
✅ Rate limiting enforced (1200 req/min)
✅ WebSocket receives real-time data
✅ Integration with existing strategies complete
✅ Error handling and retry logic implemented
✅ Docker containerization ready
✅ Systemd service file configured
✅ Deployment documentation complete
✅ Can connect to BingX testnet successfully
✅ Paper trading mode works for 24+ hours without crashes

</success_criteria>

<notes>

**Deployment Recommendation:**

For serious trading, use VPS + Systemd:
- $6/month for DigitalOcean Droplet
- Guaranteed 24/7 uptime (99.99% SLA)
- Automatic restarts on crash
- SSH access for monitoring
- Can scale to multiple strategies

**Why NOT Vercel:**
- Vercel = serverless functions (shut down after 10s-60s)
- Trading engine = persistent process (runs forever)
- Vercel has 15-minute cold starts
- No persistent state between invocations
- Not designed for WebSocket connections

**Development Workflow:**
1. Test locally first (python main.py)
2. Test in Docker (docker-compose up)
3. Deploy to VPS with systemd
4. Monitor for 48 hours in paper trading mode
5. Switch to live trading with small positions

</notes>
