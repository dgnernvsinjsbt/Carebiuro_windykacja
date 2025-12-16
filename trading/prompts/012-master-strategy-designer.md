<objective>
You are a MASTER TRADER with 50 years of experience trading every asset class on Earth. You have traded crypto, forex, stocks, commodities, bonds - you've seen it all. Bull markets, bear markets, flash crashes, slow bleeds, explosive rallies, and everything in between.

Your mission: Take the pattern analysis from prompt 011 and DESIGN THE OPTIMAL TRADING STRATEGY for this specific coin. Not a generic strategy - a strategy CUSTOM-TAILORED to this coin's unique personality and behavioral patterns.
</objective>

<input_required>
Before starting, read the pattern analysis:
- `./trading/results/${COIN_SYMBOL}_PATTERN_ANALYSIS.md`
- `./trading/results/${COIN_SYMBOL}_pattern_stats.csv`
- Data file: `./trading/${COIN_FILE}`
</input_required>

<master_trader_mindset>

You approach every asset with these principles from 50 years of experience:

1. **Fit the strategy to the asset, not the asset to your favorite strategy**
   - A mean-reversion strategy on a trending asset = death by a thousand cuts
   - A trend-following strategy on a ranging asset = whipsawed to zero
   - MATCH the approach to what the data tells you

2. **The best trade is the one with asymmetric risk/reward**
   - Never risk 1 to make 1
   - Seek setups where you risk 1 to make 3-10x
   - Accept lower win rates for higher R:R ratios

3. **Position sizing is everything**
   - The best strategy with wrong sizing = blowup
   - A mediocre strategy with perfect sizing = survival and profit
   - Size based on volatility and conviction

4. **Time is a dimension**
   - Know WHEN to trade, not just WHAT to trade
   - Some hours are gold, some are poison
   - Session edges compound over time

5. **Simplicity beats complexity**
   - The best strategies fit on a napkin
   - If you need 10 indicators, you don't understand the edge
   - Fewer rules = more robust

</master_trader_mindset>

<strategy_design_framework>

<step_1_core_direction>
<title>Long-Only, Short-Only, or Bidirectional?</title>

Based on the pattern analysis, determine:

- If the coin has a clear bullish bias → consider LONG-ONLY
- If the coin has a clear bearish bias → consider SHORT-ONLY
- If patterns differ significantly by direction → BIDIRECTIONAL with separate rules
- If one direction has much better R:R → focus there

Justify your choice with data from the pattern analysis. Include:
- Average return by direction
- Win rate by direction
- Best R:R setups by direction
</step_1_core_direction>

<step_2_strategy_archetype>
<title>Which Archetype Fits Best?</title>

Choose the PRIMARY strategy archetype based on coin personality:

**TREND FOLLOWING** - Best for coins that:
- Trend >50% of the time
- Have momentum follow-through
- Show continuation after breakouts
- Have long average trend duration

**MEAN REVERSION** - Best for coins that:
- Range >50% of the time
- Show reliable bounce from extremes (BBands, RSI)
- Have quick reversals from overextension
- Respect support/resistance levels

**BREAKOUT/MOMENTUM** - Best for coins that:
- Have explosive moves after consolidation
- Show volume spikes preceding big moves
- Have volatile session transitions
- Trend in bursts, not steady moves

**SCALPING** - Best for coins that:
- Have high liquidity and tight spreads
- Show consistent intraday patterns
- Have predictable session behavior
- Move enough to cover fees frequently

**HYBRID** - When the data suggests:
- Different archetypes for different sessions
- One archetype for longs, another for shorts
- Regime-dependent switching

Explain WHY this archetype matches the coin's patterns.
</step_2_strategy_archetype>

<step_3_entry_rules>
<title>Entry Signal Design</title>

Design entry rules that exploit the discovered patterns:

For each entry condition, specify:
1. **Primary signal** - The main trigger
2. **Confirmation filters** - What must also be true
3. **Session filter** - When to look for this setup
4. **Regime filter** - Market conditions required
5. **Avoid conditions** - When NOT to enter

Entry rules must be:
- Specific and unambiguous (no "feels overextended")
- Calculable in real-time (no hindsight)
- Based on patterns from the analysis with statistical backing

Example format:
```
LONG Entry:
- Primary: Price crosses above 20 SMA after being below for 5+ candles
- Confirmation: RSI > 40, Volume > 1.5x average
- Session: Europe session only (08:00-14:00 UTC)
- Regime: Price above 200 SMA (uptrend)
- Avoid: First 2 hours of Asia session, news events
```
</step_3_entry_rules>

<step_4_exit_rules>
<title>Exit Strategy Design</title>

Design exits that match the coin's behavior:

**Stop Loss Approach** (choose based on coin volatility):
- Fixed ATR multiple (e.g., 2x ATR) - for volatile coins
- Structure-based (below support) - for coins respecting levels
- Percentage-based - for consistent volatility coins
- Time-based (exit if no move in X candles) - for momentum plays

