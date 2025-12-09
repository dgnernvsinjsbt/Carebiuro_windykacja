# PIPPIN ATR Expansion Strategy - Test Results

## Executive Summary

The FARTCOIN ATR Expansion strategy (8.44x Return/DD baseline) was tested on PIPPIN/USDT over 7 days of 1-minute data. The strategy achieved a **-0.77x Return/DD ratio** with 62 trades and a 25.8% win rate.

**Verdict:** ❌ **DO NOT DEPLOY** - Insufficient risk-adjusted returns

---

## Performance Metrics

| Metric | PIPPIN | FARTCOIN (Baseline) |
|--------|--------|---------------------|
| **Return/DD Ratio** | **-0.77x** | **8.44x** |
| Total Return | -53.73% | +101.11% |
| Max Drawdown | -70.05% | -11.98% |
| Win Rate | 25.8% | 42.6% |
| Trades | 62 | 94 |
| Fill Rate | 38.8% | 21.2% |
| Avg Win | +7.40% | +4.97% |
| Avg Loss | -4.00% | -2.23% |
| Best Trade | +27.58% | N/A |
| Worst Trade | -9.46% | N/A |

### Exit Breakdown

| Exit Type | PIPPIN | FARTCOIN Baseline |
|-----------|--------|-------------------|
| TP | 6 (9.7%) | 40% |
| SL | 45 (72.6%) | 47% |
| TIME | 10 (16.1%) | 13% |
| END | 1 (1.6%) | 0% |

---

## Strategy Configuration

**Entry Conditions (ALL must be true):**
- ATR(14) > 1.5x rolling 20-bar average (volatility breakout)
- Price within 3% of EMA(20) (prevents late entries)
- Directional candle (bullish for LONG, bearish for SHORT)
- Limit order: LONG at +1%, SHORT at -1% from signal price
- Max wait: 3 bars for fill

**Exit Rules:**
- Stop Loss: 2.0x ATR(14) from fill price
- Take Profit: 8.0x ATR(14) from fill price (R:R = 4:1)
- Time Exit: 200 bars (3.3 hours)
- Fees: 0.1% round-trip (0.05% entry + 0.05% exit)

---

## Analysis

### Dataset Size Note

⚠️ **Limited Sample:** PIPPIN data covers only 7 days compared to FARTCOIN's 32-day baseline. With only 62 trades, results may not be statistically significant. Longer testing period recommended before live deployment.

### Why It Worked (or Didn't)

**Strategy underperformed on PIPPIN:**
- PIPPIN may have different volatility characteristics than FARTCOIN
- Possible mean-reversion behavior instead of trending breakouts
- Limited fill rate or excessive stop-outs

### Comparison to FARTCOIN Baseline

- Return/DD: -0.77x vs 8.44x (-109%)
- Total Return: -53.73% vs +101.11% (-153%)
- Max Drawdown: -70.05% vs -11.98% (worse)
- Win Rate: 25.8% vs 42.6% (-16.8pp)
- Trades: 62 vs 94 (-34%)

---

## Recommendation

### ❌ DO NOT DEPLOY

The strategy shows insufficient risk-adjusted returns on PIPPIN. Issues:

1. **Low Return/DD ratio** (-0.77x vs 8.44x target)
2. **62 trades may not be statistically significant**
3. **PIPPIN volatility profile may not suit this strategy**

**Alternative approaches:**
- Test mean-reversion strategies instead (DOGE-style)
- Try volume zone strategies (TRUMP/PEPE-style)
- Optimize parameters specifically for PIPPIN
- Collect more data (30+ days) for proper analysis

---

## Data Files

- **Data:** `trading/pippin_7d_bingx.csv` (11,097 candles)
- **Code:** `trading/pippin_atr_strategy_test.py`
- **Trades:** `trading/results/pippin_atr_trades.csv` (62 trades)
- **Report:** `trading/results/PIPPIN_ATR_STRATEGY_REPORT.md`
