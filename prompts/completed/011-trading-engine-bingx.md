<objective>
Build a production-ready automated trading engine that implements two proven strategies:
1. **Multi-Timeframe LONG** (7.14x R:R ratio, +10.38% return, -1.45% DD)
2. **Trend + Distance 2% SHORT** (8.88x R:R ratio, +20.08% return, -2.26% DD)

The engine must run continuously, process real-time market data, generate trading signals, and execute trades via BingX exchange API.

End goal: A robust, fault-tolerant trading system ready for live deployment with minimal configuration.
</objective>

<context>
Based on extensive backtesting on FARTCOIN/USDT, we've identified two highly profitable strategies:

**Strategy 1: Multi-Timeframe LONG (7.14x R:R)**
- 5-min uptrend confirmation filter
- Explosive bullish breakout pattern (body >1.2%, vol >3x)
- Entry: 1-min pattern + 5-min uptrend alignment
- Stop: 3x ATR below, Target: 12x ATR above
- Win rate: 50%, Profit factor: 4.46

**Strategy 2: Trend + Distance SHORT (8.88x R:R)**
- Strong downtrend filter (below 50 & 200 SMA)
- 2% distance requirement from 50 SMA
- Explosive bearish breakdown (body >1.2%, vol >3x)
- Stop: 3x ATR above, Target: 15x ATR below
- Win rate: 58.3%, Profit factor: 3.83

**Technology Stack Recommendation:**
- Python 3.10+ (rich trading ecosystem, pandas for data processing)
- WebSocket for real-time data
- SQLite/PostgreSQL for trade logging
- REST API for BingX integration
- systemd/supervisor for process management

**Reference Files:**
- Strategy implementations in `./strategies/multi-timeframe-long-v7.py` and trend+distance SHORT
- Backtest results and configurations in `./strategies/`
</context>

<requirements>

### 1. Core Trading Engine Architecture

Create `./trading-engine/` directory with modular structure:

```
trading-engine/
├── main.py                    # Entry point, orchestrates everything
├── config.py                  # Configuration management
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py      # Abstract base class
│   ├── multi_timeframe_long.py
│   └── trend_distance_short.py
├── data/
│   ├── __init__.py
│   ├── data_feed.py          # Real-time data ingestion
│   ├── candle_builder.py     # OHLCV candle construction
│   └── indicators.py         # Technical indicators (SMA, RSI, ATR, etc.)
├── execution/
│   ├── __init__.py
│   ├── signal_generator.py   # Strategy signal aggregation
│   ├── position_manager.py   # Position tracking and sizing
│   ├── risk_manager.py       # Risk controls and validation
│   └── bingx_client.py       # BingX API wrapper (ready for integration)
├── database/
│   ├── __init__.py
│   ├── models.py             # SQLAlchemy models
│   └── trade_logger.py       # Persistent trade history
├── monitoring/
│   ├── __init__.py
│   ├── logger.py             # Structured logging
│   └── metrics.py            # Performance tracking
└── tests/
    ├── __init__.py
    ├── test_strategies.py
    └── test_integration.py
```

### 2. Strategy Implementation

**Multi-Timeframe LONG Strategy:**
- Implement 5-minute candle resampling from 1-minute data
- Calculate 5-min indicators: 50 SMA, 14 RSI, 20 ATR
- Uptrend filter: close > SMA, RSI > 57, distance > 0.6%
- 1-min explosive bullish pattern detection
- Entry only when both timeframes align
- Position sizing: 1.0% base risk, 3.0% max risk
- Trailing stops at 3R and 5R
- Partial exits: 30% at 2R, 40% at 4R

**Trend + Distance SHORT Strategy:**
- Strong downtrend filter: price below 50 & 200 SMA
- 2% distance requirement from 50 SMA
- Explosive bearish breakdown detection
- RSI 25-55 range
- Position sizing: 1.5% base risk, 4.0% max risk
- Fixed 5:1 R:R (15x ATR target, 3x ATR stop)
- Trailing stops and partial exits

### 3. Real-Time Data Feed

**Data Source:** Use WebSocket for tick data (or REST polling as fallback)

**Implementation requirements:**
- Connect to data source (prepare for multiple providers: Binance, CoinGecko, etc.)
- Build 1-minute OHLCV candles from tick data
- Resample to 5-minute candles for multi-timeframe strategy
- Calculate indicators in real-time as candles close
- Buffer management (keep last 250 candles for SMA calculations)
- Reconnection logic with exponential backoff

**Data validation:**
- Sanity checks on incoming data (price ranges, volume)
- Gap detection and handling
- Timestamp synchronization

### 4. Signal Generation & Execution

