<objective>
Test 3 traditional trading strategies (Trend Following, Mean Reversion, Breakout) adapted for 1-minute timeframe on BTC/ETH data, since the explosive momentum strategy failed on these assets.

Goal: Determine if traditional strategies work better on major cryptocurrencies (BTC/ETH) than pattern-based momentum strategies, and find which approach yields the best risk:reward ratio on 1-minute data.
</objective>

<context>
Previous testing showed that the V7 explosive momentum strategy (8.88x R:R on memecoins) completely failed on BTC/ETH due to low volatility:
- BTC: 0 trades, 33% range
- ETH: 1-8 trades, -0.67% return, 39% range
- Root cause: Strategy requires 50%+ volatility, BTC/ETH only have 15-40%

These traditional strategies were suggested as alternatives but designed for higher timeframes (1H/4H/1D). We need to adapt them for 1-minute timeframe and test if they work.

**Available data:**
- btc_usdt_1m_lbank.csv (43,202 candles, 30 days)
- eth_usdt_1m_lbank.csv (43,201 candles, 30 days)

**Original strategy specs (need adaptation):**

1. **Trend Following** (was 4H/1D → adapt to 1m)
   - MA crossovers, MACD, trend channels
   - Target R:R: 2:1, Win Rate: 40-50%
   - Expected: 5-10% monthly returns

2. **Mean Reversion** (was 1H → adapt to 1m)
   - RSI + Bollinger Bands in ranging markets
   - Target R:R: 1.5:1, Win Rate: 60-70%
   - Expected: 8-15% monthly returns

3. **Breakout Trading** (was 1H/4H → adapt to 1m)
   - Key level breaks + volume confirmation
   - Target R:R: 2:1, Win Rate: 45%
   - Expected: 5-12% monthly returns
</context>

<requirements>

## 1. Strategy Implementations

Create 3 separate strategy classes, each adapted for 1-minute timeframe:

### Strategy 1: Trend Following (1m adaptation)
**Indicators:**
- Fast SMA: 20 periods (20 minutes)
- Slow SMA: 50 periods (50 minutes)
- MACD: (12, 26, 9) - standard settings
- Trend filter: Both SMAs aligned (fast > slow = uptrend, fast < slow = downtrend)

**Entry Signals:**
- **Long:** Fast SMA crosses above Slow SMA + MACD line above signal + MACD histogram positive
- **Short:** Fast SMA crosses below Slow SMA + MACD line below signal + MACD histogram negative

**Exit Rules:**
- Take Profit: 2% from entry (2:1 R:R target)
- Stop Loss: 1% from entry
- Trailing stop: Move SL to breakeven after +1% profit

**Position Sizing:** 2% risk per trade

### Strategy 2: Mean Reversion (1m adaptation)
**Indicators:**
- RSI: 14 periods
- Bollinger Bands: 20 periods, 2 std dev
- Volume: 20-period SMA for volume confirmation

**Entry Signals:**
- **Long (oversold):** RSI < 30 + price touches lower BB + volume > avg volume
- **Short (overbought):** RSI > 70 + price touches upper BB + volume > avg volume

**Exit Rules:**
- Take Profit: Middle BB (mean reversion target)
- Stop Loss: 1.5% from entry
- Time exit: Exit after 60 minutes if neither TP nor SL hit

**Position Sizing:** 2% risk per trade

### Strategy 3: Breakout Trading (1m adaptation)
**Indicators:**
- Support/Resistance: 50-period highs/lows
- Volume: 20-period volume SMA
- ATR: 14 periods for volatility filter

**Entry Signals:**
- **Long breakout:** Price breaks above 50-period high + volume > 1.5x avg + ATR > 50th percentile
- **Short breakdown:** Price breaks below 50-period low + volume > 1.5x avg + ATR > 50th percentile

**Exit Rules:**
- Take Profit: 2x ATR from entry (2:1 R:R target)
- Stop Loss: 1x ATR from entry
- Trailing stop: Trail by 1x ATR once in profit

**Position Sizing:** 2% risk per trade

## 2. Backtesting Requirements

For EACH strategy on BOTH coins (6 total backtests):

**Metrics to track:**
- Total return %
- Max drawdown %
- R:R ratio (return / drawdown)
- Number of trades
- Win rate %
- Profit factor
- Average win vs average loss
- Average trade duration (minutes)
- Sharpe ratio (if possible)

