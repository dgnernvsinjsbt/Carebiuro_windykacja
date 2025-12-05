<objective>
Test "Ultra-Selective LONG" approach to achieve 6-12x Return/Drawdown ratio on FARTCOIN/USDT.

Use the same ultra-strict filters as V7 SHORT version, but inverted for LONG trades.

Goal: Determine if explosive bullish breakouts are as profitable as bearish breakdowns
</objective>

<context>
SHORT Baseline: Ultra-Selective V7
- Result: +7.88% return, -1.31% DD = 6.01x R:R
- Only 6 trades over 30 days
- 50% win rate, 3.94 profit factor

V6 "Both Directions" showed LONGS were profitable:
- Longs: 24 trades, +$1,176
- Shorts: 29 trades, +$606
- Insight: FARTCOIN has strong upside moves!

Data: /workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv
</context>

<requirements>
Create new strategy file: `./strategies/ultra-selective-long-v7.py`

Ultra-Strict Entry Filters (Inverted for LONGS):

1. **Massive Bullish Move**
   - Body > 1.5% AND bullish (close > open)
   - Must be largest candle in last 20 periods

2. **Institutional Volume**
   - Volume > 3.5x average
   - Volume must be in top 10% of all candles

3. **Multi-Indicator Confluence**
   - RSI > 52 (bullish momentum, not overbought)
   - Above 50 SMA AND 200 SMA (strong uptrend)
   - ATR expanding (current > 50-period avg)

4. **Clean Bullish Candle**
   - Upper wick < 25% of body
   - Lower wick < 25% of body
   - Close in top 35% of candle range

Risk Management:
- Entry: Close of explosive bullish candle
- Stop: 3.5x ATR below entry
- Target: 25x ATR above entry (7.1:1 R:R per trade)
- Base risk: 0.8%
- Max risk: 2.0% (on 2-win streak)
- Trailing stops at 3R (BE), 5R (2R), 8R (4R)

Expected:
- 5-10 trades total
- 50-60% win rate
- -1 to -2% max DD
- +8-15% return
- 6-12x R:R ratio

Generate full backtest with CSV outputs.
</requirements>

<output>
Create file: `./strategies/ultra-selective-long-v7.py`

Must output:
1. Code file with LONG implementation
2. `./strategies/ultra-selective-long-trades.csv`
3. `./strategies/ultra-selective-long-equity.csv`
4. Print metrics and comparison to SHORT version

Show:
- How many explosive bullish patterns found
- Trade-by-trade results
- R:R ratio comparison to SHORT (6.01x baseline)
</output>

<verification>
Verify:
- Only 5-10 trades generated (ultra-selective!)
- All trades are LONG direction
- Win rate > 50%
- Max DD < -3%
- Each trade meets ALL 4 filter criteria
- R:R ratio comparable to SHORT version
</verification>

<success_criteria>
✅ R:R ratio: 5-12x (comparable to SHORT's 6.01x)
✅ Return: +8-15%
✅ Max DD: -1 to -3%
✅ Win rate: 50-65%
✅ Profit factor: 2.5+
✅ Trades: 5-10 (ultra-selective)
✅ Code runs successfully
</success_criteria>
