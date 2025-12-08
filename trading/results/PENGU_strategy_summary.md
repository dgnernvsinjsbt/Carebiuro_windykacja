# PENGU Mean Reversion Strategy - FINAL Backtest

**Generated**: 2025-12-07 19:57:39

## Strategy Philosophy

**TRUE MEAN REVERSION**: Buy extreme panic, sell at statistical mean (BB midline)

- Entry: Lower BB touch + RSI<25 + Volume spike + Below SMA
- Target: BB Midline (SMA 20) - natural mean reversion point
- Stop Loss: 3.0x ATR
- Session: US hours (16-21 UTC)
- Max Hold: 90 minutes

## Performance Metrics

| Metric | Value |
|--------|-------|
| **Total Trades** | 59 |
| **Win Rate** | 38.98% |
| **Total Return** | -15.38% |
| **Final Capital** | $8,461.69 |
| **Avg Win** | +0.50% |
| **Avg Loss** | -0.78% |
| **R:R Ratio** | 0.64x |
| **Expectancy** | -0.28% |
| **Max Drawdown** | -15.78% |
| **Avg Hold Time** | 17.5 min |
| **Avg Entry RSI** | 19.2 |

## Target Validation

- ✅ **Minimum Trades (≥50)**: 59
- ✅ **Win Rate (≥35%)**: 39.0%
- ❌ **R:R Ratio (≥1.6x)**: 0.64x
- ✅ **Max Drawdown (>-25%)**: -15.8%
- ❌ **Expectancy (>0%)**: -0.28%

## Exit Analysis

| Exit Reason | Count | % | Win Rate | Avg P&L |
|-------------|-------|---|----------|----------|
| Stop Loss | 35 | 59.3% | 0.0% | -0.80% |
| Take Profit | 23 | 39.0% | 95.7% | +0.50% |
| Time Exit | 1 | 1.7% | 100.0% | +0.09% |

## Verdict

❌ **Negative expectancy** - strategy not profitable on this dataset.

**PENGU Character**: Extremely choppy and mean-reverting. This asset requires perfect timing and strict filters to be profitable. The low win rate combined with extreme volatility makes it challenging for systematic trading. Consider alternative assets with more trending behavior.
