# UNI/USDT Pattern Discovery - Complete Analysis Index

**Analysis Date:** December 8, 2025
**Analyst:** Master Pattern Noticer
**Dataset:** 43,001 1-minute candles (30 days: Nov 7 - Dec 7, 2025)

---

## 🎯 Executive Summary

**VERDICT: UNI/USDT is NOT TRADEABLE on 1-minute timeframe.**

- ❌ **Zero high-confidence patterns found** (WR > 60% & edge > 0.1%)
- ⚠️ **All edges marginal** (< 0.1%, eaten by 0.10% fees)
- 📉 **Losing bias**: 46.4% overall win rate
- 🔄 **79.8% mean-reverting** but reversals too weak to profit
- 💸 **Best alternative**: Skip UNI or try higher timeframes

---

## 📚 Documentation Structure

### Quick Start (Read These First)

1. **UNI_QUICK_REFERENCE.txt** (133 lines)
   - One-page summary of all findings
   - Top 3 patterns (all marginal)
   - Why UNI fails on 1m
   - Alternative recommendations
   - **Start here for TL;DR**

2. **UNI_EXECUTIVE_SUMMARY.md** (209 lines)
   - Detailed verdict with reasoning
   - Coin personality profile
   - Session analysis breakdown
   - Strategy recommendations
   - **Read this for actionable insights**

### Deep Dive Analysis

3. **UNI_PATTERN_ANALYSIS.md** (193 lines)
   - Comprehensive technical report
   - Full session statistics
   - Top 20 sequential patterns
   - Top 20 statistical edges
   - Regime distribution analysis
   - Next steps for strategy development
   - **Read this for full methodology**

### Data Files (CSV)

4. **UNI_session_stats.csv** (4 sessions)
   - Avg return, volatility, win rates per session
   - Best/worst hours within sessions
   - Volume characteristics

5. **UNI_sequential_patterns.csv** (52 patterns)
   - Pattern → outcome probabilities
   - Explosive candles, consecutive bars, wicks, BB touches, volume spikes
   - Sorted by expected return

6. **UNI_regime_analysis.csv** (717 60-min windows)
   - Timeline of regime classifications
   - Trending, mean-reverting, choppy, explosive
   - Price changes and volatility per window

7. **UNI_statistical_edges.csv** (63 edges)
   - RSI extremes, SMA crosses, time-based patterns
   - Expected returns and win rates
   - Sample sizes for statistical confidence

8. **UNI_pattern_stats.csv** (4 patterns)
   - Confidence-filtered patterns (HIGH/MEDIUM)
   - Result: Zero high-confidence, 4 medium (all negative edge)

### Source Code

9. **pattern_discovery_UNI.py** (750 lines)
   - Fully replicable analysis script
   - Technical indicator calculations
   - Pattern detection algorithms
   - Statistical edge testing
   - Automated report generation

---

## 🔑 Key Findings at a Glance

### Market Regime (60-min windows)
| Regime | % of Time | Tradeable? |
|--------|-----------|------------|
| Mean-Reverting | 79.8% | ❌ (reversals too weak) |
| Choppy | 10.6% | ❌ (unplayable noise) |
| Trending | 9.5% | ❌ (too rare, weak trends) |
| Explosive | 0.1% | ❌ (almost never) |

### Session Performance
| Session | Avg Return | Best For | Recommendation |
|---------|-----------|----------|----------------|
| Overnight | +0.0043% | Long bias | Still too weak |
| Asia | +0.0007% | Neutral | Skip |
| US | -0.0006% | Slight short bias | Skip |
| Europe | -0.0018% | Short bias | Skip |

### Coin Personality
- **Volatility**: NORMAL (0.205% avg candle, ATR 0.0143)
- **Momentum**: NEUTRAL (-0.0162 autocorr, no strong bias)
- **Liquidity**: INCONSISTENT (CV 2.40, spiky volume)
- **Risk**: HIGH (47.17% max drawdown)

### Top 3 Patterns (All Marginal)
1. **After explosive bear** → LONG 3 bars: +0.628% (n=6, too rare)
2. **5+ consec red** → LONG 5 bars: +0.021% (n=940, edge too small)
3. **BB lower touch** → LONG 5 bars: +0.011% (n=2200, coin flip)

---

## 🚫 Why Traditional Strategies Fail

### Mean-Reversion
- ❌ Reversals exist (79.8% mean-reverting) but are tiny (0.01-0.02%)
- ❌ Win rate: 50-51% (no edge)
- ❌ Fees (0.10%) eat the entire edge

### Trend-Following
- ❌ Only 9.5% trending regime (5% up + 4.5% down)
- ❌ No momentum follow-through (-0.0162 autocorr)
- ❌ Trends are weak and short-lived

