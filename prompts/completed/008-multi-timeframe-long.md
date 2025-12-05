<objective>
Test "Multi-Timeframe LONG" approach to achieve 3-5x Return/Drawdown ratio on FARTCOIN/USDT.

Add 5-minute uptrend confirmation to filter 1-minute LONG entries.

Goal: Achieve 3-5x R:R ratio through higher timeframe trend alignment (bullish version)
</objective>

<context>
SHORT Baseline: Multi-Timeframe V7
- Result: +10.45% return, -3.06% DD = 3.42x R:R
- 14 trades (filtered 6 from original 20)
- 50% win rate, 3.26 profit factor
- 5-min filter removed counter-trend whipsaws

Data: /workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv
</context>

<requirements>
Create new strategy file: `./strategies/multi-timeframe-long-v7.py`

Implementation:

1. **Resample 1-min data to 5-min**
   - Use pandas resample: df.resample('5T')
   - Calculate 5-min OHLCV candles
   - Calculate 5-min indicators:
     * 50-period SMA (on 5-min = 250 min = 4+ hours)
     * 14-period RSI (on 5-min)
     * 20-period ATR (on 5-min)

2. **5-Min Uptrend Filter**
   For each 1-min candle, check corresponding 5-min:
   - 5-min close > 5-min 50 SMA (uptrend)
   - 5-min RSI > 50 (bullish momentum)
   - Last 3 5-min candles showing higher highs (momentum continuing)

3. **Only Trade When Both Align**
   ```python
   # 1-min pattern detected (Explosive Bullish Breakout)
   if (1min_explosive_bullish_detected and
       5min_in_uptrend and
       5min_rsi_bullish and
       5min_momentum_up):
       # Enter LONG trade
   ```

4. **Conservative Entry Filters (Inverted)**
   - Body > 1.2%, Volume > 3x
   - RSI > 45, In 1-min uptrend
   - Clean candle (wicks < 35%)
   - Bullish candle (close > open)

5. **Conservative Risk Management**
   - Stop: 3x ATR below entry
   - Target: 12x ATR above entry (4:1 R:R)
   - Base risk: 1.0%
   - Trailing stops and partial exits

Expected Impact:
- Fewer trades (12-16 vs 20+) - filtered by 5-min uptrend
- Higher win rate (45-50%) - better trend alignment
- Lower drawdown (-3 to -4%) - fewer counter-trend entries
- Similar returns (+10-14%)
- R:R: 3-5x

Generate full backtest with:
- 5-min data resampling
- Alignment check logging
- Trade analysis showing which were filtered
</requirements>

<output>
Create file: `./strategies/multi-timeframe-long-v7.py`

Must output:
1. Code with 5-min resampling logic
2. `./strategies/multi-timeframe-long-trades.csv`
3. `./strategies/multi-timeframe-long-equity.csv`
4. Print:
   - Total 1-min bullish patterns detected
   - How many passed 5-min uptrend filter
   - Final metrics
   - Comparison to SHORT version (3.42x R:R)
</output>

<verification>
Verify:
- 5-min data resamples correctly
- Uptrend alignment logic works
- All trades are LONG direction
- Trades are subset (1-min filters + 5-min uptrend)
- Win rate comparable to SHORT version
- R:R ratio 3-5x range
</verification>

<success_criteria>
✅ R:R ratio: 3-5x (comparable to SHORT's 3.42x)
✅ Return: +10-15%
✅ Max DD: -3 to -4%
✅ Win rate: 45-55%
✅ Profit factor: 2.5-3.5
✅ Trades: 12-16
✅ 5-min filter removes counter-trend signals
✅ Code runs successfully
</success_criteria>
