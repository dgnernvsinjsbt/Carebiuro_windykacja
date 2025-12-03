# Intelligent Adaptive Trading System

## Philosophy: Think First, Code Second

**Core Principle:** Before writing any backtest code, analyze the data like a master trader would. Understand the market's "personality" during each period. Only then build systems that trade WITH the market, never against it.

The goal is NOT to find parameters that "would have worked" through brute-force optimization. The goal is to UNDERSTAND why certain approaches worked during specific conditions, then build a system that recognizes those conditions and applies the right approach.

---

## Phase 1: Market Archaeology (Intelligence Gathering)

### Step 1.1: Monthly Market Autopsy

Go through the data month by month. For each month, answer these questions:

```
MONTH: [Date Range]

1. PRICE ACTION SUMMARY
   - Open → Close: What was the overall move?
   - High/Low range: How much volatility?
   - Character: Trending? Choppy? Explosive? Grinding?

2. TREND STRUCTURE
   - Was there a clear trend or was it ranging?
   - How many trend reversals occurred?
   - Were moves smooth or violent?

3. VOLATILITY PROFILE
   - Average daily range (%)
   - Were there volatility clusters? When?
   - Any black swan events?

4. HINDSIGHT OPTIMAL STRATEGY
   - If you knew the future, what would be the PERFECT way to trade this month?
   - Long-only? Short-only? Both? Sit out?
   - Aggressive or conservative?
   - How many trades would be optimal?
```

### Step 1.2: Winning Strategy Identification

For each month, determine what strategy WOULD HAVE been most profitable:

```
STRATEGY PROFILES TO EVALUATE:

A) TREND FOLLOWING (LONGS)
   - EMA pullbacks in uptrends
   - Breakout entries
   - Best when: Strong directional moves

B) TREND FOLLOWING (SHORTS)
   - EMA rejections in downtrends
   - Breakdown entries
   - Best when: Clear bearish momentum

C) MEAN REVERSION
   - Buy oversold, sell overbought
   - Range trading
   - Best when: Sideways, bounded markets

D) MOMENTUM BURSTS
   - Catch explosive moves
   - Wide stops, big targets
   - Best when: Volatility expansion

E) SIT OUT / CASH
   - No trades
   - Best when: Chop, no edge, uncertainty
```

For each month, rank these A-E and explain WHY.

### Step 1.3: Condition → Strategy Mapping

After analyzing all months, build a lookup table:

```
MARKET CONDITIONS                    → OPTIMAL STRATEGY
─────────────────────────────────────────────────────────
Price trending up + low volatility   → Aggressive longs, high leverage
Price trending up + high volatility  → Conservative longs, reduced size
Price trending down + low volatility → Aggressive shorts
Price trending down + high volatility→ Conservative shorts
Sideways + low volatility            → Mean reversion or sit out
Sideways + high volatility           → SIT OUT (chop kills)
Post-crash recovery                  → Careful longs, tight stops
Blow-off top                         → Prepare shorts, wait for confirmation
```

---

## Phase 2: Pattern Recognition Engine

### Step 2.1: Define Measurable Conditions

Translate your qualitative observations into quantifiable signals:

```
TREND DIRECTION (what you observe → how to measure)
─────────────────────────────────────────────────────
"Price is trending up"     → Price > EMA20 > EMA50 > EMA200
"Weak uptrend"             → Price > EMA20, but EMA20 < EMA50
"Strong downtrend"         → Price < all EMAs, lower highs/lows
"No clear trend"           → EMAs tangled, price crossing frequently

VOLATILITY STATE
─────────────────────────────────────────────────────
"Low volatility"           → ATR < 25th percentile of 90-day ATR
"Normal volatility"        → ATR between 25th-75th percentile
"High volatility"          → ATR > 75th percentile
"Extreme/dangerous"        → ATR > 95th percentile OR recent 10%+ daily move

MARKET CHARACTER
─────────────────────────────────────────────────────
"Trending cleanly"         → ADX > 25, few EMA crosses
"Choppy/ranging"           → ADX < 20, many EMA crosses (>3 in 20 candles)
"Volatile but directional" → High ATR + ADX > 25
"Dead/boring"              → Low ATR + low ADX
```

### Step 2.2: Regime Classification

Create clear regime buckets based on your analysis:

