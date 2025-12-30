# DONCHIAN 1H PORTFOLIO - TOP 8 COINS

**Created:** 2025-12-30
**Timeframe:** 1H candles
**Data Period:** Jun-Dec 2025
**Strategy:** Donchian Channel Breakout with ATR-based TP/SL

---

## PORTFOLIO PERFORMANCE BY RISK LEVEL

All trades stacked chronologically with risk-based position sizing.
Position size = (Equity × Risk%) / SL_distance%

| Risk | Final Equity | Return | Max DD | R:R |
|------|--------------|--------|--------|-----|
| **1%** | $820 | +720% | -15.4% | **47x** |
| **2%** | $5,818 | +5,718% | -28.6% | **200x** |
| **3%** | $36,002 | +35,902% | -39.9% | **899x** |
| **4%** | $195,692 | +195,592% | -49.6% | **3,941x** |
| **5%** | $948,926 | +948,826% | -57.9% | **16,390x** |

**Total Trades:** 619 | **Win Rate:** 60.6% | **Avg SL Distance:** 4.67%

---

## MONTHLY BREAKDOWN BY RISK LEVEL

### 1% Risk (Conservative)
| Month | Equity | Return |
|-------|--------|--------|
| Jun 2025 | $136 | +36% |
| Jul 2025 | $206 | +52% |
| Aug 2025 | $301 | +46% |
| Sep 2025 | $370 | +23% |
| Oct 2025 | $538 | +46% |
| Nov 2025 | $729 | +36% |
| Dec 2025 | $820 | +12% |

### 2% Risk (Moderate)
| Month | Equity | Return |
|-------|--------|--------|
| Jun 2025 | $180 | +80% |
| Jul 2025 | $404 | +124% |
| Aug 2025 | $843 | +108% |
| Sep 2025 | $1,253 | +49% |
| Oct 2025 | $2,575 | +106% |
| Nov 2025 | $4,644 | +80% |
| Dec 2025 | $5,818 | +25% |

### 3% Risk (Aggressive)
| Month | Equity | Return |
|-------|--------|--------|
| Jun 2025 | $232 | +132% |
| Jul 2025 | $754 | +224% |
| Aug 2025 | $2,212 | +194% |
| Sep 2025 | $3,907 | +77% |
| Oct 2025 | $11,025 | +182% |
| Nov 2025 | $26,026 | +136% |
| Dec 2025 | $36,002 | +38% |

### 5% Risk (Very Aggressive)
| Month | Equity | Return |
|-------|--------|--------|
| Jun 2025 | $358 | +258% |
| Jul 2025 | $2,273 | +534% |
| Aug 2025 | $12,622 | +455% |
| Sep 2025 | $30,360 | +141% |
| Oct 2025 | $149,398 | +392% |
| Nov 2025 | $576,830 | +286% |
| Dec 2025 | $948,926 | +65% |

---

## STRATEGY PARAMETERS (TOP 8 COINS)

| Rank | Coin | TP (ATR) | Period | SL (ATR) | Solo R:R | Win Rate | Trades |
|------|------|----------|--------|----------|----------|----------|--------|
| 1 | **PENGU** | 7.0 | 25 | 5 | 34.05x | 68% | 25 |
| 2 | **DOGE** | 4.0 | 15 | 4 | 16.72x | 67% | 60 |
| 3 | **FARTCOIN** | 7.5 | 15 | 2 | 12.57x | 31% | 51 |
| 4 | **ETH** | 1.5 | 20 | 4 | 10.12x | 80% | 230 |
| 5 | **UNI** | 10.5 | 30 | 2 | 9.95x | 36% | 44 |
| 6 | **PI** | 3.0 | 15 | 2 | 7.79x | 53% | 158 |
| 7 | **CRV** | 9.0 | 15 | 5 | 7.43x | 59% | 17 |
| 8 | **AIXBT** | 12.0 | 15 | 2 | 5.86x | 26% | 34 |

