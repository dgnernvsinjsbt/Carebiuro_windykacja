<objective>
Test "Combination Approach" to achieve 5-8x Return/Drawdown ratio on FARTCOIN/USDT.

Implement 3 key improvements to the Conservative config:
1. Confirmation candle requirement
2. Support/Resistance entry timing with tighter stops
3. Dynamic TP based on volatility expansion

Goal: Achieve 5-8x R:R ratio (vs current 2x)
</objective>

<context>
Base Strategy: Conservative config from V6
- Current: +11.41% return, -5.76% DD = 1.98x R:R
- Entry: Explosive Bearish Breakdown (body>1.2%, vol>3x)
- Stop: 3x ATR, Target: 12x ATR (4:1 R:R per trade)

Data: /workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv
</context>

<requirements>
Create new strategy file: `./strategies/combo-approach-v7.py`

Implement these 3 enhancements:

1. **Confirmation Candle Requirement**
   - Detect Explosive Bearish pattern on candle N
   - Wait for candle N+1
   - Only enter if candle N+1:
     * Also bearish (close < open)
     * Continues downward (close < previous close)
     * Volume still elevated (> 1.5x average)
   - This filters false breakdowns

2. **Support/Resistance Entry Timing**
   - Identify swing lows (lowest low in 20-period window)
   - Calculate support level = most recent swing low
   - Only enter breakdown if price is within 2% of support
   - Use TIGHTER stop: 2x ATR (vs 3x ATR)
   - This improves per-trade R:R from 4:1 to 6:1

3. **Dynamic TP Based on Volatility**
   - Calculate ATR expansion: current ATR vs 50-period ATR average
   - If ATR > 1.2x average (volatility expanding):
     * Use wider target: 20x ATR (10:1 R:R)
     * Remove time stop (let it run)
   - If ATR normal:
     * Use standard target: 12x ATR (6:1 R:R)
     * Keep 24h time stop
   - This captures explosive moves fully

Keep from Conservative config:
- Body > 1.2%, Volume > 3x
- RSI < 55, In downtrend
- SHORT-only (no longs)
- Base risk: 1.0%, Max risk: 3.0%
- Trailing stops at 3R and 5R
- Partial exits: 30% at 2R, 40% at 4R

Generate backtest with:
- All trades logged to CSV
- Performance metrics
- Comparison to Conservative baseline
</requirements>

<output>
Create file: `./strategies/combo-approach-v7.py`

Must output:
1. Code file with full implementation
2. `./strategies/combo-approach-trades.csv` - trade log
3. `./strategies/combo-approach-equity.csv` - equity curve
4. Print final metrics:
   - Total return %
   - Max drawdown %
   - R:R ratio
   - Win rate
   - Profit factor
   - Total trades
</output>

<verification>
Verify:
- Confirmation candle logic works (check first 5 trades manually)
- Support levels calculated correctly
- Dynamic TP triggers properly in high vol
- Tighter stops (2x ATR) applied
- R:R ratio improves over Conservative (1.98x baseline)
- Code runs without errors
</verification>

<success_criteria>
✅ R:R ratio: 4-8x (target: 5-8x)
✅ Return: +12-20%
✅ Max DD: -2 to -4%
✅ Win rate: 40-50%
✅ Profit factor: 1.8+
✅ Trades: 10-18
✅ Code executes successfully
</success_criteria>
