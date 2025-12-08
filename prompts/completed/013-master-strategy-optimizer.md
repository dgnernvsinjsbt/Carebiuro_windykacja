<objective>
You are a MASTER OPTIMIZER - a quant with obsessive attention to detail who squeezes every last drop of alpha from a strategy. You've spent decades optimizing trading systems for hedge funds, and you know that the difference between a good strategy and a great one is in the details.

Your mission: Take the strategy from prompt 012 and OPTIMIZE it to perfection. Test every possible improvement, quantify the impact, and produce a final optimized version that maximizes risk-adjusted returns.
</objective>

<input_required>
Before starting, read:
- Strategy specification: `./trading/strategies/${COIN_SYMBOL}_MASTER_STRATEGY.md`
- Strategy code: `./trading/strategies/${COIN_SYMBOL}_strategy.py`
- Backtest results: `./trading/results/${COIN_SYMBOL}_strategy_results.csv`
- Pattern analysis: `./trading/results/${COIN_SYMBOL}_PATTERN_ANALYSIS.md`
- Data file: `./trading/${COIN_FILE}`
</input_required>

<optimizer_philosophy>

The master optimizer knows:

1. **Optimization is NOT curve-fitting**
   - Every change must have a LOGICAL reason
   - If you can't explain WHY it should work, it won't work in live trading
   - Prefer robust improvements over marginal gains

2. **Test one variable at a time**
   - Change one thing, measure impact
   - Understand causation, not just correlation
   - Document what works AND what doesn't

3. **The goal is risk-adjusted returns**
   - Higher returns with same risk = good
   - Same returns with lower risk = also good
   - Higher returns with higher risk = questionable

4. **Fees are the silent killer**
   - Every filter that reduces trades must justify itself
   - Limit orders can transform a losing strategy into a winner
   - Account for slippage in volatile conditions

5. **Simplicity after optimization**
   - Start complex, end simple
   - Remove filters that don't pull their weight
   - The final strategy should be executable by a human

</optimizer_philosophy>

<data_anomaly_scan>
<title>CRITICAL: Data Quality & Anomaly Detection</title>

**Before ANY optimization, scan the backtest results for anomalies. A strategy built on polluted data is worthless.**

<anomaly_1_profit_concentration>
**Profit Concentration Check**

The goal: Ensure profits come from a REPEATABLE edge, not a few lucky outliers.

Calculate:
- Sort all trades by P&L (highest to lowest)
- What % of total profit comes from top 5 trades?
- What % of total profit comes from top 10 trades?
- What % of trades account for 50% of total profit?
- What % of trades account for 80% of total profit?

**Red Flags:**
- A SMALL MINORITY of trades drives MAJORITY of profits
- Example: 100 trades total, but just 3-5 trades = 60%+ of all profit
- Single trade = >20% of total profit
- Remove top 5 trades and strategy becomes unprofitable

**Why This Matters:**
- Those outlier trades might be data errors (price spikes, gaps)
- Those outlier trades might be unrepeatable events (listing pumps, black swans)
- If your "edge" depends on catching 3 perfect trades out of 100, it's not an edge

**Action Required:**
1. List ALL trades that individually contribute >5% of total profit:
   - Entry time, exit time, entry price, exit price
   - % gain on that single trade
   - ATR at entry (was this move realistic given volatility?)
   - Duration of trade
   - What was happening in the market? (check news, BTC move, etc.)
2. Cross-check against raw price data:
   - Did the price actually move that much in that timeframe?
   - Are there gaps/missing candles during this trade?
   - Does the exit price match what SL/TP should have been?
3. Run backtest WITH and WITHOUT outlier trades:
   - If still profitable without them → edge is real
   - If unprofitable without them → strategy depends on anomalies
4. If anomaly confirmed → REMOVE from backtest and re-run all metrics
</anomaly_1_profit_concentration>

<anomaly_2_data_gaps>
**Data Gap Detection**

Scan the price data for:
- Missing candles (gaps in timestamps)
- Duplicate timestamps
- Zero volume candles
- Price = 0 or NaN values
- Unrealistic price jumps (>10% in single candle without recovery)

**Validation Script:**
```python
# Check for gaps
df['time_diff'] = df['timestamp'].diff()
gaps = df[df['time_diff'] > expected_interval * 1.5]
print(f"Found {len(gaps)} data gaps")

# Check for duplicates
duplicates = df[df['timestamp'].duplicated()]
print(f"Found {len(duplicates)} duplicate timestamps")

# Check for zero/null values
invalid = df[(df['close'] == 0) | (df['close'].isna()) | (df['volume'] == 0)]
print(f"Found {len(invalid)} invalid candles")

# Check for unrealistic moves
df['pct_change'] = df['close'].pct_change().abs()
spikes = df[df['pct_change'] > 0.10]  # >10% single candle
print(f"Found {len(spikes)} suspicious price spikes")
```

If anomalies found → Document them, consider removing affected periods.
</anomaly_2_data_gaps>

<anomaly_3_trade_calculation_audit>
**Trade Calculation Audit**

Manually verify 5 random trades + all outlier trades:

For each trade, check:
1. **Entry Price** - Does it match the candle's high/low/close at entry time?
2. **Exit Price** - Was SL/TP actually hit at that price?
3. **P&L Calculation** - (exit_price - entry_price) / entry_price = reported %?
4. **Fee Deduction** - Are fees correctly subtracted?
5. **Slippage** - Is it accounted for?

**Common Calculation Errors:**
- Using close price for SL exit when low price should be used (LONG)
- Using close price for TP exit when high price should be used (LONG)
- Not checking if BOTH SL and TP were hit in same candle (take worst case)
- Forgetting to apply fees to both entry and exit
- Using wrong lot size in P&L calculation

**Verification Table:**
| Trade # | Entry Time | Entry Price | Exit Price | Claimed P&L | Verified P&L | Match? |
|---------|------------|-------------|------------|-------------|--------------|--------|
</anomaly_3_trade_calculation_audit>

<anomaly_4_lookahead_bias>
**Lookahead Bias Check**

Common lookahead mistakes:
- Using future high/low in current candle's indicator
- Calculating ATR including current candle's range
- Using tomorrow's data to decide today's entry

