<objective>
Build a pattern recognition trading strategy for FARTCOIN/USDT 1-minute data that identifies high-probability candlestick patterns and price structures to achieve 8:1+ risk:reward. Focus on detecting early momentum signals and exhaustion patterns using only OHLCV data.

This approach uses price action psychology and market structure to find asymmetric opportunities.
</objective>

<context>
You have OHLCV data (timestamp, open, high, low, close, volume) from FARTCOIN/USDT 1-minute candles.

Pattern recognition edge:
- Candlestick patterns reveal market psychology
- Certain patterns precede large moves consistently
- 1-minute timeframe shows micro-structure patterns
- Volume confirms pattern validity
- Memecoin volatility amplifies pattern effectiveness

Goal: Identify patterns that historically lead to 8R+ moves with high consistency.
</context>

<requirements>
1. Load FARTCOIN/USDT CSV data and analyze price patterns
2. Develop pattern recognition strategy using ONLY OHLCV data:
   - Scan for high-probability candlestick patterns
   - Identify support/resistance levels dynamically
   - Detect chart patterns (flags, triangles, wedges)
   - Confirm patterns with volume analysis
   - Optimize for 8:1 risk:reward setups
3. Implement pattern detectors:
   - **Reversal patterns**: Hammer, shooting star, engulfing, morning/evening star
   - **Continuation patterns**: Flags, pennants, inside bars preceding breakouts
   - **Volume patterns**: Climax volume, diminishing volume in consolidation
   - **Structure patterns**: Higher highs/lower lows, swing points
4. Backtest strategy with full metrics:
   - Win rate per pattern type
   - Average R:R achieved per pattern
   - Pattern frequency
   - False signal rate
   - Overall profitability
5. Include adaptive stop placement based on pattern structure
6. Account for 0.1% trading fees (0.2% round trip)
</requirements>

<implementation>
Strategy architecture:

1. **Pattern Scanner**:
   - Scan last 5-20 candles for recognizable patterns
   - Calculate candle body size, wick ratio, relative position
   - Identify swing highs and lows for structure
   - Measure volume relative to recent average

2. **High-Probability Patterns for 8R Setups**:

   **Bullish:**
   - Hammer at support + volume surge = reversal
   - Bullish engulfing after downtrend = exhaustion
   - Inside bar followed by up breakout = continuation
   - Triple bottom with decreasing volume = accumulation

   **Bearish:**
   - Shooting star at resistance + volume = rejection
   - Bearish engulfing after uptrend = distribution
   - Inside bar followed by down breakout = breakdown
   - Triple top with volume climax = exhaustion

3. **Entry Logic**:
   - Wait for pattern completion
   - Confirm with volume (surge on signal candle)
   - Enter at open of next candle after pattern
   - Only trade if pattern occurs at key structure level

4. **Stop Loss Placement**:
   - Place stop beyond pattern invalidation point
   - For hammer: stop below low of hammer wick
   - For engulfing: stop beyond engulfed candle
   - Tight stops (0.3-0.5% typical) enable 8R targets

5. **Profit Target Strategy**:
   - Measure pattern: Calculate expected move distance
   - Set target at 8x stop distance minimum
   - Use measured move technique (pattern height × 8)
   - Trail stop after 5R to protect gains

6. **Pattern Priority System**:
   - Grade patterns by historical success rate
   - Only trade A+ setups (>25% win rate at 8R)
   - Skip B-grade patterns (lower probability)

WHY this works:
- Patterns repeat because human psychology is consistent
- Volume confirms institutional participation
- Structure levels (support/resistance) create predictable reactions
- Tight stops at invalidation points maximize R:R
- Memecoin traders are emotional = stronger pattern signals
</implementation>

<output>
Create these files in `./strategies/`:

1. `pattern-strategy-analysis.md`
   - Complete pattern catalog with rules
   - Entry/exit criteria per pattern type
   - Risk management framework
   - Backtest results by pattern
   - Best performing patterns identified

2. `pattern-recognition-strategy.py`
   - Python implementation using pandas/numpy
   - CSV data loading function
   - Pattern detection functions (each pattern = separate detector)
   - Support/resistance level identification
   - Volume analysis functions
   - Backtesting engine
   - Performance breakdown by pattern type

3. `pattern-trades.csv`
   - Trade log with columns: timestamp, pattern_type, direction, entry, stop, target, exit, pnl, r_multiple, exit_reason

4. `pattern-performance.csv`
   - Summary by pattern type: win_rate, avg_rr, trade_count, profit_factor

5. `pattern-equity-curve.csv`
   - Cumulative performance over time
</output>

<verification>
Before declaring complete, verify:

1. ✓ CSV data loads and processes correctly
2. ✓ Pattern detectors work accurately (manually check 5-10 patterns)
3. ✓ Strategy generates 25+ trades minimum
4. ✓ At least 2-3 pattern types show consistent profitability
5. ✓ Average R:R on winning trades is 6:1 or higher
6. ✓ Win rate is sufficient (15-20%+ needed at 8R)
7. ✓ Best pattern identified clearly (highest profit factor)
8. ✓ Volume confirmation improves results (compare with/without)
9. ✓ Support/resistance logic is sound (price respects levels)
10. ✓ Code runs end-to-end without errors

Edge case validation:
- Do patterns work in both directions (long and short)?
- What happens during low volume periods?
- Are false patterns filtered effectively?
- Does strategy avoid overtrading (quality over quantity)?
</verification>

<success_criteria>
- Strategy achieves 8:1+ R:R on pattern-based trades
- Positive expected value with realistic win rate (15-25%)
- Clear identification of highest-probability patterns (A+ grade)
- Pattern detection code is accurate and reproducible
- Volume confirmation demonstrably improves performance
- Results show WHICH specific patterns work best on FARTCOIN
- Documentation includes visual examples of patterns
- Code is modular (easy to add/remove patterns)
- Profit factor > 1.5 overall, >2.0 on best patterns
</success_criteria>