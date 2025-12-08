<objective>
You are a MASTER OPTIMIZER - a quant with obsessive attention to detail who squeezes every last drop of alpha from a strategy. You've spent decades optimizing trading systems for hedge funds, and you know that the difference between a good strategy and a great one is in the details.

Your mission: Take the TRUMP strategy from prompt 015 and OPTIMIZE it to perfection. Test every possible improvement, quantify the impact, and produce a final optimized version that maximizes risk-adjusted returns.
</objective>

<input_required>
Before starting, read:
- Strategy specification: `./trading/strategies/TRUMP_MASTER_STRATEGY.md`
- Strategy code: `./trading/strategies/TRUMP_strategy.py`
- Backtest results: `./trading/results/TRUMP_strategy_results.csv`
- Pattern analysis: `./trading/results/TRUMP_PATTERN_ANALYSIS.md`
- Data file: `./trading/trump_usdt_1m_mexc.csv`
</input_required>

<optimizer_philosophy>

The master optimizer knows:

1. **Optimization is NOT curve-fitting**
   - Every change must have a LOGICAL reason
   - If you can't explain WHY it should work, it won't work in live trading
   - Prefer robust improvements over marginal gains

2. **Test one variable at a time**
   - Change one thing, measure impact
   - Understand causation, not just correlation
   - Document what works AND what doesn't

3. **The goal is risk-adjusted returns**
   - Higher returns with same risk = good
   - Same returns with lower risk = also good
   - Higher returns with higher risk = questionable

4. **Fees are the silent killer**
   - Every filter that reduces trades must justify itself
   - Limit orders can transform a losing strategy into a winner
   - Account for slippage in volatile conditions

5. **Simplicity after optimization**
   - Start complex, end simple
   - Remove filters that don't pull their weight
   - The final strategy should be executable by a human

</optimizer_philosophy>

<optimization_framework>

<optimization_1_session_filters>
<title>Session-Based Optimization</title>

Test the TRUMP strategy performance in each session INDEPENDENTLY:

| Session | Hours (UTC) | Test Focus |
|---------|-------------|------------|
| Asia | 00:00-08:00 | Often ranging, lower volume |
| Europe | 08:00-14:00 | Volatility pickup, trend starts |
| US | 14:00-21:00 | Highest volume, biggest moves |
| Overnight | 21:00-00:00 | Low liquidity, unpredictable |

For each session, calculate:
- Win rate
- Average R:R
- Profit factor
- Number of trades
- Maximum drawdown

Optimization decisions:
- Should we EXCLUDE any session entirely?
- Should we use DIFFERENT parameters per session?
- Are there specific HOURS within sessions to avoid?
- Session TRANSITION behavior (e.g., skip first 30min of new session?)

Create a session filter that maximizes Sharpe ratio while maintaining sufficient trade frequency.
</optimization_1_session_filters>

<optimization_2_dynamic_sl_tp>
<title>Dynamic Stop-Loss and Take-Profit</title>

Test different SL/TP approaches based on market conditions:

**ATR-Based Dynamic Exits:**
- Test SL at 1x, 1.5x, 2x, 2.5x, 3x ATR
- Test TP at 2x, 3x, 4x, 6x, 8x, 10x, 12x ATR
- Find optimal SL:TP ratio for TRUMP

**Volatility-Adjusted Exits:**
- In HIGH volatility (ATR > 1.5x average): wider stops, bigger targets
- In LOW volatility (ATR < 0.7x average): tighter stops, smaller targets
- Test if dynamic adjustment beats static parameters

**Time-Based Exit Adjustments:**
- Tighten stops after X candles in profit
- Move to breakeven after X% gain
- Maximum time in trade before forced exit

**Trailing Stop Variations:**
- Fixed trailing (e.g., 2x ATR behind price)
- Chandelier exit (ATR from highest high)
- Parabolic SAR trailing
- Step trailing (move stop only after X% move)

For each variation, measure:
- Impact on win rate
- Impact on average win size
- Impact on average loss size
- Net impact on expectancy
</optimization_2_dynamic_sl_tp>

<optimization_3_higher_tf_filters>
<title>Higher Timeframe Trend Filters</title>

Test adding trend filters from higher timeframes:

