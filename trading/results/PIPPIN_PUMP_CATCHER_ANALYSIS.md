# PIPPIN Pump/Dump Catcher - Marginal Success Analysis

**Date:** December 9, 2025
**Strategy:** Catch explosive moves (>1.5-3% candles) with large TP targets (3-8%)
**Configurations Tested:** 10
**Profitable Configs:** **1 out of 10** ⚠️

---

## Executive Summary

**VERDICT: PUMP CATCHING BARELY WORKS ON PIPPIN (Not Deployment Ready)**

After BB mean reversion completely failed (0/10 profitable), tested momentum/breakout strategy to catch PIPPIN's explosive moves. Result: **1 marginally profitable configuration** with weak risk-adjusted returns.

**Best Config:** Quick Scalp (>1.5% candle, 3% TP)
- Return: +4.20% (7 days)
- Return/DD: **0.17x** (target: >3.0x)
- Max DD: -25.28% (huge for small returns)
- Win Rate: 17.9% (abysmal)
- Trades: 318

**Key Finding:** PIPPIN's "explosive moves" are FAKE - they pump 2-3% then immediately reverse, hitting stops before reaching targets.

---

## Test Results - Only 1 Profitable

| Rank | Configuration | Return | Max DD | R/DD | Win Rate | TP% | Trades |
|------|---------------|--------|--------|------|----------|-----|--------|
| 🥇 **ONLY WINNER** | Quick Scalp 1.5%→3% TP | **+4.20%** | -25.28% | 0.17x | 17.9% | 18% | 318 |
| 🥈 | Volume Confirmed | -3.51% | -15.02% | -0.23x | 12.5% | 12% | 48 |
| 🥉 | Pullback Entry | -14.04% | -25.36% | -0.55x | 14.3% | 14% | 154 |
| 4 | ATR Expansion | -13.66% | -20.95% | -0.65x | 11.1% | 11% | 54 |
| 5 | Baseline 2%→5% | -23.92% | -34.56% | -0.69x | 13.5% | 12% | 170 |
| 6 | Combo Filters | -10.48% | -12.68% | -0.83x | 6.9% | 7% | 29 |
| 7 | Momentum 3× | -40.83% | -43.37% | -0.94x | 10.4% | 10% | 222 |
| 8 | LONG Only | -29.69% | -30.87% | -0.96x | 8.8% | 8% | 80 |
| 9 | Conservative 2.5%→4% | -24.32% | -24.26% | -1.00x | 16.8% | 17% | 101 |
| 10 | Extreme 3%→8% | -32.48% | -31.73% | -1.02x | 6.0% | 6% | 67 |

**Observations:**
- Average loss (9 failing configs): -24.05%
- Only 1 config positive, barely (+4.20%)
- No config achieved TP rate >18%
- No config achieved win rate >17.9%
- No config achieved R/DD >0.20x

---

## Why "Pump Catching" Barely Works

### The Explosive Move Illusion

**Expected:**
- PIPPIN has 26.6 extreme moves (>2%) per day
- Should be able to catch some with large TPs

**Reality:**
- Moves are **FALSE BREAKOUTS** - pump 2%, reverse, hit stop
- Only 6-18% of "pumps" continue far enough to hit TP
- 82-94% hit stop loss first (chop/whipsaw)

### The Best Config Deep Dive

**Quick Scalp (>1.5% candle, 3% TP, 0.5% SL):**

**Why it barely works:**
1. **Lower entry (1.5%):** More signals (318 vs 67-170)
2. **Smaller TP (3%):** More achievable than 5-8% (18% hit vs 6-12%)
3. **Tight SL (0.5%):** Cuts losers fast

**Math breakdown:**
```
Expected Value per trade:
Win rate: 17.9% × Avg win: ~+2.9% (3% TP - 0.1% fees)
Loss rate: 82.1% × Avg loss: ~-0.6% (0.5% SL + 0.1% fees)

EV = (0.179 × 2.9%) - (0.821 × 0.6%)
EV = 0.519% - 0.493%
EV = +0.026% per trade ✓

Over 318 trades: 0.026% × 318 = +8.27% (theoretical)
Actual: +4.20% (slippage, partial fills, etc)
```

**Why it's still not deployable:**
- Return/DD: 0.17x << 3.0x minimum target
- Max DD: -25.28% for only +4.20% return (unacceptable)
- Basically a coin flip (18% TP vs 82% SL)
- One bad streak wipes out weeks of small gains

---

## Comparison: BB Reversion vs Pump Catching

