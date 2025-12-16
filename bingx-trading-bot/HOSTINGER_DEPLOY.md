# 🚀 HOSTINGER UBUNTU DEPLOYMENT - TURNKEY READY

## ⚡ Quick Deploy (5 Minutes)

```bash
# 1. Upload to Hostinger (from your local machine)
scp -r bingx-trading-bot/ root@your-hostinger-ip:/root/

# 2. SSH into Hostinger
ssh root@your-hostinger-ip

# 3. Run one-line installer
cd /root/bingx-trading-bot && chmod +x install.sh && ./install.sh

# 4. Add API keys
nano .env
# Add your BINGX_API_KEY and BINGX_API_SECRET

# 5. Start bot
sudo systemctl start trading-bot
sudo systemctl enable trading-bot

# 6. Done! Check status
sudo systemctl status trading-bot
```

---

## 📋 Files Included

All files ready for deployment:

✅ `install.sh` - One-click installer
✅ `trading-bot.service` - Systemd service
✅ `start.sh` - Quick start script
✅ `stop.sh` - Quick stop script
✅ `status.sh` - Check bot status
✅ `config_rsi_swing.yaml` - Production config
✅ `.env.example` - API keys template

---

## 🔧 Installation Script

The `install.sh` does everything automatically:

1. ✅ Installs Python 3.10+
2. ✅ Creates virtual environment
3. ✅ Installs all dependencies
4. ✅ Creates logs directory
5. ✅ Sets up systemd service
6. ✅ Configures auto-restart
7. ✅ Enables auto-start on reboot

---

## 🔑 API Keys Setup

**REQUIRED:** Add your BingX API keys before starting:

```bash
cd /root/bingx-trading-bot
nano .env
```

Add these lines:
```
BINGX_API_KEY=your_actual_api_key_here
BINGX_API_SECRET=your_actual_secret_here
```

Save: `Ctrl+X`, `Y`, `Enter`

---

## 🎯 Management Commands

### Start/Stop/Status
```bash
# Start bot
sudo systemctl start trading-bot

# Stop bot
sudo systemctl stop trading-bot

# Restart bot
sudo systemctl restart trading-bot

# Check status
sudo systemctl status trading-bot

# Enable auto-start on reboot
sudo systemctl enable trading-bot

# Disable auto-start
sudo systemctl disable trading-bot
```

### View Logs
```bash
# Live logs (follow mode)
sudo journalctl -u trading-bot -f

# Last 100 lines
sudo journalctl -u trading-bot -n 100

# Logs from last hour
sudo journalctl -u trading-bot --since "1 hour ago"

# Logs for today
sudo journalctl -u trading-bot --since today

# Check log file directly
tail -f /root/bingx-trading-bot/logs/trading.log
```

### Quick Scripts
```bash
# Start
./start.sh

# Stop
./stop.sh

# Status
./status.sh
```

---

## ⚙️ Production Configuration

**Already configured in `config_rsi_swing.yaml`:**

### Active Strategies (5)
- **TRUMPSOL** - 13.28x R/DD 🏆 Best!
- **DOGE** - 10.66x R/DD
- **MOODENG** - 8.38x R/DD
- **FARTCOIN** - 8.44x R/DD
- **PEPE** - 7.13x R/DD

### Settings
- **Timeframe:** 1-hour candles
- **Poll frequency:** Every hour
- **Leverage:** 10x on all coins
- **Position size:** $6 USDT each
- **Max margin needed:** ~$3 USDT total
- **Safety:** Auto-stop at 35% drawdown

### Production Mode
```yaml
trading:
  enabled: true              # ✅ LIVE TRADING
  testnet: false             # ✅ PRODUCTION

safety:
  dry_run: false             # ✅ REAL ORDERS
  min_account_balance: 10.0  # Stop if balance < $10
```

---

## 📊 Monitoring

### Check if Bot is Running
```bash
# Method 1: systemctl
sudo systemctl status trading-bot

# Method 2: ps
ps aux | grep "python3 main.py"

# Method 3: quick status
./status.sh
```

### Watch Live Activity
```bash
# Follow logs in real-time
sudo journalctl -u trading-bot -f

# Filter for trades only
sudo journalctl -u trading-bot -f | grep "TRADE"

# Filter for errors only
sudo journalctl -u trading-bot -f | grep "ERROR"
```

### Check Recent Trades
```bash
# Last 20 log entries
tail -n 20 logs/trading.log

# Search for specific symbol
grep "TRUMPSOL" logs/trading.log

# Count signals today
grep "$(date +%Y-%m-%d)" logs/trading.log | grep "SIGNAL" | wc -l
```

---

## 🛡️ Safety Features

### Auto-Restart
Bot automatically restarts if it crashes (10 second delay)

### Stop File Emergency
```bash
# Create STOP file to gracefully shutdown
touch /root/bingx-trading-bot/STOP

# Bot will detect and stop trading
# Check logs to confirm
tail -f logs/trading.log
```

### Balance Protection
```yaml
min_account_balance: 10.0  # Bot stops if balance < $10 USDT
max_drawdown: 35.0          # Emergency stop at 35% drawdown
max_daily_loss_pct: 25.0    # Stop if daily loss > 25%
```

---

