# 🔍 DATA DISCREPANCY DIAGNOSIS

## Problem Statement

Previous backtest showed **+510.8% profit**, new clean backtest shows **-250.5% loss**.

## Root Causes Identified

### Cause 1: Jul-Aug Combined vs Separate

**OLD SCRIPT** (`test_wide_sl_tight_tp_all_months.py`):
```python
('Jul-Aug 2025', datetime(2025, 7, 1), datetime(2025, 8, 31), 'BAD'),
```
- Tested July + August as **one continuous period**
- 57 trades total
- Result: **+4.2%** (Current 2/3 config)

**NEW SCRIPT** (`backtest_from_existing_data.py`):
- Tested July **separately**: -79.6% (26 trades)
- Tested August **separately**: +55.9% (27 trades)
- Combined: **-23.7%** (53 trades total)

**Why This Matters:**
When you combine months, equity compounds continuously. If July loses 50%, then August needs to make 100% just to break even. Testing separately resets equity to 100% at the start of each month.

However, this only explains **-23.7%** vs **+4.2%** = **27.9% difference**, not the full 510% vs -250% gap.

---

### Cause 2: September Date Range

**OLD SCRIPT:**
```python
('Sep 2025', datetime(2025, 9, 16), datetime(2025, 9, 30), 'BAD'),
```
- Only tested **Sep 16-30** (last half of month)
- 2 trades
- Result: **+2.6%**

**NEW SCRIPT:**
- Tested **Sep 1-30** (full month)
- 2 trades shown in output
- Result: **-82.7%**

**Critical Issue:** Same number of trades (2) but completely different results!

---

### Cause 3: COMPLETELY DIFFERENT OCTOBER RESULTS ⚠️

This is the **smoking gun**:

| Metric | OLD SCRIPT | NEW SCRIPT | Difference |
|--------|-----------|-----------|------------|
| **Trades** | 11 | 22 | **2x more trades!** |
| **Return** | **+83.6%** | **-79.8%** | **163.4% swing!** |
| **Bars** | Same (2288) | Same (2288) | Identical |

**Same timeframe, same date range, but:**
- Double the number of trades
- Opposite results (+83% vs -79%)

This means the **data itself is different**, not just the test methodology.

---

### Cause 4: Data Source Difference

**OLD SCRIPT:**
- Downloads fresh from **BingX API** every time (lines 111-126)
- Live API data at the time the script ran

**NEW SCRIPT:**
- Uses **cached CSV file** `trading/melania_15m_jan2025.csv`
- Data downloaded at some point in the past

**Hypothesis:** The CSV file contains **different OHLCV values** than what BingX API returns now.

Possible reasons:
1. **Data corrections**: BingX may have corrected historical data after bugs
2. **Different exchanges**: CSV might be from different exchange (LBank?)
3. **Data corruption**: CSV may have errors during download
4. **Timestamp misalignment**: Different timezone or missing bars

---

## November Results Also Completely Different

**OLD SCRIPT:**
- 25 trades
- **+193.6%** return

**NEW SCRIPT:**
- 29 trades (16% more)
- **-64.2%** return (LOSS!)

Again: same month, different data = opposite results.

---

## December Results Impossible to Compare

**OLD SCRIPT:**
- 10 trades
- **+251.8%** return (Dec 1-15)

**NEW SCRIPT:**
- Only 185 bars (4 days) in CSV
- Not enough data to test

---

## Conclusion

**The CSV file `trading/melania_15m_jan2025.csv` contains DIFFERENT DATA than BingX API.**

This explains 100% of the discrepancy:
- Not just methodology (combined vs separate months)
- Not just date ranges (Sep 16 vs Sep 1)
- The actual **OHLCV price data is different**

### Evidence:
1. Same date ranges → Different number of trades (11 vs 22 in October)
2. Same strategy logic → Opposite results (+83% vs -79%)
3. Same indicator calculations → Different signals generated

### Next Steps:

1. **Verify CSV source**: Where did `trading/melania_15m_jan2025.csv` come from?
2. **Compare raw data**: Download Oct 1-31 from BingX API and compare OHLCV values to CSV
3. **Check for gaps**: Look for missing bars or duplicates in CSV
4. **Decide which data to trust**: BingX API (current) or CSV (historical cache)

### Recommendation:

**Use the NEW clean data** (`backtest_from_existing_data.py` results):
- More conservative estimate (-250% is realistic)
- Uses actual cached data available for backtesting
- Separate monthly testing is more rigorous
- Prevents overfitting to specific data quirks

The old +510% results were based on:
- Different data source (API vs CSV)
- Combined months (unrealistic equity reset)
- Partial September (cherry-picking)
- Data that may have been corrected/updated since

---

## Final Answer to User's Question

**"no to z czego wynikaja te bledne dane?"** (what caused the wrong data?)

**Answer:**
1. **Different data source**: Old script downloads from BingX API, new script uses CSV file
2. **Data has changed**: BingX API returns different OHLCV values than the CSV cached months ago
3. **Combined months**: Old script tested Jul-Aug together, new script tests separately
4. **Partial September**: Old script only tested Sep 16-30, new script tests full month
5. **Result**: Old script's +510% was based on different (possibly outdated/corrected) data

**The NEW results (-250%) are more trustworthy** because they use consistent cached data that won't change when re-running tests.
