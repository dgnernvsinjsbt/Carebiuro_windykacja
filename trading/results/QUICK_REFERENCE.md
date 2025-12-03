# EMA50 Pullback Strategy - Quick Reference Card

## 📊 At A Glance

| Item | Value |
|------|-------|
| **Expected Return** | +70.56% per 3 months |
| **Win Rate** | 23.5% (low is normal!) |
| **Trades Per Day** | ~5 trades |
| **Average Trade Time** | 2 hours (8 candles) |
| **Max Drawdown** | 16.41% |

---

## ✅ Entry Checklist

1. **Is price above EMA50?** → YES = Trend confirmed
2. **Did price touch EMA50?** → YES = Pullback occurred
3. **Did candle close above EMA50?** → YES = Entry signal!
4. **Is daily loss < 5%?** → YES = Can trade

**If all YES → ENTER LONG**

---

## 🎯 Entry Rules

```
WHEN: Candle closes above EMA50 after touching it
WHERE: Entry Price = Close of signal candle
STOP: Place stop at LOW of signal candle
SIZE: Use 100% of current capital
```

---

## 🚪 Exit Rules

**Exit After 8 Candles** (2 hours)
- Count candles starting from entry
- On 8th candle close → EXIT at market
- Don't wait for profit/loss target

**OR Exit If Stop Hit**
- If price touches stop loss → EXIT immediately
- Accept the loss and move on

**OR Exit End of Day**
- Close all positions before midnight
- NO overnight holds ever

---

## 💰 Position Sizing

```python
Position Size = Current Capital ÷ Entry Price

Example:
Capital: $10,000
Entry: $0.7500
Size = 10,000 ÷ 0.75 = 13,333 FARTCOIN
```

---

## 🛑 Stop Loss Calculation

```
Stop Loss = Low of Entry Candle

Example:
Entry Candle: High $0.7550, Low $0.7480, Close $0.7520
Stop Loss = $0.7480
Risk = (0.7520 - 0.7480) / 0.7520 = -0.53%
```

---

## ⚠️ Daily Drawdown Rule

**If daily loss reaches -5% → STOP TRADING**

```
Starting Capital Today: $10,000
Current Capital: $9,500
Daily Loss: -5% → HALT TRADING
```

Close any open positions and wait until tomorrow.

---

## 📈 EMA50 Calculation

**Exponential Moving Average (50 periods)**

On most platforms:
- Add indicator: "EMA" or "Exponential Moving Average"
- Period: 50
- Applied to: Close price
- Timeframe: 15 minutes

---

## 🎨 Chart Setup

**Timeframe**: 15-minute candles

**Indicators**:
- EMA(50) - Main indicator
- (Optional) Volume bars for confirmation

**Colors** (suggested):
- EMA50: Yellow/Orange (easy to see)
- Bullish candles: Green
- Bearish candles: Red

---

## 🔔 Alert Setup

Set alerts for:
1. **Price crosses EMA50** → Check if entry conditions met
2. **Time = 2 hours since entry** → Time to exit
3. **Price hits stop loss** → Emergency exit

---

## 📝 Trade Log Template

```
Date: _________
Time: _________

ENTRY
Price: $______
Stop: $______
Size: _____ coins
Capital: $______

EXIT (circle one)
[ ] 8 Candles  [ ] Stop Loss  [ ] End of Day

Exit Price: $______
Exit Time: _________
P&L: ______%  ($______)

New Capital: $______

Notes:
_________________________________
_________________________________
```

---

## 🧠 Psychology Reminders

### Expected Behavior
- ✅ **76% of trades will LOSE** → This is normal!
- ✅ Losing streaks of 10+ trades can happen
- ✅ One big winner can erase many small losses

### Don't Do This
- ❌ Skip the time exit hoping for more profit
- ❌ Move stop loss further away after entry
- ❌ Revenge trade after a loss
- ❌ Double position size to "make back" losses
- ❌ Trade during daily halt period

