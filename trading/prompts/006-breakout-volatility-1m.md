<objective>
Develop a profitable 1-minute breakout/volatility expansion strategy for FARTCOIN that captures explosive moves after consolidation for rapid compounding with R:R ratio of 8+.

This will test breakout entries from tight ranges with volatility confirmation for maximum profit potential. The goal is to catch the beginning of strong directional moves.
</objective>

<context>
Current baseline: 30m EMA 3/15 SHORT strategy achieves 942% return with 17.05 R:R over 11 months.

You have TOTAL FREEDOM to design this strategy. Focus on breakout/volatility approaches:
- Bollinger Band squeezes (volatility contraction) followed by expansion
- Price consolidation patterns (triangles, flags, ranges) then breakout
- ATR contraction/expansion cycles
- Volume breakouts (massive volume spike + price move)
- Support/resistance level breaks with momentum
- Donchian Channel breakouts (new highs/lows)

Available data: `fartcoin_1m_90days.csv` (~11,000 1-minute candles, ~7.5 days of data)

Key insight: After periods of low volatility consolidation, crypto often explodes in one direction. Catching these early with good R:R can be highly profitable.
</context>

<requirements>
1. Design and backtest a breakout/volatility strategy on 1-minute timeframe
2. Target: R:R ratio 8+ (10+ preferred)
3. Test multiple consolidation/breakout patterns - go beyond basics
4. Use dynamic position sizing: +25%/-3% (proven winner)
5. Optimize entry timing and confirmation signals
6. Include fees: 0.01% total (0.005% per side)
7. Filter false breakouts (must have follow-through potential)
</requirements>

<strategy_ideas>
Consider testing these breakout approaches (pick 1-2 to thoroughly optimize):

**Bollinger Band Squeeze**:
- Detect: BB width narrows to minimum (volatility squeeze)
- Entry: Price breaks out of bands + volume confirmation
- Confirmation: Momentum indicator (RSI, MACD) confirms direction
- Exit: Ride expansion with trailing stop or fixed R:R
- SL: Opposite side of consolidation range

**Range Breakout**:
- Identify: 10-30 bars of tight price action (< 1% range)
- Entry: Price breaks above/below range with strong candle
- Confirmation: Volume 2x+ average, no immediate rejection
- Exit: Extension of breakout move or trailing stop
- SL: Back inside the consolidation range

**ATR Expansion**:
- Detect: ATR drops below threshold (low volatility)
- Entry: ATR starts expanding + price confirms direction
- Confirmation: Directional EMA cross or momentum signal
- Exit: ATR peaks or fixed R:R target
- SL: Tight stop based on recent consolidation

**Volume Breakout**:
- Detect: Volume spikes to 3x+ average volume
- Entry: Price makes new high/low simultaneously with volume
- Confirmation: Follow-through in next 1-2 bars
- Exit: Quick profit or trail behind volatility
- SL: Before volume spike price level

**Donchian Breakout**:
- Track: Highest high and lowest low over N bars (20-50)
- Entry: Price breaks above/below Donchian channel
- Confirmation: Momentum + volume supports breakout
- Exit: Opposite channel or fixed R:R
</strategy_ideas>

<implementation>
1. Load `fartcoin_1m_90days.csv`
2. Calculate indicators: Bollinger Bands, ATR, Volume MA, Donchian Channels, RSI, EMA
3. Implement consolidation detection logic (low volatility periods)
4. Design breakout entry conditions with confirmation
5. Add false breakout filters (volume, momentum, follow-through)
6. Determine optimal SL placement and TP targets
7. Apply +25%/-3% position sizing (0.5x-2.0x caps)
8. Calculate comprehensive metrics with focus on breakout success rate
9. Compare against other strategy types

WHY breakouts on 1m:
- Crypto has explosive volatility expansions
- Early entry in breakouts provides best R:R
- Consolidations are frequent on 1m, providing many opportunities
- Clear risk definition (consolidation range)
- High profit potential when breakout follows through
</implementation>

<optimization>
Deeply explore parameter combinations. Test:
- Consolidation detection (BB width < threshold, ATR < threshold, range % < X)
- Breakout confirmation (volume multiplier: 1.5x, 2x, 3x)
- Momentum filters (RSI directional, EMA alignment, MACD)
- Consolidation length (minimum 10 bars, 15 bars, 20 bars)
- Breakout strength (candle body size, percentage move)
- Entry timing (immediate, wait for retest, wait for continuation)
- SL placement (inside range, below/above consolidation, ATR-based)
- TP targets (fixed R:R vs trailing stop vs volatility-based exit)

Use grid search to find optimal combination of parameters.
</optimization>

<output>
Create comprehensive backtest script:
- `./trading/fartcoin_1m_breakout_volatility.py` - Main strategy implementation

Include in results:
- Total return % and final equity
- Max drawdown %
- R:R ratio (MUST be 8+)
- Win rate and trade count
- Average win vs average loss
- Breakout success rate (% that follow through vs fail)
- False breakout rate
- Average consolidation duration before entry
- Equity curve visualization
- Breakout quality analysis (what confirms successful breakouts)
</output>

<success_criteria>
- Strategy achieves R:R ratio of 8+ (ideally 10+)
- Total return exceeds 200% over test period
- Breakout success rate is reasonable (45%+ of breakouts follow through)
- False breakout rate is minimized through filtering
- Maximum drawdown is controlled (< 60%)
- Clear visualization showing equity growth
- Documented optimal breakout confirmation signals
</success_criteria>

<verification>
Before declaring complete:
1. Verify R:R ratio meets 8+ requirement
2. Confirm breakout detection logic is sound (not catching noise)
3. Validate that false breakouts are filtered effectively
4. Check position sizing implementation (+25%/-3%)
5. Ensure no lookahead bias in consolidation/breakout detection
6. Compare results to momentum (004) and mean reversion (005) strategies
7. Assess which strategy type performs best on FARTCOIN 1m data
</verification>