**Signal Generator:**
- Evaluate both strategies on every 1-minute candle close
- Aggregate signals (LONG, SHORT, or NONE)
- Conflict resolution (if both strategies signal simultaneously)
- Signal validation against current positions

**Position Manager:**
- Track open positions per strategy
- Maximum concurrent positions limit (configurable, default: 1 per strategy)
- Position state: PENDING, OPEN, CLOSING, CLOSED
- PnL tracking in real-time

**Risk Manager:**
- Pre-trade validation:
  - Account balance check
  - Maximum risk per trade
  - Maximum portfolio exposure
  - Cooldown periods after losses
- Emergency stop loss (global max drawdown)
- Position size calculation based on ATR and risk %

### 5. BingX API Integration (Architecture)

**Create `bingx_client.py` with these methods:**

```python
class BingXClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """Initialize with API credentials"""
        pass

    # Market Data
    async def get_ticker(self, symbol: str) -> dict:
        """Get latest price"""
        pass

    async def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
        """Get current orderbook"""
        pass

    # Trading
    async def place_order(self, symbol: str, side: str, order_type: str,
                         quantity: float, price: float = None) -> dict:
        """Place market/limit order"""
        pass

    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        """Cancel open order"""
        pass

    async def get_open_orders(self, symbol: str = None) -> list:
        """Get all open orders"""
        pass

    # Position Management
    async def get_positions(self, symbol: str = None) -> list:
        """Get current positions"""
        pass

    async def set_leverage(self, symbol: str, leverage: int) -> dict:
        """Set position leverage"""
        pass

    # Account
    async def get_balance(self) -> dict:
        """Get account balance"""
        pass

    async def get_account_info(self) -> dict:
        """Get account information"""
        pass
```

**Implementation notes:**
- Use placeholder implementations that log the API calls
- Add comments: "# TODO: Integrate BingX API documentation here"
- Structure ready for drop-in API documentation
- Include authentication headers preparation
- Rate limiting logic (typical: 1200 requests/minute)
- WebSocket for position updates (optional, can use REST polling)

### 6. Configuration Management

**Create `config.yaml`:**

```yaml
# Trading Configuration
trading:
  enabled: false  # Set to true for live trading
  testnet: true   # Use testnet for testing

  symbols:
    - FARTCOINUSDT

  strategies:
    multi_timeframe_long:
      enabled: true
      base_risk_pct: 1.0
      max_risk_pct: 3.0
      max_positions: 1

    trend_distance_short:
      enabled: true
      base_risk_pct: 1.5
      max_risk_pct: 4.0
      max_positions: 1

  risk_management:
    max_portfolio_risk: 5.0  # % of account
    max_drawdown: 10.0       # % before emergency stop
    cooldown_after_loss: 60  # minutes

# Data Feed
data:
  provider: binance  # binance, coinbase, etc.
  websocket_url: wss://stream.binance.com:9443/ws
  rest_api_url: https://api.binance.com/api/v3

  candle_interval: 1m
  buffer_size: 300  # Keep last 300 candles

# BingX API (to be filled)
bingx:
  api_key: YOUR_API_KEY_HERE
  api_secret: YOUR_API_SECRET_HERE
  testnet: true
  base_url: https://open-api.bingx.com

# Logging
logging:
  level: INFO
  file: ./logs/trading-engine.log
  max_size_mb: 50
  backup_count: 5

# Database
database:
  type: sqlite  # or postgresql
  path: ./data/trades.db
  # For PostgreSQL:
  # host: localhost
  # port: 5432
  # database: trading
  # user: trader
  # password: secret
```

### 7. Database Schema

**Trade Log Table:**
- id (primary key)
- timestamp
- strategy (LONG/SHORT)
- symbol
- side (BUY/SELL)
- entry_price
- quantity
- stop_loss
- take_profit
- exit_price
- exit_timestamp
- pnl_usdt
- pnl_percent
- r_multiple
- status (OPEN/CLOSED)
- exit_reason (TP/SL/TRAILING/MANUAL)

**Performance Metrics Table:**
- date
- total_trades
- winning_trades
- losing_trades
- total_pnl
- max_drawdown
- sharpe_ratio (calculated daily)

### 8. Monitoring & Logging

**Logging levels:**
- DEBUG: Data feed ticks, indicator calculations
- INFO: Signals generated, orders placed, positions opened/closed
- WARNING: API errors (retryable), data gaps
- ERROR: Critical failures, position management errors
- CRITICAL: Emergency shutdown events

**Health checks:**
- Data feed status (last tick timestamp)
- API connection status
- Open positions count
- Current drawdown %
- Last signal timestamp

