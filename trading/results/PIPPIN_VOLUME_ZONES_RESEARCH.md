# PIPPIN Volume Zones Strategy Research

**Date:** December 9, 2025
**Data:** 7 days (11,100 candles) from BingX
**Objective:** Test sustained volume zones (5+ consecutive bars) vs single spikes

---

## Executive Summary

**VERDICT: ❌ VOLUME ZONES ALSO FAIL ON PIPPIN**

Tested 5 volume zone configurations (inspired by TRUMP 10.56x, DOGE 10.75x, PEPE 6.80x success):

| Rank | Strategy | Return/DD | Return | Win Rate | Trades/Day | Status |
|------|----------|-----------|--------|----------|------------|--------|
| 🥇 | **DOGE-style (Asia/EU)** | **0.78x** | **+4.90%** | 38.5% | 1.9 | ❌ NOT VIABLE |
| 🥈 | PEPE-style (Overnight) | -0.18x | -1.60% | 40.0% | 2.1 | ❌ FAILED |
| 🥉 | Relaxed (Lower threshold) | -0.34x | -10.58% | 32.8% | 38.3 | ❌ FAILED |
| 4 | US Session Focus | -0.51x | -5.07% | 36.4% | 1.6 | ❌ FAILED |
| 5 | TRUMP-style (Overnight) | -0.88x | -15.53% | 20.0% | 2.1 | ❌ FAILED |

**Key Finding:** Even the BEST configuration (DOGE-style Asia/EU) achieved only **0.78x Return/DD** - far below the 3.0x minimum viability threshold.

---

## What Are Volume Zones? (vs Spikes)

### Volume SPIKES (Already Tested - FAILED)
- **Definition:** Single bar with volume >3x average
- **On PIPPIN:** 39 per day, but 51.6% continuation (random)
- **Result:** -11.70% return, 0.17x R/DD ❌

### Volume ZONES (This Test)
- **Definition:** 5+ consecutive bars with volume >1.5x average
- **Logic:** Sustained volume = whale accumulation/distribution (not noise)
- **Worked on:** TRUMP (10.56x), DOGE (10.75x), PEPE (6.80x)
- **On PIPPIN:** 39 zones detected, but only 0.78x R/DD ❌

---

## Strategy Details & Results

### 🥇 DOGE-style (Asia/EU) - BEST (But Still Not Good Enough)

**Configuration:**
- **Volume threshold:** 1.5x average
- **Min zone bars:** 5 consecutive
- **Session:** Asia/EU (07:00-14:00 UTC)
- **Stop Loss:** 1.5x ATR
- **Take Profit:** 4.0x ATR (2.67:1 R:R)
- **Max Hold:** 90 bars

**Performance:**
- **Return/DD: 0.78x** ❌
- Return: +4.90% (slightly positive)
- Max Drawdown: -6.30%
- Win Rate: 38.5%
- Trades: 13 (1.9/day)
- Avg Win: +3.68%
- Avg Loss: -1.64%
- Exit Breakdown: 8 SL (62%), 5 TP (38%)
- **Top 20% concentration: 196.6%** (very outlier dependent!)

**Why It's Best:**
- ✅ Only profitable config (+4.90%)
- ✅ Asia/EU session avoids worst overnight losses
- ✅ Relatively shallow drawdown (-6.30%)
- ❌ Return/DD 0.78x << 3.0x threshold
- ❌ 196.6% top 20% concentration (losing overall, big winners save it)

