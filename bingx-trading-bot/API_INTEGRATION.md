# BingX API Integration - Complete Documentation

## Overview

This document provides complete details on the BingX API integration implemented in the trading engine.

## API Client Implementation

### File: `execution/bingx_client.py`

The BingX client implements all required API endpoints for perpetual futures trading:

#### Authentication
- HMAC SHA256 signature generation
- Timestamp-based request signing
- API key in header (`X-BX-APIKEY`)

#### Rate Limiting
- 1200 requests per minute enforced
- Automatic sleep when limit reached
- Request timestamp tracking

#### Error Handling
- Exponential backoff retry (3 attempts)
- Network error recovery
- BingXAPIError exception for API errors

#### Retry Logic
- Retry on error codes: -1001, -1003, -1021
- Exponential backoff: 1s, 2s, 4s
- Network timeout recovery

## API Endpoints Implemented

### Market Data (Public - No Authentication)

#### 1. Get Ticker
```python
ticker = await client.get_ticker("BTC-USDT")
# Returns: {symbol, priceChange, lastPrice, volume, ...}
```

**Endpoint**: `GET /openApi/swap/v1/ticker/price`

**Response**:
```json
{
  "symbol": "BTC-USDT",
  "lastPrice": "41000.5",
  "priceChange": "1000.5",
  "priceChangePercent": "2.5",
  "volume": "12345.67"
}
```

#### 2. Get Klines (Candlestick Data)
```python
klines = await client.get_klines(
    symbol="BTC-USDT",
    interval="1m",  # 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
    limit=500,
    start_time=None,  # Optional: timestamp in ms
    end_time=None     # Optional: timestamp in ms
)
```

**Endpoint**: `GET /openApi/swap/v3/quote/klines`

**Intervals**: `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w`

**Limits**: Max 1440 candles per request

**Response**:
```json
[
  {
    "open": "40000",
    "high": "41000",
    "low": "39500",
    "close": "40500",
    "volume": "123.45",
    "time": 1234567890000
  }
]
```

#### 3. Get Order Book
```python
orderbook = await client.get_orderbook("BTC-USDT", limit=20)
# Returns: {bids: [[price, qty], ...], asks: [[price, qty], ...]}
```

**Endpoint**: `GET /openApi/swap/v2/quote/depth`

**Limits**: 5, 10, 20, 50, 100, 500, 1000

**Response**:
```json
{
  "bids": [["40000", "1.5"], ["39990", "2.0"]],
  "asks": [["40010", "1.2"], ["40020", "0.8"]],
  "time": 1234567890000
}
```

#### 4. Get Recent Trades
```python
trades = await client.get_recent_trades("BTC-USDT", limit=100)
```

**Endpoint**: `GET /openApi/swap/v2/quote/trades`

**Limits**: Max 500

#### 5. Get Contract Info
```python
contracts = await client.get_contract_info("BTC-USDT")
# Returns contract specifications
```

**Endpoint**: `GET /openApi/swap/v2/quote/contracts`

### Trading (Requires Authentication)

#### 1. Place Order
```python
order = await client.place_order(
    symbol="BTC-USDT",
    side="BUY",           # BUY or SELL
    position_side="LONG", # LONG or SHORT
    order_type="LIMIT",   # MARKET, LIMIT, STOP_MARKET, etc.
    quantity=0.1,
    price=40000,          # Required for LIMIT
    stop_loss={           # Optional
        "type": "MARK_PRICE",
        "stopPrice": 39000,
        "price": 38900
    },
    take_profit={         # Optional
        "type": "MARK_PRICE",
        "stopPrice": 42000,
        "price": 42100
    },
    time_in_force="GTC",  # GTC, IOC, FOK
    reduce_only=False
)
```

**Endpoint**: `POST /openApi/swap/v2/trade/order`

**Order Types**:
- `MARKET` - Market order
- `LIMIT` - Limit order
- `STOP_MARKET` - Stop market order
- `STOP_LIMIT` - Stop limit order
- `TAKE_PROFIT_MARKET` - Take profit market
- `TAKE_PROFIT_LIMIT` - Take profit limit

**Time in Force**:
- `GTC` - Good Till Cancel
- `IOC` - Immediate or Cancel
- `FOK` - Fill or Kill

**Response**:
```json
{
  "orderId": 123456789,
  "symbol": "BTC-USDT",
  "side": "BUY",
  "type": "LIMIT",
  "status": "NEW",
  "price": "40000",
  "quantity": "0.1"
}
```

