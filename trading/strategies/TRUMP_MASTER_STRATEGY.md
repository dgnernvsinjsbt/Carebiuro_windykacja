# TRUMP Master Trading Strategy
**Strategy Name:** Mean Reversion Scalper with Trend Filter
**Strategy Type:** Hybrid (Primary: Mean Reversion, Secondary: Trend Following)
**Timeframe:** 1-minute
**Designed:** 2025-12-07

---

## EXECUTIVE SUMMARY

TRUMP is an ultra-low volatility coin (0.12% avg candle range) that spends 40% of time in mean-reverting regime and 45% trending. The optimal strategy exploits RSI extremes (the strongest statistical edge) while filtering out choppy periods. This is a SCALPING strategy - quick in, quick out.

**Target Performance:**
- Win Rate: 52-55%
- Average R:R: 1.2-1.5x
- Max Drawdown: <15%
- Trades per day: 5-15

---

## STEP 1: DIRECTIONAL BIAS

**BIDIRECTIONAL STRATEGY**

**Long Bias Justification:**
- RSI < 30 shows strongest edge (+0.0144% avg return, 55% win rate)
- 5 consecutive red candles → +0.0052% avg bounce (1,836 occurrences)
- Win rate balanced: Long 46.1% vs Short 45.9% in US session

**Short Bias Justification:**
- RSI > 70 shows -0.0214% avg return (52.8% win rate)
- BB upper touches mean revert only 10.8% (weak edge)

**Decision: BIDIRECTIONAL with LONG preference during oversold conditions**

---

## STEP 2: STRATEGY ARCHETYPE

**PRIMARY: MEAN REVERSION (70% of trades)**
**SECONDARY: TREND FOLLOWING (30% of trades)**

**Rationale:**
1. TRUMP spends 39.8% in mean-reverting regime (dominant behavior)
2. RSI extremes provide the strongest statistical edge
3. Ultra-low volatility (0.12% candles) favors quick reversions
4. Trending periods exist (45.1%) but are intermittent
5. Pattern analysis shows weak continuation signals

**Hybrid Approach:**
- Trade mean reversion during range-bound periods (RSI extremes)
- Switch to trend-following during trending regimes (price > SMA200 + volume surge)

---

## STEP 3: ENTRY SIGNAL DESIGN

### LONG ENTRY (Mean Reversion Primary)

**Primary Signal:**
- RSI(14) < 30 (oversold condition - strongest statistical edge)
- OR 4+ consecutive red candles (sequential pattern edge)

**Confirmation Filters:**
1. Price near lower Bollinger Band (within 20% of distance to BB lower)
2. No large lower wick on current candle (wick < 50% of range - avoid false bottoms)
3. Volume > 0.8x average (sufficient liquidity)
4. Not in EXPLOSIVE regime (ATR < 3x average ATR)

**Session Filter:**
- ACTIVE: US session (14:00-21:00 UTC) - highest volume/volatility
- ACTIVE: Asia session hours 2:00-4:00 (best hourly returns)
- AVOID: Hour 23:00 (worst hourly return -0.0035%)

**Regime Filter:**
- BEST: MEAN_REVERTING or CHOPPY regimes
- ACCEPTABLE: TRENDING_DOWN (for bounce trades)
- AVOID: Strong TRENDING_UP (no RSI oversold opportunities)

**Avoid Conditions:**
- Price > SMA(200) by more than 2% (extended uptrend)
- ATR > 0.35% (excessive volatility - 3x normal)
- Hour 23:00 UTC
- First 5 minutes after major volatility spike (>2% body candle)

---

### SHORT ENTRY (Mean Reversion Secondary)

**Primary Signal:**
- RSI(14) > 70 (overbought condition)
- Price touches or exceeds upper Bollinger Band

**Confirmation Filters:**
1. No large upper wick on current candle (wick < 50% of range)
2. Volume > 0.8x average
3. Price above SMA(50) by at least 1% (in uptrend to fade)

**Session Filter:**
- Same as long entries (US session primary)

**Regime Filter:**
- BEST: MEAN_REVERTING
- ACCEPTABLE: TRENDING_UP (for pullback trades)
- AVOID: TRENDING_DOWN

**Avoid Conditions:**
- Price < SMA(200) by more than 2%
- Strong trending momentum (5+ consecutive green candles)
- ATR > 0.35%