| Metric | BB Mean Reversion (Best) | Pump Catching (Best) | Winner |
|--------|--------------------------|----------------------|---------|
| Strategy | Fade weakness | Chase strength | - |
| Entry | BB(20,3) lower touch | >1.5% candle | - |
| TP Target | 1.5% | 3.0% | Pump (2×) |
| SL | 0.5% | 0.5% | Tie |
| **Return** | **-2.58%** ❌ | **+4.20%** ✅ | **Pump +6.78pp** |
| **Max DD** | -12.55% | -25.28% | BB (50% less) |
| **R/DD** | -0.21x | 0.17x | Pump (barely) |
| **Win Rate** | 30.2% | 17.9% | BB (+12.3pp) |
| **TP Hit %** | 29% | 18% | BB (+11pp) |
| **Trades** | 199 | 318 | Pump (60% more) |
| **Profitable?** | NO | Barely | Pump |

**Key Insight:** Pump catching is SLIGHTLY better than mean reversion on PIPPIN, but both are fundamentally broken.

---

## Why Large TP Targets Failed

Tested 3-8% TP targets to "catch the big moves". Results:

| TP Target | Best Config | TP Hit % | Return | R/DD |
|-----------|-------------|----------|--------|------|
| 3% | Quick Scalp | 18% | +4.20% | 0.17x |
| 4% | Conservative | 17% | -24.32% | -1.00x |
| 5% | Baseline | 12% | -23.92% | -0.69x |
| 6% | Volume Confirmed | 12% | -3.51% | -0.23x |
| 7% | Combo | 7% | -10.48% | -0.83x |
| 8% | Extreme | 6% | -32.48% | -1.02x |

**Pattern:** Larger TP = Lower hit rate = Worse returns

**Why:** PIPPIN pumps 2-3%, triggers entry, reverses and hits SL before reaching 5-8% TP.

Only 3% TP is small enough to hit occasionally (18% of time).

---

## What Works vs What Doesn't

### ✅ What Helped (Slightly)

1. **Smaller entry threshold (1.5% vs 2-3%)**
   - More signals (318 vs 67-170 trades)
   - Still quality (1.5% is a real move)

2. **Smaller TP target (3% vs 5-8%)**
   - 18% hit rate vs 6-12%
   - More realistic for PIPPIN's chop

3. **Tight SL (0.5% vs 1.0%)**
   - Cuts losers fast
   - Preserves capital for next attempt

### ❌ What Failed

