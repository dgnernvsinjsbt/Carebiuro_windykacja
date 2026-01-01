<objective>
Test "Ultra-Selective Approach" to achieve 6-12x Return/Drawdown ratio on FARTCOIN/USDT.

Use extremely strict filters to get only 5-10 highest-quality trades with 60-70% win rate and minimal drawdown.

Goal: Achieve 6-12x R:R ratio through quality over quantity
</objective>

<context>
Base Strategy: Conservative config from V6
- Current: +11.41% return, -5.76% DD = 1.98x R:R, 20 trades, 35% WR

Data: /workspaces/Carebiuro_windykacja/fartcoin_usdt_1m_lbank.csv
</context>

<requirements>
Create new strategy file: `./strategies/ultra-selective-v7.py`

Ultra-Strict Entry Filters:

1. **Massive Move Requirement**
   - Body > 2.0% (vs 1.2%) - only huge candles
   - Must be largest candle in last 50 periods

2. **Institutional Volume**
   - Volume > 5.0x average (vs 3.0x)
   - Volume must be in top 5% of all candles

3. **At Key Support Level**
   - Identify swing lows (lowest low in 30-period window)
   - Price must be within 1% of swing low
   - This ensures breakdown happens at significant level

4. **Confirmation Candle Required**
   - Wait for next candle after pattern detected
   - Next candle must also be bearish with vol > 2x

5. **Multi-Indicator Confluence**
   - RSI < 45 (more bearish than Conservative's 55)
   - Below 50 SMA AND 200 SMA (strong downtrend)
   - ATR must be expanding (current > 50-period avg)

6. **Clean Candle Structure**
   - Upper wick < 20% of body (vs 35%)
   - Lower wick < 20% of body
   - Close in bottom 25% of candle range

Risk Management:
- Stop: 1.5x ATR (very tight vs 3x)
- Target: 20x ATR (13:1 R:R per trade!)
- Base risk: 0.5% (conservative)
- Max risk: 1.5% (on 3-win streak)
- No time stop if profitable (let winners run)
- Trailing stop at 5R, 8R, 12R

Expected:
- 5-10 trades total
- 60-70% win rate
- -1 to -2% max DD
- +8-15% return

Generate full backtest with CSV outputs.
</requirements>

<output>
Create file: `./strategies/ultra-selective-v7.py`

Must output:
1. Code file with implementation
2. `./strategies/ultra-selective-trades.csv`
3. `./strategies/ultra-selective-equity.csv`
4. Print metrics and comparison to Conservative
</output>

<verification>
Verify:
- Only 5-10 trades generated (very selective!)
- Win rate > 50%
- Max DD < -3%
- Each trade meets ALL 6 filter criteria
- R:R ratio significantly better than 2x
</verification>

<success_criteria>
✅ R:R ratio: 6-12x (stretch goal!)
✅ Return: +8-15%
✅ Max DD: -1 to -2%
✅ Win rate: 55-70%
✅ Profit factor: 2.5+
✅ Trades: 5-10 (ultra-selective)
✅ Code runs successfully
</success_criteria>