---

### TREND ENTRY (Opportunistic)

**Long Trend Signal:**
- Price > SMA(50) AND SMA(50) > SMA(200) (uptrend confirmed)
- Strong green candle close (body > 0.15%, top 25% of candles)
- Volume > 2x average (breakout confirmation)
- RSI between 50-65 (momentum but not overbought)

**Short Trend Signal:**
- Price < SMA(50) AND SMA(50) < SMA(200)
- Strong red candle close (body > 0.15%)
- Volume > 2x average
- RSI between 35-50

---

## STEP 4: EXIT STRATEGY DESIGN

### MEAN REVERSION EXITS

**Stop Loss:**
- **Long:** 2x ATR below entry (approximately 0.24%)
- **Short:** 2x ATR above entry
- **Rationale:** Ultra-tight stops for low-volatility coin, ATR-based adapts to conditions

**Take Profit:**
- **Long:** 1.5x ATR above entry (approximately 0.18%) - Target R:R = 0.75x
- **Alternative:** Exit when RSI crosses back above 50 (momentum shift)
- **Short:** 1.5x ATR below entry OR RSI crosses below 50

**Time-Based Exit:**
- Exit after 30 candles (30 minutes) if neither TP nor SL hit
- Rationale: Mean reversion should happen quickly or trade thesis invalid

**Target R:R Ratio:** 0.75x (Win rate compensates - targeting 55%)

---

### TREND FOLLOWING EXITS

**Stop Loss:**
- **Long:** 3x ATR below entry (0.36%)
- **Short:** 3x ATR above entry

**Take Profit:**
- **Long:** 5x ATR above entry (0.60%) - Target R:R = 1.67x
- **Short:** 5x ATR below entry
- **Trailing Stop:** Activate after 2x ATR profit, trail at 1x ATR

**Time-Based Exit:**
- Exit after 60 candles (1 hour) if neither TP nor SL hit

**Target R:R Ratio:** 1.67x (Lower win rate expected - targeting 45%)

---

## STEP 5: POSITION SIZING STRATEGY

**Base Position Size:** 2% of capital per trade

**Maximum Concurrent Positions:** 3
- Allows diversification across mean reversion + trend setups
- Total max exposure: 6% of capital

**Scaling Rules:**

**Scale UP (increase to 3% per trade):**
- Win rate > 55% over last 20 trades
- Current drawdown < 5%
- Trading in US session with high volume

**Scale DOWN (decrease to 1% per trade):**
- Win rate < 48% over last 20 trades
- Current drawdown > 10%
- Trading outside optimal sessions
- ATR > 0.30% (elevated volatility)

**No Pyramiding:**
- Do NOT add to winning positions (low volatility = small moves)
- Take profits and re-enter if signal repeats

---

## STEP 6: SESSION AND TIME FILTERS

### ACTIVE TRADING WINDOWS

**Primary (80% of trades):**
- **US Session:** 14:00-21:00 UTC
  - Highest volume (1.47x average)
  - Best volatility (0.1479% ATR)
  - Best avg return (-0.0001% - least negative)

**Secondary (20% of trades):**
- **Asia Hours 2:00-4:00 UTC**
  - Hour 2:00: +0.0031% avg return (best single hour)
  - Hour 4:00: +0.0016% avg return

### AVOID WINDOWS

**Hard Avoid:**
- **Hour 23:00 UTC** - Worst hourly return (-0.0035%)
- **Hour 3:00 UTC** - Second worst (-0.0032%)
- **Overnight session overall** (21:00-00:00) - Worst session (-0.0012% avg)

**Soft Avoid (reduce position size):**
- **Europe session** (08:00-14:00) - Lower volume (0.82x), negative returns
- **Weekend low-volume hours** - Use volume filter (require >1.0x avg volume)

### SPECIAL TIMING RULES

1. **Post-Volatility Cooldown:** After any candle with >1% body, wait 5 candles before entering
2. **Session Transition:** Avoid first 10 minutes of US session (14:00-14:10) - wait for liquidity
3. **Volume Gate:** If current hour volume < 0.5x average, skip all entries (insufficient liquidity)

---

## RISK MANAGEMENT RULES

### Daily Limits
- **Max Daily Loss:** -4% of capital (STOP TRADING for the day)
- **Max Daily Trades:** 20 (prevent overtrading)
- **Daily Profit Target:** +3% of capital (consider reducing size or stopping)