## 🔥 Troubleshooting

### Bot Won't Start

```bash
# 1. Check service status
sudo systemctl status trading-bot

# 2. Check recent logs
sudo journalctl -u trading-bot -n 50

# 3. Run manually to see errors
cd /root/bingx-trading-bot
source venv/bin/activate
python3 main.py config_rsi_swing.yaml

# 4. Check API keys
cat .env

# 5. Test config
python3 -c "from config import load_config; print(load_config('config_rsi_swing.yaml'))"
```

### Bot Keeps Restarting

```bash
# Check crash logs
sudo journalctl -u trading-bot --since "10 minutes ago"

# Look for ERROR messages
grep ERROR logs/trading.log
```

### No Trades Happening

```bash
# Check if strategies are enabled
grep "enabled: true" config_rsi_swing.yaml

# Check if signals are being generated
grep "SIGNAL" logs/trading.log

# Check account balance
# (add debug script if needed)
```

### Update Bot Code

```bash
# 1. Stop bot
sudo systemctl stop trading-bot

# 2. Backup current version
cp -r /root/bingx-trading-bot /root/bingx-trading-bot.backup

# 3. Upload new files (from local machine)
scp -r bingx-trading-bot/ root@your-hostinger-ip:/root/

# 4. Restart bot
sudo systemctl start trading-bot

# 5. Check logs
sudo journalctl -u trading-bot -f
```

---

## 📦 What Runs on Hostinger

### System Service
```
trading-bot.service
├── Auto-starts on boot
├── Auto-restarts on crash
├── Runs as root (or trader user)
└── Logs to journalctl + file
```

### Bot Process
```
python3 main.py config_rsi_swing.yaml
├── Polls BingX every hour
├── Fetches 300 x 1h candles
├── Calculates indicators (RSI, ATR)
├── Generates signals
├── Places limit orders
├── Manages positions
└── Logs everything
```

### Resources Used
- **CPU:** <5% average
- **RAM:** ~200MB
- **Disk:** ~50MB (logs grow over time)
- **Network:** Minimal (hourly API calls)

---

## ✅ Pre-Launch Checklist

Before going live:

- [ ] Hostinger server accessible via SSH
- [ ] Bot files uploaded to `/root/bingx-trading-bot/`
- [ ] `install.sh` executed successfully
- [ ] API keys added to `.env`
- [ ] API keys verified (not testnet keys!)
- [ ] BingX account has > $10 USDT balance
- [ ] BingX leverage set to 10x
- [ ] BingX position mode = HEDGE
- [ ] Service enabled: `systemctl enable trading-bot`
- [ ] Service started: `systemctl start trading-bot`
- [ ] Logs showing: `journalctl -u trading-bot -f`
- [ ] No errors in logs
- [ ] First hour poll completed successfully

---

## 🎯 Expected Behavior

### First Hour
```
1. Bot starts
2. Waits until top of next hour (e.g., 14:01 UTC)
3. Fetches 300 x 1h candles for each coin
4. Calculates RSI, ATR indicators
5. Checks for signals
6. Places limit orders if signal detected
7. Logs everything
8. Waits until next hour
```

### Every Hour
```
1. Poll at :01 of hour
2. Fetch fresh candles
3. Update indicators
4. Check pending limit orders
5. Generate new signals
6. Manage open positions
7. Log all activity
8. Sleep until next hour
```

### Logs Look Like
```
2025-12-12 14:01:00 UTC - POLL START
2025-12-12 14:01:05 UTC - TRUMPSOL-USDT: 300 candles fetched
2025-12-12 14:01:06 UTC - TRUMPSOL-USDT: RSI=45.3, ATR=0.234
2025-12-12 14:01:07 UTC - SIGNAL: TRUMPSOL LONG @ $5.59 (RSI crossed above 30)
2025-12-12 14:01:08 UTC - ORDER PLACED: TRUMPSOL LONG limit @ $5.53 (1.0% below)
2025-12-12 14:01:10 UTC - Waiting 59 minutes until next poll...
```

---

## 🚨 Emergency Stop

### Method 1: Stop Service
```bash
sudo systemctl stop trading-bot
```

### Method 2: STOP File
```bash
touch /root/bingx-trading-bot/STOP
# Bot will gracefully shutdown
```

### Method 3: Kill Process
```bash
pkill -f "python3 main.py"
```

---

## 📞 Support

If you need help:

1. **Check logs first:** `sudo journalctl -u trading-bot -n 100`
2. **Read error messages** - most issues are config/API related
3. **Test components:** Run `python3 main.py` manually to see errors
4. **Verify API keys:** Check `.env` file has correct keys

---

## 🎉 You're Ready!

Bot is configured for:
- ✅ 5 strategies (TRUMPSOL, DOGE, MOODENG, FARTCOIN, PEPE)
- ✅ 1-hour timeframe (patient trading)
- ✅ $6 USDT positions (~$0.60 margin each)
- ✅ Auto-restart on crash
- ✅ Auto-start on server reboot
- ✅ Production mode (real orders)

**Next:** Upload, install, add API keys, and start!

```bash
./install.sh
nano .env
sudo systemctl start trading-bot
sudo journalctl -u trading-bot -f
```

**Good luck! 🚀**