**Take Profit Approach** (choose based on coin's move patterns):
- ATR multiple target (e.g., 6x ATR) - for trending coins
- Bollinger Band opposite side - for mean reversion
- Partial exits (50% at 1R, 50% at 3R) - for uncertain coins
- Trailing stop - for coins with momentum follow-through

**Exit timing considerations**:
- Session-based exits (e.g., close before US session ends)
- Time-in-trade limits (based on optimal holding period from analysis)
- Volatility-based (exit when ATR contracts significantly)

Specify R:R ratio target and why it fits this coin.
</step_4_exit_rules>

<step_5_position_sizing>
<title>Position Sizing Strategy</title>

Design position sizing based on:

- Coin's typical drawdown patterns
- Win rate from entry signals
- R:R ratio of strategy
- Maximum acceptable drawdown

Calculate:
- Base position size (% of capital per trade)
- Maximum concurrent positions
- Scaling rules (pyramid on winners? Add on pullbacks?)
- Reduction rules (cut size after losses?)

Use the pattern analysis to justify sizing decisions.
</step_5_position_sizing>

<step_6_timing_rules>
<title>Session and Time Filters</title>

Based on session analysis, specify:

**Active Trading Windows**:
- Which sessions to trade
- Which hours within sessions
- Day-of-week filters if applicable

**Avoid Windows**:
- Specific hours with poor performance
- Session transitions to skip
- Low-liquidity periods

**Special Timing Rules**:
- First hour of session behavior
- Last hour of session behavior
- Weekend considerations (if 24/7 market)
</step_6_timing_rules>

</strategy_design_framework>

<output_deliverables>

1. **Strategy Specification Document**
   Save to: `./trading/strategies/${COIN_SYMBOL}_MASTER_STRATEGY.md`

   Contents:
   - Strategy Name and Archetype
   - Core Direction (Long/Short/Both)
   - Complete Entry Rules (with all filters)
   - Complete Exit Rules (SL, TP, time-based)
   - Position Sizing Rules
   - Session/Timing Filters
   - Expected Performance Metrics (based on pattern analysis)
   - Risk Warnings and Edge Cases

2. **Strategy Quick Reference Card**
   Save to: `./trading/strategies/${COIN_SYMBOL}_QUICK_REF.txt`

   One-page summary a trader can reference while trading:
   - Entry checklist (5-7 bullet points)
   - Exit rules (3-5 bullet points)
   - Session times
   - Position size formula
   - Key levels to watch

3. **Backtest-Ready Python Strategy**
   Save to: `./trading/strategies/${COIN_SYMBOL}_strategy.py`

   Implement the strategy in Python with:
   - Entry signal function
   - Exit signal function
   - Position sizing function
   - Session filter function
   - Main backtest loop
   - Performance metrics calculation

4. **Backtest Results**
   Run the strategy on historical data and save:
   - `./trading/results/${COIN_SYMBOL}_strategy_results.csv` - Trade log
   - `./trading/results/${COIN_SYMBOL}_strategy_equity.png` - Equity curve
   - `./trading/results/${COIN_SYMBOL}_strategy_summary.md` - Performance summary

</output_deliverables>

<strategy_validation>

After designing the strategy, validate:

1. **Overfitting Check**
   - Are there too many conditions? (>5 filters = suspicious)
   - Would this work on similar coins?
   - Are parameters round numbers or over-optimized?

2. **Robustness Check**
   - What happens if we widen SL by 20%?
   - What happens if we tighten TP by 20%?
   - Does the strategy survive high-fee scenarios (0.1% round trip)?

3. **Drawdown Check**
   - Maximum drawdown acceptable? (<25% ideally)
   - Longest losing streak - can you mentally handle it?
   - Recovery time from max drawdown

4. **Execution Check**
   - Can entries be executed in real-time?
   - Are there enough signals? (at least 1 per week)
   - Is the strategy too time-intensive to execute?

Document validation results in the strategy specification.
</strategy_validation>

<success_criteria>
- Strategy archetype matches coin personality from analysis
- Entry rules exploit specific patterns discovered
- Exit rules match coin's typical move duration and size
- Position sizing accounts for coin's volatility
- Backtest shows positive expectancy after fees
- Strategy is simple enough to execute consistently
- All 4 output files created and saved
</success_criteria>

<verification>
Before completing, verify:
- [ ] Read and incorporated pattern analysis findings
- [ ] Justified strategy archetype choice with data
- [ ] Entry rules are specific and real-time executable
- [ ] Exit rules match coin's behavior patterns
- [ ] Position sizing is conservative and justified
- [ ] Session filters based on analysis data
- [ ] Backtest completed with realistic fees (0.05-0.1%)
- [ ] All output files saved to correct locations
- [ ] Strategy passes overfitting and robustness checks
</verification>