**Test for Lookahead:**
1. Take a random trade entry
2. At entry time, ONLY using data available up to that moment:
   - Do all indicator values match?
   - Was the signal actually triggered?
3. Simulate in real-time mode if possible

If lookahead detected → Strategy is INVALID, must be fixed.
</anomaly_4_lookahead_bias>

<anomaly_5_time_distribution>
**Time Distribution Analysis**

Check if profits are evenly distributed across:
- Days of week (is Monday carrying all profits?)
- Months (is December the only profitable month?)
- Hours (are all profits from one specific hour?)

**Red Flags:**
- Single day of week = >50% of profits
- Single month = >40% of profits
- Single hour = >30% of profits

These concentrations suggest data artifacts, not repeatable edge.
</anomaly_5_time_distribution>

<anomaly_summary>
**Anomaly Scan Summary Table**

Before proceeding to optimization, fill out:

| Check | Status | Notes |
|-------|--------|-------|
| Profits NOT concentrated in few trades | ✅/❌ | |
| Strategy profitable without top 5 trades | ✅/❌ | |
| No data gaps found | ✅/❌ | |
| Trade calculations verified | ✅/❌ | |
| No lookahead bias | ✅/❌ | |
| Time distribution normal | ✅/❌ | |

**If ANY check fails → STOP and fix before optimizing.**

A "profitable" strategy with data errors will lose money in live trading.
</anomaly_summary>

<pre_live_verification_commands>
<title>🚨 MANDATORY: Pre-Live Verification Scripts</title>

**Run ALL these verification scripts before deploying ANY strategy to live trading.**

<verification_script_1_data_integrity>
**Script 1: Data Integrity Check**

```python
#!/usr/bin/env python3
"""
DATA INTEGRITY VERIFICATION
Run this FIRST before any analysis
"""
import pandas as pd
import numpy as np

def verify_data_integrity(csv_path, expected_interval_minutes=1):
    """
    Returns: (passed: bool, report: str)
    """
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)

    issues = []

    # 1. Check for missing columns
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        issues.append(f"❌ MISSING COLUMNS: {missing}")

    # 2. Check for NaN/null values
    null_counts = df[required_cols].isnull().sum()
    if null_counts.sum() > 0:
        issues.append(f"❌ NULL VALUES FOUND:\n{null_counts[null_counts > 0]}")

    # 3. Check for zero/negative prices
    invalid_prices = df[(df['close'] <= 0) | (df['open'] <= 0) |
                        (df['high'] <= 0) | (df['low'] <= 0)]
    if len(invalid_prices) > 0:
        issues.append(f"❌ INVALID PRICES (<=0): {len(invalid_prices)} rows")

    # 4. Check OHLC logic (high >= low, high >= open/close, low <= open/close)
    ohlc_errors = df[(df['high'] < df['low']) |
                     (df['high'] < df['open']) | (df['high'] < df['close']) |
                     (df['low'] > df['open']) | (df['low'] > df['close'])]
    if len(ohlc_errors) > 0:
        issues.append(f"❌ OHLC LOGIC ERRORS: {len(ohlc_errors)} rows where high<low or similar")

    # 5. Check for duplicate timestamps
    duplicates = df[df['timestamp'].duplicated()]
    if len(duplicates) > 0:
        issues.append(f"❌ DUPLICATE TIMESTAMPS: {len(duplicates)} rows")

    # 6. Check for data gaps
    expected_interval = pd.Timedelta(minutes=expected_interval_minutes)
    df['time_diff'] = df['timestamp'].diff()
    gaps = df[df['time_diff'] > expected_interval * 2]  # Allow some tolerance
    if len(gaps) > 0:
        gap_pct = len(gaps) / len(df) * 100
        issues.append(f"⚠️  DATA GAPS: {len(gaps)} gaps ({gap_pct:.2f}% of data)")
        # Show largest gaps
        largest_gaps = gaps.nlargest(5, 'time_diff')[['timestamp', 'time_diff']]
        issues.append(f"   Largest gaps:\n{largest_gaps.to_string()}")

    # 7. Check for suspicious price spikes (>15% single candle)
    df['pct_change'] = df['close'].pct_change().abs()
    spikes = df[df['pct_change'] > 0.15]
    if len(spikes) > 0:
        issues.append(f"⚠️  SUSPICIOUS SPIKES (>15%): {len(spikes)} candles")
        issues.append(f"   Spike times: {spikes['timestamp'].head(10).tolist()}")

    # 8. Check data range
    date_range = df['timestamp'].max() - df['timestamp'].min()
    expected_candles = date_range.total_seconds() / (expected_interval_minutes * 60)
    actual_candles = len(df)
    completeness = actual_candles / expected_candles * 100

    if completeness < 95:
        issues.append(f"⚠️  DATA COMPLETENESS: {completeness:.1f}% (expected ~{int(expected_candles)}, got {actual_candles})")

    # Generate report
    report = f"""
================================================================================
DATA INTEGRITY REPORT: {csv_path}
================================================================================
Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}
Total Candles: {len(df):,}
Expected Interval: {expected_interval_minutes} min
Data Completeness: {completeness:.1f}%

CHECKS:
"""

    if not issues:
        report += "✅ ALL CHECKS PASSED\n"
        return True, report
    else:
        for issue in issues:
            report += f"\n{issue}\n"
        report += "\n❌ DATA INTEGRITY CHECK FAILED - FIX BEFORE PROCEEDING\n"
        return False, report

# USAGE:
# passed, report = verify_data_integrity('./trading/doge_usdt_1m_lbank.csv')
# print(report)
# if not passed:
#     raise Exception("Data integrity check failed!")
```
</verification_script_1_data_integrity>

<verification_script_2_data_corruption_detection>
**Script 2: Data Corruption Detection (CRITICAL)**

**IMPORTANT DISTINCTION:**
- ✅ **NORMAL**: High R:R strategy with 20 trades, 8 winners, 2-3 big winners = 70-80% of profit → This is EXPECTED for trend-following strategies
- ❌ **CORRUPTION**: Strategy has 100-200 trades, mostly small, but 1-2 trades show IMPOSSIBLE gains (1000%+ more than median) → This is DATA ERROR

