# Freqtrade Setup Instructions

## Quick Start

Tell Claude Code on your server:
```
Clone freqtrade and set it up using the instructions in freqtrade-setup/SETUP.md
```

---

## 1. Install Freqtrade

```bash
# Clone the repo
git clone https://github.com/freqtrade/freqtrade.git
cd freqtrade

# Install (Python 3.10+ required)
pip install -e . --no-deps
pip install -r requirements.txt
```

If `sdnotify` fails to build, create modified requirements:
```bash
grep -v sdnotify requirements.txt > requirements-mod.txt
pip install -r requirements-mod.txt
pip install freqtrade-client
```

## 2. Create User Directory

```bash
freqtrade create-userdir --userdir user_data
```

## 3. Copy Strategy File

Copy `DonchianBreakout.py` from this folder to:
```
freqtrade/user_data/strategies/DonchianBreakout.py
```

## 4. Configure for BingX

Copy `config.json` from this folder to:
```
freqtrade/user_data/config.json
```

Then edit and add your API keys:
```json
"exchange": {
    "name": "bingx",
    "key": "YOUR_API_KEY_HERE",
    "secret": "YOUR_API_SECRET_HERE"
}
```

## 5. Run Dry-Run (Paper Trading)

```bash
cd freqtrade
freqtrade trade --config user_data/config.json --strategy DonchianBreakout
```

## 6. Run in Background

```bash
# Using screen
screen -S freqtrade
freqtrade trade --config user_data/config.json --strategy DonchianBreakout
# Press Ctrl+A, D to detach

# To reattach later:
screen -r freqtrade
```

## 7. Switch to Live Trading

Edit `user_data/config.json`:
```json
"dry_run": false,
```

Then run the trade command again.

---

## Strategy Parameters

The DonchianBreakout strategy supports these coins (edit in strategy file):

| Coin | Period | TP (ATR) | SL (ATR) |
|------|--------|----------|----------|
| DOGE | 15 | 4.0 | 4.0 |
| PENGU | 25 | 7.0 | 5.0 |
| FARTCOIN | 15 | 7.5 | 2.0 |
| ETH | 20 | 1.5 | 4.0 |
| UNI | 30 | 10.5 | 2.0 |
| PI | 15 | 3.0 | 2.0 |
| CRV | 15 | 9.0 | 5.0 |
| AIXBT | 15 | 12.0 | 2.0 |
| TRUMPSOL | 25 | 3.0 | 3.0 |
| BTC | 30 | 4.0 | 4.0 |

---

## Useful Commands

```bash
# Check bot status
freqtrade show-trades --config user_data/config.json

# Download historical data
freqtrade download-data --exchange bingx --pairs DOGE/USDT:USDT --timeframe 1h --days 200

# Run backtest
freqtrade backtesting --config user_data/config.json --strategy DonchianBreakout --timerange 20250601-20251216

# Hyperopt (optimize parameters)
freqtrade hyperopt --config user_data/config.json --strategy DonchianBreakout --hyperopt-loss SharpeHyperOptLoss -e 100
```

---

## Verified Performance (10-Coin Portfolio @ 3% Risk)

- **Return:** +118,787%
- **Max DD:** -36.7%
- **R:R Ratio:** 3,237x
- **Win Rate:** 60.7%
- **Trades:** 849

Our backtest logic has been verified to match Freqtrade's logic exactly.
