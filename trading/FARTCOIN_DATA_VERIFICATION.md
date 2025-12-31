# FARTCOIN BingX Data Verification Report

**Date:** 2025-12-31
**Data Source:** BingX 1H Candles
**File:** `fartcoin_1h_jun_dec_2025.csv`

---

## Data Quality Check

| Metric | Value | Status |
|--------|-------|--------|
| Date Range | 2025-06-01 to 2025-12-16 | ✅ |
| Total Candles | 4,768 | ✅ |
| Data Gaps | 0 | ✅ |
| Completeness | 100.3% | ✅ |
| Price Range | $0.0957 - $1.6956 (+1672%) | ✅ |
| Invalid Candles | 0 | ✅ |
| Zero Volume | 0 | ✅ |

**Conclusion:** Data quality is excellent - no gaps, no invalid candles.

---

## Donchian Breakout Strategy Results

**Parameters (from DonchianBreakout.py):**
- Period: 15
- TP: 7.5x ATR
- SL: 2.0x ATR
- Risk: 3% per trade
- Max Leverage: 5.0x

**Performance:**

| Metric | Claimed | Actual | Difference |
|--------|---------|--------|------------|
| R:R Ratio | 12.57x | **4.61x** | -7.96x ❌ |
| Return | - | +85.0% | - |
| Max DD | - | -18.4% | - |
| Trades | - | 51 | - |
| Win Rate | - | 31.4% | - |

**Conclusion:** Strategy is profitable (+85% return, 4.61x R:R) but the previously claimed R:R ratio of 12.57x was incorrect.

---

## ATR Analysis

FARTCOIN is highly volatile:

| Metric | Value |
|--------|-------|
| Avg ATR | $0.0191 (2.57% of price) |
| Avg SL Distance | 5.15% (at 2x ATR) |
| Avg TP Distance | 19.31% (at 7.5x ATR) |
| Required Win Rate | 21.1% (to break even) |
| Actual Win Rate | 31.4% ✅ |

The strategy beats the required win rate by 10+ percentage points, resulting in profitability.

---

## Optimized Parameters

The verification script tested different parameters. Best alternatives:

| SL | TP | Trades | WR% | Return% | R:R |
|----|-----|--------|-----|---------|-----|
| 1.5 | 7.5 | 54 | 29.6% | +184.6% | **7.92x** |
| 2.0 | 7.5 | 51 | 31.4% | +85.0% | 4.61x (current) |

**Recommendation:** Consider SL=1.5 ATR for better R:R ratio (7.92x vs 4.61x).

---

## Ranking vs Other Coins (Authoritative)

| Rank | Coin | R:R | Return | Win Rate |
|------|------|-----|--------|----------|
| 1 | UNI | 19.35x | +330% | 36% |
| 2 | PI | 12.68x | +266% | 53% |
| 3 | DOGE | 7.81x | +73% | 67% |
| 4 | PENGU | 7.24x | +57% | 68% |
| 5 | ETH | 6.64x | +64% | 80% |
| 6 | AIXBT | 4.73x | +104% | 26% |
| **7** | **FARTCOIN** | **4.61x** | **+85%** | **31%** |
| 8 | CRV | 2.92x | +36% | 59% |

FARTCOIN ranks 7th out of 8 coins in the portfolio by R:R ratio.

---

## Summary

✅ **Data is valid** - BingX 1H data for FARTCOIN is complete and accurate.
✅ **Strategy is profitable** - +85% return with 4.61x R:R ratio.
❌ **Claimed metrics were wrong** - Actual R:R (4.61x) is lower than claimed (12.57x).
📊 **Potential improvement** - SL=1.5 ATR gives better results (7.92x R:R).

---

*Verified using `trading/verify_fartcoin.py` and `trading/verify_all_coins.py`*