**What we're catching:** Strategies that would be UNPROFITABLE without suspiciously large trades that couldn't happen in real trading.

```python
#!/usr/bin/env python3
"""
DATA CORRUPTION DETECTION
Detects impossible trades that indicate corrupted price data
NOT designed to flag legitimate high R:R strategies
"""
import pandas as pd
import numpy as np

def detect_data_corruption(trades_csv_path, price_data_csv, pnl_column='pnl'):
    """
    Detects DATA CORRUPTION, not legitimate outliers.

    A trade is SUSPICIOUS if:
    1. It's 10x+ larger than the MEDIAN winning trade (not average - median!)
    2. The price move exceeds what's possible given ATR
    3. Removing it makes an otherwise-losing strategy "profitable"

    A trade is LEGITIMATE (even if large) if:
    1. It's within reasonable ATR bounds (< 15x ATR move)
    2. The strategy is still profitable without it
    3. Other winners exist in similar magnitude
    """
    trades = pd.read_csv(trades_csv_path)
    prices = pd.read_csv(price_data_csv)
    prices['timestamp'] = pd.to_datetime(prices['timestamp'])

    # Calculate ATR for reality checks
    prices['range'] = prices['high'] - prices['low']
    prices['atr'] = prices['range'].rolling(14).mean()
    prices['atr_pct'] = prices['atr'] / prices['close'] * 100
    median_atr_pct = prices['atr_pct'].median()

    if pnl_column not in trades.columns:
        for alt in ['pnl', 'profit', 'return', 'pnl_pct']:
            if alt in trades.columns:
                pnl_column = alt
                break

    total_trades = len(trades)
    total_pnl = trades[pnl_column].sum()

    # Separate winners and losers
    winners = trades[trades[pnl_column] > 0].copy()
    losers = trades[trades[pnl_column] <= 0].copy()

    if len(winners) == 0:
        return False, "❌ No winning trades - strategy is unprofitable"

    # Key metrics for corruption detection
    median_winner = winners[pnl_column].median()
    max_winner = winners[pnl_column].max()
    winner_std = winners[pnl_column].std()

    # Calculate how many "median winners" the best trade equals
    best_trade_multiple = max_winner / median_winner if median_winner > 0 else float('inf')

    # Find potentially corrupted trades (>10x median winner)
    corruption_threshold = median_winner * 10
    suspicious_trades = trades[trades[pnl_column] > corruption_threshold].copy()

    # Calculate what happens without suspicious trades
    pnl_without_suspicious = trades[trades[pnl_column] <= corruption_threshold][pnl_column].sum()

    # Check if suspicious trades have realistic price moves
    corruption_confirmed = []
    legitimate_outliers = []

    for idx, trade in suspicious_trades.iterrows():
        trade_pnl = trade[pnl_column]
        trade_pnl_pct = trade_pnl * 100

        # Get entry time and check ATR
        entry_time = pd.to_datetime(trade.get('entry_time', trade.get('timestamp', None)))
        if entry_time:
            nearby_atr = prices[prices['timestamp'] <= entry_time].tail(20)['atr_pct'].mean()
        else:
            nearby_atr = median_atr_pct

        # How many ATRs did this trade move?
        # For a trade with 2:1 R:R and 1x ATR stop, max realistic profit = ~2x ATR
        # For a trade with 10:1 R:R and 1x ATR stop, max realistic profit = ~10x ATR
        # Anything beyond ~15x ATR in a single trade is suspicious
        atr_multiple = abs(trade_pnl_pct) / nearby_atr if nearby_atr > 0 else float('inf')

        trade_info = {
            'pnl': trade_pnl,
            'pnl_pct': trade_pnl_pct,
            'median_multiple': trade_pnl / median_winner,
            'atr_multiple': atr_multiple,
            'entry_time': entry_time
        }

        # CORRUPTION INDICATORS:
        # 1. Move is physically impossible (>20x ATR)
        # 2. Trade is >50x median winner (way beyond normal distribution)
        # 3. Without this trade, strategy becomes unprofitable

        is_impossible_move = atr_multiple > 20
        is_extreme_outlier = (trade_pnl / median_winner) > 50
        makes_strategy_profitable = (total_pnl > 0) and (pnl_without_suspicious <= 0)

        if is_impossible_move or (is_extreme_outlier and makes_strategy_profitable):
            trade_info['reason'] = []
            if is_impossible_move:
                trade_info['reason'].append(f"Move = {atr_multiple:.0f}x ATR (max realistic ~15x)")
            if is_extreme_outlier:
                trade_info['reason'].append(f"Trade = {trade_pnl/median_winner:.0f}x median winner")
            if makes_strategy_profitable:
                trade_info['reason'].append("Strategy unprofitable without this trade")
            corruption_confirmed.append(trade_info)
        else:
            legitimate_outliers.append(trade_info)

    # Generate report
    report = f"""
================================================================================
DATA CORRUPTION DETECTION REPORT
================================================================================
Total Trades: {total_trades}
Winners: {len(winners)} | Losers: {len(losers)}
Total P&L: {total_pnl*100:.2f}%

WINNER DISTRIBUTION:
  Median winner: {median_winner*100:+.3f}%
  Max winner:    {max_winner*100:+.3f}%
  Best trade is: {best_trade_multiple:.1f}x the median winner
  Std dev:       {winner_std*100:.3f}%

MARKET CONTEXT:
  Median ATR:    {median_atr_pct:.2f}% per candle

CORRUPTION ANALYSIS:
  Trades > 10x median winner: {len(suspicious_trades)}
  P&L without suspicious trades: {pnl_without_suspicious*100:+.2f}%
"""

    if len(corruption_confirmed) > 0:
        report += f"""
⚠️  SUSPICIOUS TRADES FLAGGED: {len(corruption_confirmed)}

These trades warrant MANUAL INVESTIGATION:
"""
        for i, t in enumerate(corruption_confirmed):
            report += f"""
  Trade #{i+1}: {t['pnl_pct']:+.2f}% profit
    - {t['atr_multiple']:.0f}x ATR move (typical: 2-15x)
    - {t['median_multiple']:.0f}x the median winner
    - Flags: {', '.join(t['reason'])}
"""
        report += f"""
================================================================================
🔍 INVESTIGATION REQUIRED

These trades have unusual characteristics. They COULD be:
1. DATA CORRUPTION - price spike that didn't happen on exchange
2. REAL EVENT - news pump, listing, liquidation cascade (verify on exchange!)
3. BLACK SWAN - legitimate but rare event that may not repeat

INVESTIGATION STEPS:
1. Pull up the chart at these exact timestamps on the exchange
2. Verify the price move actually happened
3. If real → determine if the event is repeatable or one-time
4. If data error → remove and re-run backtest
5. Use your judgment - these flags are warnings, not verdicts

The script cannot determine if these are real - YOU must verify manually.
================================================================================
"""
        # Return True but with warnings - human must investigate
        return True, report

    elif len(suspicious_trades) > 0:
        report += f"""
✅ LARGE TRADES DETECTED BUT APPEAR LEGITIMATE

{len(suspicious_trades)} trade(s) are >10x median winner, but:
- Price moves are within ATR bounds (<20x ATR)
- Strategy remains profitable without them: {pnl_without_suspicious*100:+.2f}%
- This is NORMAL for high R:R strategies

Details:
"""
        for i, t in enumerate(legitimate_outliers[:5]):
            report += f"  Trade: {t['pnl_pct']:+.2f}% | {t['atr_multiple']:.1f}x ATR | {t['median_multiple']:.1f}x median\n"

        report += """
This distribution is expected for:
- Trend-following strategies
- High R:R setups (1:4 or higher)
- Strategies that catch big moves

✅ NO DATA CORRUPTION DETECTED
"""
        return True, report

    else:
        report += """
✅ NO SUSPICIOUS TRADES FOUND

Winner distribution appears normal:
- No trades >10x median winner
- P&L comes from consistent edge, not outliers

✅ DATA INTEGRITY VERIFIED
"""
        return True, report

# USAGE:
# passed, report = detect_data_corruption(
#     './trading/results/DOGE_strategy_results.csv',
#     './trading/doge_usdt_1m_lbank.csv'
# )
# print(report)
```
</verification_script_2_data_corruption_detection>

