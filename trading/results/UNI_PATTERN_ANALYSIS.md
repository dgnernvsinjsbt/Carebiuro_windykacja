# UNI/USDT Pattern Discovery Report
Generated: 2025-12-08 13:25:01

## Dataset Summary
- **Candles**: 43,001 (30 days of 1-minute data)
- **Date Range**: 2025-11-07 16:24:00 to 2025-12-07 13:04:00
- **Price Range**: $5.38 - $10.18
- **Average Volume**: 1,420

---

## 1. Session Analysis

Best performing sessions (by average return):

| Session | Avg Return | Volatility | Long WR | Short WR | Avg Volume | Best Hour | Sample Size |
|---------|-----------|-----------|---------|----------|------------|-----------|-------------|
| OVERNIGHT | +0.0043% | 0.217% | 47.4% | 46.3% | 1.04x | 22:00 (+0.0131%) | 5,400 |
| ASIA | +0.0007% | 0.188% | 46.5% | 46.9% | 1.03x | 01:00 (+0.0073%) | 14,400 |
| US | -0.0006% | 0.194% | 46.4% | 48.5% | 1.02x | 14:00 (+0.0062%) | 12,456 |
| EUROPE | -0.0018% | 0.153% | 45.9% | 47.5% | 1.03x | 10:00 (+0.0085%) | 10,745 |

### Key Insights:
- **Best session**: OVERNIGHT (+0.0043% avg)
- **Highest volatility**: OVERNIGHT (0.217% std)
- **Best volume**: OVERNIGHT (1.04x avg)

---

## 2. Sequential Patterns

Top 20 patterns by expected return:

| Rank | Pattern | Lookforward | Avg Return | Win Rate | Sample Size |
|------|---------|-------------|------------|----------|-------------|
| 1 | after_explosive_bear | 3 bars | +0.628% | 83.3% | 6 |
| 2 | after_explosive_bear | 10 bars | +0.315% | 50.0% | 6 |
| 3 | after_explosive_bear | 5 bars | +0.202% | 50.0% | 6 |
| 4 | after_explosive_bull | 1 bars | +0.037% | 52.6% | 19 |
| 5 | touch_bb_upper_2std | 20 bars | +0.029% | 46.9% | 2268 |
| 6 | consec_red>=5 | 5 bars | +0.021% | 51.5% | 940 |
| 7 | consec_red>=4 | 5 bars | +0.016% | 51.5% | 2040 |
| 8 | consec_red>=3 | 5 bars | +0.011% | 50.0% | 4396 |
| 9 | touch_bb_lower_2std | 5 bars | +0.011% | 50.9% | 2200 |
| 10 | consec_red>=5 | 3 bars | +0.010% | 53.4% | 940 |
| 11 | consec_red>=4 | 3 bars | +0.009% | 50.9% | 2040 |
| 12 | consec_red>=3 | 3 bars | +0.008% | 49.9% | 4396 |
| 13 | consec_red>=4 | 1 bars | +0.007% | 49.1% | 2040 |
| 14 | consec_red>=3 | 1 bars | +0.005% | 48.6% | 4396 |
| 15 | touch_bb_upper_3std | 1 bars | +0.004% | 41.3% | 143 |
| 16 | touch_bb_lower_2std | 1 bars | +0.002% | 49.1% | 2200 |
| 17 | touch_bb_lower_2std | 10 bars | +0.002% | 49.8% | 2200 |
| 18 | consec_green>=4 | 1 bars | +0.002% | 46.6% | 1913 |
| 19 | consec_green>=3 | 1 bars | +0.002% | 46.2% | 4141 |
| 20 | touch_bb_upper_2std | 5 bars | +0.001% | 45.5% | 2273 |

### Pattern Categories Tested:
1. **After explosive candles** (>1.2% body + 3x volume)
2. **After consecutive green/red bars** (3, 4, 5+ in a row)
3. **After rejection wicks** (wick > 2x body)
4. **After Bollinger Band touches** (2std and 3std)
5. **After volume spikes** (>3x average)

---

## 3. Market Regime Analysis

Regime distribution (60-minute windows):

| Regime | Percentage | Description |
|--------|-----------|-------------|
| mean_reverting | 79.8% | Oscillates around mean (3+ crosses) |
| choppy | 10.6% | Small moves, no clear direction |
| trending_up | 5.0% | Strong directional move (>2%) |
| trending_down | 4.5% | Strong directional move (>2%) |
| explosive | 0.1% | Large single-candle moves (>3%) |

### Regime Implications:
- **OPPORTUNITY**: 80% mean-reverting regime supports bounce/fade strategies

---

## 4. Statistical Edges

Top 20 edges by expected return:

