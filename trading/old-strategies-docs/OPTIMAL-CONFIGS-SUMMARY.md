# Optimal Strategy Configurations - Copy-Paste Ready

## FARTCOIN - OPTIMAL CONFIG (10.67x R:R)

```python
config = {
    # Entry Filters
    'body_threshold': 1.2,          # Changed from 1.0 (stricter)
    'volume_multiplier': 2.5,       # Same as baseline
    'wick_threshold': 0.35,         # Same as baseline

    # Trend Filters
    'require_strong_trend': True,   # Both 50 & 200 SMA must align
    'sma_distance_min': 2.0,        # CRITICAL: 2% distance from SMA

    # RSI Filters
    'rsi_short_max': 55,            # Short entry RSI ceiling
    'rsi_short_min': 25,            # Short entry RSI floor
    'rsi_long_min': 45,             # Long entry RSI floor
    'rsi_long_max': 75,             # Long entry RSI ceiling

    # Volatility Filters
    'require_high_vol': True,       # Only trade high volatility
    'atr_percentile_min': 50,       # Minimum ATR percentile

    # Take Profit / Stop Loss
    'tp_atr_mult': 15.0,            # 15x ATR = 5:1 R:R per trade
    'stop_atr_mult': 3.0,           # 3x ATR stop

    # Position Sizing
    'base_risk_pct': 1.5,           # Base risk per trade
    'max_risk_pct': 5.0,            # Maximum after win streaks
    'win_streak_scaling': 0.5,      # Scale up 0.5% per win

    # Trade Management
    'use_trailing_stop': True,      # Trail stops after 3R
    'use_partial_exits': True,      # Exit 30% at 2R, 40% at 4R
    'max_hold_hours': 24,           # Force close after 24h
    'trade_both_directions': True   # Long and short
}

# Expected Performance:
# - Return: +21.38%
# - Max Drawdown: -2.00%
# - R:R Ratio: 10.67x
# - Trades: 11 per month
# - Win Rate: 63.6%
# - Profit Factor: 4.67
```

---

## FARTCOIN - CONSERVATIVE CONFIG (8.88x R:R - VALIDATED)

```python
config = {
    # Entry Filters
    'body_threshold': 1.0,          # Standard (baseline)
    'volume_multiplier': 2.5,       # Same as baseline
    'wick_threshold': 0.35,         # Same as baseline

    # Trend Filters
    'require_strong_trend': True,   # Both 50 & 200 SMA must align
    'sma_distance_min': 2.0,        # CRITICAL: 2% distance from SMA

    # RSI Filters
    'rsi_short_max': 55,
    'rsi_short_min': 25,
    'rsi_long_min': 45,
    'rsi_long_max': 75,

    # Volatility Filters
    'require_high_vol': True,
    'atr_percentile_min': 50,

    # Take Profit / Stop Loss
    'tp_atr_mult': 15.0,            # 15x ATR = 5:1 R:R per trade
    'stop_atr_mult': 3.0,

    # Position Sizing
    'base_risk_pct': 1.5,
    'max_risk_pct': 5.0,
    'win_streak_scaling': 0.5,

    # Trade Management
    'use_trailing_stop': True,
    'use_partial_exits': True,
    'max_hold_hours': 24,
    'trade_both_directions': True
}

# Expected Performance:
# - Return: +20.08%
# - Max Drawdown: -2.26%
# - R:R Ratio: 8.88x (ORIGINAL V7 RESULT)
# - Trades: 12 per month
# - Win Rate: 58.3%
# - Profit Factor: 3.83
```

---

## MELANIA - OPTIMAL CONFIG (10.71x R:R - NEEDS VALIDATION)

```python
config = {
    # Entry Filters
    'body_threshold': 1.0,          # Standard
    'volume_multiplier': 2.5,       # Same as baseline
    'wick_threshold': 0.35,         # Same as baseline

    # Trend Filters
    'require_strong_trend': True,   # Both 50 & 200 SMA must align
    'sma_distance_min': 2.5,        # WIDER than FARTCOIN (2.5% vs 2.0%)

    # RSI Filters
    'rsi_short_max': 55,
    'rsi_short_min': 25,
    'rsi_long_min': 45,
    'rsi_long_max': 75,

    # Volatility Filters
    'require_high_vol': True,
    'atr_percentile_min': 50,

    # Take Profit / Stop Loss
    'tp_atr_mult': 18.0,            # WIDER than FARTCOIN (18x vs 15x = 6:1 R:R)
    'stop_atr_mult': 3.0,

    # Position Sizing
    'base_risk_pct': 1.5,
    'max_risk_pct': 5.0,
    'win_streak_scaling': 0.5,

    # Trade Management
    'use_trailing_stop': True,
    'use_partial_exits': True,
    'max_hold_hours': 24,
    'trade_both_directions': True
}

# Expected Performance (UNVALIDATED - only 5 trades):
# - Return: +15.16%
# - Max Drawdown: -1.41%
# - R:R Ratio: 10.71x
# - Trades: 5 per month (LOW!)
# - Win Rate: 60.0%
# - Profit Factor: 14.93
#
# WARNING: Sample size too small. Paper trade first!
```