<verification_script_3_trade_verification>
**Script 3: Trade Calculation Verification**

```python
#!/usr/bin/env python3
"""
TRADE CALCULATION VERIFICATION
Manually verify that SL/TP were hit correctly
"""
import pandas as pd
import numpy as np

def verify_trade_calculations(trades_csv, price_data_csv, sample_size=10):
    """
    Randomly samples trades and verifies:
    1. Entry price matches candle data
    2. Exit price matches SL/TP logic
    3. P&L calculation is correct
    4. Fees are properly deducted
    """
    trades = pd.read_csv(trades_csv)
    prices = pd.read_csv(price_data_csv)
    prices['timestamp'] = pd.to_datetime(prices['timestamp'])

    # Sample trades to verify
    sample_indices = np.random.choice(len(trades), min(sample_size, len(trades)), replace=False)

    verification_results = []
    issues_found = []

    for idx in sample_indices:
        trade = trades.iloc[idx]
        result = {'trade_idx': idx}

        # Find entry candle
        entry_time = pd.to_datetime(trade.get('entry_time', trade.get('timestamp')))
        entry_candle = prices[prices['timestamp'] == entry_time]

        if len(entry_candle) == 0:
            issues_found.append(f"Trade {idx}: Entry candle not found at {entry_time}")
            continue

        entry_candle = entry_candle.iloc[0]

        # Verify entry price is within candle range
        entry_price = trade.get('entry', trade.get('entry_price'))
        if not (entry_candle['low'] <= entry_price <= entry_candle['high']):
            issues_found.append(f"Trade {idx}: Entry price {entry_price} outside candle range [{entry_candle['low']}, {entry_candle['high']}]")

        # Verify P&L calculation (assuming we have direction)
        exit_price = trade.get('exit', trade.get('exit_price'))
        claimed_pnl = trade.get('pnl', trade.get('profit', 0))

        direction = trade.get('direction', 'LONG')
        if direction == 'LONG':
            expected_pnl = (exit_price / entry_price - 1)
        else:
            expected_pnl = (entry_price / exit_price - 1)

        # Account for fees (assume 0.1% round-trip if not specified)
        fee = trade.get('fee', 0.001)
        expected_pnl_with_fees = expected_pnl - fee

        pnl_diff = abs(claimed_pnl - expected_pnl_with_fees)
        if pnl_diff > 0.0001:  # Allow small floating point differences
            issues_found.append(f"Trade {idx}: PnL mismatch. Claimed: {claimed_pnl:.6f}, Expected: {expected_pnl_with_fees:.6f}")

        verification_results.append({
            'trade_idx': idx,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'claimed_pnl': claimed_pnl,
            'expected_pnl': expected_pnl_with_fees,
            'pnl_match': pnl_diff <= 0.0001
        })

    # Generate report
    report = f"""
================================================================================
TRADE CALCULATION VERIFICATION
================================================================================
Trades Sampled: {len(sample_indices)}
Issues Found: {len(issues_found)}

SAMPLE VERIFICATION RESULTS:
"""

    results_df = pd.DataFrame(verification_results)
    report += results_df.to_string()

    if issues_found:
        report += f"\n\n⚠️  ISSUES DETECTED:\n"
        for issue in issues_found:
            report += f"  - {issue}\n"
        report += "\n❌ TRADE CALCULATIONS MAY BE INCORRECT - REVIEW BACKTEST CODE\n"
        return False, report
    else:
        report += "\n\n✅ ALL SAMPLED TRADES VERIFIED CORRECTLY\n"
        return True, report

# USAGE:
# passed, report = verify_trade_calculations(
#     './trading/results/DOGE_strategy_results.csv',
#     './trading/doge_usdt_1m_lbank.csv'
# )
# print(report)
```
</verification_script_3_trade_verification>

<verification_script_4_outlier_investigation>
**Script 4: Outlier Trade Investigation**

