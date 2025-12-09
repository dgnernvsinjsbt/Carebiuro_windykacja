# PIPPIN ATR Expansion Strategy - Comprehensive Analysis

## Executive Summary

The FARTCOIN ATR Expansion strategy (8.44x Return/DD baseline on FARTCOIN/USDT over 32 days) was tested on PIPPIN/USDT over 7 days of 1-minute BingX data. **The strategy completely failed**, achieving a **-53.73% loss** with **-70.05% max drawdown** and **-0.77x Return/DD ratio**.

### Verdict: ❌ **DO NOT DEPLOY**

PIPPIN's volatility structure is fundamentally incompatible with this strategy. The core assumption that ATR expansion leads to sustained trending moves does not hold for PIPPIN.

---

## Performance Comparison

| Metric | PIPPIN (7d) | FARTCOIN (32d) | Variance |
|--------|-------------|----------------|----------|
| **Return/DD Ratio** | **-0.77x** ⛔ | **8.44x** ✅ | **-109%** |
| Total Return | -53.73% | +101.11% | -153% |
| Max Drawdown | -70.05% | -11.98% | -485% (worse) |
| Win Rate | 25.8% | 42.6% | -16.8pp |
| Trades | 62 | 94 | -34% |
| Fill Rate | 38.8% | 21.2% | +83% |
| Avg Win | +7.40% | +4.97% | +49% |
| Avg Loss | -4.00% | -2.23% | -79% (worse) |
| **TP Rate** | **9.7%** ⛔ | **40.0%** ✅ | **-76%** |
| **SL Rate** | **72.6%** ⛔ | **47.0%** | **+54%** |

### Key Insight
The 9.7% TP rate vs 40% baseline is the **smoking gun**. PIPPIN volatility doesn't sustain moves to reach the 8x ATR target that makes this strategy profitable on FARTCOIN.

---

## Root Cause Analysis

### 1. Volatility Structure Mismatch

**FARTCOIN:** Sustained trending moves after ATR expansion
**PIPPIN:** Choppy volatility spikes that quickly reverse

| Characteristic | PIPPIN | FARTCOIN |
|----------------|--------|----------|
| Avg ATR (% of price) | 0.76% | ~1.5% |
| Volatility vs baseline | 2.0x LESS volatile | Baseline |
| Price swing (test period) | 155.2% (7 days) | ~250% (32 days) |
| Move sustainability | Choppy, quick reversals | Sustained trends |

**Impact:** 8x ATR target is too far for PIPPIN's choppy moves. Trades hit 2x ATR stop before reaching 8x ATR target.

---

### 2. Negative Expectancy Per Trade

**Current Math:**
- Win Rate: 25.8% × Avg Win: +7.40% = **+1.91%**
- Loss Rate: 74.2% × Avg Loss: -4.00% = **-2.97%**
- **Net Expectancy: -1.05% per trade** ⛔

**Comparison to FARTCOIN:**
- Win Rate: 42.6% × Avg Win: +4.97% = **+2.12%**
- Loss Rate: 57.4% × Avg Loss: -2.23% = **-1.28%**
- **Net Expectancy: +0.84% per trade** ✅

---

### 3. Exit Distribution Breakdown

| Exit Type | PIPPIN | FARTCOIN | Analysis |
|-----------|--------|----------|----------|
| **TP** | 6 (9.7%) | 40% | ⛔ **76% fewer TPs** - Target too far |
| **SL** | 45 (72.6%) | 47% | ⚠️ Similar rate but worse R:R |
| **TIME** | 10 (16.1%) | 13% | ✅ Comparable |
| **END** | 1 (1.6%) | 0% | Dataset boundary |

**Critical Issue:** Only 6 out of 62 trades hit the 8x ATR target. The remaining 56 trades either stopped out (45) or timed out (10).

---

### 4. Directional Performance

#### LONG Trades (32 total)
- Win Rate: 31.2% (10 winners, 22 losers)
- Avg P&L: +0.08% (barely break-even)
- Exits: TP 6 | SL 21 | TIME 4 | END 1
- **Analysis:** LONGs are marginally viable but still unprofitable due to 68.8% SL rate

#### SHORT Trades (30 total)
- Win Rate: 20.0% (6 winners, 24 losers)
- Avg P&L: -2.27% (net loss)
- Exits: TP 0 | SL 24 | TIME 6
- **Analysis:** ⛔ **SHORTs are catastrophic** - 0% TP rate, 80% SL rate

**Conclusion:** SHORTs should be disabled entirely if testing modifications.

---

### 5. Chronological Equity Curve

| Date | Daily P&L | Cumulative Equity | Exit Breakdown |
|------|-----------|-------------------|----------------|
| Dec 2 | +20.55% | $11,944 | TP:3 SL:9 TIME:5 |
| Dec 3 | **-26.94%** | $8,690 | TP:1 SL:13 TIME:0 |
| Dec 4 | -5.40% | $8,225 | TP:0 SL:2 TIME:0 |
| Dec 5 | -1.57% | $8,097 | TP:0 SL:1 TIME:0 |
| Dec 6 | -5.28% | $7,484 | TP:1 SL:7 TIME:4 |
| Dec 7 | **-32.93%** | $5,348 | TP:0 SL:9 TIME:0 |
| Dec 8 | -2.81% | $5,198 | TP:0 SL:1 TIME:1 |
| Dec 9 | -10.98% | **$4,627** | TP:1 SL:3 TIME:0 |

