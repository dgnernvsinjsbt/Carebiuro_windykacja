# BingX Trading Engine - Quick Start Guide

## 5-Minute Setup (Testnet)

### Step 1: Get BingX Testnet API Keys (2 minutes)

1. Visit BingX Testnet: https://testnet.bingx.com/
2. Sign up for testnet account
3. Go to API Management
4. Create new API key
5. Save your `API Key` and `API Secret`
6. Fund your testnet account (free testnet USDT)

### Step 2: Configure Trading Engine (1 minute)

```bash
cd trading-engine

# Copy environment template
cp .env.example .env

# Edit configuration
nano config.yaml
```

**Update these lines in `config.yaml`:**

```yaml
bingx:
  api_key: YOUR_TESTNET_API_KEY_HERE
  api_secret: YOUR_TESTNET_API_SECRET_HERE
  testnet: true  # Keep this as true for testing
```

### Step 3: Test Connection (2 minutes)

```bash
# Install dependencies (if not done)
pip install -r requirements.txt

# Run connection test
python test_bingx_connection.py
```

**Expected output:**
```
======================================================================
BingX API Integration Test
======================================================================

Testnet Mode: True
API Key: abcd1234...xyz9

=== Testing Connectivity ===
✓ API connectivity OK

=== Testing Market Data ===
✓ Last Price: 41234.50
✓ Got 10 candles
✓ Orderbook retrieved

=== Testing Account Endpoints ===
✓ Balance retrieved
✓ Available: 10000.00 USDT

======================================================================
TEST SUMMARY
======================================================================
CONNECTIVITY         ✓ PASSED
MARKET_DATA          ✓ PASSED
ACCOUNT              ✓ PASSED

✓ All tests PASSED!
```

### Step 4: Run Paper Trading (Optional)

Test strategies without placing real orders:

```yaml
# config.yaml
trading:
  enabled: false  # Disable trading

safety:
  dry_run: true  # Only log signals, don't execute
```

```bash
python main.py
```

**You'll see:**
```
[INFO] Trading engine starting
[INFO] Strategy: multi_timeframe_long enabled
[DRY RUN] Would BUY 0.05 BTC-USDT @ 41234.50
```

### Step 5: Run Live Testnet Trading (Optional)

Place actual orders on testnet:

```yaml
# config.yaml
trading:
  enabled: true  # Enable trading

safety:
  dry_run: false  # Execute real trades (on testnet)
```

```bash
python main.py
```

**Monitor logs:**
```bash
tail -f logs/trading-engine.log
```

---

## Production Deployment (When Ready)

### VPS Deployment (Recommended)

**1. Get a VPS**
- DigitalOcean, Vultr, Linode
- $5-10/month
- Ubuntu 22.04 LTS
- 1GB RAM minimum

**2. Deploy**
```bash
# SSH to VPS
ssh root@your-vps-ip

# Install Python
apt update && apt install -y python3.10 python3-pip git

# Clone repository
git clone <your-repo-url>
cd trading-engine

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano config.yaml  # Add PRODUCTION API keys

# Test
python test_bingx_connection.py

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

**3. Monitor**
```bash
# Check status
sudo systemctl status trading-engine

# View logs
tail -f logs/trading-engine.log

# Check trades
sqlite3 data/trades.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"
```

### Docker Deployment

**1. Install Docker**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

**2. Configure**
```bash
cp .env.example .env
nano .env  # Add your API keys
```

**3. Run**
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart
```

---

## Emergency Stop

Create a `STOP` file to immediately halt trading:

```bash
touch STOP
```

The engine checks for this file every second and stops all trading.

To resume:
```bash
rm STOP
sudo systemctl restart trading-engine
```

---

## Common Commands

### Check Logs
```bash
tail -f logs/trading-engine.log
```

### Check Database
```bash
sqlite3 data/trades.db
.tables
SELECT * FROM trades;
.quit
```

### Restart Service
```bash
sudo systemctl restart trading-engine
```

### Update Code
```bash
git pull
sudo systemctl restart trading-engine
```

### Check Balance
```bash
python -c "
import asyncio
from execution.bingx_client import BingXClient
from config import load_config

async def check():
    cfg = load_config('config.yaml')
    client = BingXClient(cfg.bingx.api_key, cfg.bingx.api_secret, cfg.bingx.testnet)
    balance = await client.get_balance()
    print(balance)
    await client.close()

asyncio.run(check())
"
```

---

## Safety Checklist

Before going live with real money:

- [ ] Tested on testnet for 1+ week
- [ ] Reviewed all trades manually
- [ ] Risk management verified (stop loss, position size)
- [ ] Emergency stop tested
- [ ] Backups configured
- [ ] Monitoring in place
- [ ] Start with small capital (<$100)

---

## Support

- **Full Documentation**: See `DEPLOYMENT.md`
- **API Reference**: See `API_INTEGRATION.md`
- **Troubleshooting**: See `DEPLOYMENT.md` > Troubleshooting section

---

## Quick Reference

### File Locations
- Config: `config.yaml`
- Logs: `logs/trading-engine.log`
- Database: `data/trades.db`
- Emergency Stop: `STOP` (create to stop)

### Important Endpoints
- BingX Testnet: https://testnet.bingx.com/
- BingX API Docs: https://bingx-api.github.io/docs/

### Key Commands
```bash
# Test
python test_bingx_connection.py

# Run
python main.py

# Run in background
nohup python main.py > output.log 2>&1 &

# Stop
pkill -f main.py

# Or with systemd
sudo systemctl start trading-engine
sudo systemctl stop trading-engine
sudo systemctl status trading-engine
```

---

**Ready to trade? Start with testnet!** 🚀

**Never trade more than you can afford to lose.**
