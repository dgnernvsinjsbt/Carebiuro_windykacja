<objective>
Test "Multi-Timeframe Approach" to achieve 3-5x Return/Drawdown ratio on FARTCOIN/USDT.

Add 5-minute timeframe confirmation to filter out counter-trend 1-minute trades and reduce whipsaw.

Goal: Achieve 3-5x R:R ratio through higher timeframe trend alignment
</objective>

<context>
Base Strategy: Conservative config from V6
- Current: +11.41% return, -5.76% DD = 1.98x R:R

Problem: 1-minute patterns can trigger during 5-min uptrend reversals, causing false signals and drawdown.

Solution: Only trade 1-min breakdown when 5-min timeframe also shows downtrend.

Data: /workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv
</context>

<requirements>
Create new strategy file: `./strategies/multi-timeframe-v7.py`

Implementation:

1. **Resample 1-min data to 5-min**
   - Use pandas resample: df.resample('5T')
   - Calculate 5-min OHLCV candles
   - Calculate 5-min indicators:
     * 50-period SMA (on 5-min = 250 min = 4+ hours)
     * 14-period RSI (on 5-min)
     * 20-period ATR (on 5-min)

2. **5-Min Trend Filter**
   For each 1-min candle, check corresponding 5-min:
   - 5-min close < 5-min 50 SMA (downtrend)
   - 5-min RSI < 50 (bearish momentum)
   - Last 3 5-min candles showing lower lows (momentum continuing)

3. **Only Trade When Both Align**
   ```python
   # 1-min pattern detected (Explosive Bearish Breakdown)
   if (1min_explosive_bearish_detected and
       5min_in_downtrend and
       5min_rsi_bearish and
       5min_momentum_down):
       # Enter trade
   ```

4. **Keep Conservative Config Entry Filters**
   - Body > 1.2%, Volume > 3x
   - RSI < 55, In 1-min downtrend
   - Clean candle (wicks < 35%)

5. **Keep Conservative Risk Management**
   - Stop: 3x ATR
   - Target: 12x ATR (4:1 R:R)
   - Base risk: 1.0%
   - Trailing stops and partial exits

Expected Impact:
- Fewer trades (12-16 vs 20) - some filtered by 5-min
- Higher win rate (40-45% vs 35%) - better trend alignment
- Lower drawdown (-3 to -4% vs -5.76%) - fewer counter-trend entries
- Similar returns (+10-14%)
- R:R: 3-5x

Generate full backtest with:
- 5-min data resampling
- Alignment check logging
- Trade analysis showing which were filtered
</requirements>

<output>
Create file: `./strategies/multi-timeframe-v7.py`

Must output:
1. Code with 5-min resampling logic
2. `./strategies/multi-timeframe-trades.csv`
3. `./strategies/multi-timeframe-equity.csv`
4. Print:
   - Total 1-min patterns detected
   - How many passed 5-min filter
   - Final metrics
   - Comparison to Conservative
</output>

<verification>
Verify:
- 5-min data resamples correctly (check first 10 candles)
- Alignment logic works (manually verify 3 trades)
- Trades are subset of Conservative (all should pass 1-min filters)
- Win rate improves
- Drawdown reduces
- R:R ratio improves
</verification>

<success_criteria>
✅ R:R ratio: 3-5x (realistic improvement)
✅ Return: +10-15%
✅ Max DD: -3 to -4%
✅ Win rate: 40-48%
✅ Profit factor: 1.8-2.2
✅ Trades: 12-16
✅ 5-min filter removes 4-8 trades from Conservative's 20
✅ Code runs successfully
</success_criteria>
