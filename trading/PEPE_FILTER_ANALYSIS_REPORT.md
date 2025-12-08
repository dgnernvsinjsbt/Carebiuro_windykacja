# PEPE Strategy Filter Analysis Report

**Date:** December 2025
**Strategy:** RSI ≤ 40 + BB Lower Touch (SL: 1.5x ATR, TP: 2.0x ATR)
**Fees:** 0.10% (market orders)

---

## 📊 BASELINE PERFORMANCE

| Metric | Value |
|--------|-------|
| **Total Trades** | 919 |
| **Win Rate** | 60.9% |
| **Total Return** | +11.20% |
| **Max Drawdown** | -14.11% |
| **Strategy R:R** | 0.79 |

---

## 🎯 BEST FILTER DISCOVERED

### **Filter: BB Width > 0.82% (High Volatility Only)**

| Metric | Baseline | With Filter | Change |
|--------|----------|-------------|--------|
| Trades | 919 | 459 | -50% |
| Win Rate | 60.9% | 59.5% | -1.4% |
| **Return** | **+11.20%** | **+16.80%** | **+50%** |
| **Max DD** | **-14.11%** | **-9.29%** | **-34%** |
| **Strategy R:R** | **0.79** | **1.81** | **+129%** |

### Why It Works

Mean reversion works BEST during **volatile conditions** when:
- Price swings are larger → bigger bounces from BB lower
- ATR is higher → wider TP targets catch bigger moves
- Lower volatility periods → chop/consolidation → more SL hits

---

## 📉 WINNERS vs LOSERS ANALYSIS

### Key Differences (all small - strategy is already well-tuned)

| Feature | Winners | Losers | Difference |
|---------|---------|--------|------------|
| **Hold Time** | 5.8 bars | 7.3 bars | Winners exit faster |
| Entry RSI | 29.9 | 29.7 | ~Same |
| Entry BB Distance | -0.092% | -0.101% | ~Same |
| BB Width | 0.95% | 0.99% | ~Same |
| Volume Ratio | 1.77x | 1.94x | Losers had MORE volume |
| Distance from SMA50 | -0.63% | -0.70% | Losers further below |

### Exit Reason Distribution

**Winners:**
- TP: 100% (all winners hit take profit)

**Losers:**
- SL: 99.3% (almost all losers hit stop loss)
- TP: 0.7% (a few TPs were still losers due to fees)

---

## ❌ FILTERS THAT FAILED

### 1. **15-min Uptrend Filter**
- Result: **ZERO TRADES**
- Reason: Mean reversion REQUIRES downtrend/consolidation
- Lesson: Don't filter for uptrend in a mean reversion strategy

### 2. **Deep Oversold (RSI < 35)**
- Trades: 621 (cuts 32%)
- Return: +5.69% (worse than baseline +11.20%)
- Lesson: RSI ≤ 40 is already optimal, going deeper hurts

### 3. **Low Volatility (BB Width < 0.82%)**
- Trades: 459
- Return: **-4.37%** (LOSES MONEY!)
- Lesson: Low volatility = chop = SL hits

### 4. **Volume Confirmation (>1.2x)**
- Trades: 456
- Return: **-7.93%** (LOSES MONEY!)
- Lesson: High volume on BB lower touch = panic selling → continues down

---

## 💡 KEY INSIGHTS

### 1. **Volatility is the Edge**
- The strategy makes money by catching bounces
- Bounces are BIGGER when volatility is HIGH
- Low volatility = small moves = fees eat profit

### 2. **Winners Exit Fast**
- Average winning trade: 5.8 bars (5.8 minutes)
- Average losing trade: 7.3 bars (7.3 minutes)
- Mean reversion works quickly or not at all

### 3. **Volume is a FALSE signal**
- Higher volume on entry = WORSE performance
- Volume spike at BB lower = capitulation, not bounce setup
- Avoid volume filters for mean reversion

### 4. **Hour of Day: Minimal Impact**
- Winners and losers fairly evenly distributed across hours
- No clear "golden hour" for this strategy
- Time filters don't add value

---

## 📈 FILTER TEST RESULTS (Full Table)

Ranked by Strategy R:R:

| Filter | Trades | Win Rate | Return | Max DD | R:R |
|--------|--------|----------|--------|--------|-----|
| **BB Width > 0.82%** | **459** | **59.5%** | **+16.80%** | **-9.29%** | **1.81** |
| Baseline | 919 | 60.9% | +11.20% | -14.11% | 0.79 |
| Very Close to BB | 919 | 60.9% | +11.20% | -14.11% | 0.79 |
| Within 5% SMA50 | 918 | 60.9% | +9.07% | -15.76% | 0.58 |
| RSI < 35 | 621 | 61.4% | +5.69% | -12.33% | 0.46 |
| Avoid Hours 0-6 | 660 | 59.5% | +3.60% | -12.20% | 0.29 |
| BB Width < 0.82% | 459 | 62.5% | -4.37% | -13.29% | -0.33 |
| Volume > 1.2x | 456 | 55.3% | -7.93% | -15.91% | -0.50 |
| 15-min Uptrend | 0 | - | - | - | - |

---

## ✅ RECOMMENDED STRATEGY

### **Optimized PEPE Mean Reversion Strategy**

**Entry Conditions (ALL must be true):**
1. RSI(14) ≤ 40
2. Close ≤ BB(20,2) Lower Band
3. **BB Width > 0.82%** ← NEW FILTER

**Exits:**
- Stop Loss: 1.5x ATR(14) below entry
- Take Profit: 2.0x ATR(14) above entry

**Fees:** 0.10% round-trip (market orders)

**Expected Performance:**
- Trades: ~459 per month (30 days of data)
- Win Rate: 59.5%
- Return: +16.80%
- Max Drawdown: -9.29%
- Strategy R:R: 1.81

---

## 🚨 WARNINGS

1. **Profit Concentration Risk**
   - Need to check if few trades drive most profits
   - If top 10 trades = >50% of profit → fragile strategy

2. **Overfitting Risk**
   - BB Width threshold (0.82%) is optimized on 30 days
   - May change with different market regimes
   - Monitor live performance

3. **Fees Impact**
   - With 459 trades/month, fees = ~46% round-trip
   - Strategy is fee-sensitive
   - Consider limit orders to reduce fees

---

## 📁 FILES GENERATED

- `results/PEPE_filter_test_results.csv` - All filter results
- `results/PEPE_all_trades_with_features.csv` - All 919 trades with entry features
- `results/PEPE_filter_comparison.png` - Visual comparison chart

---

## 🎓 LESSONS LEARNED

1. **Mean reversion ≠ Trend following**
   - Don't use uptrend filters on mean reversion strategies
   - They work in OPPOSITE market conditions

2. **Volatility filters work**
   - High volatility = bigger swings = better mean reversion
   - Low volatility = chop = death by a thousand cuts

3. **Intuitive filters can fail**
   - Volume confirmation HURT performance
   - More indicators ≠ better results
   - Sometimes simpler is better

4. **One filter is enough**
   - BB Width filter alone gives 1.81 R:R
   - Combining filters killed all trades
   - Don't over-engineer

---

**Next Steps:**
1. Test BB Width filter on other coins (DOGE, MOODENG)
2. Analyze profit concentration in filtered trades
3. Test limit orders with -0.15% offset
4. Forward test on fresh data