```python
#!/usr/bin/env python3
"""
OUTLIER TRADE DEEP INVESTIGATION
For trades contributing >5% of profit, verify they are REAL and REPEATABLE
"""
import pandas as pd
import numpy as np

def investigate_outlier_trades(trades_csv, price_data_csv, pnl_column='pnl', threshold_pct=5.0):
    """
    Deep dive into trades that contribute >threshold_pct of total profit.
    Checks if they are:
    1. Real price movements (not data errors)
    2. Within normal ATR bounds
    3. Not one-time events (news, listings, etc.)
    """
    trades = pd.read_csv(trades_csv)
    prices = pd.read_csv(price_data_csv)
    prices['timestamp'] = pd.to_datetime(prices['timestamp'])

    # Calculate ATR for context
    prices['range'] = prices['high'] - prices['low']
    prices['atr'] = prices['range'].rolling(14).mean()
    prices['atr_pct'] = prices['atr'] / prices['close'] * 100

    total_pnl = trades[pnl_column].sum()
    if total_pnl <= 0:
        return True, "Strategy not profitable - no outliers to investigate"

    # Find outlier trades (>threshold% of total profit)
    trades['pct_contribution'] = trades[pnl_column] / total_pnl * 100
    outliers = trades[trades['pct_contribution'] > threshold_pct].copy()

    if len(outliers) == 0:
        return True, f"✅ No trades contribute >{threshold_pct}% of profit - distribution is healthy"

    report = f"""
================================================================================
OUTLIER TRADE INVESTIGATION
================================================================================
Threshold: Trades contributing >{threshold_pct}% of total profit
Outliers Found: {len(outliers)}
Total Profit: {total_pnl*100:.2f}%

OUTLIER DETAILS:
"""

    suspicious_trades = []

    for idx, trade in outliers.iterrows():
        entry_time = pd.to_datetime(trade.get('entry_time', trade.get('timestamp')))
        exit_time = pd.to_datetime(trade.get('exit_time', entry_time + pd.Timedelta(hours=1)))

        entry_price = trade.get('entry', trade.get('entry_price'))
        exit_price = trade.get('exit', trade.get('exit_price'))
        trade_pnl = trade[pnl_column]
        contribution = trade['pct_contribution']

        # Get ATR at entry
        entry_data = prices[prices['timestamp'] <= entry_time].tail(1)
        atr_at_entry = entry_data['atr_pct'].values[0] if len(entry_data) > 0 else 0

        # Calculate how many ATRs the trade moved
        move_pct = abs((exit_price - entry_price) / entry_price * 100)
        atr_multiple = move_pct / atr_at_entry if atr_at_entry > 0 else 999

        # Flag suspicious trades
        is_suspicious = False
        suspicion_reasons = []

        if atr_multiple > 10:
            is_suspicious = True
            suspicion_reasons.append(f"Move was {atr_multiple:.1f}x ATR (unusually large)")

        if move_pct > 5:
            is_suspicious = True
            suspicion_reasons.append(f"Single trade moved {move_pct:.2f}% (check for data error)")

        if contribution > 20:
            is_suspicious = True
            suspicion_reasons.append(f"Single trade = {contribution:.1f}% of ALL profits")

        report += f"""
--------------------------------------------------------------------------------
Trade at {entry_time}
  Entry: {entry_price:.6f} → Exit: {exit_price:.6f}
  P&L: {trade_pnl*100:+.3f}% | Contribution: {contribution:.1f}% of total profit
  Move: {move_pct:.2f}% | ATR at entry: {atr_at_entry:.2f}% | ATR Multiple: {atr_multiple:.1f}x
"""

        if is_suspicious:
            report += f"  ⚠️  SUSPICIOUS: {', '.join(suspicion_reasons)}\n"
            suspicious_trades.append(trade)
        else:
            report += f"  ✅ Trade appears legitimate\n"

    if suspicious_trades:
        report += f"""
================================================================================
🚨 ACTION REQUIRED:
{len(suspicious_trades)} suspicious outlier trade(s) detected.

For each suspicious trade:
1. Check raw price data around that timestamp
2. Look for news/events that day
3. Verify the move actually happened on exchange
4. Consider removing from backtest if data error confirmed
5. If real event, assess if it's repeatable or one-time

DO NOT GO LIVE until outliers are investigated!
================================================================================
"""
        return False, report
    else:
        report += "\n✅ All outlier trades appear legitimate\n"
        return True, report

# USAGE:
# passed, report = investigate_outlier_trades(
#     './trading/results/DOGE_strategy_results.csv',
#     './trading/doge_usdt_1m_lbank.csv'
# )
# print(report)
```
</verification_script_4_outlier_investigation>

<verification_script_5_time_consistency>
**Script 5: Time Period Consistency Check**

