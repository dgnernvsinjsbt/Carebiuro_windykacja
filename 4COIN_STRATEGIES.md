# 🎯 4-COIN SHORT REVERSAL PORTFOLIO (15m timeframe)

**Portfolio Performance (Jun-Dec 2025):**
- **Total Return:** +5,204,473% ($100 → $5.2M)
- **Max Drawdown:** -65.9%
- **Return/DD Ratio:** 78,973x 🏆 EXCEPTIONAL!
- **Timeframe:** 15-minute candles
- **Position Sizing:** 5% risk per trade
- **Method:** Limit orders with swing-based entries

---

## 📊 STRATEGY PARAMETERS COMPARISON

| Coin | RSI Trigger | Limit Offset | TP % | File |
|------|-------------|--------------|------|------|
| **FARTCOIN** | 70 | 1.0 ATR | 10.0% | `fartcoin_short_reversal.py` |
| **MELANIA** | 72 | 0.8 ATR | 10.0% | `melania_short_reversal.py` |
| **DOGE** | 72 | 0.6 ATR | 6.0% | `doge_short_reversal.py` |
| **MOODENG** | 70 | 0.8 ATR | 8.0% | `moodeng_short_reversal.py` |

**Common Parameters (all 4 strategies):**
- `lookback = 5` (swing low lookback period)
- `max_wait_bars = 20` (5 hours timeout for limit orders)
- `max_sl_pct = 10.0%` (skip if SL distance > 10%)
- `risk_pct = 5.0%` (risk 5% of equity per trade)

---

## 🔄 UNIVERSAL STRATEGY LOGIC

All 4 strategies follow the same core logic with different parameters:

1. **ARM Signal:** RSI(14) > trigger (overbought, ready for reversal)
2. **Calculate Swing Low:** Min low of last 5 candles
3. **Wait for Break:** Price breaks below swing low (resistance→support failure)
4. **Place Limit Order:** `swing_low + (limit_offset × ATR)`
5. **Stop Loss:** Swing high from signal bar to break bar (dynamic)
6. **Take Profit:** Fixed % below entry price
7. **Timeout:** Cancel limit if not filled within 20 bars (5 hours)

**Position Sizing:** Risk 5% of equity per trade based on SL distance

---

## 💎 MELANIA-USDT

### Performance (Jun-Dec 2025)
| Metric | Value |
|--------|-------|
| **Total Return** | +1,330.4% |
| **Max Drawdown** | -24.66% |
| **Return/DD Ratio** | **53.96x** 🏆 |
| **Total Trades** | 45 |
| **Win Rate** | 42.2% (19W / 26L) |
| **Avg SL Distance** | 3.02% |
| **Max Consecutive Losses** | ~8-9 |
| **Profitable Months** | 6/7 |

### Parameters
```python
rsi_trigger = 72           # ARM when RSI > 72
lookback = 5               # Swing low lookback period
limit_atr_offset = 0.8     # Limit order offset above swing low
tp_pct = 10.0              # Take profit 10% below entry
max_wait_bars = 20         # Max 20 bars (5 hours) to wait for fill
max_sl_pct = 10.0          # Skip if SL distance > 10%
risk_pct = 5.0             # Risk 5% of equity per trade
```

### Monthly Performance
| Month | P&L | Status |
|-------|-----|--------|
| Jun 2025 | +$62.15 | ✅ |
| Jul 2025 | +$58.53 | ✅ |
| Aug 2025 | +$162.49 | ✅ |
| Sep 2025 | -$41.25 | ❌ ONLY LOSING MONTH |
| Oct 2025 | +$230.49 | ✅ |
| Nov 2025 | +$149.27 | ✅ |
| Dec 2025 | +$708.74 | 🚀 BEST MONTH |

### Key Insights
- **December dominance:** $708.74 profit (53% of total return) in one month
- **September drawdown:** Only losing month at -$41.25
- **High R/R:** 53.96x return/drawdown ratio is exceptional
- **Moderate win rate:** 42.2% but winners are much larger than losers
- **Tight stops:** 3.02% avg SL distance keeps losses small

### Code Location
- **Live Strategy:** `bingx-trading-bot/strategies/melania_short_reversal.py`
- **Backtest Script:** `trading/test_melania_sl_methods.py`
- **Data File:** `trading/melania_6months_bingx.csv` (15m candles)

---

## 🚀 FARTCOIN-USDT

### Performance (Jun-Dec 2025)
| Metric | Value |
|--------|-------|
| **Contribution to Portfolio** | ~30% of total |
| **Total Trades** | 86 |
| **Profitable Months** | 6/7 |

### Parameters
```python
rsi_trigger = 70           # ARM when RSI > 70 (lower threshold)
lookback = 5               # Swing low lookback period
limit_atr_offset = 1.0     # WIDER offset for FARTCOIN (more volatile)
tp_pct = 10.0              # Take profit 10% below entry
max_wait_bars = 20         # Max 20 bars (5 hours) to wait for fill
max_sl_pct = 10.0          # Skip if SL distance > 10%
risk_pct = 5.0             # Risk 5% of equity per trade
```

### Key Insights
- **Lower RSI trigger (70):** FARTCOIN more volatile, reverses earlier
- **Wider limit offset (1.0 ATR):** Allows for larger pullback before entry
- **Same TP (10%):** Keeps consistent target across coins

### Code Location
- **Live Strategy:** `bingx-trading-bot/strategies/fartcoin_short_reversal.py`
- **Data File:** `trading/fartcoin_6months_bingx.csv` (15m candles)

