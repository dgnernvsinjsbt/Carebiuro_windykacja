# Pattern Discovery Script - Reuse Guide

## Quick Start: Adapt for Any Coin

The `pattern_discovery_PIPPIN.py` script can be easily adapted for other coins by changing just 4 lines:

### Step 1: Copy the Script
```bash
cp trading/pattern_discovery_PIPPIN.py trading/pattern_discovery_NEWCOIN.py
```

### Step 2: Find & Replace (4 locations)

**Line 7:** Script title
```python
# OLD:
PIPPIN/USDT Deep Pattern Discovery Analysis

# NEW:
NEWCOIN/USDT Deep Pattern Discovery Analysis
```

**Line 19:** Print statement
```python
# OLD:
print("PIPPIN/USDT PATTERN DISCOVERY ANALYSIS")

# NEW:
print("NEWCOIN/USDT PATTERN DISCOVERY ANALYSIS")
```

**Line 23:** Data file path
```python
# OLD:
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/pippin_7d_bingx.csv')

# NEW:
df = pd.read_csv('/workspaces/Carebiuro_windykacja/trading/newcoin_7d_bingx.csv')
```

**Line 389:** Report path
```python
# OLD:
report_path = '/workspaces/Carebiuro_windykacja/trading/results/PIPPIN_PATTERN_ANALYSIS.md'

# NEW:
report_path = '/workspaces/Carebiuro_windykacja/trading/results/NEWCOIN_PATTERN_ANALYSIS.md'
```

**Line 523:** CSV path
```python
# OLD:
csv_path = '/workspaces/Carebiuro_windykacja/trading/results/PIPPIN_pattern_stats.csv'

# NEW:
csv_path = '/workspaces/Carebiuro_windykacja/trading/results/NEWCOIN_pattern_stats.csv'
```

### Step 3: Run the Script
```bash
python trading/pattern_discovery_NEWCOIN.py
```

### Output Files Created
1. `trading/results/NEWCOIN_PATTERN_ANALYSIS.md` - Full report
2. `trading/results/NEWCOIN_pattern_stats.csv` - Raw statistics

---

## Data File Requirements

The script expects a CSV file with these columns:
- `timestamp` (datetime format: YYYY-MM-DD HH:MM:SS)
- `open` (float)
- `high` (float)
- `low` (float)
- `close` (float)
- `volume` (float)

Example first 3 rows:
```csv
timestamp,open,high,low,close,volume
2025-12-02 03:45:00,0.17762,0.17846,0.17564,0.17846,10561.94
2025-12-02 03:46:00,0.1774,0.1789,0.1774,0.17749,4765.3
```

---

## Customization Options

### Adjust Pattern Thresholds

**Large body candles** (Line 92):
```python
large_body_threshold = 2.0  # Change to 1.5 or 3.0
```

**Volume spike** (Line 146):
```python
volume_spike_mask = df['volume_ratio'] > 3.0  # Change to 2.5 or 4.0
```

**ATR expansion** (Line 158):
```python
atr_expansion_mask = df['atr_ratio'] > 1.5  # Change to 1.3 or 2.0
```

**RSI extremes** (Lines 179, 187):
```python
rsi_oversold = df[df['rsi_14'] < 30]  # Change to 25 or 35
rsi_overbought = df[df['rsi_14'] > 70]  # Change to 65 or 75
```

### Change Session Times

**Adjust UTC hours** (Line 67-74):
```python
def get_session(hour):
    if 0 <= hour < 8:          # Asia
        return 'Asia'
    elif 8 <= hour < 14:       # Europe
        return 'Europe'
    elif 14 <= hour < 21:      # US
        return 'US'
    else:                      # Overnight
        return 'Overnight'
```

For example, to focus on only US + Europe:
```python
def get_session(hour):
    if 8 <= hour < 14:
        return 'Europe'
    elif 14 <= hour < 21:
        return 'US'
    else:
        return 'Other'  # Avoid trading
```

---

## Analysis Sections Explained

### 1. Session Analysis (Lines 39-67)
- Compares Asia/Europe/US/Overnight sessions
- Calculates avg return, volatility (ATR), volume
- Identifies best/worst hours within each session
- **Use case:** Find best time windows to trade

### 2. Sequential Patterns (Lines 69-207)
- Tests "When X happens, what follows?" patterns
- 10 pre-configured patterns (large bodies, consecutive candles, volume spikes, etc.)
- Calculates next 1/3/5 bar returns
- **Use case:** Discover cause-effect relationships

### 3. Regime Classification (Lines 209-251)
- Classifies each bar: Trending, Mean-Reverting, Explosive, Choppy
- Calculates % time in each regime
- Average duration of each regime
- **Use case:** Know if coin is better for trend-following or mean-reversion

