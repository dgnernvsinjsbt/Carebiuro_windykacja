# DOGE/USDT Strategy Optimization Report

**Generated:** 2025-12-07 15:53:18

---

## Baseline Strategy Performance

**Entry Signal:**
- Price < 1.0% below 20-period SMA
- Previous 4 consecutive down bars completed

**Exit Rules:**
- Stop Loss: 1.5x ATR below entry
- Take Profit: 3.0x ATR above entry

**Baseline Metrics:**
- Total Trades: 27
- Win Rate: 55.56%
- Net P&L: 6.10%
- Max Drawdown: 2.59%
- R:R Ratio: 1.42
- Profit Factor: 1.74

---

## 1. Session Optimization

| Session | Trades | Win Rate | Return % | R:R | Max DD |
|---------|--------|----------|----------|-----|--------|
| Afternoon (12-18 UTC) | 14 | 71.4% | 6.23% | 1.29 | 1.53% |
| All Hours | 27 | 55.6% | 6.10% | 1.42 | 2.59% |
| US (14-17 UTC) | 11 | 63.6% | 3.60% | 1.31 | 1.53% |
| Europe (8-14 UTC) | 2 | 100.0% | 1.93% | inf | 0.00% |
| Overnight (17-24 UTC) | 7 | 42.9% | 0.58% | 1.70 | 1.02% |
| Morning (6-12 UTC) | 0 | 0.0% | 0.00% | 0.00 | 0.00% |
| Asia (0-8 UTC) | 7 | 42.9% | -0.11% | 1.29 | 2.26% |

**Best Session:** Afternoon (12-18 UTC)
- Improvement: 0.13% vs baseline

---

## 2. Dynamic SL/TP Optimization

| Config | Trades | Win Rate | Return % | R:R | Max DD |
|--------|--------|----------|----------|-----|--------|
| SL:1.0x_TP:6.0x | 28 | 28.6% | 5.80% | 3.90 | 2.90% |
| SL:1.5x_TP:6.0x | 27 | 37.0% | 7.89% | 2.84 | 3.78% |
| SL:1.0x_TP:4.0x | 28 | 35.7% | 3.47% | 2.48 | 2.88% |
| SL:2.0x_TP:6.0x | 26 | 42.3% | 9.10% | 2.32 | 4.70% |
| SL:1.0x_TP:3.0x | 28 | 46.4% | 4.92% | 1.91 | 2.88% |
| SL:1.5x_TP:4.0x | 27 | 44.4% | 4.61% | 1.82 | 2.98% |
| SL:2.0x_TP:4.0x | 26 | 50.0% | 5.34% | 1.49 | 3.69% |
| SL:1.5x_TP:3.0x | 27 | 55.6% | 6.10% | 1.42 | 2.59% |
| SL:2.0x_TP:3.0x | 26 | 57.7% | 5.11% | 1.16 | 2.88% |
| SL:1.0x_TP:2.0x | 28 | 53.6% | 1.88% | 1.13 | 2.32% |

**Best SL/TP:** SL:1.0x_TP:6.0x
- R:R Ratio: 3.90 (baseline: 1.42)

---

## 3. Higher Timeframe Filter

| Filter | Trades | Win Rate | Return % | R:R | Max DD |
|--------|--------|----------|----------|-----|--------|
| No Filter | 27 | 55.6% | 6.10% | 1.42 | 2.59% |
| 1H SMA50 Aligned | 4 | 50.0% | -0.04% | 0.97 | 0.53% |
| 1H EMA50 Aligned | 4 | 50.0% | -0.04% | 0.97 | 0.53% |

---

## 4. Limit Order Entry

| Order Type | Trades | Win Rate | Return % | Fees Impact |
|------------|--------|----------|----------|-------------|
| Market Orders (0.1% fees) | 27 | 55.6% | 6.10% | - |
| Limit Orders (0.07% fees) | 27 | 55.6% | 7.83% | - |

---

## 5. Additional Filters

| Filter | Trades | Win Rate | Return % | R:R | Max DD |
|--------|--------|----------|----------|-----|--------|
| Volume > 1.5x avg | 21 | 47.6% | 2.37% | 1.47 | 4.46% |
| Volume > 1.2x avg | 22 | 50.0% | 3.13% | 1.44 | 4.46% |
| No Filters | 27 | 55.6% | 6.10% | 1.42 | 2.59% |
| Low volatility (0.1-0.5%) | 27 | 55.6% | 6.10% | 1.42 | 2.59% |
| Medium volatility (0.3-1.0%) | 3 | 66.7% | 1.38% | 1.26 | 0.92% |
| Combined: Vol>1.2x + Med Vol | 3 | 66.7% | 1.38% | 1.26 | 0.92% |

---

## Recommendations

### Optimized Strategy Configuration

**Entry:**
- Price < 1.0% below 20-period SMA
- 4+ consecutive down bars
- Additional filter: Volume > 1.5x avg

**Exit:**
- Stop Loss: 1.0x ATR
- Take Profit: 6.0x ATR

**Order Type:** Limit orders (0.035% offset, 0.07% fees)

### Expected Performance
- Baseline R:R: 1.42
- Optimized R:R: 3.90
- Improvement: 174.7%