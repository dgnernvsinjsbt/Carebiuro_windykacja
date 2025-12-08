# PEPE/USDT Trading Strategy Discovery - Executive Summary

**Date**: December 7, 2025
**Analyst**: Claude AI Trading System
**Objective**: Find profitable strategy with R:R >= 2.0

---

## CRITICAL RESULT: OBJECTIVE NOT MET

**No strategy achieved the 2.0 R:R target on PEPE/USDT 1m data.**

Best R:R achieved: **0.74** (63% below target)

---

## Data Overview

- **Symbol**: PEPE/USDT
- **Timeframe**: 1 minute
- **Period**: November 7 - December 7, 2025 (30 days)
- **Candles**: 43,201
- **Price Range**: $0.00000555 - $0.00002200 (296% range)
- **Exchange**: LBank

---

## Best Strategy Found

### BB Mean Reversion with Tight ATR Stops (1.5x/3x)

**Performance Metrics:**
- **R:R Ratio**: 0.74 (Target: 2.0)
- **Total PnL**: +11.0%
- **Max Drawdown**: -14.9%
- **Win Rate**: 48.3%
- **Total Trades**: 902 (30 trades/day)

**Strategy Details:**
- **Entry**: Price drops below lower Bollinger Band (20-period, 2 std dev)
- **Stop Loss**: Entry - (1.5 × ATR14)
- **Take Profit**: Entry + (3.0 × ATR14)
- **Fees**: 0.1% (market orders)
- **Average Trade Duration**: 14 minutes

**Trade Statistics:**
- Winning Trades: 436 (48.3%)
  - Average Win: +0.47%
  - Best Win: +2.98%
- Losing Trades: 466 (51.7%)
  - Average Loss: -0.41%
  - Worst Loss: -1.12%
- Win/Loss Ratio: 1.13x (Target: 2.0x)

---

## Why PEPE Failed

### 1. Extremely Low Win/Loss Ratio
- **Achieved**: 1.13x
- **Required for 2.0 R:R**: 2.0x
- **Gap**: 77% improvement needed

The average winning trade (+0.47%) was barely larger than the average losing trade (-0.41%). This means even with a 50% win rate, the strategy struggles to be profitable.

### 2. Slightly Negative Win Rate
- **Achieved**: 48.3%
- **Breakeven (at 1.13x ratio)**: ~47%
- **Ideal**: 50%+

### 3. Large Drawdown Relative to Gains
- **Total Gain**: +11.0%
- **Max Drawdown**: -14.9%
- **Ratio**: 0.74

For a 2.0 R:R, the strategy would need either:
- Same drawdown (-14.9%) with +29.8% total PnL, OR
- Same total PnL (+11.0%) with -5.5% max drawdown

---

## What Was Tested

### Total Strategies: 13

**1. Bollinger Band Mean Reversion** (4 variants)
- Best: +11.0% PnL, 0.74 R:R ✓ (winner)
- Worst: -15.6% PnL, -0.47 R:R

**2. EMA Trend Following** (3 variants)
- All FAILED catastrophically
- Worst: -182.2% PnL, -0.99 R:R
- Best: -91.5% PnL, -0.96 R:R

**3. RSI Oversold** (3 variants)
- All negative
- Range: -10.9% to -24.3% PnL
- R:R: -0.45 to -0.63

**4. Limit Orders (Lower Fees)** (3 variants)
- Helped but not enough
- Best: +12.4% PnL, 0.55 R:R
- Lower R:R due to wider stops needed

**5. EMA + RSI Pullback**
- Too restrictive, no trades generated

---

## Key Insights

### Insight #1: PEPE is Fundamentally Different from Other Meme Coins

**Comparison to Previously Tested Tokens:**

| Token | Best R:R | Best Strategy | Notes |
|-------|----------|---------------|-------|
| FARTCOIN | 1.70+ | BB3 Market Orders | Multiple strategies > 2.0 |
| MELANIA | 2.0+ | Various | Strong momentum |
| PENGU | 2.0+ | Various | Clear trends |
| **PEPE** | **0.74** | **BB MR 1.5x/3x** | **High chop, low persistence** |

### Insight #2: Tight Stops > Wide Stops (Unusual)

Normally meme coins need wide stops to let winners run. PEPE showed the opposite:

| Stop/Target | PnL | R:R |
|-------------|-----|-----|
| 1.5x / 3x ATR | +11.0% | 0.74 ✓ |
| 2.0x / 4x ATR | -15.6% | -0.47 |
| 2.5x / 5x ATR | -4.7% | -0.16 |
| 3.0x / 6x ATR | -2.8% | -0.09 |