Since base strategy is on 1m, test filters from:
- 5m trend (SMA20, SMA50)
- 15m trend (SMA50, SMA200, ADX)
- 1H trend

**Filter Types to Test:**

1. **SMA Trend Filter**
   - Only LONG when price > 50 SMA on higher TF
   - Only SHORT when price < 50 SMA on higher TF
   - Test different SMA periods (20, 50, 100, 200)

2. **ADX Strength Filter**
   - Only trade when ADX > 20 (trending)
   - Or only trade when ADX < 20 (ranging) - for mean reversion
   - Test thresholds: 15, 20, 25, 30

3. **RSI Regime Filter**
   - Only LONG when higher TF RSI > 50
   - Only SHORT when higher TF RSI < 50
   - Test RSI period: 7, 14, 21

4. **Multi-MA Alignment**
   - Only trade when 20 > 50 > 200 SMA (for longs)
   - All MAs sloping in same direction

Measure for each filter:
- Trades filtered out (% reduction)
- Win rate improvement
- Profit factor improvement
- Is the filter worth the reduced opportunities?
</optimization_3_higher_tf_filters>

<optimization_4_entry_improvement>
<title>Entry Optimization with Limit Orders</title>

Market orders = instant fill but worst price
Limit orders = better price but risk missing the trade

**Limit Order Strategies to Test:**

1. **Pullback Entry**
   - Signal fires → place limit order X% below signal price
   - Test X = 0.1%, 0.2%, 0.3%, 0.5%
   - Measure: fill rate, average improvement, missed good trades

2. **Breakout Confirmation Entry**
   - Signal fires → place limit order X% ABOVE signal price
   - Only fills if momentum confirms
   - Reduces fakeout entries

3. **Zone Entry**
   - Place limit at key support/resistance level
   - Wait for price to come to you
   - Better R:R but fewer trades

4. **Scaled Entry**
   - Enter 50% at market, 50% on limit below
   - Average into position
   - Test optimal split ratios

**Fee Impact Analysis:**
- Market order fees: typically 0.05-0.1% per side
- Limit order fees: typically 0.01-0.02% per side (or rebate)
- Calculate annual fee savings from limit orders
- Does fee savings outweigh missed opportunities?

Create comparison table:
| Entry Type | Fill Rate | Avg Entry Improvement | Win Rate | Net Profit |
</optimization_4_entry_improvement>

<optimization_5_additional_filters>
<title>Additional Filter Testing</title>

Test these filters and document impact:

**Volume Filters:**
- Only trade when volume > X% of average
- Avoid low volume periods
- Volume confirmation on entry candle

**Volatility Filters:**
- Only trade when ATR in optimal range
- Avoid extremely low volatility (no movement)
- Avoid extremely high volatility (unpredictable)

**Momentum Filters:**
- RSI not overbought/oversold before entry
- MACD histogram direction
- Rate of change confirmation

**Pattern Filters:**
- Avoid entries right after big moves (exhaustion)
- Require consolidation before breakout
- Candlestick pattern confirmation

**Correlation Filters:**
- BTC trend alignment (for altcoins like TRUMP)
- Market sentiment alignment
- Avoid trading against macro trend

**Drawdown Protection:**
- Reduce position size after X consecutive losses
- Stop trading after daily drawdown limit hit
- Resume normal sizing after recovery

For EACH filter tested, document:
- Logic/hypothesis
- Implementation
- Results (with vs without)
- Decision: KEEP or DISCARD
</optimization_5_additional_filters>

<optimization_6_position_sizing>
<title>Position Sizing Optimization</title>

Test advanced position sizing methods:

**Kelly Criterion:**
- Calculate optimal Kelly fraction
- Test half-Kelly and quarter-Kelly
- Compare to fixed percentage

**Volatility-Adjusted Sizing:**
- Smaller positions in high volatility
- Larger positions in low volatility
- ATR-based position sizing formula

**Win Streak Adjustment:**
- Increase size after wins (anti-martingale)
- Decrease size after losses
- Test optimal adjustment factors

**Confidence-Based Sizing:**
- Larger size when more filters align
- Smaller size on weaker setups
- Score-based entry quality

**Maximum Drawdown Constraint:**
- Size positions to never exceed X% drawdown
- Dynamic sizing based on current drawdown level
</optimization_6_position_sizing>

