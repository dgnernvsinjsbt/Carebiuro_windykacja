<objective>
Test "Trend + Distance 2% LONG" approach to achieve 8-12x Return/Drawdown ratio on FARTCOIN/USDT.

Use the WINNING configuration from V7 testing, inverted for LONG trades.

Goal: Replicate 8.88x R:R success with bullish breakouts
</objective>

<context>
SHORT Baseline: Trend + Distance 2%
- Result: +20.08% return, -2.26% DD = 8.88x R:R ⭐ WINNER
- 12 ultra-selective trades
- 58.3% win rate, 3.83 profit factor
- Secret: Strong trend + 2% distance from SMA

Key Insight: Simple beats complex
- Fixed 15x ATR TP (5:1 R:R) worked best
- Dynamic TP performed worse

Data: /workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv
</context>

<requirements>
Create new strategy file: `./strategies/trend-distance-long-v7.py`

Entry Filters (Inverted for LONGS):

1. **Explosive Bullish Breakout Pattern**
   - Body > 1.2%
   - Volume > 3x average
   - Bullish candle (close > open)
   - Clean structure (wicks < 35% of body)

2. **Strong Uptrend Filter** ⭐ CRITICAL
   - Price ABOVE 50 SMA AND 200 SMA
   - Both SMAs sloping upward (trend confirmation)
   - This is THE key filter that achieved 8.88x R:R

3. **2% Distance Filter** ⭐ CRITICAL
   - Price must be 2%+ ABOVE 50 SMA
   - Ensures we only trade strong momentum
   - Combined with #2, this cuts trades by 75%

4. **RSI Confirmation**
   - RSI > 48 (bullish but not overbought)
   - RSI < 75 (avoid extreme overbought)

Risk Management:
- Entry: Close of explosive candle
- Stop: 3x ATR below entry
- Target: 15x ATR above entry (5:1 R:R per trade)
- Base risk: 1.5%
- Max risk: 4.0%
- Trailing stops at 3R (BE), 5R (trail)
- Partial exits: 30% at 2R, 40% at 4R, 30% rides

Expected (matching SHORT):
- 10-15 trades total
- 55-65% win rate
- -2 to -3% max DD
- +18-25% return
- 8-12x R:R ratio

Generate full backtest with CSV outputs.
</requirements>

<output>
Create file: `./strategies/trend-distance-long-v7.py`

Must output:
1. Code file with LONG implementation
2. `./strategies/trend-distance-long-trades.csv`
3. `./strategies/trend-distance-long-equity.csv`
4. Print comprehensive metrics:
   - Total patterns detected
   - How many passed strong uptrend filter
   - How many passed 2% distance filter
   - Final 8-12x R:R comparison to SHORT (8.88x)
   - Trade-by-trade breakdown
</output>

<verification>
Verify:
- Strong uptrend filter (above 50 & 200 SMA) works
- 2% distance filter applied correctly
- Only 10-15 ultra-selective trades
- All trades are LONG direction
- Win rate > 50%
- Max DD < -3%
- R:R ratio 8-12x range (matching SHORT success)
</verification>

<success_criteria>
✅ R:R ratio: 8-12x (matching SHORT's 8.88x) ⭐ PRIMARY GOAL
✅ Return: +18-25%
✅ Max DD: -2 to -3%
✅ Win rate: 55-65%
✅ Profit factor: 3.5+
✅ Trades: 10-15 (ultra-selective like SHORT's 12)
✅ Strong trend + 2% distance filters applied
✅ Code runs successfully
</success_criteria>

<notes>
This is the most promising test since the SHORT version achieved 8.88x R:R.

If LONG version achieves similar results, combining BOTH directions with these filters could potentially achieve 10-15x R:R on the portfolio level!
</notes>
