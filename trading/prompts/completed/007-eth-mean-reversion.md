<objective>
Discover profitable mean reversion trading strategies on ETH/USDT 1-minute data that achieve >4:1 profit-to-drawdown ratio.

Goal: Find strategies that profit from price returning to average levels (RSI oversold/overbought, Bollinger Band bounces, etc.)

Success target: 40%+ total return with <10% max drawdown (or better ratios)
</objective>

<context>
Data source: `./trading/eth_usdt_1m_lbank.csv` (43,201 candles, 30 days from LBank)
Asset characteristics: ETH is more stable than FARTCOIN - explosive breakouts may be rare, but mean reversion opportunities might be more frequent
Leverage available: 1x to 20x (you choose optimal leverage for each strategy)
Fee structure: 0.005% BingX taker fee on entry + exit

WHY mean reversion: In ranging or consolidating markets, prices tend to revert to the mean. ETH might spend more time in ranges than trending, making mean reversion profitable.
</context>

<research>
Before backtesting, analyze the ETH data:
1. Calculate volatility distribution (ATR percentages)
2. Identify consolidation periods vs trending periods
3. Check if Bollinger Band width correlates with mean reversion success
4. Determine optimal RSI levels for this specific asset

Use this analysis to inform your strategy parameters.
</research>

<requirements>
Test multiple mean reversion approaches:

1. **RSI Mean Reversion**
   - Buy oversold (RSI < threshold), sell overbought (RSI > threshold)
   - Test RSI periods: 7, 14, 21
   - Test oversold levels: 20, 25, 30
   - Test overbought levels: 70, 75, 80
   - Find optimal stop/target ratios

2. **Bollinger Band Bounce**
   - Buy at lower band, sell at upper band
   - Only trade when BB width is tight (low volatility = ranging)
   - Test BB threshold positions: 0.05, 0.1, 0.15 (distance from band)
   - Test different BB width limits

3. **Double Mean Reversion**
   - Combine RSI + BB for higher confidence
   - Entry when both indicators confirm oversold/overbought
   - Test if stricter filters improve profit/DD ratio

For each approach, test:
- Stop loss multiples: 1.5x, 2.0x, 2.5x ATR
- Take profit multiples: 3x, 4x, 5x, 6x ATR
- Leverage options: 5x, 10x, 15x, 20x
- Minimum trade spacing (avoid overtrading)
</requirements>

<implementation>
Use the row-by-row backtest approach (NOT vectorized) to avoid look-ahead bias:

```python
for i in range(250, len(df)):
    row = df.iloc[i]

    if not in_position:
        signal = check_mean_reversion_signal(row)
        if signal:
            enter_trade()
    else:
        check_exit_conditions(row)
```

Calculate profit/DD ratio for each strategy variant:
- profit_dd_ratio = abs(total_return / max_drawdown)
- Filter results: only show strategies with profit_dd_ratio >= 4.0

Consider position sizing:
- Fixed size (same for all trades)
- Volatility-based (smaller size in high volatility)
- Anti-martingale (increase after wins)
</implementation>

<output>
Create file: `./trading/eth_mean_reversion_results.md`

Include:
1. Summary table of top 10 strategies (sorted by profit/DD ratio)
2. Detailed analysis of the BEST strategy including:
   - All parameters
   - Trade-by-trade results CSV
   - Equity curve visualization (if possible)
   - Win rate, avg win, avg loss
   - Expected return with recommended leverage
   - Max drawdown at recommended leverage

3. Key insights about ETH mean reversion:
   - Which RSI levels work best?
   - Does BB width filtering improve results?
   - Optimal volatility conditions
   - Time-of-day patterns (if any)
</output>

<success_criteria>
- At least ONE strategy with profit/DD ratio >= 4.0
- Minimum 10 trades (not too selective)
- Clear recommendation for best strategy with exact parameters
- Expected returns calculated with fees and leverage included
- Verification that backtest uses row-by-row iteration (no look-ahead bias)
</success_criteria>

<verification>
Before declaring complete:
1. Manually check 2-3 trades from best strategy to confirm SL/TP logic is correct
2. Verify that with recommended leverage, max DD stays under user's 40% tolerance
3. Confirm fee calculations include both entry and exit (0.01% total per trade at 10x leverage = 0.1% drag)
4. Double-check that profit/DD ratio calculation is: total_return / abs(max_drawdown)
</verification>
