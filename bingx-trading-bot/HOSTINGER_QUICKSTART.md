# 🚀 BingX Trading Bot - Hostinger Deployment Quickstart

## 📦 What's Ready

✅ **8-Coin Donchian Breakout Portfolio** (1H candles)
- Strategies for: UNI, PI, DOGE, PENGU, ETH, AIXBT, FARTCOIN, CRV
- Kelly position sizing (3% risk per trade)
- Historical warmup (<10 seconds startup)
- Backtest: +35,902% return, 899x R:R ratio

✅ **All Files on GitHub**
- Repository: https://github.com/dgnernvsinjsbt/bingx-trading-bot
- Main branch has complete working code
- No missing dependencies

## 🎯 One-Command Deployment

### On Hostinger (SSH):

```bash
# 1. Navigate to bot directory
cd ~/bingx-trading-bot

# 2. Pull latest code (OVERWRITES local changes!)
git reset --hard origin/main
git pull origin main

# 3. Copy config template (FIRST TIME ONLY)
cp config.example.yaml config.yaml

# 4. Set your API keys (FIRST TIME ONLY)
nano config.yaml
# Update these lines:
#   api_key: YOUR_BINGX_API_KEY
#   api_secret: YOUR_BINGX_API_SECRET

# 5. Install dependencies (if needed)
pip install -r requirements.txt

# 6. Start bot in screen
screen -S donchian-bot
python main.py
# Press Ctrl+A, then D to detach
```

## ✅ Verification

Bot should output:
```
✅ DONCHIAN_UNI LOADED - UNI-USDT
✅ DONCHIAN_PI LOADED - PI-USDT
✅ DONCHIAN_DOGE LOADED - DOGE-USDT
✅ DONCHIAN_PENGU LOADED - PENGU-USDT
✅ DONCHIAN_ETH LOADED - ETH-USDT
✅ DONCHIAN_AIXBT LOADED - AIXBT-USDT
✅ DONCHIAN_FARTCOIN LOADED - FARTCOIN-USDT
✅ DONCHIAN_CRV LOADED - CRV-USDT
📊 Total strategies loaded: 8
💰 Portfolio: 8-Coin Donchian Breakout (1H candles)
```

## 🔧 Troubleshooting

### Error: ModuleNotFoundError: No module named 'strategies.donchian_breakout'

**Cause:** GitHub code not pulled properly.

**Fix:**
```bash
cd ~/bingx-trading-bot
git reset --hard origin/main
git pull origin main
ls -la strategies/donchian_breakout.py  # Should exist!
python main.py
```

### Bot starts but no strategies loaded

**Cause:** Config file not set up.

**Fix:**
```bash
cd ~/bingx-trading-bot
cp config.example.yaml config.yaml
nano config.yaml  # Add your API keys
python main.py
```

## 📊 Strategy Parameters

All parameters are **hardcoded** in [strategies/donchian_breakout.py](strategies/donchian_breakout.py):

| Coin | Period | TP (ATR) | SL (ATR) | R:R Ratio |
|------|--------|----------|----------|-----------|
| UNI  | 30     | 10.5     | 2        | 19.35x    |
| PI   | 15     | 3.0      | 2        | 12.68x    |
| DOGE | 15     | 4.0      | 4        | 7.81x     |
| PENGU| 25     | 7.0      | 5        | 7.24x     |
| ETH  | 20     | 1.5      | 4        | 6.64x     |
| AIXBT| 15     | 12.0     | 2        | 4.73x     |
| FARTCOIN | 15 | 7.5    | 2        | 4.61x     |
| CRV  | 15     | 9.0      | 5        | 2.92x     |

**Risk:** 3% per trade (configurable in [config.yaml](config.yaml))

## 📁 Key Files

- [main.py](main.py) - Trading engine (polls every hour)
- [strategies/donchian_breakout.py](strategies/donchian_breakout.py) - Strategy logic + COIN_PARAMS
- [config.example.yaml](config.example.yaml) - Template (copy to config.yaml)
- [execution/order_executor.py](execution/order_executor.py) - Kelly position sizing
- [data/candle_builder.py](data/candle_builder.py) - Historical warmup

## 🎯 Next Steps

1. ✅ Bot running
2. Monitor logs: `screen -r donchian-bot`
3. Check trades: [database/trades.db](database/trades.db) (SQLite)
4. Performance metrics logged every hour

## 📝 Notes

- Bot polls **every hour at :01:00** (configurable in main.py)
- Fetches **300 candles** on each poll (historical warmup)
- Uses **1H candles** for all 8 coins
- **Kelly sizing**: Position size auto-adjusts based on SL distance
- **20x leverage** for margin efficiency (risk unchanged)

---

**Ready to trade!** 🚀

Questions? Check [DEPLOYMENT.md](DEPLOYMENT.md) for detailed setup.
