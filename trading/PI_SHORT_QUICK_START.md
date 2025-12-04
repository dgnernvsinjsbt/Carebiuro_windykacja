# PI/USDT SHORT STRATEGY - QUICK START GUIDE

## 🎯 Strategy at a Glance

**Name:** EMA 5/20 Cross Down (Risk-Reward 1.5:1)
**Direction:** SHORT ONLY
**Timeframe:** 15-minute candles
**Return:** +41.10% over 3 months (after fees)
**Win Rate:** 45%
**Trades:** ~67 per month

---

## 📋 Entry Rules (ALL must be true)

1. **Wait for EMA Crossover:**
   - EMA(5) crosses BELOW EMA(20)
   - This signals momentum shift from bullish to bearish

2. **Enter Short:**
   - Enter at the CLOSE of the candle where crossover occurs
   - Entry price = Close price of that candle

---

## 📋 Exit Rules (First one hit)

**Option A - Take Profit (45% of trades):**
- Price drops to: Entry - (1.5 × Risk)
- If entry = $0.35000 and stop = $0.36050 (risk = $0.01050)
- Take profit = $0.35000 - (1.5 × $0.01050) = $0.33425

**Option B - Stop Loss (55% of trades):**
- Price rises to: Entry + 3%
- If entry = $0.35000
- Stop loss = $0.36050

---

## 💰 Position Sizing Example

**Account Balance:** $10,000
**Risk Per Trade:** 1% = $100

**Calculation:**
1. Maximum loss per trade = $100
2. Stop loss distance = 3% from entry
3. Position size = $100 / 0.03 = **$3,333**

**Short $3,333 worth of PI/USDT**
- If stopped out: Lose $100 (1% of account)
- If take profit hits: Gain $150 (1.5% of account)

---

## 🔧 Technical Indicators Needed

**Required:**
- EMA(5) - Exponential Moving Average, 5 periods
- EMA(20) - Exponential Moving Average, 20 periods

**How to add on TradingView:**
1. Click "Indicators" button
2. Search "EMA"
3. Add "Moving Average Exponential"
4. Set length to 5 for first one
5. Repeat and set length to 20 for second one

---

## 📊 Entry Example

```
Time: 14:00
EMA(5) previous candle: 0.3520 (above EMA20)
EMA(20) previous candle: 0.3510

Time: 14:15 (current candle closes)
EMA(5) now: 0.3508 (below EMA20) ← CROSSOVER!
EMA(20) now: 0.3510
Close price: 0.3515

ACTION: Enter SHORT at 0.3515
Stop Loss: 0.3520 + 3% = 0.3626
Take Profit: 0.3515 - (1.5 × 0.0111) = 0.3348
```

---

## ⚠️ Critical Rules

**DO:**
- ✅ Always use the stop loss (3% above entry)
- ✅ Take profit at 1.5:1 ratio automatically
- ✅ Risk only 1-2% per trade
- ✅ Limit to 1-2 concurrent shorts
- ✅ Use taker fee ≤ 0.005% exchanges

**DON'T:**
- ❌ Move stop loss further away (keep at 3%)
- ❌ Let winners run past target (take profit at 1.5:1)
- ❌ Revenge trade after losses
- ❌ Risk more than 2% per trade
- ❌ Short during extreme bull runs

---

## 📱 Automation Code (Pine Script v5)

```pinescript
//@version=5
strategy("PI Short - EMA 5/20", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=100)

// Indicators
ema5 = ta.ema(close, 5)
ema20 = ta.ema(close, 20)

// Entry: EMA5 crosses below EMA20
shortCondition = ta.crossunder(ema5, ema20)

if (shortCondition)
    strategy.entry("Short", strategy.short)

// Exit conditions
if (strategy.position_size < 0)
    entryPrice = strategy.position_avg_price
    stopLoss = entryPrice * 1.03
    risk = stopLoss - entryPrice
    takeProfit = entryPrice - (risk * 1.5)
    
    strategy.exit("Exit", "Short", stop=stopLoss, limit=takeProfit)

// Plot EMAs
plot(ema5, color=color.red, linewidth=2, title="EMA 5")
plot(ema20, color=color.blue, linewidth=2, title="EMA 20")

// Plot signals
plotshape(shortCondition, title="Short Signal", location=location.abovebar, color=color.red, style=shape.triangledown, size=size.small)
```

---

## 📈 Expected Performance

**Over 100 trades, expect approximately:**
- 45 winners averaging +1.60% each = +72% gross profit
- 55 losers averaging -0.97% each = -53.35% gross loss
- Net profit = +18.65% (before considering compounding)
- With compounding: ~41% over 3 months

**Monthly targets:**
- ~67 signals per month
- ~30 winners, ~37 losers
- Net positive each month on average

---

## 🚨 Warning Signs (Stop Trading If:)

1. **Win rate drops below 35%** for 50+ trades
2. **Average loss exceeds 1.5%** consistently
3. **Drawdown exceeds 20%** of peak equity
4. **Market enters strong uptrend** (price stays above both EMAs)
5. **Slippage exceeds 0.1%** regularly

---

## 📁 File Locations

All analysis files are in: `/workspaces/Carebiuro_windykacja/trading/results/`

**Review these files:**
1. `PI_SHORT_EXECUTIVE_SUMMARY.md` - Full detailed summary
2. `pi_short_analysis.md` - Technical analysis and metrics
3. `pi_short_equity.png` - Visual equity curve
4. `pi_short_analysis_charts.png` - Performance charts
5. `pi_short_summary.csv` - All 200 trades data

**Code files:**
1. `/trading/pi_short_backtest.py` - Backtest script (run anytime)
2. `/trading/pi_short_visualize.py` - Chart generation

---

## 🎯 First Steps

1. **Study the strategy:** Read this guide + executive summary
2. **Paper trade:** Track signals for 1-2 weeks without real money
3. **Small size:** Start with 25% of intended position size
4. **Track results:** Compare to backtest metrics
5. **Scale up:** Increase size after 20+ successful trades
6. **Review monthly:** Ensure performance matches expectations

---

## 💡 Key Success Factors

1. **Discipline:** Follow rules exactly (no emotions)
2. **Stop losses:** Always use them, never move them
3. **Position sizing:** Never risk >2% per trade
4. **Patience:** Wait for valid crossover signals
5. **Acceptance:** 55% of trades will lose (normal!)

---

## 📞 Quick Reference Stats

| Metric | Value |
|--------|-------|
| Total Return | +41.10% |
| Win Rate | 45% |
| Avg Win | +1.60% |
| Avg Loss | -0.97% |
| Max Drawdown | 13.11% |
| Profit Factor | 1.35 |
| Trades (3mo) | 200 |
| Signals/Month | ~67 |

---

**Strategy Status:** ✅ PRODUCTION READY
**Risk Level:** Medium (managed with stops)
**Skill Level Required:** Beginner-Intermediate
**Time Commitment:** Can be automated or manually monitored every few hours

**Good luck and trade responsibly!**