```python
#!/usr/bin/env python3
"""
TIME PERIOD CONSISTENCY CHECK
Verify strategy works across different time periods, not just one lucky week
"""
import pandas as pd
import numpy as np

def check_time_consistency(trades_csv, pnl_column='pnl'):
    """
    Checks if profits are distributed across time or concentrated in specific periods.

    RED FLAGS:
    - Single week = >50% of profits
    - Single day of week = >40% of profits
    - Strategy only profitable in 1 out of 4 weeks
    """
    trades = pd.read_csv(trades_csv)

    # Parse timestamps
    time_col = 'entry_time' if 'entry_time' in trades.columns else 'timestamp'
    trades['datetime'] = pd.to_datetime(trades[time_col])
    trades['date'] = trades['datetime'].dt.date
    trades['week'] = trades['datetime'].dt.isocalendar().week
    trades['day_of_week'] = trades['datetime'].dt.day_name()
    trades['hour'] = trades['datetime'].dt.hour

    total_pnl = trades[pnl_column].sum()

    if total_pnl <= 0:
        return True, "Strategy not profitable - time consistency N/A"

    red_flags = []

    # Weekly breakdown
    weekly = trades.groupby('week')[pnl_column].agg(['sum', 'count'])
    weekly['pct_of_total'] = weekly['sum'] / total_pnl * 100
    weekly_profitable = (weekly['sum'] > 0).sum()
    total_weeks = len(weekly)

    max_week_contribution = weekly['pct_of_total'].max()
    if max_week_contribution > 50:
        red_flags.append(f"🚨 Single week = {max_week_contribution:.1f}% of profit")

    if weekly_profitable < total_weeks * 0.5:
        red_flags.append(f"⚠️  Only {weekly_profitable}/{total_weeks} weeks profitable")

    # Day of week breakdown
    daily = trades.groupby('day_of_week')[pnl_column].agg(['sum', 'count'])
    daily['pct_of_total'] = daily['sum'] / total_pnl * 100

    max_day_contribution = daily['pct_of_total'].max()
    max_day_name = daily['pct_of_total'].idxmax()
    if max_day_contribution > 40:
        red_flags.append(f"⚠️  {max_day_name} = {max_day_contribution:.1f}% of profit")

    # Hourly breakdown
    hourly = trades.groupby('hour')[pnl_column].agg(['sum', 'count'])
    hourly['pct_of_total'] = hourly['sum'] / total_pnl * 100

    max_hour_contribution = hourly['pct_of_total'].max()
    max_hour = hourly['pct_of_total'].idxmax()
    if max_hour_contribution > 30:
        red_flags.append(f"⚠️  Hour {max_hour}:00 UTC = {max_hour_contribution:.1f}% of profit")

    # Generate report
    report = f"""
================================================================================
TIME PERIOD CONSISTENCY CHECK
================================================================================
Total Trades: {len(trades)}
Total Profit: {total_pnl*100:.2f}%
Date Range: {trades['date'].min()} to {trades['date'].max()}

WEEKLY DISTRIBUTION:
{weekly.to_string()}

Profitable Weeks: {weekly_profitable}/{total_weeks} ({weekly_profitable/total_weeks*100:.0f}%)
Max Week Contribution: {max_week_contribution:.1f}%

DAY OF WEEK DISTRIBUTION:
{daily.to_string()}

Max Day Contribution: {max_day_name} = {max_day_contribution:.1f}%

HOURLY DISTRIBUTION (Top 5):
{hourly.nlargest(5, 'pct_of_total').to_string()}

Max Hour Contribution: {max_hour}:00 UTC = {max_hour_contribution:.1f}%
"""

    if red_flags:
        report += f"\n{'='*60}\n⚠️  RED FLAGS:\n"
        for flag in red_flags:
            report += f"  {flag}\n"
        report += "\n🛑 Profits may be concentrated in specific time periods!\n"
        return False, report
    else:
        report += "\n✅ PROFITS DISTRIBUTED ACROSS TIME - No major concentration\n"
        return True, report

# USAGE:
# passed, report = check_time_consistency('./trading/results/DOGE_strategy_results.csv')
# print(report)
```
</verification_script_5_time_consistency>

<verification_master_script>
**Master Verification Script (Run All Checks)**

```python
#!/usr/bin/env python3
"""
MASTER VERIFICATION SCRIPT
Run ALL pre-live checks and generate comprehensive report
"""

def run_all_verifications(
    price_data_csv,
    trades_csv,
    pnl_column='pnl'
):
    """
    Runs all 5 verification scripts and generates pass/fail summary.

    Returns:
        all_passed: bool - True only if ALL checks pass
        full_report: str - Complete verification report
    """

    results = {}
    full_report = """
################################################################################
#                                                                              #
#                    PRE-LIVE VERIFICATION REPORT                              #
#                                                                              #
################################################################################
"""

    # 1. Data Integrity
    print("Running Data Integrity Check...")
    passed, report = verify_data_integrity(price_data_csv)
    results['data_integrity'] = passed
    full_report += report

    # 2. Data Corruption Detection
    print("Running Data Corruption Detection...")
    passed, report = detect_data_corruption(trades_csv, price_data_csv, pnl_column)
    results['data_corruption'] = passed
    full_report += report

    # 3. Trade Calculations
    print("Running Trade Calculation Verification...")
    passed, report = verify_trade_calculations(trades_csv, price_data_csv)
    results['trade_calculations'] = passed
    full_report += report

    # 4. Outlier Investigation
    print("Running Outlier Investigation...")
    passed, report = investigate_outlier_trades(trades_csv, price_data_csv, pnl_column)
    results['outlier_investigation'] = passed
    full_report += report

    # 5. Time Consistency
    print("Running Time Consistency Check...")
    passed, report = check_time_consistency(trades_csv, pnl_column)
    results['time_consistency'] = passed
    full_report += report

    # Summary
    all_passed = all(results.values())

    full_report += f"""
################################################################################
                           VERIFICATION SUMMARY
################################################################################

| Check                    | Status |
|--------------------------|--------|
| Data Integrity           | {'✅ PASS' if results['data_integrity'] else '❌ FAIL'} |
| Data Corruption          | {'✅ PASS' if results['data_corruption'] else '❌ FAIL'} |
| Trade Calculations       | {'✅ PASS' if results['trade_calculations'] else '❌ FAIL'} |
| Outlier Investigation    | {'✅ PASS' if results['outlier_investigation'] else '❌ FAIL'} |
| Time Consistency         | {'✅ PASS' if results['time_consistency'] else '❌ FAIL'} |
|--------------------------|--------|
| OVERALL                  | {'✅ ALL CHECKS PASSED' if all_passed else '❌ CHECKS FAILED'} |

"""

    # Note: all_passed just means scripts ran without errors
    # The actual decision requires human judgment on flagged issues
    full_report += """
================================================================================
                          NEXT STEPS
================================================================================

1. REVIEW each section above for ⚠️ warnings
2. For ANY flagged trades/periods:
   - Pull up the actual chart on the exchange
   - Verify the move really happened
   - Decide if it's repeatable or one-time event
3. MAKE YOUR JUDGMENT CALL:
   - If flags are false alarms (verified on exchange) → Proceed
   - If flags reveal data errors → Fix and re-run
   - If flags show one-time events → Decide if you want that risk

These scripts FLAG issues for investigation.
They don't make decisions - YOU do.
"""

    return all_passed, full_report

# USAGE:
# all_passed, report = run_all_verifications(
#     price_data_csv='./trading/doge_usdt_1m_lbank.csv',
#     trades_csv='./trading/results/DOGE_strategy_results.csv',
#     pnl_column='pnl'
# )
# print(report)
#
# # Save report
# with open('./trading/results/DOGE_VERIFICATION_REPORT.md', 'w') as f:
#     f.write(report)
```
</verification_master_script>

<verification_checklist>
**Pre-Live Verification Checklist**

