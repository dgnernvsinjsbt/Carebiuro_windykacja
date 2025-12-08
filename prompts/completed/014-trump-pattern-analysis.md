<objective>
Become the MASTER of TRUMP cryptocurrency. Your mission: exhaustively analyze historical data to discover every exploitable pattern that can form the foundation of a profitable trading strategy.

This is DEEP PATTERN DISCOVERY mode. You are not building a strategy yet - you are creating the analytical foundation that will inform strategy creation.
</objective>

<coin_to_analyze>
TRUMP - Analyze the data file: `./trading/trump_usdt_1m_mexc.csv`

Before starting, read the data file to understand:
- Timeframe (1m, 5m, 15m, 30m, 1h)
- Date range available
- Columns available (OHLCV minimum required)
</coin_to_analyze>

<analysis_framework>

<session_analysis>
<title>Trading Session Patterns</title>

Define sessions (UTC):
- Asia: 00:00-08:00 UTC (Tokyo/Singapore/Hong Kong)
- Europe: 08:00-14:00 UTC (London open through US pre-market)
- US: 14:00-21:00 UTC (NYSE/NASDAQ active hours)
- Overnight: 21:00-00:00 UTC (low liquidity transition)

For EACH session, calculate and compare:
1. Average return (%) - is this session bullish or bearish?
2. Volatility (ATR, std dev of returns)
3. Average volume vs 24h average
4. Win rate of longs vs shorts
5. Best performing hour within session
6. Worst performing hour within session

Key questions to answer:
- Which session has the most predictable direction?
- Which session has the highest volatility (opportunity)?
- Are there session-to-session momentum effects? (e.g., strong Asia → continuation in EU?)
- What happens at session transitions? (handoff patterns)
</session_analysis>

<sequential_patterns>
<title>Event Sequence Analysis (X → Y Patterns)</title>

Discover what happens AFTER specific events:

Price Action Sequences:
- After a candle with >2% body → what happens in next 1, 3, 5 candles?
- After 3+ consecutive green/red candles → reversal or continuation?
- After a wick >2x the body (rejection) → next candle behavior?
- After breaking above/below 20, 50, 200 SMA → follow-through rate?
- After price touches Bollinger Band (2 or 3 std) → mean reversion success rate?

Volume Sequences:
- After volume spike (>3x average) → price continuation or exhaustion?
- After volume dry-up (<0.5x average for 3+ candles) → breakout probability?
- Volume increasing with price vs volume decreasing with price (divergence signals)

Volatility Sequences:
- After ATR contracts to <50% of 20-period average → expansion coming?
- After ATR expands to >200% of average → contraction/consolidation?
- Volatility regime shifts - how long do high/low vol periods last?

Gap/Jump Analysis:
- After a gap up/down of >1% → fill rate and timing?
- After a sudden move (3% in 5 candles) → pullback probability and depth?
</sequential_patterns>

<regime_classification>
<title>Market Regime Identification</title>

Classify the coin's behavior into regimes:

1. TRENDING (Strong directional moves)
   - How often is the coin in trend mode? (% of time)
   - Average trend duration
   - Best indicators for trend detection

2. MEAN-REVERTING (Range-bound, oscillating)
   - How often is the coin ranging? (% of time)
   - Average range duration and width
   - Best levels for mean reversion entries

3. EXPLOSIVE (Sudden breakouts/breakdowns)
   - Frequency of explosive moves (>3% in short time)
   - Warning signs before explosions
   - Best way to participate or avoid

4. CHOPPY (No clear pattern, whipsaws)
   - How often is the coin unplayable?
   - Characteristics to identify and avoid this regime

Key question: Is this coin BETTER for trend-following or mean-reversion strategies overall?
</regime_classification>

<statistical_edges>
<title>Statistical Edge Discovery</title>

Calculate statistical significance for:

