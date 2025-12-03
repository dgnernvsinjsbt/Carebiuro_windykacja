# Sample Trades - EMA50 Pullback Strategy

## Visual Examples of How the Strategy Works

This document shows hypothetical trade examples to illustrate the EMA50 Pullback + 8-Candle Time Exit strategy in action.

---

## 📊 Understanding the Entry

### Chart Setup
```
Price Chart (15-minute candles)
|
|   /\
|  /  \  ← Price above EMA50 (uptrend)
| /    \_____ EMA50 (yellow line)
|/         \  ← Pullback touches EMA50
|           ▲ ← Entry: Close above EMA50
|
└───────────────────────────────> Time
```

---

## ✅ Example 1: Typical Winning Trade (Small Win)

### Setup
```
EMA50: $0.7500
Previous trend: Price at $0.7650 (above EMA50)
```

### Trade Flow

**Candle 1-3: Pullback**
```
Candle 1: Open $0.7650 → Close $0.7600 (moving down)
Candle 2: Open $0.7600 → Close $0.7520 (still falling)
Candle 3: Open $0.7520 → Low $0.7480 → Close $0.7530 (touches EMA50)
         ↓ EMA50 is at $0.7500, low of $0.7480 touched it
         ↓ Closes at $0.7530 (ABOVE EMA50)
         ✅ ENTRY SIGNAL!
```

**Entry Execution**
```
Entry Price: $0.7530
Stop Loss: $0.7480 (low of entry candle)
Risk: ($0.7530 - $0.7480) / $0.7530 = -0.66%
Position Size: $10,000 / $0.7530 = 13,280 FARTCOIN
```

**Candles 4-10: Hold for 8 candles**
```
Candle 4: $0.7530 → $0.7550 (up)
Candle 5: $0.7550 → $0.7570 (up)
Candle 6: $0.7570 → $0.7590 (up)
Candle 7: $0.7590 → $0.7600 (up)
Candle 8: $0.7600 → $0.7610 (up)
Candle 9: $0.7610 → $0.7620 (up)
Candle 10: $0.7620 → $0.7640 (up)
Candle 11: $0.7640 → $0.7650 (up)
         ↓ 8 candles complete
         ✅ TIME EXIT
```

**Exit Execution**
```
Exit Price: $0.7650 (close of 8th candle)
P&L: ($0.7650 - $0.7530) / $0.7530 = +1.59%
Dollar Gain: 13,280 × ($0.7650 - $0.7530) = +$159.36
New Capital: $10,159.36
Duration: 2 hours (8 × 15min candles)
```

**Result**: ✅ +1.59% win in 2 hours

---

## ✅ Example 2: Large Winning Trade (Momentum Continuation)

### Setup
```
EMA50: $0.6800
Previous trend: Strong uptrend, price at $0.7200
Sharp pullback occurs (volatility spike)
```

### Trade Flow

**Entry**
```
Pullback low touches EMA50 at $0.6780
Entry Candle: Low $0.6780 → Close $0.6850
Entry Price: $0.6850
Stop Loss: $0.6780
Risk: -1.02%
Position Size: $10,159 / $0.6850 = 14,833 FARTCOIN
```

**During Hold (Strong Momentum)**
```
Candle 4: Price jumps to $0.7100 (news/momentum)
Candle 5: $0.7100 → $0.7300 (continued momentum)
Candle 6: $0.7300 → $0.7450
Candle 7: $0.7450 → $0.7600
Candle 8: $0.7600 → $0.7800
Candle 9: $0.7800 → $0.8200
Candle 10: $0.8200 → $0.8400
Candle 11: Exit at $0.8400
```

**Exit Execution**
```
Exit Price: $0.8400
P&L: ($0.8400 - $0.6850) / $0.6850 = +22.63%
Dollar Gain: 14,833 × ($0.8400 - $0.6850) = +$2,299
New Capital: $12,458
Duration: 2 hours
```

**Result**: ✅ +22.63% win - **This type of rare big winner makes the strategy work!**

---

## ❌ Example 3: Typical Losing Trade (Stop Loss Hit)

### Setup
```
EMA50: $0.8000
Previous trend: Weak uptrend, price at $0.8100
```

### Trade Flow

**Entry**
```
Pullback to EMA50
Entry Candle: Low $0.7980 → Close $0.8020
Entry Price: $0.8020
Stop Loss: $0.7980
Risk: -0.50%
Position Size: $12,458 / $0.8020 = 15,532 FARTCOIN
```

**Stop Loss Triggered (Candle 2)**
```
Candle 4: Open $0.8020 → Low $0.7960 → Close $0.7990
         ↓ Low of $0.7960 broke stop at $0.7980
         ❌ STOP LOSS EXIT
```