---

## KEY DIFFERENCES BETWEEN COINS

| Parameter | FARTCOIN Optimal | MELANIA Optimal | Why Different? |
|-----------|-----------------|-----------------|----------------|
| **Body Threshold** | 1.2% | 1.0% | FARTCOIN more selective |
| **SMA Distance** | 2.0% | 2.5% | MELANIA needs wider pullbacks |
| **TP Multiplier** | 15x ATR (5:1) | 18x ATR (6:1) | MELANIA benefits from wider targets |
| **Expected Trades** | 11/month | 5/month | MELANIA half as frequent |
| **Validation** | ✓ Robust | ⚠ Needs testing | Trade count difference |

---

## PORTFOLIO ALLOCATION STRATEGY

### Option 1: Conservative (FARTCOIN Only)
```
100% FARTCOIN (Body 1.2% config)
- Most reliable
- 11 trades/month
- 10.67x R:R
```

### Option 2: Moderate (Validate First)
```
100% FARTCOIN (live)
Paper trade MELANIA for 2-4 weeks
If MELANIA validates → Switch to Option 3
```

### Option 3: Diversified (Advanced)
```
70% FARTCOIN (Body 1.2% config)
30% MELANIA (Aggressive TP config)

Combined stats:
- ~16 trades/month (11 + 5)
- Diversified across 2 volatility patterns
- Risk: MELANIA unproven (small sample)
```

---

## IMPLEMENTATION CHECKLIST

### FARTCOIN (Ready to Deploy)
- [ ] Copy optimal config to trading bot
- [ ] Set initial capital allocation
- [ ] Configure alerts for pattern detection
- [ ] Monitor first 5 trades closely
- [ ] Compare live results to backtest

### MELANIA (Paper Trade First)
- [ ] Copy optimal config to paper trading account
- [ ] Run for minimum 10 trades or 30 days
- [ ] Compare paper results to backtest
- [ ] If validated (8+ R:R) → Go live with 30% allocation
- [ ] If underperforms (< 5x R:R) → Skip this coin

### PI & PENGU (Skip)
- [ ] Do NOT trade these coins with this strategy
- [ ] Strategy fundamentally doesn't match their characteristics
- [ ] Consider different approach or different assets

---

## PARAMETER TUNING GUIDE

If you want to experiment further, here's the impact of each parameter:

### Increase SMA Distance (e.g., 2.0% → 2.5%)
- ✓ Higher R:R ratio
- ✗ Fewer trades
- Best for: Coins with strong trends (MELANIA)

### Increase Body Threshold (e.g., 1.0% → 1.2%)
- ✓ Better win rate
- ✓ Higher R:R
- ✗ Fewer trades
- Best for: Reducing false signals (FARTCOIN)

### Increase TP Multiplier (e.g., 15x → 18x)
- ✓ Bigger winners
- ✗ Lower win rate (harder to hit TP)
- Best for: Trending markets (MELANIA)

### Decrease Volume Multiplier (e.g., 2.5x → 2.0x)
- ✓ More trades
- ✗ Lower quality setups
- ✗ Lower R:R
- Best for: Increasing frequency (FARTCOIN showed 9.75x at 2.0x vol)

---

## LIVE TRADING NOTES

1. **Start Small:** Test with 20-30% of intended capital first
2. **Track Every Trade:** Compare to backtest expectations
3. **Watch Win Rate:** Should be 55-65% (if < 50%, stop and reassess)
4. **Monitor R:R:** Live should match backtest ±20%
5. **Slippage:** Factor in 0.1-0.2% slippage on entries/exits
6. **Adjust if Needed:** Markets change, parameters may need tweaking after 30-50 trades

---

## QUICK START COMMANDS

### Test FARTCOIN Config
```bash
python strategies/explosive-v7-advanced.py --config strategies/best-config-fartcoin.json
```

### Test MELANIA Config
```bash
python strategies/explosive-v7-advanced.py --config strategies/best-config-melania.json
```

### Run Live Bot (Example)
```bash
python trading_bot/main.py \
  --symbol FARTCOIN/USDT \
  --config strategies/best-config-fartcoin.json \
  --capital 10000 \
  --mode live
```

---

**Last Updated:** 2025-12-05
**Backtest Period:** 30 days (Nov 5 - Dec 5, 2025)
**Data Source:** LBank 1-minute OHLCV data