**Performance dashboard (console output every 1 hour):**
```
=== Trading Engine Status ===
Uptime: 5h 23m
Symbols: FARTCOINUSDT
Strategies: LONG (active), SHORT (active)

Open Positions: 1
  - LONG @ 0.00012345 | PnL: +2.3% (+1.5R)

Today's Stats:
  Trades: 3 (2W / 1L)
  PnL: +4.2%
  Win Rate: 66.7%

Current Drawdown: -0.8%
Account Balance: $10,234.56
```

### 9. Process Management

**Create `run.sh` startup script:**
```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python -u main.py
```

**Systemd service file `trading-engine.service`:**
```ini
[Unit]
Description=Crypto Trading Engine
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/path/to/trading-engine
ExecStart=/path/to/trading-engine/run.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 10. Safety Features

**Required safeguards:**
- Dry-run mode (log signals without executing)
- Maximum daily loss limit
- Maximum consecutive losses before pause
- Manual emergency stop mechanism (create STOP file)
- Graceful shutdown (close positions on SIGTERM)
- Position size limits (never risk more than configured %)

**Pre-flight checks on startup:**
- Configuration validation
- API connectivity test
- Database connection test
- Sufficient account balance
- No conflicting positions from manual trading

</requirements>

<implementation>

### Development Approach

**Phase 1: Core Infrastructure**
1. Set up project structure
2. Implement configuration loading
3. Create database models and migrations
4. Build logging system

**Phase 2: Data Pipeline**
1. Implement real-time data feed (start with REST polling, then WebSocket)
2. Build candle construction and resampling
3. Implement technical indicators
4. Add data validation and gap handling

**Phase 3: Strategy Implementation**
1. Port Multi-Timeframe LONG from `./strategies/multi-timeframe-long-v7.py`
2. Port Trend+Distance SHORT from backtest results
3. Unit tests for pattern detection
4. Dry-run testing with historical data replay

**Phase 4: Execution Layer**
1. Build signal generator with conflict resolution
2. Implement position manager
3. Create risk manager with all safety checks
4. Build BingX client architecture (placeholder methods)

**Phase 5: Integration & Testing**
1. End-to-end integration tests with simulated data
2. Paper trading mode (signals only, no execution)
3. Performance monitoring and logging
4. Documentation for BingX API integration

### Code Quality Standards

- **Type hints**: All functions must have type annotations
- **Docstrings**: Google-style docstrings for all classes and public methods
- **Error handling**: Try-except blocks with specific exceptions, never bare except
- **Async/await**: Use asyncio for I/O operations (API calls, WebSocket)
- **Testing**: Minimum 70% code coverage
- **Logging**: Use structured logging (JSON format for production)

### What to Avoid (and WHY)

❌ **Hardcoded values** - All parameters must be in config.yaml for easy tuning
❌ **Blocking I/O** - Use async/await to prevent blocking the event loop during API calls
❌ **Silent failures** - Every exception must be logged, retried if appropriate, or escalated
❌ **Tight coupling** - Strategies must be independent of execution layer (enables easy testing)
❌ **No state persistence** - Always save state to database (survive crashes/restarts)

### Dependencies

**Required Python packages:**
```
pandas>=2.0.0
numpy>=1.24.0
python-binance>=1.0.19  # For data feed
websockets>=11.0
aiohttp>=3.8.0
sqlalchemy>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

</implementation>

<output>

### Files to Create

**Core engine files:**
1. `./trading-engine/main.py` - Entry point and orchestration
2. `./trading-engine/config.py` - Configuration management
3. `./trading-engine/config.yaml` - Configuration file

**Strategy modules:**
4. `./trading-engine/strategies/base_strategy.py` - Abstract base class
5. `./trading-engine/strategies/multi_timeframe_long.py` - LONG strategy
6. `./trading-engine/strategies/trend_distance_short.py` - SHORT strategy

**Data pipeline:**
7. `./trading-engine/data/data_feed.py` - Real-time data ingestion
8. `./trading-engine/data/candle_builder.py` - OHLCV construction
9. `./trading-engine/data/indicators.py` - Technical indicators

**Execution layer:**
10. `./trading-engine/execution/signal_generator.py` - Signal aggregation
11. `./trading-engine/execution/position_manager.py` - Position tracking
12. `./trading-engine/execution/risk_manager.py` - Risk controls
13. `./trading-engine/execution/bingx_client.py` - BingX API wrapper

**Database:**
14. `./trading-engine/database/models.py` - SQLAlchemy models
15. `./trading-engine/database/trade_logger.py` - Trade persistence

**Monitoring:**
16. `./trading-engine/monitoring/logger.py` - Structured logging
17. `./trading-engine/monitoring/metrics.py` - Performance tracking

