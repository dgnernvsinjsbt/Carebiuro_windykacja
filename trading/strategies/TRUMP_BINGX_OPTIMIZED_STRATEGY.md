# TRUMP Volume Zones - Optimized Strategy Specification (BingX)

**Strategy Name:** TRUMP Volume Zones (BingX Optimized)
**Token:** TRUMP/USDT
**Exchange:** BingX
**Timeframe:** 1-minute
**Direction:** SHORT ONLY
**Version:** 2.0 (BingX Optimized)
**Date:** December 9, 2025

---

## Performance Summary

| Metric | Value |
|--------|-------|
| **Return/DD Ratio** | **7.94x** |
| **Total Return** | **+9.01%** (32 days) |
| **Max Drawdown** | **-1.14%** |
| **Win Rate** | **61.5%** |
| **Profit Factor** | **4.17** |
| **Trades** | 13 |
| **Avg Hold Time** | 56 minutes |
| **Top 20% Concentration** | 55.4% (low outlier dependency) |

---

## Strategy Logic

### 1. Zone Detection

Detect **distribution zones** (sustained selling volume at local highs):

```python
# Calculate volume ratio
vol_ma = volume.rolling(20).mean()
vol_ratio = volume / vol_ma

# Detect elevated volume bars
elevated_bars = []
for i in range(len(df)):
    if vol_ratio[i] >= 1.3:  # 1.3x threshold (BingX specific)
        elevated_bars.append(i)

# Group into zones (3+ consecutive bars)
zones = []
current_zone = []
for i in range(len(elevated_bars)):
    if not current_zone or elevated_bars[i] == current_zone[-1] + 1:
        current_zone.append(elevated_bars[i])
    else:
        if len(current_zone) >= 3:  # Minimum 3 bars
            zones.append(current_zone)
        current_zone = [elevated_bars[i]]

if len(current_zone) >= 3:
    zones.append(current_zone)
```

### 2. Classify as Distribution Zone

A zone is a **distribution zone** (SHORT setup) if:

```python
zone_start = zone[0]
zone_end = zone[-1]

# Get zone high
zone_high = df.loc[zone_start:zone_end, 'high'].max()

# Check if zone high is local maximum (20-bar lookback + 5-bar lookahead)
lookback_start = max(0, zone_start - 20)
lookahead_end = min(len(df), zone_end + 5)

if zone_high == df.loc[lookback_start:lookahead_end, 'high'].max():
    # This is a distribution zone (at top)
    entry_idx = zone_end + 1  # Enter on next bar
```

### 3. Entry Rules

**SHORT Entry:**
- Distribution zone detected (volume spike at local high)
- Enter **1 bar after zone ends**
- Use **LIMIT ORDER** 0.035% above current close
- All sessions eligible (24/7 trading)

```python
entry_price = df.loc[entry_idx, 'close']
limit_order_price = entry_price * 1.00035  # 0.035% above

# Place limit SHORT at limit_order_price
```

**Why Limit Orders:**
- Reduces fees from 0.1% to 0.07% (maker + taker vs 2x taker)
- Improves fill quality (entering slight bounces)
- Adds ~0.8-1.0x to R/DD ratio

### 4. Exit Rules

**Stop Loss:** Fixed 0.5% above entry

```python
stop_loss = entry_price * 1.005  # 0.5% above entry
```

**Take Profit:** 5:1 Risk/Reward ratio

```python
sl_distance = entry_price * 0.005  # 0.5%
take_profit = entry_price - (5 * sl_distance)  # 2.5% below entry
```

**Time Exit:** 90 bars (90 minutes)

```python
if bars_in_trade >= 90:
    exit_at_market()
```

### 5. Position Sizing

**Fixed % of Capital:**
- Risk 1% of capital per trade
- Position size = (Capital * 0.01) / (Entry * 0.005)

```python
capital = 10000  # Example
risk_per_trade = capital * 0.01  # $100 risk
stop_distance_dollars = entry_price * 0.005

position_size = risk_per_trade / stop_distance_dollars
```

**Leverage:** 5x (for futures)
- Allows larger position sizes with same capital
- Keep stop loss at 0.5% (tight control)

---

## Configuration Parameters