#### 2. Cancel Order
```python
result = await client.cancel_order(
    symbol="BTC-USDT",
    order_id=123456789
)
```

**Endpoint**: `DELETE /openApi/swap/v2/trade/order`

#### 3. Cancel All Orders
```python
result = await client.cancel_all_orders("BTC-USDT")
```

**Endpoint**: `DELETE /openApi/swap/v2/trade/allOpenOrders`

#### 4. Get Open Orders
```python
orders = await client.get_open_orders("BTC-USDT")  # or None for all
```

**Endpoint**: `GET /openApi/swap/v2/trade/openOrders`

#### 5. Query Order
```python
order = await client.get_order("BTC-USDT", order_id=123456789)
```

**Endpoint**: `GET /openApi/swap/v2/trade/order`

#### 6. Get Order History
```python
history = await client.get_order_history(
    symbol="BTC-USDT",
    limit=100
)
```

**Endpoint**: `GET /openApi/swap/v2/trade/allOrders`

### Account & Positions (Requires Authentication)

#### 1. Get Balance
```python
balance = await client.get_balance()
```

**Endpoint**: `GET /openApi/swap/v3/user/balance`

**Response**:
```json
{
  "balance": {
    "asset": "USDT",
    "balance": "10000.00",
    "equity": "10050.00",
    "unrealizedProfit": "50.00",
    "availableMargin": "9500.00"
  }
}
```

#### 2. Get Positions
```python
positions = await client.get_positions("BTC-USDT")  # or None for all
```

**Endpoint**: `GET /openApi/swap/v2/user/positions`

**Response**:
```json
[
  {
    "symbol": "BTC-USDT",
    "positionSide": "LONG",
    "positionAmt": "0.1",
    "entryPrice": "40000",
    "markPrice": "40500",
    "unRealizedProfit": "50",
    "liquidationPrice": "38000",
    "leverage": "10"
  }
]
```

#### 3. Set Leverage
```python
result = await client.set_leverage(
    symbol="BTC-USDT",
    side="LONG",
    leverage=10
)
```

**Endpoint**: `POST /openApi/swap/v2/trade/leverage`

**Range**: 1-125x (varies by symbol)

#### 4. Set Margin Mode
```python
result = await client.set_margin_mode(
    symbol="BTC-USDT",
    margin_type="ISOLATED"  # or "CROSSED"
)
```

**Endpoint**: `POST /openApi/swap/v2/trade/marginType`

#### 5. Set Position Mode
```python
result = await client.set_position_mode(dual_side=True)  # Hedge mode
```

**Endpoint**: `POST /openApi/swap/v2/trade/positionSide/dual`

#### 6. Get Income History
```python
income = await client.get_income_history(
    symbol="BTC-USDT",
    income_type="REALIZED_PNL",
    limit=100
)
```

**Endpoint**: `GET /openApi/swap/v2/user/income`

**Income Types**:
- `REALIZED_PNL` - Realized profit/loss
- `FUNDING_FEE` - Funding fees
- `COMMISSION` - Trading commissions

### Utility

#### 1. Ping
```python
is_connected = await client.ping()
```

Uses contract info endpoint as health check.

#### 2. Get Server Time
```python
timestamp = await client.get_server_time()
# Returns: milliseconds timestamp
```

## WebSocket Implementation

### File: `data/websocket_feed.py`

Real-time market data and account updates via WebSocket.

#### Features
- Auto-reconnect with exponential backoff
- GZIP decompression
- Ping/pong heartbeat (20s interval)
- Multiple stream subscriptions
- Event callbacks

#### WebSocket URLs
- Production: `wss://open-api-swap.bingx.com/swap-market`
- Testnet: `wss://open-api-swap-vst.bingx.com/swap-market`

### Stream Types

#### 1. Kline Stream
```python
ws = BingXWebSocketFeed(testnet=True, on_kline=callback)
await ws.subscribe('kline', 'BTC-USDT', '1m')
await ws.start()
```

**Data Type**: `{symbol}@kline_{interval}`

**Message**:
```json
{
  "dataType": "BTC-USDT@kline_1m",
  "data": {
    "open": "40000",
    "high": "40100",
    "low": "39900",
    "close": "40050",
    "volume": "10.5",
    "time": 1234567890000
  }
}
```

#### 2. Trade Stream
```python
await ws.subscribe('trade', 'BTC-USDT')
```

**Data Type**: `{symbol}@trade`

#### 3. Order Book (Depth) Stream
```python
await ws.subscribe('depth', 'BTC-USDT')
```

