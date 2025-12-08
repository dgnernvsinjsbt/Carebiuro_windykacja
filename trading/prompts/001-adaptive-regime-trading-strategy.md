<objective>
Develop a highly profitable adaptive trading strategy for FARTCOIN 5-minute data that intelligently detects market regime changes and only trades during favorable conditions.

The goal is to create a strategy that maximizes returns while maintaining smooth equity curves by aggressively filtering out unfavorable market conditions. The strategy should automatically turn ON when conditions are favorable and turn OFF when the market regime changes to unfavorable patterns.
</objective>

<context>
You have 11 months of FARTCOIN 5-minute data (Jan 1 - Dec 4, 2025) in `fartcoin_5m_max.csv`.

Previous findings:
- Simple Bollinger Bounce SHORT strategy failed on the full dataset (-0.4% return, 21% DD) despite working on a 6-day sample
- This demonstrates the critical need for adaptive filters that detect when a strategy should trade vs sit out
- The market goes through different regimes (trending, mean-reverting, high/low volatility) and strategies perform differently in each

You have complete creative freedom to develop any strategy approach. The key insight is: **strategies don't fail - they just trade in the wrong conditions. Your job is to detect those conditions.**
</context>

<requirements>
1. **Profitability**: Achieve the highest possible return over the 11-month period
2. **Risk Management**: Maximum drawdown must stay below 30%
3. **Smooth Equity Curve**: Avoid extended losing streaks by detecting regime changes early
4. **Adaptive Execution**:
   - Implement market regime detection that identifies when conditions are favorable
   - Strategy should trade actively in good regimes
   - Strategy should sit in cash (or trade very selectively) in bad regimes
5. **Aggressive Filtering**: Use multiple filters - don't be conservative. It's better to miss trades than take bad ones.
</requirements>

<implementation_approach>
Your implementation should include:

### 1. Market Regime Detection
Develop indicators that detect market state. Consider:
- **Volatility regimes**: High vs low volatility (use ATR, Bollinger Band width, rolling std)
- **Trend strength**: Strong trend vs choppy sideways (use ADX, EMA slopes, directional movement)
- **Volume patterns**: Normal vs abnormal volume, volume trends
- **Price action**: Higher highs/lows vs consolidation
- **Momentum quality**: Clean momentum vs erratic price movement

Create a regime classification system (e.g., "trending_high_vol", "sideways_low_vol", "reverting", etc.)

### 2. Strategy Selection Based on Regime
Different strategies work in different conditions:
- **Mean reversion** (Bollinger bounce, RSI extremes): Best in ranging/sideways markets with clear boundaries
- **Trend following** (EMA crossovers, breakouts): Best in trending markets with momentum
- **Momentum scalping** (volume spikes, quick moves): Best in high volatility with clear direction
- **Hybrid approaches**: Combine multiple signals with confidence scoring

For each regime, determine:
- Which strategy type performs best
- What are the optimal parameters (SL, TP, hold time)
- What additional filters are needed

### 3. Aggressive Multi-Layer Filtering
Before any trade, check ALL of the following (examples - add more):
- Is the current market regime favorable for this strategy?
- Is volatility in acceptable range (not too low = small moves, not too extreme = false signals)?
- Is volume sufficient (avoid trading in thin/illiquid conditions)?
- Is price action clean (no erratic whipsaws)?
- Have recent similar trades been profitable (meta-filter on recent performance)?
- Are we in a favorable time of day (some hours may perform better)?

A trade should only execute if ALL filters pass. This aggressively reduces trade frequency but increases quality.

### 4. Systematic Testing Approach
1. Test multiple base strategies (5-10 different approaches)
2. For each strategy, identify which market conditions it excels in
3. Build regime detection that accurately identifies those conditions
4. Combine strategies with their optimal regimes
5. Add meta-filters (recent performance, market quality checks)
6. Validate on full 11-month period

### 5. Performance Optimization
Continuously refine by:
- Analyzing periods where strategy lost money - what regime indicators failed?
- Identifying missed opportunities - what filters were too strict?
- Testing parameter sensitivity - are results robust or overfit?
- Checking equity curve smoothness - are there extended drawdown periods that could be avoided?
</implementation_approach>

