# TRUMP Pattern Discovery Analysis
**Analysis Date:** 2025-12-07 16:03:39
**Data Period:** 2025-11-07 to 2025-12-07
**Total Candles:** 43,202 (1-minute timeframe)
**Days of Data:** 30

---

## Executive Summary

### Top 5 Most Significant Patterns Discovered


**1. Best Trading Session:** US session shows avg return of -0.0001% with 0.1479% ATR

**2. Strongest Sequential Pattern:** '5 consecutive red' followed by 0.0052% avg move (1836 occurrences)

**3. Dominant Market Regime:** MEAN_REVERTING (39.8% of time)

**4. Strongest Statistical Edge:** RSI < 30 shows 0.0144% avg return

**5. Key Behavioral Trait:** 0.01% of candles are explosive (>2% body), indicating moderate volatility character


---

## 1. Session Analysis

Trading sessions analyzed (UTC time):
- **Asia:** 00:00-08:00 (Tokyo/Singapore/Hong Kong)
- **Europe:** 08:00-14:00 (London through US pre-market)
- **US:** 14:00-21:00 (NYSE/NASDAQ active)
- **Overnight:** 21:00-00:00 (low liquidity transition)

### Session Performance Comparison

| Session | Avg Return | Volatility (ATR) | Volume vs 24h | Long Win% | Short Win% | Best Hour | Worst Hour |
|---------|------------|------------------|---------------|-----------|------------|-----------|------------|
| Asia       |  -0.0004% |       0.1097% |       0.78x |    45.2% |     44.7% | 02:00 (0.003%) | 03:00 (-0.003%) |
| Europe     |  -0.0011% |       0.1054% |       0.82x |    44.4% |     46.0% | 12:00 (0.001%) | 11:00 (-0.002%) |
| US         |  -0.0001% |       0.1479% |       1.47x |    46.1% |     45.9% | 19:00 (0.003%) | 20:00 (-0.002%) |
| Overnight  |  -0.0012% |       0.1025% |       0.86x |    44.7% |     44.4% | 22:00 (0.000%) | 23:00 (-0.003%) |


### Session Insights:
- **Most Profitable Session:** US with -0.0001% avg return
- **Most Volatile Session:** US with 0.1479% ATR
- **Highest Volume Session:** US at 1.47x average volume

---

## 2. Sequential Pattern Catalog

**"When X happens → Then Y follows"** patterns with statistical backing:


### Pattern: 3 consecutive green
- **Occurrences:** 3,725
- **Next candle avg move:** -0.0031%
- **Reversal rate:** 48.8%
- **Continuation rate:** 51.2%


### Pattern: 3 consecutive red
- **Occurrences:** 6,747
- **Next candle avg move:** 0.0027%
- **Reversal rate:** 47.9%
- **Continuation rate:** 52.1%


### Pattern: 4 consecutive green
- **Occurrences:** 1,617
- **Next candle avg move:** -0.0023%
- **Reversal rate:** 49.0%
- **Continuation rate:** 51.0%


### Pattern: 4 consecutive red
- **Occurrences:** 3,514
- **Next candle avg move:** 0.0038%
- **Reversal rate:** 47.8%
- **Continuation rate:** 52.2%


### Pattern: 5 consecutive green
- **Occurrences:** 702
- **Next candle avg move:** -0.0078%
- **Reversal rate:** 49.9%
- **Continuation rate:** 50.1%


### Pattern: 5 consecutive red
- **Occurrences:** 1,836
- **Next candle avg move:** 0.0052%
- **Reversal rate:** 48.4%
- **Continuation rate:** 51.6%


### Pattern: Large upper wick (rejection)
- **Occurrences:** 5,718
- **Next candle avg move:** 0.0015%
- **Win rate:** 43.2%


### Pattern: Large lower wick (support)
- **Occurrences:** 5,795
- **Next candle avg move:** -0.0016%
- **Win rate:** 44.2%


### Pattern: Volume spike (>3x avg)
- **Occurrences:** 2,741
- **Continuation rate:** 48.0%


### Pattern: BB upper touch
- **Occurrences:** 2,198
- **Mean reversion rate:** 10.8%


### Pattern: BB lower touch
- **Occurrences:** 2,318
- **Mean reversion rate:** 8.4%



---

## 3. Regime Analysis

Market regime classification based on price action and indicators:

### Time Spent in Each Regime

- **TRENDING_UP:** 20.86% of time (9,011 candles)
  - Avg return: 0.0161%
  - Avg volatility: 0.1293%

- **TRENDING_DOWN:** 24.23% of time (10,467 candles)
  - Avg return: -0.0165%
  - Avg volatility: 0.1254%

- **MEAN_REVERTING:** 39.83% of time (17,206 candles)
  - Avg return: -0.0004%
  - Avg volatility: 0.1105%

- **EXPLOSIVE:** 0.01% of time (4 candles)
  - Avg return: -1.4801%
  - Avg volatility: 0.7970%

- **CHOPPY:** 15.08% of time (6,514 candles)
  - Avg return: 0.0024%
  - Avg volatility: 0.1155%



### Regime Insights:

**Primary Character:** TRENDING

- Trending behavior: 45.1% of time
- Mean-reverting behavior: 39.8% of time
- Choppy behavior: 15.1% of time