Day-of-Week Patterns:
- Which day has best/worst average return?
- Which day has highest volatility?
- Weekend effect (if 24/7 trading data available)

Time-of-Day Patterns:
- Most profitable hour to enter longs
- Most profitable hour to enter shorts
- Hours to avoid (high whipsaw, low opportunity)

Technical Level Patterns:
- Round number effects (psychological levels like $6.00, $7.00, $8.00)
- Previous day high/low as support/resistance
- VWAP deviation patterns

Correlation Patterns:
- RSI extremes → reversal probability
- MACD crossovers → success rate
- Bollinger Band touches → mean reversion success
</statistical_edges>

<behavioral_profile>
<title>Coin Personality Profile</title>

Create a behavioral profile:

Volatility Character:
- Average daily range (% high-low)
- Typical move size before pullback
- How often does it trend vs chop?
- Explosive or gradual mover?

Liquidity Character:
- Volume consistency or sporadic?
- Slippage risk assessment
- Best execution windows

Momentum Character:
- Does momentum follow through or fade?
- Optimal holding periods for wins
- How quickly do losses develop?

Risk Character:
- Typical drawdown depth in losing trades
- How fast can it move against you?
- Black swan frequency (extreme moves)
</behavioral_profile>

</analysis_framework>

<output_requirements>

Create a comprehensive analysis report saved to: `./trading/results/TRUMP_PATTERN_ANALYSIS.md`

Structure:
1. **Executive Summary** - Top 3-5 most significant patterns discovered
2. **Session Analysis Results** - Tables with session statistics
3. **Sequential Pattern Catalog** - List of "When X → Then Y" patterns with probabilities
4. **Regime Analysis** - Pie chart description of time in each regime
5. **Statistical Edges** - Ranked list of statistically significant patterns
6. **Coin Personality Profile** - Narrative description of coin behavior
7. **Strategy Implications** - Which strategy types are most suitable:
   - Trend-following recommended? When?
   - Mean-reversion recommended? When?
   - Breakout/momentum plays? Conditions?
   - Avoid trading when? (unplayable conditions)
8. **Raw Data** - Save key statistics to CSV: `./trading/results/TRUMP_pattern_stats.csv`

</output_requirements>

<methodology>

1. Load and prepare data:
   - Read the CSV file
   - Calculate derived features (returns, ATR, RSI, BBands, SMAs, volume ratios)
   - Add time-based columns (hour, session, day_of_week)

2. Run systematic analysis:
   - For each analysis category, calculate statistics
   - Test for statistical significance where applicable
   - Focus on ACTIONABLE patterns (not just interesting trivia)

3. Prioritize by tradability:
   - Pattern must occur frequently enough to be useful
   - Edge must be large enough to overcome fees (assume 0.1% round-trip)
   - Pattern must be identifiable in real-time (no hindsight bias)

4. Document everything:
   - Include sample sizes for all statistics
   - Note confidence levels
   - Highlight patterns that need more data to confirm

</methodology>

<python_implementation>
Write a Python script that performs this analysis. Save to: `./trading/pattern_discovery_TRUMP.py`

The script should:
- Be well-commented and reusable for other coins
- Output both markdown report and CSV data
- Include visualizations where helpful (save as PNG)
- Print progress as it runs through each analysis section
</python_implementation>

<success_criteria>
- Minimum 10 distinct patterns identified with statistical backing
- At least 3 "high confidence" patterns (p < 0.05 or win rate > 60%)
- Clear recommendation on which strategy type suits this coin
- Actionable insights that could be immediately tested in backtesting
</success_criteria>

<verification>
Before completing, verify:
- [ ] All session statistics calculated and compared
- [ ] Sequential patterns tested with sample sizes > 30
- [ ] Regime classification completed with time percentages
- [ ] Statistical edges ranked by significance
- [ ] Personality profile captures coin's unique characteristics
- [ ] Strategy implications are specific and actionable
- [ ] Output files saved to correct locations
</verification>