<technical_specifications>
**Data**: Use `fartcoin_5m_max.csv` (11 months, Jan-Dec 2025)

**Indicators to Consider** (not exhaustive - add your own):
- EMAs: 5, 10, 20, 50, 100, 200
- RSI: 14-period
- Bollinger Bands: 20-period, 2 std dev
- ATR: 14-period for volatility
- ADX: For trend strength
- Volume: Rolling averages, spikes, trends
- Price patterns: Higher highs/lows, support/resistance breaks
- Custom regime indicators you design

**Output Requirements**:
- Save strategy code to: `./adaptive_5m_strategy.py`
- Save results to: `./results/adaptive_5m_results.csv`
- Save equity curve plot to: `./results/adaptive_5m_equity.png`
- Save detailed analysis to: `./results/adaptive_5m_analysis.md`

**Analysis Document Must Include**:
- Strategy description and logic
- Regime detection methodology
- Filter criteria and thresholds
- Performance metrics (return, DD, Sharpe, win rate, etc.)
- Trade distribution across different regimes (show strategy turned on/off appropriately)
- Comparison of performance in different market conditions
- Equity curve analysis with regime annotations
- Failed periods analysis (when/why did it lose money?)
</technical_specifications>

<creative_freedom>
You have COMPLETE freedom to:
- Design any regime detection approach
- Test any strategy types (mean reversion, trend following, hybrid, etc.)
- Use any combination of indicators
- Create custom indicators
- Implement ensemble approaches (multiple strategies voting)
- Add machine learning-style features (if simple enough)
- Experiment with position sizing (fixed, Kelly criterion, confidence-based)
- Try different timeframe analysis (use longer timeframes to detect regime)

The only constraints are:
- Max DD < 30%
- Must be implementable in Python with standard libraries (pandas, numpy, matplotlib)
- Must be explainable (no black-box models)
- Must backtest on the full 11-month dataset
</creative_freedom>

<thinking_guidance>
This is a complex optimization problem. Before coding:

1. **Deeply analyze the data**: What patterns exist? When does price trend vs revert? What characterizes different market states?

2. **Think about WHY strategies fail**: The Bollinger strategy failed because it traded in trending conditions when mean reversion doesn't work. How do you detect trending vs mean-reverting markets?

3. **Consider multiple approaches**: Don't settle on the first idea. Test 5-10 different strategy concepts and see which regimes they excel in.

4. **Build incrementally**: Start with regime detection, validate it visually, then add strategies, then add filters, then optimize.

5. **Question your filters**: Are they actually predictive or just curve-fitting? Test on different time periods within the dataset.

Take your time to develop something truly robust. Aim for breakthrough insights, not incremental improvements.
</thinking_guidance>

<success_criteria>
**Minimum Success**:
- Total return > 50% over 11 months
- Max drawdown < 30%
- Strategy clearly demonstrates regime awareness (trades more in favorable conditions)

**Excellent Success**:
- Total return > 100%
- Max drawdown < 20%
- Smooth equity curve with no extended losing periods
- Clear regime detection with visual proof of strategy turning on/off appropriately
- Multiple strategies combined intelligently

**Breakthrough Success**:
- Total return > 200%
- Max drawdown < 15%
- Multiple winning regime-specific strategies
- Sophisticated filter system that avoids bad trades
- Detailed analysis showing deep market understanding
</success_criteria>

<verification>
Before declaring complete, verify:
1. Strategy has been tested on the FULL 11-month dataset (no sample bias)
2. Equity curve is smooth with controlled drawdowns
3. Trade distribution shows strategy is adaptive (more trades in good regimes, fewer in bad)
4. Results are reproducible (run backtest 3 times, confirm same results)
5. Analysis document thoroughly explains the approach and results
6. All output files are generated and saved to correct locations
</verification>

<output>
Generate these files:
- `./adaptive_5m_strategy.py` - Complete strategy implementation
- `./results/adaptive_5m_results.csv` - Trade-by-trade results
- `./results/adaptive_5m_equity.png` - Equity curve with regime annotations
- `./results/adaptive_5m_analysis.md` - Detailed analysis document
</output>