**Exit Execution**
```
Exit Price: $0.7980 (stop loss level)
P&L: ($0.7980 - $0.8020) / $0.8020 = -0.50%
Dollar Loss: 15,532 × ($0.7980 - $0.8020) = -$62
New Capital: $12,396
Duration: 30 minutes (2 candles)
```

**Result**: ❌ -0.50% loss in 30 minutes

**Note**: Small losses like this are expected 76% of the time!

---

## ❌ Example 4: Losing Trade (Time Exit at Loss)

### Setup
```
EMA50: $0.7700
Price pulls back and bounces but trend doesn't resume
```

### Trade Flow

**Entry**
```
Entry Price: $0.7720
Stop Loss: $0.7680
Risk: -0.52%
Position Size: $12,396 / $0.7720 = 16,057 FARTCOIN
```

**During Hold (Choppy Action)**
```
Candle 4: $0.7720 → $0.7730 (small gain)
Candle 5: $0.7730 → $0.7710 (back down)
Candle 6: $0.7710 → $0.7720 (sideways)
Candle 7: $0.7720 → $0.7700 (down more)
Candle 8: $0.7700 → $0.7690 (continues down)
Candle 9: $0.7690 → $0.7680 (near stop)
Candle 10: $0.7680 → $0.7700 (bounce)
Candle 11: Exit at $0.7700
         ↓ 8 candles complete
         ⏰ TIME EXIT (at small loss)
```

**Exit Execution**
```
Exit Price: $0.7700
P&L: ($0.7700 - $0.7720) / $0.7720 = -0.26%
Dollar Loss: 16,057 × ($0.7700 - $0.7720) = -$32
New Capital: $12,364
Duration: 2 hours
```

**Result**: ❌ -0.26% loss after full 2 hours (choppy market)

---

## 📊 10-Trade Sequence Example

Showing realistic performance over 10 trades:

| # | Entry | Stop | Exit | P&L | Capital | Note |
|---|-------|------|------|-----|---------|------|
| 1 | $0.7530 | $0.7480 | $0.7650 | +1.59% | $10,159 | Small win |
| 2 | $0.8020 | $0.7980 | $0.7980 | -0.50% | $10,108 | Stopped out |
| 3 | $0.7720 | $0.7680 | $0.7700 | -0.26% | $10,082 | Time exit loss |
| 4 | $0.7890 | $0.7850 | $0.7850 | -0.51% | $10,030 | Stopped out |
| 5 | $0.8100 | $0.8060 | $0.8080 | -0.25% | $10,005 | Time exit loss |
| 6 | $0.6850 | $0.6780 | $0.8400 | +22.63% | $12,268 | 🎯 BIG WIN! |
| 7 | $0.8210 | $0.8170 | $0.8170 | -0.49% | $12,208 | Stopped out |
| 8 | $0.7950 | $0.7910 | $0.8020 | +0.88% | $12,315 | Small win |
| 9 | $0.8300 | $0.8260 | $0.8260 | -0.48% | $12,256 | Stopped out |
| 10 | $0.7800 | $0.7760 | $0.7950 | +1.92% | $12,491 | Medium win |

**Summary of 10 Trades:**
- Wins: 4 (40%) - Above average win rate!
- Losses: 6 (60%)
- Net Result: +24.91% gain
- Key: One big win (+22.63%) covered all losses and added profit

**Typical Pattern**: Many small losses, occasional small wins, rare large wins that drive profits.

---

## 🎯 Key Observations from Sample Trades

### Why Low Win Rate Works

**Math Behind It:**
```
Winners (30% of trades, simplified for example):
- 3 × (+2.0%) = +6.0%

Losers (70% of trades):
- 7 × (-0.5%) = -3.5%

Net: +6.0% - 3.5% = +2.5% average per 10 trades
```

With daily compounding over 90 days and occasional big wins (like +22%), this compounds to +70%!

### The Role of Time Exit

**If we held winners "until they reverse":**
- Many small winners would turn into losers
- Psychological torture watching profits evaporate
- Overall performance would likely be worse

**8-candle time exit advantages:**
- Captures quick mean reversion moves
- Prevents winners from turning to losers
- Removes emotion ("Should I hold or exit?")
- Simple rule = easy execution

### The Importance of Big Wins

In the 10-trade example, **ONE big winner** (+22.63%) made the strategy profitable despite 60% loss rate.

Over 442 trades in backtest:
- Largest win: +25.30%
- Average win: +2.29%
- Win rate: 23.53%

**This distribution is CRITICAL** - without occasional large wins, strategy wouldn't work.

---

## 📈 Equity Curve Visualization (Conceptual)