This suggests PEPE has:
- Rapid mean reversions that need quick exits
- Frequent false moves that punish patient holders
- Low momentum persistence

### Insight #3: Trend Following Destroyed Capital

EMA crossover strategies lost 91-182% of capital. This indicates:
- Extreme whipsaw action
- False breakouts
- Sideways grinding with no directional edge

### Insight #4: High Trade Frequency

902 trades in 30 days = 30 trades/day = 1.25 trades/hour

This shows PEPE oscillates frequently around its mean, but:
- Most oscillations are small
- Risk/reward on individual trades is poor
- High trade frequency increases slippage/fee impact

---

## Recommended Next Steps

### Priority 1: Test Higher Timeframes
**1m may be too noisy for PEPE.**

Test in order:
1. **5m timeframe** - Reduce noise, maintain trade frequency
2. **15m timeframe** - Clearer trends, lower chop
3. **30m timeframe** - Momentum strategies may work

**Expected**: 5m should reduce whipsaw while keeping 5-10 trades/day

### Priority 2: Test Short Strategies
PEPE may have downside edge. Test:
- BB upper band rejection (short)
- Breakdown below support
- RSI overbought shorts (>70, >75, >80)

### Priority 3: Add Advanced Filters

**Volume Filters:**
- Only trade when volume > 2x average
- Avoid low-volume chop

**Volatility Regime:**
- Only trade in specific ATR ranges
- Avoid both extreme volatility and dead zones

**Session Filters:**
- Asian (0-8 UTC)
- European (8-14 UTC)
- US (14-22 UTC)

One session may have stronger edge than 24h trading.

### Priority 4: Dynamic Position Sizing
Current tests used fixed 1x size. Implement:
- Kelly Criterion
- Anti-Martingale (increase after wins)
- Drawdown-based reduction

### Priority 5: Consider Abandoning PEPE
If 5m/15m timeframes also fail to achieve 2.0 R:R:
- **Focus on proven tokens** (FARTCOIN, MELANIA, PENGU)
- **Use PEPE in portfolio** (not standalone)
- **Accept lower R:R** if consistent (0.8-1.0 R:R with 60%+ win rate)

---

## Files Generated

1. **pepe_master_backtest.py** - Comprehensive strategy tester (13+ strategies, sessions, filters)
2. **pepe_quick_discovery.py** - Medium-speed tester (~40 strategies)
3. **pepe_fast_test.py** - Fast core strategy tester (13 strategies) ✓ Used
4. **visualize_pepe_best.py** - Analysis and charts for best strategy
5. **results/pepe_fast_results.csv** - Raw test results
6. **results/PEPE_STRATEGY_DISCOVERY.md** - Detailed technical report
7. **results/pepe_best_strategy_analysis.png** - Equity curve, drawdown, PnL distribution
8. **PEPE_EXECUTIVE_SUMMARY.md** - This document

---

## Comparison to Prompt Requirements

| Requirement | Target | Achieved | Status |
|-------------|--------|----------|--------|
| R:R Ratio | >= 2.0 | 0.74 | FAIL ❌ |
| Win Rate | >= 50% | 48.3% | CLOSE ⚠️ |
| Min Trades | >= 30 | 902 | PASS ✓ |
| Fee Structure | 0.1% / 0.07% | Tested both | PASS ✓ |
| ATR-based stops | Yes | Multiple variants | PASS ✓ |
| Sessions tested | Asian/Euro/US | (Fast test: 24h only) | PARTIAL ⚠️ |

**Overall**: 2/6 full pass, 2/6 partial, 2/6 fail

---

## Final Recommendation

### DO NOT trade PEPE on 1m timeframe with current strategies.

**Next Action**: Run 5m timeframe test ASAP.

**If 5m also fails**: Move PEPE to "difficult tokens" list and focus on:
- FARTCOIN (proven 1.70 R:R)
- MELANIA (proven 2.0+ R:R)
- PENGU (proven 2.0+ R:R)

**Alternative**: Use PEPE as part of diversified portfolio, accepting lower individual R:R if it's uncorrelated with other tokens.

---

## Key Takeaway

**Not all meme coins are created equal.**

PEPE's extreme choppiness and low momentum persistence make it fundamentally harder to trade profitably on 1m timeframe compared to other meme coins that showed clear edges.

The system correctly identified this through rigorous testing rather than deploying capital on an unsuitable token.

---

*Report Generated: December 7, 2025*
*Testing Platform: Claude AI Trading Analysis*
*Status: OBJECTIVE NOT MET - FURTHER TESTING REQUIRED*
