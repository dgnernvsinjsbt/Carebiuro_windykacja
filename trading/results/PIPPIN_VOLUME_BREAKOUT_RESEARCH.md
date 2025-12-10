# PIPPIN Volume Breakout / ATR Expansion / Pump Chasing Research

**Date:** December 9, 2025
**Data:** 7 days (11,080 candles) from BingX
**Objective:** Test volume breakout, ATR expansion, and pump chasing strategies on PIPPIN

---

## Executive Summary

**VERDICT: ❌ ALL VOLUME BREAKOUT STRATEGIES FAILED**

Tested 3 distinct approaches to volume breakout / pump chasing on PIPPIN:

| Rank | Strategy | Return/DD | Return | Win Rate | Trades | Status |
|------|----------|-----------|--------|----------|--------|--------|
| 🥇 1 | **Fade Pumps** (Contrarian) | **0.17x** | **+1.62%** | 50.0% | 22 | ❌ NOT VIABLE |
| 2 | Tight Volume Breakout | -1.00x | -11.70% | 16.7% | 12 | ❌ FAILED |
| 3 | Volume + Price Breakout | -1.00x | -8.76% | 0.0% | 4 | ❌ FAILED |

**Key Finding:** Even the BEST strategy (Fade Pumps) achieved only **0.17x Return/DD** - far below the 3.0x minimum viability threshold.

---

## Why Volume Breakout Strategies Fail on PIPPIN