```
Capital Over 10 Trades

$12,500 |                                    •─────• (Trade 10)
        |                          •────────•
$12,000 |                         ╱
        |                        ╱
$11,500 |                       ╱
        |         •────────────• (Trade 6: +22.63%)
$11,000 |        ╱
        |       ╱
$10,500 |      ╱
        | •───• (Trades 1-5: small wins/losses)
$10,000 |•──────────────────────────────────────────> Trades
        1   2   3   4   5   6   7   8   9   10

Key Events:
- Trades 1-5: Choppy, mostly flat
- Trade 6: Big momentum win shoots equity up
- Trades 7-10: Back to choppy, but above starting point
```

---

## ⚠️ Psychological Reality Check

### What Losing Streaks Look Like

**7 Losing Trades in a Row** (will happen!):

```
Trade 1: -0.50% → $9,950
Trade 2: -0.48% → $9,902
Trade 3: -0.52% → $9,851
Trade 4: -0.49% → $9,803
Trade 5: -0.51% → $9,753
Trade 6: -0.50% → $9,704
Trade 7: -0.48% → $9,658

Down -3.42% from 7 trades
```

**Then comes the bounce back:**

```
Trade 8: +1.80% → $9,832
Trade 9: -0.47% → $9,786
Trade 10: +3.20% → $10,099 (back above starting!)
```

**Can you handle this emotionally?** Be honest with yourself.

---

## 🧪 Test Yourself

Before trading live, verify you understand:

### Quiz Questions

1. **When do you enter?**
   - [ ] When price crosses above EMA50 ✅
   - [ ] When RSI is oversold ❌
   - [ ] When you "feel" market will go up ❌

2. **When do you exit (normal conditions)?**
   - [ ] When profit is +5% ❌
   - [ ] After 8 candles ✅
   - [ ] When you're bored ❌

3. **If your stop is hit on trade 2, what do you do?**
   - [ ] Double position size next trade to "make it back" ❌
   - [ ] Stop trading for the day ❌
   - [ ] Accept the loss, look for next setup ✅

4. **You've had 8 losers in a row. What do you do?**
   - [ ] Question the strategy, stop trading ❌
   - [ ] Keep following rules, next trade could be the big winner ✅
   - [ ] Change the rules ❌

5. **You're up +2% after 4 candles. Exit now?**
   - [ ] Yes, take the profit! ❌
   - [ ] No, wait for 8-candle time exit ✅

**If you got any wrong, review QUICK_REFERENCE.md before trading!**

---

## 📝 Sample Trade Log Format

Use this template to track your trades:

```
═══════════════════════════════════════════════════════
TRADE LOG #___
═══════════════════════════════════════════════════════
Date: _____________ Time: _____________

ENTRY
├─ Price: $________
├─ Stop: $________ (Risk: ___%)
├─ Size: ________ FARTCOIN
└─ Capital Before: $________

MARKET CONTEXT
├─ EMA50: $________
├─ Entry Reason: Pullback bounced above EMA50
└─ Market Condition: [ ] Trending [ ] Ranging [ ] Volatile

HOLD PERIOD (Track each candle)
├─ Candle 1: $________ [ ] Above entry [ ] Below
├─ Candle 2: $________ [ ] Above entry [ ] Below
├─ Candle 3: $________ [ ] Above entry [ ] Below
├─ Candle 4: $________ [ ] Above entry [ ] Below
├─ Candle 5: $________ [ ] Above entry [ ] Below
├─ Candle 6: $________ [ ] Above entry [ ] Below
├─ Candle 7: $________ [ ] Above entry [ ] Below
└─ Candle 8: $________ [ ] Above entry [ ] Below

EXIT
├─ Price: $________
├─ Reason: [ ] 8 Candles [ ] Stop Loss [ ] End of Day
└─ Time: _____________

RESULTS
├─ P&L: _____% ($________)
├─ Capital After: $________
├─ Duration: ____ candles (____ minutes)
└─ Outcome: [ ] WIN [ ] LOSS

NOTES/LESSONS
_____________________________________________
_____________________________________________
_____________________________________________

═══════════════════════════════════════════════════════
```

---

## 🎓 Conclusion

These sample trades show the **realistic day-to-day experience** of trading the EMA50 Pullback strategy:

✅ **Most trades are small** (±0.5% to ±2%)
✅ **Losses are frequent but small** (average -0.52%)
✅ **Winners are less frequent but larger** (average +2.29%)
✅ **Rare big winners are the profit driver** (5-25% gains)

**The key to success:**
1. Follow rules exactly every single trade
2. Accept that most trades will lose
3. Don't exit early on winners
4. Don't move stops on losers
5. Trust the math over hundreds of trades

**Remember**: This isn't a "get rich quick" scheme. It's a systematic approach with positive expectancy that works over time through discipline and compounding.

---

*For more details, see FINAL_SUMMARY.md and QUICK_REFERENCE.md*