### Do This Instead
- ✅ Follow rules exactly every single time
- ✅ Accept losses as cost of doing business
- ✅ Trust the math (positive expectancy)
- ✅ Keep detailed records
- ✅ Review performance weekly, not trade-by-trade

---

## 📊 Performance Tracking

### Daily Review
- [ ] How many trades today?
- [ ] Daily P&L: _____%
- [ ] Hit daily limit? Y / N
- [ ] Followed all rules? Y / N

### Weekly Review
- [ ] Total trades this week: _____
- [ ] Win rate: _____%
- [ ] Total return: _____%
- [ ] Any rule violations?
- [ ] Emotional state: Good / Neutral / Struggling

### Monthly Review
- [ ] Compare to backtest expectations
- [ ] Is win rate ~23-25%?
- [ ] Is average win ~2-3%?
- [ ] Is average loss ~0.5%?
- [ ] Should I continue this strategy?

---

## 🚨 Warning Signs

**Stop trading and reassess if:**
- Win rate drops below 15% for 2+ weeks
- Average loss exceeds -1% consistently
- Drawdown exceeds 25%
- You're consistently breaking rules
- You feel too stressed to trade

---

## 🎯 Success Metrics (3 months)

| Metric | Target Range | Action If Outside |
|--------|--------------|------------------|
| Total Return | 50-90% | Review if < 30% or > 100% |
| Win Rate | 20-30% | Check execution if outside |
| Profit Factor | 1.2-1.5 | Investigate if < 1.0 |
| Avg Win | 2-3% | Confirm time exit working |
| Avg Loss | -0.4% to -0.7% | Check stop losses |

---

## 💡 Quick Tips

1. **Best Time to Trade**: All hours work, but higher activity during US/Europe overlap
2. **Market Conditions**: Strategy works best in trending markets with pullbacks
3. **Ranging Markets**: Win rate may drop but big wins still possible
4. **Volatility**: Higher volatility = bigger wins but also bigger losses
5. **Patience**: Sometimes no setups for hours - don't force trades

---

## 🔧 Troubleshooting

### "I'm not seeing entry signals"
- Check EMA50 is calculating correctly
- Ensure you're on 15-minute timeframe
- Market might be ranging below EMA50
- Be patient - average 5 setups per day

### "My stop losses keep getting hit"
- This is expected (76% of trades lose)
- Ensure stop is at candle LOW, not arbitrary
- Don't move stop after entry
- Check for slippage on your exchange

### "I exit at 8 candles but price keeps going"
- Discipline is key - don't chase
- Some trades will continue, most won't
- Time exit is what makes strategy work
- Trust the backtest

### "I'm down 15% this week"
- Check if following rules exactly
- Review each trade for mistakes
- Drawdown of 16% occurred in backtest
- Don't panic - could be normal variance

---

## 📞 Emergency Protocols

### System Failure During Trade
1. Manually close position at market
2. Record actual exit price/time
3. Update capital manually
4. Resume normal trading when system restored

### Exchange Issues
1. Have backup exchange ready
2. Know how to manually execute trades
3. Keep API keys secure but accessible
4. Have emergency contact for exchange support

### Emotional Breakdown
1. Stop trading immediately
2. Close all positions
3. Take 24-hour break minimum
4. Review what triggered emotions
5. Return only when calm and rational

---

## 📚 Resources

- **Backtest Code**: `/trading/backtest.py`
- **Strategy Code**: `/trading/strategies.py` (lines 157-187)
- **Full Report**: `/trading/results/FINAL_SUMMARY.md`
- **Detailed Results**: `/trading/results/detailed_results.csv`
- **Live Template**: `/trading/live_strategy.py`

---

## 🎓 Final Reminders

> **"Plan the trade, trade the plan"**

- This strategy has positive expectancy (+70% in 3 months)
- Low win rate is FINE with good reward:risk
- Discipline beats intelligence in trading
- Track everything, review regularly
- Start small, scale up with confidence

**Good luck, and trade safely!** 🚀

---

*Last Updated: December 3, 2025*
*Strategy Performance: +70.56% (90 days, 442 trades)*
