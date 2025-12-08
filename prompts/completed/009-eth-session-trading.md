<objective>
Discover if time-based trading (session optimization) improves strategy performance on ETH/USDT, achieving >4:1 profit-to-drawdown ratio.

Goal: Test whether trading only during specific hours (Asian, European, US sessions) or avoiding certain hours improves profitability and reduces drawdown.

Success target: 40%+ total return with <10% max drawdown through session filtering
</objective>

<context>
Data source: `./trading/eth_usdt_1m_lbank.csv` (43,201 candles, 30 days from LBank)
Trading sessions (UTC):
- Asian session: 23:00 - 07:00 UTC (Tokyo open)
- European session: 07:00 - 15:00 UTC (London open)
- US session: 13:00 - 21:00 UTC (NY open, overlaps with London)
- Off-hours: 21:00 - 23:00 UTC (lowest volume)

WHY session trading: Crypto markets trade 24/7 but liquidity and volatility vary by time. Certain sessions might have clearer trends or better mean reversion opportunities. Filtering can reduce bad trades.
</context>

<research>
Before strategy testing, analyze ETH patterns by hour:
1. Calculate average volume by hour of day
2. Measure volatility (ATR%) by hour
3. Identify which hours have strongest trends vs ranging
4. Check win rate of basic strategies by hour
5. Determine if certain hours have higher false breakouts

Create a heatmap or table showing:
- Hour of day (0-23 UTC)
- Avg volume
- Avg ATR%
- Trend strength
- Strategy win rate (if you test a simple strategy)

Use this to identify:
- Best hours for trend following
- Best hours for mean reversion
- Hours to avoid entirely
</research>

<requirements>
Test session-based strategies:

1. **Session-Filtered Mean Reversion**
   - Take your best mean reversion approach from prompt 007 (if available) or create simple RSI strategy
   - Test trading ONLY during:
     - Asian session only
     - European session only
     - US session only
     - European + US (high volume)
     - Custom hours based on research findings
   - Compare profit/DD ratio with and without session filter

2. **Session-Filtered Trend Following**
   - Take your best trend approach from prompt 008 (if available) or create simple EMA pullback
   - Test trading ONLY during:
     - Each session separately
     - Session combinations
     - Peak volatility hours (based on research)
   - Compare profit/DD ratio with and without session filter

3. **Session-Specific Strategies**
   - Mean reversion during low-volatility sessions
   - Trend following during high-volatility sessions
   - Hybrid: switch strategy based on hour

4. **Avoid-Hours Strategy**
   - Identify worst performing hours
   - Test if simply avoiding them improves overall results
   - E.g., "Trade anytime except 21:00-23:00 UTC"

For each approach, test:
- Stop/target multiples optimized per session
- Leverage adjusted per session (higher in clearer sessions)
- Position sizing per session
</requirements>

<implementation>
Add hour-based filtering to backtest:

```python
def session_filter(timestamp, allowed_hours):
    """Check if trade should be taken based on hour"""
    hour = timestamp.hour
    return hour in allowed_hours

for i in range(250, len(df)):
    row = df.iloc[i]

    # Define allowed hours based on strategy
    allowed_hours = [13, 14, 15, 16, 17, 18, 19, 20]  # US session example

    if not in_position and session_filter(row['timestamp'], allowed_hours):
        signal = check_strategy_signal(row)
        if signal:
            enter_trade()
    else:
        check_exit_conditions(row)
```

Calculate metrics:
- Profit/DD ratio with session filter
- Profit/DD ratio without filter (baseline)
- Improvement percentage
- Trade frequency per session
</implementation>

<output>
Create file: `./trading/eth_session_trading_results.md`

Include:
1. **Hourly Analysis Heatmap/Table**
   - Volume, volatility, performance by hour
   - Visual representation if possible

2. **Session Comparison Table**
   - Each session tested
   - Profit/DD ratio
   - Trade count
   - Win rate
   - Best vs worst session highlighted

3. **Best Session-Based Strategy**
   - Exact hours to trade
   - Strategy type (mean reversion or trend)
   - All parameters
   - Expected return with recommended leverage
   - Comparison: filtered vs unfiltered performance

4. **Key Insights**
   - Which session is most profitable for ETH?
   - Does session filtering improve profit/DD ratio?
   - Is it worth the reduced trade frequency?
   - Recommended approach: session filter or 24/7?
</output>

<success_criteria>
- At least ONE session-based strategy with profit/DD ratio >= 4.0
- Clear data showing which hours are best/worst for trading ETH
- Quantified improvement (if any) from session filtering
- Recommendation on whether to use session filters or trade 24/7
</success_criteria>

<verification>
Before declaring complete:
1. Verify hour calculations are in UTC (not local time)
2. Check that trades during "allowed hours" are actually taken
3. Confirm session boundaries are correct (e.g., US session includes overlap with London)
4. Test that removing worst hours actually improves results
</verification>
