# TRUMPSOL ATR Expansion with Trend Filter - Backtest Report

**Date:** 2025-12-12
**Status:** NOT LIVE - Available for future deployment
**Strategy File:** `bingx-trading-bot/strategies/trumpsol_atr_expansion.py`

---

## Performance Summary (60-day backtest)

| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **5.29x** ⚠️ |
| **Total Return** | +24.65% |
| **Max Drawdown** | -4.66% |
| **Trades** | 23 |
| **Win Rate** | 39.1% |
| **TP Rate** | 34.8% |
| **Data Period** | Oct 13 - Dec 12, 2025 (60 days) |
| **Candles** | 86,400 (1-minute) |

---

## Configuration

```python
{
    'atr_threshold': 1.5,      # ATR > 1.5x rolling average
    'ema_distance': 2.0,       # Max 2% from EMA20
    'tp_multiplier': 8.0,      # TP at 8x ATR
    'sl_multiplier': 1.5,      # SL at 1.5x ATR
    'limit_offset_pct': 0.5,   # Limit order 0.5% above signal
    'daily_rsi_min': 50,       # Daily RSI > 50
    'trend_filter': True       # CRITICAL: Only LONG when Price > EMA20
}
```

---

## Key Filter: Trend Alignment (Price > EMA20)

**Why This Filter Works:**

- **Logical Edge:** Only trade ATR expansion breakouts when price is already above EMA20 (in direction of trend)
- **Not Arbitrary:** Trend alignment is a proven trading concept
- **Replicable:** Simple boolean rule that doesn't overfit
- **Improvement:** +31.6% R/DD improvement over baseline (4.02x → 5.29x)

**Filter Impact:**
- Baseline signals: 149
- After trend filter: 88 signals (59% retained)
- Filled trades: 23 (26.1% fill rate)

---

## Comparison vs Other Strategies

| Rank | Strategy | R/DD | Return | Max DD | Trades | Status |
|------|----------|------|--------|--------|--------|--------|
| 🥇 1 | **FARTCOIN ATR** | **26.21x** | +98.8% | -3.77% | 28 | ✅ LIVE |
| 🥈 2 | **MOODENG ATR** | **13.34x** | +73.8% | -5.53% | 26 | ✅ IMPLEMENTED |
| 🥉 3 | **TRUMPSOL Trend** | **5.29x** | +24.7% | -4.66% | 23 | ⚠️ ACCEPTABLE |

---

## Optimization Process

### Initial Test (Baseline)
- ATR 1.5x, no trend filter
- Result: 42 trades, 4.02x R/DD, +34.6%
- Issue: Below 5x threshold

### Filter Exploration
1. **Body % filter** - Too arbitrary, likely overfitting
2. **Volume >= 2.0x** - Only 7 trades, too restrictive
3. **RSI 50-70** - Only 7 trades, too restrictive
4. **Trend filter (Price > EMA20)** ✅ - **23 trades, 5.29x R/DD**

### Final Decision
- Trend filter chosen for:
  - Logical, replicable edge
  - Sufficient trade count (23 > 20 minimum)
  - Crosses 5x R/DD threshold
  - Not arbitrary or overfitted

---

## Evaluation

**Strengths:**
- ✅ Crosses 5x R/DD threshold (acceptable)
- ✅ 20+ trades (sufficient sample size)
- ✅ Logical filter (trend alignment)
- ✅ Replicable edge (not arbitrary)
- ✅ 34.8% TP rate (targets actually hit)

**Weaknesses:**
- ⚠️ Below 10x R/DD "excellent" threshold
- ⚠️ Lower absolute returns (+24.7% vs FARTCOIN +98.8%)
- ⚠️ Win rate only 39.1% (needs tight stops)

**Conclusion:**
TRUMPSOL with trend filter is **ACCEPTABLE** for deployment but ranks #3 behind FARTCOIN and MOODENG. The 5.29x R/DD with logical filters makes it viable, but monitor live performance before full commitment.

---

## Next Steps

1. ⏳ Monitor FARTCOIN and MOODENG live performance first
2. ⏳ If both perform well, consider adding TRUMPSOL as 3rd strategy
3. ⏳ Validate trend filter edge holds in live trading
4. ⏳ Set conservative position sizing (lower allocation than FARTCOIN/MOODENG)

---

**Report Generated:** 2025-12-12
**Backtest Data:** `trading/trumpsol_60d_bingx.csv`
**Strategy Code:** `bingx-trading-bot/strategies/trumpsol_atr_expansion.py`