**Pattern:** Two catastrophic drawdown days (Dec 3: -27%, Dec 7: -33%) wiped out early gains. Both days had 0-1 TPs and 9-13 SLs.

---

## What Would Need to Change?

### Option 1: Increase Win Rate
**Current:** 25.8% → **Need:** 35.1%
**Gap:** +9.2 percentage points

**How:**
- Better entry filters (trend confirmation, RSI, volume)
- Tighter EMA distance (2% instead of 3%)
- Session filters (avoid choppy Asian hours)

### Option 2: Tighter Stop Loss
**Current:** 2.0x ATR → **Need:** 1.28x ATR
**Reduction:** 36%

**Trade-off:** Even tighter stops may increase SL rate further (already at 72.6%)

### Option 3: Wider Take Profit
**Current:** 8.0x ATR → **Need:** 12.4x ATR
**Increase:** 55%

**Trade-off:** Even wider targets will make TP rate <5%, turning strategy into lottery

---

## Alternative Strategy Recommendations

Given PIPPIN's volatility characteristics, the following strategies may perform better:

### 1. Mean-Reversion (DOGE-style)
- **Entry:** Price 1% below SMA(20) after 4 consecutive down bars
- **SL:** 1.0x ATR
- **TP:** 6.0x ATR
- **Rationale:** PIPPIN volatility spikes tend to revert

### 2. Volume Zones (TRUMP/PEPE-style)
- **Entry:** 5+ bars with volume > 1.5x average at local highs/lows
- **SL:** 1.5x ATR or 0.5% fixed
- **TP:** 2:1 or 4:1 R:R
- **Session:** Test overnight (21:00-07:00 UTC) vs US (14:00-21:00 UTC)

### 3. Tighter ATR Parameters
- **TP:** 3-4x ATR instead of 8x
- **SL:** 1.0x ATR instead of 2x
- **Target R:R:** 3:1 or 4:1 (more achievable)
- **Test first:** Backtest with 30+ days of data

---

## Statistical Validity Warning

⚠️ **Limited Sample Size**

- **PIPPIN:** 7 days, 62 trades
- **FARTCOIN:** 32 days, 94 trades

PIPPIN's sample is **4.6x shorter** in duration and **34% fewer trades**. Results may not be statistically significant.

**Minimum recommended:** 30 days, 100+ trades for reliable conclusions.

However, the **magnitude of failure** (-53.73% vs +101.11%, -70% drawdown vs -12%) suggests the strategy is fundamentally incompatible, not just variance.

---

## Volatility Regime Analysis

### FARTCOIN (Baseline)
- **Regime:** Trending after ATR expansion (40% TP rate)
- **Behavior:** Sustained moves in one direction (8x ATR achievable)
- **Strategy fit:** ✅ Perfect - designed for this

### PIPPIN (Test)
- **Regime:** Choppy volatility spikes (9.7% TP rate)
- **Behavior:** Quick reversals, no sustained trends (8x ATR rare)
- **Strategy fit:** ❌ Incompatible - wrong volatility structure

---

## Final Recommendation

### ❌ **DO NOT DEPLOY to Live Trading**

**Reasons:**
1. **Negative expectancy** (-1.05% per trade)
2. **9.7% TP rate** vs 40% required
3. **72.6% SL rate** - constant stop-outs
4. **-70% max drawdown** - unacceptable risk
5. **Fundamental mismatch** - PIPPIN volatility ≠ FARTCOIN volatility

---

## Next Steps

1. **Test alternative strategies** (mean-reversion, volume zones)
2. **Collect more data** (30+ days) for statistical validity
3. **Optimize parameters specifically for PIPPIN:**
   - TP: 3-4x ATR
   - SL: 1.0x ATR
   - Direction: LONG only (disable SHORTs)
   - Session filter: Test US/Asia/Overnight separately
4. **Consider different approach entirely:**
   - RSI momentum (MOODENG-style)
   - Bollinger Band mean-reversion (ETH-style)
   - Chart pattern recognition

---

## Data Files

- **Data:** `/workspaces/Carebiuro_windykacja/trading/pippin_7d_bingx.csv` (11,129 candles)
- **Code:** `/workspaces/Carebiuro_windykacja/trading/pippin_atr_strategy_test.py`
- **Trades:** `/workspaces/Carebiuro_windykacja/trading/results/pippin_atr_trades.csv` (62 trades)
- **Analysis:** `/workspaces/Carebiuro_windykacja/trading/pippin_failure_analysis.py`

---

## Conclusion

The FARTCOIN ATR Expansion strategy is a proven winner on FARTCOIN (8.44x Return/DD), but it **catastrophically fails on PIPPIN** (-0.77x Return/DD, -53.73% loss). The root cause is a fundamental volatility structure mismatch:

- **FARTCOIN:** Sustained trends after ATR expansion → 8x ATR target achievable
- **PIPPIN:** Choppy volatility spikes with quick reversals → 8x ATR target too far

**Do not deploy this strategy on PIPPIN without major modifications or extensive re-optimization.**

Consider testing PIPPIN-specific strategies that suit its mean-reverting, choppy volatility profile instead of trend-following breakout strategies.

---

**Report Generated:** December 2025
**Strategy Tested:** FARTCOIN ATR Expansion (8.44x R/DD baseline)
**Test Asset:** PIPPIN/USDT (BingX)
**Test Period:** 7 days (Dec 2-9, 2025)
**Result:** ❌ FAILED - DO NOT DEPLOY
