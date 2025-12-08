# Sequential Longs Strategy - Comprehensive Exploration

## OBJECTIVE
Build and backtest a "Sequential Longs" strategy on FARTCOIN/USDT 15-minute data (last 3 months). Test multiple variations of position sizing and daily trade limits to find optimal configuration.

## DATA
- File: `/workspaces/Carebiuro_windykacja/trading/fartcoin_bingx_15m.csv`
- Use LAST 3 MONTHS only (approximately 8,640 candles)
- Columns: timestamp, open, high, low, close, volume

## STRATEGY RULES (Core Logic)

### Entry Signal
- Wait for a GREEN candle (close > open)
- Enter LONG at the CLOSE price of that green candle
- This is the ONLY entry condition - pure price action

### Stop Loss
- Set stop loss at the LOW of the entry candle
- Exit immediately when price drops to or below stop loss level

### Exit Rules
- **NO TAKE PROFIT** - let winners run
- Exit ONLY when stop loss is hit
- This allows capturing large moves

### Sequential Trading
- Only ONE position at a time
- After stop loss hit → wait for next green candle → enter again
- Never stack positions

### Daily Reset
- Define "session" as a calendar day (00:00-23:59 UTC)
- Count stopped-out trades per session
- After X stopped trades → stop trading for that day
- Reset counter at midnight

## VARIATIONS TO TEST

### A. Daily Trade Limits
Test different maximum trades per day before stopping:
1. **3 trades** - Conservative, avoid choppy days
2. **5 trades** - Moderate
3. **7 trades** - More aggressive
4. **10 trades** - Very aggressive
5. **Unlimited** - No daily cap (baseline)

### B. Position Sizing Strategies

#### B1. Fixed 100% (Baseline)
- Every trade uses 100% of current capital
- Simple compounding

#### B2. Ramp-Up After Losses
Start small, increase after consecutive losses:
- Trade 1-2: 10% capital
- Trade 3-4: 50% capital
- Trade 5+: 100% capital
- Reset to 10% after a winning trade

#### B3. Gradual Increase Per Trade
Progressive sizing within each day:
- Trade 1: 20% capital
- Trade 2: 40% capital
- Trade 3: 60% capital
- Trade 4: 80% capital
- Trade 5+: 100% capital
- Reset to 20% at start of new day

#### B4. Martingale Light
Double after each loss (capped):
- Start: 10% capital
- After loss 1: 20% capital
- After loss 2: 40% capital
- After loss 3: 80% capital
- After loss 4+: 100% capital (cap)
- Reset to 10% after any win

#### B5. Anti-Martingale
Increase after wins, decrease after losses:
- Start: 50% capital
- After win: increase to 75%, then 100%
- After loss: decrease to 25%, then 10%
- Rewards winning streaks

#### B6. Kelly-Inspired
- Calculate win rate and avg win/loss from rolling 20-trade window
- Size position based on edge
- Formula: size = win_rate - (lose_rate / reward_risk_ratio)
- Minimum 10%, maximum 100%

## FEES
- Apply 0.10% round-trip fee (0.05% entry + 0.05% exit)
- This is realistic for BingX/Bybit

## OUTPUT REQUIREMENTS

### 1. Summary Table
Create CSV with columns:
- Config name (e.g., "Limit5_Ramp", "Limit3_Fixed100")
- Total Return %
- Final Capital (from $10,000 start)
- Max Drawdown %
- Total Trades
- Win Rate %
- Average Win %
- Average Loss %
- Profit Factor
- Best Day %
- Worst Day %
- Avg Trades Per Day

### 2. Detailed Analysis
For TOP 5 configurations:
- Equity curve data (for plotting)
- Trade log with entry/exit/P&L
- Monthly breakdown
- Winning/losing streak analysis

### 3. Comparison Chart
Create visualization showing:
- Equity curves of top 5 vs baseline (Fixed100_Unlimited)
- Drawdown comparison

## IMPLEMENTATION NOTES

```python
# Pseudocode for core logic

def is_green_candle(row):
    return row['close'] > row['open']

def backtest_sequential_longs(df, daily_limit, sizing_strategy):
    capital = 10000
    position = None
    daily_trades = 0
    current_day = None
    trades = []

    for i, row in df.iterrows():
        day = row['timestamp'].date()

        # Reset daily counter
        if day != current_day:
            current_day = day
            daily_trades = 0

        # Check if in position
        if position:
            # Check stop loss
            if row['low'] <= position['stop_loss']:
                # Exit at stop loss
                exit_price = position['stop_loss']
                pnl = (exit_price - position['entry']) / position['entry']
                pnl_after_fees = pnl - 0.001  # 0.10% fees
                capital *= (1 + pnl_after_fees * position['size_pct'])
                trades.append({...})
                position = None
                daily_trades += 1

                # Check daily limit
                if daily_trades >= daily_limit:
                    continue  # Skip rest of day

        else:
            # Look for entry
            if daily_trades < daily_limit and is_green_candle(row):
                size_pct = get_position_size(sizing_strategy, daily_trades, ...)
                position = {
                    'entry': row['close'],
                    'stop_loss': row['low'],
                    'size_pct': size_pct,
                    'entry_time': row['timestamp']
                }

    return trades, capital
```

## TEST MATRIX

Run all combinations:
- 5 daily limits × 6 sizing strategies = 30 configurations

Name format: `Limit{X}_{SizingName}`
Examples:
- Limit3_Fixed100
- Limit5_RampUp
- Limit7_Gradual
- LimitNone_Martingale

## SUCCESS CRITERIA
Find configurations that:
1. Beat buy-and-hold (which lost ~40% in 3 months)
2. Achieve positive returns
3. Keep max drawdown < 50%
4. Have reasonable trade frequency (not too few to be meaningful)

## SAVE RESULTS TO
- `/workspaces/Carebiuro_windykacja/trading/results/sequential_longs_results.csv`
- `/workspaces/Carebiuro_windykacja/trading/results/sequential_longs_equity.png`
- `/workspaces/Carebiuro_windykacja/trading/results/sequential_longs_trades.csv`

## IMPORTANT
- Use vectorized operations where possible for speed
- Handle edge cases (first/last candle, overnight positions)
- Close any open position at end of data
- Print progress updates

NOW BUILD AND RUN THIS BACKTEST.