**Trade logging:**
- Entry time, price, direction
- Exit time, price, reason (TP/SL/time)
- P&L per trade
- Running equity curve

## 3. Optimization (Optional Phase 2)

If baseline results show promise (R:R > 1.5x), test parameter variations:
- Trend Following: SMA periods (15/40, 20/50, 30/70)
- Mean Reversion: RSI levels (25/75, 30/70, 35/65)
- Breakout: Volume threshold (1.3x, 1.5x, 2.0x)

## 4. Comparative Analysis

Create comparison showing:
- Which strategy works best on BTC vs ETH
- How 1m performance compares to expected higher-timeframe performance
- Whether traditional strategies outperform explosive momentum on BTC/ETH
- Trade frequency analysis (too many/too few trades?)
</requirements>

<implementation>

## Script Structure

Create: `strategies/btc-eth-traditional-strategies.py`

**Key components:**

1. **Base Strategy Class**
```python
class BaseStrategy:
    def __init__(self, data, risk_per_trade=0.02):
        self.data = data
        self.risk = risk_per_trade
        self.trades = []
        self.equity_curve = []

    def calculate_indicators(self):
        # Implement indicators
        pass

    def generate_signals(self):
        # Entry/exit logic
        pass

    def backtest(self):
        # Run backtest
        pass

    def calculate_metrics(self):
        # Performance metrics
        pass
```

2. **3 Strategy Implementations**
- `TrendFollowingStrategy(BaseStrategy)`
- `MeanReversionStrategy(BaseStrategy)`
- `BreakoutStrategy(BaseStrategy)`

3. **Main Execution Loop**
```python
for coin in ['BTC', 'ETH']:
    for strategy_class in [TrendFollowing, MeanReversion, Breakout]:
        # Load data
        # Run backtest
        # Save results
```

## Technical Considerations

**1-minute timeframe adaptations:**
- Indicators must be fast enough to avoid lag but filter noise
- Position holding time: Expect 30-120 minutes per trade
- Commission/slippage: Add 0.1% per trade (realistic for 1m trading)
- Avoid overtrading: Max 5 open positions simultaneously

**Data handling:**
- Use pandas for indicator calculation
- Use TA-Lib or pandas_ta if available, else manual calculation
- Handle missing data/gaps appropriately

**Performance:**
- Expect lower returns on 1m than stated targets (those were for 1H/4H)
- Realistic 1m targets: 2-5% monthly (vs 5-15% for higher TF)
- Higher win rate but smaller wins on 1m (frequent small gains)

**Why these adaptations:**
- 1m has more noise → need stronger filters (volume, ATR)
- Timeouts prevent getting stuck in bad trades
- Trailing stops capture profits in fast-moving 1m markets
- 2% risk keeps losses manageable with frequent trading
</implementation>

<output>

Create these files:

1. **Main script:** `./strategies/btc-eth-traditional-strategies.py`
   - Contains all 3 strategy implementations
   - Runs all 6 backtests (3 strategies × 2 coins)
   - Generates results automatically

2. **Results CSV:** `./strategies/traditional-strategies-results.csv`
   - Columns: coin, strategy, return%, max_dd, rr_ratio, trades, win_rate, profit_factor, avg_duration_min
   - One row per backtest (6 rows total)

3. **Best config per strategy:** `./strategies/traditional-best-[strategy-name].json`
   - Save best-performing config for each strategy type
   - Example: `traditional-best-trend-following.json`

4. **Analysis report:** `./strategies/TRADITIONAL-STRATEGIES-1M-RESULTS.md`
   - Comparison table of all results
   - Which strategy works best on BTC vs ETH
   - Performance vs explosive momentum strategy
   - Recommendations for live trading
   - Answer: Do traditional strategies work better than pattern-based momentum on BTC/ETH?

5. **Equity curves:** `./strategies/equity-curve-[coin]-[strategy].csv` (if time permits)
   - Timestamp, equity, trade_count for visualization
</output>

<verification>

Before declaring complete, verify:

1. ✓ All 3 strategies implemented with 1m-adapted parameters
2. ✓ All 6 backtests completed (BTC×3 + ETH×3)
3. ✓ CSV results file generated with all metrics
4. ✓ Analysis report created answering key questions
5. ✓ At least one strategy achieves R:R > 1.0x on either coin
6. ✓ Trade frequency is reasonable (not 0, not 1000+)
7. ✓ Report clearly states whether traditional strategies outperform explosive momentum

