<objective>
Perform comprehensive statistical analysis and validation of trading strategy backtest results to determine if they are realistic, identify anomalies, and assess viability for live trading.

This analysis is critical for risk management - it prevents deploying strategies with inflated/unrealistic results and identifies data errors or overfitting before capital is at risk.
</objective>

<context>
You will receive trading results data (CSV or similar format) containing individual trade outcomes from a backtest. The data typically includes:
- Entry/exit prices and timestamps
- Trade P/L (profit/loss)
- Trade direction (LONG/SHORT)
- Stop loss and take profit levels
- Trade duration

Your goal is to validate whether these results represent realistic trading performance or contain anomalies, errors, or unrealistic patterns that would fail in live markets.
</context>

<analysis_requirements>

## 1. Podstawowe Statystyki

Calculate and report:

- **Win Rate**: Percentage of winning trades vs total trades
- **Total P/L**: Sum of all profits and losses (net return)
- **Average Win**: Mean profit of winning trades
- **Average Loss**: Mean loss of losing trades
- **Median Win**: Median profit of winning trades
- **Median Loss**: Median loss of losing trades
- **Max Win**: Largest single winning trade
- **Max Loss**: Largest single losing trade
- **Profit Factor**: Gross profits ÷ Gross losses (should be > 1.0)
- **Expectancy**: (Win Rate × Avg Win) - (Loss Rate × Avg Loss)

## 2. Wykrycie Anomalii

Thoroughly analyze for:

- **Outliers Detection**:
  - Identify trades with P/L > 3 standard deviations from mean
  - Calculate what % of total P/L comes from top 5 trades
  - Calculate what % of total P/L comes from bottom 5 trades
  - Flag any single trade contributing >20% of total profits

- **Concentration Analysis**:
  - Determine if results are dominated by few trades
  - Calculate Top 5 dependency: (Top 5 trades P/L ÷ Total P/L) × 100%
  - If Top 5 > 80%, mark as "outlier-dependent strategy"

- **Unrealistic Values**:
  - Flag any individual trade with >50% return
  - Flag any trades with exact round numbers (possible hardcoded values)
  - Check for impossible price movements given ATR/volatility

- **Distribution Analysis**:
  - Is P/L distribution uniform or concentrated?
  - Count trades in brackets: <-5%, -5-0%, 0-2%, 2-5%, >5%
  - Assess if distribution is normal, skewed, or bimodal

## 3. Analiza Rozkładu

Describe the shape and characteristics:

- **Distribution Shape**: Normal, skewed left/right, fat-tailed, bimodal
- **Mean vs Median Comparison**:
  - If Mean Win >> Median Win → positive skew (few large winners)
  - If Mean Loss >> Median Loss → negative skew (few catastrophic losses)
  - Median is more robust to outliers - compare both

- **Skewness Interpretation**:
  - Right-skewed profits = lottery-like (few huge wins)
  - Left-skewed losses = tail risk (rare but devastating losses)

## 4. Risk-Reward Realism

Critically assess:

- **Return/DD Ratio**: Total Return ÷ Max Drawdown
  - <3.0 = Marginal
  - 3.0-5.0 = Good
  - 5.0-10.0 = Excellent
  - >10.0 = Potentially unrealistic (verify carefully)

- **Equity Curve Analysis**:
  - Calculate max drawdown from peak equity
  - Check if equity curve is smooth or based on 1-2 extreme trades
  - Calculate average drawdown vs maximum drawdown
  - Flag if max DD occurred in a single trade

- **Trade Sequence Realism**:
  - Check for unrealistic win/loss streaks (>10 consecutive wins)
  - Calculate longest winning streak and losing streak
  - Assess if streaks follow statistical probability

- **Live Trading Viability**:
  - Would this strategy survive typical slippage (0.05-0.1%)?
  - Would transaction costs (0.1% round-trip) destroy the edge?
  - Are TP/SL distances realistic given market volatility?

## 5. Ocena Realności

Evaluate whether results could occur in live markets:

- **Market Possibility**:
  - Are returns consistent with asset volatility?
  - Do trade durations make sense for timeframe?
  - Are there suspicious patterns (too perfect, too consistent)?

- **Sequence Logic**:
  - Do win/loss sequences follow random distribution?
  - Are there unnatural patterns (alternating wins/losses)?
  - Check for look-ahead bias indicators

- **Script/Data Errors**:
  - Are there duplicate trades at exact same timestamp?
  - Are there trades with zero P/L (possibly incomplete)?
  - Are entry/exit prices logical given direction?
  - Do timestamps progress chronologically?

</analysis_requirements>

<output_format>

Provide analysis in this structure:

## 📊 STATISTICAL SUMMARY

[Table with all basic statistics]

## 🔍 ANOMALY DETECTION

**Outliers Found:**
[List any trades >3 SD from mean with details]

**Concentration Analysis:**
- Top 5 trades contribute: X% of total P/L
- Bottom 5 trades contribute: X% of total P/L
- Dependency classification: [Low/Medium/High/Extreme]

**Unrealistic Values:**
[List any flagged values with reasoning]

## 📈 DISTRIBUTION ANALYSIS

**Shape:** [Description]
**Skewness:** [Mean vs Median comparison and interpretation]
**Trade Distribution:**
[Histogram or table showing P/L brackets]

## ⚖️ RISK-REWARD ASSESSMENT

**Return/DD Ratio:** X.XXx ([Classification])
**Equity Curve Quality:** [Smooth/Volatile/Outlier-dependent]
**Max Drawdown Context:** [Single trade or accumulated]
**Trade Sequence:** [Realistic/Suspicious patterns noted]

## ✅ FINAL VERDICT

Choose ONE and explain reasoning:

**🟢 REALISTYCZNE** - Results appear achievable in live trading
- [List supporting evidence]
- [Note any caveats]

**🟡 CZĘŚCIOWO PODEJRZANE** - Results show concerning patterns
- [List specific concerns]
- [Recommend further investigation or adjustments]

**🔴 EWIDENTNIE BŁĘDNE** - Results are unrealistic or contain errors
- [List critical issues]
- [Recommend actions: fix data, revise strategy, etc.]

</output_format>

<verification>

Before declaring analysis complete:

1. Every calculation has been double-checked
2. All anomalies have been identified and explained
3. Distribution characteristics are clearly described
4. Return/DD ratio has been validated against realistic benchmarks
5. Final verdict is supported by concrete evidence from the data
6. Any data quality issues (missing values, duplicates) are flagged

</verification>

<success_criteria>

- All 5 analysis sections completed with specific numbers
- Clear identification of any outliers or anomalies
- Statistical metrics calculated correctly
- Risk-reward assessment includes specific thresholds
- Final verdict is unambiguous with supporting reasoning
- User can confidently decide whether to deploy strategy or investigate further

</success_criteria>

<constraints>

- Use actual calculations from the data - do not make assumptions
- Flag anything that looks "too good to be true" - skepticism protects capital
- Compare results to known benchmarks (e.g., professional traders rarely exceed 5x Return/DD sustained)
- If data format is unclear, ask for clarification before proceeding
- Provide specific row numbers or trade IDs when flagging anomalies

</constraints>