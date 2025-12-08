<objective>
Simulate the full trading bot portfolio over 30 days using actual backtest trade data from all strategies.

Merge ALL trades from all strategies chronologically and simulate a single portfolio where:
- Starting equity: $10,000
- Each trade uses 100% of current equity
- 1x leverage (no margin)
- Track open positions that lock up capital and affect unrealized P&L
- Calculate final equity, max drawdown, total return, and risk metrics
</objective>

<context>
The bot trades 6 tokens with different strategies:
1. FARTCOIN - Multi-Timeframe Long + Trend Distance Short
2. MOODENG - RSI Momentum Long
3. DOGE - Volume Zones
4. PEPE - Volume Zones
5. TRUMP - Volume Zones
6. UNI - Volume Zones

Each strategy has backtest results with individual trade logs in CSV format.
</context>

<data_sources>
Load trade data from these CSV files (they contain entry_time, exit_time, direction, entry_price, exit_price, pnl_pct, etc.):

@trading/results/FARTCOIN_LONG_detailed_trades.csv
@trading/results/moodeng_audit_trades.csv (or moodeng_strategy_backtest.csv)
@trading/results/DOGE_volume_zones_optimized_trades.csv
@trading/results/PEPE_volume_zones_optimized_trades.csv
@trading/results/TRUMP_volume_zones_optimized_trades.csv
@trading/results/UNI_volume_zones_trades.csv

If a file doesn't exist, check for alternatives in trading/results/ with similar names.
</data_sources>

<simulation_requirements>
1. **Merge All Trades Chronologically**
   - Load all trade CSVs
   - Normalize column names (entry_time, exit_time, pnl_pct, direction)
   - Sort all trades by entry_time across all strategies
   - Tag each trade with its strategy/token source

2. **Position Management**
   - When a trade opens: lock 100% of current equity into that position
   - Track unrealized P&L while position is open
   - When a trade closes: update equity by realized P&L
   - Handle overlapping positions: if a new trade opens while another is still open, that capital is already locked - SKIP the new trade or use remaining equity

3. **Equity Curve Calculation**
   - Start: $10,000
   - At each trade close: equity = equity * (1 + pnl_pct/100)
   - Track max equity (high water mark)
   - Track drawdown = (current_equity - max_equity) / max_equity

4. **Output Metrics**
   - Final equity
   - Total return %
   - Max drawdown %
   - Return/Drawdown ratio
   - Total trades executed
   - Trades skipped (due to capital locked)
   - Win rate
   - Average win % vs average loss %
   - Longest winning streak / losing streak
   - Equity curve data for plotting

5. **Position Overlap Analysis**
   - How many trades overlapped in time?
   - How much potential profit was missed due to capital being locked?
   - Peak concurrent positions
</simulation_requirements>

<implementation>
Create a Python script that:

```python
# Pseudocode structure
1. Load all trade CSVs into DataFrames
2. Normalize columns and add 'strategy' tag
3. Concat and sort by entry_time
4. Initialize: equity=10000, positions=[], equity_curve=[]
5. For each trade (sorted by entry_time):
   - Check if capital is available (no open position)
   - If available: open position with current equity
   - If trade closes: realize P&L, update equity
   - Track equity at each close
6. Calculate all metrics
7. Save results to CSV and summary MD
```

Handle edge cases:
- Trades with no exit_time (still open at end of period)
- Trades with missing pnl_pct (calculate from prices)
- Duplicate timestamps (use secondary sort by strategy name)
</implementation>

<output>
Save results to:
- `./trading/results/PORTFOLIO_SIMULATION_30D.md` - Executive summary with all metrics
- `./trading/results/portfolio_equity_curve.csv` - Timestamp, equity, drawdown for each trade close
- `./trading/results/portfolio_all_trades.csv` - Merged trade log with execution status (executed/skipped)

Print summary to console showing:
- Final equity and return %
- Max drawdown and Return/DD ratio
- Breakdown by strategy (how much each contributed)
- Comparison: sum of individual strategy returns vs portfolio return
</output>

<verification>
Before completing:
1. Verify total trades loaded from each strategy
2. Confirm no duplicate trades in merged dataset
3. Validate equity never goes negative
4. Check that drawdown calculation is correct (should match worst peak-to-trough)
5. Cross-reference: portfolio max DD should be >= any individual strategy's DD
</verification>

<success_criteria>
- All 6 strategy trade files loaded and merged
- Chronological simulation completed without errors
- Clear metrics showing portfolio performance vs individual strategies
- Equity curve data saved for visualization
- Executive summary explaining whether portfolio diversification helped or hurt
</success_criteria>