Before deploying ANY strategy to live trading, complete this checklist:

| # | Check | Purpose | Status |
|---|-------|---------|--------|
| 1 | Run `verify_data_integrity()` | Flag gaps, duplicates, OHLC errors | ⬜ |
| 2 | Run `detect_data_corruption()` | Flag unusually large trades for review | ⬜ |
| 3 | Run `verify_trade_calculations()` | Verify SL/TP/PnL math is correct | ⬜ |
| 4 | Run `investigate_outlier_trades()` | Get details on big winners | ⬜ |
| 5 | Run `check_time_consistency()` | Check profit distribution over time | ⬜ |
| 6 | **MANUAL**: Verify flagged trades on exchange | Pull up charts, confirm moves happened | ⬜ |
| 7 | **MANUAL**: Assess if big moves are repeatable | News event? Listing? Or normal edge? | ⬜ |
| 8 | **JUDGMENT CALL**: Accept the risk profile | Understand what you're trading | ⬜ |

**IMPORTANT: Scripts flag issues, YOU decide what to do**

The scripts produce WARNINGS, not verdicts. A flag means:
- "Hey, look at this more closely"
- NOT "This is definitely wrong"

Examples:
- Script flags 25x ATR move → You check exchange → It was a real liquidation cascade → ✅ OK
- Script flags 50x median winner → You check → Data shows price spike that didn't happen → ❌ Remove
- Script shows 1 week = 60% profit → You check → That week had a major news event → ✅ Understand the risk

**Use your intelligence. The scripts are assistants, not judges.**

</verification_checklist>

</pre_live_verification_commands>

</data_anomaly_scan>

<optimization_framework>

<optimization_1_session_filters>
<title>Session-Based Optimization</title>

Test the strategy performance in each session INDEPENDENTLY:

| Session | Hours (UTC) | Test Focus |
|---------|-------------|------------|
| Asia | 00:00-08:00 | Often ranging, lower volume |
| Europe | 08:00-14:00 | Volatility pickup, trend starts |
| US | 14:00-21:00 | Highest volume, biggest moves |
| Overnight | 21:00-00:00 | Low liquidity, unpredictable |

For each session, calculate:
- Win rate
- Average R:R
- Profit factor
- Number of trades
- Maximum drawdown

Optimization decisions:
- Should we EXCLUDE any session entirely?
- Should we use DIFFERENT parameters per session?
- Are there specific HOURS within sessions to avoid?
- Session TRANSITION behavior (e.g., skip first 30min of new session?)

Create a session filter that maximizes Sharpe ratio while maintaining sufficient trade frequency.
</optimization_1_session_filters>

<optimization_2_dynamic_sl_tp>
<title>Dynamic Stop-Loss and Take-Profit</title>

Test different SL/TP approaches based on market conditions:

**ATR-Based Dynamic Exits:**
- Test SL at 1x, 1.5x, 2x, 2.5x, 3x ATR
- Test TP at 2x, 3x, 4x, 6x, 8x, 10x, 12x ATR
- Find optimal SL:TP ratio for this coin

**Volatility-Adjusted Exits:**
- In HIGH volatility (ATR > 1.5x average): wider stops, bigger targets
- In LOW volatility (ATR < 0.7x average): tighter stops, smaller targets
- Test if dynamic adjustment beats static parameters

**Time-Based Exit Adjustments:**
- Tighten stops after X candles in profit
- Move to breakeven after X% gain
- Maximum time in trade before forced exit

**Trailing Stop Variations:**
- Fixed trailing (e.g., 2x ATR behind price)
- Chandelier exit (ATR from highest high)
- Parabolic SAR trailing
- Step trailing (move stop only after X% move)

For each variation, measure:
- Impact on win rate
- Impact on average win size
- Impact on average loss size
- Net impact on expectancy
</optimization_2_dynamic_sl_tp>

<optimization_3_higher_tf_filters>
<title>Higher Timeframe Trend Filters</title>

Test adding trend filters from higher timeframes:

If base strategy is on 1m/5m/15m, test filters from:
- 1H trend (SMA50, SMA200, ADX)
- 4H trend
- Daily trend

**Filter Types to Test:**

1. **SMA Trend Filter**
   - Only LONG when price > 50 SMA on higher TF
   - Only SHORT when price < 50 SMA on higher TF
   - Test different SMA periods (20, 50, 100, 200)

2. **ADX Strength Filter**
   - Only trade when ADX > 20 (trending)
   - Or only trade when ADX < 20 (ranging) - for mean reversion
   - Test thresholds: 15, 20, 25, 30

3. **RSI Regime Filter**
   - Only LONG when higher TF RSI > 50
   - Only SHORT when higher TF RSI < 50
   - Test RSI period: 7, 14, 21

4. **Multi-MA Alignment**
   - Only trade when 20 > 50 > 200 SMA (for longs)
   - All MAs sloping in same direction

Measure for each filter:
- Trades filtered out (% reduction)
- Win rate improvement
- Profit factor improvement
- Is the filter worth the reduced opportunities?
</optimization_3_higher_tf_filters>

<optimization_4_entry_improvement>
<title>Entry Optimization with Limit Orders</title>

Market orders = instant fill but worst price
Limit orders = better price but risk missing the trade

**Limit Order Strategies to Test:**

1. **Pullback Entry**
   - Signal fires → place limit order X% below signal price
   - Test X = 0.1%, 0.2%, 0.3%, 0.5%
   - Measure: fill rate, average improvement, missed good trades

2. **Breakout Confirmation Entry**
   - Signal fires → place limit order X% ABOVE signal price
   - Only fills if momentum confirms
   - Reduces fakeout entries

3. **Zone Entry**
   - Place limit at key support/resistance level
   - Wait for price to come to you
   - Better R:R but fewer trades

4. **Scaled Entry**
   - Enter 50% at market, 50% on limit below
   - Average into position
   - Test optimal split ratios

**Fee Impact Analysis:**
- Market order fees: typically 0.05-0.1% per side
- Limit order fees: typically 0.01-0.02% per side (or rebate)
- Calculate annual fee savings from limit orders
- Does fee savings outweigh missed opportunities?