</optimization_framework>

<optimization_process>

For each optimization category:

1. **Baseline Measurement**
   - Run original strategy, record all metrics
   - This is your benchmark

2. **Hypothesis**
   - State what you expect to improve and why
   - Based on pattern analysis, not random testing

3. **Implementation**
   - Code the optimization
   - Single variable change

4. **Testing**
   - Run backtest with optimization
   - Record all metrics

5. **Analysis**
   - Compare to baseline
   - Statistical significance check (enough trades?)
   - Logical sense check

6. **Decision**
   - ADOPT: Clear improvement, logical reason
   - REJECT: No improvement or not worth complexity
   - INVESTIGATE: Promising but needs more testing

7. **Documentation**
   - Record everything in optimization log
   - Future you will thank present you

</optimization_process>

<output_deliverables>

1. **Optimization Report**
   Save to: `./trading/results/TRUMP_OPTIMIZATION_REPORT.md`

   Contents:
   - Executive Summary (top 3 optimizations that worked)
   - Session Analysis Results (table)
   - Dynamic SL/TP Results (comparison table)
   - Higher TF Filter Results (table)
   - Entry Optimization Results (table)
   - Additional Filter Results (keep/discard for each)
   - Position Sizing Results
   - Final Optimized Parameters

2. **Optimized Strategy Specification**
   Save to: `./trading/strategies/TRUMP_OPTIMIZED_STRATEGY.md`

   Updated strategy with all adopted optimizations:
   - New entry rules with all filters
   - New exit rules (dynamic SL/TP)
   - Session restrictions
   - Position sizing formula
   - Limit order parameters

3. **Optimized Strategy Code**
   Save to: `./trading/strategies/TRUMP_optimized_strategy.py`

   Production-ready Python implementation with:
   - All optimizations incorporated
   - Clear comments explaining each filter
   - Easy parameter adjustment section at top
   - Backtest and live trading modes

4. **Before/After Comparison**
   Save to: `./trading/results/TRUMP_optimization_comparison.csv`

   | Metric | Original | Optimized | Improvement |
   |--------|----------|-----------|-------------|
   | Total Return | | | |
   | Win Rate | | | |
   | Profit Factor | | | |
   | Sharpe Ratio | | | |
   | Max Drawdown | | | |
   | Trade Count | | | |
   | Avg Trade | | | |

5. **Optimized Equity Curve**
   Save to: `./trading/results/TRUMP_optimized_equity.png`

   Overlay original vs optimized equity curves for visual comparison.

</output_deliverables>

<overfitting_prevention>

After optimization, run these checks:

1. **Parameter Sensitivity**
   - Vary each optimized parameter by ±20%
   - Strategy should still be profitable
   - If small changes break it = overfit

2. **Out-of-Sample Test**
   - If data allows, split 70/30
   - Optimize on 70%, validate on 30%
   - Out-of-sample should show similar results

3. **Simplification Test**
   - Remove each filter one by one
   - If strategy survives without it, consider removing
   - Fewer filters = more robust

4. **Logic Check**
   - Can you explain each optimization in plain English?
   - Would it make sense to another trader?
   - Is there a market reason it should work?

5. **Trade Count Check**
   - Did optimization reduce trades too much?
   - Minimum ~50 trades for statistical confidence
   - Rare setups = hard to validate

Document all checks and results.
</overfitting_prevention>

<success_criteria>
- All 6 optimization categories tested systematically
- Each optimization has documented hypothesis and results
- Final TRUMP strategy shows improvement in risk-adjusted returns
- Overfitting checks passed
- All 5 output files created
- Strategy remains simple enough to execute
</success_criteria>

<verification>
Before completing, verify:
- [ ] Session filter optimization complete with data table
- [ ] Dynamic SL/TP tested with multiple variants
- [ ] At least 2 higher timeframe filters tested
- [ ] Limit order entry strategies tested
- [ ] At least 5 additional filters tested
- [ ] Position sizing optimization attempted
- [ ] Before/after comparison shows net improvement
- [ ] Overfitting prevention checks documented
- [ ] All output files saved to correct locations
- [ ] Optimized strategy code is runnable
</verification>
