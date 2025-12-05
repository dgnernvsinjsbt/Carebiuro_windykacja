<objective>
Test "Combo Approach LONG" to achieve 4-6x Return/Drawdown ratio on FARTCOIN/USDT.

Implement 3 key improvements for LONG trades:
1. Confirmation candle requirement
2. Resistance breakout entry timing with tighter stops
3. Dynamic TP based on volatility expansion

Goal: Achieve 4-6x R:R ratio (vs SHORT's 2.45x)
</objective>

<context>
SHORT Baseline: Combo Approach V7
- Result: +8.71% return, -3.55% DD = 2.45x R:R
- 16 trades, 37.5% win rate, 1.89 profit factor
- Implemented confirmation + S/R + dynamic TP

Data: /workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv
</context>

<requirements>
Create new strategy file: `./strategies/combo-long-v7.py`

Implement these 3 enhancements (inverted for LONGS):

1. **Confirmation Candle Requirement**
   - Detect Explosive Bullish pattern on candle N
   - Wait for candle N+1
   - Only enter if candle N+1:
     * Also bullish (close > open)
     * Continues upward (close > previous close)
     * Volume still elevated (> 1.5x average)
   - This filters false breakouts

2. **Resistance Breakout Entry Timing**
   - Identify swing highs (highest high in 20-period window)
   - Calculate resistance level = most recent swing high
   - Only enter breakout if price is within 2% of resistance
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
- RSI > 45, In uptrend
- LONG-only
- Base risk: 1.0%, Max risk: 3.0%
- Trailing stops at 3R and 5R
- Partial exits: 30% at 2R, 40% at 4R

Generate backtest with:
- All trades logged to CSV
- Performance metrics
- Comparison to SHORT baseline
</requirements>

<output>
Create file: `./strategies/combo-long-v7.py`

Must output:
1. Code file with full implementation
2. `./strategies/combo-long-trades.csv` - trade log
3. `./strategies/combo-long-equity.csv` - equity curve
4. Print final metrics:
   - Total return %
   - Max drawdown %
   - R:R ratio
   - Win rate
   - Profit factor
   - Total trades
   - Comparison to SHORT (2.45x R:R)
</output>

<verification>
Verify:
- Confirmation candle logic works
- Resistance levels calculated correctly
- Dynamic TP triggers properly in high vol
- Tighter stops (2x ATR) applied
- R:R ratio improves over SHORT version
- Code runs without errors
</verification>

<success_criteria>
✅ R:R ratio: 3-6x (target improvement over SHORT's 2.45x)
✅ Return: +10-18%
✅ Max DD: -2 to -4%
✅ Win rate: 40-50%
✅ Profit factor: 2.0+
✅ Trades: 10-16
✅ Code executes successfully
</success_criteria>