Create comparison table:
| Entry Type | Fill Rate | Avg Entry Improvement | Win Rate | Net Profit |
</optimization_4_entry_improvement>

<optimization_5_additional_filters>
<title>Additional Filter Testing</title>

Test these filters and document impact:

**Volume Filters:**
- Only trade when volume > X% of average
- Avoid low volume periods
- Volume confirmation on entry candle

**Volatility Filters:**
- Only trade when ATR in optimal range
- Avoid extremely low volatility (no movement)
- Avoid extremely high volatility (unpredictable)

**Momentum Filters:**
- RSI not overbought/oversold before entry
- MACD histogram direction
- Rate of change confirmation

**Pattern Filters:**
- Avoid entries right after big moves (exhaustion)
- Require consolidation before breakout
- Candlestick pattern confirmation

**Correlation Filters:**
- BTC trend alignment (for altcoins)
- Market sentiment alignment
- Avoid trading against macro trend

**Drawdown Protection:**
- Reduce position size after X consecutive losses
- Stop trading after daily drawdown limit hit
- Resume normal sizing after recovery

For EACH filter tested, document:
- Logic/hypothesis
- Implementation
- Results (with vs without)
- Decision: KEEP or DISCARD
</optimization_5_additional_filters>

<optimization_6_position_sizing>
<title>Position Sizing Optimization</title>

Test advanced position sizing methods:

**Kelly Criterion:**
- Calculate optimal Kelly fraction
- Test half-Kelly and quarter-Kelly
- Compare to fixed percentage

**Volatility-Adjusted Sizing:**
- Smaller positions in high volatility
- Larger positions in low volatility
- ATR-based position sizing formula

**Win Streak Adjustment:**
- Increase size after wins (anti-martingale)
- Decrease size after losses
- Test optimal adjustment factors

**Confidence-Based Sizing:**
- Larger size when more filters align
- Smaller size on weaker setups
- Score-based entry quality

**Maximum Drawdown Constraint:**
- Size positions to never exceed X% drawdown
- Dynamic sizing based on current drawdown level
</optimization_6_position_sizing>

</optimization_framework>

<optimization_process>

For each optimization category:

1. **Baseline Measurement**
   - Run original strategy, record all metrics
   - This is your benchmark

2. **Hypothesis**
   - State what you expect to improve and why
   - Based on pattern analysis, not random testing

3. **Implementation**
   - Code the optimization
   - Single variable change

4. **Testing**
   - Run backtest with optimization
   - Record all metrics

5. **Analysis**
   - Compare to baseline
   - Statistical significance check (enough trades?)
   - Logical sense check

6. **Decision**
   - ADOPT: Clear improvement, logical reason
   - REJECT: No improvement or not worth complexity
   - INVESTIGATE: Promising but needs more testing

7. **Documentation**
   - Record everything in optimization log
   - Future you will thank present you

</optimization_process>

<output_deliverables>

1. **Optimization Report**
   Save to: `./trading/results/${COIN_SYMBOL}_OPTIMIZATION_REPORT.md`

   Contents:
   - Executive Summary (top 3 optimizations that worked)
   - Session Analysis Results (table)
   - Dynamic SL/TP Results (comparison table)
   - Higher TF Filter Results (table)
   - Entry Optimization Results (table)
   - Additional Filter Results (keep/discard for each)
   - Position Sizing Results
   - Final Optimized Parameters

2. **Optimized Strategy Specification**
   Save to: `./trading/strategies/${COIN_SYMBOL}_OPTIMIZED_STRATEGY.md`

   Updated strategy with all adopted optimizations:
   - New entry rules with all filters
   - New exit rules (dynamic SL/TP)
   - Session restrictions
   - Position sizing formula
   - Limit order parameters

3. **Optimized Strategy Code**
   Save to: `./trading/strategies/${COIN_SYMBOL}_optimized_strategy.py`

   Production-ready Python implementation with:
   - All optimizations incorporated
   - Clear comments explaining each filter
   - Easy parameter adjustment section at top
   - Backtest and live trading modes

4. **Before/After Comparison**
   Save to: `./trading/results/${COIN_SYMBOL}_optimization_comparison.csv`

   | Metric | Original | Optimized | Improvement |
   |--------|----------|-----------|-------------|
   | Total Return | | | |
   | Win Rate | | | |
   | Profit Factor | | | |
   | Sharpe Ratio | | | |
   | Max Drawdown | | | |
   | Trade Count | | | |
   | Avg Trade | | | |

5. **Optimized Equity Curve**
   Save to: `./trading/results/${COIN_SYMBOL}_optimized_equity.png`

   Overlay original vs optimized equity curves for visual comparison.

</output_deliverables>

<overfitting_prevention>

After optimization, run these checks:

1. **Parameter Sensitivity**
   - Vary each optimized parameter by ±20%
   - Strategy should still be profitable
   - If small changes break it = overfit

2. **Out-of-Sample Test**
   - If data allows, split 70/30
   - Optimize on 70%, validate on 30%
   - Out-of-sample should show similar results

3. **Simplification Test**
   - Remove each filter one by one
   - If strategy survives without it, consider removing
   - Fewer filters = more robust

4. **Logic Check**
   - Can you explain each optimization in plain English?
   - Would it make sense to another trader?
   - Is there a market reason it should work?

5. **Trade Count Check**
   - Did optimization reduce trades too much?
   - Minimum ~50 trades for statistical confidence
   - Rare setups = hard to validate

Document all checks and results.
</overfitting_prevention>

<success_criteria>
- All 6 optimization categories tested systematically
- Each optimization has documented hypothesis and results
- Final strategy shows improvement in risk-adjusted returns
- Overfitting checks passed
- All 5 output files created
- Strategy remains simple enough to execute
</success_criteria>

<verification>
Before completing, verify:
- [ ] Session filter optimization complete with data table
- [ ] Dynamic SL/TP tested with multiple variants
- [ ] At least 2 higher timeframe filters tested
- [ ] Limit order entry strategies tested
- [ ] At least 5 additional filters tested
- [ ] Position sizing optimization attempted
- [ ] Before/after comparison shows net improvement
- [ ] Overfitting prevention checks documented
- [ ] All output files saved to correct locations
- [ ] Optimized strategy code is runnable
</verification>
