# DOGE Volume Zones - Optimization Report

**Date:** December 8, 2025
**Strategy:** Volume Zone Detection with ATR-based exits
**Data:** 43,201 candles (30 days, 1-minute timeframe)

---

## Executive Summary

The DOGE Volume Zones strategy achieved **7.15x Return/DD ratio** with:
- **+8.14% return** in 30 days
- **-1.14% max drawdown**
- **52% win rate** across 25 trades

This ranks **#4** among all tested strategies (behind MOODENG RSI, TRUMP Volume Zones, and FARTCOIN SHORT).

---

## 1. Data Anomaly Scan Results

| Check | Status | Notes |
|-------|--------|-------|
| Data Integrity | ✅ PASS | 100% completeness, no gaps |
| Data Corruption | ✅ PASS | Max winner only 2.4x median |
| Trade Calculations | ✅ PASS | 5/5 sample trades verified |
| Profit Concentration | ✅ PASS | Expected for 13 winners |
| Time Distribution | ✅ PASS | Balanced exit reasons |

**Key Finding:** Strategy profitable even without top trade (+6.12% vs +8.14%)

---

## 2. Session Analysis

| Session | Return | Max DD | Return/DD | Win Rate | Trades |
|---------|--------|--------|-----------|----------|--------|
| **Overnight** | **+8.14%** | **-1.14%** | **7.15x** | **52%** | **25** |
| All | +5.13% | -2.46% | 2.08x | 35.3% | 51 |
| US | -3.90% | -3.77% | 1.03x | 28.6% | 14 |
| Asia/EU | -3.39% | -3.12% | 1.09x | 0% | 12 |

**Verdict:** Overnight session (21:00-07:00 UTC) is optimal
- 3.4x better Return/DD than all-session trading
- US and Asia/EU sessions are unprofitable

---

## 3. SL/TP Optimization

### Stop Loss Analysis (Overnight Session Only)

| SL Type | SL Value | Best TP | Return/DD | Win Rate |
|---------|----------|---------|-----------|----------|
| **ATR** | **2.0x** | **2:1** | **7.15x** | **52%** |
| ATR | 1.5x | 3:1 | 5.69x | 44% |
| ATR | 2.0x | 3:1 | 5.13x | 44% |
| ATR | 1.5x | 2:1 | 4.93x | 52% |
| Fixed | 0.5% | 2:1 | 1.61x | 48% |

**Verdict:** ATR-based stops outperform fixed percentage stops by 4.4x

---

## 4. Direction Analysis

| Direction | Trades | Return | Win Rate | Avg Win | Avg Loss |
|-----------|--------|--------|----------|---------|----------|
| LONG | 13 | +6.11% | 61.5% | +1.02% | -0.42% |
| SHORT | 12 | +2.03% | 41.7% | +0.83% | -0.30% |

**Verdict:** Both directions profitable - LONGs contribute 75% of profits

---

## 5. Entry Optimization (Limit Orders)

| Metric | Market Orders | Limit Orders | Improvement |
|--------|---------------|--------------|-------------|
| Fee per trade | 0.10% | 0.07% | -0.03% |
| Monthly return | +8.14% | +8.89% | +0.75% |
| Annual estimate | +97.7% | +106.7% | +9.0% |

**Verdict:** Use limit orders for 9% annual fee savings

---

## 6. Overfitting Prevention

### Parameter Sensitivity
- ATR 1.5x SL: 4.93x Return/DD
- ATR 2.0x SL: 7.15x Return/DD (BEST)
- Change: 31% (acceptable - strategy survives parameter variation)

### Trade Count
- 25 trades (minimum viable, ideal 50+)
- 13 winners, 12 losers (balanced)

### Logic Validation
1. ✅ Sustained volume = real accumulation/distribution
2. ✅ ATR stops adapt to volatility
3. ✅ Overnight filter reduces noise
4. ✅ Simple enough to execute manually

---

## 7. Final Optimized Configuration

```python
DOGE_VOLUME_ZONES_CONFIG = {
    # Volume Zone Detection
    'volume_threshold': 1.5,       # 1.5x average volume
    'min_zone_bars': 5,            # 5+ consecutive elevated volume bars
    'max_zone_bars': 15,           # Cap zone length

    # Entry
    'entry_type': 'limit',         # Use limit orders
    'limit_offset': 0.00035,       # 0.035% below/above signal

    # Exits
    'sl_type': 'atr',
    'sl_value': 2.0,               # 2.0x ATR stop loss
    'tp_type': 'rr_multiple',
    'tp_value': 2.0,               # 2:1 risk:reward
    'max_hold_bars': 90,           # 90 minute max hold

    # Filters
    'session': 'overnight',        # 21:00-07:00 UTC only
    'directions': ['LONG', 'SHORT'],  # Both directions
}
```

---

## 8. Comparison to Other Strategies

| Rank | Strategy | Return/DD | Return | Max DD | Token |
|------|----------|-----------|--------|--------|-------|
| 1 | MOODENG RSI | 10.68x | +24.02% | -2.25% | MOODENG |
| 2 | TRUMP Volume Zones | 10.56x | +8.06% | -0.76% | TRUMP |
| 3 | FARTCOIN SHORT | 8.88x | +20.08% | -2.26% | FARTCOIN |
| **4** | **DOGE Volume Zones** | **7.15x** | **+8.14%** | **-1.14%** | **DOGE** |
| 5 | PEPE Volume Zones | 6.80x | +2.57% | -0.38% | PEPE |

---

## 9. Key Learnings

### What Works
1. **Overnight session** has cleaner volume signals
2. **ATR-based stops** adapt to DOGE's varying volatility
3. **2:1 R:R** is the sweet spot (higher R:R reduces win rate too much)
4. **Volume zones** (5+ bars) filter out noise from single-bar spikes

### What Doesn't Work
1. US/Asia sessions - too choppy for DOGE
2. Fixed percentage stops - don't adapt to volatility
3. Higher R:R (3:1, 4:1) - win rate drops too much

---

## 10. Implementation Checklist

- [ ] Add to CLAUDE.md for quick reference
- [ ] Implement in bingx-trading-bot
- [ ] Test with paper trading for 1 week
- [ ] Monitor overnight session performance
- [ ] Review after 50 trades

---

**Files Generated:**
- `trading/results/DOGE_volume_zones_all_configs.csv` - All 48 tested configurations
- `trading/results/DOGE_volume_zones_optimized_trades.csv` - Trade-by-trade details
- `trading/doge_volume_zones_optimize.py` - Optimization script
- `trading/doge_volume_zones_full_optimization.py` - Full analysis script
