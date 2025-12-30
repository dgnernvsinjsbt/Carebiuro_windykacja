# DONCHIAN 1H PORTFOLIO - TOP 8 COINS

**Created:** 2025-12-30
**Timeframe:** 1H candles
**Data Period:** Jun-Dec 2025
**Strategy:** Donchian Channel Breakout with ATR-based TP/SL

---

## PORTFOLIO PERFORMANCE

| Metric | Value |
|--------|-------|
| **Starting Equity** | $100.00 |
| **Final Equity** | $453.48 |
| **Total Return** | +353.5% |
| **Max Drawdown** | -13.1% |
| **R:R Ratio** | **27.01x** |
| **Total Trades** | 619 |
| **Profitable Months** | 7/7 (100%) |

### Monthly Performance

| Month | Equity | Return | Status |
|-------|--------|--------|--------|
| Jun 2025 | $110.59 | +10.6% | ✅ |
| Jul 2025 | $181.07 | +63.7% | ✅ |
| Aug 2025 | $217.89 | +20.3% | ✅ |
| Sep 2025 | $259.28 | +19.0% | ✅ |
| Oct 2025 | $346.03 | +33.5% | ✅ |
| Nov 2025 | $408.55 | +18.1% | ✅ |
| Dec 2025 | $453.48 | +11.0% | ✅ |

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

## PORTFOLIO RULES

1. **Allocation:** Each coin gets 1/8th (12.5%) of total equity
2. **Position Size:** 100% of coin's allocated equity per trade
3. **Rebalancing:** Monthly (redistribute equity equally across all 8 coins)
4. **Fees:** 0.07% round-trip included in all calculations

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

### TP Optimization Results

**Tight TPs work for:** ETH (1.5), PI (3.0), DOGE (4.0)
- Lower volatility, cleaner reversals
- Higher win rates (53-80%)

**Wide TPs work for:** PENGU (7.0), FARTCOIN (7.5), CRV (9.0), UNI (10.5), AIXBT (12.0)
- Higher volatility memecoins
- Lower win rates (26-68%) but bigger winners

### Portfolio Diversification Benefits

- **Solo best coin (PENGU):** 34.05x R:R, 740% return, 21.7% DD
- **8-coin portfolio:** 27.01x R:R, 353.5% return, **13.1% DD**

Portfolio has **lower drawdown** (-13.1% vs -21.7%) with still excellent R:R!

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

FEE_PCT = 0.07  # Total round-trip fee
ATR_PERIOD = 14  # For ATR calculation
```

---

**Last Updated:** 2025-12-30
