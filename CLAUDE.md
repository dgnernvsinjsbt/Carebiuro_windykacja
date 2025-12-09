CLAUDE.md — Best Practices for Fiscal Development

---

# 🤖 BINGX TRADING BOT - FARTCOIN STRATEGIES (MEMORIZE THIS!)

## 🚀 INSTANT STARTUP - NO 4-HOUR WAIT

**Historical Data Warmup (December 2025)**

The bot now downloads the last 300 candles on startup instead of waiting 4 hours to accumulate them from live WebSocket:

- **Before**: 4-hour warmup required (250+ candles accumulated from live feed)
- **After**: <10 seconds warmup (300 candles fetched from BingX REST API)
- **Method**: `MultiTimeframeCandleManager.warmup_from_history()`
- **Location**: [data/candle_builder.py:320](bingx-trading-bot/data/candle_builder.py#L320)
- **Trigger**: Automatically runs on startup in [main.py:441](bingx-trading-bot/main.py#L441)

Benefits:
- ✅ Restarts/rebuilds no longer wipe progress
- ✅ Can deploy updates without losing 4 hours
- ✅ Indicators calculated immediately from historical data
- ✅ Bot starts trading within seconds of launch

---

## 📐 KEY METRIC DEFINITION

**R:R Ratio = Total Return ÷ Max Drawdown**

This is the PRIMARY metric for ranking strategies. It measures how much profit you make relative to the worst loss you experienced.

```
Example: MOODENG RSI
- Return: +24.02%
- Max Drawdown: -2.25%
- R:R = 24.02 ÷ 2.25 = 10.68x
```

**ALWAYS use this definition when discussing R:R.** Do NOT confuse with trade-level TP/SL ratios.

Higher R:R = Better risk-adjusted performance.

---

## Strategy 1: Multi-Timeframe LONG
| Metric | Value |
|--------|-------|
| **R:R Ratio** | **7.14x** |
| **Return** | +10.38% |
| **Max Drawdown** | -1.45% |
| Direction | LONG |
| Timeframe | 1-min entry + 5-min confirmation |

**Entry:**
- Explosive Bullish Breakout on 1-min (body >1.2%, volume >3x, minimal wicks)
- 5-min uptrend: Close > SMA50, RSI > 57, distance > 0.6% above SMA
- RSI 45-75, high volatility required

**Exits:**
- Stop Loss: 3x ATR below entry
- Take Profit: 12x ATR above entry

---

## Strategy 2: Trend Distance SHORT
| Metric | Value |
|--------|-------|
| **R:R Ratio** | **8.88x** |
| **Return** | +20.08% |
| **Max Drawdown** | -2.26% |
| Direction | SHORT |
| Timeframe | 1-min |

**Entry:**
- Price below BOTH 50 and 200 SMA (strong downtrend)
- At least **2% distance** below 50 SMA
- Explosive Bearish Breakdown (body >1.2%, volume >3x, minimal wicks)
- RSI 25-55

**Exits:**
- Stop Loss: 3x ATR above entry
- Take Profit: 15x ATR below entry

---

## Strategy 3: MOODENG RSI Momentum LONG
| Metric | Value |
|--------|-------|
| **R:R Ratio** | **5.75x** |
| **Return** | +24.02% (30 days) |
| **Max Drawdown** | -2.25% |
| **Win Rate** | 31% |
| **Trades** | 129 |
| Direction | LONG |
| Timeframe | 1-min |

**Entry (ALL conditions must be true):**
- RSI(14) crosses ABOVE 55 (previous candle < 55, current >= 55)
- Bullish candle with body > 0.5%
- Price ABOVE SMA(20)

**Exits:**
- Stop Loss: 1.0x ATR(14) below entry
- Take Profit: 4.0x ATR(14) above entry
- Time Exit: 60 bars (60 minutes) if neither SL/TP hit

**Fees:** 0.10% per trade (BingX Futures taker 0.05% x2)

**Audit Notes (Dec 2025):**
- Verified NO backtest artifacts - all trades replicable in live trading
- Dec 6-7 pump (+185%) captured correctly with 16 trades
- Top 20% concentration: 43% (borderline consistent)
- Strategy catches momentum breakouts - requires patience for big moves

**Data File:** `trading/moodeng_usdt_1m_lbank.csv` (43,201 candles, 30 days)
**Code:** `trading/moodeng_optimize_rsi.py`
**Trade Log:** `trading/results/moodeng_audit_trades.csv`

---

## Strategy 4: DOGE Mean Reversion LONG (Best R:R)
| Metric | Value |
|--------|-------|
| **R:R Ratio** | **4.55x** |
| **Return** | +7.64% |
| **Max Drawdown** | -2.93% |
| **Win Rate** | 28.6% |
| **Trades** | 28 |
| Direction | LONG |
| Timeframe | 1-min |
| Avg Trade Duration | 33 minutes |

**Entry (ALL conditions must be true):**
- Price < **1% below SMA(20)** (deviation filter)
- **4 consecutive down bars** (exhaustion signal)
- Place **limit order** at current_price × 0.99965 (0.035% below for better fill)

**Exits:**
- Stop Loss: **1.0x ATR(14)** below entry (tight stop)
- Take Profit: **6.0x ATR(14)** above entry (wide target)

**Fees:** 0.07% round-trip (limit orders: 0.02% maker + 0.05% taker)

**Why It Works:**
- DOGE mean reverts after exhaustion moves (autocorrelation slightly negative)
- Tight SL (1x ATR) = small losses when wrong
- Wide TP (6x ATR) = big winners when right
- Math: 28.6% × 6.0 - 71.4% × 1.0 = +1.00 expectancy per trade
- Pattern discovered through data analysis, not generic indicators

**Alternative Configs:**
| Config | SL | TP | Return | Win Rate | R:R |
|--------|----|----|--------|----------|-----|
| Best Return | 2.0x | 6.0x | +14.72% | 46.2% | 2.67 |
| Best R:R | 1.0x | 6.0x | +7.64% | 28.6% | 4.55 |
| Best Win Rate | 1.5x | 3.0x | +7.12% | 71.4% | 1.51 |
| Balanced | 1.5x | 6.0x | +9.65% | 37.0% | 3.20 |

**Data File:** `trading/doge_usdt_1m_lbank.csv` (43,201 candles, 30 days)
**Code:** `trading/doge_optimized_strategy.py`, `trading/doge_final_optimized.py`
**Full Report:** `trading/results/DOGE_OPTIMIZATION_EXECUTIVE_SUMMARY.md`

---

## Quick Reference Table (Ranked by Return/DD Ratio - Most Important!)
| Rank | Strategy | Return/DD | Return | Max DD | R:R | Token |
|------|----------|-----------|--------|--------|-----|-------|
| 🥇 | **MOODENG RSI** | **10.68x** | **+24.02%** | **-2.25%** | 5.75x | MOODENG |
| 🥈 | **TRUMP Volume Zones** ⚠️ | **10.56x** | **+8.06%** | **-0.76%** | 4.00x | TRUMP |
| 🥉 | **DOGE BingX Zones** ⚠️ | **10.75x** | **+5.15%** | **-0.48%** | 10.75x | DOGE |
| 4 | **FARTCOIN SHORT** | **8.88x** | **+20.08%** | **-2.26%** | 8.88x | FARTCOIN |
| 5 | **FARTCOIN LONG** | **7.16x** | **+10.38%** | **-1.45%** | 7.14x | FARTCOIN |
| 6 | **PEPE Volume Zones** | **6.80x** | **+2.57%** | **-0.38%** | 2.00x | PEPE |
| 7 | PENGU Volume Zones | 4.35x | +17.39% | -4.00% | 1.90x | PENGU |
| 8 | ETH BB3 STD | 4.10x | +15.43% | -3.76% | 2.22x | ETH |
| 9 | ETH Volume Zones | 3.60x | +3.78% | -1.05% | 2.00x | ETH |
| 10 | DOGE Mean Reversion | 2.61x | +7.64% | -2.93% | 4.55x | DOGE |

**Legend:** ⚠️ = Outlier-dependent (requires discipline to take all signals)

**⭐ NEW:** DOGE BingX Zones optimized Dec 9, 2025 - now ranks #3!

**Code Location:** `bingx-trading-bot/strategies/`
- `multi_timeframe_long.py`
- `trend_distance_short.py`

**Data Source (for quick lookup):**
- Full calculations: `bingx-trading-bot/calculate_real_pnl_with_leverage.py`
- Strategy implementations: `bingx-trading-bot/strategies/`
- Backtest results: `trading/explosive-v7-advanced.py`, `trading/multi-timeframe-long-v7.py`
- MOODENG optimization: `trading/moodeng_optimize_rsi.py`
- DOGE optimization: `trading/results/DOGE_OPTIMIZATION_EXECUTIVE_SUMMARY.md`
- DOGE Volume Zones: `trading/results/DOGE_VOLUME_ZONES_OPTIMIZATION_REPORT.md`

---

## Strategy 5: DOGE Volume Zones (BingX Optimized - Outlier Harvester)
| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **10.75x** ⭐ |
| **Return** | +5.15% (32 days BingX) |
| **Max Drawdown** | **-0.48%** (shallowest!) |
| **Win Rate** | 63.6% |
| **Trades** | 22 |
| **Actual R:R** | 4.0x ATR TP / 1.5x ATR SL |
| Direction | LONG + SHORT |
| Timeframe | 1-min |
| **⚠️ Outlier Dependency** | **95.3%** from top 5 trades |

**Entry (Accumulation Zones for LONG):**
- Detect 5+ consecutive bars with volume > 1.5x average
- Zone must be at local low (20-bar lookback)
- Enter **Asia/EU session (07:00-14:00 UTC) ONLY** ⚠️
- Market order (0.05% taker fee)

**Entry (Distribution Zones for SHORT):**
- Detect 5+ consecutive bars with volume > 1.5x average
- Zone must be at local high (20-bar lookback)
- Enter **Asia/EU session (07:00-14:00 UTC) ONLY** ⚠️
- Market order (0.05% taker fee)

**Exits:**
- Stop Loss: **1.5x ATR(14)** (tighter for lower volatility session)
- Take Profit: **4.0x ATR** (absolute ATR target, not R:R)
- Max Hold: 90 bars (90 minutes)

**Fees:** 0.10% per trade (0.05% taker x2)

**Why It Works (But Differently):**
- **CRITICAL:** This is an outlier-harvesting strategy like TRUMP Volume Zones
- Top 5 trades = 95.3% of all profits (remaining 17 = +0.24%)
- Must take EVERY signal - cannot cherry-pick
- Asia/EU session has cleaner volume zone follow-through on BingX
- ATR-based TP (4.0x) captures explosive moves better than R:R
- LONGs contribute 88.5% of profits (keep SHORTs for 11.5%)

**Session Analysis (BingX vs LBank):**
| Exchange | Session | Return/DD | Notes |
|----------|---------|-----------|-------|
| **BingX** | **Asia/EU (07-14)** | **10.75x** | ⭐ OPTIMAL |
| BingX | Overnight (21-07) | 1.08x | Fails on BingX |
| LBank | Overnight (21-07) | 7.15x | Optimal on LBank |

**⚠️ Exchange-Specific Behavior:** Parameters don't transfer between exchanges!

**Configuration (BingX Optimized):**
```python
{
    'volume_threshold': 1.5,      # 1.5x average volume
    'min_zone_bars': 5,           # 5+ consecutive bars
    'sl_type': 'atr',
    'sl_value': 1.5,              # 1.5x ATR stop (tighter)
    'tp_type': 'atr_multiple',    # ATR-based (not R:R!)
    'tp_value': 4.0,              # 4.0x ATR target
    'session': 'asia_eu',         # 07:00-14:00 UTC ONLY
    'max_hold_bars': 90           # 90 minute max hold
}
```

**Data File:** `trading/doge_30d_bingx.csv` (46,080 candles, 32 days)
**Code:** `trading/doge_bingx_comprehensive_optimizer.py` (567 configs tested)
**Full Report:** `trading/strategies/DOGE_BINGX_VOLUME_ZONES_FINAL.md`
**Trades:** `trading/results/doge_bingx_optimized_trades.csv` (22 trades)

**Key Discovery:**
- Comprehensive re-optimization with ATR-based TP + relaxed filters
- NO configuration with Return/DD > 5.0x has Top5 < 80% (fundamental to DOGE)
- Strategy works by catching 3-5 explosive moves per month
- Remaining trades tread water (+0.24% from 17 trades)

---

## Strategy 6: PENGU Volume Zones
| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **4.35x** |
| **Return** | +17.39% (30 days) |
| **Max Drawdown** | -4.00% |
| **Win Rate** | 50.0% |
| **Trades** | 100 |
| **Actual R:R** | 1.90:1 |
| Direction | LONG + SHORT |
| Timeframe | 1-min |

**Entry (Accumulation Zones for LONG):**
- Detect 5+ consecutive bars with volume > 1.3x average
- Zone must be at local low (20-bar lookback)
- Enter on breakout after zone ends

**Entry (Distribution Zones for SHORT):**
- Detect 5+ consecutive bars with volume > 1.3x average
- Zone must be at local high (20-bar lookback)
- Enter on breakdown after zone ends

**Exits:**
- Stop Loss: 1.0x ATR(14) below/above entry
- Take Profit: 3.0x ATR(14) in direction
- Time Exit: 30 bars if neither SL/TP hit

**Fees:** 0.10% per trade (0.05% x2 taker fees)

**Why It Works:**
- PENGU is 91.76% choppy - generic strategies fail
- Sustained volume (5+ bars) = real whale accumulation/distribution
- Single-candle volume spikes = retail noise (tested and failed)
- Strategy catches the rare 1.22% trending regime when whales act

**Configuration:**
- volume_threshold = 1.3x
- min_zone_bars = 5
- sl_atr_mult = 1.0x
- rr_ratio = 3.0:1
- session = 'all' (24/7)

**Data File:** `trading/pengu_usdt_1m_lbank.csv` (43,200 candles, 30 days)
**Code:** `trading/pengu_volume_zones_optimizer.py`
**Results:** `trading/results/PENGU_volume_zones_optimization.csv`

**Key Discovery:**
- Failed approaches: Chart patterns (-12.33%), single volume spikes (-155%)
- Breakthrough: Multi-bar volume zones at price extremes = +17.39%
- User's trading experience hypothesis validated!

---

## Strategy 7: ETH BB3 STD (Best Spot Strategy)
| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **4.10x** |
| **Return** | +15.43% (30 days) |
| **Max Drawdown** | -3.76% |
| **Win Rate** | 43.8% |
| **Trades** | 121 |
| **Actual R:R** | 2.22:1 |
| Direction | LONG only |
| Timeframe | 1-min |

**Entry:**
- Price < Bollinger Band Lower (20 period, 3 STD)
- Place LIMIT order 0.035% below signal price

**Exits:**
- Stop Loss: 2.0x ATR below entry
- Take Profit: 4.0x ATR above entry

**Fees:** 0.07% round-trip (limit orders: 0.02% maker + 0.05% taker)

**Why It Works:**
- 3 STD is extreme (~0.3% probability), strong mean reversion
- High quality entries (121 trades vs 700+ for failed strategies)
- Limit orders crucial: +5.54% net vs +2.44% with market orders

**Data File:** `trading/results/bb3_std_all_trades.csv`
**Code:** `trading/eth_lowfreq_strats.py`
**Full Report:** `trading/BEST_SPOT_STRATEGY.md`

---

## Strategy 8: ETH Volume Zones (US Session Only)
| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **3.60x** |
| **Return** | +3.78% (30 days) |
| **Max Drawdown** | -1.05% |
| **Win Rate** | 52.9% |
| **Trades** | 17 |
| **Actual R:R** | 2.00:1 |
| Direction | LONG + SHORT |
| Timeframe | 1-min |

**Entry (Accumulation Zones for LONG):**
- Detect 5+ consecutive bars with volume > 1.5x average
- Zone must be at local low (20-bar lookback)
- Enter US session (14:00-21:00 UTC) only

**Entry (Distribution Zones for SHORT):**
- Detect 5+ consecutive bars with volume > 1.5x average
- Zone must be at local high (20-bar lookback)
- Enter US session (14:00-21:00 UTC) only

**Exits:**
- Stop Loss: **1.5x ATR** below/above entry
- Take Profit: **2:1 R:R** (adaptive based on ATR)
- Max Hold: 90 bars (90 minutes)

**Fees:** 0.10% per trade (0.05% x2 taker fees)

**Why It Works:**
- ETH has clearer volume zone follow-through during US trading hours
- ATR-based stops adapt to ETH's volatility (unlike fixed % for TRUMP)
- Tighter 2:1 R:R hits 53% of the time (vs 4:1 only hitting 11%)
- Both directions profitable when properly configured

**Configuration Differences from TRUMP:**
- **Stop:** 1.5x ATR (not 0.5% fixed) - ETH needs volatility-adaptive stops
- **Target:** 2:1 R:R (not 4:1) - ETH doesn't trend as far
- **Session:** US hours (not overnight) - Different liquidity profile
- **Direction:** Both work (not LONGS only)

**Configuration:**
```python
{
    'volume_threshold': 1.5,      # 1.5x average volume
    'min_zone_bars': 5,           # 5+ consecutive bars
    'sl_type': 'atr',
    'sl_value': 1.5,              # 1.5x ATR stop
    'tp_type': 'rr_multiple',
    'tp_value': 2.0,              # 2:1 R:R
    'session': 'us',              # 14:00-21:00 UTC only
    'max_hold_bars': 90           # 90 minute max hold
}
```

**Data File:** `trading/eth_usdt_1m_lbank.csv` (43,201 candles, 30 days)
**Code:**
- `trading/eth_volume_zones_optimize.py` (optimization across 200 configs)
**Results:**
- `trading/results/ETH_volume_zones_optimized_trades.csv`

**Key Discovery:**
- TRUMP's config completely failed on ETH (-2.77%, 0.40x R/DD)
- ETH-specific optimization found profitable setup (+3.78%, 3.60x R/DD)
- Different tokens need different parameters (session, R:R, stop type)

---

## Strategy 9: TRUMP Volume Zones ⚠️ (Outlier-Dependent but Highest R/DD!)
| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **10.56x** |
| **Return** | +8.06% (30 days) |
| **Max Drawdown** | -0.76% |
| **Win Rate** | 61.9% |
| **Trades** | 21 |
| **Actual R:R** | 4.00:1 |
| Direction | LONG + SHORT |
| Timeframe | 1-min |

**Entry (Accumulation Zones for LONG):**
- Detect 5+ consecutive bars with volume > 1.5x average
- Zone must be at local low (20-bar lookback)
- Enter overnight session (21:00-07:00 UTC) only

**Entry (Distribution Zones for SHORT):**
- Detect 5+ consecutive bars with volume > 1.5x average
- Zone must be at local high (20-bar lookback)
- Enter overnight session (21:00-07:00 UTC) only

**Exits:**
- Stop Loss: **0.5% fixed** below/above entry
- Take Profit: **4:1 R:R** (2.0% target)
- Max Hold: 90 bars (90 minutes)

**Fees:** 0.10% per trade (0.05% x2 taker fees)

**⚠️ OUTLIER-DEPENDENCY WARNING:**
- **Top 20% concentration: 88.6%** (top 4 trades generate most profit)
- **Top 2 trades alone: 47.2%** of total profit
- Winners consistent (CV 0.72), but **you MUST catch the big moves**
- Zero losing streaks (max 0 consecutive losses) = psychologically smooth
- Best trade contributes 23.6% (acceptable single-trade dependency)

**Why It Works:**
- TRUMP is choppy, but overnight session has clearer volume zones
- Sustained volume (5+ bars) = real whale accumulation/distribution
- 4:1 R:R means accepting many -0.60% losses for few +1.90% winners
- High 61.9% win rate helps offset outlier dependency
- Math: Need to take ALL signals or you'll miss the winners

**Trading Requirements:**
- **Discipline to take every signal** (can't cherry-pick)
- **Patience during small loss periods** (many -0.60% stops)
- **Understanding that 4-5 trades make most profit** (normal for high R:R)

**Configuration:**
```python
{
    'volume_threshold': 1.5,      # 1.5x average volume
    'min_zone_bars': 5,           # 5+ consecutive bars
    'sl_type': 'fixed_pct',
    'sl_value': 0.5,              # 0.5% fixed stop
    'tp_type': 'rr_multiple',
    'tp_value': 4.0,              # 4:1 R:R
    'session': 'overnight',       # 21:00-07:00 UTC only
    'max_hold_bars': 90           # 90 minute max hold
}
```

**Data File:** `trading/trump_usdt_1m_mexc.csv` (43,202 candles, 30 days)
**Code:**
- `trading/trump_volume_zones.py` (parameter search)
- `trading/trump_volume_zones_optimize.py` (full optimization)
- `trading/trump_volume_zones_best_riskadj.py` (best R/DD config)
**Analysis:**
- `trading/trump_volume_zones_outlier_analysis.py` (consistency check)
- `trading/results/TRUMP_volume_zones_best_riskadj_trades.csv`

**Key Discovery:**
- Failed approaches: Scalping (-0.59%), Mean-Reversion (-2.91%), Chart Patterns (-1.05%)
- Breakthrough: Volume zones with overnight filter + 4:1 R:R = +8.06% with 10.56x R/DD
- Trade-off: Best risk-adjusted returns but requires catching outlier winners

---

## Strategy 10: PEPE Volume Zones (Shallowest Drawdown!)
| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **6.80x** |
| **Return** | +2.57% (30 days) |
| **Max Drawdown** | -0.38% |
| **Win Rate** | 66.7% |
| **Trades** | 15 |
| **Actual R:R** | 2.00:1 |
| Direction | LONG + SHORT |
| Timeframe | 1-min |

**Entry (Accumulation Zones for LONG):**
- Detect 5+ consecutive bars with volume > 1.5x average
- Zone must be at local low (20-bar lookback)
- Enter overnight session (21:00-07:00 UTC) only
- Enter on breakout after zone ends

**Entry (Distribution Zones for SHORT):**
- Detect 5+ consecutive bars with volume > 1.5x average
- Zone must be at local high (20-bar lookback)
- Enter overnight session (21:00-07:00 UTC) only
- Enter on breakdown after zone ends

**Exits:**
- Stop Loss: **1.0x ATR** below/above entry
- Take Profit: **2:1 R:R** (adaptive based on ATR)
- Max Hold: 90 bars (90 minutes)

**Fees:** 0.10% per trade (0.05% x2 taker fees)

**Why It Works:**
- **Highest win rate** (66.7%) among volume zone strategies
- **Shallowest drawdown** (-0.38%) of ALL strategies - extremely smooth equity curve
- PEPE responds strongly to sustained volume accumulation/distribution
- Overnight session filters out choppy Asian/EU session noise
- Only 33.3% stopped out (10 TPs hit out of 15 trades)

**Key Advantages:**
- **Risk Management Excellence**: -0.38% max DD = minimal psychological stress
- **High Consistency**: 2 out of 3 trades hit TP
- **Capital Efficient**: Tight stops (1.0x ATR) with good follow-through
- **Session-Filtered**: Overnight liquidity creates cleaner setups

**Configuration:**
```python
{
    'volume_threshold': 1.5,      # 1.5x average volume
    'min_zone_bars': 5,           # 5+ consecutive bars
    'sl_type': 'atr',
    'sl_value': 1.0,              # 1.0x ATR stop (tighter than ETH)
    'tp_type': 'rr_multiple',
    'tp_value': 2.0,              # 2:1 R:R
    'session': 'overnight',       # 21:00-07:00 UTC only
    'max_hold_bars': 90           # 90 minute max hold
}
```

**Data File:** `trading/pepe_usdt_1m_lbank.csv` (43,201 candles, 30 days)
**Code:**
- `trading/pepe_volume_zones_optimize.py` (96 configurations tested)
**Results:**
- `trading/results/PEPE_volume_zones_optimized_trades.csv`

**Comparison to Other Volume Zone Strategies:**
| Token | Return/DD | Max DD | Win Rate | Session | SL Type | R:R |
|-------|-----------|--------|----------|---------|---------|-----|
| TRUMP | 10.56x | -0.76% | 61.9% | Overnight | Fixed 0.5% | 4:1 |
| PEPE | 6.80x | **-0.38%** | **66.7%** | Overnight | 1.0x ATR | 2:1 |
| ETH | 3.60x | -1.05% | 52.9% | US | 1.5x ATR | 2:1 |
| PENGU | 4.35x | -4.00% | 50.0% | All | 1.0x ATR | 3:1 |

**Key Discovery:**
- PEPE has the **smoothest equity curve** (-0.38% DD)
- PEPE has the **highest win rate** (66.7%)
- Lower Return/DD than TRUMP, but much more consistent and less stressful to trade
- Perfect for traders who prioritize psychological comfort over max returns

---

## ✅ TRUMP/USDT - FAILED APPROACHES (For Reference)

### Generic Strategies ALL Failed
| Approach | Best Config | Return | Win Rate | Trades |
|----------|-------------|--------|----------|--------|
| Scalping | Momentum Wide R:R (1:3) | **-0.59%** | 27.5% | 160 |
| Mean-Reversion | RSI < 20 | -2.91% | 39.1% | 64 |
| Chart Patterns Filtered | Double Top + HTF | -1.05% | 44.4% | 18 |

### Why TRUMP Generic Strategies Fail

1. **Ultra-low volatility**: 0.12% avg candle range (too small for generic indicators)
2. **Choppy price action**: No clean directional moves
3. **Win rates too low**: 27-39% across scalping/mean-reversion
4. **Fees eat the edge**: 0.1% round-trip kills marginal setups

### Lesson Learned
- Pattern analysis recommended Scalping over Mean-Reversion
- Scalping loses 4x less (-0.59% vs -2.91%) but still unprofitable
- Chart patterns with filters reduced over-trading (18 trades vs 1,336) but still lost
- **Breakthrough came from volume zone analysis** (adapted from PENGU)
- **"Best generic approach" ≠ "Profitable approach"**

**Failed Approach Files:**
- `trading/trump_scalping_strategy.py`
- `trading/trump_pattern_reversals.py`
- `trading/trump_pattern_filtered.py`
- `trading/results/TRUMP_OPTIMIZATION_REPORT.md`

---

## ✅ PENGU/USDT - BREAKTHROUGH WITH VOLUME ZONES!

**VERDICT: NOW TRADEABLE with Volume Zones Strategy (+17.39%)**

### Failed Approaches (Generic Strategies)
| Approach | Best Config | Return | Win Rate | Trades |
|----------|-------------|--------|----------|--------|
| Mean-Reversion | BB + RSI < 25 | **-15.38%** | 39.0% | 59 |
| Exhaustion Bounce | 4 down bars | **-12.33%** | 21.3% | 89 |
| Fade SMA20 Breakdown | RSI 25-45 | -80.60% | 40.1% | 680 |
| Range Trading | Buy low/sell mid | -121.18% | 27.8% | 1,067 |
| Grid Trading | 10 levels | **FAKE +95%** | 100% | 14 (7 stuck) |

### ✅ Successful Approach (Volume Zones)
| Approach | Config | Return | Win Rate | Return/DD |
|----------|--------|--------|----------|-----------|
| **Volume Zones** | **1.3x, 5 bars, 1.0x ATR, 3:1 R:R** | **+17.39%** | **50.0%** | **4.35x** |

### Why PENGU Fails (6 Strategies Tested - ALL Lost Money)

1. **Extreme choppiness**: 91.76% of time in choppy regime (only 1.22% trending)
2. **Mean-reversion fails**: Even though recommended, stops get hit constantly
3. **SMA breakouts FADE 78%**: But fading them ALSO loses money
4. **-22% price drift**: Downtrend kills longs, grid positions get stuck underwater
5. **Fees eat micro-edges**: 0.1% round-trip destroys any small statistical edge

### Strategies Tested (All Failed)
| Strategy | Return | Win Rate | Issue |
|----------|--------|----------|-------|
| Fade SMA20 Breakdown | -80.60% | 40.1% | Chop eats stops |
| Range Trading | -121.18% | 27.8% | Range breaks down |
| 21:00 UTC Scalping | -2.30% | 0% | Too few signals |
| Exhaustion Bounce | -12.33% | 21.3% | Bounces fail |
| BB Squeeze Breakout | -22.77% | 31.7% | Breakouts fail |
| Grid Trading | -14 (real) | 100% | 7 positions stuck -20% to -30% |

### Grid Trading Reality Check
- **Closed trades:** +$116 realized
- **Open positions:** -$130 unrealized (7 stuck underwater)
- **ACTUAL TOTAL:** -$14 loss
- Grid trading only "works" if you ignore stuck positions

### PENGU Personality Profile
- **Regime:** 91.76% choppy, 3.99% mean-reverting, 1.22% trending
- **Momentum:** Mean-reverting (38% follow-through only)
- **Best session:** US 14:00-21:00 UTC (36% long WR - still loses)
- **Best hour:** 21:00 UTC (+0.0077% avg - not enough for fees)

### Lesson Learned
- Pattern analysis correctly identified mean-reversion as best approach
- But "best approach" on a bad asset is STILL a losing strategy
- 91.76% choppy regime = no clean entries, constant stop-outs
- **Some tokens simply cannot be traded profitably on 1m timeframe**

**Data File:** `trading/pengu_usdt_1m_lbank.csv` (43,200 candles, 30 days)
**Analysis Reports:**
- `trading/results/PENGU_PATTERN_ANALYSIS.md`
- `trading/results/PENGU_strategy_summary.md`
- `trading/pattern_discovery_PENGU.py`
**Code:** `trading/strategies/PENGU_strategy_final.py`

---

⚡ CRITICAL: Supabase Database Management

**ZAWSZE używaj Supabase CLI do zarządzania bazą danych, NIE proś użytkownika o wklejanie SQL.**

Dostępne komendy:
- `SUPABASE_ACCESS_TOKEN="sbp_488bb6b5a6b6e2b652b28c6c736776023117c461" npx supabase gen types typescript --linked` - generuj TypeScript types (sprawdzaj strukturę tabel)
- `SUPABASE_ACCESS_TOKEN="sbp_488bb6b5a6b6e2b652b28c6c736776023117c461" npx supabase inspect db table-stats --linked` - statystyki tabel
- `SUPABASE_ACCESS_TOKEN="sbp_488bb6b5a6b6e2b652b28c6c736776023117c461" npx supabase migration new nazwa_migracji` - stwórz nową migrację
- `SUPABASE_ACCESS_TOKEN="sbp_488bb6b5a6b6e2b652b28c6c736776023117c461" npx supabase db push` - wypchnij migracje do bazy

Workflow:
1. Sprawdź strukturę bazy przez `gen types` lub `table-stats`
2. Stwórz migrację przez `migration new`
3. Napisz SQL w pliku migracji
4. Użytkownik wykonuje `npx supabase db push`

**NIE pytaj użytkownika o strukturę - sam ją sprawdź przez CLI!**

🎯 Core Principles
1. Plan First, Code Second

Zanim napiszesz choć jedną linijkę kodu, przeczytaj cały opis funkcji.

Podziel pracę na najmniejsze logiczne kroki.

Zapisz pseudokod lub szkic przepływu danych.

Zidentyfikuj zależności między modułami (np. Supabase ↔ Fakturownia ↔ n8n).

2. Small Steps, Frequent Checks

Implementuj jedną funkcję na raz.

Testuj natychmiast po każdej zmianie.

Nie przechodź dalej, dopóki obecny etap nie działa.

Jeśli coś się psuje → zatrzymaj się, przeczytaj błąd, zrozum przyczynę.

3. Think Like a Product Engineer

Zawsze pytaj „po co”, zanim coś dodasz.

Myśl o przypadkach brzegowych (np. pusta faktura, brak klienta, limit API).

Dbaj o doświadczenie użytkownika — system ma być prosty i zrozumiały.

Kod powinien tłumaczyć się sam przez nazwy funkcji i zmiennych.

4. Communication is Key

Jeśli coś jest niejasne → pytaj, nie zakładaj.

Wyjaśnij swój plan przed implementacją.

Dziel się postępami po każdym większym kroku.

Dokumentuj decyzje i kompromisy (np. „parsowanie komentarzy zamiast webhooków”).

🔄 Development Workflow
Stage 1: Planning

Przeczytaj wymagania funkcji.

Zrób listę plików do utworzenia lub modyfikacji.

Zanotuj potencjalne problemy (np. limity API Fakturowni).

Zadaj pytania, zanim zaczniesz pisać.

Potwierdź plan.

Stage 2: Implementation

Stwórz strukturę folderów i plików.

Zaimplementuj najmniejszy element (np. pojedynczy node w n8n).

Przetestuj w izolacji.

Dopiero wtedy zintegruj z resztą systemu.

Testuj ponownie.

Utwórz checkpoint commit.

Stage 3: Validation

Uruchom aplikację lokalnie lub w stagingu.

Sprawdź konsolę (brak błędów i ostrzeżeń).

Przetestuj ścieżkę „happy path” + edge cases.

Popraw błędy natychmiast.

Zapisz co działa.

Stage 4: Checkpoint

Podsumuj, co zostało wdrożone.

Wypisz, co działa, a co nie.

Zapisz dług techniczny (np. „refactor parsera komentarzy”).

Potwierdź gotowość do następnego modułu.

🛠️ Technical Best Practices
File Organization

✅ DO

Jeden komponent / plik.

Grupy po funkcjonalności (np. /fakturownia-sync, /client-ui, /supabase-hooks).

Nazwy opisowe: UpdateCommentNode.ts, InvoiceParser.ts.

❌ DON’T

Jeden plik z dziesiątkami funkcji.

Nazwy generyczne jak utils.ts z 500 liniami.

Głębokie zagnieżdżenia (max 3–4 poziomy).

Code Style (TypeScript / Python / JS)

✅ DO

async function syncInvoiceComment(invoiceId: string, field: string, value: boolean) {
  const invoice = await getInvoice(invoiceId);
  const updatedComment = updateFiscalSync(invoice.comment, field, value);
  await fakturownia.put(`/invoices/${invoiceId}`, { invoice: { comment: updatedComment } });
}


❌ DON’T

async function doSync(id, f, v) {
  const x = await api(id);
  await send(x, f, v);
}

Error Handling

✅ DO

try {
  const res = await supabase.from('invoices').select('*');
  if (!res.data) throw new Error('No data returned');
} catch (err) {
  console.error('Fetch error:', err);
  toast.error('Nie udało się pobrać danych z bazy');
}


❌ DON’T

const res = await supabase.from('invoices').select('*'); // bez obsługi błędu

Component Structure

✅ DO

export default async function DashboardPage() {
  const clients = await getClientsFromSupabase();
  return <ClientList clients={clients} />;
}


❌ DON’T

'use client';
export default function DashboardPage() {
  const [clients, setClients] = useState([]);
  useEffect(() => { fetch('/api/clients').then(r => r.json()).then(setClients); }, []);
});

🐛 Debugging Process

Zatrzymaj się. Nie pisz kolejnych linijek.

Odczytaj błąd dosłownie.

Cofnij się do ostatniej zmiany.

Odizoluj problem — wykomentuj kod.

Napraw przyczynę, nie objaw.

Zrozum dlaczego się zepsuło.

📋 Checkpoint System

Po każdej większej funkcji dodaj notatkę:

## Checkpoint: Fakturownia Sync — 2025-10-05

### ✅ Completed
- Dodano parser komentarzy `[FISCAL_SYNC]`
- Obsługa STOP flagi
- Aktualizacja Supabase po kliknięciu w UI

### 🐛 Known Issues
- Czasem zbyt częste wywołania API przy wielu kliknięciach

### 📝 Next Steps
- Debounce wywołania
- Dodać logi wysyłki w Supabase

🎨 UI/UX Standards

Każda akcja użytkownika → feedback (toast.success / toast.error).

Komponenty mają stany: loading, error, empty.

Interfejs responsywny (mobile / desktop).

Brak skoków layoutu przy wczytywaniu danych.

🔒 Security & Data

Waliduj dane wejściowe (Zod, Supabase policies).

Autoryzacja po stronie serwera (Next.js API Routes).

Nie loguj tokenów API.

Wrażliwe dane (np. NIP, e-mail) — tylko na poziomie autoryzowanego użytkownika.

Przy integracjach (np. Fakturownia API) respektuj limity 1000 req/h.

🚀 Performance

Pobieraj tylko potrzebne kolumny (select('id,status,total')).

Limituj zapytania (paginacja / per_page).

Buforuj dane w Supabase lub w RAMie aplikacji.

Używaj memoizacji (useMemo, useSWR).

Optymalizuj obrazy (next/image).

🧪 Testing Checklist

Happy Path

 Wysłanie e-maila / SMS działa poprawnie.

 Komentarz aktualizuje się w Fakturowni.

 Dane są zgodne w Supabase.

Edge Cases

 Brak klienta / faktury.

 Faktura z pustym komentarzem.

 Limit API osiągnięty.

Error Handling

 Błędy są widoczne w UI.

 System nie wiesza się przy awarii Fakturowni.

📚 Context Management

Przed każdą funkcją zapytaj:

Dlaczego to robimy?

Kto będzie tego używać? (księgowa, pracownik, system automatyczny)

Jak często to będzie wykonywane?

Jak rozpoznać sukces?

Jakie ograniczenia (API, czas, dane)?

🎓 Learning from Mistakes

Każdy większy błąd → dokumentuj.

## Lesson Learned: Zduplikowane wysyłki e-maili
**Data**: 2025-10-05  
**Przyczyna**: Brak blokady przy wielokrotnym kliknięciu przycisku.  
**Naprawa**: Dodano debounce + `isSending` state.  
**Wniosek**: Każda akcja API musi mieć blokadę ponownego kliknięcia.

🏁 Definition of Done

Feature jest gotowy, gdy:

 Działa poprawnie (happy + edge cases).

 Brak błędów w konsoli.

 UI spójny z resztą aplikacji.

 Kod czysty, bez TODO.

 Typy uzupełnione, brak any.

 Testy ręczne zakończone sukcesem.

 Checkpoint utworzony.

🎯 Daily Workflow Template
## Start
- [ ] Przeczytaj ostatni checkpoint
- [ ] Ustal max 3 cele na dziś
- [ ] Sprawdź ewentualne blokery

## W trakcie
- [ ] Koduj małymi krokami
- [ ] Testuj każdy etap
- [ ] Twórz checkpointy

## Koniec dnia
- [ ] Sprawdź integrację modułów
- [ ] Zaktualizuj główny checkpoint
- [ ] Zapisz pytania / blokery

💡 Pro Tips

Produktowo

Jeden cel → jedna sesja pracy.

Zrób najprostsze działające rozwiązanie, potem ulepszaj.

Kodowo

Czytaj swój kod na głos — znajdziesz błędy.

Upraszczaj — złożoność to koszt.

Nie bój się kasować — kod to nie relikwia.

Komunikacja

Lepiej zapytać 2× niż zgadywać raz.

Pokazuj — zrzuty ekranu > opisy.

🚨 Red Flags

Zatrzymaj się i zapytaj, jeśli:

utknąłeś na > 30 min,

masz pomysł „obejścia” trzeciego błędu,

nie wiesz, jak coś powinno działać,

masz zamiar „tymczasowo” dodać hardkodowane dane.

🎬 Pre-Launch Checklist

Funkcjonalność

 Sync z Fakturownią działa w obie strony

 Supabase poprawnie zapisuje dane

 Komentarze [FISCAL_SYNC] generują się prawidłowo

UX

 Wszystkie akcje mają feedback

 Stany loading/error/empty zaimplementowane

 Interfejs prosty dla nietechnicznych użytkowników

Performance

 API < 1000 req/h

 Czas ładowania < 2 s

 Brak nadmiarowych zapytań

Security

 Dane klientów chronione

 Klucze API w .env

 RLS w Supabase działa

Dokumentacja

 README + .env.example aktualne

 Endpointy API opisane

 Znane problemy zarejestrowane

📖 Remember

Make it work → Make it right → Make it fast.

Najpierw zrób, żeby działało.
Potem zadbaj o jakość i bezpieczeństwo.
Na końcu optymalizuj.

Perfect is the enemy of shipped.

Nie potrzebujesz perfekcji, tylko działającego systemu,
który realnie pomaga biurom księgowym.

✅ Sukces =

Funkcja działa i jest stabilna.

Kod jest zrozumiały tydzień później.

Klient widzi efekt („wow, działa automatycznie”).

Ty rozumiesz każdy element, który napisałeś.

Now go build Fiscal the smart way. 🧠⚡
Plan → Test → Document → Ship.
- memorize this strategy, i want to come back to it on demand.
- write that best r:r strategy to memory. i want it accessible on demand, attach data you worked on
- ok memorize this strat and data you worked on