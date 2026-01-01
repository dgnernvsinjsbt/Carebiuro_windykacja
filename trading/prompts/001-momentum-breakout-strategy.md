<objective>
Develop a high risk:reward (8:1+) momentum breakout trading strategy for FARTCOIN/USDT 1-minute chart data. Focus on capturing explosive moves by identifying compression patterns followed by volatility expansion.

This strategy will exploit memecoin volatility characteristics where periods of consolidation are followed by rapid directional moves.
</objective>

<context>
You have OHLCV data (timestamp, open, high, low, close, volume) from FARTCOIN/USDT 1-minute candles.

Memecoin characteristics:
- Extreme volatility creates opportunity for asymmetric returns
- Strong momentum when moves begin
- Volume precedes price on major moves
- 1-minute timeframe captures intraday volatility explosions

Goal: Achieve 8:1 risk:reward by using tight stops and riding full momentum waves.
</context>

<requirements>
1. Load and analyze the FARTCOIN/USDT CSV data
2. Design a breakout strategy using ONLY OHLCV data:
   - Identify consolidation zones (low volatility periods)
   - Detect breakout triggers (price + volume confirmation)
   - Set tight stop losses (just below/above breakout level)
   - Target 8R+ profit levels (ride the momentum wave)
3. Calculate technical indicators using pandas/numpy:
   - ATR (Average True Range) for volatility measurement
   - Volume moving averages for surge detection
   - Bollinger Bands or similar for compression identification
   - Price range analysis for breakout confirmation
4. Backtest the strategy on the data and generate:
   - Win rate
   - Average risk:reward achieved
   - Profit factor
   - Maximum drawdown
   - Total trades
   - Equity curve
5. Include position sizing rules based on stop loss distance
6. Account for 0.1% trading fees (entry + exit = 0.2% total)
</requirements>

<implementation>
Strategy components:

1. **Consolidation Detection**:
   - Measure ATR to identify low volatility periods
   - Look for price compression (narrow range candles)
   - Volume decrease during consolidation

2. **Breakout Entry Triggers**:
   - Price breaks above/below consolidation range
   - Volume surge (2x+ recent average)
   - Strong directional candle (close near high/low)
   - Enter on next candle open after confirmation

3. **Stop Loss Placement**:
   - Place stop just beyond consolidation range
   - Maximum 0.5-1% of capital at risk per trade
   - Tight stops enable 8R targets

4. **Profit Targets**:
   - Primary target: 8x stop loss distance
   - Secondary target: 12x stop loss distance (partial exit)
   - Trailing stop: Activate after 5R to protect gains

5. **Exit Rules**:
   - Hit profit target
   - Stop loss triggered
   - Momentum dies (candle closes against position)
   - Time stop: Exit after 30 minutes if no movement

WHY these rules work:
- Consolidation = energy buildup for next move
- Volume surge = institutional/whale participation
- Tight stops = can afford to lose 4+ times and still profit on 1 winner
- Riding full move = captures the entire volatility expansion
</implementation>

<output>
Create these files in `./strategies/`:

1. `breakout-strategy-analysis.md`
   - Strategy rules and logic
   - Entry/exit criteria with examples
   - Risk management framework
   - Backtest results and insights

2. `breakout-strategy.py`
   - Python implementation using pandas
   - Load CSV data function
   - Technical indicator calculations
   - Backtesting engine
   - Performance metrics calculation

3. `breakout-trades.csv`
   - Log of all trades from backtest
   - Columns: timestamp, direction, entry, stop, target, exit, pnl, r_multiple, reason

4. `breakout-equity-curve.csv`
   - Equity progression over time
   - Cumulative P&L, drawdown tracking
</output>

<verification>
Before completing, verify:

1. ✓ Code loads the FARTCOIN CSV data successfully
2. ✓ Strategy generates at least 20+ trades for statistical validity
3. ✓ Average R:R across all trades is 6:1 or higher
4. ✓ At least 15-20% win rate (needed for profitability at 8R)
5. ✓ Maximum drawdown is acceptable (under 25%)
6. ✓ Profit factor > 1.5 (strategy is profitable after fees)
7. ✓ Code runs without errors and outputs all files

Test edge cases:
- What happens during extreme volatility?
- Does strategy avoid false breakouts effectively?
- Are stop losses realistic given 1-minute candle ranges?
</verification>

<success_criteria>
- Strategy achieves 8:1+ average risk:reward on winning trades
- Positive expected value: (Win% × Avg Win) - (Loss% × Avg Loss) > 0
- Clear edge identified: WHY does this strategy work on FARTCOIN?
- Reproducible results: Anyone can run the Python code and get same results
- Documentation explains the logic in plain language
- Trade log shows realistic entries/exits based on actual candle data
</success_criteria>