**Key validation checks:**
- If a strategy generates 0 trades → flag as too restrictive
- If a strategy generates 500+ trades → flag as overtrading
- If win rate is 0% or 100% → check for implementation bugs
- If all strategies fail (R:R < 1.0x) → document why and suggest next steps
</verification>

<success_criteria>

**Minimum success:**
- All 6 backtests complete without errors
- At least 1 strategy achieves R:R > 1.0x on at least 1 coin
- Results CSV and analysis report generated
- Clear answer to: "Do traditional strategies work on BTC/ETH 1m data?"

**Ideal success:**
- At least 2 strategies show positive R:R (>1.5x)
- Win rates match expected ranges (40-70%)
- Trade frequency reasonable (20-100 trades per strategy per coin)
- Clear recommendation which strategy to pursue for live trading
- Performance comparable to or better than explosive momentum baseline

**Expected outcome:**
Given BTC/ETH's lower volatility, realistic targets for 1m are:
- R:R: 1.0-2.0x (lower than 4H/1D targets)
- Win rate: 45-65%
- Monthly return: 2-5% (vs 5-15% for higher TF)

If ALL strategies fail (R:R < 0.5x):
- Document why (too noisy, not enough volatility, poor timeframe match)
- Suggest testing on 5m or 15m timeframe instead
- Confirm that BTC/ETH may not be suitable for 1m algorithmic trading
</success_criteria>

<constraints>

**What to avoid and WHY:**

1. **Don't use future data in signals** (look-ahead bias)
   - WHY: Indicators must calculate from past data only, never peek into future
   - Example: Use `close[i-1]` for signal at bar `i`, not `close[i]`

2. **Don't ignore commission/slippage** (unrealistic results)
   - WHY: 1m trading has high turnover, 0.1% per trade compounds quickly
   - Add to backtest: `pnl -= 0.001 * position_size` on entry/exit

3. **Don't overtrade** (execution risk)
   - WHY: Real trading can't execute 1000 trades/month, leads to failed orders
   - Max 5 simultaneous positions, min 10 trades/month for statistical validity

4. **Don't use overly complex indicators** (overfitting risk)
   - WHY: Complex = more parameters = more overfitting on limited 30-day data
   - Keep it simple: Standard SMA, RSI, BB, MACD only

5. **Don't expect 4H/1D performance on 1m data** (timeframe mismatch)
   - WHY: 1m is noisier, has smaller moves, requires different targets
   - Adjust expectations: 2:1 R:R instead of 5:1, 2% returns instead of 10%

6. **Don't test on same data used for development** (overfitting)
   - WHY: Parameters tuned to training data won't generalize
   - If optimizing, split data: First 20 days = train, last 10 days = validate
</constraints>

<research>

**Files to examine before implementation:**

1. @strategies/explosive-v7-advanced.py
   - See how backtest engine is structured
   - Reuse metric calculation logic
   - Understand trade logging format

2. @strategies/multi-coin-optimizer-btc-eth.py
   - See how BTC/ETH data is loaded
   - Reuse data loading utilities
   - Understand result formatting

3. Check if pandas_ta or talib is available:
   - `!pip list | grep -E 'pandas_ta|talib'`
   - If not available, implement indicators manually with pandas

**Technical details to research:**
- How to calculate MACD manually if no library
- Bollinger Bands calculation: `middle = SMA(20), upper/lower = middle ± 2*std`
- Support/Resistance: `resistance = high.rolling(50).max(), support = low.rolling(50).min()`
</research>

<examples>

**Good vs Bad indicator calculation:**

❌ **Bad (look-ahead bias):**
```python
signals['long'] = (close > sma_20) & (close.shift(-1) > close)  # Uses future!
```

✅ **Good:**
```python
signals['long'] = (close > sma_20) & (close > close.shift(1))  # Uses past only
```

**Good vs Bad position sizing:**

❌ **Bad (fixed size):**
```python
position_size = 1000  # Ignores risk management
```

✅ **Good (risk-based):**
```python
risk_amount = equity * 0.02  # 2% risk
stop_distance = entry - stop_loss
position_size = risk_amount / stop_distance
```

**Good vs Bad result interpretation:**

❌ **Bad:**
"Strategy achieved 50% win rate with 30 trades."

✅ **Good:**
"Strategy achieved 50% win rate with 30 trades over 30 days (1 trade/day frequency). This is statistically significant (n=30) and matches expected 40-50% target. However, R:R of 0.8x indicates losses outweigh wins despite good win rate."
</examples>