### 4. Statistical Edges (Lines 253-308)
- Day-of-week patterns
- Hour-of-day patterns
- Technical indicator edges (RSI, BB, volume)
- **Use case:** Find time-based or indicator-based biases

### 5. Behavioral Profile (Lines 310-343)
- Volatility character (daily range, ATR, move sizes)
- Liquidity character (volume consistency, spikes)
- Momentum character (follow-through vs fade)
- Risk character (avg loss, consecutive losses, extreme moves)
- **Use case:** Understand coin's personality for strategy design

---

## Interpreting Results

### High-Value Patterns

**Look for:**
- Win rate > 55% (beats random chance)
- Sample size > 100 (statistical significance)
- Edge > 0.1% per trade (covers fees)
- Occurs frequently (multiple times per day)

**Example good pattern:**
```
BB lower band touch: 524 occurrences, +0.047% next 5 bars, 60.1% reversion rate
→ 75 signals/day, edge covers 0.1% fees, high frequency = BACKTEST THIS
```

**Example bad pattern:**
```
After >2% body: 175 occurrences, -0.085% next bar, 46% win rate
→ Loses money, below 50% WR, infrequent = AVOID
```

### Regime Insights

**If choppy > 70%:**
- Generic trend-following will fail
- Generic mean-reversion will fail
- Need TIGHT FILTERS (volume, session, etc.)
- Examples: PIPPIN (82.6%), PENGU (91.8%)

**If trending > 30%:**
- Trend-following can work
- Use momentum confirmations
- Examples: FARTCOIN has trending regimes

**If mean-reverting > 15%:**
- Mean-reversion strategies viable
- Use BB touches, RSI extremes
- Example: PIPPIN (9.88% mean-reverting)

### Session Insights

**If one session dominates:**
- Filter trades to only that session
- Example: PIPPIN US session (+0.025% avg) vs Overnight (-0.018%)
- 50% of trades eliminated, but profitability improves

---

## Common Pitfalls

### 1. Small Sample Size
- 7 days of data = patterns may not hold
- **Solution:** Run on 30+ days, compare results

### 2. Overfitting
- 10 patterns tested = some will look good by chance
- **Solution:** Validate on out-of-sample data

### 3. Ignoring Fees
- Pattern shows +0.05% edge, but fees are 0.1%
- **Solution:** Only trade patterns with edge > 0.15%

### 4. Survivorship Bias
- Analysis assumes coin exists throughout period
- **Solution:** Be cautious with newly listed coins

---

## Advanced Modifications

### Add New Patterns

Insert after Line 207 (before regime classification):

```python
# Pattern: Price crosses above SMA(50)
cross_above_sma50 = df[(df['close'] > df['sma_50']) & (df['close'].shift(1) <= df['sma_50'].shift(1))].index
if len(cross_above_sma50) > 30:
    next_returns = [df.loc[i+1:i+10, 'returns'].sum() if i+10 < len(df) else np.nan for i in cross_above_sma50]

    patterns.append({
        'Pattern': 'Cross above SMA(50)',
        'Count': len(cross_above_sma50),
        'Next_10_Bars_%': np.nanmean(next_returns),
        'Win_Rate_%': (sum([1 for r in next_returns if r > 0.5]) / len([r for r in next_returns if not np.isnan(r)])) * 100
    })
```

### Add Visualization

Install matplotlib:
```bash
pip install matplotlib
```

Add after Line 251 (after regime stats):
```python
import matplotlib.pyplot as plt

# Regime pie chart
plt.figure(figsize=(8, 6))
plt.pie(regime_stats.values(), labels=regime_stats.keys(), autopct='%1.1f%%')
plt.title('NEWCOIN Market Regime Distribution')
plt.savefig('/workspaces/Carebiuro_windykacja/trading/results/NEWCOIN_regimes.png')
print("✓ Regime chart saved: NEWCOIN_regimes.png")
```

---

## Batch Processing Multiple Coins

Create a wrapper script:

```python
# batch_pattern_discovery.py
import subprocess

coins = ['FARTCOIN', 'MOODENG', 'DOGE', 'PEPE', 'PIPPIN']

for coin in coins:
    print(f"\n{'='*80}")
    print(f"Analyzing {coin}...")
    print('='*80)

    # Copy template
    subprocess.run(['cp', 'trading/pattern_discovery_PIPPIN.py', f'trading/pattern_discovery_{coin}.py'])

    # Run analysis
    subprocess.run(['python', f'trading/pattern_discovery_{coin}.py'])

print("\n✓ All coins analyzed!")
```

---

## Support

**Questions?** Check the full analysis example:
- PIPPIN full report: `trading/results/PIPPIN_PATTERN_ANALYSIS.md`
- PIPPIN executive summary: `trading/results/PIPPIN_EXECUTIVE_SUMMARY.md`

**Script source:** `/workspaces/Carebiuro_windykacja/trading/pattern_discovery_PIPPIN.py`
