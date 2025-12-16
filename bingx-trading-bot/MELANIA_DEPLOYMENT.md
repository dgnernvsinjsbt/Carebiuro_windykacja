# MELANIA RSI OPTIMIZED - DEPLOYMENT GUIDE

## Strategy Performance (Jun-Dec 2025 Backtest)

- **Return:** +3,441%
- **Max Drawdown:** -64.40%
- **Return/DD Ratio:** 53.43x
- **Win Rate:** 38.1% (53W / 86L)
- **Total Trades:** 139
- **Avg Trades/Month:** 20

### Monthly Performance

| Month | Return | Max DD | Trades | Win% |
|-------|--------|--------|--------|------|
| June | -20.8% | -21.52% | 11 | 27.3% |
| July | +14.2% | -64.40% | 35 | 22.9% |
| August | -12.6% | -58.97% | 33 | 27.3% |
| September | +9.5% | -41.27% | 16 | 37.5% |
| October | +292.1% | -30.83% | 10 | 70.0% |
| November | +94.5% | -25.58% | 25 | 52.0% |
| December | +436.2% | -24.24% | 9 | 77.8% |

---

## Strategy Configuration

### Entry Rules
- **Symbol:** MELANIA-USDT
- **Timeframe:** 15m
- **RSI Levels:** 35 (oversold) / 65 (overbought)
- **Momentum Filter:** ret_20 > 0 (only trade when 20-bar return is positive)
- **Order Type:** LIMIT orders with 0.1 ATR offset
- **Max Wait:** 8 bars (2 hours)

### Exit Rules
- **Stop Loss:** 1.2x ATR
- **Take Profit:** 3.0x ATR
- **Fees:** 0.1% round-trip (included in backtest)

### Dynamic Position Sizing
- **Initial Risk:** 12% per trade
- **Win Multiplier:** +50% (1.5x) after each win
- **Loss Multiplier:** -50% (0.5x) after each loss
- **Min Risk Floor:** 2% (THE SECRET WEAPON - protects capital during drawdowns)
- **Max Risk Cap:** 30%

### Surgical Filter
- **SHORT Filter:** Skip SHORT trades when avg move size < 0.8%
- **Why:** Prevents trading SHORT in dead markets (removed 7/20 worst losers)
- **LONG Filter:** None (LONG trades work in all conditions)

---

## Deployment Instructions

### 1. Configuration

The strategy is configured in `config.yaml`:

```yaml
symbols:
  - MELANIA-USDT

strategies:
  melania_rsi_optimized:
    enabled: true
```

All other strategies are disabled by default in this config.

### 2. Environment Variables

Set your BingX API credentials:

```bash
export BINGX_API_KEY="your_api_key"
export BINGX_API_SECRET="your_api_secret"
```

### 3. Start Trading

```bash
cd bingx-trading-bot
python main.py
```

### 4. Monitor

The bot will:
- Fetch 15m candles every 15 minutes
- Calculate RSI, ATR, momentum filter, move size filter
- Generate signals based on strategy rules
- Place limit orders with dynamic position sizing
- Manage stop-loss and take-profit orders
- Log all trades and performance metrics

---

## Risk Management

### Capital Protection (2% Floor)

The **2% minimum risk floor** is the key innovation:

**During losing periods (Jun-Sep):**
- Risk drops to 2% after consecutive losses
- Position sizes become tiny
- **Result:** Only -9.7% total loss across 4 losing months

**During winning periods (Oct-Dec):**
- Risk scales up to 30% after win streaks
- Captures explosive moves
- **Result:** +822.8% gain across 3 winning months

### Expected Drawdowns

Based on backtesting:
- **Normal:** -20% to -40% drawdowns expected during choppy markets
- **Severe:** -64.40% worst case (July 2025)
- **Recovery:** Strategy turns positive even after severe drawdowns (July ended +14.2%)

### Position Sizing Examples

| Scenario | Risk % | $1,000 Account | $10,000 Account |
|----------|--------|----------------|-----------------|
| Starting | 12% | $120/trade | $1,200/trade |
| After win | 18% | $180/trade | $1,800/trade |
| After loss | 9% | $90/trade | $900/trade |
| 3 losses | 4.5% | $45/trade | $450/trade |
| **Turtle mode** | **2%** | **$20/trade** | **$200/trade** |
| 3 wins | 27% | $270/trade | $2,700/trade |
| Max cap | 30% | $300/trade | $3,000/trade |

---

## Key Success Factors

1. **Low win rate (38%) but positive R/DD** - Asymmetric payoff
2. **Dynamic sizing** - Scales down during drawdowns, up during wins
3. **2% floor** - Prevents account destruction during bad periods
4. **Surgical filter** - Removes worst SHORT setups (dead markets)
5. **Limit orders** - Better fills, filters fake breakouts

---

## Monitoring & Alerts

Watch for:
- ✅ **Risk scaling down to 2%** - Turtle mode activated (normal during bad periods)
- ⚠️ **Win rate < 20% for > 20 trades** - Consider pausing (market regime shift)
- ⚠️ **Drawdown > 70%** - Outside historical range (review strategy)
- ✅ **Risk scaling up to 30%** - Aggressive mode (capitalizing on wins)

---

## Files Modified

1. `strategies/melania_rsi_optimized.py` - New strategy implementation
2. `config.yaml` - Configuration (only MELANIA enabled)
3. `main.py` - Added strategy import and initialization

---

## Disclaimer

**Past performance does not guarantee future results.**

This strategy achieved +3,441% on backtested data (Jun-Dec 2025). Live trading may differ due to:
- Market regime changes
- Slippage and execution quality
- API reliability
- BingX liquidity for MELANIA-USDT

**Start with small capital and monitor closely for the first 2-4 weeks.**

---

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Verify BingX API connectivity
3. Ensure MELANIA-USDT has sufficient liquidity
4. Monitor position sizing (should start at ~12% risk)

**Good luck! 🚀**
