<objective>
Discover profitable trend-following trading strategies on ETH/USDT 1-minute data that achieve >4:1 profit-to-drawdown ratio.

Goal: Find strategies that ride trends (EMA pullbacks, breakouts, momentum) rather than counter-trend mean reversion.

Success target: 40%+ total return with <10% max drawdown (or better ratios)
</objective>

<context>
Data source: `./trading/eth_usdt_1m_lbank.csv` (43,201 candles, 30 days from LBank)
Asset characteristics: ETH may have sustained trends when Bitcoin or macro news moves markets
Leverage available: 1x to 20x (you choose optimal leverage for each strategy)
Fee structure: 0.005% BingX taker fee on entry + exit

WHY trend following: While ETH might range more than memecoins, when trends do develop they can be strong and profitable. Higher R:R ratios possible.
</context>

<research>
Before backtesting, analyze the ETH data:
1. Identify trending vs ranging periods (compare EMA slopes)
2. Calculate average trend duration and magnitude
3. Determine if volume spikes correlate with trend starts
4. Check if certain hours of day have stronger trends (NY open, London open, Asian session)

Use this analysis to inform your strategy parameters and filters.
</research>

<requirements>
Test multiple trend-following approaches:

1. **EMA Pullback Strategy**
   - Identify trend: fast EMA > slow EMA (uptrend) or vice versa (downtrend)
   - Wait for pullback to fast EMA
   - Enter when price crosses back above/below EMA
   - Test EMA pairs: (9,50), (20,50), (20,100)
   - Test different pullback depths

2. **Volume Breakout Strategy**
   - Detect breakout above/below recent range
   - Require high volume confirmation (>2x, >2.5x, >3x average)
   - Only trade breakouts with strong candle bodies (>50% of range)
   - Test different volume thresholds

3. **Multi-Timeframe Trend**
   - 1-min signal + 5-min trend confirmation
   - Only LONG when both timeframes show uptrend
   - Only SHORT when both timeframes show downtrend
   - Test different trend definitions (EMA, SMA, price action)

4. **Momentum Continuation**
   - Detect strong momentum candles (large body, high volume)
   - Enter in direction of momentum
   - Tight stops, wide targets (1:4 or 1:6 R:R)

For each approach, test:
- Stop loss multiples: 2.0x, 2.5x, 3.0x, 3.5x ATR
- Take profit multiples: 6x, 8x, 10x, 12x ATR (higher R:R for trends)
- Leverage options: 5x, 10x, 15x, 20x
- Trend filters (only trade when trend is clear)
</requirements>

<implementation>
Use row-by-row backtest approach (NOT vectorized):

```python
for i in range(250, len(df)):
    row = df.iloc[i]

    # For multi-timeframe, get CLOSED 5-min candle
    if df_5min is not None:
        current_timestamp = row['timestamp']
        closed_5min = df_5min[df_5min['timestamp'] < current_timestamp].iloc[-1]

    if not in_position:
        signal = check_trend_signal(row, closed_5min)
        if signal:
            enter_trade()
    else:
        check_exit_conditions(row)
```

Calculate profit/DD ratio for each strategy variant:
- profit_dd_ratio = abs(total_return / max_drawdown)
- Filter results: only show strategies with profit_dd_ratio >= 4.0

Consider position sizing:
- Fixed size
- ATR-based (smaller in high volatility)
- Confidence-based (larger when all filters align)
</implementation>

<output>
Create file: `./trading/eth_trend_following_results.md`

Include:
1. Summary table of top 10 strategies (sorted by profit/DD ratio)
2. Detailed analysis of the BEST strategy including:
   - All parameters
   - Trade-by-trade results CSV
   - Win rate, avg win, avg loss
   - R:R ratio achieved
   - Expected return with recommended leverage
   - Max drawdown at recommended leverage

3. Key insights about ETH trend following:
   - Which EMA pairs work best?
   - Does volume filtering significantly improve results?
   - Multi-timeframe confirmation worth the reduced trade count?
   - Optimal stop/target ratios for ETH trends
</output>

<success_criteria>
- At least ONE strategy with profit/DD ratio >= 4.0
- Minimum 8 trades (trend strategies are naturally more selective)
- Clear recommendation for best strategy with exact parameters
- Expected returns calculated with fees and leverage included
- Verification that backtest uses row-by-row iteration with closed candles only
</success_criteria>

<verification>
Before declaring complete:
1. Manually check 2-3 trades to confirm trend identification is correct
2. For multi-timeframe strategies, verify only CLOSED 5-min candles were used
3. Verify that with recommended leverage, max DD stays under 40% tolerance
4. Confirm high R:R targets are achievable (check if TPs actually get hit)
</verification>
