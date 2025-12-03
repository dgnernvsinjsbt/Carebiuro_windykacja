# FARTCOIN/USDT Trading Strategy Backtest Results

**Backtest Period**: 2025-09-04 12:15:00 to 2025-12-03 12:00:00
**Total Candles**: 8640 (15-minute intervals)
**Initial Capital**: $10,000
**Trading Fees**: 0% (zero-fee spot exchange)

---

## Strategy Rankings - Top 10

| Rank | Strategy | Exit Method | Return (%) | Trades | Win Rate (%) | Profit Factor | Max DD (%) | Sharpe |
|------|----------|-------------|-----------|--------|-------------|---------------|-----------|--------|
| 1 | ema50_pullback | time_based_8 | 70.56 | 442 | 23.5 | 1.32 | 16.41 | 1.07 |
| 2 | ema50_pullback | time_based_4 | 44.05 | 497 | 29.8 | 1.24 | 15.31 | 1.00 |
| 3 | ema50_pullback | fixed_rr_1.5 | 14.97 | 534 | 38.2 | 1.08 | 15.84 | 0.47 |
| 4 | ema_10_50_cross | time_based_8 | 8.95 | 118 | 43.2 | 1.10 | 21.33 | 0.71 |
| 5 | ema_10_50_cross | trail_atr_2.0 | -20.31 | 120 | 33.3 | 0.76 | 31.03 | -1.34 |
| 6 | ema_10_50_cross | trail_atr_1.5 | -25.66 | 121 | 30.6 | 0.54 | 29.81 | -3.34 |
| 7 | ema50_pullback | trail_atr_1.5 | -42.78 | 498 | 24.5 | 0.67 | 43.63 | -1.88 |

---

## Top 3 Strategies - Detailed Analysis

### #1: ema50_pullback + time_based_8

**Performance Metrics:**
- **Total Return**: 70.56%
- **Final Capital**: $17,056.00
- **Total Trades**: 442
- **Win Rate**: 23.53%
- **Profit Factor**: 1.32
- **Average Win**: 2.29%
- **Average Loss**: -0.52%
- **Max Drawdown**: 16.41%
- **Sharpe Ratio**: 1.07
- **Average Trade Duration**: 3.7 candles (56 minutes)
- **Largest Win**: 25.30%
- **Largest Loss**: -3.43%

### #2: ema50_pullback + time_based_4

**Performance Metrics:**
- **Total Return**: 44.05%
- **Final Capital**: $14,405.00
- **Total Trades**: 497
- **Win Rate**: 29.78%
- **Profit Factor**: 1.24
- **Average Win**: 1.40%
- **Average Loss**: -0.48%
- **Max Drawdown**: 15.31%
- **Sharpe Ratio**: 1.00
- **Average Trade Duration**: 2.5 candles (38 minutes)
- **Largest Win**: 12.42%
- **Largest Loss**: -3.43%

### #3: ema50_pullback + fixed_rr_1.5

**Performance Metrics:**
- **Total Return**: 14.97%
- **Final Capital**: $11,497.00
- **Total Trades**: 534
- **Win Rate**: 38.20%
- **Profit Factor**: 1.08
- **Average Win**: 0.99%
- **Average Loss**: -0.56%
- **Max Drawdown**: 15.84%
- **Sharpe Ratio**: 0.47
- **Average Trade Duration**: 2.5 candles (38 minutes)
- **Largest Win**: 11.60%
- **Largest Loss**: -4.13%

---

## Recommended Trading Strategy

**Strategy**: ema50_pullback
**Exit Method**: time_based_8

### Entry Rules

### Exit Rules
- Time-based exit after based candles
- Stop loss if price hits stop level
- Close all positions at end of day (no overnight holds)

### Position Sizing
- Use 100% of available capital per trade (long only, no leverage)
- No overlapping positions
- Daily compounding: Profits/losses affect next trade size

### Risk Management
- **Daily Drawdown Limit**: 5% - Stop trading for the day if hit
- **No Overnight Positions**: Close all trades by end of session
- **Stop Loss**: Always use stop loss on every trade

### Expected Performance
- Total Return: 70.56% over 3 months
- Win Rate: 23.53%
- Average Trade: ~56 minutes
- Trades per day: ~4.9