```
REGIME 1: BULL RUN
Conditions: Price > EMA50, EMA20 > EMA50, ADX > 25
Historical observation: "These months had X% return, longs worked great"
Optimal approach: Aggressive EMA pullback longs, 7-10x leverage

REGIME 2: BEAR TREND
Conditions: Price < EMA50, EMA20 < EMA50, ADX > 25
Historical observation: "These months crushed long-only strategies"
Optimal approach: EMA rejection shorts, 5-7x leverage

REGIME 3: HIGH VOL BULL
Conditions: Price > EMA50 but ATR > 75th percentile
Historical observation: "Big moves but also big whipsaws"
Optimal approach: Reduced position size, wider stops, 3-5x leverage

REGIME 4: HIGH VOL BEAR
Conditions: Price < EMA50, ATR > 75th percentile
Historical observation: "Fast crashes, hard to catch perfectly"
Optimal approach: Small short positions, or sit out

REGIME 5: CHOP ZONE
Conditions: ADX < 20, multiple EMA crosses
Historical observation: "Death by 1000 cuts - no strategy worked"
Optimal approach: DO NOT TRADE - preserve capital

REGIME 6: RECOVERY/TRANSITION
Conditions: After major drawdown, price reclaiming EMAs
Historical observation: "Tricky - false starts common"
Optimal approach: Small longs, tight stops, prove itself first
```

---

## Phase 3: Strategy Playbook

### For Each Regime, Define Exact Rules:

```
REGIME: BULL RUN
═══════════════════════════════════════════════════════════

ENTRY SIGNALS (pick best one based on historical analysis):
□ EMA20 Pullback: Close > EMA20, low touches EMA20, green candle
□ Breakout: New local high with volume > 1.2x average
□ Support bounce: Touch of rising trendline + reversal candle

POSITION SIZE:
Based on your month-by-month analysis, what worked?
□ Full size (100% of risk capital)
□ 70% size
□ 50% size

LEVERAGE:
What leverage produced best risk-adjusted returns historically?
□ 10x (aggressive)
□ 7x (moderate)
□ 5x (conservative)

STOP LOSS:
□ Below entry candle low
□ 1.5x ATR below entry
□ Below EMA20

TAKE PROFIT:
□ Fixed candle hold (4, 6, 8 candles)
□ R:R based (2:1, 3:1)
□ Trail with EMA

TIME FILTER:
Based on your analysis, which sessions worked best?
□ US session (14-22 UTC)
□ Asia session (0-8 UTC)
□ No filter needed
```

Repeat this playbook definition for each regime.

---

## Phase 4: Validation Backtest

Now - and ONLY now - write Python code to validate your hypotheses.

### Step 4.1: Regime Detection Code

```python
def detect_regime(row, lookback_data):
    """
    Classify current market regime based on conditions
    identified during Phase 1-2 analysis.
    """
    # Calculate indicators
    price = row['close']
    ema20 = row['ema20']
    ema50 = row['ema50']
    atr_percentile = calculate_atr_percentile(row, lookback_data)
    adx = row['adx']
    ema_crosses = count_recent_ema_crosses(lookback_data, periods=20)

    # Regime classification (based on YOUR analysis)
    if price > ema50 and ema20 > ema50 and adx > 25:
        if atr_percentile < 75:
            return 'BULL_RUN'
        else:
            return 'HIGH_VOL_BULL'

    elif price < ema50 and ema20 < ema50 and adx > 25:
        if atr_percentile < 75:
            return 'BEAR_TREND'
        else:
            return 'HIGH_VOL_BEAR'

    elif adx < 20 or ema_crosses > 3:
        return 'CHOP_ZONE'

    else:
        return 'TRANSITION'
```

### Step 4.2: Strategy Selector

```python
# This mapping comes FROM your Phase 1-2 analysis
# NOT from blind parameter optimization

REGIME_STRATEGIES = {
    'BULL_RUN': {
        'direction': 'LONG',
        'entry': 'ema20_pullback',
        'leverage': 7,
        'position_size': 1.0,
        'stop_method': 'candle_low',
        'exit_candles': 6,
    },
    'BEAR_TREND': {
        'direction': 'SHORT',
        'entry': 'ema20_rejection',
        'leverage': 5,
        'position_size': 0.8,
        'stop_method': 'candle_high',
        'exit_candles': 4,
    },
    'HIGH_VOL_BULL': {
        'direction': 'LONG',
        'entry': 'ema20_pullback',
        'leverage': 3,
        'position_size': 0.5,
        'stop_method': 'atr_stop',
        'exit_candles': 4,
    },
    'HIGH_VOL_BEAR': {
        'direction': 'SHORT',
        'entry': 'ema20_rejection',
        'leverage': 3,
        'position_size': 0.3,
        'stop_method': 'atr_stop',
        'exit_candles': 4,
    },
    'CHOP_ZONE': {
        'direction': 'NONE',  # DO NOT TRADE
        'position_size': 0,
    },
    'TRANSITION': {
        'direction': 'CAUTIOUS',
        'leverage': 2,
        'position_size': 0.25,
        'exit_candles': 4,
    },
}
```

