<objective>
Analyze the last 7 days of live trading performance for all strategies in our BingX trading bot and compare them against the original 30-day backtest results that were used to discover and validate these strategies.

This analysis will help determine if strategies are performing within expected parameters or if adjustments are needed.
</objective>

<context>
We have a live trading bot running on BingX with 7 strategies. Each strategy was validated through extensive backtesting before deployment.

**IMPORTANT CLASSIFICATION RULE:**
- TIME exits that are profitable should be counted as WINS, not losses
- Only SL (stop loss) exits are losses
- TP (take profit) exits are wins
- TIME exits with positive P/L are wins, TIME exits with negative P/L are losses

Be fair and balanced in your analysis - don't be a panician. Small deviations from backtest are normal variance.
</context>

<strategies_and_backtest_benchmarks>
The following are the FIXED backtest results we're comparing against. These were the original discovery backtests:

**1. MOODENG RSI Momentum (LONG)**
- Backtest Period: 30 days (Nov 2025)
- Return: +24.02%
- Max Drawdown: -2.25%
- Win Rate: 31%
- Trades: 129
- R:R Ratio: 5.75x
- Data File: trading/moodeng_usdt_1m_lbank.csv
- Trades File: trading/results/moodeng_audit_trades.csv

**2. FARTCOIN Multi-Timeframe LONG**
- Backtest Period: 30 days
- Return: +10.38%
- Max Drawdown: -1.45%
- R:R Ratio: 7.14x
- Note: Rare signals (explosive breakouts only)

**3. FARTCOIN Trend Distance SHORT**
- Backtest Period: 30 days
- Return: +20.08%
- Max Drawdown: -2.26%
- R:R Ratio: 8.88x
- Note: Requires strong downtrend (2%+ below SMA50)

**4. DOGE Volume Zones (LONG + SHORT)**
- Backtest Period: 30 days
- Return: +8.14%
- Max Drawdown: -1.14%
- Win Rate: 52%
- Trades: 25
- R:R Ratio: 7.15x (Return/DD)
- Session: Overnight only (21:00-07:00 UTC)
- Data File: trading/doge_usdt_1m_lbank.csv
- Report: trading/results/DOGE_VOLUME_ZONES_OPTIMIZATION_REPORT.md

**5. PEPE Volume Zones (LONG + SHORT)**
- Backtest Period: 30 days
- Return: +2.57%
- Max Drawdown: -0.38%
- Win Rate: 66.7%
- Trades: 15
- R:R Ratio: 6.80x (Return/DD)
- Session: Overnight only (21:00-07:00 UTC)

**6. TRUMP Volume Zones (LONG + SHORT)**
- Backtest Period: 30 days
- Return: +8.06%
- Max Drawdown: -0.76%
- Win Rate: 61.9%
- Trades: 21
- R:R Ratio: 10.56x (Return/DD)
- Session: Overnight only (21:00-07:00 UTC)
- WARNING: Outlier-dependent (88.6% profit from top 20% trades)

**7. UNI Volume Zones (LONG + SHORT)**
- Backtest Period: 3 months (~90 days)
- Return: +31.99%
- Max Drawdown: -1.78%
- Win Rate: 45.1%
- Trades: 195 (over 3 months, ~65/month)
- R:R Ratio: 17.98x (Return/DD)
- Session: Asia/EU only (00:00-14:00 UTC)
- Trades File: trading/results/UNI_volume_zones_trades.csv
</strategies_and_backtest_benchmarks>

<data_sources>
Live data should be fetched from BingX API for the last 7 days.

Use the existing scripts as reference:
@bingx-trading-bot/check_all_strategies_72h.py
@bingx-trading-bot/config.yaml

Backtest reference files:
@trading/results/UNI_volume_zones_trades.csv
@trading/results/DOGE_VOLUME_ZONES_OPTIMIZATION_REPORT.md
</data_sources>

<analysis_requirements>
For each strategy, calculate and compare:

1. **Trade Count**
   - Live: Number of signals in last 7 days
   - Expected: (Backtest trades / 30) × 7
   - Variance: Is it within reasonable range?

2. **Win Rate**
   - Live win rate (TP + profitable TIME exits) / total trades
   - Backtest win rate
   - Difference and whether it's statistically significant

3. **P/L Performance**
   - Live P/L for 7 days
   - Expected P/L: (Backtest return / 30) × 7
   - Variance analysis

4. **Losing Streaks**
   - Max consecutive losses in live period
   - Max consecutive losses in backtest
   - Is current streak within historical norms?

5. **Exit Type Distribution**
   - % TP vs % SL vs % TIME
   - Compare to backtest distribution
   - Flag if TIME exits are abnormally high (may indicate targets too aggressive)

6. **Overall Health Score**
   - Rate each strategy: HEALTHY / WATCH / CONCERN
   - HEALTHY: Within 20% of expected metrics
   - WATCH: 20-40% deviation
   - CONCERN: >40% deviation or structural issues
</analysis_requirements>

<output_format>
Create a comprehensive markdown report saved to: `./trading/results/7DAY_VS_BACKTEST_ANALYSIS.md`

Structure:
1. Executive Summary (1 paragraph overall assessment)
2. **Portfolio Summary**
   - Total P/L (all strategies combined)
   - Max Drawdown (portfolio level)
   - Total trades taken
3. **Per-Strategy Breakdown** (table + brief commentary for each)
   - P/L
   - Max DD
   - Win rate
   - Trade count
   - Exit distribution (TP/SL/TIME)
   - All relevant metrics
4. **Comparison Table** (all strategies side by side: Live 7d vs Backtest 30d)
5. Recommendations (if any strategies need attention)
6. Conclusion

Use tables for easy comparison. Be data-driven and fair.
</output_format>

<verification>
Before completing:
- Verify all 7 strategies are analyzed
- Confirm TIME exit classification is correct (profitable = win)
- Check that backtest numbers match the benchmarks above exactly
- Ensure recommendations are proportionate to actual deviations
</verification>

<success_criteria>
- Complete analysis for all 7 strategies
- Fair comparison that accounts for normal variance
- Clear actionable recommendations (or confirmation that all is well)
- Report saved to specified location
</success_criteria>
