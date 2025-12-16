<objective>
Test the V7 "Trend + Distance 2%" winning strategy across all 4 coin pairs (FARTCOIN, PI, MELANIA, PENGU) and optimize parameters for each coin individually to find the best risk:reward ratios.

This analysis will validate whether the 8.88x R:R achieved on FARTCOIN is:
1. **Robust** - Does it work across multiple assets?
2. **Coin-specific** - Do different coins need different parameters?
3. **Reliable** - Can we identify which coins work best with this approach?

The goal is to find the optimal configuration for each coin and potentially create a multi-coin portfolio strategy.
</objective>

<context>
You have 30 days of 1-minute OHLCV data for 4 memecoins:
- fartcoin_usdt_1m_lbank.csv (43,200 candles)
- pi_usdt_1m_lbank.csv (43,201 candles)
- melania_usdt_1m_lbank.csv (43,202 candles)
- pengu_usdt_1m_lbank.csv (43,203 candles)

The V7 winning strategy achieved on FARTCOIN:
- **R:R Ratio: 8.88x** (Return: +20.08%, Max DD: -2.26%)
- **Key filters:**
  - Strong trend: Both 50 & 200 SMA aligned
  - Distance filter: 2%+ from 50 SMA (THE CRITICAL FILTER)
  - Fixed 5:1 R:R per trade (15x ATR TP, 3x ATR SL)
  - Dynamic position sizing (1.5-5%)
  - Patterns: Explosive Bearish Breakdown + Explosive Bullish Breakout

The base implementation is in: @strategies/explosive-v7-advanced.py

However, you should NOT assume the exact same parameters work for all coins. Different assets have different:
- Volatility characteristics (PENGU likely more volatile than PI)
- Trend strength (some coins may be more directional)
- Optimal entry thresholds (body%, volume multiplier, wick ratios)
- Risk:reward per trade (maybe 4:1 or 6:1 works better than 5:1 for some)
</context>

<requirements>
For EACH of the 4 coins, you must:

1. **Test the baseline V7 config first** (exact same parameters as FARTCOIN)
   - This gives us a comparison baseline

2. **Optimize key parameters** through systematic testing:
   - Body threshold: Test 0.8%, 1.0%, 1.2%, 1.5%
   - Volume multiplier: Test 2.0x, 2.5x, 3.0x, 3.5x
   - Wick threshold: Test 0.25, 0.35, 0.45
   - SMA distance: Test 1.5%, 2.0%, 2.5%, 3.0%
   - TP/SL ratios: Test 3:1, 4:1, 5:1, 6:1 (per trade R:R)
   - RSI ranges: Test different overbought/oversold levels

3. **Find the best configuration for each coin** that maximizes R:R ratio

4. **Create a comparative analysis** showing:
   - Which coin works best with this strategy
   - How parameters differ across coins
   - Whether the strategy is robust or overfitted
   - Portfolio potential (combining multiple coins)
</requirements>

<implementation>
Create a new script: `strategies/multi-coin-optimizer.py`

The script should:

1. **Use the V7 base logic** from explosive-v7-advanced.py as the starting point

2. **For each coin, test multiple configurations:**
   - Don't test every possible combination (too many)
   - Use smart parameter sweeps focusing on the most impactful variables:
     - SMA distance (1.5%, 2.0%, 2.5%, 3.0%)
     - Body threshold (0.8%, 1.0%, 1.2%)
     - TP multiplier (12x, 15x, 18x ATR for 4:1, 5:1, 6:1 R:R)
   - Maybe 8-12 configurations per coin (not 100+)

3. **Track these metrics for each test:**
   - Total return %
   - Max drawdown %
   - R:R ratio (return / drawdown)
   - Number of trades
   - Win rate
   - Profit factor
   - Avg win vs avg loss

4. **Output comprehensive results:**
   - CSV file per coin: `strategies/optimization-results-[coin].csv`
   - Summary comparison: `strategies/MULTI-COIN-RESULTS.md`
   - Best config per coin saved to: `strategies/best-config-[coin].json`

5. **Consider volatility differences:**
   - PENGU (lowest price, $0.009-0.016) likely very volatile
   - PI (mid price, $0.21-0.28) moderate volatility
   - MELANIA (mid price, $0.098-0.23) likely volatile (135% range!)
   - Adjust ATR multipliers if needed based on typical ATR percentiles

