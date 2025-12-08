# PEPE Pattern Analysis - Master Discovery Report

**Analysis Date**: 2025-12-07 19:45:00
**Data Period**: 2025-11-07 13:02:00 to 2025-12-07 13:02:00
**Total Candles**: 43,201 (1-minute timeframe)
**Duration**: 30 days

---

## Executive Summary - Top 5 Patterns Discovered

### Top Sequential Patterns

**14. After Lower BB touch** (Horizon: 3 candles)
   - Average Return: 0.107%
   - Win Rate: 69.8%
   - Sample Size: 2842

**15. After Lower BB touch** (Horizon: 5 candles)
   - Average Return: 0.107%
   - Win Rate: 73.0%
   - Sample Size: 2842

**13. After Lower BB touch** (Horizon: 1 candles)
   - Average Return: 0.080%
   - Win Rate: 41.1%
   - Sample Size: 2842

**5. After 3+ consecutive red** (Horizon: 1 candle)
   - Average Return: 0.054%
   - Win Rate: 19.8%
   - Sample Size: 262

**2. After >2% body candle** (Horizon: 3 candles)
   - Average Return: 0.021%
   - Win Rate: 50.0%
   - Sample Size: 4


---

## Session Analysis Results

| Session   |   Avg_Return_% |   Volatility_% |   Avg_ATR_% |   Avg_Volume_Ratio |   Long_WinRate_% |   Short_WinRate_% |   Best_Hour |   Worst_Hour |   Candles |
|:----------|---------------:|---------------:|------------:|-------------------:|-----------------:|------------------:|------------:|-------------:|----------:|
| Asia      |   -0.000296512 |       0.204338 |    0.182722 |            1.00926 |          49.848  |           50.152  |           2 |            7 |     14400 |
| Europe    |   -0.000881553 |       0.201893 |    0.183953 |            1.0256  |          49.003  |           50.9782 |          10 |            9 |     10801 |
| US        |   -2.79065e-05 |       0.238391 |    0.238115 |            1.02354 |          49.5964 |           50.4036 |          14 |           18 |     12600 |
| Overnight |    0.000512858 |       0.208416 |    0.185339 |            1.01662 |          49.6006 |           50.3994 |          21 |           23 |      5400 |

### Key Session Insights:

- **Best Performance**: Overnight session (Avg: 0.0005%)
- **Most Volatile**: US session (StdDev: 0.238%)
- **Best Long Win Rate**: Asia (49.8%)
- **Best Short Win Rate**: Europe (51.0%)

---

## Market Regime Analysis

| Regime         |   Percentage_% |   Avg_Return_% |   Volatility_% |   Long_WinRate_% |   Avg_Duration_Minutes |
|:---------------|---------------:|---------------:|---------------:|-----------------:|-----------------------:|
| CHOPPY         |     16.0344    |     0.00049074 |      0.0522832 |          2.87282 |                   6927 |
| UNKNOWN        |     46.7929    |    -0.00290823 |      0.236853  |         29.7947  |                  20215 |
| MEAN_REVERTING |     31.6034    |     0.00405338 |      0.190653  |         26.236   |                  13653 |
| TRENDING       |      5.55311   |    -0.0050003  |      0.362327  |         38.516   |                   2399 |
| EXPLOSIVE      |      0.0162033 |     0.0961673  |      2.1385    |         57.1429  |                      7 |

### Regime Insights:
- PEPE spends **5.6%** of time in trending mode
- **31.6%** in mean-reverting conditions
- **0.0%** in explosive/breakout mode
- **16.0%** in choppy/unplayable conditions

**Strategy Implication**: PEPE shows balanced regime distribution - hybrid strategies recommended

---

## Statistical Edges (Top 15)