**Data Type**: `{symbol}@depth20`

**Options**: `@depth`, `@depth5`, `@depth10`, `@depth20`

#### 4. Ticker Stream
```python
await ws.subscribe('ticker', 'BTC-USDT')
```

**Data Type**: `{symbol}@ticker`

### Callbacks

```python
def on_kline(data):
    print(f"New candle: {data}")

def on_trade(data):
    print(f"New trade: {data}")

def on_orderbook(data):
    print(f"Orderbook update: {data}")

def on_account_update(data):
    print(f"Account update: {data}")

ws = BingXWebSocketFeed(
    testnet=True,
    on_kline=on_kline,
    on_trade=on_trade,
    on_orderbook=on_orderbook,
    on_account_update=on_account_update
)
```

### Heartbeat

- Ping sent every 20 seconds
- Pong timeout: 30 seconds
- Auto-reconnect on timeout

### Reconnection

- Initial delay: 5 seconds
- Max delay: 60 seconds
- Exponential backoff
- Re-subscribes to all streams

## Error Handling

### API Errors

```python
from execution.bingx_client import BingXAPIError

try:
    order = await client.place_order(...)
except BingXAPIError as e:
    print(f"API Error {e.code}: {e.msg}")
```

### Common Error Codes

- `-1001` - Internal error (retryable)
- `-1003` - Rate limit exceeded
- `-1021` - Timestamp error (clock sync)
- `-2013` - Order does not exist
- `-2019` - Margin insufficient

### Network Errors

Handled automatically with retry logic:
- Connection timeout
- DNS resolution failure
- SSL errors

## Rate Limits

### REST API
- **Default**: 1200 requests/minute
- **Weight**: Some endpoints consume more weight
- **IP-based**: Per IP address

**Implemented**:
```python
# Automatic rate limiting
await client._check_rate_limit()
# Sleeps if limit reached
```

### WebSocket
- **Connections**: Max 5 per IP
- **Subscriptions**: Max 200 per connection
- **Messages**: Unlimited (receive only)

## Testing

### Connection Test Script

Run before deployment:

```bash
python test_bingx_connection.py
```

Tests:
1. API connectivity (ping)
2. Market data endpoints
3. Account endpoints
4. WebSocket feed (optional)
5. Trading endpoints (testnet only)

### Manual Testing

```python
import asyncio
from execution.bingx_client import BingXClient

async def test():
    client = BingXClient("API_KEY", "API_SECRET", testnet=True)

    # Test market data
    ticker = await client.get_ticker("BTC-USDT")
    print(ticker)

    # Test account
    balance = await client.get_balance()
    print(balance)

    await client.close()

asyncio.run(test())
```

## Configuration

### config.yaml

```yaml
bingx:
  api_key: YOUR_API_KEY
  api_secret: YOUR_API_SECRET
  testnet: true
  base_url: https://open-api.bingx.com
  requests_per_minute: 1200
  default_leverage: 1
```

### Environment Variables (.env)

```bash
BINGX_API_KEY=your_key
BINGX_API_SECRET=your_secret
BINGX_TESTNET=true
```

## Production Checklist

Before going live:

- [ ] Test all endpoints on testnet
- [ ] Verify signature generation
- [ ] Test rate limiting behavior
- [ ] Verify order placement and cancellation
- [ ] Test WebSocket stability (24h+)
- [ ] Verify error handling and retries
- [ ] Test emergency stop mechanism
- [ ] Backup API keys securely
- [ ] Enable monitoring and alerts
- [ ] Document all API quirks/issues

## Known Issues & Limitations

### BingX API Limitations
1. **Kline Limit**: Max 1440 candles per request
2. **Timestamp Sensitivity**: Server time sync critical
3. **Leverage Range**: Varies by symbol (check contract info)
4. **Minimum Order Size**: Varies by symbol

### Implementation Notes
1. **No Dedicated Ping**: Using contract info as health check
2. **WebSocket Auth**: Requires listen key (not yet implemented)
3. **Signature Order**: Parameters must be alphabetically sorted

## Support & Resources

- **BingX API Docs**: https://bingx-api.github.io/docs/
- **Testnet**: https://bingx.com/en-us/support/announcement/testnet-announcement/
- **API Support**: Check BingX official channels

## Updates & Maintenance

- Regularly check BingX announcements for API changes
- Update endpoint URLs if BingX migrates
- Monitor rate limit adjustments
- Test after major BingX updates

---

**Last Updated**: 2024-12-05
**API Version**: v2/v3
**Integration Status**: ✅ Complete