6. **Validation checks:**
   - Flag configurations with <10 trades (too selective, unreliable)
   - Flag configurations with >100 trades (too aggressive, likely poor quality)
   - Flag win rates <30% or >70% (suspicious, possible overfitting)
</implementation>

<optimization_strategy>
Use a smart search approach:

**Phase 1: Baseline Test**
- Run exact V7 config on all 4 coins
- Establish baseline R:R for each

**Phase 2: Distance Filter Sweep** (most impactful from V7 findings)
- Test 1.5%, 2.0%, 2.5%, 3.0% SMA distance on each coin
- Keep all other params at V7 baseline

**Phase 3: Entry Threshold Tuning**
- Take best distance from Phase 2
- Test body thresholds: 0.8%, 1.0%, 1.2%
- Test volume multipliers: 2.0x, 2.5x, 3.0x

**Phase 4: Risk:Reward Optimization**
- Take best from Phase 3
- Test TP multipliers: 12x (4:1), 15x (5:1), 18x (6:1), 21x (7:1)

This gives ~40 tests per coin (4 coins × 40 = 160 total backtests) which is manageable.
</optimization_strategy>

<output>
Create these files:

1. **Main script:** `./strategies/multi-coin-optimizer.py`
   - Contains the optimization logic
   - Reuses V7 backtest engine
   - Runs all tests automatically

2. **Results per coin:**
   - `./strategies/optimization-results-fartcoin.csv`
   - `./strategies/optimization-results-pi.csv`
   - `./strategies/optimization-results-melania.csv`
   - `./strategies/optimization-results-pengu.csv`

3. **Best configurations:**
   - `./strategies/best-config-fartcoin.json`
   - `./strategies/best-config-pi.json`
   - `./strategies/best-config-melania.json`
   - `./strategies/best-config-pengu.json`

4. **Comprehensive analysis:** `./strategies/MULTI-COIN-RESULTS.md`
   - Comparison table of all 4 coins
   - Best R:R found per coin
   - Parameter sensitivity analysis
   - Portfolio recommendations
   - Robustness assessment (is 8.88x an outlier or repeatable?)
</output>

<analysis_questions>
In the final MULTI-COIN-RESULTS.md, answer:

1. **Which coin has the best R:R potential?**
2. **Are the optimal parameters similar across coins or very different?**
   - If similar → strategy is robust
   - If different → each coin needs custom tuning
3. **Does the 2% distance filter work universally or just on FARTCOIN?**
4. **What's the typical R:R range we can expect?** (e.g., 5-10x realistic?)
5. **Should we run a portfolio approach?** (trade all 4 coins simultaneously)
6. **Which coins should be avoided?** (if any show poor results)
7. **Is there evidence of overfitting?** (dramatically different results on same strategy)
</analysis_questions>

<verification>
Before declaring complete:

1. ✓ All 4 coins tested with baseline V7 config
2. ✓ Optimization phases completed for each coin
3. ✓ CSV results files generated for all coins
4. ✓ Best configs saved as JSON
5. ✓ MULTI-COIN-RESULTS.md created with comprehensive analysis
6. ✓ Each coin has at least one configuration with 10+ trades
7. ✓ Analysis answers all 7 questions above
8. ✓ Clear recommendation provided on which coin(s) to trade live
</verification>

<success_criteria>
- Optimization completes for all 4 coins without errors
- At least one configuration per coin achieves R:R > 3.0x
- MULTI-COIN-RESULTS.md provides clear, actionable insights
- User can immediately see which coin offers best opportunity
- Parameter differences across coins are clearly explained
- Robustness of 8.88x R:R is validated or debunked
</success_criteria>

<constraints>
- Don't test every possible combination (combinatorial explosion)
- Focus on the most impactful parameters (distance, body%, TP ratio)
- Keep test count manageable (~40 tests per coin = 160 total)
- Flag suspicious results (too few trades, impossible win rates)
- If a coin shows consistently poor results (<2x R:R), document why
- Don't overcomplicate - the V7 logic is the base, just tune parameters
</constraints>