| Edge_Type    | Condition              |   Avg_Return_% |   WinRate_% |   Sample_Size |
|:-------------|:-----------------------|---------------:|------------:|--------------:|
| RSI_Extreme  | Oversold (RSI 30)      |     0.0580664  |     66.9751 |          3458 |
| RSI_Extreme  | Overbought (RSI 70)    |    -0.0505703  |     45.6198 |          3025 |
| SMA_Distance | Far_Below SMA50 (2.0%) |     0.0228194  |     44.0758 |           211 |
| SMA_Distance | Far_Above SMA50 (2.0%) |    -0.0195968  |     50      |           146 |
| Hour_of_Day  | 23:00                  |    -0.00703686 |     22.1111 |          1800 |
| Hour_of_Day  | 21:00                  |     0.00480994 |     25.5    |          1800 |
| Hour_of_Day  | 09:00                  |    -0.00449698 |     24.2778 |          1800 |
| Hour_of_Day  | 13:00                  |    -0.00400409 |     26.2632 |          1801 |
| Hour_of_Day  | 22:00                  |     0.00376549 |     24.8333 |          1800 |
| Hour_of_Day  | 10:00                  |     0.00328226 |     23.3333 |          1800 |
| Hour_of_Day  | 12:00                  |     0.00324896 |     24.6111 |          1800 |
| Hour_of_Day  | 14:00                  |     0.0030033  |     27.0556 |          1800 |
| Hour_of_Day  | 07:00                  |    -0.00297757 |     23.5    |          1800 |
| Hour_of_Day  | 11:00                  |    -0.00279762 |     23.3333 |          1800 |
| Hour_of_Day  | 18:00                  |    -0.00269268 |     27      |          1800 |

---

## PEPE Behavioral Profile

### Volatility Character:
- **Average Daily Range**: 8.15%
- **Typical Move Size**: 1.43% before pullback
- **Extreme Moves/Day**: 0.0 (>3% moves)
- **Character**: Moderate mover

### Liquidity Character:
- **Average Volume**: 1,232,938,648
- **Volume Variability**: 2,981,293,695 (StdDev)
- **Assessment**: Sporadic liquidity - use limit orders

### Momentum Character:
- **Follow-Through Rate**: 32.4% (after >1% move)
- **Average Win**: 0.274%
- **Average Loss**: -0.270%
- **Win/Loss Ratio**: 1.01x

### Risk Character:
- **Max Observed Drawdown**: 37.83%
- **Risk Assessment**: Moderate volatility - standard risk management

---

## Strategy Implications

### ✅ RECOMMENDED Strategies:


**2. MEAN-REVERSION** (Secondary Strategy)
- Use Bollinger Band extremes for entries
- RSI oversold/overbought confirmation
- Quick profit targets (not a strong mean-reverter)
- Best sessions: Europe


### ❌ AVOID Trading When:

- Regime is **CHOPPY** (16.0% of time) - high wick ratios, small bodies
- During Europe session (lowest opportunity)
- After extreme moves without volume confirmation (likely fake-outs)

---

## High-Confidence Patterns (Win Rate > 60% or Strong Returns)

### Sequential Patterns:
- **After Lower BB touch** → 0.107% avg return, 69.8% win rate (n=2842)
- **After Lower BB touch** → 0.107% avg return, 73.0% win rate (n=2842)
- **After bullish SMA50 cross** → 0.007% avg return, 60.9% win rate (n=5111)
- **After Upper BB touch** → -0.105% avg return, 52.5% win rate (n=2665)
- **After Upper BB touch** → -0.120% avg return, 55.4% win rate (n=2665)

### Statistical Edges:
- **RSI_Extreme: Oversold (RSI 30)** → 0.058% avg return, 67.0% win rate (n=3458)
- **RSI_Extreme: Overbought (RSI 70)** → -0.051% avg return, 45.6% win rate (n=3025)


---

## Next Steps - Strategy Development

Based on this analysis, the following strategy types should be developed and backtested:

1. **Primary**: Mean-reversion with BB bands and RSI
2. **Secondary**: Volume-confirmed breakout strategies
3. **Filters**: Avoid CHOPPY regime, focus on high-volatility sessions

---

## Data Files Generated

- `PEPE_session_stats.csv` - Session-by-session statistics
- `PEPE_sequential_patterns.csv` - Complete sequential pattern analysis
- `PEPE_regime_analysis.csv` - Regime classification results
- `PEPE_statistical_edges.csv` - All statistical edges discovered

**Analysis Complete** ✓