### Step 4.3: Walk-Forward Validation

```python
def run_intelligent_backtest(df):
    """
    Month-by-month backtest that:
    1. Detects current regime
    2. Applies appropriate strategy from playbook
    3. Tracks results by regime for analysis
    """
    results = []

    for idx, row in df.iterrows():
        # Get recent data for context
        lookback = df.loc[:idx].tail(100)

        # Detect regime (using YOUR intelligence, not optimization)
        regime = detect_regime(row, lookback)

        # Get strategy for this regime
        strategy = REGIME_STRATEGIES[regime]

        # Skip if CHOP_ZONE or no position size
        if strategy['direction'] == 'NONE' or strategy['position_size'] == 0:
            continue

        # Check for entry signal
        if check_entry_signal(row, strategy):
            trade = execute_trade(row, strategy, df)
            trade['regime'] = regime
            results.append(trade)

    return results
```

---

## Phase 5: Analysis & Refinement

### Step 5.1: Regime Performance Breakdown

After backtest, analyze results BY REGIME:

```
REGIME ANALYSIS REPORT
═══════════════════════════════════════════════════════════

BULL_RUN:
- Trades: 45
- Win Rate: 58%
- Avg P&L: +2.3%
- Verdict: Strategy working as expected ✓

BEAR_TREND:
- Trades: 28
- Win Rate: 52%
- Avg P&L: +1.8%
- Verdict: Shorts protecting capital ✓

CHOP_ZONE:
- Trades: 0 (correctly avoided)
- Verdict: Good discipline ✓

HIGH_VOL_BULL:
- Trades: 12
- Win Rate: 42%
- Avg P&L: +0.5%
- Verdict: Reduced size helped, consider sitting out

═══════════════════════════════════════════════════════════

KEY INSIGHT: Did the regime detection CORRECTLY identify
market conditions? If not, refine detection criteria.
```

### Step 5.2: Monthly Attribution

Show that your intelligent approach outperforms blind optimization:

```
MONTH-BY-MONTH COMPARISON
═══════════════════════════════════════════════════════════

Month       | Intelligent | Blind Optimize | Difference
------------+-------------+----------------+-----------
2024-03     | +45%        | +52%           | -7% (optimize wins in bull)
2024-04     | +23%        | +18%           | +5% (intelligence wins)
2024-05     | -8%         | -25%           | +17% (avoided chop)
2024-06     | +15%        | -40%           | +55% (shorts saved us)
...

TOTAL:      | +180%       | -45%           | Intelligence wins
```

---

## Implementation Checklist

```
PHASE 1: Market Archaeology
□ Load full dataset
□ Create monthly summary for EACH month
□ Document: price action, volatility, optimal strategy
□ Build condition → strategy mapping table

PHASE 2: Pattern Recognition
□ Define measurable conditions for each observation
□ Create regime classification rules
□ Document WHY each regime should use specific strategy

PHASE 3: Strategy Playbook
□ Define exact entry/exit rules per regime
□ Set leverage and position sizing per regime
□ Define conditions to sit out (CRITICAL)

PHASE 4: Validation
□ Implement regime detector
□ Implement strategy selector
□ Run walk-forward backtest
□ Generate per-regime statistics

PHASE 5: Refinement
□ Analyze regime detection accuracy
□ Compare intelligent vs blind optimization
□ Document lessons learned
□ Create final trading playbook
```

---

## Constraints

- Round-trip fees: 0.10%
- Max leverage: 10x
- 100% capital per trade (adjusted by position sizing)
- No overnight positions
- Data: /workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv

---

## Success Criteria

A successful intelligent system should:

1. **Demonstrate understanding** - You can explain WHY each month required a different approach
2. **Survive the drawdown** - Profitable or minimal loss during the 79% crash (because it shorted or sat out)
3. **Beat blind optimization** - Higher returns AND lower drawdown than parameter grid search
4. **Trade with the market** - Longs in bulls, shorts in bears, cash in chop
5. **Fewer but better trades** - Quality over quantity, each trade has clear reasoning

---

## The Key Question

Before each trade, you should be able to answer:

> "Given current conditions (trend X, volatility Y, market character Z),
> my analysis shows that strategy A has worked best historically.
> Therefore I am taking this trade with B leverage and C position size,
> with stop at D and exit after E candles."

If you can't answer this clearly, don't trade.

---

## Output Files

```
/trading/results/monthly_market_analysis.md      # Your Phase 1 analysis
/trading/results/regime_strategy_mapping.csv     # Condition → Strategy table
/trading/results/intelligent_backtest.csv        # Trade-by-trade results
/trading/results/regime_performance.csv          # Performance by regime
/trading/results/intelligent_vs_blind.png        # Comparison chart
```
