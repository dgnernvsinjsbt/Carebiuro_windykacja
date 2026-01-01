<objective>
Develop a profitable 1-minute mean reversion strategy for FARTCOIN that exploits short-term extremes and snap-back moves for rapid compounding with R:R ratio of 8+.

This will test counter-trend entries at statistical extremes with precise timing for quick profits. The goal is to capture mean reversion moves in choppy/ranging markets.
</objective>

<context>
Current baseline: 30m EMA 3/15 SHORT strategy achieves 942% return with 17.05 R:R over 11 months.

You have TOTAL FREEDOM to design this strategy. Focus on mean reversion approaches:
- Bollinger Band extremes (price touches/penetrates bands)
- RSI oversold/overbought (< 20 for longs, > 80 for shorts)
- Z-score price deviations from moving average
- Stochastic oscillator extremes
- Price distance from VWAP
- Exhaustion patterns (wicks, dojis after strong moves)

Available data: `fartcoin_1m_90days.csv` (~11,000 1-minute candles, ~7.5 days of data)

Key insight: 1-minute charts have HIGH noise and frequent overextensions that snap back quickly. Mean reversion can capture these with tight stops and quick profits.
</context>

<requirements>
1. Design and backtest a mean reversion strategy on 1-minute timeframe
2. Target: R:R ratio 8+ (10+ preferred)
3. Test multiple statistical indicators - explore creative combinations beyond RSI
4. Use dynamic position sizing: +25%/-3% (proven winner)
5. Optimize entry/exit thresholds for 1m mean reversion
6. Include fees: 0.01% total (0.005% per side)
7. Filter out false extremes (must have actual reversion potential)
</requirements>

<strategy_ideas>
Consider testing these mean reversion approaches (pick 1-2 to deeply optimize):

**Bollinger Band Extremes**:
- Entry: Price closes outside BB (2 std dev) + RSI extreme
- Confirmation: Volume spike or rejection wick
- Exit: Reversion to middle BB or opposite band
- SL: Beyond recent swing extreme

**RSI Extreme Bounce**:
- Entry LONG: RSI < 15-20 + price shows bullish rejection
- Entry SHORT: RSI > 80-85 + price shows bearish rejection
- Confirmation: Momentum divergence or volume
- Exit: RSI returns to 40-60 range or fixed R:R

**Z-Score Reversion**:
- Calculate z-score: (price - SMA) / StdDev
- Entry LONG: z-score < -2.5 (extremely undervalued)
- Entry SHORT: z-score > +2.5 (extremely overvalued)
- Exit: z-score returns to neutral (-0.5 to +0.5)

**VWAP Deviation**:
- Entry: Price deviates > 2% from VWAP
- Confirmation: Volume profile shows exhaustion
- Exit: Reversion to VWAP or fixed profit target
</strategy_ideas>

<implementation>
1. Load `fartcoin_1m_90days.csv`
2. Calculate indicators: Bollinger Bands, RSI, Stochastic, Z-score, VWAP, ATR
3. Design mean reversion entry logic - test 2-3 different statistical approaches
4. Implement confirmation filters to avoid catching falling knives
5. Determine optimal entry thresholds and exit targets through testing
6. Apply +25%/-3% position sizing (0.5x-2.0x caps)
7. Calculate comprehensive metrics focusing on R:R and consistency
8. Compare against momentum-based approaches

WHY mean reversion on 1m:
- High-frequency noise creates frequent overextensions
- Quick snap-backs provide fast profit opportunities
- Statistical edges are more pronounced on shorter timeframes
- Can complement momentum strategies in different market conditions
</implementation>

<optimization>
Thoroughly explore parameter space. Test:
- Bollinger Band periods (10, 15, 20) and std dev (1.5, 2.0, 2.5)
- RSI periods (7, 9, 14) and extreme thresholds (15, 20, 80, 85)
- Z-score lookback periods (20, 30, 50 bars)
- Entry thresholds vs exit targets (risk-reward optimization)
- Minimum time in position (avoid instant reversals)
- Maximum time in position (cut losses on non-reversion)
- Volume filters (only trade when volume confirms exhaustion)

Use systematic grid search to find best parameter combinations.
</optimization>

<output>
Create comprehensive backtest script:
- `./trading/fartcoin_1m_mean_reversion.py` - Main strategy implementation

Include in results:
- Total return % and final equity
- Max drawdown %
- R:R ratio (MUST be 8+)
- Win rate and trade count
- Average win vs average loss
- Trade frequency and average holding time
- Reversion success rate (% of trades that hit TP vs SL)
- Equity curve visualization
- Distribution of entry conditions (which setups work best)
</output>

<success_criteria>
- Strategy achieves R:R ratio of 8+ (ideally 10+)
- Total return exceeds 200% over test period
- Win rate is reasonable for mean reversion (40-50%+)
- Maximum drawdown is controlled (< 60%)
- Average holding time is SHORT (minutes, not hours)
- Clear visualization showing equity growth
- Documented best-performing reversion setups
</success_criteria>

<verification>
Before declaring complete:
1. Verify R:R ratio meets 8+ requirement
2. Confirm mean reversion logic is sound (not trend-following in disguise)
3. Check that position sizing matches +25%/-3% logic
4. Ensure no lookahead bias in indicator calculations
5. Validate that exits are based on reversion, not arbitrary targets
6. Compare results to momentum strategy (prompt 004) for complementary insights
</verification>
