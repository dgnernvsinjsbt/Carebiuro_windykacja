<objective>
Develop and backtest multiple simple trading strategies on FARTCOIN/USDT 15-minute data to find a profitable long-only approach with daily compounding.

The user previously had slight success with a "green candle close → enter long, stop below candle low" strategy but fees ate profits. Now testing on zero-fee spot exchanges, we need to find the most profitable simple strategy.
</objective>

<context>
Data file: `./fartcoin_15m_3months.csv`
- 8,640 candles of 15-minute OHLC data
- Date range: 2025-09-04 to 2025-12-03
- Columns: timestamp, open, high, low, close

Trading constraints:
- Long only (no shorts)
- Zero trading fees (spot exchange with 0% maker/taker)
- No leverage - can use 100% of capital per trade
- Daily compounding (profits reinvested next day)
- 5% daily drawdown limit - halt trading for the day if hit
- Never hold positions past session close (each day is independent)
</context>

<strategies_to_test>
Test these simple strategies and variations:

1. **Green Candle Entry** (user's original)
   - Enter long on green candle close
   - Stop loss below that candle's low
   - Variations: require minimum candle size, consecutive greens

2. **Moving Average Strategies**
   - Price crosses above SMA/EMA (test 5, 10, 20, 50 periods)
   - Dual MA crossover (fast crosses above slow)
   - Price pullback to MA then continuation

3. **RSI Strategies**
   - RSI oversold bounce (RSI < 30 then crosses above)
   - RSI momentum (RSI crosses above 50)
   - Test different periods (7, 14, 21)

4. **Breakout Strategies**
   - Break above previous candle high
   - Break above N-period high (test 4, 8, 12 candles)
   - Break above session open price

5. **Combined/Hybrid**
   - Green candle + above MA
   - RSI oversold + price above MA
   - Breakout + volume confirmation (if volume available)

For each strategy, test multiple exit methods:
- Fixed R:R targets (1:1, 1:1.5, 1:2, 1:3)
- Trailing stop (ATR-based or candle-based)
- Time-based exit (exit after N candles)
- Opposite signal exit
</strategies_to_test>

<session_analysis>
Analyze profitability by time of day:
- Split the day into segments (e.g., 4-hour blocks or hourly)
- Identify which hours have best win rate and profit factor
- Test if restricting trading to optimal hours improves results
- Consider: Asian session (00:00-08:00), European (08:00-16:00), US (16:00-24:00)
</session_analysis>

<metrics_to_calculate>
For each strategy variation, calculate:
- Total return (%)
- Win rate (%)
- Profit factor (gross profit / gross loss)
- Max drawdown (%)
- Sharpe ratio (if possible)
- Average trade duration
- Number of trades
- Average win vs average loss
- Largest win / largest loss
- Daily returns distribution
- Days with 5% drawdown hit (halted days)
</metrics_to_calculate>

<implementation>
Create a Python backtesting script that:

1. Loads and preprocesses the CSV data
2. Implements each strategy as a testable function
3. Simulates realistic trading:
   - Start each day with current capital
   - Track intraday P&L
   - Halt if 5% daily drawdown hit
   - Compound to next day
4. Generates comparison table of all strategies
5. Identifies the top 3 performers
6. Performs deeper analysis on winners

Output files to create:
- `./trading/backtest.py` - Main backtesting engine
- `./trading/strategies.py` - Strategy implementations
- `./trading/results/summary.md` - Human-readable results summary
- `./trading/results/detailed_results.csv` - Full metrics for all strategies
</implementation>

<output_requirements>
The final summary should include:

1. **Strategy Ranking Table** - All strategies ranked by total return
2. **Top 3 Deep Dive** - Detailed analysis of best performers including:
   - Equity curve description
   - Monthly breakdown
   - Best/worst days
   - Optimal session hours (if any)
3. **Recommended Strategy** - Clear recommendation with:
   - Exact entry rules
   - Exact exit rules
   - Position sizing guidance
   - When to trade (hours)
   - Risk management rules
4. **Sample Trades** - Show 5-10 example trades from the best strategy
</output_requirements>

<verification>
Before completing:
- Verify all strategies were tested (minimum 10 variations)
- Confirm daily compounding is correctly implemented
- Check that 5% daily stop is enforced
- Validate that no trades span multiple days
- Ensure results are reproducible (same data, same results)
</verification>

<success_criteria>
- Comprehensive backtest of 15+ strategy variations completed
- Clear winner(s) identified with >20% total return over 3 months
- Optimal trading hours identified
- Actionable strategy with specific entry/exit rules documented
- All code is clean, commented, and reusable
</success_criteria>