---

## 🐕 DOGE-USDT

### Performance (Jun-Dec 2025)
| Metric | Value |
|--------|-------|
| **Contribution to Portfolio** | $2,993,404 (57.5% of total!) 🏆 |
| **Total Trades** | 79 |
| **Profitable Months** | 5/7 |
| **Best Trade** | +$998,362 (Dec 9) |

### Parameters
```python
rsi_trigger = 72           # ARM when RSI > 72
lookback = 5               # Swing low lookback period
limit_atr_offset = 0.6     # TIGHTER offset for DOGE
tp_pct = 6.0               # TIGHTER TP target (higher win rate)
max_wait_bars = 20         # Max 20 bars (5 hours) to wait for fill
max_sl_pct = 10.0          # Skip if SL distance > 10%
risk_pct = 5.0             # Risk 5% of equity per trade
```

### Key Insights
- **STAR PERFORMER:** 57.5% of portfolio returns!
- **Tightest limit offset (0.6 ATR):** DOGE has cleaner reversals
- **Lowest TP (6%):** Optimized for higher fill rate and win rate
- **Best single trade:** +$998k in December

### Code Location
- **Live Strategy:** `bingx-trading-bot/strategies/doge_short_reversal.py`
- **Data File:** `trading/doge_6months_bingx.csv` (15m candles)

---

## 🦛 MOODENG-USDT

### Performance (Jun-Dec 2025)
| Metric | Value |
|--------|-------|
| **Contribution to Portfolio** | ~10% of total |
| **Total Trades** | 78 |
| **Profitable Months** | 6/7 |

### Parameters
```python
rsi_trigger = 70           # ARM when RSI > 70 (lower threshold)
lookback = 5               # Swing low lookback period
limit_atr_offset = 0.8     # Mid-range offset
tp_pct = 8.0               # Mid-range TP (balance between DOGE 6% and MELANIA 10%)
max_wait_bars = 20         # Max 20 bars (5 hours) to wait for fill
max_sl_pct = 10.0          # Skip if SL distance > 10%
risk_pct = 5.0             # Risk 5% of equity per trade
```

### Key Insights
- **Balanced approach:** Mid-range offset and TP
- **Lower RSI trigger (70):** Similar to FARTCOIN
- **Consistent performer:** 6/7 profitable months

### Code Location
- **Live Strategy:** `bingx-trading-bot/strategies/moodeng_short_reversal.py`
- **Data File:** `trading/moodeng_6months_bingx.csv` (15m candles)

---

## 🎯 PARAMETER OPTIMIZATION INSIGHTS

### RSI Triggers
- **70:** FARTCOIN, MOODENG (more volatile, reverse earlier)
- **72:** MELANIA, DOGE (higher threshold for cleaner signals)

### Limit Offsets
- **0.6 ATR:** DOGE (tightest - cleanest reversals)
- **0.8 ATR:** MELANIA, MOODENG (mid-range)
- **1.0 ATR:** FARTCOIN (widest - most volatile)

### Take Profit Targets
- **6%:** DOGE (tightest - highest win rate)
- **8%:** MOODENG (balanced)
- **10%:** MELANIA, FARTCOIN (wider targets for larger moves)

**General Rule:** More volatile coins (FARTCOIN) need wider offsets and can support wider TPs. Cleaner reversals (DOGE) work better with tighter parameters.

---

## 🚨 IMPORTANT NOTES

1. **All strategies use corrected RSI (Wilder's EMA method)** - see Bug Fixes section
2. **5% risk per trade** - position size calculated from SL distance
3. **Limit orders only** - no market orders (reduces slippage, filters fake breakouts)
4. **20-bar timeout** - prevents stale orders in ranging markets
5. **Dynamic stop loss** - based on swing high, adapts to market structure

---

## 📁 CODE STRUCTURE

```
bingx-trading-bot/
├── strategies/
│   ├── base_strategy.py           # Base class
│   ├── fartcoin_short_reversal.py # FARTCOIN strategy
│   ├── melania_short_reversal.py  # MELANIA strategy
│   ├── doge_short_reversal.py     # DOGE strategy
│   └── moodeng_short_reversal.py  # MOODENG strategy
├── data/
│   ├── indicators.py              # RSI (Wilder's EMA), ATR
│   └── candle_builder.py          # 15m candle aggregation
└── execution/
    ├── signal_generator.py        # Strategy signal routing
    └── bingx_client.py            # BingX API client

trading/
├── melania_6months_bingx.csv      # MELANIA historical data
├── fartcoin_6months_bingx.csv     # FARTCOIN historical data
├── doge_6months_bingx.csv         # DOGE historical data
└── moodeng_6months_bingx.csv      # MOODENG historical data
```

---

## 🔥 PORTFOLIO SUMMARY

**Why These 4 Coins Work Together:**

1. **DOGE:** 57.5% contributor - star performer, cleanest reversals
2. **FARTCOIN:** 30% contributor - volatile, wider targets capture big moves
3. **MELANIA:** Exceptional R/DD (53.96x), highest quality trades
4. **MOODENG:** Consistent diversifier, balanced approach

**Combined Effect:**
- Diversification smooths equity curve
- Different volatility profiles = trades don't overlap perfectly
- $100 → $5.2M in 6 months (backtest with 5% risk)
- Return/DD: 78,973x (indicates exceptional risk-adjusted returns)

**⚠️ Backtest Disclaimer:** These results are from historical backtesting with 5% risk per trade and full compounding. Live trading results may vary due to slippage, API latency, and market conditions.

---