### Trade Limits
- **Max Loss Per Trade:** 0.5% of capital (2.5% size * 20% stop = 0.5%)
- **Max Open Trades:** 3 simultaneous
- **Max Trades in Same Direction:** 2 (if 2 longs open, can't open another long)

### Drawdown Protocol
- **-5% Drawdown:** Reduce position size to 1.5%
- **-10% Drawdown:** Reduce position size to 1%, max 2 open trades
- **-15% Drawdown:** STOP TRADING, review strategy

---

## REGIME DETECTION

**TRENDING_UP:**
- Price > SMA(200)
- SMA(50) > SMA(200)
- ATR > 0.13% (above average)
- → Trade trend entries (long), reduce mean reversion shorts

**TRENDING_DOWN:**
- Price < SMA(200)
- SMA(50) < SMA(200)
- ATR > 0.13%
- → Trade trend entries (short), reduce mean reversion longs

**MEAN_REVERTING:**
- Price oscillating around SMA(200) (within ±1%)
- ATR < 0.13%
- BB width contracted
- → Focus on RSI extreme mean reversion trades

**CHOPPY:**
- ATR < 0.10% (very low volatility)
- No clear SMA alignment
- → Reduce size or avoid trading

**EXPLOSIVE:**
- ATR > 0.35% (3x normal)
- Recent candle with >1% body
- → AVOID all entries, wait for normalization

---

## STRATEGY SUMMARY

| Parameter | Value |
|-----------|-------|
| **Strategy Type** | Hybrid: Mean Reversion (70%) + Trend (30%) |
| **Primary Edge** | RSI < 30 oversold bounces |
| **Base Position Size** | 2% of capital |
| **Max Concurrent Trades** | 3 |
| **Mean Reversion R:R** | 0.75x (SL: 2xATR, TP: 1.5xATR) |
| **Trend Following R:R** | 1.67x (SL: 3xATR, TP: 5xATR) |
| **Best Trading Time** | US Session 14:00-21:00 UTC |
| **Avoid Time** | Hour 23:00, Overnight session |
| **Target Win Rate** | 53-55% overall |
| **Max Daily Loss** | -4% |
| **Max Drawdown** | -15% (STOP) |

---

## EXPECTED PERFORMANCE

**Conservative Estimate:**
- Win Rate: 53%
- Avg Win: +0.18% (+1.5x ATR)
- Avg Loss: -0.24% (-2x ATR)
- Profit Factor: (0.53 * 0.18) / (0.47 * 0.24) = 0.85x

**With Position Sizing (2% per trade):**
- Avg Win: +0.36% of capital
- Avg Loss: -0.48% of capital
- Expected Value: (0.53 * 0.36) - (0.47 * 0.48) = -0.035% per trade

**This suggests we need to optimize for HIGHER win rate or BETTER R:R!**

**Optimistic Estimate (with filters working):**
- Win Rate: 55% (matching RSI < 30 edge)
- Avg Win: +0.20% (better exits)
- Avg Loss: -0.22% (tighter stops)
- Profit Factor: (0.55 * 0.20) / (0.45 * 0.22) = 1.11x
- Expected Value: (0.55 * 0.40) - (0.45 * 0.44) = +0.022% per trade

**With 10 trades/day:** +0.22% daily, +66% monthly

---

## BACKTEST VALIDATION CHECKLIST

- [ ] Overfitting check: <8 entry conditions (PASS - we have 5 main filters)
- [ ] Robustness check: Test SL/TP variations ±20%
- [ ] Drawdown check: Max DD <25% (target <15%)
- [ ] Execution check: >100 signals in dataset (43K candles should yield 200+)
- [ ] Fee impact: Test with 0.05% maker, 0.10% taker fees
- [ ] Slippage impact: Add 0.02% slippage on entries/exits

---

## NEXT STEPS

1. Code the strategy in Python
2. Run backtest on full 30-day dataset
3. Analyze trade distribution by session/regime
4. Optimize SL/TP ratios
5. Generate equity curve and drawdown analysis
6. Validate against overfitting
7. Paper trade for 3-5 days before live deployment

---

**Strategy designed by Master Trader analysis - Custom-tailored for TRUMP's ultra-low volatility, mean-reverting personality.**
