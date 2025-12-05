# BingX Trading Engine - Deployment Guide

## Table of Contents
1. [Deployment Options](#deployment-options)
2. [VPS Deployment (Recommended)](#vps-deployment-recommended)
3. [Docker Deployment](#docker-deployment)
4. [Why NOT Vercel](#why-not-vercel)
5. [Testing Procedures](#testing-procedures)
6. [Monitoring & Health Checks](#monitoring--health-checks)
7. [Troubleshooting](#troubleshooting)

---

## Deployment Options

### Option 1: VPS with Systemd (Recommended)
- **Best for**: Production trading
- **Cost**: $5-20/month (DigitalOcean, Vultr, Linode)
- **Uptime**: 99.9%
- **Control**: Full control over resources

### Option 2: Docker
- **Best for**: Easy deployment and scaling
- **Cost**: Same as VPS
- **Uptime**: 99.9%
- **Control**: Containerized environment

### Option 3: Kubernetes (Advanced)
- **Best for**: Multiple strategies, high availability
- **Cost**: $50+/month
- **Uptime**: 99.99%
- **Control**: Auto-scaling, self-healing

---

## VPS Deployment (Recommended)

### 1. Choose a VPS Provider

Recommended providers:
- **DigitalOcean** ($6/month for 1GB RAM)
- **Vultr** ($5/month for 1GB RAM)
- **Linode** ($5/month for 1GB RAM)
- **Hetzner** (€4/month for 2GB RAM - Europe)

Minimum specs:
- 1 vCPU
- 1GB RAM
- 10GB SSD
- Ubuntu 22.04 LTS

### 2. Initial Server Setup

```bash
# SSH into your VPS
ssh root@your-vps-ip

# Update system
apt update && apt upgrade -y

# Install Python 3.10+
apt install -y python3.10 python3.10-venv python3-pip git

# Create trading user (don't run as root!)
adduser trader
usermod -aG sudo trader
su - trader
```

### 3. Clone Repository

```bash
# Clone your trading engine
cd ~
git clone https://github.com/yourusername/trading-engine.git
cd trading-engine
```

### 4. Setup Python Environment

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
# Copy and edit environment variables
cp .env.example .env
nano .env
```

Update with your BingX credentials:
```bash
BINGX_API_KEY=your_actual_api_key
BINGX_API_SECRET=your_actual_api_secret
BINGX_TESTNET=true  # Use testnet first!
TRADING_ENABLED=false  # Start with false
DRY_RUN=true  # Start with dry run
```

### 6. Configure Trading Strategy

```bash
nano config.yaml
```

Review and adjust:
- Symbol to trade
- Risk parameters
- Strategy settings
- Stop loss / take profit levels

### 7. Create Systemd Service

```bash
sudo nano /etc/systemd/system/trading-engine.service
```

```ini
[Unit]
Description=BingX Trading Engine
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/home/trader/trading-engine
Environment="PATH=/home/trader/trading-engine/venv/bin"
ExecStart=/home/trader/trading-engine/venv/bin/python main.py

# Restart policy
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/home/trader/trading-engine/logs/stdout.log
StandardError=append:/home/trader/trading-engine/logs/stderr.log

# Resource limits
MemoryLimit=512M
CPUQuota=100%

[Install]
WantedBy=multi-user.target
```

### 8. Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable trading-engine

# Start service
sudo systemctl start trading-engine

# Check status
sudo systemctl status trading-engine

# View logs
sudo journalctl -u trading-engine -f
```

### 9. Setup Log Rotation

```bash
sudo nano /etc/logrotate.d/trading-engine
```

```
/home/trader/trading-engine/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 trader trader
}
```

---

## Docker Deployment

### 1. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install -y docker-compose

# Add user to docker group
usermod -aG docker trader
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env  # Add your API keys
```

### 3. Build and Run

```bash
# Build image
docker-compose build

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart
```

### 4. Docker Commands

```bash
# Check status
docker ps

# View logs
docker logs -f bingx-trading-engine

# Execute command in container
docker exec -it bingx-trading-engine python -c "from execution.bingx_client import BingXClient; print('OK')"

# Shell access
docker exec -it bingx-trading-engine bash

# Update and restart
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

---

## Why NOT Vercel

**Vercel is NOT suitable for trading bots:**

### Issues:
1. **Execution Time Limits**
   - Serverless functions timeout after 10-60 seconds
   - Trading requires persistent connections

2. **No WebSocket Support**
   - Vercel doesn't support long-lived WebSocket connections
   - Real-time data feed is impossible

3. **Stateless Architecture**
   - Functions are stateless and ephemeral
   - Can't maintain position state between invocations

4. **Cold Starts**
   - Functions sleep when idle
   - Delays of 1-5 seconds on wake = missed trades

5. **No Background Jobs**
   - Can't run continuous event loops
   - No cron jobs for monitoring

### Use Vercel For:
- REST APIs
- Static websites
- Next.js applications
- Webhooks (short-lived)

### Use VPS For:
- **Trading bots** ✅
- WebSocket servers ✅
- Background workers ✅
- Persistent connections ✅

---

## Testing Procedures

### Pre-Deployment Testing

1. **Test API Connection**
```bash
python -c "
import asyncio
from execution.bingx_client import BingXClient

async def test():
    client = BingXClient('YOUR_KEY', 'YOUR_SECRET', testnet=True)
    result = await client.ping()
    print(f'Ping: {result}')

    balance = await client.get_balance()
    print(f'Balance: {balance}')

    await client.close()

asyncio.run(test())
"
```

2. **Test WebSocket Feed**
```bash
python -c "
import asyncio
from data.websocket_feed import BingXWebSocketFeed

async def test():
    ws = BingXWebSocketFeed(testnet=True)
    await ws.subscribe('kline', 'BTC-USDT', '1m')

    # Let it run for 60 seconds
    await asyncio.sleep(60)
    await ws.stop()

asyncio.run(test())
"
```

3. **Backtest on Historical Data**
```bash
# Run backtests on your strategies
python tests/test_strategies.py
```

4. **Paper Trading (Dry Run)**
```bash
# Edit config.yaml
# Set: dry_run: true
# Set: trading.enabled: false

python main.py

# Monitor logs for signals
tail -f logs/trading-engine.log
```

### Testnet Deployment (Before Live)

1. **Setup Testnet Account**
   - Visit BingX testnet
   - Get testnet API keys
   - Fund testnet account

2. **Configure for Testnet**
```yaml
# config.yaml
bingx:
  testnet: true
  api_key: YOUR_TESTNET_KEY
  api_secret: YOUR_TESTNET_SECRET

trading:
  enabled: true  # Enable trading

safety:
  dry_run: false  # Disable dry run (place real testnet orders)
```

3. **Run on Testnet for 1 Week**
   - Monitor all trades
   - Check order execution
   - Verify risk management
   - Review PnL tracking

### Go Live Checklist

- [ ] Backtests profitable (>50% win rate, positive expectancy)
- [ ] Testnet trading successful for 1+ week
- [ ] Risk management tested (stop loss, position sizing)
- [ ] Emergency stop file mechanism tested
- [ ] Logging and monitoring working
- [ ] Balance checks implemented
- [ ] Rate limiting working (no bans)
- [ ] WebSocket reconnection tested
- [ ] VPS has backup/snapshot
- [ ] Alerts configured (email/Telegram)

**Then:**
```yaml
bingx:
  testnet: false  # LIVE
  api_key: YOUR_LIVE_KEY
  api_secret: YOUR_LIVE_SECRET

safety:
  dry_run: false
```

Start with small position sizes!

---

## Monitoring & Health Checks

### 1. System Monitoring

**CPU and Memory**
```bash
# Install htop
apt install htop

# Monitor
htop
```

**Disk Space**
```bash
df -h
du -sh logs/
```

### 2. Application Logs

```bash
# Live tail
tail -f logs/trading-engine.log

# Search for errors
grep ERROR logs/trading-engine.log

# Last 100 lines
tail -n 100 logs/trading-engine.log
```

### 3. Trading Metrics

```bash
# Check database
sqlite3 data/trades.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"

# Count trades
sqlite3 data/trades.db "SELECT COUNT(*) FROM trades;"

# Total PnL
sqlite3 data/trades.db "SELECT SUM(pnl) FROM trades WHERE status='CLOSED';"
```

### 4. Health Check Script

Create `health_check.sh`:
```bash
#!/bin/bash

# Check if process is running
if systemctl is-active --quiet trading-engine; then
    echo "✓ Service running"
else
    echo "✗ Service down!"
    exit 1
fi

# Check recent log activity
if [ $(find logs/trading-engine.log -mmin -5) ]; then
    echo "✓ Logs updated recently"
else
    echo "⚠ No log updates in 5 minutes"
fi

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "✓ Disk space OK ($DISK_USAGE%)"
else
    echo "⚠ Disk space high ($DISK_USAGE%)"
fi

echo "Health check complete"
```

Run every 5 minutes via cron:
```bash
crontab -e

# Add:
*/5 * * * * /home/trader/trading-engine/health_check.sh >> /home/trader/health.log 2>&1
```

### 5. Alerts (Optional)

**Telegram Bot Integration:**
```python
# Add to monitoring/alerts.py
import requests

TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})
```

**Send Alerts On:**
- Large losses (> 2% in one trade)
- Service crashes
- Connection errors
- Daily PnL summary

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u trading-engine -n 50

# Check Python errors
python main.py  # Run directly to see errors

# Check permissions
ls -la /home/trader/trading-engine
```

### API Connection Errors

```bash
# Test connectivity
curl https://open-api.bingx.com/openApi/swap/v2/quote/contracts

# Check API key
python -c "from execution.bingx_client import BingXClient; print(BingXClient('key', 'secret', True).base_url)"

# Verify signature generation
# Enable DEBUG logging in config.yaml
```

### WebSocket Disconnections

```bash
# Check firewall
sudo ufw status

# Allow websocket ports
sudo ufw allow 443/tcp

# Test WebSocket
python data/websocket_feed.py
```

### High Memory Usage

```bash
# Check current usage
free -h

# Limit in systemd service
nano /etc/systemd/system/trading-engine.service
# Add: MemoryLimit=512M

# Restart
sudo systemctl daemon-reload
sudo systemctl restart trading-engine
```

### Database Locked

```bash
# Check database
sqlite3 data/trades.db "PRAGMA integrity_check;"

# Backup and recreate
mv data/trades.db data/trades.db.bak
python -c "from database.models import Base; from database.trade_logger import TradeLogger; t = TradeLogger('sqlite:///./data/trades.db', False)"
```

### Emergency Stop

```bash
# Create STOP file
touch STOP

# Service will detect and halt trading
# Check logs to confirm
tail -f logs/trading-engine.log
```

---

## Production Checklist

Before going live with real money:

- [ ] VPS is stable (uptime > 99%)
- [ ] Backups automated (daily snapshots)
- [ ] Monitoring in place (logs, metrics, alerts)
- [ ] Emergency stop tested
- [ ] API keys secured (not in git!)
- [ ] Rate limits respected
- [ ] Testnet traded successfully for 1+ week
- [ ] Risk management verified (stop loss, max drawdown)
- [ ] Start with small capital (< $100)
- [ ] Gradually increase if profitable
- [ ] Review every trade manually (first week)
- [ ] Have exit strategy ready

**Remember:**
- Trading is risky
- Never invest more than you can afford to lose
- Past performance ≠ future results
- Monitor daily, especially first month
- Keep improving based on results

---

## Support

If you encounter issues:

1. Check logs first
2. Review this guide
3. Test components individually
4. Ask in GitHub issues
5. Contact support

**Good luck and trade safely!** 🚀
