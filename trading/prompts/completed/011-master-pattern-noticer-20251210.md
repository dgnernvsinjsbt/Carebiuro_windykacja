# Master Pattern Noticer - PI/USDT Analysis

## Objective
Analyze PI/USDT 1-minute data (30 days from BingX Perpetual) to discover profitable trading patterns and strategies.

## Data
- **File**: `pi_30d_bingx.csv`
- **Period**: Nov 10 - Dec 10, 2025 (30 days)
- **Candles**: 43,157 (1-minute)
- **Source**: BingX Perpetual Futures
- **Characteristics**:
  - Price: $0.2304 → $0.2149 (-6.73%)
  - Volatility: 0.087% avg per candle (very stable)
  - Explosive moves (>1%): Only 0.1% of candles
  - Much calmer than typical meme coins

## Task
Perform comprehensive pattern discovery and strategy research on PI/USDT:

### 1. Baseline Analysis
- Calculate key metrics: volatility, ATR, volume patterns
- Compare to existing strategy coins (FARTCOIN, DOGE, TRUMPSOL, PIPPIN)
- Identify PI's unique characteristics vs meme coins

### 2. Pattern Discovery
Test multiple strategy concepts:
- **Mean Reversion** (like TRUMPSOL Contrarian)
- **Volume Zones** (like DOGE)
- **ATR Expansion** (like FARTCOIN)
- **EMA Crosses** (like PIPPIN Fresh Crosses)
- **Volatility Breakouts**
- **Time-based patterns** (session analysis)
- **Any other patterns you discover in the data**

### 3. Strategy Development
For each promising pattern:
- Test multiple configurations
- Analyze winner vs loser trades
- Optimize entry/exit rules
- Calculate Return/DD ratio (primary metric)
- Validate with proper fees (0.10% round-trip for perpetual)

### 4. Deliverables

**Analysis Script(s)**:
- `pi_pattern_discovery.py` - initial exploration
- `pi_[strategy_name]_backtest.py` - focused strategy tests
- Clear, well-commented code

**Results Files**:
- `results/pi_pattern_analysis.csv` - all patterns tested
- `results/pi_[best_strategy]_trades.csv` - winning strategy details
- Charts/visualizations if helpful

**Report**:
- `results/PI_STRATEGY_REPORT.md` with:
  - Executive summary (best strategy found)
  - Pattern discovery process
  - Strategy comparison table
  - Winner/loser analysis
  - Final recommendation with config

## Success Criteria
Find at least ONE strategy with:
- Return/DD ratio > 3.0x
- Win rate > 40%
- Minimum 30 trades over 30 days
- Realistic fees included (0.10% round-trip)
- Clear entry/exit rules
- Production-ready configuration

## Important Notes
- PI is MUCH more stable than meme coins (0.087% avg vs 0.4%+ for FARTCOIN)
- May require different approach than explosive meme strategies
- Consider if lower volatility = harder to profit or just different patterns
- Be creative - don't just copy existing strategies blindly
- Focus on Return/DD ratio as primary ranking metric

## Reference
Existing strategies for comparison:
1. PIPPIN Fresh Crosses: 12.71x R/DD
2. FARTCOIN ATR Limit: 8.44x R/DD
3. DOGE Volume Zones: 10.75x R/DD (outlier-dependent)
4. TRUMPSOL Contrarian: 5.17x R/DD

Can PI match or beat these?
