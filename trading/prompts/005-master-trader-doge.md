# Master Trader: DOGE/USDT 1-Minute Strategy Discovery

## Objective
Become a master trader for DOGE/USDT. Find a profitable trading strategy with minimum 2:1 R:R ratio (net P&L vs max drawdown).

## Data
- File: `doge_usdt_1m_lbank.csv` (~43,000 candles, 30 days of 1m data)
- Columns: timestamp, open, high, low, close, volume

## Fee Structure (CRITICAL)
- **Market orders**: 0.1% round-trip (0.05% open + 0.05% close)
- **Limit orders**: 0.07% round-trip (0.02% maker + 0.05% taker)
- For limit orders, use 0.035% offset from signal price

## Approach: Probe First, Then Optimize
1. **Start basic** - Test simple strategies with default parameters
2. **Find what works** - Identify which approach shows promise (positive P&L)
3. **Then optimize** - Only fine-tune parameters after finding a working base

## Testing Areas

### 1. Trading Sessions
Test each session separately to find DOGE's best trading hours:
- **Asian**: 0-8 UTC
- **European**: 8-14 UTC
- **US**: 14-22 UTC
- **24h**: No time filter (baseline)

### 2. Strategy Types to Test
A. **Mean Reversion (BB-based)**
   - Bollinger Bands (20 SMA, 2-3 STD)
   - Entry: Price crosses below lower band (LONG) / above upper band (SHORT)
   - Start with BB2.5, then try BB2, BB3

B. **Trend Following**
   - EMA crossovers (fast: 5-10, slow: 20-50)
   - Breakout strategies
   - Only trade in direction of higher timeframe trend

C. **Momentum**
   - RSI extremes (oversold < 30, overbought > 70)
   - MACD crossovers
   - Volume spikes

D. **Meme Coin Specific**
   - High volatility exploitation
   - Volume surge entries
   - Quick scalps with tight stops

### 3. ATR-Based TP/SL
Test various ATR multipliers:
- Conservative: SL=1.5x ATR, TP=3x ATR
- Balanced: SL=2x ATR, TP=4x ATR
- Wide: SL=3x ATR, TP=6x ATR
- Tight: SL=1x ATR, TP=2x ATR

### 4. Volatility Filters
- Only trade when ATR > X percentile
- Only trade when volume > Y percentile
- Skip trades during low volatility periods

### 5. Dynamic Position Sizing
Test streak-based sizing:
- Base size after loss streak
- Increase size after win streak
- Kelly-inspired sizing

## Success Metrics
- **Primary**: R:R ratio = Net P&L % / Max Drawdown % (target: >= 2.0)
- **Secondary**: Win rate >= 50%
- **Minimum trades**: >= 30 for statistical significance

## Output Requirements
1. Create backtest script: `doge_master_backtest.py`
2. Save results to: `results/doge_master_results.csv`
3. Document best strategy with parameters
4. Generate equity curve if profitable strategy found

## Workflow
1. Load data and calculate basic indicators
2. Test sessions with simple strategy (find best hours)
3. Test strategy types during best session
4. Test ATR multipliers for best strategy
5. Add volatility filters if helpful
6. Test position sizing variations
7. Combine best elements into final strategy
8. Document findings

## Key Context
- DOGE is a meme coin but more established than PEPE
- BB3 strategy showed -3.18% loss (Conservative) and -7.85% loss (Aggressive)
- The coin had NEGATIVE results with all tested BB3 configurations
- DOGE may need:
  - Different indicator entirely (RSI, MACD, EMA crossover)
  - Session-specific trading (may only work certain hours)
  - Trend-following instead of mean-reversion
  - Tighter stops due to choppy price action
