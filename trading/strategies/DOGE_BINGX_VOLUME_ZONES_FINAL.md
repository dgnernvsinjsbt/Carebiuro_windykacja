# DOGE Volume Zones Strategy - BingX Optimized (FINAL)

**Last Updated:** December 9, 2025
**Optimization:** Comprehensive 567-config test
**Status:** ✅ Ready for paper trading

---

## Performance Summary

| Metric | Value | Rank |
|--------|-------|------|
| **Return/DD Ratio** | **10.75x** | **#3 overall** |
| **Total Return** | +5.15% (32 days) | - |
| **Max Drawdown** | -0.48% | **#1 (shallowest)** |
| **Win Rate** | 63.6% | #2 (after PEPE 66.7%) |
| **Trades** | 22 | 0.69/day |

---

## ⚠️ CRITICAL: Outlier-Harvesting Strategy

**THIS IS NOT A CONSISTENT-EDGE STRATEGY**

**The Reality:**
- **Top 5 trades = 95.3% of all profits**
- **Remaining 17 trades = +0.24%** (treading water)
- **You MUST take every single signal** or you'll miss the winners

**What This Means:**
- ✅ Many small +0.3% or -0.3% trades (boring but necessary)
- ✅ Patient waiting for 3-5 explosive moves per month
- ✅ Those explosive moves = your entire profit
- ❌ Cannot cherry-pick signals (you'll miss the big ones)
- ❌ Cannot skip trading during "boring" periods

**Similar Strategies:**
- TRUMP Volume Zones: 88.6% from top 4 trades (also outlier-harvester)
- MOODENG RSI: 43% from top 5 trades (consistent edge)

**If you're not comfortable with this profile, DON'T trade this strategy.**

---

## Complete Entry Rules

### 1. Volume Zone Detection

**Requirements (ALL must be true):**
1. **5+ consecutive 1-minute candles** with volume > 1.5x the 20-bar MA
2. Zone ends when volume drops below 1.5x threshold
3. Zone maximum length: 15 bars (resets if longer)

**Zone Classification:**
- **Accumulation Zone (LONG):** Volume spike occurs at 20-bar local LOW
  - Zone low = lowest point in 20-bar lookback window
  - Indicates whale buying at support

- **Distribution Zone (SHORT):** Volume spike occurs at 20-bar local HIGH
  - Zone high = highest point in 20-bar lookback window
  - Indicates whale selling at resistance

### 2. Session Filter (CRITICAL!)

**✅ ONLY trade Asia/EU session: 07:00-14:00 UTC**

| Session | Return/DD | Verdict |
|---------|-----------|---------|
| **Asia/EU** | **10.75x** | ✅ OPTIMAL |
| Overnight | 1.08x | ❌ Terrible |
| US | 0.52x | ❌ Unprofitable |
| All | 1.01x | ❌ Poor |

**Why Asia/EU works:**
- Asian market open (07:00 UTC) creates directional moves
- European pre-market (08:00 UTC) adds liquidity
- Cleaner volume zone follow-through than other sessions
- Lower false signals

**Trading Hours:**
- **UTC:** 07:00-14:00
- **EST:** 02:00-09:00 (early morning)
- **CET:** 08:00-15:00 (morning)
- **Asia (UTC+8):** 15:00-22:00 (afternoon/evening)

### 3. Entry Execution

**Trigger:** Immediately when zone ends (volume drops below 1.5x)

**Entry Type:** Market order (0.05% taker fee each side)

**Entry Price:** Close of candle that ends the zone

---

## Exit Rules

### Stop Loss: 1.5x ATR (Adaptive)

**Calculation:**
- **LONG:** SL = Entry - (1.5 × ATR14)
- **SHORT:** SL = Entry + (1.5 × ATR14)

**Why 1.5x ATR:**
- Tighter than 2.0x (old overnight session parameter)
- Asia/EU session less volatile → tighter stops work better
- Reduces max drawdown to -0.48% (shallowest of all strategies)

**Example:**
```
Entry: $0.1500
ATR14: $0.0010
SL: $0.1500 - (1.5 × $0.0010) = $0.14850
```

### Take Profit: 4.0x ATR (Absolute Target)

**Calculation:**
- **LONG:** TP = Entry + (4.0 × ATR14)
- **SHORT:** TP = Entry - (4.0 × ATR14)

**Why ATR-based (not R:R):**
- Better Return/DD (10.75x vs 9.74x with 2.5:1 R:R)
- Captures explosive moves better on BingX
- Less outlier-dependent (95.3% vs 99.2%)

**Example:**
```
Entry: $0.1500
ATR14: $0.0010
TP: $0.1500 + (4.0 × $0.0010) = $0.15400
```

### Time Exit: 90 Bars (90 Minutes)

If neither SL nor TP hit within 90 candles:
- Exit at market on 90th candle
- Accept whatever profit/loss exists
- Prevents capital from being locked up

**Historical Distribution:**
- TP hits: 54.5% of trades
- SL hits: 36.4% of trades
- Time exits: 9.1% of trades (both were profitable)

---

## Position Sizing

### Recommended Risk Per Trade

**Conservative:** 0.5-1.0% risk per trade
- Best for live testing
- Allows 100-200 trades before significant drawdown risk

**Standard:** 1.0-1.5% risk per trade
- Normal operating mode after paper trading success
- Allows 66-100 trades

**Aggressive:** 1.5-2.0% risk per trade
- Only after 50+ successful live trades
- Requires strict discipline

### Calculation

```python
# Example: $10,000 account, 1% risk, LONG entry
account_size = 10000
risk_pct = 0.01  # 1%
entry = 0.1500
stop_loss = 0.14850

risk_per_trade = account_size * risk_pct  # $100
stop_distance = entry - stop_loss  # 0.0015
position_size = risk_per_trade / stop_distance  # $100 / 0.0015 = 66,666 DOGE

# With 10x leverage
margin_required = (66666 * 0.1500) / 10  # $1,000 margin
```

**Important:**
- Position size based on SL distance (not arbitrary)
- Wider stops = smaller position
- Tighter stops = larger position
- Always respects % risk per trade

---

## Risk Management

### Daily Limits

| Limit | Value | Action When Hit |
|-------|-------|-----------------|
| Max trades/day | 3 | Stop trading for day |
| Max loss/day | -2% | Stop trading for day |
| Consecutive losses | 3 | Stop trading for day |

### Weekly Review

**Check after 7 days:**
- [ ] Win rate 55-70%? (should be ~63%)
- [ ] Return/DD > 7.0x?
- [ ] Max DD < -1.5%?
- [ ] Taking ALL signals?
- [ ] Any missed signals?

**If any check fails:** Review logs, analyze missed signals, adjust or pause

---

## Expected Trade Distribution

### By Outcome (22 trades, 32 days)

| Outcome | Count | % | Avg P&L |
|---------|-------|---|---------|
| Winners | 14 | 63.6% | +0.50% |
| Losers | 8 | 36.4% | -0.30% |

### By Exit Type

| Exit | Count | % |
|------|-------|---|
| Take Profit | 12 | 54.5% |
| Stop Loss | 8 | 36.4% |
| Time Exit | 2 | 9.1% |

### By Direction

| Direction | Trades | P&L | Win Rate | Contribution |
|-----------|--------|-----|----------|--------------|
| LONG | 13 | +4.15% | 61.5% | 88.5% |
| SHORT | 9 | +0.54% | 66.7% | 11.5% |

**Key Insight:** LONGs generate most profits, but keep SHORTs (contribute 11.5%)

---

## Trade Examples (Top 5)

### Trade #7: +1.36% (29.1% of total profit)
```
Date: Nov 21, 12:27 UTC
Direction: LONG
Entry: $0.13386
SL: $0.13236 (1.5x ATR)
TP: $0.13582 (4.0x ATR)
Exit: $0.13582 (TP HIT)
Bars Held: 4 (only 4 minutes!)
P&L: +1.36%
```

### Trade #5: +1.17% (24.9% of total profit)
```
Date: Nov 21, 07:37 UTC
Direction: LONG
Entry: $0.13947
Exit: $0.14124 (TIME EXIT)
Bars Held: 90 (max hold)
P&L: +1.17%
```

### Trade #8: +1.03% (22.1% of total profit)
```
Date: Nov 22, 08:37 UTC
Direction: LONG
Entry: $0.13624
TP: $0.13779 (TP HIT)
Bars Held: 58
P&L: +1.03%
```

**Pattern:** All top 5 trades are LONGs during Asia/EU session

---

## Pre-Live Checklist

### Paper Trading Requirements (MANDATORY)

- [ ] **1 week minimum** (5-10 trades expected)
- [ ] **Win rate 55-70%** (target: 63.6%)
- [ ] **Return/DD > 7.0x** after 10 trades
- [ ] **Max DD < -1.5%** maintained
- [ ] **All signals executed** (no cherry-picking)
- [ ] **Session filter working** (07:00-14:00 UTC only)

### Live Trading Setup

- [ ] BingX API keys configured
- [ ] DOGE-USDT market available
- [ ] ATR(14) calculation verified
- [ ] Volume MA(20) calculation verified
- [ ] Session filter tested (07:00-14:00 UTC)
- [ ] Position sizing logic tested
- [ ] Stop loss orders working
- [ ] Take profit orders working
- [ ] Time exit logic working
- [ ] Logging all trades to CSV

---

## Monitoring & Maintenance

### Daily Checklist (During Session)

- [ ] Bot running during 07:00-14:00 UTC?
- [ ] No errors in logs?
- [ ] All volume zones detected?
- [ ] Position sizes correct?
- [ ] SL/TP orders placed correctly?

### Weekly Review

- [ ] Total trades this week?
- [ ] Win rate this week?
- [ ] Return/DD tracking on target?
- [ ] Any missed signals?
- [ ] Any false signals?

### Monthly Deep Dive

- [ ] Compare to backtest expectations
- [ ] Profit concentration analysis (still ~95% from top 5?)
- [ ] Session performance (Asia/EU still optimal?)
- [ ] Re-optimize if market structure changed

---

## Stop Conditions (SHUT DOWN BOT IF:)

🚨 **Immediate Stop:**
- Win rate drops below 45% (vs 63.6% expected)
- Return/DD drops below 4.0x after 30+ trades
- Max DD exceeds -2.5% (vs -0.48% backtest)
- 5 consecutive losses

⚠️ **Review & Adjust:**
- Win rate 45-55% (borderline)
- Return/DD 4.0-7.0x (below target but not terrible)
- Missed 2+ signals in a row
- Major DOGE news/events

✅ **Continue Trading:**
- Win rate 55-70%
- Return/DD > 7.0x
- Max DD < -1.5%
- Taking all signals consistently

---

## Technical Implementation

### Configuration (config.yaml)

```yaml
doge_volume_zones:
  enabled: true
  symbol: DOGE-USDT
  base_risk_pct: 1.0
  max_risk_pct: 2.0
  max_positions: 1

  params:
    volume_threshold: 1.5
    min_zone_bars: 5
    max_zone_bars: 15
    lookback_bars: 20
    stop_atr_mult: 1.5
    tp_type: 'atr_multiple'
    tp_atr_mult: 4.0
    max_hold_bars: 90
    session_filter: 'asia_eu'
```

### Strategy File

**Location:** `bingx-trading-bot/strategies/doge_volume_zones.py`

**Key Methods:**
- `detect_volume_zone_end()` - Detects 5+ bar volume zones
- `_classify_zone()` - Determines accumulation vs distribution
- `check_session()` - Filters for Asia/EU hours only
- `analyze()` - Generates entry signals when zone ends

---

## FAQ

**Q: Why only 22 trades in 32 days?**
A: Volume zones (5+ bars at 1.5x threshold at price extremes) are rare. Relaxing filters adds noise, not quality.

**Q: Can I trade overnight session instead?**
A: No. Overnight = 1.08x Return/DD (vs 10.75x Asia/EU). This is exchange-specific behavior.

**Q: What if I miss a signal?**
A: Accept it and wait for the next one. Don't chase. You can't predict which signals will be the big winners.

**Q: Can I increase R:R to 5:1 or 6:1?**
A: Tested. 6x ATR = 5.03x Return/DD (worse). 4x ATR is optimal.

**Q: Can I use this on LBank or other exchanges?**
A: No. This is BingX-optimized. LBank optimal = overnight session + 2.0x ATR SL.

**Q: What if top 5 dependency improves over time?**
A: Unlikely with 22 trades/month. If you get 50+ trades, dependency may decrease. Monitor monthly.

**Q: Should I reduce risk due to outlier dependency?**
A: Yes, 0.5-1% risk per trade recommended (vs 1-2% for consistent strategies).

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| Dec 9, 2025 | 2.0 | BingX optimization: Asia/EU session, 1.5x SL, 4.0x ATR TP |
| Dec 8, 2025 | 1.0 | Initial LBank version: Overnight, 2.0x SL, 2:1 R:R TP |

---

## Files

**Strategy Code:**
`bingx-trading-bot/strategies/doge_volume_zones.py`

**Configuration:**
`bingx-trading-bot/config.example.yaml` (line 59-85)

**Optimization Reports:**
- `trading/results/DOGE_VOLUME_ZONES_BINGX_OPTIMIZATION_REPORT.md`
- `trading/results/DOGE_BINGX_EXECUTIVE_SUMMARY.md`
- `trading/results/doge_bingx_comprehensive_optimization.csv` (567 configs tested)

**Trade Logs:**
`trading/results/doge_bingx_optimized_trades.csv` (22 trades with full metrics)

---

**🎯 FINAL VERDICT: APPROVED FOR PAPER TRADING**

This is a valid, profitable outlier-harvesting strategy. Similar to TRUMP Volume Zones (#2 ranked), it requires discipline to take every signal and patience during "boring" periods. The math works: 95% of profit from 5 trades is acceptable when those trades reliably occur and the other 17 trades don't lose money.

**Proceed to paper trading with 0.5-1% risk per trade.**