**Deployment:**
18. `./trading-engine/requirements.txt` - Python dependencies
19. `./trading-engine/run.sh` - Startup script
20. `./trading-engine/trading-engine.service` - Systemd service
21. `./trading-engine/.env.example` - Environment variables template
22. `./trading-engine/README.md` - Setup and usage documentation

**Testing:**
23. `./trading-engine/tests/test_strategies.py` - Strategy unit tests
24. `./trading-engine/tests/test_integration.py` - Integration tests

</output>

<verification>

Before declaring the trading engine complete, verify:

### Functional Tests
- [ ] Data feed connects and receives real-time data
- [ ] 1-minute candles build correctly from ticks
- [ ] 5-minute candles resample correctly
- [ ] All indicators calculate correctly (SMA, RSI, ATR)
- [ ] LONG strategy detects patterns correctly (compare to backtest)
- [ ] SHORT strategy detects patterns correctly (compare to backtest)
- [ ] Signals generate only when all filters pass
- [ ] Position sizing calculates correctly based on ATR and risk %
- [ ] Stop loss and take profit levels are accurate
- [ ] Trailing stops trigger at correct R-multiples
- [ ] Partial exits execute at 2R and 4R

### Safety Tests
- [ ] Risk manager blocks trades exceeding max risk
- [ ] Emergency stop triggers at max drawdown
- [ ] Cooldown period enforces after losses
- [ ] Manual stop file (./STOP) halts trading immediately
- [ ] Graceful shutdown closes positions cleanly
- [ ] Pre-flight checks prevent startup with invalid config

### Integration Tests
- [ ] BingX client architecture ready for API docs
- [ ] All API methods have placeholder implementations
- [ ] Rate limiting logic in place
- [ ] Authentication header preparation works
- [ ] Database logs all trades correctly
- [ ] Performance metrics calculate correctly

### Operational Tests
- [ ] Engine runs for 24+ hours without crashes
- [ ] Logging outputs to file and console
- [ ] Health checks report accurate status
- [ ] Configuration hot-reload works (if implemented)
- [ ] Systemd service starts/stops/restarts correctly

### Comparison to Backtest
Run paper trading for 7 days and compare to backtest expectations:
- [ ] Multi-Timeframe LONG: Win rate ~50%, R:R ~7x
- [ ] Trend+Distance SHORT: Win rate ~58%, R:R ~9x
- [ ] Signal frequency matches backtest (14-12 trades per 30 days)
- [ ] Exit reasons align (TP/SL/trailing/partial)

</verification>

<success_criteria>

✅ **Architecture Complete:**
- Modular, extensible structure
- All components implemented and tested
- Clear separation of concerns (data/strategy/execution)

✅ **Strategy Accuracy:**
- Strategies match backtested logic exactly
- Signal generation validated against historical data
- Performance metrics within expected range

✅ **Production Ready:**
- Comprehensive error handling and logging
- Database persistence for all trades
- Monitoring and health checks
- Graceful startup and shutdown

✅ **BingX Integration Ready:**
- Client architecture complete with all required methods
- Placeholder implementations with clear TODOs
- Authentication and rate limiting framework in place
- Ready for API documentation drop-in

✅ **Safety First:**
- All risk controls implemented and tested
- Emergency stop mechanisms work
- Position limits enforced
- Pre-flight validation prevents bad states

✅ **Documentation:**
- README with setup instructions
- Code comments explaining strategy logic
- Configuration file well-documented
- API integration guide for BingX docs

✅ **Testing:**
- Unit tests for strategies (>70% coverage)
- Integration tests for full pipeline
- Paper trading validation (7+ days)
- Comparison report vs backtest results

</success_criteria>

<notes>

**Why Python:**
Python is the industry standard for algorithmic trading due to:
- Rich ecosystem (pandas, numpy, TA-Lib)
- Excellent async support (asyncio)
- Easy integration with exchanges
- Strong typing with type hints
- Mature testing frameworks

**Why NOT JavaScript:**
While you have a Next.js project, mixing trading logic with web UI creates tight coupling and deployment complexity. Keep them separate - the trading engine can expose an API that your Next.js dashboard consumes.

**BingX Integration Strategy:**
The architecture is designed so you can literally:
1. Read BingX API documentation
2. Fill in the method bodies in `bingx_client.py`
3. Add authentication logic
4. Test with small positions
5. Go live

**Deployment Recommendation:**
- Start with local testing (laptop/desktop)
- Move to VPS (DigitalOcean, AWS EC2) for 24/7 operation
- Use systemd for automatic restarts
- Set up monitoring (UptimeRobot, Discord webhooks)
- Keep logs for at least 90 days

**Risk Management Philosophy:**
The engine prioritizes capital preservation over profit maximization. Better to miss 10 trades than to take 1 bad trade that wipes out a week of gains.

</notes>
