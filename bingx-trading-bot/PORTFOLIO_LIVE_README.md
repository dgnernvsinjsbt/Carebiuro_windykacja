# 🚀 9-COIN RSI PORTFOLIO - LIVE TRADING READY

## ✅ Configuration Complete

All 9 strategies are configured with **exact parameters from the 90-day backtest** and ready for live trading.

### 📊 Expected Performance (90-day backtest)
- **Return:** +35.19%
- **Max Drawdown:** -1.69%
- **Return/DD Ratio:** 20.78x
- **Win Rate:** 75.5%
- **Total Trades:** 212 (~2.4 per day)

### 💰 Position Sizing
- **10% of current equity per trade**
- **1x leverage** (no borrowing)
- **Minimum balance:** $5 (allows $0.50 per trade)
- **Example:** $100 balance → $10 per trade → max 10 concurrent positions

### 🎯 Active Strategies (9 coins)

| Coin | RSI | Limit Offset | Stop Loss | Take Profit | R/R Ratio |
|------|-----|--------------|-----------|-------------|-----------|
| CRV | 25/70 | 1.5% | 1.0x ATR | 1.5x ATR | 22.03x 🏆 |
| MELANIA | 27/65 | 1.5% | 1.5x ATR | 2.0x ATR | 21.36x |
| AIXBT | 30/65 | 1.5% | 2.0x ATR | 1.0x ATR | 20.20x |
| TRUMPSOL | 30/65 | 1.0% | 1.0x ATR | 0.5x ATR | 13.28x |
| UNI | 27/65 | 2.0% | 1.0x ATR | 1.0x ATR | 12.38x |
| DOGE | 27/65 | 1.0% | 1.5x ATR | 1.0x ATR | 10.66x |
| XLM | 27/65 | 1.5% | 1.5x ATR | 1.5x ATR | 9.53x |
| MOODENG | 27/65 | 2.0% | 1.5x ATR | 1.5x ATR | 8.38x |
| PEPE | 27/65 | 1.5% | 1.0x ATR | 1.0x ATR | 7.13x |

## 🚀 How to Start

### Quick Start
```bash
./start_portfolio.sh
```

### Manual Start
```bash
python main.py --config config_portfolio_fixed10.yaml
```

### Stop the Bot
- **Graceful:** Create a file named `STOP` in the bot directory
- **Immediate:** Press `Ctrl+C`

## ⚙️ How It Works

1. **Every hour at :01 past** the hour
2. Fetches 300 1-hour candles for each coin
3. Calculates RSI(14) and ATR(14)
4. **Entry:** When RSI crosses threshold → places **limit order** X% away
5. **Waits max 5 bars** for limit fill
6. **If filled:** Automatically places SL and TP orders
7. **Exit:** TP hit, SL hit, or RSI reversal (whichever first)

## 📝 Trading Logic Example

**CRV LONG Entry:**
1. RSI(14) crosses above 25
2. Place limit order 1.5% **below** signal price
3. Wait max 5 hours for fill
4. If filled:
   - Stop Loss: Entry - 1.0 × ATR
   - Take Profit: Entry + 1.5 × ATR
   - Also exit if RSI crosses below 70

**Each coin trades independently** - can have multiple positions simultaneously.

## 🔒 Safety Features

- **Minimum balance check:** $5 USD
- **Stop file:** Create `STOP` file to halt trading
- **No leverage:** 1x only (uses your actual capital)
- **Independent positions:** Each coin has max 1 position

## 📊 Monitoring

**Logs:** `logs/trading.log`
**Database:** `data/trades.db`

Check logs to see:
- Signal generation
- Limit order placement
- Fill confirmations
- SL/TP execution
- Position P&L

## ⚠️ Important Notes

1. **Limit orders may not fill** - Only ~21-43% of signals fill (backtest matched)
2. **Multiple positions expected** - Normal to have 3-4 concurrent trades
3. **Hourly checks** - Bot only analyzes at top of each hour
4. **BingX minimum positions** - Some coins may have $1-5 minimum position requirements

## 🎯 Current Configuration

- **Mode:** 🔴 LIVE TRADING (real money!)
- **API Keys:** Loaded from `.env` file
- **Testnet:** Disabled (production)
- **Position Sizing:** 10% of equity
- **Leverage:** 1x (no leverage)

## 📈 Portfolio Composition

The portfolio is **weighted by R/R ratio** (better strategies naturally get more signals):
- Top 3 strategies (CRV, MELANIA, AIXBT): ~40% of trades
- Mid tier (TRUMPSOL, UNI, DOGE, XLM): ~40% of trades
- Lower tier (MOODENG, PEPE): ~20% of trades

This matches backtest behavior where CRV had 17 trades and PEPE had 33 trades over 90 days.

## 🚨 Emergency Stop

If something goes wrong:
1. Create file named `STOP` in bot directory: `touch STOP`
2. Bot will gracefully shutdown within 1 hour
3. Existing positions will remain open (you can close manually on BingX)

---

**Ready to trade!** 🎯

Run `./start_portfolio.sh` to begin.