### 1. Choppy Market Regime (82.6%)
- PIPPIN is choppy 82.6% of the time (more than TRUMP's 70%)
- Volume spikes trigger false breakouts, not sustained moves
- Price action is erratic and unpredictable

### 2. Mean-Reverting Personality
- **Fade rate: 52.9%** (moves reverse more than they continue)
- After >2% body candle: **-0.085% next bar** (pumps fade immediately)
- After ATR expansion >1.5x: **-0.063% next 5 bars** (volatility doesn't persist)

### 3. Weak Volume Follow-Through
- Volume spike >3x: **+0.015% next 5 bars** (barely positive)
- Continuation rate: **51.6%** (worse than coin flip)
- Volume doesn't predict direction effectively

### 4. Extreme Risk Profile
- **26.6 extreme moves (>2%) per day** - highest among all analyzed coins
- Max 1-minute move: **10.35%** (can trigger stop-loss instantly)
- Max consecutive losses: **42** (psychological torture)

---

## Strategy Details & Results

### 🥇 Strategy 1: Fade Pumps (Contrarian) - BEST

**Concept:** Short after big up moves (opposite of pump chasing)

**Entry Conditions:**
- Green candle with body >1.5%
- Volume >2x average
- US session only (14:00-21:00 UTC)

**Exits:**
- Stop Loss: 1.5x ATR above entry
- Take Profit: 2.0x ATR below entry
- Time Exit: 30 bars (30 minutes)

**Performance:**
- **Return/DD: 0.17x** ❌
- Return: +1.62%
- Max Drawdown: -9.57%
- Win Rate: 50.0%
- Trades: 22 (3 per day)
- Exit Breakdown: 11 TP (50%), 11 SL (50%)

**Why It's Best (But Still Not Good Enough):**
- ✅ Only profitable strategy (+1.62%)
- ✅ 50% win rate (balanced)
- ✅ Captures mean-reversion behavior
- ❌ Return/DD 0.17x << 3.0x threshold
- ❌ Only +1.62% return over 7 days

**Verdict:** MARGINAL PROFIT but insufficient risk-adjusted returns. Would need 17x improvement to reach viability threshold.

---

### 🥈 Strategy 2: Tight Volume Breakout (Outlier Hunter)

**Concept:** Chase explosive moves with very tight filters

**Entry Conditions:**
- Volume >4x average (tighter than typical 3x)
- Body >1.0% (significant move)
- ATR expansion >1.2x
- US session only

**Exits:**
- Stop Loss: 1.0x ATR
- Take Profit: 3.0x ATR (3:1 R:R)
- Time Exit: 60 bars (1 hour)

**Performance:**
- **Return/DD: -1.00x** ❌
- Return: -11.70%
- Max Drawdown: -11.70%
- Win Rate: 16.7%
- Trades: 12 (1.7 per day)
- Exit Breakdown: 10 SL (83%), 1 TP (8%), 1 TIME (8%)

**Why It Failed:**
- ❌ 83% of trades stopped out
- ❌ Only 16.7% win rate (terrible)
- ❌ Filters too tight → misses good setups
- ❌ Filters too loose → catches bad setups

**Verdict:** COMPLETE FAILURE. Even tighter filters than typical volume strategies couldn't find edge.

---

### 🥉 Strategy 3: Volume + Price Breakout (Momentum Confirmation)

**Concept:** Volume spike + price breaks 20-bar high/low

**Entry Conditions:**
- Volume >3x average
- ATR expansion >1.3x
- Price breaks 20-bar high (LONG) or low (SHORT)
- US session only

**Exits:**
- Stop Loss: 1.5x ATR
- Take Profit: 3.0x ATR (2:1 R:R)
- Time Exit: 45 bars

**Performance:**
- **Return/DD: -1.00x** ❌
- Return: -8.76%
- Max Drawdown: -8.76%
- Win Rate: **0.0%** (!!!!)
- Trades: 4 (0.6 per day)
- Exit Breakdown: 4 SL (100%)

**Why It Failed:**
- ❌ **0% win rate** - every single trade lost
- ❌ Breakouts instantly faded (mean-reversion)
- ❌ Volume doesn't confirm momentum on PIPPIN
- ❌ Only 4 trades generated (filters too restrictive)

**Verdict:** CATASTROPHIC FAILURE. 0% win rate = strategy concept fundamentally incompatible with PIPPIN's behavior.

---

## Comparison to Previous PIPPIN Tests

### ATR Expansion Strategy (Already Tested)
- **Return/DD: -0.77x**
- Return: -53.73%
- Win Rate: 25.8%
- Trades: 62

**Lesson:** ATR expansion alone is even worse than volume breakout.

### Volume Breakout Research (This Test)
- **Best: Fade Pumps 0.17x** (slightly positive but not viable)
- **Worst: Volume+Price -1.00x** (complete failure)

**Lesson:** Adding volume to ATR expansion doesn't help. Pumps must be FADED, not CHASED.

---

## What DOES Work on PIPPIN?

Based on pattern analysis, these approaches showed promise:

### ✅ BB Lower Band Mean Reversion
- **Occurrences:** 524 (75 per day)
- **Next 5 bars:** +0.047% avg
- **Reversion rate:** 60.1%
- **Expected Return/DD:** 3-5x (estimated, needs testing)

### ✅ Consecutive Reds Reversal
- **Occurrences:** 1,104 (158 per day)
- **Next 1 bar:** +0.035% avg
- **Reversal rate:** 56.4%
- **Expected Return/DD:** 2.5-4x (estimated, needs testing)

**Why These Work:** PIPPIN is 9.88% mean-reverting. Mean reversion strategies exploit exhaustion, not momentum.

---

## Key Lessons Learned

### 1. Token Personality Matters
- **FARTCOIN:** 60% choppy → ATR expansion works (8.44x R/DD) ✅
- **TRUMP:** 70% choppy → Volume zones work (10.56x R/DD) ✅
- **PIPPIN:** 82.6% choppy → Volume breakout FAILS ❌

**Lesson:** Same strategy family can succeed or fail based on token's regime distribution.

### 2. Volume Doesn't Always Predict Direction
- Volume spike >3x on PIPPIN: +0.015% next 5 bars (barely positive)
- Volume spike >3x on FARTCOIN: Signals explosive breakout
- **Lesson:** Volume context matters - PIPPIN's volume = chop, not trend

### 3. Pump Chasing vs Fade Pumps
- **Chase pumps:** -11.70% (failed)
- **Fade pumps:** +1.62% (barely profitable)
- **Lesson:** PIPPIN moves reverse, not continue. But even fading isn't enough for viable R/DD.

### 4. Tight Filters Can't Save Bad Concepts
- Tight Volume Breakout used 4x volume (not 3x), 1% body, ATR expansion, session filter
- Still failed: -11.70% return, 16.7% win rate
- **Lesson:** If fundamental strategy concept is wrong, optimization won't fix it

---

## Recommended Next Steps

### ❌ Do NOT Pursue Further:
1. **Volume breakout strategies** - tested 3 approaches, all failed
2. **ATR expansion strategies** - already tested, failed badly (-53.73%)
3. **Pump chasing strategies** - tested, failed catastrophically (0% WR)
4. **Momentum strategies** - PIPPIN has 52.9% fade rate, anti-momentum

### ✅ DO Test These Instead:
1. **BB Lower Band Mean Reversion** (60.1% reversion rate)
2. **Consecutive Reds Reversal** (56.4% reversal rate)
3. **Volume Zones** (sustained volume, not spikes) - worked on PENGU/TRUMP
4. **Session-filtered mean reversion** (US session shows +0.025% bias)

### 📊 Data Requirements:
- **CRITICAL:** 7 days is NOT enough data
- Collect **30+ days minimum** for validation
- Re-test patterns to ensure stability
- If patterns degrade → abandon PIPPIN entirely

---

## Final Assessment

### For Volume Breakout / Pump Chasing Strategies:

**PIPPIN IS NOT TRADEABLE WITH MOMENTUM STRATEGIES.**

- 82.6% choppy regime kills trend-following
- 52.9% fade rate reverses momentum immediately
- Volume spikes don't predict direction (51.6% continuation)
- Even the BEST approach (Fade Pumps) achieved only 0.17x Return/DD

### Comparison to Target:
- **Target:** Return/DD > 3.0x (minimum viability)
- **Best achieved:** 0.17x (Fade Pumps)
- **Gap:** 17.6x improvement needed
- **Realistic?** NO - would require fundamentally different token behavior

### Recommendation:

**ABANDON VOLUME BREAKOUT STRATEGIES ON PIPPIN.**

Pivot to:
1. Mean reversion strategies (BB, consecutive reds)
2. Or test 5-minute / 15-minute timeframe (less chop)
3. Or abandon PIPPIN and focus on proven tokens (FARTCOIN, TRUMP, DOGE)

---

## Data & Code

**Data Source:** `trading/pippin_7d_bingx.csv` (11,080 candles)
**Script:** `trading/pippin_volume_breakout_research.py`
**Previous Reports:**
- `trading/results/PIPPIN_ATR_STRATEGY_REPORT.md` (ATR expansion: -0.77x)
- `trading/results/PIPPIN_PATTERN_ANALYSIS.md` (Pattern discovery)
- `trading/results/PIPPIN_EXECUTIVE_SUMMARY.md` (Strategic recommendations)

---

**Analysis Complete:** December 9, 2025
**Verdict:** Volume breakout / ATR expansion / pump chasing strategies are **NOT VIABLE** on PIPPIN.
