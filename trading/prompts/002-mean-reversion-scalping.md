<objective>
Create a mean reversion scalping strategy for FARTCOIN/USDT 1-minute data that exploits extreme price deviations to achieve 8:1+ risk:reward ratios. Capitalize on the tendency of volatile assets to snap back to equilibrium after overextensions.

This strategy targets panic moves and exhaustion points where price has moved too far too fast.
</objective>

<context>
Working with OHLCV data (timestamp, open, high, low, close, volume) from FARTCOIN/USDT 1-minute candles.

Mean reversion premise:
- Extreme moves are unsustainable
- Price tends to return to average/equilibrium
- Memecoin volatility creates frequent overextensions
- 1-minute timeframe = quick reversals = rapid scalping opportunities

Target: 8:1 R:R by entering at exhaustion points with tiny stops and riding the snapback.
</context>

<requirements>
1. Load and analyze FARTCOIN/USDT CSV data
2. Develop mean reversion strategy using ONLY OHLCV data:
   - Identify overextended price moves (statistical extremes)
   - Detect reversal signals (exhaustion patterns)
   - Enter counter-trend with precision timing
   - Ultra-tight stops (beyond recent extreme)
   - Large targets (return to mean + overshoot)
3. Calculate indicators for mean reversion:
   - Bollinger Bands (2, 3, 4 standard deviations)
   - RSI (Relative Strength Index) for overbought/oversold
   - VWAP or SMA for dynamic mean level
   - Price distance from moving average (% deviation)
   - Volume exhaustion signals
4. Backtest and generate metrics:
   - Win rate
   - Risk:reward ratio distribution
   - Profit factor
   - Drawdown analysis
   - Trade frequency
5. Include filters to avoid catching falling knives
6. Account for 0.1% fees per side (0.2% round trip)
</requirements>

<implementation>
Strategy logic:

1. **Overextension Detection**:
   - Price touches or exceeds 3rd Bollinger Band
   - RSI above 80 (overbought) or below 20 (oversold)
   - Price is 5%+ away from 20-period SMA
   - Large single candle move (2x+ recent ATR)

2. **Reversal Confirmation**:
   - Volume climax (huge volume spike)
   - Long wick on candle (rejection of extreme)
   - Small body on exhaustion candle (indecision)
   - Next candle closes back toward mean

3. **Entry Rules**:
   - Wait for confirmation candle (don't catch falling knife)
   - Enter at open of candle after reversal signal
   - Only trade if volume suggests exhaustion not continuation

4. **Stop Loss**:
   - Place stop 0.2-0.3% beyond the extreme point
   - If overextended high: stop 0.2% above high
   - If overextended low: stop 0.2% below low
   - Extremely tight stops enable 8R targets

5. **Profit Targets**:
   - Primary: Return to VWAP or 20-SMA (usually 5-10 candles)
   - Extended: Overshoot to opposite side (8R+)
   - Scale out: 50% at mean, 50% at 8R

6. **Exit Logic**:
   - Target hit
   - Stop triggered
   - Mean reached but no continuation (close partial)
   - Maximum holding period: 20 minutes

WHY this works:
- Emotional extremes = overreaction = opportunity
- Tiny stop = can lose many times but one 8R winner covers it
- Mean reversion is strongest edge in high volatility assets
- Volume exhaustion = smart money exiting, dumb money exhausted
</implementation>

<output>
Create these files in `./strategies/`:

1. `mean-reversion-strategy.md`
   - Complete strategy documentation
   - Entry/exit rules with visual examples
   - Risk management system
   - Backtest summary and analysis

2. `mean-reversion-strategy.py`
   - Python code using pandas/numpy
   - CSV data loader
   - Indicator calculations (BB, RSI, VWAP, SMA)
   - Backtesting engine with trade logging
   - Performance analytics

3. `mean-reversion-trades.csv`
   - Trade log: entry, stop, target, exit, pnl, R-multiple
   - Include reason for entry and exit

4. `mean-reversion-equity.csv`
   - Cumulative equity over time
   - Drawdown tracking
</output>

<verification>
Before completion, verify:

1. ✓ Data loads correctly from FARTCOIN CSV
2. ✓ Strategy generates sufficient trades (30+ for validity)
3. ✓ Risk:reward on winning trades averages 7:1 or better
4. ✓ Win rate is reasonable (need ~15%+ for profitability at 8R)
5. ✓ No catastrophic drawdowns (max 20-30%)
6. ✓ Profit factor > 1.3 (profitable after fees)
7. ✓ Indicators calculate correctly (spot check values)
8. ✓ Stop losses are realistic given candle volatility

Edge case testing:
- Strong trending markets (strategy should stand aside)
- Multiple fake reversals in a row (risk of ruin)
- Extreme volatility spikes (stops get hit instantly)
</verification>

<success_criteria>
- Achieves 8:1 average R:R on profitable mean reversion trades
- Positive expected value: System is mathematically profitable
- Win rate sufficient to compensate for tight stops (15-25%)
- Clear identification of when NOT to trade (trend filter)
- Code executes cleanly and produces consistent results
- Strategy explanation includes the behavioral/statistical edge
- Results demonstrate edge exists in the FARTCOIN data specifically
</success_criteria>