**Strategy Suitability:**
- **BEST:** Trend-following strategies (breakout, momentum)
- **GOOD:** Volatility expansion plays
- **AVOID:** Pure mean-reversion during strong trends


---

## 4. Statistical Edges

Ranked list of statistically significant patterns:


### Day of Week: Saturday
- **Avg Return:** -0.0004%
- **Volatility:** 0.0944%
- **Sample Size:** 7,200
- **Significance:** Low

### Day of Week: Sunday
- **Avg Return:** -0.0002%
- **Volatility:** 0.0904%
- **Sample Size:** 6,716
- **Significance:** Low

### Day of Week: Friday
- **Avg Return:** -0.0013%
- **Volatility:** 0.1405%
- **Sample Size:** 6,246
- **Significance:** Low

### Day of Week: Monday
- **Avg Return:** 0.0017%
- **Volatility:** 0.1596%
- **Sample Size:** 5,760
- **Significance:** Low

### Day of Week: Tuesday
- **Avg Return:** -0.0011%
- **Volatility:** 0.1075%
- **Sample Size:** 5,760
- **Significance:** Low

### Day of Week: Thursday
- **Avg Return:** -0.0018%
- **Volatility:** 0.0980%
- **Sample Size:** 5,760
- **Significance:** Low

### Day of Week: Wednesday
- **Avg Return:** -0.0012%
- **Volatility:** 0.0987%
- **Sample Size:** 5,760
- **Significance:** Low

### RSI Extreme: RSI < 30
- **Avg Return:** 0.0144%
- **Win Rate:** 55.0%
- **Sample Size:** 5,209
- **Significance:** Medium

### RSI Extreme: RSI > 70
- **Avg Return:** -0.0214%
- **Win Rate:** 52.8%
- **Sample Size:** 4,318
- **Significance:** Medium

### Hour of Day: 15:00
- **Avg Return:** 0.0012%
- **Volatility:** 0.1505%
- **Sample Size:** 1,802
- **Significance:** Low

### Hour of Day: 02:00
- **Avg Return:** 0.0031%
- **Volatility:** 0.1060%
- **Sample Size:** 1,800
- **Significance:** Low

### Hour of Day: 04:00
- **Avg Return:** 0.0016%
- **Volatility:** 0.1210%
- **Sample Size:** 1,800
- **Significance:** Low

### Hour of Day: 05:00
- **Avg Return:** -0.0023%
- **Volatility:** 0.0935%
- **Sample Size:** 1,800
- **Significance:** Low

### Hour of Day: 06:00
- **Avg Return:** -0.0003%
- **Volatility:** 0.0909%
- **Sample Size:** 1,800
- **Significance:** Low

### Hour of Day: 03:00
- **Avg Return:** -0.0032%
- **Volatility:** 0.0998%
- **Sample Size:** 1,800
- **Significance:** Low


---

## 5. Coin Personality Profile

### Volatility Character
- **Average daily range:** 165.86%
- **Average candle range:** 0.1190%
- **Average body size:** 0.0741%
- **Explosive moves (>2% body):** 0.01% of candles
- **Character:** GRADUAL - smooth mover

### Liquidity Character
- **Average volume:** 911.03 TRUMP
- **Volume consistency (CV):** 2.69 (High variance - sporadic)
- **Slippage risk:** HIGH - use limit orders

### Momentum Character
- **Win rate (all candles):** 45.2%
- **Average winning move:** 0.0814%
- **Average losing move:** -0.0824%
- **Profit factor:** 0.99x
- **Character:** Quick mean reversion - take profits fast

### Risk Character
- **Largest single move up:** 2.45%
- **Largest single move down:** -4.44%
- **Total price range (period):** 71.44%
- **Black swan frequency:** LOW - predictable ranges

---

## 6. Strategy Implications

Based on the comprehensive pattern analysis, here are the BEST strategy types for TRUMP:

### Recommended Strategy Types (Ranked)

1. **Scalping** (Score: 8.5/10)
2. **Trend Following** (Score: 4.5/10)
3. **Mean Reversion** (Score: 4.0/10)
4. **Breakout Trading** (Score: 0.0/10)


### Specific Strategy Ideas

**HIGH CONFIDENCE (>60% win rate potential):**
- No single patterns exceeded 60% threshold - consider combination strategies


**BEST TIMES TO TRADE:**
- US session (best avg return)
- Hour 2:00 (best hourly return: 0.0031%)

**TIMES TO AVOID:**
- Overnight session (worst avg return)
- Hour 23:00 (worst hourly return: -0.0035%)

---

## 7. Next Steps for Strategy Development

1. **Backtest the top 3 sequential patterns** identified in Section 2
2. **Focus development on scalping** strategies based on regime analysis
3. **Incorporate session filtering** - trade primarily during US session
4. **Test statistical edges** from Section 4 with minimum sample sizes
5. **Build regime detection** to switch between trend/mean-revert modes

---

## Data Files Generated

- `TRUMP_session_stats.csv` - Session performance metrics
- `TRUMP_sequential_patterns.csv` - X→Y pattern catalog
- `TRUMP_regime_analysis.csv` - Regime classification results
- `TRUMP_statistical_edges.csv` - Statistical edge rankings
- `TRUMP_pattern_stats.csv` - Overall behavioral statistics

**Analysis complete. Ready for strategy backtesting phase.**
