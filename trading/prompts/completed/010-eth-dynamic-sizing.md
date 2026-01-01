<objective>
Discover if dynamic position sizing (instead of fixed size) improves profit-to-drawdown ratio on ETH/USDT, achieving >4:1 ratio.

Goal: Test whether adjusting position size based on market conditions, confidence, or past performance creates better risk-adjusted returns.

Success target: 40%+ total return with <10% max drawdown through intelligent sizing
</objective>

<context>
Data source: `./trading/eth_usdt_1m_lbank.csv` (43,201 candles, 30 days from LBank)
Current approach: Fixed position size per trade (e.g., always $100 at 10x leverage = $1000 position)
Alternative: Vary size based on conditions

WHY dynamic sizing:
- Higher confidence setups → larger size → maximize good opportunities
- High volatility periods → smaller size → reduce risk
- Winning streaks → scale up → compound gains (anti-martingale)
- Losing streaks → scale down → preserve capital

This can significantly improve profit/DD ratio by risking more when odds are favorable and less when uncertain.
</context>

<research>
Before implementing, analyze:
1. **Volatility Patterns**
   - Calculate rolling ATR% over different windows (20, 50, 100 bars)
   - Identify high vs low volatility periods
   - Check if strategy win rate varies with volatility

2. **Confidence Scoring**
   - Do trades with multiple confirmations win more often?
   - Example: RSI oversold + BB lower band + high volume = high confidence
   - Can you score each setup 0-100?

3. **Performance Streaks**
   - How long are typical winning/losing streaks?
   - What's the risk of over-sizing during streaks?
   - Is anti-martingale profitable on this dataset?

Use findings to design sizing rules.
</research>

<requirements>
Test multiple dynamic sizing approaches:

1. **Volatility-Based Sizing**
   - Measure current ATR% vs average ATR%
   - Low volatility (ATR < avg × 0.8) → 1.5x normal size
   - Medium volatility → 1.0x normal size
   - High volatility (ATR > avg × 1.2) → 0.5x normal size
   - Rationale: Low volatility = ranging = better for mean reversion
   - Test different thresholds and multipliers

2. **Confidence-Based Sizing**
   - Score each trade setup based on filters:
     - RSI extreme (>75 or <25): +20 points
     - BB position (<0.1 or >0.9): +20 points
     - High volume (>2.5x avg): +20 points
     - Trend alignment: +20 points
     - Time session (optimal hours): +20 points
   - Size based on score:
     - 80-100: 1.5x size (high confidence)
     - 60-79: 1.0x size (medium)
     - 40-59: 0.7x size (low confidence)
     - <40: skip trade
   - Test different scoring systems

3. **Anti-Martingale (Winning Streak Scaling)**
   - Track consecutive wins/losses
   - After 2 wins in a row → 1.3x size
   - After 3 wins in a row → 1.5x size
   - After any loss → reset to 1.0x size
   - Never increase after losses (this would be martingale - dangerous)
   - Test different scaling factors

4. **Kelly Criterion (Advanced)**
   - Calculate optimal bet size: f = (bp - q) / b
     - b = odds (avg_win / abs(avg_loss))
     - p = win rate
     - q = 1 - p
   - Use fractional Kelly (e.g., 0.25× Kelly) for safety
   - Recalculate Kelly every N trades based on recent performance

5. **Hybrid Approach**
   - Combine volatility + confidence
   - Example: base_size × volatility_mult × confidence_mult
   - Test if combination works better than single factor

For each approach:
- Compare vs fixed sizing baseline
- Measure profit/DD ratio improvement
- Track maximum position size reached
- Verify sizing doesn't exceed leverage limits
</requirements>

<implementation>
Add dynamic sizing logic to backtest:

```python
def calculate_position_size(row, recent_trades, base_size, method='fixed'):
    """Calculate position size based on method"""

    if method == 'fixed':
        return base_size

    elif method == 'volatility':
        atr_ratio = row['atr_pct'] / avg_atr_pct
        if atr_ratio < 0.8:
            return base_size * 1.5  # Low volatility
        elif atr_ratio > 1.2:
            return base_size * 0.5  # High volatility
        else:
            return base_size

    elif method == 'confidence':
        score = calculate_confidence_score(row)
        if score >= 80:
            return base_size * 1.5
        elif score >= 60:
            return base_size * 1.0
        else:
            return base_size * 0.7

    elif method == 'anti_martingale':
        wins_in_row = count_recent_wins(recent_trades)
        if wins_in_row >= 3:
            return base_size * 1.5
        elif wins_in_row >= 2:
            return base_size * 1.3
        else:
            return base_size

    elif method == 'kelly':
        kelly_fraction = calculate_kelly(recent_trades)
        return base_size * kelly_fraction

# Apply in backtest
for i in range(250, len(df)):
    row = df.iloc[i]

    if not in_position:
        signal = check_strategy_signal(row)
        if signal:
            position_size = calculate_position_size(row, recent_trades, base_size=100, method='volatility')
            enter_trade(size=position_size)
```

Calculate and compare:
- Fixed sizing: profit/DD ratio
- Each dynamic method: profit/DD ratio
- Improvement percentage
- Max position size used
</implementation>

<output>
Create file: `./trading/eth_dynamic_sizing_results.md`

Include:
1. **Baseline (Fixed Sizing)**
   - Use best strategy from prompts 007 or 008
   - Results with fixed 1.0x size throughout

2. **Sizing Method Comparison Table**
   - Method name
   - Profit/DD ratio
   - Total return
   - Max drawdown
   - Avg position size
   - Max position size
   - Improvement vs fixed

3. **Best Dynamic Sizing Strategy**
   - Method details and parameters
   - Trade-by-trade analysis showing size variations
   - When did it size up/down?
   - Expected return with recommended leverage
   - Risk analysis: what if sizing goes wrong?

4. **Key Insights**
   - Does dynamic sizing improve profit/DD ratio?
   - Which method works best for ETH?
   - Is the added complexity worth it?
   - Risks of over-sizing or under-sizing

5. **Recommendation**
   - Use fixed or dynamic sizing?
   - If dynamic, which method and parameters?
</output>

<success_criteria>
- At least ONE dynamic sizing method with profit/DD ratio >= 4.0
- Clear comparison showing improvement (or lack thereof) vs fixed sizing
- Verification that position sizes never exceed safe limits
- Practical recommendation with justification
</success_criteria>

<verification>
Before declaring complete:
1. Verify position sizes are calculated correctly for each method
2. Check that sizing logic doesn't create look-ahead bias (e.g., using future data)
3. Confirm max position size stays within leverage and account balance limits
4. Test edge cases: What if all trades are max size? What if Kelly goes negative?
5. Validate that improvements are statistically significant (not just luck)
</verification>