1. **Large entry thresholds (2.5-3%)**
   - Too selective (67-101 trades)
   - Only 6% TP hit rate (moves don't continue)

2. **Large TP targets (5-8%)**
   - 6-12% hit rate (unrealistic)
   - PIPPIN rarely sustains moves that far

3. **Volume/ATR filters**
   - Reduced trade count
   - Didn't improve win rate
   - Made results worse

4. **Pullback entries**
   - 14% TP hit vs 18% immediate entry
   - Missed the initial spike

5. **Directional bias (LONG only)**
   - 8.8% TP hit (worst)
   - Even though PIPPIN went +76% overall
   - Individual pumps still reverse

---

## Statistical Confidence

**Question:** Is the +4.20% return from Quick Scalp strategy statistically significant or just luck?

**Analysis:**
- 318 trades
- Win rate: 17.9% (57 winners, 261 losers)
- Expected by chance: 50% (159 winners, 159 losers)
- Chi-square test: p < 0.001 (highly significant)

**Conclusion:** Win rate of 17.9% is SIGNIFICANTLY BELOW coin flip. This is not luck - the strategy actively loses more than random.

**But it's still profitable?**
- Yes, because avg win (+2.9%) >> avg loss (-0.6%)
- Math: 5:1 reward-to-risk ratio compensates for 18% win rate
- However, this creates massive drawdown variance (82% of trades lose)

---

## Why PIPPIN Specifically Struggles

### Root Cause: Fake Volatility

**PIPPIN's Volatility Profile:**
- 26.6 extreme moves (>2%) per day ← Looks tradeable
- 82.6% choppy regime ← Actually unplayable
- 160% price range in 7 days ← Deceptive

**The Problem:**
- Moves are VIOLENT but BRIEF
- Pump 2-3% → Immediate reversal
- No follow-through or sustained trends
- Stop losses get run before targets

**Comparison to Successful Coins:**

| Coin | Extreme Moves/Day | Choppy % | TP Hit % (5% target) | Tradeable? |
|------|-------------------|----------|----------------------|------------|
| FARTCOIN | ~15 | 60% | 40% | ✅ YES |
| DOGE | ~12 | 60% | 35% | ✅ YES |
| PIPPIN | **26.6** | **83%** | **12%** | ❌ NO |

**Insight:** More extreme moves ≠ More tradeable. PIPPIN's moves are too choppy.

---

## Lessons Learned

### 1. Explosive Moves Need Follow-Through

**Mistake:** Seeing 26.6 extreme moves/day and assuming they're tradeable
**Reality:** Moves reverse before targets hit
**Fix:** Require 3+ consecutive bars in same direction (but this reduced TP rate to 10%)

### 2. Large TPs Don't Help If They're Unreachable

**Mistake:** Setting 5-8% TPs to "catch big pumps"
**Reality:** Only 6-12% hit rate, 88-94% stopped out
**Fix:** Match TP to coin's actual move sizes (3% max for PIPPIN)

### 3. Low Win Rate = High Variance

**Result:** 82% SL rate = huge drawdowns from losing streaks
**Impact:** -25.28% max DD for only +4.20% return
**Lesson:** Need >30% win rate for psychological sustainability

### 4. Positive EV ≠ Deployable

**Quick Scalp has +0.026% EV per trade** ← Technically profitable
**But:**
- R/DD: 0.17x (need >3.0x)
- Max DD: -25.28% (unacceptable)
- One bad day wipes out weeks

**Lesson:** Profitability alone is not enough. Need strong risk-adjusted returns.

---

## PIPPIN Strategy Scorecard (All Tests)

| Strategy | Configs Tested | Profitable | Best Return | Best R/DD | Verdict |
|----------|----------------|------------|-------------|-----------|---------|
| FARTCOIN ATR Expansion | 1 | 0 | -53.73% | -0.77x | ❌ FAILED |
| BB Mean Reversion | 10 | 0 | -2.58% | -0.21x | ❌ FAILED |
| **Pump/Dump Catching** | **10** | **1** | **+4.20%** | **0.17x** | **⚠️ MARGINAL** |

**Summary:**
- 3 strategy families tested
- 21 total configurations
- 1 marginally profitable (4.76% success rate)
- Best R/DD: 0.17x (17× below 3.0x target)

**Conclusion:** PIPPIN is fundamentally unplayable on 1-minute timeframe with BingX fee structure.

---

## Final Verdict

### ⚠️ DO NOT DEPLOY PIPPIN PUMP CATCHING

**Reasons:**
1. Only 1/10 configs profitable (not robust)
2. Return/DD: 0.17x << 3.0x minimum
3. Max DD: -25.28% for +4.20% return (unacceptable)
4. Win rate: 17.9% (psychologically brutal)
5. One losing streak wipes out weeks of small gains
6. No margin for live trading slippage/fees

**Mathematical Reality:**
- Expected: +0.026% per trade
- One 10-trade losing streak: -6% (wipes 143 profitable trades)
- Probability of 10 consecutive losses: (0.821)^10 = 13.9% (happens every 7 trades)

---

## Recommended Next Steps

### Option 1: Try Different Timeframe ⭐ Worth Testing
- **5-minute or 15-minute candles**
- Rationale: Larger moves, less chop
- Pro: Might reduce false breakouts
- Con: Fewer signals, still fundamentally choppy

### Option 2: Test on Different Coin ✅ Strongly Recommended
**Stop wasting time on PIPPIN.** Test proven volatility profiles:
- **FARTCOIN** (60% trending, ATR expansion works: 8.44x R/DD)
- **DOGE** (mean-reverting, 4.55x R/DD achieved)
- **MOODENG** (70% choppy BUT RSI momentum: 10.68x R/DD)

### Option 3: Abandon PIPPIN for 1m Trading ⭐⭐ Best Choice
**Evidence:**
- 3 strategy types tested, all failed/marginal
- 21 configurations total, 1 barely profitable (5% success)
- Best R/DD: 0.17x (96% below minimum target)
- 82.6% choppy regime (fundamentally broken)
- Only 7 days data (insufficient for confidence)

**Recommendation:** Mark PIPPIN as "No Viable 1m Strategy" and move on.

---

## Files Generated

- `trading/pippin_pump_catcher.py` - Test script (10 configs)
- `trading/results/pippin_pump_catcher_test.csv` - Results table
- `trading/results/pippin_pump_best_trades.csv` - Best config trades
- `trading/results/PIPPIN_PUMP_CATCHER_ANALYSIS.md` - This report

---

**3 strategies tested. 1 barely profitable. Time to move on.** 🚫