### Scalping
- ❌ Candle range too small (0.205% avg)
- ❌ Volume inconsistent (can't trust breakouts)
- ❌ Slippage + fees destroy micro-edges

### Volume Breakouts
- ❌ Volume spikes have zero follow-through (tested)
- ❌ Volume zones might work but edge is marginal

---

## 💡 Recommendations

### Best Option: SKIP UNI on 1m
Focus on proven profitable coins:
- **MOODENG**: +24.02% (R/DD 10.68x, RSI momentum strategy)
- **FARTCOIN SHORT**: +20.08% (R/DD 8.88x, trend distance)
- **TRUMP**: +8.06% (R/DD 10.56x, volume zones overnight)
- **PEPE**: +2.57% (R/DD 6.80x, volume zones, -0.38% max DD)
- **DOGE**: +7.64% (R/DD 2.61x, mean reversion 4.55x R:R)

### If You Must Trade UNI

#### Option A: Higher Timeframes
- Try 5m, 15m, or 30m
- Mean-reversion patterns may work better with larger moves
- Fees become smaller % of edge

#### Option B: Volume Zone Strategy (Low Confidence)
- **Entry**: 5+ bars with volume >1.5x at local extremes
- **Session**: Overnight only (22:00 UTC)
- **Stops**: 1.5x ATR (~$0.021)
- **Targets**: 4:1 R:R (wide targets to overcome low WR)
- **Orders**: LIMIT ORDERS ONLY (save 0.03% on entry)
- **Expected**: Marginal profitability at best, 45-50% win rate

**Reality Check**: Even with perfect execution, you'll likely break even or lose slightly due to:
- 46.4% natural win rate
- Tiny edges (0.01-0.04%)
- Inconsistent volume makes entries difficult
- 79.8% mean-reversion with weak bounces

---

## 📊 Analysis Methodology

### Patterns Analyzed
- **Sequential**: 52 patterns (explosive candles, consecutive bars, rejection wicks, BB touches, volume spikes)
- **Statistical**: 63 edges (RSI extremes, SMA crosses, day/hour patterns)
- **Sessions**: 4 (Asia, Europe, US, Overnight)
- **Regimes**: 5 classifications over 717 60-min windows

### Quality Standards
- **High confidence**: Win rate > 60% AND edge > 0.1% (above fees)
- **Medium confidence**: Win rate > 50% AND edge > 0.05%
- **Minimum samples**: 20+ trades for statistical validity
- **Fees**: 0.10% round-trip (BingX futures taker 0.05% x2)

### Tools Used
- Technical indicators: RSI(14), SMA(20/50/200), BB(20,2std/3std), ATR(14)
- Statistical analysis: Autocorrelation, win rates, expected returns
- Time analysis: Hourly, daily, session-based patterns
- Volume analysis: Spikes, dry-ups, sustained accumulation/distribution

### Result
- **High-confidence patterns**: 0
- **Medium-confidence patterns**: 4 (all negative edge)
- **Tradeable patterns**: 0
- **Recommendation**: AVOID

---

## 🎓 Lessons Learned

### What This Analysis Revealed
1. **Not all coins are tradeable on all timeframes**
   - UNI's 1m structure has no exploitable edges
   - 79.8% mean-reverting ≠ profitable mean-reversion

2. **Fees matter critically**
   - 0.10% round-trip = minimum 0.1% edge needed
   - UNI's best edges are 0.01-0.06% (too small)

3. **Win rate + edge size both matter**
   - 51% WR with 0.02% edge = losing strategy
   - Need either high WR (>60%) OR large edge (>0.2%)

4. **Volume consistency is crucial**
   - UNI's CV 2.40 = unpredictable volume spikes
   - Makes volume-based strategies unreliable

### Comparison to Winning Strategies
| Coin | Strategy | Return | R/DD | Max DD | Win Rate | Why It Works |
|------|----------|--------|------|--------|----------|--------------|
| MOODENG | RSI Momentum | +24.02% | 10.68x | -2.25% | 31% | Strong momentum, 4:1 R:R compensates low WR |
| FARTCOIN | Trend Distance SHORT | +20.08% | 8.88x | -2.26% | N/A | Clear downtrends, explosive breakdowns |
| TRUMP | Volume Zones | +8.06% | 10.56x | -0.76% | 61.9% | Sustained volume = real whale activity |
| PEPE | Volume Zones | +2.57% | 6.80x | -0.38% | 66.7% | High WR, smoothest equity curve |
| **UNI** | **N/A** | **N/A** | **N/A** | **-47.17%** | **46.4%** | **NO EXPLOITABLE EDGE** |

---

## 🔄 Next Steps

### If You Want to Trade UNI
1. **Download higher timeframe data** (5m, 15m, 30m)
2. **Re-run pattern discovery** on longer timeframes
3. **Test volume zone strategy** (low confidence)
4. **Consider spot market** (no leverage, less fees)

### If You Want to Trade Profitably
1. **Pick a different coin** with proven edges (see above table)
2. **Use existing strategies** with documented backtests
3. **Start small** (0.5% risk per trade)
4. **Track performance** live before scaling up

---

## 📁 File Inventory

### Summary Documents
- `UNI_INDEX.md` (this file) - Navigation and overview
- `UNI_QUICK_REFERENCE.txt` - One-page TL;DR
- `UNI_EXECUTIVE_SUMMARY.md` - Detailed verdict

### Technical Reports
- `UNI_PATTERN_ANALYSIS.md` - Full analysis report

### Data Files
- `UNI_session_stats.csv` - Session performance
- `UNI_sequential_patterns.csv` - Pattern probabilities
- `UNI_regime_analysis.csv` - Regime timeline
- `UNI_statistical_edges.csv` - Technical edges
- `UNI_pattern_stats.csv` - Confidence-filtered patterns

### Source Code
- `pattern_discovery_UNI.py` - Replicable analysis script

**Total Size**: ~90KB across 9 files
**Total Lines**: 1,379 lines of documentation and data

---

## 🏁 Final Recommendation

**DO NOT TRADE UNI/USDT ON 1-MINUTE TIMEFRAME.**

The exhaustive pattern discovery found zero exploitable edges above transaction costs. All 52 sequential patterns and 63 statistical edges have returns too small to overcome 0.10% fees.

### Better Alternatives:
1. **Trade proven coins**: MOODENG (+24%), FARTCOIN (+20%), TRUMP (+8%)
2. **Higher timeframes**: Test UNI on 5m/15m/30m
3. **Different strategy**: Spot market with volume zones (marginal at best)

---

*Analysis by Master Pattern Noticer*
*Generated: December 8, 2025*
*Data: 30 days (43,001 candles) from Nov 7 - Dec 7, 2025*