| Rank | Edge Type | Lookforward | Avg Return | Win Rate | Sample Size |
|------|-----------|-------------|------------|----------|-------------|
| 1 | rsi_overbought_fade | 20 bars | +0.0400% | 43.5% | 4616 |
| 2 | cross_above_sma200 | 20 bars | +0.0357% | 50.3% | 785 |
| 3 | cross_below_sma200 | 20 bars | +0.0280% | 49.6% | 785 |
| 4 | cross_above_sma200 | 10 bars | +0.0231% | 47.3% | 785 |
| 5 | rsi_overbought_fade | 10 bars | +0.0185% | 45.0% | 4625 |
| 6 | cross_below_sma50 | 10 bars | +0.0155% | 48.8% | 1771 |
| 7 | cross_above_sma50 | 10 bars | +0.0134% | 46.2% | 1771 |
| 8 | hour_22 | 1 bars | +0.0131% | 48.2% | 1800 |
| 9 | cross_above_sma200 | 5 bars | +0.0116% | 45.9% | 785 |
| 10 | cross_above_sma200 | 1 bars | +0.0108% | 46.6% | 785 |
| 11 | cross_below_sma50 | 5 bars | +0.0107% | 49.6% | 1771 |
| 12 | cross_below_sma200 | 5 bars | +0.0101% | 47.3% | 785 |
| 13 | hour_21 | 1 bars | +0.0090% | 48.8% | 1800 |
| 14 | cross_below_sma200 | 10 bars | +0.0088% | 48.3% | 785 |
| 15 | hour_10 | 1 bars | +0.0085% | 47.6% | 1800 |
| 16 | hour_01 | 1 bars | +0.0073% | 49.6% | 1800 |
| 17 | hour_14 | 1 bars | +0.0062% | 46.0% | 1740 |
| 18 | day_Monday | 1 bars | +0.0061% | 47.7% | 5760 |
| 19 | cross_above_sma50 | 5 bars | +0.0050% | 46.0% | 1771 |
| 20 | cross_above_sma50 | 20 bars | +0.0044% | 46.9% | 1771 |

### Edge Categories Tested:
1. **RSI extremes** (oversold bounce < 30, overbought fade > 70)
2. **SMA crossovers** (20, 50, 200 period)
3. **Day of week** patterns
4. **Hour of day** patterns

---

## 5. Coin Personality Profile

### Volatility Character
- **Daily range**: 284.72% average
- **Candle range**: 0.205% average
- **Max single move**: 5.33%
- **ATR(14)**: 0.0143
- **Assessment**: NORMAL volatility - standard risk management applies

### Liquidity Character
- **Average volume**: 1,420
- **Volume CV**: 2.40
- **Assessment**: INCONSISTENT volume - spiky, avoid low-volume periods

### Momentum Character
- **1-lag autocorr**: -0.0162
- **5-lag autocorr**: +0.0037
- **After +1% move**: +1.5163% avg next candle
- **After -1% move**: -1.4723% avg next candle
- **Assessment**: NEUTRAL momentum - no strong continuation/reversal bias

### Risk Character
- **Max drawdown**: 47.17%
- **Overall win rate**: 46.4%

---

## 6. High-Confidence Patterns

Patterns with win rate > 60% AND edge > 0.1% (above fees):

| Pattern Type | Pattern Name | Edge | Win Rate | Sample Size | Lookforward |
|--------------|--------------|------|----------|-------------|-------------|
| - | **NO HIGH-CONFIDENCE PATTERNS FOUND** | - | - | - | - |

**This suggests UNI is very difficult to trade profitably on 1-minute timeframe.**

---

## 7. Strategy Recommendations

1. **MIXED: Weak autocorrelation suggests both trend and mean-reversion may work**

2. **NORMAL VOLATILITY: Standard ATR-based stops should work**

3. **BEST SESSION: OVERNIGHT (avg return: +0.0043%)**


---

## 8. Next Steps for Strategy Development

Based on this analysis, here are the recommended approaches for backtesting:


### Risk Management Guidelines
- **Position size**: Start with 0.5-1% risk per trade
- **Stop loss**: 1.5-2.0x ATR(14) = ~$0.0215 - $0.0286
- **Take profit**: 3-4:1 R:R minimum to overcome 11% choppy regime
- **Max trades/day**: Limit to 5-10 to avoid overtrading in chop
- **Session filter**: Stick to OVERNIGHT session for best odds

---

## Files Generated
1. `UNI_session_stats.csv` - Session performance data
2. `UNI_sequential_patterns.csv` - X→Y pattern probabilities
3. `UNI_regime_analysis.csv` - Regime classification timeline
4. `UNI_statistical_edges.csv` - Technical indicator edges
5. `UNI_pattern_stats.csv` - High-confidence pattern summary
6. `UNI_PATTERN_ANALYSIS.md` - This comprehensive report

---

*Generated by Master Pattern Noticer*
*Analysis completed in deep discovery mode*