### EXCLUDED COINS (R:R < 5x)

| Coin | TP (ATR) | Period | SL (ATR) | R:R | Reason |
|------|----------|--------|----------|-----|--------|
| BTC | 9.0 | 25 | 3 | 3.56x | Low return for effort |
| TRUMPSOL | 3.0 | 25 | 3 | 1.07x | Barely profitable |
| MOODENG | 1.5 | 30 | 2 | 0.12x | Strategy doesn't work |

---

## POSITION SIZING RULES

**Risk-Based Position Sizing:**
```
Position Size = (Equity × Risk%) / SL_Distance%

Example (2% risk, 4% SL distance):
  Position Size = ($10,000 × 2%) / 4% = $5,000
  Leverage = $5,000 / $10,000 = 0.5x

Example (2% risk, 2% SL distance):
  Position Size = ($10,000 × 2%) / 2% = $10,000
  Leverage = $10,000 / $10,000 = 1.0x
```

**Key:** If SL hits, you lose exactly Risk% of equity. Tighter SL = bigger position.

**Max Leverage Cap:** 5x (to prevent extreme positions on very tight SLs)

---

## STRATEGY LOGIC

```
Entry LONG:  Close > Highest High of last N bars (Period)
Entry SHORT: Close < Lowest Low of last N bars (Period)

Take Profit: Entry ± (TP_ATR × ATR14)
Stop Loss:   Entry ∓ (SL_ATR × ATR14)

ATR = 14-period Average True Range (simple rolling mean of H-L)
```

---

## DATA FILES

```
trading/
├── pengu_1h_jun_dec_2025.csv
├── doge_1h_jun_dec_2025.csv
├── fartcoin_1h_jun_dec_2025.csv
├── eth_1h_2025.csv
├── uni_1h_jun_dec_2025.csv
├── pi_1h_jun_dec_2025.csv
├── crv_1h_jun_dec_2025.csv
└── aixbt_1h_jun_dec_2025.csv
```

---

## KEY INSIGHTS

### TP Optimization Results (0.5 ATR increments, 1-12 ATR tested)

**Tight TPs work for:** ETH (1.5), PI (3.0), DOGE (4.0)
- Lower volatility, cleaner reversals
- Higher win rates (53-80%)

**Wide TPs work for:** PENGU (7.0), FARTCOIN (7.5), CRV (9.0), UNI (10.5), AIXBT (12.0)
- Higher volatility memecoins
- Lower win rates (26-68%) but bigger winners

### Risk Level Recommendations

| Risk | Use Case | Drawdown Tolerance |
|------|----------|-------------------|
| 1% | Conservative / large accounts | -15% max |
| 2% | Balanced growth | -29% max |
| 3% | Aggressive growth | -40% max |
| 5% | High risk / small accounts | -58% max |

---

## QUICK REFERENCE - COPY/PASTE PARAMETERS

```python
DONCHIAN_STRATEGIES = {
    'PENGU':    {'tp_atr': 7.0,  'period': 25, 'sl_atr': 5},
    'DOGE':     {'tp_atr': 4.0,  'period': 15, 'sl_atr': 4},
    'FARTCOIN': {'tp_atr': 7.5,  'period': 15, 'sl_atr': 2},
    'ETH':      {'tp_atr': 1.5,  'period': 20, 'sl_atr': 4},
    'UNI':      {'tp_atr': 10.5, 'period': 30, 'sl_atr': 2},
    'PI':       {'tp_atr': 3.0,  'period': 15, 'sl_atr': 2},
    'CRV':      {'tp_atr': 9.0,  'period': 15, 'sl_atr': 5},
    'AIXBT':    {'tp_atr': 12.0, 'period': 15, 'sl_atr': 2},
}

FEE_PCT = 0.07       # Total round-trip fee
ATR_PERIOD = 14      # For ATR calculation
MAX_LEVERAGE = 5.0   # Cap leverage to prevent extreme positions
```

---

**Last Updated:** 2025-12-30
