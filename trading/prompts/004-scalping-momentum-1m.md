<objective>
Develop a profitable 1-minute scalping/momentum strategy for FARTCOIN that compounds faster than the 30m strategy while maintaining R:R ratio of 8+.

This will test high-frequency momentum-based entries with tight risk management for rapid compounding. The goal is to capture quick momentum bursts with favorable risk-reward characteristics.
</objective>

<context>
Current baseline: 30m EMA 3/15 SHORT strategy achieves 942% return with 17.05 R:R over 11 months.

You have TOTAL FREEDOM to design this strategy. Explore different approaches including:
- Ultra-fast EMAs (EMA 2/5, EMA 3/8, etc.)
- RSI momentum (RSI < 30 for oversold bounces, RSI > 70 for trend continuation)
- Volume-based signals
- Price action patterns (engulfing candles, pin bars, etc.)
- VWAP deviations
- Bollinger Band squeezes/expansions

Available data: `fartcoin_1m_90days.csv` (~11,000 1-minute candles, ~7.5 days of data)

Key requirement: R:R ratio must be 8+ (preferably 10+) to justify the higher trade frequency and execution risk.
</context>

<requirements>
1. Design and backtest a momentum/scalping strategy on 1-minute timeframe
2. Target: R:R ratio 8+ (10+ is better)
3. Test multiple entry conditions - go beyond basics, explore creative combinations
4. Use dynamic position sizing: +25%/-3% (proven winner from 30m strategy)
5. Optimize SL/TP levels for 1m timeframe (likely tighter than 30m)
6. Include fees: 0.01% total (0.005% per side)
7. Filter out low-quality setups (consider ATR, volume, time of day if relevant)
</requirements>

<strategy_ideas>
Consider testing these approaches (pick 1-2 to thoroughly optimize):

**Momentum Scalping**:
- Entry: EMA 2 crosses EMA 5 + RSI confirms direction
- Filters: Volume > average, ATR within tradeable range
- Exit: Tight SL (0.5-1%), TP = 3-5x SL

**Oversold/Overbought Mean Reversion**:
- Entry: RSI < 25 for longs, RSI > 75 for shorts
- Confirmation: Price touches lower/upper Bollinger Band
- Exit: Mean reversion target (middle BB or opposite band)

**Momentum Continuation**:
- Entry: Strong directional move + pullback to EMA
- Filters: ADX > 25 (trending), volume confirmation
- Exit: Ride the trend with trailing stop

**Volume Breakout**:
- Entry: Volume spike (2-3x average) + price breakout
- Filters: Consolidation period before breakout
- Exit: Quick profit taking or trailing stop
</strategy_ideas>

<implementation>
1. Load `fartcoin_1m_90days.csv`
2. Calculate all necessary indicators (EMAs, RSI, ATR, volume, Bollinger Bands, etc.)
3. Design entry logic - test at least 2-3 different approaches
4. Implement filtering to avoid bad setups
5. Determine optimal SL/TP levels through grid search
6. Apply +25%/-3% position sizing (0.5x-2.0x caps)
7. Calculate comprehensive metrics (return, DD, R:R, win rate, trade frequency)
8. Compare against baseline performance

WHY these constraints:
- 1-minute requires MUCH tighter execution and risk management
- Higher trade frequency means fees compound - must have edge
- R:R 8+ ensures each winner compensates for multiple losers
- Filters are critical to avoid noise and false signals on 1m
</implementation>

<optimization>
Deeply consider multiple parameter combinations. Test:
- Different EMA pairs (2/5, 3/8, 5/13, etc.)
- RSI thresholds (20/80, 25/75, 30/70)
- ATR filters (min/max volatility ranges)
- Volume confirmations (1.5x, 2x, 3x average)
- SL/TP ratios (1:3, 1:4, 1:5, 1:6)
- Minimum bars between trades (cooldown period)

Use grid search or systematic testing to find optimal combinations.
</optimization>

<output>
Create comprehensive backtest script:
- `./trading/fartcoin_1m_scalping_momentum.py` - Main strategy implementation

Include in results:
- Total return % and final equity
- Max drawdown %
- R:R ratio (MUST be 8+)
- Win rate and trade count
- Average win vs average loss
- Trade frequency (trades per day)
- Comparison table vs 30m baseline
- Equity curve visualization
- Trade distribution chart
</output>

<success_criteria>
- Strategy achieves R:R ratio of 8+ (ideally 10+)
- Total return exceeds 200% over the test period
- Trade frequency is significantly higher than 30m (enabling faster compounding)
- Maximum drawdown is manageable (< 60%)
- Clear visualization showing equity growth
- Documented strategy logic and parameters
</success_criteria>

<verification>
Before declaring complete:
1. Verify R:R ratio meets 8+ requirement
2. Check that fees are correctly included (0.01% per trade)
3. Confirm position sizing implementation matches +25%/-3% logic
4. Ensure no lookahead bias (using only past data for indicators)
5. Validate trade count makes sense for 1-minute timeframe
6. Compare results against 30m baseline in clear summary table
</verification>