```yaml
strategy:
  name: TRUMP_Volume_Zones_BingX_Optimized
  version: 2.0

exchange:
  name: BingX
  symbol: TRUMP-USDT
  timeframe: 1m
  leverage: 5x

zone_detection:
  volume_threshold: 1.3        # 1.3x average volume
  min_consecutive_bars: 3      # 3+ bars required
  lookback_period: 20          # Check 20 bars before zone
  lookahead_period: 5          # Check 5 bars after zone

entry:
  direction: SHORT             # SHORT ONLY
  order_type: LIMIT            # Use limit orders
  limit_offset_pct: 0.035      # 0.035% above/below signal
  session_filter: null         # Trade 24/7

exit:
  stop_loss:
    type: fixed_pct
    value: 0.5                 # 0.5% fixed stop

  take_profit:
    type: rr_multiple
    value: 5.0                 # 5:1 R:R (2.5% target)

  time_exit:
    max_hold_bars: 90          # Exit after 90 minutes

risk_management:
  risk_per_trade_pct: 1.0      # 1% of capital per trade
  max_daily_loss_pct: 3.0      # Stop trading at -3% daily loss
  max_concurrent_trades: 1     # One position at a time

fees:
  maker_fee: 0.02              # 0.02% for limit orders
  taker_fee: 0.05              # 0.05% for market orders
  total_round_trip: 0.07       # 0.07% average
```

---

## Key Differences from MEXC Version

| Parameter | MEXC Original | BingX Optimized | Reason |
|-----------|---------------|-----------------|--------|
| **Volume Threshold** | 1.5x | 1.3x | BingX has fewer volume spikes |
| **Min Consecutive Bars** | 5 | 3 | Relaxed to catch more signals |
| **Direction** | BOTH | SHORT only | LONGs don't work on BingX |
| **Session Filter** | Overnight | ALL | No session edge on BingX |
| **Limit Orders** | NO | YES | Better fills, lower fees |
| **R:R Ratio** | 4:1 | 5:1 | Slightly wider target optimal |

---

## Risk Warnings

⚠️ **SHORT-Only Strategy:** This strategy does NOT trade LONGs. You will miss any uptrends. Consider adding a LONG configuration if accumulation zones start working.

⚠️ **Exchange-Specific:** This config is optimized for BingX. DO NOT use on other exchanges without re-optimization. Volume dynamics differ significantly.

⚠️ **Sample Period Bias:** Optimized on Nov-Dec 2025 data (choppy market). May underperform in strong trends. Monitor performance and adjust.

⚠️ **Outlier Dependency:** While improved (55.4%), still moderately dependent on large winners. Missing a few big moves will hurt returns.

⚠️ **Low Signal Frequency:** Only 13 trades in 32 days (~1 trade every 2.5 days). Requires patience. Consider trading multiple tokens to increase frequency.

---

## Live Trading Checklist

Before deploying to live trading:

- [ ] Verify BingX API connectivity
- [ ] Test limit order placement in paper trading
- [ ] Confirm 1.3x volume threshold is correctly calculated
- [ ] Implement 3-bar consecutive volume detection logic
- [ ] Set up 0.5% stop loss and 5:1 R:R take profit
- [ ] Enable 90-bar time exit
- [ ] Test SHORT-only filter (no LONGs)
- [ ] Verify 0.07% fee calculation
- [ ] Implement 1% risk per trade position sizing
- [ ] Set up max 3% daily loss circuit breaker
- [ ] Monitor first 5 trades manually before full automation

---

## Performance Monitoring

Track these metrics weekly:

1. **Return/DD Ratio** - Should stay above 5.0x
2. **Win Rate** - Should stay above 55%
3. **Top 20% Concentration** - Should stay below 65%
4. **Avg Hold Time** - Should stay around 50-60 minutes
5. **Profit Factor** - Should stay above 3.0

**Red Flags:**
- Win rate drops below 50% for 2+ weeks
- Top 20% concentration exceeds 75%
- Max DD exceeds -2.5%
- Profit factor drops below 2.0

If any red flag occurs, **pause trading** and re-optimize with recent data.

---

## Code Files

1. **trump_bingx_adaptive_optimizer.py** - Full optimization code
2. **TRUMP_bingx_optimized_trades.csv** - All 13 backtest trades
3. **TRUMP_optimization_comparison.csv** - MEXC vs BingX comparison
4. **TRUMP_optimized_equity.png** - Equity curve visualization

---

**Strategy Specification Version:** 2.0
**Optimization Date:** December 9, 2025
**Data Period:** Nov 7 - Dec 9, 2025 (32 days)
**Tested Configurations:** 8,640
**Rank:** #1 of 2,880 valid configs (Top 0.03%)