**Analysis:**
The strategy is slightly profitable BUT:
- Top 20% trades (3 trades) contribute 196.6% of profit
- Remaining 80% (10 trades) lose money
- This is EXTREME outlier dependency (worse than TRUMP's 88.6%)
- Can't cherry-pick outliers - must take all signals
- Result: +4.90% is too small for the risk

---

### 🥈 PEPE-style (Overnight, Tight) - Second Best

**Configuration:**
- Volume: 1.5x, Min bars: 5, Session: Overnight
- SL: 1.0x ATR, TP: 2.0x ATR (2:1 R:R - tighter than DOGE)
- Max Hold: 90 bars

**Performance:**
- **Return/DD: -0.18x** ❌
- Return: -1.60%
- Max Drawdown: -9.05%
- Win Rate: 40.0% (best WR among all configs)
- Trades: 15 (2.1/day)
- Exit: 9 SL (60%), 6 TP (40%)

**Why It Failed:**
- Tight 2:1 R:R not enough on PIPPIN (works on PEPE due to 66.7% WR)
- Overnight session poor on PIPPIN (-0.018% bias)
- Even with 40% WR, couldn't overcome chop

---

### 🥉 Relaxed (Lower Threshold) - High Frequency Failure

**Configuration:**
- Volume: 1.3x (lower), Min bars: 3 (shorter zones)
- Session: All (no filter), SL: 1.5x ATR, TP: 3.0x ATR
- Max Hold: 90 bars

**Performance:**
- **Return/DD: -0.34x** ❌
- Return: -10.58%
- Max Drawdown: -30.91%
- Win Rate: 32.8%
- **Trades: 268 (38.3/day!)** - Massive overtrading
- Exit: 179 SL (67%), 87 TP (32%), 2 TIME (1%)

**Why It Failed Catastrophically:**
- Relaxed filters detected 271 zones (vs 39 with strict filters)
- 38 trades/day = overtrading in choppy regime
- 67% stopped out, 33% hit TP (not enough)
- Largest drawdown: -30.91% (unacceptable)

---

### TRUMP-style (Overnight) - Worst Performer

**Configuration:**
- Based on TRUMP's winning config (10.56x R/DD on TRUMP)
- Volume: 1.5x, Min bars: 5, Session: Overnight
- SL: 1.5x ATR, TP: 4.0x ATR

**Performance:**
- **Return/DD: -0.88x** ❌
- Return: **-15.53%** (worst return)
- Max Drawdown: -17.59%
- Win Rate: **20.0%** (worst WR)
- Trades: 15 (2.1/day)
- Exit: 12 SL (80%), 3 TP (20%)

**Why It Failed:**
- Config that won on TRUMP (10.56x) loses badly on PIPPIN
- 80% stopped out vs TRUMP's 38% SL rate
- Overnight session loses on PIPPIN (-0.018% bias)
- **Same strategy, different token = opposite results**

---

### US Session Focus - Expected to Work, Didn't

**Configuration:**
- Volume: 1.5x, Min bars: 5, Session: US (best for PIPPIN)
- SL: 1.5x ATR, TP: 3.0x ATR (2:1 R:R)
- Max Hold: 60 bars

**Performance:**
- **Return/DD: -0.51x** ❌
- Return: -5.07%
- Win Rate: 36.4%
- Trades: 11 (1.6/day)

**Why It Failed:**
- US session is best for PIPPIN (+0.025% avg return)
- But volume zones still don't predict direction
- 64% stopped out despite favorable session

---

## Comparison: Volume Spikes vs Volume Zones

| Metric | Volume SPIKES (tested earlier) | Volume ZONES (this test) |
|--------|--------------------------------|--------------------------|
| **Best Return/DD** | 0.17x (Fade Pumps) | **0.78x (DOGE Asia/EU)** |
| **Best Return** | +1.62% | **+4.90%** |
| **Best Win Rate** | 50.0% | 38.5% |
| **Trades/Day** | 3.1 | 1.9 |
| **Detection Method** | Single bar >3x volume | 5+ bars >1.5x volume |
| **Status** | ❌ NOT VIABLE | ❌ NOT VIABLE |

**Conclusion:** Volume zones slightly better than spikes (0.78x vs 0.17x) but still far from viable (need 3.0x+).

---

## Why Volume Zones Fail on PIPPIN

### 1. Choppiness Kills Directional Edge
- PIPPIN: **82.6% choppy** (worse than TRUMP's 70%)
- Volume zones detect accumulation/distribution correctly
- But breakouts from zones instantly fade (52.9% fade rate)
- Even sustained volume doesn't predict follow-through

### 2. Outlier Dependency Too Extreme
- DOGE-style: **196.6% top 20% concentration**
- Means: 80% of trades lose money, 20% make all profit + extra to offset losses
- Compare to:
  - TRUMP: 88.6% concentration (high but profitable)
  - DOGE BingX: 95.3% concentration (high but profitable)
  - PIPPIN: 196.6% = losing strategy saved by few winners

### 3. Session Filters Don't Help Enough
- US session (+0.025% bias): Still lost -5.07%
- Asia/EU session: Only +4.90% (0.78x R/DD)
- Overnight session: Lost -15.53%
- **Lesson:** Session edge too small to overcome chop

### 4. Token Behavior Doesn't Transfer
- TRUMP overnight zones: 10.56x R/DD ✅
- PIPPIN overnight zones: -0.88x R/DD ❌
- **Same config, opposite results** = token personality matters

---

## What Works on Other Tokens vs PIPPIN

| Token | Choppy % | Best Strategy | Return/DD | Works on PIPPIN? |
|-------|----------|---------------|-----------|------------------|
| FARTCOIN | 60% | ATR Expansion | 8.44x | ❌ NO (-0.77x) |
| TRUMP | 70% | Volume Zones | 10.56x | ❌ NO (-0.88x) |
| DOGE | ~70% | Volume Zones | 10.75x | ❌ NO (0.78x) |
| PEPE | ~70% | Volume Zones | 6.80x | ❌ NO (-0.18x) |
| PIPPIN | **82.6%** | ??? | **???** | **Nothing works yet** |

**Conclusion:** PIPPIN is TOO CHOPPY for any momentum-based strategy (volume zones, ATR expansion, breakouts).

---

## Remaining Approaches to Test

Based on pattern analysis, these are the ONLY remaining approaches with potential:

### ✅ 1. BB Lower Band Mean Reversion
- **Pattern performance:** 60.1% reversion rate
- **Frequency:** 524 occurrences (75/day)
- **Expected Return/DD:** 3-5x (estimated)
- **Status:** NOT YET TESTED

### ✅ 2. Consecutive Reds Reversal
- **Pattern performance:** 56.4% reversal rate
- **Frequency:** 1,104 occurrences (158/day)
- **Expected Return/DD:** 2.5-4x (estimated)
- **Status:** ALREADY TESTED - likely profitable

### ⚠️ 3. Switch to Higher Timeframe
- **5-minute or 15-minute candles** may reduce chop
- 1-minute = 82.6% choppy
- 5-minute = potentially 60-70% choppy (more tradeable)
- **Status:** Alternative approach if mean reversion fails

### ❌ Do NOT Test:
- ❌ Any momentum strategies (ATR, volume, breakouts) - all tested, all failed
- ❌ Pump chasing - already tested, 0% win rate
- ❌ Price action patterns - RSI/BB breakouts also failed

---

## Key Lessons

### 1. Volume Zones Are Not Universal
- Work on TRUMP (10.56x), DOGE (10.75x), PEPE (6.80x)
- Fail on PIPPIN (0.78x best)
- **Lesson:** Token personality > strategy type

### 2. Sustained Volume ≠ Direction Prediction
- Volume zones correctly identify accumulation/distribution
- But on PIPPIN, zones don't predict breakout direction
- **Lesson:** Volume must combine with low chop for edge

### 3. Session Filters Insufficient
- US session has +0.025% bias (best for PIPPIN)
- But combining with volume zones still loses
- **Lesson:** Small session edge can't overcome 82.6% chop

### 4. Outlier Dependency Warning Sign
- 196.6% top 20% concentration = unsustainable
- Compare to viable outlier strategies:
  - TRUMP: 88.6% (still profitable with discipline)
  - PIPPIN: 196.6% (losing with rare big winners)
- **Lesson:** >150% concentration = not a real edge

---

## Final Assessment

### For Volume Zones on PIPPIN:

**❌ NOT TRADEABLE**

- Best config: 0.78x Return/DD (need 3.0x minimum)
- Gap to viability: 3.8x improvement needed
- Realistic? NO - would require fundamentally different token behavior

### Complete Testing Summary (All Momentum Strategies):

| Strategy Type | Best R/DD | Status |
|---------------|-----------|--------|
| Volume Spikes | 0.17x | ❌ FAILED |
| Volume Zones | **0.78x** | ❌ FAILED |
| ATR Expansion | -0.77x | ❌ FAILED |
| Volume + Price Breakout | -1.00x | ❌ FAILED |
| Pump Chasing | -1.00x | ❌ FAILED |

**Conclusion:** PIPPIN is **incompatible with ALL momentum-based strategies**. Only mean reversion remains.

---

## Recommendation

**ABANDON momentum strategies on PIPPIN. Test mean reversion immediately.**

### Immediate Next Steps:
1. ✅ **Test BB mean reversion** (60.1% reversion rate, 75/day)
2. ⚠️ **Collect 30+ days data** (7 days not enough for confidence)
3. ⚠️ **Consider 5-minute timeframe** (reduce chop from 82.6%)
4. ❌ **Or abandon PIPPIN** - focus on proven tokens (FARTCOIN, TRUMPSOL)

---

## Data & Code

**Data:** `trading/pippin_7d_bingx.csv` (11,100 candles)
**Script:** `trading/pippin_volume_zones_research.py`
**Previous Reports:**
- Volume Breakout: `trading/results/PIPPIN_VOLUME_BREAKOUT_RESEARCH.md` (0.17x best)
- ATR Expansion: `trading/results/PIPPIN_ATR_STRATEGY_REPORT.md` (-0.77x)
- Pattern Analysis: `trading/results/PIPPIN_PATTERN_ANALYSIS.md`

---

**Analysis Complete:** December 9, 2025
**Verdict:** Volume zones strategy is **NOT VIABLE** on PIPPIN (0.78x R/DD << 3.0x threshold).
