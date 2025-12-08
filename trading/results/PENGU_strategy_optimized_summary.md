# PENGU Mean Reversion Strategy - OPTIMIZED Backtest

**Date**: 2025-12-07 19:55:56

## Optimization Changes

1. **BB Std Dev**: 2.0 → 2.5 (wider bands, stronger extremes)
2. **RSI Threshold**: 35 → 30 (more extreme oversold)
3. **Volume Spike**: 1.5x → 2.0x (require stronger capitulation)
4. **Stop Loss**: 2.5 ATR → 4.0 ATR (wider stops)
5. **Take Profit**: 5.0 ATR → 8.0 ATR (better R:R)
6. **Max Hold**: 120 min → 60 min (faster exits)

## Performance Metrics

| Metric | Value |
|--------|-------|
| **Total Trades** | 42 |
| **Win Rate** | 33.33% |
| **Total Return** | -8.58% |
| **Final Capital** | $9,141.90 |
| **Avg Win** | +1.08% |
| **Avg Loss** | -0.85% |
| **R:R Ratio** | 1.27x |
| **Expectancy** | -0.21% |
| **Max Drawdown** | -12.36% |
| **Avg Hold Time** | 36.3 min |
| **Avg Entry RSI** | 22.5 |

## Target Validation

- ❌ **Minimum Trades (≥50)**: 42
- ❌ **Win Rate (≥35%)**: 33.3%
- ❌ **R:R Ratio (≥1.6x)**: 1.27x
- ✅ **Max Drawdown (>-25%)**: -12.4%
- ❌ **Expectancy (>0%)**: -0.21%
