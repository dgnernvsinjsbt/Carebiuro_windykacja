<objective>
Develop a profitable SHORT-ONLY trading strategy for PI/USDT using historical 15-minute candlestick data.

The goal is to find consistent, repeatable patterns that indicate price will decline, allowing profitable short entries with good risk/reward characteristics.
</objective>

<context>
Data source: `trading/pi_15m_3months.csv` - 3 months of 15-minute candles for PI/USDT
Fee structure: 0.005% taker fee on BOTH sides (open and close) = 0.01% round-trip cost
Focus: SHORT positions only (profiting from price declines)

PI is a volatile altcoin - look for patterns that exploit this volatility for short entries.
</context>

<research>
Before developing the strategy, thoroughly analyze the PI/USDT data:

1. Load and examine the data structure (columns, date range, price range)
2. Calculate basic statistics: volatility, average daily range, trend characteristics
3. Identify regime characteristics - is PI trending, mean-reverting, or mixed?
4. Look for patterns that precede significant price drops:
   - Overbought conditions (RSI, distance from MAs)
   - Rejection patterns (wicks, failed breakouts)
   - Volume anomalies before drops
   - Time-of-day patterns for selloffs
5. Analyze existing strategies in `trading/strategies.py` for patterns to adapt
</research>

<requirements>
Develop a shorting strategy with these characteristics:

1. **Entry Criteria**: Clear, objective rules for when to enter short positions
   - Consider: RSI overbought, EMA crossovers, price rejection patterns, volume spikes
   - Multiple confirming signals preferred over single indicator

2. **Exit Criteria**: Define both profit-taking and stop-loss rules
   - Take-profit: Fixed percentage, trailing stop, or indicator-based
   - Stop-loss: Maximum acceptable loss per trade (suggest 1-3%)
   - Consider time-based exits for stale positions

3. **Position Sizing**: Account for fees in profitability calculations
   - Round-trip fee: 0.01% (0.005% open + 0.005% close)
   - Minimum profitable move must exceed fees

4. **Risk Management**:
   - Maximum concurrent short positions
   - Daily/weekly loss limits
   - Avoid shorting during strong uptrends

5. **Performance Metrics** to calculate:
   - Total return (after fees)
   - Win rate
   - Average win vs average loss
   - Maximum drawdown
   - Sharpe ratio (if possible)
   - Profit factor
   - Number of trades
</requirements>

<implementation>
Create a Python backtest script that:

1. Loads `trading/pi_15m_3months.csv`
2. Implements your shorting strategy with clear entry/exit logic
3. Simulates trades with 0.005% fee on each side
4. Tracks equity curve and all trade statistics
5. Outputs detailed results

Strategy ideas to explore (pick best performing):
- **Overbought RSI shorts**: Short when RSI > 70-80, exit when RSI < 50
- **EMA rejection shorts**: Short when price touches upper EMA band and shows rejection
- **Failed breakout shorts**: Short after price fails to hold above resistance
- **Volume climax shorts**: Short after unusual volume spike with upper wick
- **Mean reversion shorts**: Short when price is X% above short-term moving average

Thoroughly test multiple parameter combinations to find optimal settings.
</implementation>

<output>
Create these files:

1. `trading/pi_short_backtest.py` - Main backtest script with the shorting strategy
2. `trading/results/pi_short_summary.csv` - Trade-by-trade results
3. `trading/results/pi_short_analysis.md` - Written analysis including:
   - Strategy description and rationale
   - Key parameters and why they were chosen
   - Performance metrics (all listed above)
   - Equity curve description
   - Recommendations for live trading
   - Known limitations and risks
</output>

<verification>
Before declaring complete, verify:
- [ ] Strategy is profitable AFTER accounting for 0.01% round-trip fees
- [ ] At least 20+ trades in the backtest for statistical significance
- [ ] Win rate and average win/loss ratio are realistic (not curve-fitted)
- [ ] Maximum drawdown is acceptable (suggest < 20%)
- [ ] Strategy logic is clearly documented in code comments
- [ ] Results are saved to specified output files
</verification>

<success_criteria>
A successful strategy should demonstrate:
- Positive total return after all fees
- Profit factor > 1.2 (gross profit / gross loss)
- Reasonable win rate (40%+ with good risk/reward, or 50%+ with moderate R:R)
- Clear, objective entry/exit rules that can be automated
- Robustness across different market conditions in the data
</success_criteria>
