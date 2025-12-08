# TRUMP Optimized Strategy Backtest Summary

**Strategy:** RSI Mean Reversion (Long Only, US Session)

**Backtest Date:** 2025-12-07 19:23:11

**Data Period:** 2025-11-07 15:54:00 to 2025-12-07 15:55:00

**Total Candles:** 43,202

---

## Performance Summary

| Metric | Value |
|--------|-------|
| Initial Capital | $10,000.00 |
| Final Capital | $9,937.55 |
| Total Return | -0.62% |
| Max Drawdown | -0.63% |
| Total Trades | 287 |
| Win Rate | 42.51% |
| Profit Factor | 0.57x |
| Avg R:R Ratio | 0.77x |
| Avg Win | 0.18% |
| Avg Loss | -0.24% |
| Avg Holding Time | 6.3 minutes |

## Strategy Details

**Entry Criteria:**
- RSI < 30 (strongest statistical edge: 55% win rate)
- OR 5+ consecutive red candles
- Price within 10% of lower Bollinger Band
- Volume >= 1.0x average
- Normal volatility (ATR < 0.30%)
- US session ONLY (14:00-21:00 UTC)

**Exit Criteria:**
- Stop Loss: 1.5x ATR below entry
- Take Profit: 3x ATR above entry (R:R = 2.0)
- RSI Exit: When RSI > 45
- Time Exit: After 20 candles (20 minutes)

**Position Sizing:**
- 2% of capital per trade
- Max 2 concurrent trades
- Max 15 trades per day


## Exit Analysis

| Exit Type | Count | Percentage |
|-----------|-------|------------|
| Stop Loss | 120 | 41.8% |
| Take Profit | 40 | 13.9% |
| RSI Exit | 127 | 44.3% |
| Time Exit | 0 | 0.0% |

## Files Generated

- Trade log: `TRUMP_strategy_results.csv`
- Equity curve: `TRUMP_strategy_equity.png`
- Summary: `TRUMP_strategy_summary.md`
