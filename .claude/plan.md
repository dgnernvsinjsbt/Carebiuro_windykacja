# FARTCOIN Regime Analysis & Adaptive Filtering

## Objective
Test the EMA 5/20 short strategy on FARTCOIN's full 3-month dataset to identify when it works vs fails, then develop regime detection filters that stop trading during unfavorable conditions (uptrends) while preserving performance in current profitable conditions.

## Context
- Current strategy: EMA 5/20 cross down shorting with optimized SL/TP
- FARTCOIN showed +94% return on 3-month data in optimization
- Data shows price dropped from ~$0.77 (Sept) to ~$0.32 (Dec) = major downtrend
- User wants to understand: Would blind trading during uptrend periods have been unprofitable?
- Goal: Create filters to detect unfavorable regimes WITHOUT overf itting to past data

## Research Phase

### 1. Analyze Full 3-Month FARTCOIN Performance
**Files to examine:**
- `/workspaces/Carebiuro_windykacja/fartcoin_15m_3months.csv`

**Analysis needed:**
- Run baseline strategy (no filters) on full 3 months
- Track equity curve over time with timestamps
- Identify drawdown periods (when equity declined)
- Calculate rolling win rate (e.g., per week or per 20 trades)
- Identify price trend periods (uptrend vs downtrend vs sideways)

**Output:** Time-series analysis showing when strategy made/lost money

### 2. Regime Classification
**Define market regimes using multiple indicators:**
- **Price trend:** EMA 50 vs EMA 200 (or price vs EMA 100)
- **Trend strength:** ADX or ATR as % of price
- **Recent performance:** Price change over last 7 days, 14 days, 30 days
- **Volatility:** Rolling standard deviation
- **EMA slope:** Is EMA 50 rising or falling?

**Classify each bar into regime:**
- Strong uptrend (bad for shorts)
- Weak uptrend (marginal for shorts)
- Sideways/choppy (mixed)
- Weak downtrend (good for shorts)
- Strong downtrend (best for shorts)

**Output:** Each bar labeled with regime + strategy performance in that regime

### 3. Identify Unfavorable Periods
**Correlation analysis:**
- Which regimes had negative returns?
- Which regimes had win rate < 35%?
- Which regimes had high drawdowns?

**Time-based analysis:**
- Were there specific date ranges where strategy failed?
- What were the market characteristics during those periods?

**Output:** Clear definition of "unfavorable conditions"

## Implementation Phase

### 4. Design Regime Detection Filter
**Approach:** Create leading indicators that detect regime BEFORE losses pile up

**Candidate filters:**
1. **Price vs long-term EMA:** Don't short if close > EMA(100) by more than X%
2. **EMA slope filter:** Don't short if EMA(50) has positive slope over last N bars
3. **Recent strength filter:** Don't short if price up >Y% in last 7-14 days
4. **Volatility filter:** Don't short in extremely low volatility (consolidation before breakout)
5. **ADX filter:** Don't short if ADX < threshold (no clear trend)
6. **Multi-timeframe:** Check 1H or 4H trend alongside 15m

**Combination strategy:**
- Use multiple filters together (e.g., price > EMA100 AND positive EMA slope)
- Require 2-3 confirming signals before stopping trading

### 5. Backtest Filter on Historical Data
**Test methodology:**
- Apply filter to full 3-month period
- Measure:
  - How many trades filtered out?
  - Return improvement (avoid losses during bad regimes?)
  - Did filter work in profitable periods? (Sept-early Oct)
  - Did filter catch unprofitable periods?

**Success criteria:**
- Filter improves total return by 10%+ OR reduces max drawdown by 20%+
- Filter does NOT eliminate >30% of profitable trades
- Filter DOES eliminate >50% of unprofitable period trades
- **Critical:** Filter allows trading in "current conditions" (last 2-4 weeks)

### 6. Validate on Current Conditions
**Current period definition:** Last 2-4 weeks of data (when strategy was profitable)

**Validation:**
- Run strategy WITH and WITHOUT filter on current period
- Ensure filter doesn't reduce return by >10% in current conditions
- Confirm filter would allow most/all recent profitable trades

## Deliverables

### Code Files
1. **`trading/fartcoin_regime_analysis.py`**
   - Load full 3-month FARTCOIN data
   - Run baseline strategy
   - Track equity curve with timestamps
   - Classify each period into regimes
   - Output time-series analysis

2. **`trading/regime_filter.py`**
   - Implement regime detection filters
   - Multiple filter options to test
   - Combination logic

3. **`trading/fartcoin_filtered_backtest.py`**
   - Run strategy WITH regime filters
   - Compare filtered vs unfiltered performance
   - Show when filter activated/deactivated
   - Validate on current profitable period

### Analysis Files
4. **`trading/results/fartcoin_regime_analysis.md`**
   - Time-series breakdown of performance
   - Regime classification results
   - Identification of unfavorable periods
   - Filter design rationale

5. **`trading/results/fartcoin_filtered_results.csv`**
   - Trade-by-trade results with filter status
   - Regime labels
   - Comparison metrics

6. **`trading/results/fartcoin_equity_comparison.png`** (optional)
   - Visual comparison of filtered vs unfiltered equity curves

## Key Questions to Answer

1. **Historical performance:** Did strategy lose money during specific uptrend periods?
2. **Regime characteristics:** What defines an "unfavorable" regime for shorts?
3. **Filter effectiveness:** Can we detect unfavorable regimes in advance?
4. **Current validation:** Do filters preserve current profitable conditions?
5. **Trade-off:** How many good trades do we sacrifice to avoid bad regimes?

## Success Metrics

- [ ] Regime filter improves risk-adjusted return (Sharpe ratio)
- [ ] Regime filter reduces maximum drawdown by >15%
- [ ] Filter preserves >80% of return in current profitable period
- [ ] Filter activates during identifiable uptrend periods
- [ ] Filter logic is simple and not overfit (uses 2-3 indicators max)

## Notes

- **Avoid overfitting:** Use simple, well-known indicators (EMAs, price trends)
- **Forward-looking:** Filters should use ONLY data available at time of decision
- **Practical:** Filter logic must be implementable in live trading
- **Conservative:** Better to trade less frequently than to trade in bad conditions
- **Current priority:** Ensure recent profitable period passes the filter

## Next Steps After Plan Approval

1. Implement `fartcoin_regime_analysis.py` first
2. Review regime analysis results with user
3. Design filter based on findings
4. Implement filtered backtest
5. Validate on current conditions
6. Iterate if needed